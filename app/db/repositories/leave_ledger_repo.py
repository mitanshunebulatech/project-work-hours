"""
app/db/repositories/leave_ledger_repo.py

Deliberately does NOT inherit BaseRepository's update()/delete() usage —
the ledger is append-only by design (see LeaveLedgerEntry's docstring).
Only create() and read methods are exposed here.
"""

from sqlalchemy import extract, func, select

from app.models.leave_ledger import LeaveLedgerEntry


class LeaveLedgerRepository:
    def __init__(self, db):
        self.db = db

    def create(self, entry: LeaveLedgerEntry) -> LeaveLedgerEntry:
        self.db.add(entry)
        self.db.flush()
        self.db.refresh(entry)
        return entry

    def list_for_employee(
        self,
        *,
        employee_id: int,
        leave_type_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeaveLedgerEntry]:
        stmt = (
            select(LeaveLedgerEntry)
            .where(LeaveLedgerEntry.employee_id == employee_id)
            .order_by(LeaveLedgerEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if leave_type_id is not None:
            stmt = stmt.where(LeaveLedgerEntry.leave_type_id == leave_type_id)
        return list(self.db.execute(stmt).scalars().all())

    def sum_for_employee_type(self, *, employee_id: int, leave_type_id: int) -> float:
        """
        Replays the ledger by summing amount_days — the ground-truth balance
        calculation. Used to verify (or rebuild) leave_balances if the cache
        ever drifts; not used on the hot path (that's what the cache is for).
        """
        stmt = select(func.coalesce(func.sum(LeaveLedgerEntry.amount_days), 0)).where(
            LeaveLedgerEntry.employee_id == employee_id,
            LeaveLedgerEntry.leave_type_id == leave_type_id,
        )
        return self.db.execute(stmt).scalar_one()

    def has_annual_grant_for_year(self, *, employee_id: int, leave_type_id: int, year: int) -> bool:
        """
        Idempotency guard for the automatic yearly grant job (Task 19): checks
        whether an 'annual_grant' entry already exists for this employee/type
        within the given calendar year, based on created_at. Prevents double-
        granting if the job is re-run for a year already processed.
        """
        stmt = select(func.count()).select_from(LeaveLedgerEntry).where(
            LeaveLedgerEntry.employee_id == employee_id,
            LeaveLedgerEntry.leave_type_id == leave_type_id,
            LeaveLedgerEntry.transaction_type == "annual_grant",
            extract("year", LeaveLedgerEntry.created_at) == year,
        )
        count = self.db.execute(stmt).scalar_one()
        return count > 0
