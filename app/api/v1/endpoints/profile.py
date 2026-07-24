"""
app/api/v1/endpoints/profile.py
Separate from users.py because users.py is admin-only at the router level (FR-A06).
This satisfies FR-E08: any authenticated user can view their own profile.

Sprint 2: GET /profile/me now merges in EmployeeProfile fields (department,
designation, masked PAN, etc.) when a profile row exists for this user —
absence of a profile is a normal state (HR hasn't onboarded them into the
new schema yet), not an error. PATCH /profile/me lets the employee edit
their own self-service fields (phone_number, date_of_birth, pan_number);
org-managed fields (department, designation, full_name) stay admin-only,
via app/api/v1/endpoints/employees.py.
"""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.models.user import User
from app.schemas.employee_profile import (
    ALLOWED_DOCUMENT_TYPES,
    EmployeeProfileSelfUpdate,
    IdentityDocumentBrief,
    MyProfileResponse,
)
from app.services.employee_profile_service import EmployeeProfileService
from app.services.user_preferences_service import UserPreferencesService
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.utils.file_storage import resolve_profile_picture_path

router = APIRouter(prefix="/profile", tags=["Profile"])


def _own_profile_id_or_404(service: EmployeeProfileService, user_id: int) -> int:
    profile = service.get_own_profile(user_id)
    if profile is None:
        raise NotFoundError(
            "No employee profile exists yet for this account — ask an admin to create one first"
        )
    return profile.id


@router.get("/me", response_model=MyProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MyProfileResponse:
    profile = EmployeeProfileService(db).get_own_profile(current_user.id)
    return MyProfileResponse.build(current_user, profile)


@router.patch("/me", response_model=MyProfileResponse)
def update_my_profile(
    payload: EmployeeProfileSelfUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MyProfileResponse:
    EmployeeProfileService(db).update_own_profile(
        current_user.id, payload, ip_address=get_client_ip(request)
    )
    # Re-fetch so the response reflects the freshly-committed row.
    profile = EmployeeProfileService(db).get_own_profile(current_user.id)
    return MyProfileResponse.build(current_user, profile)


@router.get("/me/preferences", response_model=UserPreferencesResponse)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPreferencesResponse:
    return UserPreferencesService(db).get_preferences(current_user)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
def update_my_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPreferencesResponse:
    return UserPreferencesService(db).update_preferences(current_user, payload)


@router.post("/me/picture", response_model=MyProfileResponse)
def update_my_profile_picture(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MyProfileResponse:
    """PM item 10: Profile Picture is employee-uploadable (per decision).
    Requires a profile row to already exist — same "no profile yet" guard
    as update_my_profile above."""
    service = EmployeeProfileService(db)
    profile = service.get_own_profile(current_user.id)
    if profile is None:
        raise NotFoundError(
            "No employee profile exists yet for this account — ask an admin to create one first"
        )
    service.set_profile_picture(
        profile.id, file=file, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    updated_profile = service.get_own_profile(current_user.id)
    return MyProfileResponse.build(current_user, updated_profile)


@router.get("/me/picture")
def get_my_profile_picture(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Serves the raw image file. The upload endpoint above stores
    profile_picture_path on the row, but nothing served it back — an
    <img src=...> would have had nowhere valid to point without this.
    Self-only, same scoping as the upload endpoint; see
    app/api/v1/endpoints/employees.py's get_employee_picture for the
    admin view-only counterpart (mirrors the identity-documents split).
    """
    service = EmployeeProfileService(db)
    profile = service.get_own_profile(current_user.id)
    if profile is None or not profile.profile_picture_path:
        raise NotFoundError("No profile picture set")
    file_path = resolve_profile_picture_path(profile.profile_picture_path)
    if not file_path.exists():
        raise NotFoundError("Profile picture file not found")
    return FileResponse(file_path)


@router.post("/me/identity-documents", response_model=IdentityDocumentBrief, status_code=201)
def upload_my_identity_document(
    request: Request,
    # Form(...), not plain str — these ride alongside file: UploadFile in the
    # same multipart request, so FastAPI requires every field to be declared
    # as Form()/File() or it silently treats document_type/document_number as
    # query params instead of body fields (a real bug caught in the earlier
    # admin-only version of this endpoint; fixed here from the start).
    document_type: str = Form(...),
    document_number: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IdentityDocumentBrief:
    """
    PM item 6/7 (per decision): identity documents are employee
    self-service only — the employee uploads their own Aadhaar/PAN/
    Passport/Other scan after onboarding, an admin never uploads on
    their behalf (see app/api/v1/endpoints/employees.py's
    list_identity_documents for the admin's view-only counterpart).
    """
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValidationError(
            f"Invalid document_type '{document_type}'. Must be one of: "
            f"{', '.join(sorted(ALLOWED_DOCUMENT_TYPES))}"
        )
    service = EmployeeProfileService(db)
    profile_id = _own_profile_id_or_404(service, current_user.id)
    return service.upload_identity_document(
        profile_id,
        document_type=document_type,
        document_number=document_number,
        file=file,
        actor_id=current_user.id,
        ip_address=get_client_ip(request),
    )


@router.get("/me/identity-documents", response_model=list[IdentityDocumentBrief])
def list_my_identity_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IdentityDocumentBrief]:
    service = EmployeeProfileService(db)
    profile_id = _own_profile_id_or_404(service, current_user.id)
    return service.list_identity_documents(profile_id)


@router.delete("/me/identity-documents/{document_id}", status_code=204)
def delete_my_identity_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    service = EmployeeProfileService(db)
    profile_id = _own_profile_id_or_404(service, current_user.id)
    service.delete_identity_document(
        profile_id, document_id, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return Response(status_code=204)
