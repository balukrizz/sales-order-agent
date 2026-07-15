"""
agents/po_extractor.py
----------------------
Document Extraction Agent.

Responsibility: turn raw PO text into a validated `PurchaseOrder` object.
It builds a LangChain PromptTemplate from prompts/po_prompt.txt, invokes the
configured LLM (Mistral or mock), then parses/repairs the JSON response and
coerces it through Pydantic.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate

from llm.mistral import get_llm
from schemas import PurchaseOrder
from utils.logger import get_logger

log = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "po_prompt.txt"

_SYSTEM = (
    "You are a precise document-extraction engine. "
    "You always respond with a single valid JSON object and nothing else."
)


class DocumentExtractionAgent:
    name = "Document Extraction Agent"

    def __init__(self) -> None:
        self.llm = get_llm()
        raw_template = _PROMPT_PATH.read_text(encoding="utf-8")
        # The prompt file contains a literal JSON schema with { } braces. Escape
        # them for f-string formatting, then restore the single {po_text} slot so
        # the on-disk prompt stays clean and human-readable.
        escaped = (
            raw_template.replace("{", "{{").replace("}", "}}").replace("{{po_text}}", "{po_text}")
        )
        self.prompt = PromptTemplate.from_template(escaped, template_format="f-string")

    def run(self, po_text: str) -> tuple[PurchaseOrder, float]:
        """Extract structured data. Returns (PurchaseOrder, confidence%)."""
        user_prompt = self.prompt.format(po_text=po_text)
        raw = self.llm.invoke(_SYSTEM, user_prompt)
        data = self._parse_json(raw)
        po = PurchaseOrder(**data)
        confidence = self._confidence(po)
        log.info("Extraction complete: PO=%s, items=%d, conf=%.1f%%",
                 po.po_number or "?", len(po.items), confidence)
        return po, confidence

    # ------------------------------------------------------------------ #
    #  JSON parsing / repair                                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_json(raw: str) -> dict:
        """LLMs sometimes wrap JSON in prose or ```json fences. Strip & parse."""
        text = raw.strip()
        # Remove code fences.
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Last resort: grab the outermost {...} block.
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        log.warning("Could not parse LLM JSON; returning empty structure.")
        return {}

    # ------------------------------------------------------------------ #
    #  Confidence heuristic                                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _confidence(po: PurchaseOrder) -> float:
        """
        Simple, explainable extraction-confidence score: the share of key
        fields that came back populated. Good enough to headline the demo
        dashboard while being honest about what it measures.
        """
        key_fields = [
            po.customer_name, po.po_number, po.po_date, po.delivery_date,
            po.currency, po.shipping_address, po.gst_number, po.payment_terms,
        ]
        filled = sum(1 for f in key_fields if str(f).strip())
        item_score = 1 if po.items else 0
        total = len(key_fields) + 1
        return round(100.0 * (filled + item_score) / total, 1)
