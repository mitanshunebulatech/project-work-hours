"""
app/core/permissions.py

Non-DB source of truth for permission codes, mirroring the catalogue seeded
in alembic/versions/0018_create_roles_permissions_tables.py.

Why this exists: users created before Sprint 1's role_id backfill (migration
0020) still have role_id = NULL. require_permission() (app/core/deps.py)
needs *some* permission set to check those users against — falling back to
role_id entirely would silently deny every legacy user until a backfill
script runs. Rather than hardcode a bypass ("if role == admin: allow
everything"), this fallback re-derives the exact same permission codes an
admin/employee role would have via role_id, so behavior is identical
before and after backfill — no flag day, no silent access change.

IMPORTANT: If you add/remove/rename a permission code in a future
migration's seed data, update ALL_PERMISSION_CODES / EMPLOYEE_PERMISSION_CODES
here to match, or legacy (role_id=NULL) users will see stale permission
behavior that diverges from what a freshly-backfilled user would get.
"""

ALL_PERMISSION_CODES: frozenset[str] = frozenset(
    {
        "leave_requests:create",
        "leave_requests:view_own",
        "leave_requests:view_all",
        "leave_requests:approve",
        "work_entries:create",
        "work_entries:view_own",
        "work_entries:view_all",
        "employees:view",
        "employees:manage",
        "departments:manage",
        "roles:manage",
        "audit_logs:view",
    }
)

# Must match EMPLOYEE_PERMISSION_CODES in 0018_create_roles_permissions_tables.py exactly.
EMPLOYEE_PERMISSION_CODES: frozenset[str] = frozenset(
    {
        "leave_requests:create",
        "leave_requests:view_own",
        "work_entries:create",
        "work_entries:view_own",
    }
)
