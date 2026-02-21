"""add hospital metadata columns and forecast_run signal_date_used

Revision ID: a7b8c9d0e1f2
Revises: 6f2d3b1a9c4e
Create Date: 2026-02-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "6f2d3b1a9c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hospital metadata columns for ML features
    op.add_column(
        "hospitals",
        sa.Column("population", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "hospitals",
        sa.Column(
            "population_density", sa.Float(), nullable=True, server_default="0"
        ),
    )
    op.add_column(
        "hospitals",
        sa.Column("elderly_ratio", sa.Float(), nullable=True, server_default="0"),
    )
    op.add_column(
        "hospitals",
        sa.Column("icu_capacity", sa.Integer(), nullable=True, server_default="0"),
    )

    # ForecastRun: track which signal date was used
    op.add_column(
        "forecast_runs",
        sa.Column("signal_date_used", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("forecast_runs", "signal_date_used")
    op.drop_column("hospitals", "icu_capacity")
    op.drop_column("hospitals", "elderly_ratio")
    op.drop_column("hospitals", "population_density")
    op.drop_column("hospitals", "population")

