"""add role_id fk and must_change_password to users

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-10 00:00:20

role_id is added nullable, then backfilled from the legacy `role` string
column, then left nullable — the legacy column stays as the fallback per
the F4 decision (full router migration to role_id-based checks is a later
sprint). Existing rows are never dropped or altered beyond this backfill.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=True))
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_users_role_id", "users", ["role_id"])

    # Backfill role_id from the legacy role string. System role ids seeded in
    # 0018: 1 = admin, 2 = employee. Any other legacy value is left NULL
    # rather than guessed at.
    op.execute("UPDATE users SET role_id = 1 WHERE role = 'admin'")
    op.execute("UPDATE users SET role_id = 2 WHERE role = 'employee'")


def downgrade() -> None:
    op.drop_index("idx_users_role_id", table_name="users")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "role_id")
