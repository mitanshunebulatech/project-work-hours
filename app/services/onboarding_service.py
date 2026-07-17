"""
app/services/onboarding_service.py

PM item 7's single combined workflow: create User, generate a secure
temporary password, assign role + department, create EmployeeProfile,
send the welcome email — one transaction, one entry point. Composes
UserRepository and EmployeeProfileRepository directly (not
UserService/EmployeeProfileService, which each commit independently)
since User + EmployeeProfile must land in the *same* transaction — a
failure partway through must never leave an orphaned User with no
profile, or a profile pointing at a rolled-back user_id.
"""

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.employee_profile_repo import EmployeeProfileRepository
from app.db.repositories.role_repo import RoleRepository
from app.db.repositories.user_repo import UserRepository
from app.models.employee_profile import EmployeeProfile
from app.models.user import User
from app.schemas.onboarding import EmployeeOnboardingRequest, EmployeeOnboardingResponse
from app.services.email_service import EmailService
from app.core.config import settings
from app.utils.password_generator import generate_temp_password

logger = logging.getLogger(__name__)


def _generate_username(first_name: str, last_name: str | None, email: str) -> str:
    """Best-effort readable username derived from the name; uniqueness is
    enforced by the caller appending a numeric suffix on collision."""
    base = f"{first_name}.{last_name}" if last_name else first_name
    base = base.lower().replace(" ", "")
    base = "".join(c for c in base if c.isalnum() or c == ".")
    return base or email.split("@")[0]


class OnboardingService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.profile_repo = EmployeeProfileRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = AuditRepository(db)
        self.email_service = EmailService()

    def onboard_employee(
        self, payload: EmployeeOnboardingRequest, *, actor_id: int, ip_address: str | None
    ) -> EmployeeOnboardingResponse:
        if self.user_repo.get_by_email(payload.email):
            raise ConflictError("A user with this email already exists")

        role = self.role_repo.get(payload.role_id)
        if role is None:
            raise NotFoundError("Selected role does not exist")

        base_username = _generate_username(payload.first_name, payload.last_name, payload.email)
        username = base_username
        suffix = 1
        while self.user_repo.get_by_username(username):
            suffix += 1
            username = f"{base_username}{suffix}"

        temp_password = generate_temp_password()

        # Legacy `role` string still drives is_admin/JWT claims (see
        # app/models/user.py's own comment: "migrating fully to role_id-based
        # permission checks is a later sprint, not this one") — derived from
        # whether the assigned functional role is the seeded system "Admin"
        # role, so onboarding into a custom non-admin role never accidentally
        # grants legacy admin fallback access.
        legacy_role = "admin" if role.name.lower() == "admin" else "employee"

        user = User(
            username=username,
            email=payload.email,
            password_hash=hash_password(temp_password),
            role=legacy_role,
            role_id=role.id,
            must_change_password=True,
        )
        created_user = self.user_repo.create(user)

        employee_code = self.profile_repo.generate_next_employee_code()
        profile = EmployeeProfile(
            user_id=created_user.id,
            department_id=payload.department_id,
            employee_code=employee_code,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.birth_date,
            date_of_joining=payload.joining_date,
            phone_number=payload.personal_phone_number,
            emergency_contact_phone=payload.emergency_phone_number,
            present_address=payload.present_address,
            designation=payload.designation,
            years_of_experience=payload.years_of_experience,
            pan_number=payload.pan_number,
        )
        created_profile = self.profile_repo.create(profile)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="users",
            operation="INSERT",
            record_id=created_user.id,
            after_data={
                "username": created_user.username,
                "email": created_user.email,
                "role_id": role.id,
                "onboarded": True,
            },
            ip_address=ip_address,
        )
        self.audit_repo.log(
            actor_id=actor_id,
            table_name="employee_profiles",
            operation="INSERT",
            record_id=created_profile.id,
            after_data={
                "user_id": created_user.id,
                "employee_code": employee_code,
                "department_id": payload.department_id,
            },
            ip_address=ip_address,
        )
        # Single commit for User + EmployeeProfile + both audit rows — if
        # anything above raised, nothing here has touched the DB yet.
        self.db.commit()

        full_name = f"{payload.first_name} {payload.last_name}" if payload.last_name else payload.first_name
        email_sent = self.email_service.send_onboarding_welcome(
            to_address=created_user.email,
            full_name=full_name,
            username=created_user.username,
            employee_code=employee_code,
            temp_password=temp_password,
            login_url=settings.FRONTEND_BASE_URL,
        )
        if not email_sent:
            logger.warning(
                "Onboarding email did not send for user_id=%s (SMTP not configured or a send "
                "failure) — account was still created; admin should hand over credentials manually.",
                created_user.id,
            )

        return EmployeeOnboardingResponse(
            user_id=created_user.id,
            employee_profile_id=created_profile.id,
            username=created_user.username,
            email=created_user.email,
            employee_code=employee_code,
            email_sent=email_sent,
        )
