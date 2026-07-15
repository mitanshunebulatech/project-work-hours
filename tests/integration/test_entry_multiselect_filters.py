"""
tests/integration/test_entry_multiselect_filters.py
Covers the multi-select employee/project checkbox filters (PM req #2,
Timesheet Module) added to WorkEntryRepository.search /
search_all_for_export and threaded through EntryService.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.project import Project
from app.models.user import User
from app.models.work_entry import WorkEntry
from app.services.entry_service import EntryService


@pytest.fixture
def admin_user(db_session: Session) -> User:
    admin = User(
        username="admin1", email="admin1@test.local", password_hash=hash_password("Password1"), role="admin"
    )
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def two_projects(db_session: Session) -> dict[str, Project]:
    p1 = Project(project_name="Project One", description="")
    p2 = Project(project_name="Project Two", description="")
    db_session.add_all([p1, p2])
    db_session.commit()
    return {"one": p1, "two": p2}


def _make_entry(db_session, employee_id, project_id, hours="4"):
    entry = WorkEntry(
        employee_id=employee_id,
        project_id=project_id,
        entry_date=date.today(),
        hours_worked=Decimal(hours),
        remarks="test",
        status="pending",
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_admin_can_filter_by_multiple_employee_ids(
    db_session: Session, seeded_users: dict[str, User], two_projects: dict[str, Project], admin_user: User
):
    alice, bob = seeded_users["alice"], seeded_users["bob"]
    # A third employee who should be excluded by the filter.
    carol = User(
        username="carol", email="carol@test.local", password_hash=hash_password("Password1"), role="employee"
    )
    db_session.add(carol)
    db_session.commit()

    _make_entry(db_session, alice.id, two_projects["one"].id)
    _make_entry(db_session, bob.id, two_projects["one"].id)
    _make_entry(db_session, carol.id, two_projects["one"].id)

    service = EntryService(db_session)
    result = service.list_entries(
        current_user=admin_user,
        page=1,
        size=20,
        employee_id=None,
        employee_ids=[alice.id, bob.id],
        project_id=None,
        project_ids=None,
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )
    returned_employee_ids = {item.employee_id for item in result.items}
    assert returned_employee_ids == {alice.id, bob.id}
    assert result.total == 2


def test_admin_can_filter_by_multiple_project_ids(
    db_session: Session, seeded_users: dict[str, User], two_projects: dict[str, Project], admin_user: User
):
    alice = seeded_users["alice"]
    _make_entry(db_session, alice.id, two_projects["one"].id)
    _make_entry(db_session, alice.id, two_projects["two"].id)

    service = EntryService(db_session)
    result = service.list_entries(
        current_user=admin_user,
        page=1,
        size=20,
        employee_id=None,
        employee_ids=None,
        project_id=None,
        project_ids=[two_projects["one"].id],
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )
    assert result.total == 1
    assert result.items[0].project_id == two_projects["one"].id


def test_non_admin_employee_ids_filter_is_silently_ignored(
    db_session: Session, seeded_users: dict[str, User], two_projects: dict[str, Project]
):
    """
    A non-admin has no legitimate use for employee_ids (they can only ever
    see their own entries) — the filter should be dropped, not error, and
    the employee's own-entries scoping must still apply.
    """
    alice, bob = seeded_users["alice"], seeded_users["bob"]
    _make_entry(db_session, alice.id, two_projects["one"].id)
    _make_entry(db_session, bob.id, two_projects["one"].id)

    service = EntryService(db_session)
    result = service.list_entries(
        current_user=alice,  # not admin
        page=1,
        size=20,
        employee_id=None,
        employee_ids=[alice.id, bob.id],  # attempting to see bob's too
        project_id=None,
        project_ids=None,
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )
    assert result.total == 1
    assert result.items[0].employee_id == alice.id


def test_export_csv_respects_multiselect_employee_ids(
    db_session: Session, seeded_users: dict[str, User], two_projects: dict[str, Project]
):
    alice, bob = seeded_users["alice"], seeded_users["bob"]
    carol = User(
        username="carol2", email="carol2@test.local", password_hash=hash_password("Password1"), role="employee"
    )
    db_session.add(carol)
    db_session.commit()

    _make_entry(db_session, alice.id, two_projects["one"].id)
    _make_entry(db_session, bob.id, two_projects["one"].id)
    _make_entry(db_session, carol.id, two_projects["one"].id)

    service = EntryService(db_session)
    csv_content = service.export_entries_csv(
        employee_id=None,
        employee_ids=[alice.id, bob.id],
        project_id=None,
        project_ids=None,
        status=None,
        date_from=None,
        date_to=None,
    )
    assert "carol" not in csv_content
    assert "alice" in csv_content
    assert "bob" in csv_content


def test_plural_filter_wins_when_both_singular_and_plural_given(
    db_session: Session, seeded_users: dict[str, User], two_projects: dict[str, Project], admin_user: User
):
    """Documents the deliberate precedence rule: employee_ids overrides employee_id
    if both are somehow passed together."""
    alice, bob = seeded_users["alice"], seeded_users["bob"]
    _make_entry(db_session, alice.id, two_projects["one"].id)
    _make_entry(db_session, bob.id, two_projects["one"].id)

    service = EntryService(db_session)
    result = service.list_entries(
        current_user=admin_user,
        page=1,
        size=20,
        employee_id=alice.id,  # would normally restrict to alice only
        employee_ids=[bob.id],  # plural should win instead
        project_id=None,
        project_ids=None,
        status=None,
        date_from=None,
        date_to=None,
        search=None,
    )
    assert result.total == 1
    assert result.items[0].employee_id == bob.id
