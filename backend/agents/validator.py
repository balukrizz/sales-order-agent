"""
agents/validator.py
--------------------
Two agents in one module:

* ValidationAgent     — master-data & field-level validation
    - Customer exists          - Price available
    - Material exists          - GST present
    - Quantity > 0             - Delivery date valid (parseable)

* BusinessRulesAgent  — enterprise business rules on top of validation
    - Delivery date not in the past
    - Duplicate PO must not create a second SO
    - Stock check -> "Partial Delivery Possible" warning
    - Missing customer -> suggest top-3 matches

Both return / extend a `ValidationReport`.
"""
from __future__ import annotations

from datetime import date

from database.db import Database
from schemas import PurchaseOrder, ValidationCheck, ValidationReport
from utils.logger import get_logger
from utils.master_data import MasterData

log = get_logger(__name__)


class ValidationAgent:
    name = "Validation Agent"

    def __init__(self, master: MasterData) -> None:
        self.master = master

    def run(self, po: PurchaseOrder) -> ValidationReport:
        report = ValidationReport()

        # 1) Customer exists ------------------------------------------------
        customer = self.master.find_customer(po.customer_name, po.customer_code)
        if customer:
            report.checks.append(ValidationCheck(
                name="Customer exists", passed=True,
                message=f"Matched {customer['Customer Name']} ({customer['Customer Code']})"))
        else:
            report.checks.append(ValidationCheck(
                name="Customer exists", passed=False, level="error",
                message=f"No master record for '{po.customer_name or po.customer_code}'"))

        # 2/3/4) Per-item: material exists, qty>0, price available ----------
        if not po.items:
            report.checks.append(ValidationCheck(
                name="Line items present", passed=False, level="error",
                message="No line items were extracted from the PO"))

        for idx, item in enumerate(po.items, start=1):
            material = self.master.find_material(item.material)

            report.checks.append(ValidationCheck(
                name=f"Material valid (line {idx})",
                passed=bool(material),
                level="error",
                message=(f"{item.material} found in material master"
                         if material else f"Unknown material code '{item.material}'")))

            report.checks.append(ValidationCheck(
                name=f"Quantity > 0 (line {idx})",
                passed=item.qty > 0,
                level="error",
                message=f"Qty = {item.qty:g}" if item.qty > 0 else "Quantity must be greater than 0"))

            price_ok = item.unit_price > 0 or bool(material)
            report.checks.append(ValidationCheck(
                name=f"Price available (line {idx})",
                passed=price_ok,
                level="error",
                message=("Price on PO or in master"
                         if price_ok else "No price on PO and none in master")))

        # 5) GST present ----------------------------------------------------
        report.checks.append(ValidationCheck(
            name="GST present",
            passed=bool(po.gst_number.strip()),
            level="warning",
            message=(f"GSTIN {po.gst_number}" if po.gst_number.strip()
                     else "GST number missing (non-blocking)")))

        # 6) Delivery date valid (parseable) --------------------------------
        parsed = po.parsed_delivery_date()
        report.checks.append(ValidationCheck(
            name="Delivery date valid",
            passed=parsed is not None,
            level="error",
            message=(f"Delivery on {parsed.isoformat()}" if parsed
                     else f"Unrecognised delivery date '{po.delivery_date}'")))

        log.info("Validation produced %d checks (accuracy %.1f%%)",
                 len(report.checks), report.accuracy)
        return report


class BusinessRulesAgent:
    name = "Business Rules Agent"

    def __init__(self, master: MasterData, db: Database) -> None:
        self.master = master
        self.db = db

    def run(self, po: PurchaseOrder, report: ValidationReport) -> ValidationReport:
        # Rule: delivery date cannot be before today ------------------------
        parsed = po.parsed_delivery_date()
        if parsed is not None:
            in_future = parsed >= date.today()
            report.checks.append(ValidationCheck(
                name="Delivery date not in past",
                passed=in_future,
                level="error",
                message=("OK" if in_future
                         else f"Delivery date {parsed.isoformat()} is before today")))

        # Rule: duplicate PO must not create another SO ---------------------
        existing = self.db.find_so_by_po(po.po_number)
        report.checks.append(ValidationCheck(
            name="PO not duplicate",
            passed=existing is None,
            level="error",
            message=("New PO" if existing is None
                     else f"PO {po.po_number} already created as {existing}")))

        # Rule: stock check -> partial delivery warning ---------------------
        for idx, item in enumerate(po.items, start=1):
            material = self.master.find_material(item.material)
            if material:
                stock = int(material.get("Stock", 0))
                if item.qty > stock:
                    report.checks.append(ValidationCheck(
                        name=f"Stock sufficient (line {idx})",
                        passed=False, level="warning",
                        message=(f"Requested {item.qty:g} > stock {stock}. "
                                 f"Partial Delivery Possible ({stock} now).")))
                else:
                    report.checks.append(ValidationCheck(
                        name=f"Stock sufficient (line {idx})",
                        passed=True, level="info",
                        message=f"{stock} in stock"))

        # Rule: missing customer -> suggest top-3 --------------------------
        if not self.master.find_customer(po.customer_name, po.customer_code):
            report.customer_suggestions = self.master.suggest_customers(po.customer_name, top_n=3)
            if report.customer_suggestions:
                log.info("Suggesting customers: %s", report.customer_suggestions)

        return report
