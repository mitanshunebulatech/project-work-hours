"""
app/services/annual_grant_service.py
"""

from sqlalchemy.orm import Session

from app.db.repositories.leave_ledger_repo import LeaveLedgerRepository
from app.db.repositories.leave_policy_repo import LeavePolicyRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.leave_ledger import LedgerAdjustmentCreate, LedgerTransactionType
from app.services.leave_ledger_service import LeaveLedgerService


class AnnualGrantService:
    """
    Grants every active employee their standard policy quota, for every active
    leave type that has a policy for the given year. Leave types with no policy
    row for that year (LOP, WFH — by design, per migration 0013's note) are
    silently skipped, no special-casing needed.

    Reuses LeaveLedgerService.create_adjustment() — the same mechanism the
    manual admin endpoint (Task 18) uses — so automatic grants and manual
    overrides never diverge in logic, only in how they're triggered.
    """

    def __init__(self, db: Session):
        self.db = db
        self.leave_type_repo = LeaveTypeRepository(db)
        self.leave_policy_repo = LeavePolicyRepository(db)
        self.user_repo = UserRepository(db)
        self.ledger_repo = LeaveLedgerRepository(db)
        self.ledger_service = LeaveLedgerService(db)

    def run(self, *, year: int) -> dict:
        granted = 0
        skipped = 0
        errors: list[str] = []

        active_types = self.leave_type_repo.list_active()
        # Large limit: pragmatic for a company-sized employee list (see Task 19
        # future-scalability note — batch this if headcount grows substantially).
        active_employees, _ = self.user_repo.search(is_active=True, limit=10000, offset=0)

        for leave_type in active_types:
            policy = self.leave_policy_repo.get_for_type_year(leave_type_id=leave_type.id, year=year)
            if policy is None:
                # No policy for this type/year (e.g. LOP by design) — nothing to grant.
                continue
            if not policy.auto_grant_enabled:
                # HRMS V3: admin-input leave types (CL/SL/Birthday) and
                # separately-mechanized ones (WFH, monthly not annual) keep
                # their policy row for max_consecutive_days/min_notice_days
                # validation, but this flag is what actually stops
                # AnnualGrantService from also granting them — without
                # this check the column would exist but do nothing.
                continue

            for employee in active_employees:
                already_granted = self.ledger_repo.has_annual_grant_for_year(
                    employee_id=employee.id, leave_type_id=leave_type.id, year=year
                )
                if already_granted:
                    skipped += 1
                    continue

                try:
                    self.ledger_service.create_adjustment(
                        LedgerAdjustmentCreate(
                            employee_id=employee.id,
                            leave_type_id=leave_type.id,
                            year=year,
                            amount_days=policy.annual_quota_days,
                            transaction_type=LedgerTransactionType.ANNUAL_GRANT,
                            reason=f"Automatic annual grant for {year}",
                        ),
                        actor_id=None,
                        ip_address=None,
                    )
                    granted += 1
                except Exception as exc:  # noqa: BLE001 — one employee's failure shouldn't halt the run
                    errors.append(f"employee_id={employee.id} leave_type_id={leave_type.id}: {exc}")

        return {"year": year, "granted": granted, "skipped": skipped, "errors": errors}
