"""create holidays table

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-08 12:00:16

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("date", name="uq_holidays_date"),
    )
    op.create_index("idx_holidays_date", "holidays", ["date"])
    op.create_index("idx_holidays_is_active", "holidays", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_holidays_is_active", table_name="holidays")
    op.drop_index("idx_holidays_date", table_name="holidays")
    op.drop_table("holidays")
