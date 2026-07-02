"""
app/api/v1/endpoints/entries.py
"""

from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.entry import (
    RejectRequest,
    WorkEntryCreate,
    WorkEntryResponse,
    WorkEntryUpdate,
)
from app.services.entry_service import EntryService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/entries", tags=["Work Entries"])


@router.get("", response_model=PaginatedResponse[WorkEntryResponse])
def list_entries(
    pagination: PageParams = Depends(),
    employee_id: int | None = None,
    project_id: int | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[WorkEntryResponse]:
    return EntryService(db).list_entries(
        current_user=current_user,
        page=pagination.page,
        size=pagination.size,
        employee_id=employee_id,
        project_id=project_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.post("", response_model=WorkEntryResponse, status_code=201)
def create_entry(
    payload: WorkEntryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkEntryResponse:
    return EntryService(db).create_entry(
        payload, current_user=current_user, ip_address=get_client_ip(request)
    )


@router.patch("/{entry_id}", response_model=WorkEntryResponse)
def update_entry(
    entry_id: int,
    payload: WorkEntryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkEntryResponse:
    return EntryService(db).update_entry(
        entry_id, payload, current_user=current_user, ip_address=get_client_ip(request)
    )


@router.delete("/{entry_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def delete_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> MessageResponse:
    EntryService(db).delete_entry(entry_id, current_user=current_user, ip_address=get_client_ip(request))
    return MessageResponse(message="Entry deleted")


@router.post("/{entry_id}/approve", response_model=WorkEntryResponse, dependencies=[Depends(require_admin)])
def approve_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> WorkEntryResponse:
    return EntryService(db).approve_entry(
        entry_id, current_user=current_user, ip_address=get_client_ip(request)
    )


@router.post("/{entry_id}/reject", response_model=WorkEntryResponse, dependencies=[Depends(require_admin)])
def reject_entry(
    entry_id: int,
    payload: RejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> WorkEntryResponse:
    return EntryService(db).reject_entry(
        entry_id, payload.reason, current_user=current_user, ip_address=get_client_ip(request)
    )
