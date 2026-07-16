"""create work_schedule_policy table and seed default half-day hours

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-15 00:00:24

Item 4 (PM requirement): half-day leave must be a configurable policy, not
hardcoded values. This creates a deliberate single-row table (id always 1)
and seeds it with the company's stated office hours: first half 11:00-16:00,
second half 16:00-20:00. Also extends the permission catalogue with
"work_schedule:manage" (same additive pattern as 0023) so an admin — via
the functional-roles system, not just the legacy role string — can update
these hours through the API.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_ROLE_ID = 1  # seeded in 0018; system role, never deleted
NEW_PERMISSION_ID = 22  # continuing on from 0023's ids 13-21
NEW_PERMISSION_CODE = "work_schedule:manage"


def upgrade() -> None:
    op.create_table(
        "work_schedule_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_half_start", sa.Time(), nullable=False),
        sa.Column("first_half_end", sa.Time(), nullable=False),
        sa.Column("second_half_start", sa.Time(), nullable=False),
        sa.Column("second_half_end", sa.Time(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.execute(
        sa.text(
            "INSERT INTO work_schedule_policy "
            "(id, first_half_start, first_half_end, second_half_start, second_half_end) "
            "VALUES (1, '11:00:00', '16:00:00', '16:00:00', '20:00:00')"
        )
    )

    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": NEW_PERMISSION_ID,
                "code": NEW_PERMISSION_CODE,
                "description": "Configure the company's half-day office-hour boundaries",
            }
        ],
    )
    op.execute("SELECT setval('permissions_id_seq', (SELECT MAX(id) FROM permissions))")

    role_permissions_table = sa.table(
        "role_permissions", sa.column("role_id", sa.Integer), sa.column("permission_id", sa.Integer)
    )
    op.bulk_insert(
        role_permissions_table, [{"role_id": ADMIN_ROLE_ID, "permission_id": NEW_PERMISSION_ID}]
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_id = :pid").bindparams(
            sa.bindparam("pid")
        ),
        {"pid": NEW_PERMISSION_ID},
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE id = :pid").bindparams(sa.bindparam("pid")),
        {"pid": NEW_PERMISSION_ID},
    )
    op.drop_table("work_schedule_policy")
