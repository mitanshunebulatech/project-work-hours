"""
tests/integration/test_employee_profile_service.py
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.audit_log import AuditLog
from app.schemas.department import DepartmentCreate
from app.schemas.employee_profile import (
    EmployeeProfileAdminCreate,
    EmployeeProfileAdminUpdate,
    EmployeeProfileSelfUpdate,
)
from app.services.department_service import DepartmentService
from app.services.employee_profile_service import EmployeeProfileService

VALID_PAN = "ABCDE1234F"
VALID_PAN_2 = "PQRSX5678K"


def test_admin_create_profile(db_session: Session, seeded_users):
    service = EmployeeProfileService(db_session)
    result = service.admin_create_profile(
        EmployeeProfileAdminCreate(user_id=seeded_users["alice"].id, full_name="Alice Sharma"),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )
    assert result.user_id == seeded_users["alice"].id
    assert result.full_name == "Alice Sharma"
    assert result.pan_number_masked is None  # no PAN set yet


def test_admin_create_profile_duplicate_user_raises_conflict(db_session: Session, seeded_users):
    service = EmployeeProfileService(db_session)
    service.admin_create_profile(
        EmployeeProfileAdminCreate(user_id=seeded_users["alice"].id, full_name="Alice Sharma"),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )
    with pytest.raises(ConflictError):
        service.admin_create_profile(
            EmployeeProfileAdminCreate(user_id=seeded_users["alice"].id, full_name="Alice Again"),
            actor_id=seeded_users["bob"].id,
            ip_address=None,
        )


def test_pan_is_masked_in_response_not_returned_in_full(db_session: Session, seeded_users):
    service = EmployeeProfileService(db_session)
    result = service.admin_create_profile(
        EmployeeProfileAdminCreate(
            user_id=seeded_users["alice"].id, full_name="Alice Sharma", pan_number=VALID_PAN
        ),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )
    assert result.pan_number_masked is not None
    assert VALID_PAN not in result.pan_number_masked
    assert result.pan_number_masked.endswith(VALID_PAN[-5:])


def test_pan_format_validation_rejects_bad_format():
    with pytest.raises(ValueError):
        EmployeeProfileAdminCreate(user_id=1, full_name="X", pan_number="not-a-pan")


def test_self_update_requires_existing_profile(db_session: Session, seeded_users):
    service = EmployeeProfileService(db_session)
    with pytest.raises(NotFoundError):
        service.update_own_profile(
            seeded_users["alice"].id,
            EmployeeProfileSelfUpdate(phone_number="9999999999"),
            ip_address=None,
        )


def test_self_update_own_pan_is_freely_editable_and_audit_logged(db_session: Session, seeded_users):
    service = EmployeeProfileService(db_session)
    service.admin_create_profile(
        EmployeeProfileAdminCreate(
            user_id=seeded_users["alice"].id, full_name="Alice Sharma", pan_number=VALID_PAN
        ),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )

    # First self-edit
    updated = service.update_own_profile(
        seeded_users["alice"].id,
        EmployeeProfileSelfUpdate(pan_number=VALID_PAN_2),
        ip_address="10.0.0.1",
    )
    assert updated.pan_number_masked.endswith(VALID_PAN_2[-5:])

    # Freely re-editable — no lock, per the agreed decision.
    updated_again = service.update_own_profile(
        seeded_users["alice"].id,
        EmployeeProfileSelfUpdate(pan_number=VALID_PAN),
        ip_address="10.0.0.1",
    )
    assert updated_again.pan_number_masked.endswith(VALID_PAN[-5:])

    # Every PAN change must appear in audit_logs with the actual value redacted.
    audit_rows = db_session.execute(
        select(AuditLog).where(AuditLog.table_name == "employee_profiles", AuditLog.operation == "UPDATE")
    ).scalars().all()
    assert len(audit_rows) == 2
    for row in audit_rows:
        assert row.after_data["pan_number"] == "***CHANGED***"
        assert VALID_PAN not in str(row.after_data)
        assert VALID_PAN_2 not in str(row.after_data)


def test_self_update_cannot_change_department_or_full_name(db_session: Session, seeded_users):
    """EmployeeProfileSelfUpdate simply has no such fields — this test pins that
    contract so a future change can't accidentally widen self-service scope."""
    assert not hasattr(EmployeeProfileSelfUpdate(), "department_id")
    assert not hasattr(EmployeeProfileSelfUpdate(), "full_name")


def test_admin_update_can_change_department(db_session: Session, seeded_users):
    dept_service = DepartmentService(db_session)
    department = dept_service.create_department(
        DepartmentCreate(name="Engineering"), actor_id=seeded_users["bob"].id, ip_address=None
    )

    profile_service = EmployeeProfileService(db_session)
    created = profile_service.admin_create_profile(
        EmployeeProfileAdminCreate(user_id=seeded_users["alice"].id, full_name="Alice Sharma"),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )

    updated = profile_service.admin_update_profile(
        created.id,
        EmployeeProfileAdminUpdate(department_id=department.id, designation="SDE-1"),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )
    assert updated.department_id == department.id
    assert updated.designation == "SDE-1"


def test_list_profiles_filters_by_department(db_session: Session, seeded_users):
    dept_service = DepartmentService(db_session)
    eng = dept_service.create_department(
        DepartmentCreate(name="Engineering"), actor_id=seeded_users["bob"].id, ip_address=None
    )
    sales = dept_service.create_department(
        DepartmentCreate(name="Sales"), actor_id=seeded_users["bob"].id, ip_address=None
    )

    profile_service = EmployeeProfileService(db_session)
    profile_service.admin_create_profile(
        EmployeeProfileAdminCreate(
            user_id=seeded_users["alice"].id, full_name="Alice Sharma", department_id=eng.id
        ),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )
    profile_service.admin_create_profile(
        EmployeeProfileAdminCreate(
            user_id=seeded_users["bob"].id, full_name="Bob Patel", department_id=sales.id
        ),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )

    page = profile_service.list_profiles(page=1, size=10, department_id=eng.id)
    assert page.total == 1
    assert page.items[0].full_name == "Alice Sharma"
