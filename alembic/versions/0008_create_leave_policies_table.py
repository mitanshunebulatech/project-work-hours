"""create leave_policies table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-07 00:00:08

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_types.id"), nullable=False),
        sa.Column("annual_quota_days", sa.Numeric(5, 2), nullable=False),
        sa.Column("max_consecutive_days", sa.Integer(), nullable=False),
        sa.Column("min_notice_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("carry_forward_cap_days", sa.Numeric(5, 2), nullable=True),
        sa.Column("carry_forward_expiry_month", sa.Integer(), nullable=True),
        sa.Column("accrual_frequency", sa.String(20), nullable=False, server_default="upfront"),
        sa.Column("effective_year", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("leave_type_id", "effective_year", name="uq_policy_type_year"),
        sa.CheckConstraint(
            "carry_forward_cap_days IS NULL OR carry_forward_cap_days <= annual_quota_days",
            name="chk_carry_forward_not_exceed_quota",
        ),
    )
    op.create_index("idx_leave_policies_type_year", "leave_policies", ["leave_type_id", "effective_year"])
    op.create_index("idx_leave_policies_year", "leave_policies", ["effective_year"])


def downgrade() -> None:
    op.drop_index("idx_leave_policies_year", table_name="leave_policies")
    op.drop_index("idx_leave_policies_type_year", table_name="leave_policies")
    op.drop_table("leave_policies")
