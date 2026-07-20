"""
app/api/v1/endpoints/leave_plans.py

PM req #6 (Leave Planning). Separate router from leave_requests.py by
design: LeavePlan is deliberately uncoupled from LeaveRequest (see
app/models/leave_plan.py and LeavePlanService docstrings) — informational
year-ahead intent, no approval workflow, no ledger impact. Keeping the
routes separate mirrors that separation at the model/service layers.

No dedicated leave_plans:* permission code exists yet (unlike holidays or
leave_requests, which got fine-grained codes in earlier migrations).
Assumption: admin-vs-employee scoping here uses current_user.role == "admin"
directly, the same coarse check require_any_role/require_admin are built
on, rather than adding a new permission code — that would mean a new
migration seeding it into roles/permissions tables, which is out of scope
for this stage. Flagging this so it can be revisited if finer-grained
control (e.g. a "leave_plans:view_all" separate from full admin) is
wanted later.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.leave_plan import LeavePlanCreate, LeavePlanResponse, LeavePlanUpdate
from app.services.leave_plan_service import LeavePlanService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/leave-plans", tags=["Leave Plans"])


@router.get("", response_model=PaginatedResponse[LeavePlanResponse])
def list_plans(
    pagination: PageParams = Depends(),
    employee_id: int | None = None,
    year: int | None = None,
    leave_type_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[LeavePlanResponse]:
    """Employees always see only their own plans (employee_id is forced to
    their own id, same pattern as GET /leave-requests) — admins can pass
    employee_id to filter, or omit it to see everyone's."""
    return LeavePlanService(db).list_plans(
        requesting_user_id=current_user.id,
        is_admin=current_user.role == "admin",
        employee_id=employee_id,
        year=year,
        leave_type_id=leave_type_id,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/{plan_id}", response_model=LeavePlanResponse)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeavePlanResponse:
    return LeavePlanService(db).get_plan(
        plan_id, requesting_user_id=current_user.id, is_admin=current_user.role == "admin"
    )


@router.post("", response_model=LeavePlanResponse, status_code=201)
def create_plan(
    payload: LeavePlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeavePlanResponse:
    return LeavePlanService(db).create_plan(
        payload, employee_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.patch("/{plan_id}", response_model=LeavePlanResponse)
def update_plan(
    plan_id: int,
    payload: LeavePlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeavePlanResponse:
    return LeavePlanService(db).update_plan(
        plan_id,
        payload,
        requesting_user_id=current_user.id,
        is_admin=current_user.role == "admin",
        ip_address=get_client_ip(request),
    )


@router.delete("/{plan_id}", response_model=MessageResponse)
def delete_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    LeavePlanService(db).delete_plan(
        plan_id,
        requesting_user_id=current_user.id,
        is_admin=current_user.role == "admin",
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Leave plan deleted")
