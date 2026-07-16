"""
app/models/work_schedule_policy.py
A deliberate singleton (always id=1) holding the company-wide half-day
office-hour boundaries. Kept separate from LeavePolicy: LeavePolicy varies
per leave-type/per-year (quota, notice, carry-forward), but office hours
are a company-wide fact that doesn't vary by leave type — modeling it as a
column on LeavePolicy would mean either duplicating the same four times
across every leave-type/year row, or arbitrarily picking one row as
"authoritative," both worse than a dedicated single-row table.

PM requirement #4: "Design this as a configurable policy, not hardcoded
values" — this table (plus its GET/PATCH endpoint) is that configurability:
an admin can change the boundaries without a code deploy.
"""

from datetime import datetime, time

from sqlalchemy import DateTime, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkSchedulePolicy(Base):
    __tablename__ = "work_schedule_policy"

    id: Mapped[int] = mapped_column(primary_key=True)  # always 1 — singleton, no autoincrement needed
    first_half_start: Mapped[time] = mapped_column(Time, nullable=False)
    first_half_end: Mapped[time] = mapped_column(Time, nullable=False)
    second_half_start: Mapped[time] = mapped_column(Time, nullable=False)
    second_half_end: Mapped[time] = mapped_column(Time, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<WorkSchedulePolicy first_half={self.first_half_start}-{self.first_half_end} "
            f"second_half={self.second_half_start}-{self.second_half_end}>"
        )
