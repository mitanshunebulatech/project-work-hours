"""
app/api/v1/endpoints/leave_ledger.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave_ledger import (
    AnnualGrantRunResponse,
    LedgerAdjustmentCreate,
    LedgerAdjustmentResponse,
    LeaveLedgerEntryResponse,
)
from app.services.annual_grant_service import AnnualGrantService
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


@router.post("/annual-grant/run", response_model=AnnualGrantRunResponse)
def run_annual_grant(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AnnualGrantRunResponse:
    """
    Manual trigger for the automatic yearly grant (Task 19). Same underlying
    logic that fires automatically every Jan 1 via APScheduler — exposed here
    so it can be tested or re-run off-cycle without waiting for New Year's.
    Idempotent: re-running for a year already processed skips employees who
    already have an annual_grant entry for that year/type.
    """
    result = AnnualGrantService(db).run(year=year)
    return AnnualGrantRunResponse(**result)


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
