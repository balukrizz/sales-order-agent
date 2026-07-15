"""
database/db.py
--------------
SQLite persistence layer that *simulates* an ERP order store. Handles schema
creation, atomic Sales-Order-number generation, header/item persistence,
duplicate-PO detection and the KPI aggregates the dashboard reads.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

from config import settings
from schemas import SalesOrder, SalesOrderItem
from utils.logger import get_logger

log = get_logger(__name__)

_SO_SEQ_START = 100001  # first SO number -> SO100001


class Database:
    """Lightweight wrapper around the SQLite ERP-simulation store."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or settings.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Schema                                                            #
    # ------------------------------------------------------------------ #
    def init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS SalesOrderHeader (
                    so_number         TEXT PRIMARY KEY,
                    customer_code     TEXT,
                    customer_name     TEXT,
                    po_number         TEXT,
                    po_reference_date TEXT,
                    currency          TEXT,
                    shipping_address  TEXT,
                    gst_number        TEXT,
                    payment_terms     TEXT,
                    net_value         REAL,
                    tax_amount        REAL,
                    total_value       REAL,
                    status            TEXT,
                    created_by        TEXT,
                    created_at        TEXT,
                    processing_time   REAL,
                    extraction_conf   REAL,
                    validation_acc    REAL
                );

                CREATE TABLE IF NOT EXISTS SalesOrderItems (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    so_number     TEXT,
                    line_no       INTEGER,
                    material      TEXT,
                    description   TEXT,
                    qty           REAL,
                    unit_price    REAL,
                    net_value     REAL,
                    FOREIGN KEY (so_number) REFERENCES SalesOrderHeader(so_number)
                );
                """
            )
        log.info("SQLite schema ready at %s", self.db_path)

    # ------------------------------------------------------------------ #
    #  SO number generation                                              #
    # ------------------------------------------------------------------ #
    def next_so_number(self) -> str:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM SalesOrderHeader").fetchone()
            seq = _SO_SEQ_START + row["n"]
        return f"SO{seq}"

    # ------------------------------------------------------------------ #
    #  Duplicate PO detection (business rule)                            #
    # ------------------------------------------------------------------ #
    def find_so_by_po(self, po_number: str) -> Optional[str]:
        if not po_number:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT so_number FROM SalesOrderHeader WHERE po_number = ? LIMIT 1",
                (po_number,),
            ).fetchone()
        return row["so_number"] if row else None

    # ------------------------------------------------------------------ #
    #  Persistence                                                       #
    # ------------------------------------------------------------------ #
    def save_sales_order(
        self,
        so: SalesOrder,
        processing_time: float = 0.0,
        extraction_conf: float = 0.0,
        validation_acc: float = 0.0,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO SalesOrderHeader
                    (so_number, customer_code, customer_name, po_number,
                     po_reference_date, currency, shipping_address, gst_number,
                     payment_terms, net_value, tax_amount, total_value, status,
                     created_by, created_at, processing_time, extraction_conf,
                     validation_acc)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    so.so_number, so.customer_code, so.customer_name, so.po_number,
                    so.po_reference_date, so.currency, so.shipping_address, so.gst_number,
                    so.payment_terms, so.net_value, so.tax_amount, so.total_value, so.status,
                    so.created_by, so.created_at, processing_time, extraction_conf,
                    validation_acc,
                ),
            )
            for line_no, item in enumerate(so.items, start=10):
                conn.execute(
                    """
                    INSERT INTO SalesOrderItems
                        (so_number, line_no, material, description, qty, unit_price, net_value)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (so.so_number, line_no, item.material, item.description,
                     item.qty, item.unit_price, item.net_value),
                )
        log.info("Persisted Sales Order %s (%d items)", so.so_number, len(so.items))

    # ------------------------------------------------------------------ #
    #  Reads                                                             #
    # ------------------------------------------------------------------ #
    def get_sales_order(self, so_number: str) -> Optional[SalesOrder]:
        with self._conn() as conn:
            h = conn.execute(
                "SELECT * FROM SalesOrderHeader WHERE so_number = ?", (so_number,)
            ).fetchone()
            if not h:
                return None
            items = conn.execute(
                "SELECT * FROM SalesOrderItems WHERE so_number = ? ORDER BY line_no", (so_number,)
            ).fetchall()
        return SalesOrder(
            so_number=h["so_number"],
            customer_code=h["customer_code"],
            customer_name=h["customer_name"],
            po_number=h["po_number"],
            po_reference_date=h["po_reference_date"],
            currency=h["currency"],
            shipping_address=h["shipping_address"],
            gst_number=h["gst_number"],
            payment_terms=h["payment_terms"],
            status=h["status"],
            created_by=h["created_by"],
            created_at=h["created_at"],
            items=[
                SalesOrderItem(
                    material=i["material"], description=i["description"],
                    qty=i["qty"], unit_price=i["unit_price"],
                )
                for i in items
            ],
        )

    def all_headers(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM SalesOrderHeader ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  KPI aggregates for the dashboard                                  #
    # ------------------------------------------------------------------ #
    def kpis(self) -> Dict[str, float]:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                         AS orders,
                    COALESCE(AVG(processing_time),0) AS avg_time,
                    COALESCE(AVG(validation_acc),0)  AS avg_val,
                    COALESCE(AVG(extraction_conf),0) AS avg_conf,
                    COALESCE(SUM(total_value),0)     AS total_value
                FROM SalesOrderHeader
                """
            ).fetchone()
            today = conn.execute(
                "SELECT COUNT(*) AS n FROM SalesOrderHeader WHERE date(created_at) = date('now','localtime')"
            ).fetchone()
        return {
            "orders": row["orders"],
            "avg_time": round(row["avg_time"], 2),
            "avg_val": round(row["avg_val"], 1),
            "avg_conf": round(row["avg_conf"], 1),
            "total_value": round(row["total_value"], 2),
            "today": today["n"],
        }
