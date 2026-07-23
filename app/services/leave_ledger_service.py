"""
app/services/leave_ledger_service.py
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.leave_balance_repo import LeaveBalanceRepository
from app.db.repositories.leave_ledger_repo import LeaveLedgerRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.repositories.user_repo import UserRepository
from app.models.leave_ledger import LeaveLedgerEntry
from app.schemas.leave_ledger import (
    LedgerAdjustmentCreate,
    LedgerAdjustmentResponse,
    LeaveBalanceResponse,
    LeaveLedgerEntryResponse,
    LedgerTransactionType,
    SetBalanceRequest,
)


class LeaveLedgerService:
    def __init__(self, db: Session):
        self.db = db
        self.ledger_repo = LeaveLedgerRepository(db)
        self.balance_repo = LeaveBalanceRepository(db)
        self.user_repo = UserRepository(db)
        self.leave_type_repo = LeaveTypeRepository(db)
        self.audit_repo = AuditRepository(db)

    def create_adjustment(
        self, payload: LedgerAdjustmentCreate, *, actor_id: int | None, ip_address: str | None
    ) -> LedgerAdjustmentResponse:
        employee = self.user_repo.get(payload.employee_id)
        if employee is None or employee.deleted_at is not None:
            raise NotFoundError("Employee not found")

        leave_type = self.leave_type_repo.get(payload.leave_type_id)
        if leave_type is None or not leave_type.is_active:
            raise NotFoundError("Leave type not found or inactive")

        year = payload.year or datetime.now(timezone.utc).year

        entry = LeaveLedgerEntry(
            employee_id=payload.employee_id,
            leave_type_id=payload.leave_type_id,
            transaction_type=payload.transaction_type.value,
            amount_days=payload.amount_days,
            reason=payload.reason,
        )
        created_entry = self.ledger_repo.create(entry)

        balance = self.balance_repo.get_or_create_for_year(
            employee_id=payload.employee_id, leave_type_id=payload.leave_type_id, year=year
        )
        before_balance = {
            "total_credited_days": str(balance.total_credited_days),
            "total_debited_days": str(balance.total_debited_days),
            "remaining_days": str(balance.remaining_days),
        }

        if payload.amount_days > 0:
            updated_balance = self.balance_repo.adjust_balance(balance, credit_delta=payload.amount_days)
        else:
            updated_balance = self.balance_repo.adjust_balance(
                balance, debit_delta=abs(payload.amount_days)
            )

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="leave_ledger",
            operation="INSERT",
            record_id=created_entry.id,
            before_data=before_balance,
            after_data={
                "transaction_type": created_entry.transaction_type,
                "amount_days": str(created_entry.amount_days),
                "remaining_days": str(updated_balance.remaining_days),
            },
            ip_address=ip_address,
        )
        self.db.commit()

        return LedgerAdjustmentResponse(
            ledger_entry=LeaveLedgerEntryResponse.model_validate(created_entry),
            balance=LeaveBalanceResponse.model_validate(updated_balance),
        )

    def set_balance(
        self, payload: SetBalanceRequest, *, actor_id: int, ip_address: str | None
    ) -> LedgerAdjustmentResponse:
        """
        HRMS V3 Work Leave Balance: admin sets a leave type to an absolute
        number, any time — the primary mechanism for CL/SL/Birthday (fully
        admin-manual, no auto-grant). WFH is normally auto-credited monthly
        by WfhMonthlyGrantService instead, but this endpoint still works on
        WFH too for manual corrections (e.g. fixing a missed automatic
        grant) — it's just not how WFH's balance is meant to be set day to
        day. Reads the current balance, computes the signed delta against
        target_days, and writes it through create_adjustment — the exact
        same path every other balance-affecting write already goes through
        (annual grant, monthly grant, leave debit, manual +/- adjustment),
        so this never becomes a second, divergent way of touching a balance.
        A target equal to the current balance is a legitimate no-op (e.g.
        admin re-confirms a number without changing it) — not an error, but
        create_adjustment() rejects a zero amount_days, so that case skips
        the ledger write entirely and just returns the balance as-is.
        """
        employee = self.user_repo.get(payload.employee_id)
        if employee is None or employee.deleted_at is not None:
            raise NotFoundError("Employee not found")

        leave_type = self.leave_type_repo.get(payload.leave_type_id)
        if leave_type is None or not leave_type.is_active:
            raise NotFoundError("Leave type not found or inactive")

        year = payload.year or datetime.now(timezone.utc).year
        current_balance = self.balance_repo.get_or_create_for_year(
            employee_id=payload.employee_id, leave_type_id=payload.leave_type_id, year=year
        )
        delta = payload.target_days - current_balance.remaining_days

        if delta == 0:
            return LedgerAdjustmentResponse(
                ledger_entry=LeaveLedgerEntryResponse(
                    id=0,
                    employee_id=payload.employee_id,
                    leave_type_id=payload.leave_type_id,
                    leave_request_id=None,
                    transaction_type=LedgerTransactionType.ADMIN_ADJUSTMENT.value,
                    amount_days=0,
                    reason="No change — balance already at target",
                    created_at=datetime.now(timezone.utc),
                ),
                balance=LeaveBalanceResponse.model_validate(current_balance),
            )

        return self.create_adjustment(
            LedgerAdjustmentCreate(
                employee_id=payload.employee_id,
                leave_type_id=payload.leave_type_id,
                year=year,
                amount_days=delta,
                transaction_type=LedgerTransactionType.ADMIN_ADJUSTMENT,
                reason=payload.reason or f"Balance set to {payload.target_days} by admin",
            ),
            actor_id=actor_id,
            ip_address=ip_address,
        )

    def list_for_employee(
        self, *, employee_id: int, leave_type_id: int | None, limit: int, offset: int
    ) -> list[LeaveLedgerEntryResponse]:
        entries = self.ledger_repo.list_for_employee(
            employee_id=employee_id, leave_type_id=leave_type_id, limit=limit, offset=offset
        )
        return [LeaveLedgerEntryResponse.model_validate(e) for e in entries]
