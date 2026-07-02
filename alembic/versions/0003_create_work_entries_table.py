"""create work_entries table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29 00:00:03

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("hours_worked", sa.Numeric(5, 2), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("employee_id", "project_id", "entry_date", name="uq_employee_project_date"),
        sa.CheckConstraint("hours_worked > 0 AND hours_worked <= 24", name="chk_hours_range"),
    )
    op.create_index("idx_entries_employee_date", "work_entries", ["employee_id", "entry_date"])
    op.create_index("idx_entries_project", "work_entries", ["project_id"])
    op.create_index("idx_entries_status", "work_entries", ["status"])
    op.create_index("idx_entries_date", "work_entries", ["entry_date"])


def downgrade() -> None:
    op.drop_index("idx_entries_date", table_name="work_entries")
    op.drop_index("idx_entries_status", table_name="work_entries")
    op.drop_index("idx_entries_project", table_name="work_entries")
    op.drop_index("idx_entries_employee_date", table_name="work_entries")
    op.drop_table("work_entries")
