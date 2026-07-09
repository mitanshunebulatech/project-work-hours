"""
app/api/v1/endpoints/leave_requests.py
"""

from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_admin, require_any_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.leave_request import (
    BulkApproveRequest,
    BulkApproveResponse,
    BulkApproveResultItem,
    LeavePreviewRequest,
    LeavePreviewResponse,
    LeaveRejectRequest,
    LeaveRequestCreate,
    LeaveRequestResponse,
)
from app.services.leave_service import LeaveService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/leave-requests", tags=["Leave Requests"])


@router.post("/preview", response_model=LeavePreviewResponse, dependencies=[Depends(require_any_role)])
def preview_request(
    payload: LeavePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeavePreviewResponse:
    return LeaveService(db).preview_request(employee_id=current_user.id, payload=payload)


@router.post("", response_model=LeaveRequestResponse, status_code=201)
def create_request(
    payload: LeaveRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveRequestResponse:
    created = LeaveService(db).create_request(
        employee_id=current_user.id, payload=payload, ip_address=get_client_ip(request)
    )
    return LeaveRequestResponse.model_validate(created)


@router.get("", response_model=PaginatedResponse[LeaveRequestResponse])
def list_requests(
    pagination: PageParams = Depends(),
    status: str | None = None,
    leave_type_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[LeaveRequestResponse]:
    """
    Employees always see only their own requests (employee_id is forced to
    their own id, any other value is silently ignored) — admins can pass
    employee_id to filter, or omit it to see everyone's.
    """
    service = LeaveService(db)
    effective_employee_id = employee_id if current_user.role == "admin" else current_user.id
    items, total = service.leave_request_repo.search(
        employee_id=effective_employee_id,
        status=status,
        leave_type_id=leave_type_id,
        date_from=date_from,
        date_to=date_to,
        search=search if current_user.role == "admin" else None,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[LeaveRequestResponse.model_validate(r) for r in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/pending", response_model=PaginatedResponse[LeaveRequestResponse])
def list_pending(
    pagination: PageParams = Depends(),
    leave_type_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> PaginatedResponse[LeaveRequestResponse]:
    """Admin triage queue — oldest-pending-first (see LeaveRequestRepository.search's oldest_first)."""
    service = LeaveService(db)
    items, total = service.leave_request_repo.search(
        status="pending",
        leave_type_id=leave_type_id,
        oldest_first=True,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[LeaveRequestResponse.model_validate(r) for r in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/employee/{employee_id}", response_model=PaginatedResponse[LeaveRequestResponse])
def employee_history(
    employee_id: int,
    pagination: PageParams = Depends(),
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> PaginatedResponse[LeaveRequestResponse]:
    service = LeaveService(db)
    items, total = service.leave_request_repo.search(
        employee_id=employee_id,
        status=status,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[LeaveRequestResponse.model_validate(r) for r in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post("/{request_id}/cancel", response_model=LeaveRequestResponse)
def cancel_request(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveRequestResponse:
    cancelled = LeaveService(db).cancel_request(
        request_id=request_id,
        requesting_user_id=current_user.id,
        is_admin=current_user.role == "admin",
        ip_address=get_client_ip(request),
    )
    return LeaveRequestResponse.model_validate(cancelled)


@router.post("/{request_id}/approve", response_model=LeaveRequestResponse)
def approve_request(
    request_id: int,
    request: Request,
    admin_comment: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LeaveRequestResponse:
    approved = LeaveService(db).approve_request(
        request_id=request_id,
        admin_user_id=current_user.id,
        admin_comment=admin_comment,
        ip_address=get_client_ip(request),
    )
    return LeaveRequestResponse.model_validate(approved)


@router.post("/{request_id}/reject", response_model=LeaveRequestResponse)
def reject_request(
    request_id: int,
    payload: LeaveRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LeaveRequestResponse:
    rejected = LeaveService(db).reject_request(
        request_id=request_id,
        admin_user_id=current_user.id,
        admin_comment=payload.admin_comment,
        ip_address=get_client_ip(request),
    )
    return LeaveRequestResponse.model_validate(rejected)


@router.post("/bulk-approve", response_model=BulkApproveResponse)
def bulk_approve(
    payload: BulkApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BulkApproveResponse:
    """
    Best-effort loop: one request's failure (already actioned, self-approval,
    insufficient balance, etc.) doesn't block the rest — each result is
    reported individually so the admin UI can show a per-row outcome.
    """
    service = LeaveService(db)
    results: list[BulkApproveResultItem] = []
    approved_count = 0
    failed_count = 0

    for request_id in payload.request_ids:
        try:
            service.approve_request(
                request_id=request_id,
                admin_user_id=current_user.id,
                admin_comment=payload.admin_comment,
                ip_address=get_client_ip(request),
            )
            results.append(BulkApproveResultItem(request_id=request_id, success=True))
            approved_count += 1
        except Exception as exc:  # noqa: BLE001 — one row's failure must not abort the batch
            results.append(
                BulkApproveResultItem(request_id=request_id, success=False, detail=str(exc))
            )
            failed_count += 1

    return BulkApproveResponse(
        results=results, approved_count=approved_count, failed_count=failed_count
    )
