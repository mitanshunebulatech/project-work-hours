"""
app/api/v1/endpoints/leave_requests.py
"""

from datetime import date

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_any_role, require_permission, user_permission_codes
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.leave_request import (
    AttachmentUploadResponse,
    BulkApproveRequest,
    BulkApproveResponse,
    BulkApproveResultItem,
    LeaveCalendarEntryResponse,
    LeavePreviewRequest,
    LeavePreviewResponse,
    LeaveRejectRequest,
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveStatisticsResponse,
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


@router.post(
    "/attachments", response_model=AttachmentUploadResponse, dependencies=[Depends(require_any_role)]
)
def upload_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AttachmentUploadResponse:
    """
    Standalone upload step — call this first, then pass the returned
    attachment_path into POST /leave-requests. Kept separate from
    create_request (which stays plain JSON) rather than making the whole
    submission endpoint multipart.
    """
    attachment_path = LeaveService(db).upload_attachment(file)
    return AttachmentUploadResponse(attachment_path=attachment_path)


@router.get("/{request_id}/attachment")
def download_attachment(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Only the request's own employee or someone with leave_requests:view_all may fetch the file — never a public URL."""
    file_path = LeaveService(db).get_attachment_path(
        request_id=request_id,
        requesting_user_id=current_user.id,
        is_admin="leave_requests:view_all" in user_permission_codes(current_user),
    )
    return FileResponse(file_path)


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
    can_view_all = "leave_requests:view_all" in user_permission_codes(current_user)
    effective_employee_id = employee_id if can_view_all else current_user.id
    items, total = service.leave_request_repo.search(
        employee_id=effective_employee_id,
        status=status,
        leave_type_id=leave_type_id,
        date_from=date_from,
        date_to=date_to,
        search=search if can_view_all else None,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[LeaveRequestResponse.model_validate(r) for r in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get(
    "/pending",
    response_model=PaginatedResponse[LeaveRequestResponse],
    dependencies=[Depends(require_permission("leave_requests:approve"))],
)
def list_pending(
    pagination: PageParams = Depends(),
    leave_type_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> PaginatedResponse[LeaveRequestResponse]:
    """Approval-queue triage — latest-first (PM req #3, Leave Approval Module).
    Was oldest-first triage-order originally; product direction changed to
    latest-first so newly-submitted requests surface at the top. The repo's
    search() already defaults to newest-first when oldest_first is omitted,
    so this only required dropping the explicit override below.
    Gated on leave_requests:approve (not view_all): this is a to-do list for
    whoever approves leave, not a general reporting view."""
    service = LeaveService(db)
    items, total = service.leave_request_repo.search(
        status="pending",
        leave_type_id=leave_type_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[LeaveRequestResponse.model_validate(r) for r in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get(
    "/employee/{employee_id}",
    response_model=PaginatedResponse[LeaveRequestResponse],
    dependencies=[Depends(require_permission("leave_requests:view_all"))],
)
def employee_history(
    employee_id: int,
    pagination: PageParams = Depends(),
    status: str | None = None,
    db: Session = Depends(get_db),
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
        is_admin="leave_requests:approve" in user_permission_codes(current_user),
        ip_address=get_client_ip(request),
    )
    return LeaveRequestResponse.model_validate(cancelled)


@router.post("/{request_id}/approve", response_model=LeaveRequestResponse)
def approve_request(
    request_id: int,
    request: Request,
    admin_comment: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave_requests:approve")),
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
    current_user: User = Depends(require_permission("leave_requests:approve")),
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
    current_user: User = Depends(require_permission("leave_requests:approve")),
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


@router.get("/calendar", response_model=list[LeaveCalendarEntryResponse])
def calendar(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LeaveCalendarEntryResponse]:
    """
    Approved-only, org-wide. Deliberately visible to any authenticated user
    (not admin-only) — an employee's pending request never appears here
    (see LeaveRequestRepository.get_calendar_entries' status filter), so
    there's no privacy leak in showing who's confirmed to be out.
    """
    entries = LeaveService(db).get_calendar(month=month, year=year)
    return [
        LeaveCalendarEntryResponse(
            employee_username=e.employee.username,
            leave_type_code=e.leave_type.code,
            leave_type_display_name=e.leave_type.display_name,
            start_date=e.start_date,
            end_date=e.end_date,
        )
        for e in entries
    ]


@router.get(
    "/statistics",
    response_model=LeaveStatisticsResponse,
    dependencies=[Depends(require_permission("leave_requests:view_all"))],
)
def statistics(
    date_from: date | None = None,
    date_to: date | None = None,
    leave_type_id: int | None = None,
    db: Session = Depends(get_db),
) -> LeaveStatisticsResponse:
    data = LeaveService(db).get_statistics(
        date_from=date_from, date_to=date_to, leave_type_id=leave_type_id
    )
    return LeaveStatisticsResponse(**data)


@router.get("/export", dependencies=[Depends(require_permission("leave_requests:view_all"))])
def export_csv(
    status: str | None = None,
    leave_type_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    csv_content = LeaveService(db).export_requests_csv(
        status=status, leave_type_id=leave_type_id, date_from=date_from, date_to=date_to
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leave_requests_export.csv"},
    )
