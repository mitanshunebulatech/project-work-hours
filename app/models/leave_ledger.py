"""
app/models/leave_ledger.py
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaveLedgerEntry(Base):
    """
    Append-only transaction log. Rows are NEVER updated or deleted — a
    reversal (e.g. cancelling an approved leave) is a new row with an
    opposite-signed amount, never an edit to the original row. amount_days
    is signed: positive for credits (accrual, carry-forward), negative for
    debits (leave taken). Summing this column for an employee/type/year
    always reproduces the balance from scratch, which is the whole point
    of keeping it this way — leave_balances is just a cache of this sum.
    """

    __tablename__ = "leave_ledger"
    __table_args__ = (
        Index("idx_leave_ledger_employee_type_date", "employee_id", "leave_type_id", "created_at"),
        Index("idx_leave_ledger_request", "leave_request_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    leave_request_id: Mapped[int | None] = mapped_column(ForeignKey("leave_requests.id"), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("User", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType")

    def __repr__(self) -> str:
        return (
            f"<LeaveLedgerEntry employee_id={self.employee_id} type={self.transaction_type} "
            f"amount={self.amount_days}>"
        )
