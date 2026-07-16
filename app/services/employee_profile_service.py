"""
app/services/employee_profile_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.employee_profile_repo import EmployeeProfileRepository
from app.models.employee_profile import EmployeeProfile
from app.schemas.common import PaginatedResponse
from app.schemas.employee_profile import (
    EmployeeProfileAdminCreate,
    EmployeeProfileAdminUpdate,
    EmployeeProfileResponse,
    EmployeeProfileSelfUpdate,
)
from app.utils.name_utils import split_full_name

# Fields where the *value itself* must never be written into audit_logs
# (before_data/after_data are stored as JSON and would otherwise persist a
# second, unencrypted copy of a sensitive government ID). Every other field
# audits its real before/after value, same as UserService/DepartmentService.
_REDACTED_AUDIT_FIELDS = {"pan_number"}


def _redact(field: str, value: object) -> object:
    return "***CHANGED***" if field in _REDACTED_AUDIT_FIELDS and value is not None else value


class EmployeeProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.profile_repo = EmployeeProfileRepository(db)
        self.audit_repo = AuditRepository(db)

    # ---- Self-service (own profile) ----

    def get_own_profile(self, user_id: int) -> EmployeeProfile | None:
        """Returns None (not an error) when no profile exists yet — the caller
        (profile.py) merges this into /profile/me, where "no profile row yet"
        is a normal, expected state for a user HR hasn't onboarded."""
        return self.profile_repo.get_by_user_id(user_id)

    def update_own_profile(
        self, user_id: int, payload: EmployeeProfileSelfUpdate, *, ip_address: str | None
    ) -> EmployeeProfileResponse:
        profile = self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError(
                "No employee profile exists yet for this account — ask an admin to create one first"
            )

        before = {
            "phone_number": profile.phone_number,
            "date_of_birth": str(profile.date_of_birth) if profile.date_of_birth else None,
            "pan_number": _redact("pan_number", profile.pan_number),
        }

        if payload.phone_number is not None:
            profile.phone_number = payload.phone_number
        if payload.date_of_birth is not None:
            profile.date_of_birth = payload.date_of_birth
        if payload.pan_number is not None:
            profile.pan_number = payload.pan_number

        updated = self.profile_repo.update(profile)

        self.audit_repo.log(
            actor_id=user_id,
            table_name="employee_profiles",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "phone_number": updated.phone_number,
                "date_of_birth": str(updated.date_of_birth) if updated.date_of_birth else None,
                "pan_number": _redact("pan_number", updated.pan_number) if payload.pan_number else before["pan_number"],
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return EmployeeProfileResponse.from_model(updated)

    # ---- Admin management ----

    def list_profiles(
        self, *, page: int, size: int, department_id: int | None
    ) -> PaginatedResponse[EmployeeProfileResponse]:
        items, total = self.profile_repo.search(
            department_id=department_id, limit=size, offset=(page - 1) * size
        )
        return PaginatedResponse(
            items=[EmployeeProfileResponse.from_model(p) for p in items], total=total, page=page, size=size
        )

    def get_profile(self, profile_id: int) -> EmployeeProfileResponse:
        profile = self.profile_repo.get(profile_id)
        if profile is None:
            raise NotFoundError("Employee profile not found")
        return EmployeeProfileResponse.from_model(profile)

    def admin_create_profile(
        self, payload: EmployeeProfileAdminCreate, *, actor_id: int, ip_address: str | None
    ) -> EmployeeProfileResponse:
        if self.profile_repo.get_by_user_id(payload.user_id):
            raise ConflictError("An employee profile already exists for this user")

        first_name, last_name = split_full_name(payload.full_name)
        profile = EmployeeProfile(
            user_id=payload.user_id,
            employee_code=self.profile_repo.generate_next_employee_code(),
            department_id=payload.department_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=payload.date_of_birth,
            date_of_joining=payload.date_of_joining,
            phone_number=payload.phone_number,
            designation=payload.designation,
            pan_number=payload.pan_number,
        )
        created = self.profile_repo.create(profile)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="employee_profiles",
            operation="INSERT",
            record_id=created.id,
            after_data={
                "user_id": created.user_id,
                "employee_code": created.employee_code,
                "full_name": created.full_name,
                "department_id": created.department_id,
                "pan_number": _redact("pan_number", created.pan_number),
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return EmployeeProfileResponse.from_model(created)

    def admin_update_profile(
        self, profile_id: int, payload: EmployeeProfileAdminUpdate, *, actor_id: int, ip_address: str | None
    ) -> EmployeeProfileResponse:
        profile = self.profile_repo.get(profile_id)
        if profile is None:
            raise NotFoundError("Employee profile not found")

        before = {
            "full_name": profile.full_name,
            "department_id": profile.department_id,
            "designation": profile.designation,
            "pan_number": _redact("pan_number", profile.pan_number),
        }

        if payload.full_name is not None:
            profile.first_name, profile.last_name = split_full_name(payload.full_name)
        if payload.department_id is not None:
            profile.department_id = payload.department_id
        if payload.date_of_birth is not None:
            profile.date_of_birth = payload.date_of_birth
        if payload.date_of_joining is not None:
            profile.date_of_joining = payload.date_of_joining
        if payload.phone_number is not None:
            profile.phone_number = payload.phone_number
        if payload.designation is not None:
            profile.designation = payload.designation
        if payload.pan_number is not None:
            profile.pan_number = payload.pan_number

        updated = self.profile_repo.update(profile)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="employee_profiles",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "full_name": updated.full_name,
                "department_id": updated.department_id,
                "designation": updated.designation,
                "pan_number": _redact("pan_number", updated.pan_number) if payload.pan_number else before["pan_number"],
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return EmployeeProfileResponse.from_model(updated)
