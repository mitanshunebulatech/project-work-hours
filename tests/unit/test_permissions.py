"""
tests/unit/test_permissions.py
Pure-Python tests for the permission-resolution logic in app/core/deps.py.
Uses lightweight stand-ins instead of real SQLAlchemy User/Role objects —
user_permission_codes() only touches .role, .role_id, .role_ref.permissions
and Permission.code, so a stub with those attributes is sufficient and
keeps these tests independent of any database.
"""

import pytest

from app.core.deps import require_permission, user_permission_codes
from app.core.exceptions import ForbiddenError
from app.core.permissions import ALL_PERMISSION_CODES, EMPLOYEE_PERMISSION_CODES


class _StubPermission:
    def __init__(self, code: str):
        self.code = code


class _StubRole:
    def __init__(self, codes: set[str]):
        self.permissions = [_StubPermission(c) for c in codes]


class _StubUser:
    def __init__(self, role: str, role_id: int | None = None, role_ref=None):
        self.role = role
        self.role_id = role_id
        self.role_ref = role_ref


# ---- user_permission_codes: legacy fallback (role_id is NULL) ----


def test_legacy_admin_gets_all_permission_codes():
    user = _StubUser(role="admin", role_id=None, role_ref=None)
    assert user_permission_codes(user) == set(ALL_PERMISSION_CODES)


def test_legacy_employee_gets_self_service_codes_only():
    user = _StubUser(role="employee", role_id=None, role_ref=None)
    assert user_permission_codes(user) == set(EMPLOYEE_PERMISSION_CODES)


def test_legacy_employee_does_not_get_admin_only_codes():
    user = _StubUser(role="employee", role_id=None, role_ref=None)
    codes = user_permission_codes(user)
    assert "departments:manage" not in codes
    assert "leave_requests:approve" not in codes


# ---- migration 0023: newly added codes for previously require_admin-only routers ----

NEW_CODES_FROM_MIGRATION_0023 = {
    "work_entries:approve",
    "work_entries:manage",
    "users:manage",
    "projects:manage",
    "holidays:manage",
    "leave_types:manage",
    "leave_ledger:manage",
    "leave_balances:view_all",
    "reports:view",
}


def test_legacy_admin_gets_the_newly_added_permission_codes():
    """Guards against ALL_PERMISSION_CODES drifting out of sync with migration
    0023's seed data (see that migration's docstring) — a legacy (role_id=NULL)
    admin must get exactly the same access a freshly-backfilled admin would."""
    user = _StubUser(role="admin", role_id=None, role_ref=None)
    codes = user_permission_codes(user)
    assert NEW_CODES_FROM_MIGRATION_0023.issubset(codes)


def test_legacy_employee_does_not_get_the_newly_added_permission_codes():
    user = _StubUser(role="employee", role_id=None, role_ref=None)
    codes = user_permission_codes(user)
    assert NEW_CODES_FROM_MIGRATION_0023.isdisjoint(codes)


# ---- user_permission_codes: role_id backfilled, sourced from Role.permissions ----


def test_backfilled_role_uses_role_permissions_not_legacy_string():
    # role string says "employee" but the real Role grants an admin-only code —
    # the DB-backed role must win once role_id/role_ref are populated.
    custom_role = _StubRole({"leave_requests:approve", "employees:view"})
    user = _StubUser(role="employee", role_id=5, role_ref=custom_role)
    assert user_permission_codes(user) == {"leave_requests:approve", "employees:view"}


def test_backfilled_role_with_no_permissions_grants_nothing():
    empty_role = _StubRole(set())
    user = _StubUser(role="admin", role_id=5, role_ref=empty_role)
    # Even though the legacy string says "admin", a real (empty) role_ref
    # takes precedence — this is deliberate: once role_id is set, it's the
    # source of truth, not a hint layered on top of the legacy string.
    assert user_permission_codes(user) == set()


# ---- require_permission: the FastAPI dependency itself ----


def test_require_permission_allows_when_user_has_code():
    checker = require_permission("leave_requests:approve")
    user = _StubUser(role="admin", role_id=None, role_ref=None)
    result = checker(user)
    assert result is user


def test_require_permission_denies_when_user_lacks_code():
    checker = require_permission("departments:manage")
    user = _StubUser(role="employee", role_id=None, role_ref=None)
    with pytest.raises(ForbiddenError):
        checker(user)


def test_require_permission_requires_all_codes_when_multiple_given():
    role = _StubRole({"leave_requests:approve"})  # missing employees:view
    user = _StubUser(role="employee", role_id=5, role_ref=role)
    checker = require_permission("leave_requests:approve", "employees:view")
    with pytest.raises(ForbiddenError):
        checker(user)
