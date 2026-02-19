"""
Application package initializer.

Exposes the FastAPI application instance as ``app`` so that
``uvicorn app:app`` works both locally and in production.
"""

from .main import app  # noqa: F401

__all__ = ["app"]

