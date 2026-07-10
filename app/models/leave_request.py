"""
app/models/leave_request.py
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_leave_dates_valid"),
        # Explicit "is_half_day = false OR (IS NOT NULL AND IN (...))" — a bare
        # "half_day_slot IN (...)" evaluates to NULL (not FALSE) when the column
        # is NULL, and SQL treats a NULL CHECK result as passing on Postgres too.
        CheckConstraint(
            "(is_half_day = false AND half_day_slot IS NULL) OR "
            "(is_half_day = true AND half_day_slot IS NOT NULL AND half_day_slot IN ('first_half', 'second_half'))",
            name="chk_half_day_slot_consistency",
        ),
        Index("idx_leave_requests_employee_status", "employee_id", "status"),
        Index("idx_leave_requests_status_created", "status", "created_at"),
        Index("idx_leave_requests_dates", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_half_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    half_day_slot: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "first_half" | "second_half"
    working_days_count: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("User", foreign_keys=[employee_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    leave_type = relationship("LeaveType")

    def __repr__(self) -> str:
        return (
            f"<LeaveRequest id={self.id} employee_id={self.employee_id} "
            f"status={self.status!r} {self.start_date}..{self.end_date}>"
        )
