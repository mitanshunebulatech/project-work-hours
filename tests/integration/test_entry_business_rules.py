"""
tests/integration/test_entry_business_rules.py
Closes gaps named in Document 11 (Testing Strategy) §11.7:
  1. Overlap-rejection 409 path (Sprint 3, replaces the old duplicate-entry
     check now that BR-01 allows multiple time-blocks per project per day).
  2. Role-scoping (employee A cannot see employee B's entries) — previously
     verified by code review of EntryService.list_entries only.

These run against a real SQLite-backed Session (see conftest.py), exercising
the actual EntryService + WorkEntryRepository + SQLAlchemy stack, not a mock.
"""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.project import Project
from app.models.user import User
from app.schemas.entry import WorkEntryCreate
from app.services.entry_service import EntryService


def test_overlapping_entries_raise_conflict_error(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """BR-01 (Sprint 3): an employee's time-blocks may not overlap on a given day."""
    service = EntryService(db_session)
    alice = seeded_users["alice"]

    payload = WorkEntryCreate(
        project_id=seeded_project.id,
        entry_date=date.today(),
        start_time=time(9, 0),
        end_time=time(12, 0),
        hours_worked=Decimal("3"),
        remarks="First block",
    )
    first = service.create_entry(payload, current_user=alice, ip_address="127.0.0.1")
    assert first.status == "pending"

    overlapping_payload = WorkEntryCreate(
        project_id=seeded_project.id,
        entry_date=date.today(),
        start_time=time(11, 0),  # overlaps the 9-12 block
        end_time=time(14, 0),
        hours_worked=Decimal("3"),
        remarks="Overlapping block",
    )

    with pytest.raises(ConflictError) as exc_info:
        service.create_entry(overlapping_payload, current_user=alice, ip_address="127.0.0.1")

    assert exc_info.value.status_code == 409
    assert "overlap" in exc_info.value.detail.lower()


def test_non_overlapping_blocks_same_project_same_day_allowed(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """Sprint 3: multiple time-blocks against the SAME project on the SAME day are now allowed,
    as long as their times don't overlap — this is the behavior BR-01 was relaxed to support."""
    service = EntryService(db_session)
    alice = seeded_users["alice"]

    service.create_entry(
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            hours_worked=Decimal("3"),
        ),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    # Same employee, same project, same date, non-overlapping time — must succeed, not raise.
    second_entry = service.create_entry(
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(13, 0),
            end_time=time(17, 0),
            hours_worked=Decimal("4"),
        ),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    assert second_entry.project_id == seeded_project.id
    assert second_entry.start_time == time(13, 0)


def test_different_project_overlapping_time_still_raises_conflict(
    db_session: Session, seeded_users: dict[str, User], seeded_project: Project
) -> None:
    """The overlap check is per-employee-per-day across ALL projects, not per-project —
    an employee can't be logged against two different projects at the same time."""
    service = EntryService(db_session)
    alice = seeded_users["alice"]

    second_project = Project(project_name="Second Project")
    db_session.add(second_project)
    db_session.commit()

    service.create_entry(
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            hours_worked=Decimal("3"),
        ),
        current_user=alice,
        ip_address="127.0.0.1",
    )

    with pytest.raises(ConflictError):
        service.create_entry(
            WorkEntryCreate(
                project_id=second_project.id,
                entry_date=date.today(),
                start_time=time(10, 0),  # overlaps the first block, different project
                end_time=time(13, 0),
                hours_worked=Decimal("3"),
            ),
            current_user=alice,
            ip_address="127.0.0.1",
        )


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
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(15, 0),
            hours_worked=Decimal("6"),
        ),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    service.create_entry(
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(16, 0),
            hours_worked=Decimal("7"),
        ),
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
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(15, 0),
            hours_worked=Decimal("6"),
        ),
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
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(14, 0),
            hours_worked=Decimal("5"),
        ),
        current_user=alice,
        ip_address="127.0.0.1",
    )
    service.create_entry(
        WorkEntryCreate(
            project_id=seeded_project.id,
            entry_date=date.today(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            hours_worked=Decimal("3"),
        ),
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
