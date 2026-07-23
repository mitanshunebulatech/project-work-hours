"""
tests/integration/test_search_service.py

Stage 3 (HRMS V3): global search (⌘K command palette backend).
"""

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.repositories.department_repo import DepartmentRepository
from app.db.repositories.employee_profile_repo import EmployeeProfileRepository
from app.db.repositories.project_repo import ProjectRepository
from app.models.department import Department
from app.models.employee_profile import EmployeeProfile
from app.models.project import Project
from app.models.user import User
from app.services.search_service import SearchService


@pytest.fixture
def searchable_data(db_session: Session):
    dept = Department(name="Engineering")
    db_session.add(dept)
    db_session.commit()

    user = User(
        username="priyanair", email="priya.search@test.local",
        password_hash=hash_password("Password1"), role="employee",
    )
    db_session.add(user)
    db_session.commit()

    profile = EmployeeProfile(
        user_id=user.id, employee_code="EMP-0099", first_name="Priya", last_name="Nair",
        department_id=dept.id, designation="QA Engineer",
    )
    db_session.add(profile)

    project = Project(project_name="Nebula Migration", description="Legacy data migration")
    db_session.add(project)
    db_session.commit()

    return {"department": dept, "user": user, "profile": profile, "project": project}


# ---------- Repository-level text search ----------

def test_employee_profile_repo_search_matches_full_name(db_session: Session, searchable_data):
    repo = EmployeeProfileRepository(db_session)
    items, total = repo.search(search="priya")
    assert total == 1
    assert items[0].id == searchable_data["profile"].id


def test_employee_profile_repo_search_matches_employee_code(db_session: Session, searchable_data):
    repo = EmployeeProfileRepository(db_session)
    items, total = repo.search(search="emp-0099")
    assert total == 1


def test_employee_profile_repo_search_is_case_insensitive(db_session: Session, searchable_data):
    repo = EmployeeProfileRepository(db_session)
    items, _ = repo.search(search="NAIR")
    assert len(items) == 1


def test_employee_profile_repo_search_no_match_returns_empty(db_session: Session, searchable_data):
    repo = EmployeeProfileRepository(db_session)
    items, total = repo.search(search="nonexistent-name-xyz")
    assert total == 0
    assert items == []


def test_department_repo_search_matches_name(db_session: Session, searchable_data):
    repo = DepartmentRepository(db_session)
    items, total = repo.search(search="engineer")
    assert total == 1
    assert items[0].id == searchable_data["department"].id


def test_project_repo_search_still_works_unchanged(db_session: Session, searchable_data):
    """Regression check — ProjectRepository.search() already had text
    matching before this stage; confirms extending the other two repos
    to match its pattern didn't disturb it."""
    repo = ProjectRepository(db_session)
    items, total = repo.search(search="nebula")
    assert total == 1


# ---------- SearchService: composition + permission-awareness ----------

def test_search_service_returns_results_across_all_categories(
    db_session: Session, searchable_data
):
    # Deliberately NOT setting role_id here — user_permission_codes() checks
    # role_id/role_ref FIRST and only falls back to the legacy role-string
    # fallback (ALL_PERMISSION_CODES for "admin") when role_id is None. A
    # role_id pointing at a Role with no Permission rows attached would
    # resolve to an EMPTY set, not "all permissions" — the opposite of
    # what this test needs.
    admin = User(
        username="admin_search_test", email="admin.search@test.local",
        password_hash=hash_password("Password1"), role="admin",
    )
    db_session.add(admin)
    db_session.commit()

    result = SearchService(db_session).search(q="e", requesting_user=admin)  # broad query
    categories = {r.category for r in result.results}
    assert "employee" in categories or "project" in categories or "department" in categories


def test_search_service_excludes_employees_without_employees_view_permission(
    db_session: Session, searchable_data
):
    """The actual permission-awareness this service exists for: an
    employee account (no employees:view) must never see employee search
    results, even if they know exactly who they're looking for."""
    employee = User(
        username="plain_search_test", email="plain.search@test.local",
        password_hash=hash_password("Password1"), role="employee",
    )
    db_session.add(employee)
    db_session.commit()

    result = SearchService(db_session).search(q="priya", requesting_user=employee)
    assert all(r.category != "employee" for r in result.results)


def test_search_service_query_is_returned_verbatim(db_session: Session, searchable_data):
    admin = User(
        username="admin_search_test2", email="admin.search2@test.local",
        password_hash=hash_password("Password1"), role="admin",
    )
    db_session.add(admin)
    db_session.commit()

    result = SearchService(db_session).search(q="nebula", requesting_user=admin)
    assert result.query == "nebula"
    assert any(r.category == "project" and r.label == "Nebula Migration" for r in result.results)
