"""extend permission catalogue for remaining admin-gated routers

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-15 00:00:23

Sprint context: 0018 seeded an initial permission catalogue covering leave
requests, work entries (view-only), employees, departments, roles, and
audit logs. Everything else (entries approve/delete, users, projects,
holidays, leave policy config, leave ledger, leave balances, reports) was
left on the legacy require_admin/require_role("admin") check — which reads
users.role (a plain string), not users.role_id (the functional-roles FK).
That means an admin-equivalent custom role created via the Role module
(Sprint 4) still can't actually use most admin screens today: a real
functional-permissions gap, not a display cosmetics issue.

This migration is purely additive: 9 new permission codes, attached only to
the existing "admin" system role (role_id=1) — the "employee" role's grant
set is untouched. No existing table, column, or row is modified.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

permissions_table = sa.table(
    "permissions",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("description", sa.String),
)

role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", sa.Integer),
    sa.column("permission_id", sa.Integer),
)

# id : (code, description) — continuing straight on from 0018's ids 1-12.
NEW_PERMISSIONS = [
    (13, "work_entries:approve", "Approve or reject work entries"),
    (14, "work_entries:manage", "Delete work entries and export the entries CSV"),
    (15, "users:manage", "Create/edit/deactivate user (login/auth) accounts"),
    (16, "projects:manage", "Create/edit/deactivate projects"),
    (17, "holidays:manage", "Create/edit/deactivate the holiday calendar"),
    (18, "leave_types:manage", "Configure leave types and leave policies"),
    (19, "leave_ledger:manage", "Post manual ledger adjustments and run annual grants"),
    (20, "leave_balances:view_all", "View any employee's leave balance"),
    (21, "reports:view", "View and export cross-employee reports"),
]

ADMIN_ROLE_ID = 1  # seeded in 0018; system role, never deleted


def upgrade() -> None:
    op.bulk_insert(
        permissions_table,
        [{"id": pid, "code": code, "description": desc} for pid, code, desc in NEW_PERMISSIONS],
    )
    op.execute("SELECT setval('permissions_id_seq', (SELECT MAX(id) FROM permissions))")

    op.bulk_insert(
        role_permissions_table,
        [{"role_id": ADMIN_ROLE_ID, "permission_id": pid} for pid, _, _ in NEW_PERMISSIONS],
    )


def downgrade() -> None:
    ids = [pid for pid, _, _ in NEW_PERMISSIONS]
    op.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": ids},
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": ids},
    )
