"""create notifications table

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-07 00:00:12

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_notifications_recipient_read_created",
        "notifications",
        ["recipient_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_recipient_read_created", table_name="notifications")
    op.drop_table("notifications")
