"""
agents/orchestrator.py
----------------------
Multi-agent orchestrator (the "Agentic AI" core).

Runs four cooperating agents in sequence and *streams* their status so the UI
can render an enterprise-grade execution timeline:

    Document Extraction Agent  ->  Running / Completed
    Validation Agent           ->  Running / Completed
    Business Rules Agent       ->  Running / Completed
    Sales Order Creation Agent ->  Running / Success | Failed

It also emits a fine-grained reasoning log (Step 6 in the spec) so the demo
can show the agent "thinking" line by line.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from agents.po_extractor import DocumentExtractionAgent
from agents.sales_order_creator import SalesOrderCreationAgent
from agents.validator import BusinessRulesAgent, ValidationAgent
from database.db import Database
from schemas import PurchaseOrder, SalesOrder, ValidationReport
from utils.logger import get_logger
from utils.master_data import load_master_data
from utils.pdf_reader import PDFReader

log = get_logger(__name__)

# Agent lifecycle states used by the timeline UI.
PENDING, RUNNING, COMPLETED, SUCCESS, FAILED = (
    "pending", "running", "completed", "success", "failed",
)


@dataclass
class AgentState:
    key: str
    label: str
    status: str = PENDING
    detail: str = ""


@dataclass
class PipelineResult:
    success: bool = False
    message: str = ""
    duplicate: bool = False
    purchase_order: Optional[PurchaseOrder] = None
    validation: Optional[ValidationReport] = None
    sales_order: Optional[SalesOrder] = None
    extraction_conf: float = 0.0
    processing_time: float = 0.0


@dataclass
class PipelineEvent:
    """One streamed update: the whole current state, easy for the UI to render."""

    agents: List[AgentState]
    reasoning: List[str] = field(default_factory=list)
    result: Optional[PipelineResult] = None


class Orchestrator:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or Database()
        self.master = load_master_data()
        self.reader = PDFReader()
        self.extractor = DocumentExtractionAgent()
        self.validator = ValidationAgent(self.master)
        self.rules = BusinessRulesAgent(self.master, self.db)
        self.creator = SalesOrderCreationAgent(self.master, self.db)

    # ------------------------------------------------------------------ #
    #  Streaming pipeline                                                #
    # ------------------------------------------------------------------ #
    def stream(self, pdf_bytes: bytes, step_delay: float = 0.35) -> Iterator[PipelineEvent]:
        """
        Yield PipelineEvents as the pipeline advances. `step_delay` adds a small
        pause purely so the on-screen animation is legible during a live demo.
        """
        start = time.perf_counter()
        agents = [
            AgentState("extract", "Document Extraction Agent"),
            AgentState("validate", "Validation Agent"),
            AgentState("rules", "Business Rules Agent"),
            AgentState("create", "Sales Order Creation Agent"),
        ]
        reasoning: List[str] = []

        def emit(result: Optional[PipelineResult] = None) -> PipelineEvent:
            return PipelineEvent(agents=[AgentState(**a.__dict__) for a in agents],
                                 reasoning=list(reasoning), result=result)

        # ---------- Agent 1: extraction --------------------------------- #
        agents[0].status = RUNNING
        reasoning.append("Reading Purchase Order...")
        yield emit(); time.sleep(step_delay)

        po_text = self.reader.extract_text(pdf_bytes)
        reasoning.append("Extracting fields with the LLM...")
        yield emit(); time.sleep(step_delay)

        po, confidence = self.extractor.run(po_text)
        reasoning.append(f"Extracted customer '{po.customer_name or 'unknown'}' "
                         f"and {len(po.items)} line item(s).")
        agents[0].status = COMPLETED
        agents[0].detail = f"{len(po.items)} items · {confidence:.0f}% confidence"
        yield emit(); time.sleep(step_delay)

        # ---------- Agent 2: validation --------------------------------- #
        agents[1].status = RUNNING
        reasoning.append("Matching Customer Master...")
        yield emit(); time.sleep(step_delay)
        reasoning.append("Matching Material Master...")
        yield emit(); time.sleep(step_delay)
        reasoning.append("Checking prices and quantities...")

        report = self.validator.run(po)
        agents[1].status = COMPLETED
        agents[1].detail = f"{report.accuracy:.0f}% checks passed"
        yield emit(); time.sleep(step_delay)

        # ---------- Agent 3: business rules ----------------------------- #
        agents[2].status = RUNNING
        reasoning.append("Validating Delivery Date...")
        yield emit(); time.sleep(step_delay)
        reasoning.append("Checking for duplicate PO and stock levels...")

        report = self.rules.run(po, report)
        agents[2].status = COMPLETED
        n_warn = len(report.warnings)
        agents[2].detail = f"{n_warn} warning(s)" if n_warn else "all rules OK"
        yield emit(); time.sleep(step_delay)

        # ---------- Gate: blocking errors? ------------------------------ #
        if report.has_blocking_errors:
            # Distinguish "duplicate PO" (a legitimate stop) from data errors.
            dup = next((c for c in report.checks
                        if c.name == "PO not duplicate" and not c.passed), None)
            agents[3].status = FAILED
            agents[3].detail = "blocked by validation"
            elapsed = round(time.perf_counter() - start, 2)
            reasoning.append("Sales Order NOT created — validation failed.")
            result = PipelineResult(
                success=False,
                duplicate=dup is not None,
                message=(dup.message if dup else
                         "Validation failed. Resolve the highlighted errors and re-run."),
                purchase_order=po,
                validation=report,
                extraction_conf=confidence,
                processing_time=elapsed,
            )
            yield emit(result)
            return

        # ---------- Agent 4: sales order creation ----------------------- #
        agents[3].status = RUNNING
        reasoning.append("Generating Sales Order...")
        yield emit(); time.sleep(step_delay)

        elapsed = round(time.perf_counter() - start, 2)
        so = self.creator.run(
            po,
            processing_time=elapsed,
            extraction_conf=confidence,
            validation_acc=report.accuracy,
        )
        reasoning.append("Saving into ERP (SQLite)...")
        yield emit(); time.sleep(step_delay)

        agents[3].status = SUCCESS
        agents[3].detail = so.so_number
        reasoning.append(f"Sales Order {so.so_number} created successfully.")
        result = PipelineResult(
            success=True,
            message=f"Sales Order {so.so_number} created successfully.",
            purchase_order=po,
            validation=report,
            sales_order=so,
            extraction_conf=confidence,
            processing_time=elapsed,
        )
        yield emit(result)

    # ------------------------------------------------------------------ #
    #  Non-streaming convenience (tests / CLI)                           #
    # ------------------------------------------------------------------ #
    def run(self, pdf_bytes: bytes) -> PipelineResult:
        result: Optional[PipelineResult] = None
        for event in self.stream(pdf_bytes, step_delay=0.0):
            if event.result is not None:
                result = event.result
        assert result is not None
        return result
