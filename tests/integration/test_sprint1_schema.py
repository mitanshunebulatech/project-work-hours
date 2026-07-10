"""
tests/integration/test_sprint1_schema.py
Schema-level checks for the Sprint 1 additions: departments, roles/permissions,
employee_profiles (encrypted PAN), and leave_requests.half_day_slot.

Uses its own isolated in-memory SQLite engine (portable types only) per the
project's existing convention (see tests/integration/conftest.py) — this is
schema-shape verification, not a substitute for real Postgres execution.
"""

from datetime import date

import pytest
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.db.base import Base
from app.models.department import Department
from app.models.employee_profile import EmployeeProfile
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.permission import Permission
from app.models.role import Role, role_permissions
from app.models.user import User


def _build_engine():
    test_metadata = MetaData()
    for table_name in (
        "roles",
        "permissions",
        "role_permissions",
        "users",
        "departments",
        "employee_profiles",
        "leave_types",
        "leave_requests",
    ):
        Base.metadata.tables[table_name].to_metadata(test_metadata)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session():
    engine = _build_engine()
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_department_create_and_unique_name(db_session: Session) -> None:
    db_session.add(Department(name="Engineering"))
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.add(Department(name="Engineering"))
        db_session.commit()


def test_role_permission_many_to_many(db_session: Session) -> None:
    perm = Permission(code="leave_requests:approve", description="Approve leave")
    role = Role(name="admin", is_system_role=True)
    role.permissions.append(perm)
    db_session.add(role)
    db_session.commit()

    fetched = db_session.query(Role).filter_by(name="admin").one()
    assert len(fetched.permissions) == 1
    assert fetched.permissions[0].code == "leave_requests:approve"


def test_employee_profile_encrypted_pan_round_trips(db_session: Session) -> None:
    dept = Department(name="Finance")
    user = User(username="carol", password_hash=hash_password("Password1"), role="employee")
    db_session.add_all([dept, user])
    db_session.commit()
    user_id = user.id  # captured before expunge_all() below detaches the instance

    profile = EmployeeProfile(
        user_id=user_id,
        department_id=dept.id,
        full_name="Carol Employee",
        pan_number="ABCDE1234F",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.expunge_all()

    fetched = db_session.query(EmployeeProfile).filter_by(user_id=user_id).one()
    assert fetched.pan_number == "ABCDE1234F"  # decrypted transparently on read

    # Verify it's genuinely not stored in plaintext at the raw DB row level.
    raw = db_session.execute(
        text("SELECT pan_number FROM employee_profiles WHERE user_id = :uid"),
        {"uid": user_id},
    ).scalar_one()
    assert raw != "ABCDE1234F"


def test_employee_profile_unique_user_id(db_session: Session) -> None:
    user = User(username="dave", password_hash=hash_password("Password1"), role="employee")
    db_session.add(user)
    db_session.commit()

    db_session.add(EmployeeProfile(user_id=user.id, full_name="Dave One"))
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.add(EmployeeProfile(user_id=user.id, full_name="Dave Duplicate"))
        db_session.commit()


def test_half_day_slot_requires_slot_when_is_half_day_true(db_session: Session) -> None:
    user = User(username="erin", password_hash=hash_password("Password1"), role="employee")
    leave_type = LeaveType(code="AL", display_name="Annual Leave")
    db_session.add_all([user, leave_type])
    db_session.commit()

    # is_half_day=True with no slot must be rejected by the CHECK constraint.
    bad = LeaveRequest(
        employee_id=user.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        is_half_day=True,
        half_day_slot=None,
        working_days_count=0.5,
        reason="Doctor visit",
    )
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Valid pairing succeeds.
    good = LeaveRequest(
        employee_id=user.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 8, 2),
        end_date=date(2026, 8, 2),
        is_half_day=True,
        half_day_slot="first_half",
        working_days_count=0.5,
        reason="Doctor visit",
    )
    db_session.add(good)
    db_session.commit()
    assert good.id is not None


def test_half_day_slot_must_be_null_when_is_half_day_false(db_session: Session) -> None:
    user = User(username="frank", password_hash=hash_password("Password1"), role="employee")
    leave_type = LeaveType(code="AL2", display_name="Annual Leave 2")
    db_session.add_all([user, leave_type])
    db_session.commit()

    bad = LeaveRequest(
        employee_id=user.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 3),
        is_half_day=False,
        half_day_slot="first_half",  # inconsistent — full day but a slot is set
        working_days_count=1,
        reason="Full day leave",
    )
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
