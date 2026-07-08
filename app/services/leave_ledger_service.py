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

    def list_for_employee(
        self, *, employee_id: int, leave_type_id: int | None, limit: int, offset: int
    ) -> list[LeaveLedgerEntryResponse]:
        entries = self.ledger_repo.list_for_employee(
            employee_id=employee_id, leave_type_id=leave_type_id, limit=limit, offset=offset
        )
        return [LeaveLedgerEntryResponse.model_validate(e) for e in entries]
