"""
app/models/leave_plan.py

PM requirement #6 (Leave Planning): informational-only yearly leave
planning. Deliberately zero coupling to LeaveRequest/LeaveLedgerEntry —
no approval step, no balance impact, no auto-conversion to a real request
(locked-in design decision). An employee plans "I intend to take leave
around this date, for this reason" without it touching the actual leave
balance/approval machinery at all; converting a plan into a real request
is a manual, separate action the employee takes later via the normal
leave-request flow, not something this table does automatically.
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeavePlan(Base):
    __tablename__ = "leave_plans"
    __table_args__ = (
        CheckConstraint("planned_end_date >= planned_start_date", name="chk_leave_plans_dates_valid"),
        Index("idx_leave_plans_employee_year", "employee_id", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    planned_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Stored explicitly, not derived — same reasoning as Holiday.year:
    # "give me my 2027 plan" is a common query shape, worth indexing directly.
    year: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Bidirectional, matching this codebase's established pattern for every
    # child-of-User/child-of-LeaveType table (WorkEntry.employee/User.entries,
    # LeavePolicy.leave_type/LeaveType.policies, etc.) — consistency itself
    # is the thing that prevents a future confused fix on this table.
    #
    # Deliberately default (lazy) loading, not eager: User is loaded on
    # every authenticated request via get_current_user(), so an eager
    # leave_plans relationship would silently pull each user's entire
    # leave-planning history on every single request — a real, slow-growing
    # production performance regression.
    #
    # Deliberately no cascade="all, delete-orphan": leave plans are
    # historical/planning records, the same category as WorkEntry and
    # LeaveRequest (neither of which cascade-deletes today), not a
    # uniquely-owned child like EmployeeProfile. This system doesn't hard
    # delete User rows in practice (Department is deactivate-only; User
    # follows the same pattern) — matching that convention, not overriding it.
    employee = relationship("User", back_populates="leave_plans", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType", back_populates="leave_plans")

    def __repr__(self) -> str:
        return f"<LeavePlan id={self.id} employee_id={self.employee_id} year={self.year}>"
