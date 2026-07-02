"""create refresh_tokens table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29 00:00:05

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_rtoken_user", "refresh_tokens", ["user_id"])
    op.create_index("idx_rtoken_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index("idx_rtoken_hash", table_name="refresh_tokens")
    op.drop_index("idx_rtoken_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
