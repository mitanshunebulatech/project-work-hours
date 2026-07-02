"""create projects table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29 00:00:02

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_projects_name_active",
        "projects",
        ["project_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("idx_projects_name", "projects", ["project_name"])
    op.create_index("idx_projects_is_active", "projects", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_projects_is_active", table_name="projects")
    op.drop_index("idx_projects_name", table_name="projects")
    op.drop_index("uq_projects_name_active", table_name="projects")
    op.drop_table("projects")
