"""
tests/integration/test_onboarding_service.py
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.department import Department
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


@pytest.fixture
def department(db_session: Session) -> Department:
    """PM req #7: joining_date/department_id/designation/last_name are now
    required on EmployeeOnboardingRequest, so every test needs a real
    department to reference rather than relying on the old
    department_id=None default."""
    dept = Department(name="Engineering")
    db_session.add(dept)
    db_session.commit()
    return dept


def _make_request(*, department_id: int, **overrides) -> EmployeeOnboardingRequest:
    defaults = dict(
        first_name="Priya",
        last_name="Nair",
        email="priya.nair@nebulatech-test.com",
        role_id=1,
        department_id=department_id,
        designation="Software Engineer",
        joining_date=date(2026, 1, 5),
    )
    defaults.update(overrides)
    return EmployeeOnboardingRequest(**defaults)


def test_onboard_employee_creates_user_and_profile_atomically(
    db_session: Session, employee_role: Role, department: Department
):
    service = OnboardingService(db_session)
    result = service.onboard_employee(
        _make_request(
            role_id=employee_role.id, department_id=department.id, years_of_experience=Decimal("3.5")
        ),
        actor_id=1,
        ip_address="127.0.0.1",
    )

    created_user = db_session.get(User, result.user_id)
    assert created_user is not None
    assert created_user.email == "priya.nair@nebulatech-test.com"
    assert created_user.role == "employee"
    assert created_user.role_id == employee_role.id
    assert created_user.must_change_password is True

    profile = EmployeeProfileService(db_session).get_profile(result.employee_profile_id)
    assert profile.first_name == "Priya"
    assert profile.employee_code.startswith("EMP-")

    assert result.temp_password
    from app.core.security import verify_password

    assert verify_password(result.temp_password, created_user.password_hash)


def test_onboard_employee_derives_legacy_admin_role_from_system_admin_role(
    db_session: Session, admin_role: Role, department: Department
):
    service = OnboardingService(db_session)
    result = service.onboard_employee(
        _make_request(email="new.admin@nebulatech-test.com", role_id=admin_role.id, department_id=department.id),
        actor_id=1,
        ip_address=None,
    )
    created_user = db_session.get(User, result.user_id)
    assert created_user.role == "admin"


def test_onboard_employee_rejects_duplicate_email(
    db_session: Session, employee_role: Role, department: Department
):
    service = OnboardingService(db_session)
    service.onboard_employee(
        _make_request(role_id=employee_role.id, department_id=department.id), actor_id=1, ip_address=None
    )

    with pytest.raises(ConflictError):
        service.onboard_employee(
            _make_request(role_id=employee_role.id, department_id=department.id), actor_id=1, ip_address=None
        )


def test_onboard_employee_rejects_unknown_role(db_session: Session, department: Department):
    service = OnboardingService(db_session)
    with pytest.raises(NotFoundError):
        service.onboard_employee(
            _make_request(role_id=999999, department_id=department.id), actor_id=1, ip_address=None
        )


def test_onboard_employee_deduplicates_username_on_collision(
    db_session: Session, employee_role: Role, department: Department
):
    service = OnboardingService(db_session)
    first = service.onboard_employee(
        _make_request(email="one@nebulatech-test.com", role_id=employee_role.id, department_id=department.id),
        actor_id=1, ip_address=None
    )
    second = service.onboard_employee(
        _make_request(
            first_name="Priya", last_name="Nair", email="two@nebulatech-test.com",
            role_id=employee_role.id, department_id=department.id,
        ),
        actor_id=1,
        ip_address=None,
    )
    assert first.username != second.username


def test_generated_temp_password_satisfies_complexity_rule(db_session: Session, employee_role: Role):
    from app.schemas.auth import _validate_password_complexity
    from app.utils.password_generator import generate_temp_password

    for _ in range(50):
        pw = generate_temp_password()
        assert len(pw) == 8
        _validate_password_complexity(pw)


def test_employee_code_sequence_never_collides_across_many_onboardings(
    db_session: Session, employee_role: Role, department: Department
):
    service = OnboardingService(db_session)
    codes = set()
    for i in range(10):
        result = service.onboard_employee(
            _make_request(email=f"person{i}@nebulatech-test.com", role_id=employee_role.id, department_id=department.id),
            actor_id=1,
            ip_address=None,
        )
        assert result.employee_code not in codes
        codes.add(result.employee_code)


def test_identity_document_upload_list_and_delete(
    db_session: Session, employee_role: Role, department: Department
):
    onboarding = OnboardingService(db_session)
    result = onboarding.onboard_employee(
        _make_request(role_id=employee_role.id, department_id=department.id), actor_id=1, ip_address=None
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


# --- PM req #7: last_name/department_id/designation/joining_date are now required ---

def test_onboarding_request_rejects_missing_last_name():
    with pytest.raises(ValueError):
        EmployeeOnboardingRequest(
            first_name="Priya", email="priya@nebulatech-test.com", role_id=1,
            department_id=1, designation="Engineer", joining_date=date(2026, 1, 5),
        )


def test_onboarding_request_rejects_missing_department(department: Department):
    with pytest.raises(ValueError):
        EmployeeOnboardingRequest(
            first_name="Priya", last_name="Nair", email="priya@nebulatech-test.com", role_id=1,
            designation="Engineer", joining_date=date(2026, 1, 5),
        )


def test_onboarding_request_rejects_missing_designation(department: Department):
    with pytest.raises(ValueError):
        EmployeeOnboardingRequest(
            first_name="Priya", last_name="Nair", email="priya@nebulatech-test.com", role_id=1,
            department_id=department.id, joining_date=date(2026, 1, 5),
        )


def test_onboarding_request_rejects_missing_joining_date(department: Department):
    with pytest.raises(ValueError):
        EmployeeOnboardingRequest(
            first_name="Priya", last_name="Nair", email="priya@nebulatech-test.com", role_id=1,
            department_id=department.id, designation="Engineer",
        )


def test_onboarding_request_accepts_all_required_fields_present(department: Department):
    req = EmployeeOnboardingRequest(
        first_name="Priya", last_name="Nair", email="priya@nebulatech-test.com", role_id=1,
        department_id=department.id, designation="Engineer", joining_date=date(2026, 1, 5),
    )
    assert req.last_name == "Nair"
    assert req.department_id == department.id
    assert req.designation == "Engineer"
    assert req.joining_date == date(2026, 1, 5)
