"""add holiday year/is_published, create leave_plans table

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-19 00:00:27

PM requirements #1-3, #6 (Year-wise Leave Calendar, Holiday Management,
Publish Workflow, Leave Planning).

Design decisions locked in during requirements discussion:
- holidays.year: explicit indexed integer column, not derived from date on
  every query — matches how real HRMS platforms (Zoho People, Keka,
  Darwinbox) manage holiday calendars as year-scoped entities (bulk-publish
  a whole year, "clone last year's calendar", etc.). Backfilled from the
  existing date column for current rows.
- holidays.is_published: existing rows are grandfathered to True (they were
  already effectively visible to everyone under the old model — defaulting
  them to False would cause every currently-visible holiday to vanish from
  employee-facing views the moment this ships). The column's own default is
  then flipped to False AFTER the backfill, so only the backfill grandfathers
  old data — every new holiday created going forward starts as an
  unpublished draft, matching the Publish Workflow requirement. This is
  deliberately NOT server_default=true() at the column-definition level
  (that would silently un-do the "new holidays start as drafts" decision
  for any insert path that forgets to set it explicitly).
- leave_plans: brand new table, zero coupling to leave_requests/leave_ledger
  — informational only (no approval step, no balance impact, no
  auto-conversion to a real request). Date range (start+end), leave_type_id
  required (employee must pick a type even when just planning). `year` is
  stored explicitly (not derived) for the same reason as holidays.year —
  "give me my 2027 plan" is a common query shape.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- holidays: year + is_published ---
    op.add_column("holidays", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column(
        "holidays", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    conn = op.get_bind()
    # Backfill year from the existing date column.
    conn.execute(sa.text("UPDATE holidays SET year = EXTRACT(YEAR FROM date)::integer WHERE year IS NULL"))
    # Grandfather existing rows as published — they were already effectively
    # visible under the old (no-publish-concept) model. New rows inserted
    # after this migration keep the column's real default (False, set above).
    conn.execute(sa.text("UPDATE holidays SET is_published = true"))

    op.alter_column("holidays", "year", nullable=False)
    op.create_index("idx_holidays_year", "holidays", ["year"])
    op.create_index("idx_holidays_is_published", "holidays", ["is_published"])

    # --- leave_plans: brand new, informational-only leave planning ---
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


def downgrade() -> None:
    op.drop_index("idx_leave_plans_employee_year", table_name="leave_plans")
    op.drop_table("leave_plans")

    op.drop_index("idx_holidays_is_published", table_name="holidays")
    op.drop_index("idx_holidays_year", table_name="holidays")
    op.drop_column("holidays", "is_published")
    op.drop_column("holidays", "year")
