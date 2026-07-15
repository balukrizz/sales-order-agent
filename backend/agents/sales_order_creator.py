"""
agents/sales_order_creator.py
-----------------------------
Sales Order Creation Agent.

Responsibility: turn a validated PurchaseOrder into a SalesOrder, enrich it
from master data, assign a unique SO number, and persist it into the SQLite
"ERP". Prices missing from the PO are back-filled from the material master —
exactly what a real order-entry step would do.
"""
from __future__ import annotations

from database.db import Database
from schemas import PurchaseOrder, SalesOrder, SalesOrderItem
from utils.logger import get_logger
from utils.master_data import MasterData

log = get_logger(__name__)


class SalesOrderCreationAgent:
    name = "Sales Order Creation Agent"

    def __init__(self, master: MasterData, db: Database) -> None:
        self.master = master
        self.db = db

    def run(
        self,
        po: PurchaseOrder,
        processing_time: float = 0.0,
        extraction_conf: float = 0.0,
        validation_acc: float = 0.0,
    ) -> SalesOrder:
        customer = self.master.find_customer(po.customer_name, po.customer_code) or {}

        items: list[SalesOrderItem] = []
        for item in po.items:
            material = self.master.find_material(item.material) or {}
            # Prefer PO price; fall back to master price.
            unit_price = item.unit_price or float(material.get("Price", 0.0) or 0.0)
            description = item.description or str(material.get("Description", "")) or item.material
            items.append(SalesOrderItem(
                material=item.material,
                description=description,
                qty=item.qty,
                unit_price=unit_price,
            ))

        so = SalesOrder(
            so_number=self.db.next_so_number(),
            customer_code=customer.get("Customer Code", po.customer_code) or "UNKNOWN",
            customer_name=customer.get("Customer Name", po.customer_name) or po.customer_name,
            po_number=po.po_number,
            po_reference_date=po.po_date,
            currency=po.currency or "INR",
            shipping_address=po.shipping_address,
            gst_number=po.gst_number or str(customer.get("GST", "")),
            payment_terms=po.payment_terms or str(customer.get("Payment Terms", "")),
            items=items,
            status="Created",
            created_by="AI Agent",
        )

        self.db.save_sales_order(
            so,
            processing_time=processing_time,
            extraction_conf=extraction_conf,
            validation_acc=validation_acc,
        )
        log.info("Sales Order %s created for %s (total %.2f %s)",
                 so.so_number, so.customer_name, so.total_value, so.currency)
        return so
