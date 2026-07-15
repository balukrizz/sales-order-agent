"""
FastAPI backend for the Purchase Order -> Sales Order agent.

It wraps the existing four-agent pipeline (extraction -> validation -> business
rules -> sales-order creation) behind a small HTTP API that the Next.js
frontend on Vercel calls. The agent code itself is unchanged; this module only
serializes its objects to JSON and adds CORS + a couple of convenience routes.

Run locally:      uvicorn app:app --reload --port 8000
Run on Render:    uvicorn app:app --host 0.0.0.0 --port $PORT
On Vercel:        exposed via api/index.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from agents.orchestrator import Orchestrator, PipelineEvent, PipelineResult
from config import settings
from database.db import Database
from schemas import PurchaseOrder, SalesOrder, ValidationReport
from utils.pdf_generator import SalesOrderPDF

SAMPLES = Path(__file__).resolve().parent / "samples"
SAMPLE_FILES = {
    "default": "sample_po.pdf",
    "success": "sample_po_success.pdf",
    "partial": "sample_po_partial_stock.pdf",
    "errors": "sample_po_validation_errors.pdf",
}

app = FastAPI(title="PO -> Sales Order Agent API", version="1.0.0")

# CORS: allow the Vercel frontend. Set FRONTEND_ORIGIN in prod (comma-separated
# for multiple). Falls back to "*" so local dev and preview URLs just work.
_origins = os.getenv("FRONTEND_ORIGIN", "*")
allow_origins = ["*"] if _origins.strip() == "*" else [o.strip() for o in _origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
#  Serialization helpers (Pydantic computed props aren't in model_dump)        #
# --------------------------------------------------------------------------- #
def po_json(po: Optional[PurchaseOrder]) -> Optional[dict]:
    if po is None:
        return None
    return po.model_dump(mode="json")


def validation_json(vr: Optional[ValidationReport]) -> Optional[dict]:
    if vr is None:
        return None
    return {
        "accuracy": vr.accuracy,
        "has_blocking_errors": vr.has_blocking_errors,
        "customer_suggestions": list(vr.customer_suggestions),
        "checks": [
            {"name": c.name, "passed": c.passed, "level": c.level,
             "message": c.message, "icon": c.icon}
            for c in vr.checks
        ],
        "warnings": [
            {"name": c.name, "message": c.message} for c in vr.warnings
        ],
    }


def so_json(so: Optional[SalesOrder]) -> Optional[dict]:
    if so is None:
        return None
    return {
        "so_number": so.so_number,
        "customer_code": so.customer_code,
        "customer_name": so.customer_name,
        "po_number": so.po_number,
        "po_reference_date": so.po_reference_date,
        "currency": so.currency,
        "shipping_address": so.shipping_address,
        "gst_number": so.gst_number,
        "payment_terms": so.payment_terms,
        "status": so.status,
        "created_by": so.created_by,
        "created_at": getattr(so, "created_at", ""),
        "net_value": so.net_value,
        "tax_rate": getattr(so, "tax_rate", 0.18),
        "tax_amount": so.tax_amount,
        "total_value": so.total_value,
        "items": [
            {"material": it.material, "description": it.description,
             "qty": it.qty, "unit_price": it.unit_price, "net_value": it.net_value}
            for it in so.items
        ],
    }


def result_json(res: PipelineResult) -> dict:
    return {
        "success": res.success,
        "message": res.message,
        "duplicate": res.duplicate,
        "extraction_conf": res.extraction_conf,
        "processing_time": res.processing_time,
        "purchase_order": po_json(res.purchase_order),
        "validation": validation_json(res.validation),
        "sales_order": so_json(res.sales_order),
    }


def agents_json(ev: PipelineEvent) -> dict:
    return {
        "agents": [
            {"key": a.key, "label": a.label, "status": a.status, "detail": a.detail}
            for a in ev.agents
        ],
        "reasoning": list(ev.reasoning),
        "result": result_json(ev.result) if ev.result else None,
    }


# One orchestrator/db per process. (On serverless each cold start rebuilds it;
# that is fine — the master data load is cheap.)
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def get_db() -> Database:
    return Database()


# --------------------------------------------------------------------------- #
#  Routes                                                                      #
# --------------------------------------------------------------------------- #
@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": "po-sales-order-agent"}


@app.get("/api/config")
def api_config() -> dict:
    return {
        "provider": "mock" if settings.use_mock_llm else "mistral",
        "model": settings.mistral_model if not settings.use_mock_llm else None,
        "ocr": settings.enable_ocr,
    }


@app.get("/api/sample-po")
def sample_po(kind: str = "default") -> Response:
    name = SAMPLE_FILES.get(kind, SAMPLE_FILES["default"])
    path = SAMPLES / name
    if not path.exists():
        raise HTTPException(404, f"sample '{kind}' not found")
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


@app.post("/api/process")
async def process(file: UploadFile = File(...)) -> dict:
    pdf = await file.read()
    if not pdf:
        raise HTTPException(400, "empty file")
    try:
        res = get_orchestrator().run(pdf)
    except Exception as exc:  # keep the API from 500-crashing the demo
        raise HTTPException(500, f"pipeline error: {exc}") from exc
    return result_json(res)


@app.post("/api/process/stream")
async def process_stream(file: UploadFile = File(...)) -> StreamingResponse:
    """Server-Sent Events: one JSON payload per agent-state change, so the
    frontend can animate the four-agent timeline in real time."""
    pdf = await file.read()
    if not pdf:
        raise HTTPException(400, "empty file")

    orch = get_orchestrator()

    def gen() -> Iterator[str]:
        try:
            for ev in orch.stream(pdf):
                yield f"data: {json.dumps(agents_json(ev))}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sales-orders")
def list_sales_orders() -> List[dict]:
    return get_db().all_headers()


@app.get("/api/sales-orders/{so_number}")
def get_sales_order(so_number: str) -> dict:
    so = get_db().get_sales_order(so_number)
    if so is None:
        raise HTTPException(404, f"Sales Order {so_number} not found")
    return so_json(so)


@app.get("/api/sales-orders/{so_number}/pdf")
def sales_order_pdf(so_number: str) -> Response:
    so = get_db().get_sales_order(so_number)
    if so is None:
        raise HTTPException(404, f"Sales Order {so_number} not found")
    pdf_bytes = SalesOrderPDF().build(so)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{so_number}.pdf"'},
    )


@app.get("/api/kpis")
def kpis() -> dict:
    return get_db().kpis()


@app.post("/api/reset")
def reset() -> dict:
    """Clear all demo Sales Orders (keeps the schema)."""
    import sqlite3
    db = get_db()
    db.init_db()  # ensure tables exist
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("DELETE FROM SalesOrderItems")
        conn.execute("DELETE FROM SalesOrderHeader")
        conn.commit()
    return {"status": "reset"}
