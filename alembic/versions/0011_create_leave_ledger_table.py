"""create leave_ledger table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-07 00:00:11

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_types.id"), nullable=False),
        sa.Column(
            "leave_request_id", sa.Integer(), sa.ForeignKey("leave_requests.id"), nullable=True
        ),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("amount_days", sa.Numeric(6, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_leave_ledger_employee_type_date",
        "leave_ledger",
        ["employee_id", "leave_type_id", "created_at"],
    )
    op.create_index("idx_leave_ledger_request", "leave_ledger", ["leave_request_id"])


def downgrade() -> None:
    op.drop_index("idx_leave_ledger_request", table_name="leave_ledger")
    op.drop_index("idx_leave_ledger_employee_type_date", table_name="leave_ledger")
    op.drop_table("leave_ledger")
