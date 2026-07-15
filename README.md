# Purchase Order → Sales Order Agent (Web)

A production-style, two-tier version of the PO → Sales Order agent, ready to
deploy on **Vercel** (frontend) + **Render** (backend API).

- **`frontend/`** — Next.js 14 (App Router, TypeScript, Tailwind). Upload a PO,
  watch the four-agent pipeline animate live, see the validation report and the
  created Sales Order, browse all orders, and view a KPI dashboard.
- **`backend/`** — FastAPI wrapping the existing four-agent LangChain pipeline
  (Document Extraction → Validation → Business Rules → Sales Order Creation).
  Same agents as the Streamlit build; only the transport is new (HTTP + SSE).

## How it fits together

```
Browser ──HTTPS──▶ Next.js on Vercel ──fetch/SSE──▶ FastAPI on Render ──▶ agents ──▶ SQLite ERP
```

The frontend calls the backend via `NEXT_PUBLIC_API_URL`. The backend exposes:

| Route | Purpose |
|---|---|
| `GET /api/config` | LLM provider + OCR status for the UI |
| `GET /api/sample-po?kind=…` | Bundled sample PO PDFs (default / success / partial / errors) |
| `POST /api/process` | Run the pipeline, return the full JSON result |
| `POST /api/process/stream` | Same, streamed as SSE for the live timeline |
| `GET /api/sales-orders` | List created Sales Orders |
| `GET /api/sales-orders/{so}` | One Sales Order (detail) |
| `GET /api/sales-orders/{so}/pdf` | Download the branded Sales Order PDF |
| `GET /api/kpis` | Dashboard metrics |
| `POST /api/reset` | Clear demo data |

## Deploy

See **[DEPLOY.md](./DEPLOY.md)** for the full step-by-step (push → Render → Vercel → CORS).

## Modes

Ships in **mock mode** (deterministic offline extraction) so it runs with zero
setup. Set `LLM_PROVIDER=mistral` + `MISTRAL_API_KEY` on the backend for live
Mistral extraction; it auto-falls back to mock if the key is missing.

## Notes

- The ERP is a local **SQLite** stand-in. To go live against SAP / Oracle /
  Dynamics, swap the persistence call in `backend/database/db.py` — the
  extraction, validation, and orchestration layers stay unchanged.
- OCR is off by default and needs the system Tesseract binary; leave it off for
  text-based PDFs (including the samples).
