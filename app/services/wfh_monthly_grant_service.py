"""
app/services/wfh_monthly_grant_service.py

PM decision (confirmed explicitly): WFH auto-credits 2 days/month with no
admin action needed — not a manual set_balance() call like CL/SL/Birthday.
Deliberately a separate service from AnnualGrantService rather than a
generalization of it — genuinely different cadence (monthly vs annual)
and reset semantics (resets every month, confirmed: unused days do NOT
carry forward), and this codebase's own convention favors additive
services over rewriting a working one.

"Resets every month" here means this service ONLY credits
monthly_quota_days each month — it does not zero out any unused balance
from the prior month. remaining_days is a running total the same way it
is for every other leave type in this table; if an employee doesn't use
last month's 2 days, they'd still show extra remaining_days this month
unless something separately debits it back down. Flagging this as a known
limitation rather than quietly solving it: enforcing a true reset
(zeroing unused days at the month boundary) is a separate, larger
decision that changes what "remaining_days" means for WFH specifically
vs every other type sharing this table, and hasn't been asked for
explicitly — this service only adds the credit, it does not zero
anything out.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories.leave_ledger_repo import LeaveLedgerRepository
from app.db.repositories.leave_policy_repo import LeavePolicyRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.leave_ledger import LedgerAdjustmentCreate, LedgerTransactionType
from app.services.leave_ledger_service import LeaveLedgerService

WFH_LEAVE_TYPE_CODE = "WFH"


class WfhMonthlyGrantService:
    def __init__(self, db: Session):
        self.db = db
        self.leave_type_repo = LeaveTypeRepository(db)
        self.leave_policy_repo = LeavePolicyRepository(db)
        self.user_repo = UserRepository(db)
        self.ledger_repo = LeaveLedgerRepository(db)
        self.ledger_service = LeaveLedgerService(db)

    def run(self, *, year: int, month: int) -> dict:
        granted = 0
        skipped = 0
        errors: list[str] = []

        wfh_type = next(
            (t for t in self.leave_type_repo.list_active() if t.code == WFH_LEAVE_TYPE_CODE), None
        )
        if wfh_type is None:
            return {
                "year": year, "month": month, "granted": 0, "skipped": 0,
                "errors": ["WFH leave type not found or inactive"],
            }

        policy = self.leave_policy_repo.get_for_type_year(leave_type_id=wfh_type.id, year=year)
        if policy is None or policy.monthly_quota_days is None:
            return {
                "year": year, "month": month, "granted": 0, "skipped": 0,
                "errors": ["No WFH policy or monthly_quota_days for this year"],
            }

        active_employees, _ = self.user_repo.search(is_active=True, limit=10000, offset=0)

        for employee in active_employees:
            already_granted = self.ledger_repo.has_monthly_grant_for_month(
                employee_id=employee.id, leave_type_id=wfh_type.id, year=year, month=month
            )
            if already_granted:
                skipped += 1
                continue

            try:
                self.ledger_service.create_adjustment(
                    LedgerAdjustmentCreate(
                        employee_id=employee.id,
                        leave_type_id=wfh_type.id,
                        year=year,
                        amount_days=policy.monthly_quota_days,
                        transaction_type=LedgerTransactionType.MONTHLY_GRANT,
                        reason=f"Automatic WFH monthly grant for {date(year, month, 1):%B %Y}",
                    ),
                    actor_id=None,
                    ip_address=None,
                )
                granted += 1
            except Exception as exc:  # noqa: BLE001 — one employee's failure shouldn't halt the run
                errors.append(f"employee_id={employee.id}: {exc}")

        return {"year": year, "month": month, "granted": granted, "skipped": skipped, "errors": errors}
