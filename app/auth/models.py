"""
Auth-related model re-exports.

We reuse the existing SQLAlchemy User model from the shared database layer
to avoid duplicating ORM mappings.
"""

from database.models import User  # noqa: F401



