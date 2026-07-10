"""create permissions, roles, role_permissions tables and seed system roles

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-10 00:00:18

Seeds a starter permission catalogue and two system roles: "admin" (all
permissions) and "employee" (self-service permissions only). These are
additive rows only — they don't touch users.role_id, which is introduced
and backfilled in 0020.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

permissions_table = sa.table(
    "permissions",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("description", sa.String),
)

roles_table = sa.table(
    "roles",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("is_system_role", sa.Boolean),
)

role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", sa.Integer),
    sa.column("permission_id", sa.Integer),
)

# id : (code, description)
PERMISSIONS = [
    (1, "leave_requests:create", "Submit a leave request"),
    (2, "leave_requests:view_own", "View own leave requests"),
    (3, "leave_requests:view_all", "View all employees' leave requests"),
    (4, "leave_requests:approve", "Approve or reject leave requests"),
    (5, "work_entries:create", "Submit work hour entries"),
    (6, "work_entries:view_own", "View own work entries"),
    (7, "work_entries:view_all", "View all employees' work entries"),
    (8, "employees:view", "View employee profiles"),
    (9, "employees:manage", "Create/edit employee profiles"),
    (10, "departments:manage", "Create/edit departments"),
    (11, "roles:manage", "Create/edit roles and permissions"),
    (12, "audit_logs:view", "View audit log entries"),
]

# Employee gets only self-service permission codes.
EMPLOYEE_PERMISSION_CODES = {
    "leave_requests:create",
    "leave_requests:view_own",
    "work_entries:create",
    "work_entries:view_own",
}


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True),
    )

    op.bulk_insert(
        permissions_table,
        [{"id": pid, "code": code, "description": desc} for pid, code, desc in PERMISSIONS],
    )
    op.execute("SELECT setval('permissions_id_seq', (SELECT MAX(id) FROM permissions))")

    op.bulk_insert(
        roles_table,
        [
            {"id": 1, "name": "admin", "description": "Full system access", "is_system_role": True},
            {"id": 2, "name": "employee", "description": "Self-service access only", "is_system_role": True},
        ],
    )
    op.execute("SELECT setval('roles_id_seq', (SELECT MAX(id) FROM roles))")

    # admin (role_id=1): every permission
    admin_links = [{"role_id": 1, "permission_id": pid} for pid, _, _ in PERMISSIONS]
    # employee (role_id=2): self-service subset only
    employee_links = [
        {"role_id": 2, "permission_id": pid}
        for pid, code, _ in PERMISSIONS
        if code in EMPLOYEE_PERMISSION_CODES
    ]
    op.bulk_insert(role_permissions_table, admin_links + employee_links)


def downgrade() -> None:
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
