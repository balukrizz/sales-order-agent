"""
utils/pdf_reader.py
-------------------
Robust PDF -> text extraction with a layered strategy:

    1. pdfplumber   — best for well-structured, text-based PDFs (keeps tables).
    2. PyMuPDF      — fast fallback / secondary opinion for text extraction.
    3. OCR          — only when the page is image-only (scanned PO) AND OCR is
                      enabled. Uses PyMuPDF to rasterise + pytesseract to read.

The reader also renders the first page to a PNG so the UI can show a preview.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Tuple

import fitz  # PyMuPDF
import pdfplumber

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)

# A page with fewer characters than this is treated as "probably scanned".
_MIN_CHARS_PER_PAGE = 20


class PDFReader:
    """Extracts text (and a preview image) from a purchase-order PDF."""

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Return the best-effort plain-text of the entire document."""
        text = self._extract_with_pdfplumber(pdf_bytes)

        # If pdfplumber found little/nothing, try PyMuPDF.
        if len(text.strip()) < _MIN_CHARS_PER_PAGE:
            log.info("pdfplumber returned little text; trying PyMuPDF.")
            text = self._extract_with_pymupdf(pdf_bytes)

        # Still nothing? Likely a scanned image -> OCR (if enabled).
        if len(text.strip()) < _MIN_CHARS_PER_PAGE and settings.enable_ocr:
            log.info("Document looks scanned; falling back to OCR.")
            text = self._extract_with_ocr(pdf_bytes)

        log.info("Extracted %d characters from PDF.", len(text))
        return text

    # ------------------------------------------------------------------ #
    #  Individual strategies                                             #
    # ------------------------------------------------------------------ #
    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> str:
        parts: list[str] = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001 - demo robustness
            log.warning("pdfplumber failed: %s", exc)
        return "\n".join(parts)

    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> str:
        parts: list[str] = []
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    parts.append(page.get_text("text"))
        except Exception as exc:  # noqa: BLE001
            log.warning("PyMuPDF failed: %s", exc)
        return "\n".join(parts)

    def _extract_with_ocr(self, pdf_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
        except Exception as exc:  # noqa: BLE001
            log.warning("OCR libraries unavailable: %s", exc)
            return ""

        parts: list[str] = []
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    parts.append(pytesseract.image_to_string(img))
        except Exception as exc:  # noqa: BLE001
            log.warning("OCR failed (is tesseract installed?): %s", exc)
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    #  Preview                                                           #
    # ------------------------------------------------------------------ #
    def first_page_png(self, pdf_bytes: bytes, dpi: int = 130) -> bytes:
        """Render page 1 to PNG bytes for the Streamlit preview panel."""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            page = doc[0]
            pix = page.get_pixmap(dpi=dpi)
            return pix.tobytes("png")

    def read_file(self, path: str | Path) -> Tuple[str, bytes]:
        """Convenience: read a PDF from disk -> (text, raw_bytes)."""
        raw = Path(path).read_bytes()
        return self.extract_text(raw), raw
