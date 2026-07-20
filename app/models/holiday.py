"""
app/models/holiday.py
"""
from datetime import date as date_, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("date", name="uq_holidays_date"),
        Index("idx_holidays_date", "date"),
        Index("idx_holidays_is_active", "is_active"),
        Index("idx_holidays_year", "year"),
        Index("idx_holidays_is_published", "is_published"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    # Explicit, not derived from date on every query (PM req #1) — matches
    # migration 0027's own reasoning: bulk-publish/clone-a-year operations
    # need year as a first-class filterable column.
    year: Mapped[int] = mapped_column(nullable=False)
    # Deliberately no default=True here at the model level either (mirrors
    # the migration's own column-level default=False) — new holidays start
    # as unpublished drafts (PM req #2/#3); existing rows were grandfathered
    # to True once, by the migration's data backfill, not by this default.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Holiday id={self.id} date={self.date!r} name={self.name!r}>"
