"""
tests/integration/test_onboarding_service.py
"""

from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.role import Role
from app.models.user import User
from app.schemas.onboarding import EmployeeOnboardingRequest
from app.services.employee_profile_service import EmployeeProfileService
from app.services.onboarding_service import OnboardingService


@pytest.fixture
def employee_role(db_session: Session) -> Role:
    role = Role(name="Employee", is_system_role=True)
    db_session.add(role)
    db_session.commit()
    return role


@pytest.fixture
def admin_role(db_session: Session) -> Role:
    role = Role(name="Admin", is_system_role=True)
    db_session.add(role)
    db_session.commit()
    return role


def _make_request(**overrides) -> EmployeeOnboardingRequest:
    defaults = dict(
        first_name="Priya",
        last_name="Nair",
        email="priya.nair@nebulatech-test.com",
        role_id=1,
    )
    defaults.update(overrides)
    return EmployeeOnboardingRequest(**defaults)


def test_onboard_employee_creates_user_and_profile_atomically(
    db_session: Session, employee_role: Role
):
    service = OnboardingService(db_session)
    result = service.onboard_employee(
        _make_request(role_id=employee_role.id, department_id=None, years_of_experience=Decimal("3.5")),
        actor_id=1,
        ip_address="127.0.0.1",
    )

    created_user = db_session.get(User, result.user_id)
    assert created_user is not None
    assert created_user.email == "priya.nair@nebulatech-test.com"
    assert created_user.role == "employee"
    assert created_user.role_id == employee_role.id
    # PM item 7 + the must_change_password decision: onboarding always
    # forces a password reset on first login.
    assert created_user.must_change_password is True

    profile = EmployeeProfileService(db_session).get_profile(result.employee_profile_id)
    assert profile.first_name == "Priya"
    assert profile.employee_code.startswith("EMP-")


def test_onboard_employee_derives_legacy_admin_role_from_system_admin_role(
    db_session: Session, admin_role: Role
):
    """Legacy `role` string still drives is_admin/JWT claims — onboarding
    into the seeded system "Admin" role must set it correctly, not just
    role_id, or the account would silently lose admin fallback access."""
    service = OnboardingService(db_session)
    result = service.onboard_employee(
        _make_request(email="new.admin@nebulatech-test.com", role_id=admin_role.id),
        actor_id=1,
        ip_address=None,
    )
    created_user = db_session.get(User, result.user_id)
    assert created_user.role == "admin"


def test_onboard_employee_rejects_duplicate_email(db_session: Session, employee_role: Role):
    service = OnboardingService(db_session)
    service.onboard_employee(
        _make_request(role_id=employee_role.id), actor_id=1, ip_address=None
    )

    with pytest.raises(ConflictError):
        service.onboard_employee(
            _make_request(role_id=employee_role.id), actor_id=1, ip_address=None
        )


def test_onboard_employee_rejects_unknown_role(db_session: Session):
    service = OnboardingService(db_session)
    with pytest.raises(NotFoundError):
        service.onboard_employee(_make_request(role_id=999999), actor_id=1, ip_address=None)


def test_onboard_employee_deduplicates_username_on_collision(
    db_session: Session, employee_role: Role
):
    service = OnboardingService(db_session)
    first = service.onboard_employee(
        _make_request(email="one@nebulatech-test.com", role_id=employee_role.id), actor_id=1, ip_address=None
    )
    second = service.onboard_employee(
        _make_request(
            first_name="Priya", last_name="Nair", email="two@nebulatech-test.com", role_id=employee_role.id
        ),
        actor_id=1,
        ip_address=None,
    )
    assert first.username != second.username


def test_generated_temp_password_satisfies_complexity_rule(db_session: Session, employee_role: Role):
    """The generated password must pass the same complexity rule real user
    passwords are validated against (letter + digit, >=8 chars) — the
    account is created with a pre-hashed password, so nothing else would
    ever catch a generator regression that started producing weak values."""
    from app.schemas.auth import _validate_password_complexity
    from app.utils.password_generator import generate_temp_password

    for _ in range(50):
        pw = generate_temp_password()
        assert len(pw) == 8
        _validate_password_complexity(pw)  # raises on failure


def test_employee_code_sequence_never_collides_across_many_onboardings(
    db_session: Session, employee_role: Role
):
    """Regression pin for the MAX+1 race condition bug — not a true
    concurrency test (the test suite is single-threaded/SQLite), but pins
    that a run of onboardings never produces a duplicate employee_code."""
    service = OnboardingService(db_session)
    codes = set()
    for i in range(10):
        result = service.onboard_employee(
            _make_request(email=f"person{i}@nebulatech-test.com", role_id=employee_role.id),
            actor_id=1,
            ip_address=None,
        )
        assert result.employee_code not in codes
        codes.add(result.employee_code)


def test_identity_document_upload_list_and_delete(db_session: Session, employee_role: Role):
    onboarding = OnboardingService(db_session)
    result = onboarding.onboard_employee(
        _make_request(role_id=employee_role.id), actor_id=1, ip_address=None
    )

    profile_service = EmployeeProfileService(db_session)
    upload = UploadFile(filename="pan_card.pdf", file=BytesIO(b"%PDF-1.4 fake pan card bytes"))

    created = profile_service.upload_identity_document(
        result.employee_profile_id,
        document_type="PAN",
        document_number="ABCDE1234F",
        file=upload,
        actor_id=1,
        ip_address=None,
    )
    assert created.document_type == "PAN"
    # Never returned in full — same masking posture as employee_profiles.pan_number.
    assert created.document_number_masked is not None
    assert "ABCDE1234F" not in created.document_number_masked

    listed = profile_service.list_identity_documents(result.employee_profile_id)
    assert len(listed) == 1

    profile_service.delete_identity_document(
        result.employee_profile_id, created.id, actor_id=1, ip_address=None
    )
    assert profile_service.list_identity_documents(result.employee_profile_id) == []


def test_identity_document_upload_requires_existing_profile(db_session: Session):
    profile_service = EmployeeProfileService(db_session)
    upload = UploadFile(filename="doc.pdf", file=BytesIO(b"fake bytes"))
    with pytest.raises(NotFoundError):
        profile_service.upload_identity_document(
            999999, document_type="PAN", document_number=None, file=upload, actor_id=1, ip_address=None
        )
