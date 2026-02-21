"""
Vercel Serverless Entry Point
=============================
Wraps the FastAPI application with the Mangum adapter so it can be
served as an AWS Lambda-compatible handler that Vercel's Python runtime
invokes on every request.

All routes registered on ``app.main.app`` are exposed unchanged:
    /health, /hospitals, /forecast/latest, /predict, /auth/*, etc.

No background tasks, no file-system writes, no in-process schedulers.
"""

from mangum import Mangum
from app.main import app

# Mangum translates API Gateway / Lambda events ↔ ASGI.
# Vercel's Python runtime calls ``handler(event, context)``.
handler = Mangum(app, lifespan="off")

