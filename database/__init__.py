"""
Database package for Hospital Forecast API.

Provides SQLAlchemy models, session management, and CRUD operations.
"""

from database.session import get_db, SessionLocal
from database.base import Base

__all__ = ["get_db", "SessionLocal", "Base"]

