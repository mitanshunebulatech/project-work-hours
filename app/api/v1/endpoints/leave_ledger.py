"""
app/api/v1/endpoints/leave_ledger.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave_ledger import (
    AnnualGrantRunResponse,
    LedgerAdjustmentCreate,
    LedgerAdjustmentResponse,
    LeaveLedgerEntryResponse,
    SetBalanceRequest,
)
from app.services.annual_grant_service import AnnualGrantService
from app.services.leave_ledger_service import LeaveLedgerService

router = APIRouter(prefix="/leave-ledger", tags=["Leave Ledger"])


@router.post("/adjustments", response_model=LedgerAdjustmentResponse, status_code=201)
def create_adjustment(
    payload: LedgerAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave_ledger:manage")),
) -> LedgerAdjustmentResponse:
    return LeaveLedgerService(db).create_adjustment(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.post("/set-balance", response_model=LedgerAdjustmentResponse, status_code=201)
def set_balance(
    payload: SetBalanceRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave_ledger:manage")),
) -> LedgerAdjustmentResponse:
    """
    HRMS V3 Work Leave Balance tab: admin sets an employee's CL/SL/WFH
    balance to an absolute value, any time — a full manual override, not a
    +/- adjustment (that's still /adjustments above, kept for anything that
    prefers a signed delta). Same permission gate, same underlying ledger.
    """
    return LeaveLedgerService(db).set_balance(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.post("/annual-grant/run", response_model=AnnualGrantRunResponse)
def run_annual_grant(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave_ledger:manage")),
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
    current_user: User = Depends(require_permission("leave_ledger:manage")),
) -> list[LeaveLedgerEntryResponse]:
    return LeaveLedgerService(db).list_for_employee(
        employee_id=employee_id, leave_type_id=leave_type_id, limit=limit, offset=offset
    )
