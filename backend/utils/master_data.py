"""
utils/master_data.py
--------------------
Loads customer & material master CSVs into memory and offers the lookups the
validation / business-rules agents need, including fuzzy customer matching so
we can "suggest top 3 matching customers" when an exact match fails.

Uses only the Python standard library (csv + difflib) so the backend stays
lean enough for serverless deployment — no pandas dependency.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)


def _read_csv(path: str) -> List[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(f)]


def _to_float(v: str) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _to_int(v: str) -> int:
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return 0


@dataclass
class MasterData:
    customers: List[dict]
    materials: List[dict]

    # ---- customer lookups -------------------------------------------- #
    def find_customer(self, name: str = "", code: str = "") -> Optional[dict]:
        """Return the customer row (as dict) by code first, then exact name."""
        if code:
            for row in self.customers:
                if row.get("Customer Code", "").upper() == code.upper():
                    return dict(row)
        if name:
            norm = name.strip().lower()
            for row in self.customers:
                if row.get("Customer Name", "").strip().lower() == norm:
                    return dict(row)
        return None

    def suggest_customers(self, name: str, top_n: int = 3) -> List[str]:
        """Fuzzy match on customer name -> top-N candidate names."""
        if not name:
            return []
        target = name.strip().lower()
        scored = [
            (SequenceMatcher(None, target, row.get("Customer Name", "").strip().lower()).ratio(),
             row.get("Customer Name", ""))
            for row in self.customers
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [nm for _, nm in scored[:top_n]]

    # ---- material lookups -------------------------------------------- #
    def find_material(self, code: str) -> Optional[dict]:
        if not code:
            return None
        for row in self.materials:
            if row.get("Material Code", "").upper() == code.upper():
                return dict(row)
        return None

    # ---- KPI helpers -------------------------------------------------- #
    def counts(self) -> Dict[str, int]:
        return {"customers": len(self.customers), "materials": len(self.materials)}


def load_master_data() -> MasterData:
    """Read both master CSVs from the paths configured via environment."""
    customers = _read_csv(settings.customer_master)
    materials = _read_csv(settings.material_master)
    # Numeric coercion for the fields the agents compute on.
    for m in materials:
        m["Price"] = _to_float(m.get("Price", "0"))
        m["Stock"] = _to_int(m.get("Stock", "0"))
    log.info("Loaded master data: %d customers, %d materials", len(customers), len(materials))
    return MasterData(customers=customers, materials=materials)
