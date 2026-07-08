"""
app/models/leave_balance.py
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaveBalance(Base):
    """
    The fast-read, materialized current balance per employee per leave type
    per year. This is a cache derived from leave_ledger — the ledger stays
    the source of truth; this table exists purely so a dashboard load is a
    single indexed row lookup instead of an aggregation over the full ledger.
    """

    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_balance_employee_type_year"),
        Index("idx_leave_balances_employee_year", "employee_id", "year"),
        Index("idx_leave_balances_type", "leave_type_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_credited_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total_debited_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    remaining_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("User", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType")

    def __repr__(self) -> str:
        return (
            f"<LeaveBalance employee_id={self.employee_id} leave_type_id={self.leave_type_id} "
            f"year={self.year} remaining={self.remaining_days}>"
        )
