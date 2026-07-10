"""
app/api/v1/endpoints/departments.py

Reads (GET) are open to any authenticated user — departments are reference
data used e.g. when filtering/searching employees or leave requests, so
gating reads behind departments:manage would force every employee-facing
screen that shows "Engineering" / "Sales" labels to also carry that
permission. Only mutations (create/update/deactivate) require it.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services.department_service import DepartmentService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=PaginatedResponse[DepartmentResponse])
def list_departments(
    pagination: PageParams = Depends(),
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[DepartmentResponse]:
    return DepartmentService(db).list_departments(
        page=pagination.page, size=pagination.size, is_active=is_active
    )


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=201,
    dependencies=[Depends(require_permission("departments:manage"))],
)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("departments:manage")),
) -> DepartmentResponse:
    return DepartmentService(db).create_department(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
    dependencies=[Depends(require_permission("departments:manage"))],
)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("departments:manage")),
) -> DepartmentResponse:
    return DepartmentService(db).update_department(
        department_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.delete(
    "/{department_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("departments:manage"))],
)
def deactivate_department(
    department_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("departments:manage")),
) -> MessageResponse:
    DepartmentService(db).deactivate_department(
        department_id, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return MessageResponse(message="Department deactivated")
