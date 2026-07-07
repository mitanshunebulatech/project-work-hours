"""create leave_balances table

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-07 00:00:09

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_balances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_types.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("total_credited_days", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("total_debited_days", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("remaining_days", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_balance_employee_type_year"),
    )
    op.create_index("idx_leave_balances_employee_year", "leave_balances", ["employee_id", "year"])
    op.create_index("idx_leave_balances_type", "leave_balances", ["leave_type_id"])


def downgrade() -> None:
    op.drop_index("idx_leave_balances_type", table_name="leave_balances")
    op.drop_index("idx_leave_balances_employee_year", table_name="leave_balances")
    op.drop_table("leave_balances")
