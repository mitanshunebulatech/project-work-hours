"""
app/api/v1/endpoints/employees.py

Admin-facing employee profile management (viewing/managing OTHER users'
profiles). Self-service (a user's own profile) lives in profile.py instead —
kept separate the same way users.py (admin-only) and profile.py
(self, FR-E08) are already split in this codebase.
"""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_permission
from app.core.exceptions import ValidationError
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
from app.utils.pagination import PageParams

# Free string, not a DB enum (see IdentityDocument model) — validated here
# at the API boundary instead.
ALLOWED_DOCUMENT_TYPES = frozenset({"PAN", "AADHAAR", "PASSPORT", "OTHER"})

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


@router.post(
    "/{profile_id}/identity-documents",
    response_model=IdentityDocumentBrief,
    status_code=201,
    dependencies=[Depends(require_permission("employees:manage"))],
)
def upload_identity_document(
    profile_id: int,
    document_type: str,
    request: Request,
    document_number: str | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:manage")),
) -> IdentityDocumentBrief:
    """
    Separate follow-up call after the employee record already exists (per
    decision — matches the existing leave-attachment pattern: create first,
    upload after). document_type accepts PAN/AADHAAR/PASSPORT/OTHER today
    (a free string on the model, not a DB enum, so a 5th type never needs a
    migration) — validated here at the API boundary.
    """
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValidationError(
            f"Invalid document_type '{document_type}'. Must be one of: {', '.join(sorted(ALLOWED_DOCUMENT_TYPES))}"
        )
    return EmployeeProfileService(db).upload_identity_document(
        profile_id,
        document_type=document_type,
        document_number=document_number,
        file=file,
        actor_id=current_user.id,
        ip_address=get_client_ip(request),
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
    return EmployeeProfileService(db).list_identity_documents(profile_id)


@router.delete(
    "/{profile_id}/identity-documents/{document_id}",
    status_code=204,
    dependencies=[Depends(require_permission("employees:manage"))],
)
def delete_identity_document(
    profile_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:manage")),
) -> Response:
    EmployeeProfileService(db).delete_identity_document(
        profile_id, document_id, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return Response(status_code=204)
