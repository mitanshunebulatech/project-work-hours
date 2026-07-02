"""create audit_logs table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-29 00:00:04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("before_data", postgresql.JSONB(), nullable=True),
        sa.Column("after_data", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_audit_actor", "audit_logs", ["actor_id"])
    op.create_index("idx_audit_table_record", "audit_logs", ["table_name", "record_id"])
    op.create_index("idx_audit_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_table_record", table_name="audit_logs")
    op.drop_index("idx_audit_actor", table_name="audit_logs")
    op.drop_table("audit_logs")
