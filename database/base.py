"""
Base database configuration.

SQLAlchemy 2.0 style declarative base.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

