"""
app/api/v1/endpoints/leave_ledger.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave_ledger import (
    LedgerAdjustmentCreate,
    LedgerAdjustmentResponse,
    LeaveLedgerEntryResponse,
)
from app.services.leave_ledger_service import LeaveLedgerService

router = APIRouter(prefix="/leave-ledger", tags=["Leave Ledger"])


@router.post("/adjustments", response_model=LedgerAdjustmentResponse, status_code=201)
def create_adjustment(
    payload: LedgerAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LedgerAdjustmentResponse:
    return LeaveLedgerService(db).create_adjustment(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.get("/{employee_id}", response_model=list[LeaveLedgerEntryResponse])
def list_employee_ledger(
    employee_id: int,
    leave_type_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[LeaveLedgerEntryResponse]:
    return LeaveLedgerService(db).list_for_employee(
        employee_id=employee_id, leave_type_id=leave_type_id, limit=limit, offset=offset
    )
