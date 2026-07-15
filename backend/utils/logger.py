"""
utils/logger.py
---------------
Rich-powered logger shared by every agent. Produces colourful, readable
console output that doubles as a lightweight audit trail during the demo.
"""
from __future__ import annotations

import logging

from rich.logging import RichHandler

_CONFIGURED = False


def get_logger(name: str = "sales_order_agent") -> logging.Logger:
    """Return a configured logger. Configuration runs only once per process."""
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
        )
        _CONFIGURED = True
    return logging.getLogger(name)
