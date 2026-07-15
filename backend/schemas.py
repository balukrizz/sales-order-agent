"""
schemas.py
----------
Pydantic models that define the canonical shape of data as it flows through
the pipeline:  raw extraction -> validated PO -> sales order.

Using Pydantic gives us free coercion (e.g. "100" -> 100), validation, and a
clean contract between agents.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
#  Extraction models                                                          #
# --------------------------------------------------------------------------- #
class POItem(BaseModel):
    """A single line item on the purchase order."""

    material: str = ""
    description: str = ""
    qty: float = 0.0
    unit_price: float = 0.0

    @field_validator("qty", "unit_price", mode="before")
    @classmethod
    def _clean_number(cls, v):
        """Tolerate strings like '1,200.50', '₹250', '' coming from the LLM."""
        if v is None or v == "":
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        cleaned = "".join(ch for ch in str(v) if ch.isdigit() or ch == ".")
        return float(cleaned) if cleaned not in {"", "."} else 0.0


class PurchaseOrder(BaseModel):
    """Structured purchase order as extracted from the PDF."""

    customer_name: str = ""
    customer_code: str = ""
    po_number: str = ""
    po_date: str = ""
    delivery_date: str = ""
    currency: str = "INR"
    payment_terms: str = ""
    shipping_address: str = ""
    gst_number: str = ""
    items: List[POItem] = Field(default_factory=list)

    def parsed_delivery_date(self) -> Optional[date]:
        return _parse_date(self.delivery_date)

    def parsed_po_date(self) -> Optional[date]:
        return _parse_date(self.po_date)


# --------------------------------------------------------------------------- #
#  Validation models                                                          #
# --------------------------------------------------------------------------- #
class ValidationCheck(BaseModel):
    """Result of a single validation rule."""

    name: str
    passed: bool
    level: str = "error"          # "error" | "warning" | "info"
    message: str = ""

    @property
    def icon(self) -> str:
        if self.passed:
            return "✅"
        return "⚠️" if self.level == "warning" else "❌"


class ValidationReport(BaseModel):
    """Aggregated result of the validation agent."""

    checks: List[ValidationCheck] = Field(default_factory=list)
    customer_suggestions: List[str] = Field(default_factory=list)

    @property
    def has_blocking_errors(self) -> bool:
        return any((not c.passed) and c.level == "error" for c in self.checks)

    @property
    def warnings(self) -> List[ValidationCheck]:
        return [c for c in self.checks if (not c.passed) and c.level == "warning"]

    @property
    def accuracy(self) -> float:
        """Share of checks that passed — surfaced as a KPI in the dashboard."""
        if not self.checks:
            return 0.0
        return round(100.0 * sum(c.passed for c in self.checks) / len(self.checks), 1)


# --------------------------------------------------------------------------- #
#  Sales order models                                                         #
# --------------------------------------------------------------------------- #
class SalesOrderItem(BaseModel):
    material: str
    description: str
    qty: float
    unit_price: float

    @property
    def net_value(self) -> float:
        return round(self.qty * self.unit_price, 2)


class SalesOrder(BaseModel):
    so_number: str
    customer_code: str
    customer_name: str
    po_number: str
    po_reference_date: str = ""
    currency: str = "INR"
    shipping_address: str = ""
    gst_number: str = ""
    payment_terms: str = ""
    items: List[SalesOrderItem] = Field(default_factory=list)
    status: str = "Created"
    created_by: str = "AI Agent"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # --- money -------------------------------------------------------------- #
    @property
    def net_value(self) -> float:
        return round(sum(i.net_value for i in self.items), 2)

    @property
    def tax_rate(self) -> float:
        return 0.18  # demo assumes 18% GST

    @property
    def tax_amount(self) -> float:
        return round(self.net_value * self.tax_rate, 2)

    @property
    def total_value(self) -> float:
        return round(self.net_value + self.tax_amount, 2)


# --------------------------------------------------------------------------- #
#  Date parsing helper                                                        #
# --------------------------------------------------------------------------- #
_DATE_FORMATS = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
    "%Y/%m/%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
)


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
