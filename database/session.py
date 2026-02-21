"""
Database session management.

Provides SQLAlchemy session factory and FastAPI dependency.
Compatible with both local development and Vercel serverless.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
from dotenv import load_dotenv

from database.base import Base

# Load .env values and override inherited env vars so local config is deterministic.
load_dotenv(override=True)

# Database URL from environment variable (required in production)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    import warnings
    warnings.warn(
        "DATABASE_URL is not set — falling back to localhost default. "
        "This WILL fail in production / Vercel.",
        stacklevel=2,
    )
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/hospital_forecast"

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------
# Vercel (Lambda) spins up short-lived processes. A connection pool with
# many idle connections is wasteful and can hit Neon limits.  Use NullPool
# in serverless so each request opens / closes its own connection.
#
# For local / long-running servers (uvicorn), a small pool is fine.
# We detect the Vercel runtime via the AWS_LAMBDA_FUNCTION_NAME env var
# that Vercel always sets inside its Python functions.
_is_serverless = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("VERCEL"))

if _is_serverless:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    DEV / SEED ONLY — create tables via SQLAlchemy metadata.

    In production the schema is managed exclusively by Alembic.
    The FastAPI app does NOT call this function; it exists only for:
      - scripts/seed_db_from_csv.py  (one-time bootstrap)
      - Local development convenience
    """
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all database tables (use with caution — dev only!)."""
    Base.metadata.drop_all(bind=engine)
