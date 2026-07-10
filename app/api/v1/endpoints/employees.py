"""
app/api/v1/endpoints/employees.py

Admin-facing employee profile management (viewing/managing OTHER users'
profiles). Self-service (a user's own profile) lives in profile.py instead —
kept separate the same way users.py (admin-only) and profile.py
(self, FR-E08) are already split in this codebase.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.employee_profile import (
    EmployeeProfileAdminCreate,
    EmployeeProfileAdminUpdate,
    EmployeeProfileResponse,
)
from app.services.employee_profile_service import EmployeeProfileService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/employees", tags=["Employees"])


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
