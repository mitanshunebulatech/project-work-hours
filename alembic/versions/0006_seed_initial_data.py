"""seed initial data

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-29 00:00:06

Note: soft-delete columns (deleted_at) were included directly in the 0001/0002
table-creation migrations rather than as a separate bolt-on ALTER TABLE step,
since the schema was designed with soft-delete from the start. This migration
covers what the TRD's migration plan lists as "seed initial data".
"""

from datetime import date, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from passlib.context import CryptContext

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)
# Deliberately NOT computed at module import time: hashing here would run bcrypt
# (slow, and backend-sensitive) just from *importing* this file for inspection,
# e.g. when Alembic lists revisions. It is computed once, lazily, inside upgrade().

users_table = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("username", sa.String),
    sa.column("email", sa.String),
    sa.column("password_hash", sa.String),
    sa.column("role", sa.String),
    sa.column("is_active", sa.Boolean),
)

projects_table = sa.table(
    "projects",
    sa.column("id", sa.Integer),
    sa.column("project_name", sa.String),
    sa.column("description", sa.Text),
    sa.column("is_active", sa.Boolean),
)

entries_table = sa.table(
    "work_entries",
    sa.column("employee_id", sa.Integer),
    sa.column("project_id", sa.Integer),
    sa.column("entry_date", sa.Date),
    sa.column("hours_worked", sa.Numeric),
    sa.column("remarks", sa.Text),
    sa.column("status", sa.String),
)


def upgrade() -> None:
    seed_password_hash = _pwd_context.hash("ChangeMe123")

    op.bulk_insert(
        users_table,
        [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@workhours.local",
                "password_hash": seed_password_hash,
                "role": "admin",
                "is_active": True,
            },
            {
                "id": 2,
                "username": "mitanshu",
                "email": "mitanshu@workhours.local",
                "password_hash": seed_password_hash,
                "role": "employee",
                "is_active": True,
            },
            {
                "id": 3,
                "username": "priya",
                "email": "priya@workhours.local",
                "password_hash": seed_password_hash,
                "role": "employee",
                "is_active": True,
            },
            {
                "id": 4,
                "username": "rahul",
                "email": "rahul@workhours.local",
                "password_hash": seed_password_hash,
                "role": "employee",
                "is_active": True,
            },
            {
                "id": 5,
                "username": "sneha",
                "email": "sneha@workhours.local",
                "password_hash": seed_password_hash,
                "role": "employee",
                "is_active": True,
            },
            {
                "id": 6,
                "username": "arjun",
                "email": "arjun@workhours.local",
                "password_hash": seed_password_hash,
                "role": "employee",
                "is_active": True,
            },
        ],
    )

    op.bulk_insert(
        projects_table,
        [
            {
                "id": 1,
                "project_name": "Website Redesign",
                "description": "Marketing site revamp",
                "is_active": True,
            },
            {
                "id": 2,
                "project_name": "Mobile App",
                "description": "Customer-facing Flutter app",
                "is_active": True,
            },
            {
                "id": 3,
                "project_name": "Data Migration",
                "description": "Legacy DB to PostgreSQL",
                "is_active": True,
            },
            {
                "id": 4,
                "project_name": "API Integration",
                "description": "Third-party payment gateway",
                "is_active": True,
            },
            {
                "id": 5,
                "project_name": "Security Audit",
                "description": "Annual OWASP review",
                "is_active": True,
            },
        ],
    )

    today = date.today()
    seed_entries = []
    employee_ids = [2, 3, 4, 5, 6]
    project_ids = [1, 2, 3, 4, 5]
    for i in range(10):
        seed_entries.append(
            {
                "employee_id": employee_ids[i % len(employee_ids)],
                "project_id": project_ids[i % len(project_ids)],
                "entry_date": today - timedelta(days=i % 7),
                "hours_worked": 6.0 + (i % 4),
                "remarks": f"Seed entry #{i + 1}",
                "status": "pending" if i % 3 != 0 else "approved",
            }
        )
    op.bulk_insert(entries_table, seed_entries)

    # Keep the SERIAL sequences in sync after explicit id inserts
    op.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
    op.execute("SELECT setval('projects_id_seq', (SELECT MAX(id) FROM projects))")


def downgrade() -> None:
    op.execute("DELETE FROM work_entries")
    op.execute("DELETE FROM projects")
    op.execute("DELETE FROM users")
