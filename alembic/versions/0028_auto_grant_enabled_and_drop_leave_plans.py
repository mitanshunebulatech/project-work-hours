"""add auto_grant_enabled to leave_policies, hard-drop leave_plans

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-21 00:00:28

HRMS V3 PM requirements (post-demo revision):
- Leave Planning is removed entirely — the PM's own words: "remove the
  leave planning module completely." leave_plans was always informational
  only, zero coupling to leave_requests/leave_ledger (see migration 0027's
  own note), so this is a clean, dependency-free hard drop — no data
  migration path needed, nothing else references rows in this table.
- auto_grant_enabled on leave_policies: the new PM direction moves most
  leave types to an admin-input balance model (set during onboarding,
  editable in the new Leave Balance tab) rather than the existing
  automatic annual-grant job (see app/services/annual_grant_service.py).
  Rather than deleting policy rows or special-casing leave types by code
  (fragile, and loses the policy's other config like
  max_consecutive_days/carry_forward), this adds one explicit flag so
  AnnualGrantService.run() can skip a policy without losing it.
- Defaults to True (not False): existing policies keep automatic granting
  working exactly as today the moment this migration lands. Turning it
  off per-policy is a deliberate admin action in a later stage, once the
  admin-input Leave Balance UI actually exists — flipping the default to
  False here would silently stop every current employee's annual leave
  credit before any replacement mechanism is in place.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- leave_policies: auto_grant_enabled ---
    op.add_column(
        "leave_policies",
        sa.Column("auto_grant_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # --- leave_plans: hard drop (Leave Planning module removed entirely) ---
    op.drop_index("idx_leave_plans_employee_year", table_name="leave_plans")
    op.drop_table("leave_plans")


def downgrade() -> None:
    # Recreates the table structure (matching migration 0027 exactly) —
    # this does NOT restore any data that existed before the hard drop,
    # which is expected: a downgrade reverses schema, not lost rows.
    op.create_table(
        "leave_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_types.id"), nullable=False),
        sa.Column("planned_start_date", sa.Date(), nullable=False),
        sa.Column("planned_end_date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "planned_end_date >= planned_start_date", name="chk_leave_plans_dates_valid"
        ),
    )
    op.create_index("idx_leave_plans_employee_year", "leave_plans", ["employee_id", "year"])

    op.drop_column("leave_policies", "auto_grant_enabled")
