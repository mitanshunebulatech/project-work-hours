"""create leave_types table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-07 00:00:07

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_attachment_after_days", sa.Integer(), nullable=True),
        sa.Column("allows_half_day", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_leave_types_code"),
    )
    op.create_index("idx_leave_types_code", "leave_types", ["code"])
    op.create_index("idx_leave_types_is_active", "leave_types", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_leave_types_is_active", table_name="leave_types")
    op.drop_index("idx_leave_types_code", table_name="leave_types")
    op.drop_table("leave_types")
