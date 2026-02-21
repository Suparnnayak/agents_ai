"""
Vercel Serverless Entry Point
=============================
Vercel's @vercel/python runtime natively understands ASGI applications.
We simply re-export the FastAPI ``app`` object — Vercel handles the
Lambda ↔ ASGI translation internally.

No Mangum adapter is needed (Mangum is for raw AWS Lambda / API Gateway).

All routes registered on ``app.main.app`` are exposed unchanged:
    /health, /hospitals, /forecast/latest, /predict, /auth/*, etc.

No background tasks, no file-system writes, no in-process schedulers.
"""

from app.main import app  # noqa: F401 — Vercel detects this ASGI app
