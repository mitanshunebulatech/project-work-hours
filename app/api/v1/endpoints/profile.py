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

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.employee_profile import EmployeeProfileSelfUpdate, MyProfileResponse
from app.services.employee_profile_service import EmployeeProfileService

router = APIRouter(prefix="/profile", tags=["Profile"])


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
