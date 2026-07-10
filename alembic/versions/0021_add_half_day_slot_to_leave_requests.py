"""add half_day_slot to leave_requests

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-10 00:00:21

CHECK constraint is written as an explicit is_half_day/half_day_slot pair
guard rather than a bare "half_day_slot IN (...)". A bare IN check evaluates
to NULL (not FALSE) when half_day_slot is NULL, and Postgres treats a NULL
CHECK result as passing — so a naive constraint would silently allow
is_half_day=true rows with no slot set. This mirrors app/models/leave_request.py.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leave_requests", sa.Column("half_day_slot", sa.String(20), nullable=True))
    op.create_check_constraint(
        "chk_half_day_slot_consistency",
        "leave_requests",
        "(is_half_day = false AND half_day_slot IS NULL) OR "
        "(is_half_day = true AND half_day_slot IS NOT NULL AND half_day_slot IN ('first_half', 'second_half'))",
    )


def downgrade() -> None:
    op.drop_constraint("chk_half_day_slot_consistency", "leave_requests", type_="check")
    op.drop_column("leave_requests", "half_day_slot")
