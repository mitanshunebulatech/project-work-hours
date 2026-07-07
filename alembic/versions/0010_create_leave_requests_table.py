"""create leave_requests table

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-07 00:00:10

Note: this table is created before leave_ledger (0011), even though the ledger
was designed first, because leave_ledger.leave_request_id is a nullable FK
into this table — the referenced table must exist first.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_types.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_half_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("working_days_count", sa.Numeric(5, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attachment_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("end_date >= start_date", name="chk_leave_dates_valid"),
    )
    op.create_index("idx_leave_requests_employee_status", "leave_requests", ["employee_id", "status"])
    op.create_index("idx_leave_requests_status_created", "leave_requests", ["status", "created_at"])
    op.create_index("idx_leave_requests_dates", "leave_requests", ["start_date", "end_date"])


def downgrade() -> None:
    op.drop_index("idx_leave_requests_dates", table_name="leave_requests")
    op.drop_index("idx_leave_requests_status_created", table_name="leave_requests")
    op.drop_index("idx_leave_requests_employee_status", table_name="leave_requests")
    op.drop_table("leave_requests")
