"""add start_time/end_time to work_entries, relax per-project-per-day uniqueness

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-10 00:00:22

Sprint 3: employees can now log multiple time-blocks against the same
project on the same day (e.g. 9-12 and 2-5), so the old
uq_employee_project_date constraint (BR-01: one entry per employee+project+
day) is dropped. In its place, EntryService enforces at the application
layer that an employee's time-blocks don't overlap each other on a given
day, across any project (you can't work two things at once).

start_time/end_time are nullable and NOT backfilled for existing rows:
those rows only ever recorded hours_worked, so fabricating start/end times
for them would introduce data that was never actually captured. The app
treats NULL start_time/end_time as "no time-of-day recorded" for legacy
entries, not an error state.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("work_entries", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("work_entries", sa.Column("end_time", sa.Time(), nullable=True))
    op.drop_constraint("uq_employee_project_date", "work_entries", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_employee_project_date",
        "work_entries",
        ["employee_id", "project_id", "entry_date"],
    )
    op.drop_column("work_entries", "end_time")
    op.drop_column("work_entries", "start_time")
