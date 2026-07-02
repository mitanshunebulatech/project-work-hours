"""
app/models/work_entry.py
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkEntry(Base):
    __tablename__ = "work_entries"
    __table_args__ = (
        UniqueConstraint("employee_id", "project_id", "entry_date", name="uq_employee_project_date"),
        CheckConstraint("hours_worked > 0 AND hours_worked <= 24", name="chk_hours_range"),
        Index("idx_entries_employee_date", "employee_id", "entry_date"),
        Index("idx_entries_project", "project_id"),
        Index("idx_entries_status", "status"),
        Index("idx_entries_date", "entry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours_worked: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("User", back_populates="entries", foreign_keys=[employee_id])
    project = relationship("Project", back_populates="entries")

    def __repr__(self) -> str:
        return f"<WorkEntry id={self.id} employee_id={self.employee_id} date={self.entry_date} status={self.status}>"
