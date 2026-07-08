"""
app/db/repositories/leave_balance_repo.py
"""

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.leave_balance import LeaveBalance


class LeaveBalanceRepository(BaseRepository[LeaveBalance]):
    model = LeaveBalance

    def get_for_employee_type_year(
        self, *, employee_id: int, leave_type_id: int, year: int
    ) -> LeaveBalance | None:
        stmt = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create_for_year(
        self, *, employee_id: int, leave_type_id: int, year: int
    ) -> LeaveBalance:
        """
        Every employee/type/year combination needs exactly one row (enforced
        by the DB's uq_balance_employee_type_year constraint too — this is
        defense in depth, same dual-layer pattern used elsewhere in this
        codebase). Called the first time a balance is ever read or written
        for a given year, rather than requiring a separate provisioning step.
        """
        existing = self.get_for_employee_type_year(
            employee_id=employee_id, leave_type_id=leave_type_id, year=year
        )
        if existing is not None:
            return existing

        new_balance = LeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            year=year,
            total_credited_days=0,
            total_debited_days=0,
            remaining_days=0,
        )
        return self.create(new_balance)

    def list_for_employee(self, *, employee_id: int, year: int) -> list[LeaveBalance]:
        stmt = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == year,
        )
        return list(self.db.execute(stmt).scalars().all())

    def adjust_balance(
        self, balance: LeaveBalance, *, credit_delta: float = 0, debit_delta: float = 0
    ) -> LeaveBalance:
        """
        Pure arithmetic update — applies a credit and/or debit delta and
        recomputes remaining_days. Deciding WHEN to call this (e.g. only on
        approval, never on submission) is a business rule that belongs in
        LeaveService, not here — this method just does the mechanical part.
        """
        balance.total_credited_days += credit_delta
        balance.total_debited_days += debit_delta
        balance.remaining_days = balance.total_credited_days - balance.total_debited_days
        return self.update(balance)
