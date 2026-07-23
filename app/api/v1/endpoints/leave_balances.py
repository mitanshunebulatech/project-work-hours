"""
app/api/v1/endpoints/leave_balances.py
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.db.repositories.leave_balance_repo import LeaveBalanceRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave_balance import LeaveBalanceResponse

router = APIRouter(prefix="/leave-balances", tags=["Leave Balances"])


def _balances_for_employee(db: Session, employee_id: int, year: int) -> list[LeaveBalanceResponse]:
    """
    Shows one row per active, paid leave type — HRMS V3: this used to skip
    any type with no LeavePolicy row for the year, which meant WFH (paid,
    but intentionally policy-less per migration 0013) could never appear in
    an employee's or admin's balance view at all. Now that CL/SL/WFH are all
    admin-managed via LeaveLedgerService.set_balance() rather than tied to
    an annual policy grant, "has a policy row" is no longer the right test
    for "should this show up" — is_paid alone is (LOP stays excluded since
    it's unpaid/unlimited by design, matching "LOP has no limits").
    Provisions a zero-balance row on the fly for any type the employee has
    never touched yet, via the same get_or_create_for_year() used everywhere
    else, so the view shows "0 remaining" rather than omitting the type.
    """
    type_repo = LeaveTypeRepository(db)
    balance_repo = LeaveBalanceRepository(db)

    results: list[LeaveBalanceResponse] = []
    for leave_type in type_repo.list_active():
        if not leave_type.is_paid:
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
    dependencies=[Depends(require_permission("leave_balances:view_all"))],
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
