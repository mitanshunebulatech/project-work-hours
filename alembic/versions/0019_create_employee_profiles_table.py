"""create employee_profiles table

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-10 00:00:19

pan_number is stored ciphertext-only (app.core.encryption.EncryptedString /
Fernet at the application layer) — the column here is a plain VARCHAR since
encryption happens before the value ever reaches the DB driver.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("date_of_joining", sa.Date(), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("pan_number", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_employee_profiles_user_id"),
    )
    op.create_index("idx_employee_profiles_department_id", "employee_profiles", ["department_id"])


def downgrade() -> None:
    op.drop_index("idx_employee_profiles_department_id", table_name="employee_profiles")
    op.drop_table("employee_profiles")
