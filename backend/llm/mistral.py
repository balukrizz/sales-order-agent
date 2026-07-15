"""
llm/mistral.py
--------------
Thin, provider-agnostic LLM layer.

`get_llm()` returns an object exposing a single `.invoke(system, user) -> str`
method so the rest of the code never has to care which backend is live:

    * MistralLLM  -> real Mistral API via LangChain's ChatMistralAI
    * MockLLM     -> deterministic offline extractor (regex based)

The mock lets the whole pipeline run with zero network / zero API key, which
is invaluable for an on-stage client demo where WiFi cannot be trusted.
"""
from __future__ import annotations

import json
import re
from typing import Protocol

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)


class LLM(Protocol):
    """Structural interface every provider must satisfy."""

    name: str

    def invoke(self, system_prompt: str, user_prompt: str) -> str: ...


# --------------------------------------------------------------------------- #
#  Real Mistral provider (LangChain)                                          #
# --------------------------------------------------------------------------- #
class MistralLLM:
    """Wraps langchain_mistralai.ChatMistralAI behind our simple interface."""

    name = "mistral"

    def __init__(self) -> None:
        # Imported lazily so `mock` mode works even if the package is absent.
        from langchain_mistralai import ChatMistralAI

        self._model_id = settings.mistral_model
        self._client = ChatMistralAI(
            model=settings.mistral_model,
            mistral_api_key=settings.mistral_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        log.info("Mistral LLM initialised (model=%s)", self._model_id)

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = self._client.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)


# --------------------------------------------------------------------------- #
#  Offline mock provider                                                      #
# --------------------------------------------------------------------------- #
class MockLLM:
    """
    Deterministic offline "extraction". It does NOT pretend to be an LLM's
    reasoning — it simply parses the raw PO text with resilient regexes and
    returns the same JSON shape the real model would. Perfect for demos with
    no connectivity.
    """

    name = "mock"

    def __init__(self) -> None:
        log.warning("Using MOCK LLM (offline). Set LLM_PROVIDER=mistral + a key for live extraction.")

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        text = user_prompt
        # Lookahead that stops a field value before the *next* known label on
        # the same line (PDF text often merges two visual columns into one line)
        # or at end of line.
        stop = (
            r"(?=\s+(?:PO\s*Number|PO\s*Date|Delivery\s*Date|Delivery|Currency|"
            r"GST|Payment\s*Terms|Customer\s*Code|Shipping\s*Address|Material\s*Code)\b|$)"
        )
        data = {
            "customer_name": self._first(text, r"(?:Customer|Bill\s*To|Sold\s*To)\s*(?:Name)?\s*[:\-]\s*(.+?)" + stop),
            "customer_code": self._first(text, r"Customer\s*Code\s*[:\-]\s*([A-Za-z0-9\-]+)"),
            "po_number": self._first(text, r"(?:PO|Purchase\s*Order)\s*(?:No\.?|Number|#)\s*[:\-]\s*([A-Za-z0-9\-\/]+)"),
            "po_date": self._first(text, r"PO\s*Date\s*[:\-]\s*([0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{1,4})"),
            "delivery_date": self._first(text, r"(?:Delivery|Deliver\s*By|Required)\s*Date\s*[:\-]\s*([0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{1,4})"),
            "currency": self._first(text, r"Currency\s*[:\-]\s*([A-Za-z]{3})") or self._guess_currency(text),
            "payment_terms": self._first(text, r"Payment\s*Terms\s*[:\-]\s*(.+?)" + stop),
            "shipping_address": self._first(text, r"(?:Shipping|Ship\s*To|Delivery)\s*Address\s*[:\-]\s*(.+)"),
            "gst_number": self._first(text, r"GST(?:IN)?\s*(?:No\.?|Number)?\s*[:\-]\s*([0-9A-Z]{15})"),
            "items": self._items(text),
        }
        return json.dumps(data)

    # --- helpers ----------------------------------------------------------- #
    @staticmethod
    def _first(text: str, pattern: str) -> str:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _guess_currency(text: str) -> str:
        if "₹" in text or "INR" in text or "GST" in text:
            return "INR"
        if "$" in text:
            return "USD"
        return "INR"

    @staticmethod
    def _items(text: str) -> list[dict]:
        """
        Parse a line-item table. Expected rough shape per row:
            MAT-1001   Steel Rod 12mm   100   250.00
        i.e. code, description, qty, unit price.
        """
        items: list[dict] = []
        row_re = re.compile(
            r"(?P<mat>[A-Z]{2,}-?\d{3,})\s+"
            r"(?P<desc>.+?)\s+"
            r"(?P<qty>\d+(?:\.\d+)?)\s+"
            r"(?P<price>\d+(?:,\d{3})*(?:\.\d+)?)\s*$",
            flags=re.MULTILINE,
        )
        for m in row_re.finditer(text):
            items.append(
                {
                    "material": m.group("mat").strip(),
                    "description": m.group("desc").strip(),
                    "qty": m.group("qty").strip(),
                    "unit_price": m.group("price").replace(",", "").strip(),
                }
            )
        return items


# --------------------------------------------------------------------------- #
#  Factory                                                                    #
# --------------------------------------------------------------------------- #
def get_llm() -> LLM:
    """Return the configured LLM provider (mock fallback is automatic)."""
    if settings.use_mock_llm:
        return MockLLM()
    return MistralLLM()
