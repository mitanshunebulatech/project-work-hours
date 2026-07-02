"""
tests/integration/test_entry_business_rules.py
Closes two of the three gaps named in Document 11 (Testing Strategy) §11.7:
  1. Duplicate-entry 409 path — previously manually verified only.
  2. Role-scoping (employee A cannot see employee B's entries) — previously
     verified by code review of EntryService.list_entries only.

These run against a real SQLite-backed Session (see conftest.py), exercising
the actual EntryService + WorkEntryRepository + SQLAlchemy stack, not a mock.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.project import Project
from app.models.user import User
from app.schemas.entry import WorkEntryCreate
from app.services.entry_service import EntryService


def test_duplicate_entry_raises_conflict_error(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """BR-01: one entry per employee+project+day. Second identical submission must be rejected."""
    service = EntryService(db_session)
    alice = seeded_users["alice"]

    payload = WorkEntryCreate(
        project_id=seeded_project.id,
        entry_date=date.today(),
        hours_worked=Decimal("8"),
        remarks="First submission",
    )

    first = service.create_entry(payload, current_user=alice, ip_address="127.0.0.1")
    assert first.status == "pending"
    assert first.hours_worked == Decimal("8")

    duplicate_payload = WorkEntryCreate(
        project_id=seeded_project.id,
        entry_date=date.today(),
        hours_worked=Decimal("4"),  # different hours, same employee+project+date — still a duplicate
        remarks="Attempted second submission",
    )

    with pytest.raises(ConflictError) as exc_info:
        service.create_entry(duplicate_payload, current_user=alice, ip_address="127.0.0.1")

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail.lower()


def test_different_project_same_day_is_allowed(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """Sanity check on the other side of BR-01: the constraint is per-project, not per-day globally."""
    service = EntryService(db_session)
    alice = seeded_users["alice"]

    second_project = Project(project_name="Second Project")
    db_session.add(second_project)
    db_session.commit()

    service.create_entry(
        WorkEntryCreate(project_id=seeded_project.id, entry_date=date.today(), hours_worked=Decimal("4")),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    # Same employee, same date, DIFFERENT project — must succeed, not raise.
    second_entry = service.create_entry(
        WorkEntryCreate(project_id=second_project.id, entry_date=date.today(), hours_worked=Decimal("4")),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    assert second_entry.project_id == second_project.id


def test_employee_cannot_see_another_employees_entries(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """
    Role-scoping gap closure: confirms EntryService.list_entries actually
    enforces row-level isolation for a non-admin caller, not just that the
    code reads correctly on review.
    """
    service = EntryService(db_session)
    alice = seeded_users["alice"]
    bob = seeded_users["bob"]

    service.create_entry(
        WorkEntryCreate(project_id=seeded_project.id, entry_date=date.today(), hours_worked=Decimal("6")),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    service.create_entry(
        WorkEntryCreate(project_id=seeded_project.id, entry_date=date.today(), hours_worked=Decimal("7")),
        current_user=bob,
        ip_address="127.0.0.1",
    )

    # Bob lists his own entries — must see exactly his one entry, never Alice's.
    bob_view = service.list_entries(
        current_user=bob,
        page=1,
        size=20,
        employee_id=None,  # employees can't filter by employee_id anyway — service should ignore/override this
        project_id=None,
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )

    assert bob_view.total == 1
    assert all(item.employee_username == "bob" for item in bob_view.items)
    assert all(item.employee_username != "alice" for item in bob_view.items)


def test_employee_cannot_bypass_scoping_by_passing_another_employee_id(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """
    The sharper version of the role-scoping test: an employee explicitly
    PASSES another employee's id as a filter. The service must ignore that
    and still scope to the caller's own id — this is the exact line in
    EntryService.list_entries ("scoped_employee_id = employee_id if
    current_user.is_admin else current_user.id") that the gap in §11.7
    called out as verified by code review only.
    """
    service = EntryService(db_session)
    alice = seeded_users["alice"]
    bob = seeded_users["bob"]

    service.create_entry(
        WorkEntryCreate(project_id=seeded_project.id, entry_date=date.today(), hours_worked=Decimal("6")),
        current_user=alice,
        ip_address="127.0.0.1",
    )

    # Bob, a non-admin, explicitly requests employee_id=alice.id. Must NOT see Alice's entry.
    bob_attempting_to_view_alice = service.list_entries(
        current_user=bob,
        page=1,
        size=20,
        employee_id=alice.id,
        project_id=None,
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )

    assert bob_attempting_to_view_alice.total == 0
    assert bob_attempting_to_view_alice.items == []


def test_admin_can_see_all_employees_entries(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """Confirms the admin branch of the same scoping logic — admins are NOT scoped."""
    service = EntryService(db_session)
    alice = seeded_users["alice"]
    bob = seeded_users["bob"]

    admin = User(
        username="admin_test",
        email="admin@test.local",
        password_hash="irrelevant-for-this-test",
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()

    service.create_entry(
        WorkEntryCreate(project_id=seeded_project.id, entry_date=date.today(), hours_worked=Decimal("5")),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    service.create_entry(
        WorkEntryCreate(project_id=seeded_project.id, entry_date=date.today(), hours_worked=Decimal("3")),
        current_user=bob,
        ip_address="127.0.0.1",
    )

    admin_view = service.list_entries(
        current_user=admin,
        page=1,
        size=20,
        employee_id=None,
        project_id=None,
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )

    assert admin_view.total == 2
    usernames_seen = {item.employee_username for item in admin_view.items}
    assert usernames_seen == {"alice", "bob"}
