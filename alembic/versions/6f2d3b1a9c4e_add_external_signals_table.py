"""add external signals table

Revision ID: 6f2d3b1a9c4e
Revises: ed9905fc483a
Create Date: 2026-02-20 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2d3b1a9c4e"
down_revision: Union[str, None] = "ed9905fc483a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_signals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hospital_id", sa.UUID(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("aqi", sa.Float(), nullable=False),
        sa.Column("outbreak_index", sa.Float(), nullable=False),
        sa.Column("mobility_index", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hospital_id", "date", name="uq_external_signal_hospital_date"),
    )
    op.create_index(
        "idx_external_signal_hospital_date",
        "external_signals",
        ["hospital_id", "date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_external_signals_hospital_id"),
        "external_signals",
        ["hospital_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_external_signals_hospital_id"), table_name="external_signals")
    op.drop_index("idx_external_signal_hospital_date", table_name="external_signals")
    op.drop_table("external_signals")

