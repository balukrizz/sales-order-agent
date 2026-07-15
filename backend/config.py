"""
config.py
---------
Central configuration loader. Reads settings from environment variables
(populated from a local .env file via python-dotenv) so that every module
shares one source of truth. Nothing here is hard-coded to a single provider,
which keeps the demo portable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env once, from the project root, regardless of the working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of all runtime settings."""

    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "").strip()
    mistral_model: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest").strip()
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0") or 0)
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048") or 2048)

    # OCR
    enable_ocr: bool = _get_bool("ENABLE_OCR", True)

    # Paths (resolved to absolute against the project root)
    db_path: str = str(PROJECT_ROOT / os.getenv("DB_PATH", "database/sales.db"))
    customer_master: str = str(PROJECT_ROOT / os.getenv("CUSTOMER_MASTER", "data/customer_master.csv"))
    material_master: str = str(PROJECT_ROOT / os.getenv("MATERIAL_MASTER", "data/material_master.csv"))

    @property
    def use_mock_llm(self) -> bool:
        """Fall back to the offline mock if explicitly requested OR if the
        provider is mistral but no API key was supplied. This guarantees the
        demo never hard-crashes in front of a client."""
        if self.llm_provider == "mock":
            return True
        if self.llm_provider == "mistral" and not self.mistral_api_key:
            return True
        return False


# A single shared instance used across the app.
settings = Settings()
