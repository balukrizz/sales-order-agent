"""
Vercel Python entrypoint.

Vercel's @vercel/python runtime imports this module and serves the ASGI `app`.
We add the backend root to sys.path so the agent packages import cleanly.

NOTE: Vercel serverless functions are short-lived (Hobby = 10s) and don't stream
well, so the live SSE timeline (/api/process/stream) and long Mistral calls are
better served from a always-on host (see render.yaml). This entry is provided
for teams that want everything under Vercel; use the non-streaming /api/process
route there and set DB_PATH=/tmp/sales.db (the only writable path).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401  (re-exported for Vercel)
