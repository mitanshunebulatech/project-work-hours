"""
app/api/v1/endpoints/employees.py

Admin-facing employee profile management (viewing/managing OTHER users'
profiles). Self-service (a user's own profile) lives in profile.py instead —
kept separate the same way users.py (admin-only) and profile.py
(self, FR-E08) are already split in this codebase.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_permission
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.employee_profile import (
    EmployeeProfileAdminCreate,
    EmployeeProfileAdminUpdate,
    EmployeeProfileResponse,
    IdentityDocumentBrief,
)
from app.schemas.onboarding import EmployeeOnboardingRequest, EmployeeOnboardingResponse
from app.services.employee_profile_service import EmployeeProfileService
from app.services.onboarding_service import OnboardingService
from app.utils.file_storage import resolve_profile_picture_path
from app.utils.pagination import PageParams

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "/onboard",
    response_model=EmployeeOnboardingResponse,
    status_code=201,
    dependencies=[Depends(require_permission("employees:manage"))],
)
def onboard_employee(
    payload: EmployeeOnboardingRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:manage")),
) -> EmployeeOnboardingResponse:
    """
    PM item 7: the single combined onboarding workflow — creates the User
    account, generates a secure temporary password, assigns role +
    department, creates the EmployeeProfile, and sends the welcome email —
    all from one request. See app/services/onboarding_service.py for why
    this composes repositories directly rather than the separately-
    committing UserService/EmployeeProfileService.
    """
    return OnboardingService(db).onboard_employee(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.get(
    "",
    response_model=PaginatedResponse[EmployeeProfileResponse],
    dependencies=[Depends(require_permission("employees:view"))],
)
def list_employees(
    pagination: PageParams = Depends(),
    department_id: int | None = None,
    db: Session = Depends(get_db),
) -> PaginatedResponse[EmployeeProfileResponse]:
    return EmployeeProfileService(db).list_profiles(
        page=pagination.page, size=pagination.size, department_id=department_id
    )


@router.get(
    "/{profile_id}",
    response_model=EmployeeProfileResponse,
    dependencies=[Depends(require_permission("employees:view"))],
)
def get_employee(
    profile_id: int,
    db: Session = Depends(get_db),
) -> EmployeeProfileResponse:
    return EmployeeProfileService(db).get_profile(profile_id)


@router.post(
    "",
    response_model=EmployeeProfileResponse,
    status_code=201,
    dependencies=[Depends(require_permission("employees:manage"))],
)
def create_employee_profile(
    payload: EmployeeProfileAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:manage")),
) -> EmployeeProfileResponse:
    return EmployeeProfileService(db).admin_create_profile(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.patch(
    "/{profile_id}",
    response_model=EmployeeProfileResponse,
    dependencies=[Depends(require_permission("employees:manage"))],
)
def update_employee_profile(
    profile_id: int,
    payload: EmployeeProfileAdminUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:manage")),
) -> EmployeeProfileResponse:
    return EmployeeProfileService(db).admin_update_profile(
        profile_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.get(
    "/{profile_id}/identity-documents",
    response_model=list[IdentityDocumentBrief],
    dependencies=[Depends(require_permission("employees:manage"))],
)
def list_identity_documents(
    profile_id: int,
    db: Session = Depends(get_db),
) -> list[IdentityDocumentBrief]:
    """
    View-only for HR/admin oversight (e.g. confirming an employee has
    submitted required documents). Upload and delete are deliberately
    NOT here — identity documents are employee self-service only (see
    POST/GET/DELETE /profile/me/identity-documents in profile.py). An
    admin uploading on someone else's behalf would undermine the whole
    point of these being the employee's own identity verification.
    """
    return EmployeeProfileService(db).list_identity_documents(profile_id)


@router.get(
    "/{profile_id}/picture",
    dependencies=[Depends(require_permission("employees:manage"))],
)
def get_employee_picture(
    profile_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Admin, view-only counterpart to GET /profile/me/picture — HR oversight
    (e.g. confirming a picture was actually uploaded), not an upload
    endpoint. Uploading on an employee's behalf isn't offered here, same
    reasoning as list_identity_documents above: profile picture is
    employee self-service (see profile.py's POST /me/picture).
    """
    service = EmployeeProfileService(db)
    profile = service.profile_repo.get(profile_id)
    if profile is None or not profile.profile_picture_path:
        raise NotFoundError("No profile picture set for this employee")
    file_path = resolve_profile_picture_path(profile.profile_picture_path)
    if not file_path.exists():
        raise NotFoundError("Profile picture file not found")
    return FileResponse(file_path)
