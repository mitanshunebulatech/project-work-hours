"""onboarding fields expansion and identity_documents table

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-16 00:00:25

Splits employee_profiles.full_name into first_name/last_name (full_name
becomes an application-level computed property, not a column — see
app/models/employee_profile.py), adds the remaining PM-item-#6 onboarding
fields, and introduces identity_documents as a proper one-to-many table so
Aadhaar/Passport/Other document types can be added later without another
schema change.

document_number is encrypted at rest the same way pan_number already is
(app.core.encryption.EncryptedString / Fernet at the application layer) —
the column here is a plain VARCHAR since encryption happens before the
value reaches the DB driver. The document *file* itself is stored
encrypted on disk (see app/utils/secure_file_storage.py, added in a later
step); this table only ever holds a path + metadata, never file bytes.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Add new columns as nullable first — existing rows need backfilling
    # before we can enforce NOT NULL / UNIQUE on first_name and employee_code. ---
    op.add_column("employee_profiles", sa.Column("first_name", sa.String(75), nullable=True))
    op.add_column("employee_profiles", sa.Column("last_name", sa.String(75), nullable=True))
    op.add_column("employee_profiles", sa.Column("employee_code", sa.String(20), nullable=True))
    op.add_column(
        "employee_profiles", sa.Column("emergency_contact_phone", sa.String(20), nullable=True)
    )
    op.add_column("employee_profiles", sa.Column("present_address", sa.String(500), nullable=True))
    op.add_column(
        "employee_profiles", sa.Column("years_of_experience", sa.Numeric(4, 1), nullable=True)
    )
    op.add_column(
        "employee_profiles", sa.Column("profile_picture_path", sa.String(255), nullable=True)
    )

    # --- 2. Backfill first_name / last_name from the existing full_name column. ---
    # split_part gives everything before the first space as first_name; the
    # remainder (if any) becomes last_name. Single-word names get last_name = NULL.
    op.execute(
        """
        UPDATE employee_profiles
        SET first_name = split_part(full_name, ' ', 1),
            last_name = NULLIF(
                trim(substring(full_name from position(' ' in full_name) + 1)),
                ''
            )
        WHERE position(' ' in full_name) > 0
        """
    )
    op.execute(
        """
        UPDATE employee_profiles
        SET first_name = full_name
        WHERE position(' ' in full_name) = 0
        """
    )

    # --- 3. Backfill employee_code sequentially (EMP-0001, EMP-0002, ...),
    # ordered by id so existing employees keep a stable, predictable code. ---
    op.execute(
        """
        UPDATE employee_profiles
        SET employee_code = 'EMP-' || LPAD(sub.rn::text, 4, '0')
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
            FROM employee_profiles
        ) AS sub
        WHERE employee_profiles.id = sub.id
        """
    )

    # --- 4. Now that every row is backfilled, enforce NOT NULL / UNIQUE and
    # drop full_name (it becomes a computed property in the model). ---
    op.alter_column("employee_profiles", "first_name", nullable=False)
    op.alter_column("employee_profiles", "employee_code", nullable=False)
    op.create_unique_constraint(
        "uq_employee_profiles_employee_code", "employee_profiles", ["employee_code"]
    )
    op.drop_column("employee_profiles", "full_name")

    # --- 5. identity_documents: one-to-many, extensible document_type (plain
    # string, not an enum) so Aadhaar/Passport/Other can be added later without
    # another migration. ---
    op.create_table(
        "identity_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_profile_id",
            sa.Integer(),
            sa.ForeignKey("employee_profiles.id"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("document_number", sa.String(255), nullable=True),
        sa.Column("file_path", sa.String(255), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_identity_documents_employee_profile_id",
        "identity_documents",
        ["employee_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_identity_documents_employee_profile_id", table_name="identity_documents")
    op.drop_table("identity_documents")

    op.add_column("employee_profiles", sa.Column("full_name", sa.String(150), nullable=True))
    op.execute(
        """
        UPDATE employee_profiles
        SET full_name = trim(coalesce(first_name, '') || ' ' || coalesce(last_name, ''))
        """
    )
    op.alter_column("employee_profiles", "full_name", nullable=False)

    op.drop_constraint(
        "uq_employee_profiles_employee_code", "employee_profiles", type_="unique"
    )
    op.drop_column("employee_profiles", "profile_picture_path")
    op.drop_column("employee_profiles", "years_of_experience")
    op.drop_column("employee_profiles", "present_address")
    op.drop_column("employee_profiles", "emergency_contact_phone")
    op.drop_column("employee_profiles", "employee_code")
    op.drop_column("employee_profiles", "last_name")
    op.drop_column("employee_profiles", "first_name")
