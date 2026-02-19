"""
Database utilities for the FastAPI app.

This module re-exports the existing SQLAlchemy session and Base
from the top-level `database` package to avoid duplication.
"""

from database.session import get_db, SessionLocal  # noqa: F401
from database.base import Base  # noqa: F401



