"""
database/init_db.py
-------------------
Standalone initialiser. Run once to create a fresh SQLite ERP-simulation DB:

    python -m database.init_db

The app also self-initialises on start, so this is mainly for a clean reset.
"""
from __future__ import annotations

import os
import sys

# Allow running as a script from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings          # noqa: E402
from database.db import Database     # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("init_db")


def main(reset: bool = False) -> None:
    if reset and os.path.exists(settings.db_path):
        os.remove(settings.db_path)
        log.info("Removed existing DB at %s", settings.db_path)
    Database(settings.db_path)  # __init__ creates the schema
    log.info("Database initialised successfully.")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
