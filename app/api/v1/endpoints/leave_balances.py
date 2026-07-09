"""
app/api/v1/endpoints/leave_balances.py
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.repositories.leave_balance_repo import LeaveBalanceRepository
from app.db.repositories.leave_policy_repo import LeavePolicyRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave_balance import LeaveBalanceResponse

router = APIRouter(prefix="/leave-balances", tags=["Leave Balances"])


def _balances_for_employee(db: Session, employee_id: int, year: int) -> list[LeaveBalanceResponse]:
    """
    Shows one row per active leave type that actually has a policy for this
    year (LOP and WFH have none by design — see migration 0013 — so they
    never appear here, matching preview_request()'s own is_paid+policy gate).
    Provisions a zero-balance row on the fly for any type the employee has
    never touched yet, via the same get_or_create_for_year() used everywhere
    else, so the dashboard shows "0 remaining" rather than omitting the type.
    """
    type_repo = LeaveTypeRepository(db)
    policy_repo = LeavePolicyRepository(db)
    balance_repo = LeaveBalanceRepository(db)

    results: list[LeaveBalanceResponse] = []
    for leave_type in type_repo.list_active():
        if not leave_type.is_paid:
            continue
        policy = policy_repo.get_for_type_year(leave_type_id=leave_type.id, year=year)
        if policy is None:
            continue

        balance = balance_repo.get_or_create_for_year(
            employee_id=employee_id, leave_type_id=leave_type.id, year=year
        )
        results.append(
            LeaveBalanceResponse(
                leave_type_id=leave_type.id,
                leave_type_code=leave_type.code,
                leave_type_display_name=leave_type.display_name,
                year=year,
                total_credited_days=balance.total_credited_days,
                total_debited_days=balance.total_debited_days,
                remaining_days=balance.remaining_days,
            )
        )
    return results


@router.get("/me", response_model=list[LeaveBalanceResponse])
def my_balances(
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LeaveBalanceResponse]:
    resolved_year = year or date.today().year
    result = _balances_for_employee(db, current_user.id, resolved_year)
    db.commit()  # commits any newly-provisioned zero-balance rows
    return result


@router.get(
    "/employee/{employee_id}",
    response_model=list[LeaveBalanceResponse],
    dependencies=[Depends(require_admin)],
)
def employee_balances(
    employee_id: int,
    year: int | None = None,
    db: Session = Depends(get_db),
) -> list[LeaveBalanceResponse]:
    resolved_year = year or date.today().year
    result = _balances_for_employee(db, employee_id, resolved_year)
    db.commit()
    return result
