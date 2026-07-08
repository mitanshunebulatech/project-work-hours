"""
app/db/repositories/holiday_repo.py
"""
from datetime import date as date_
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.holiday import Holiday


class HolidayRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_holidays_in_range(self, start_date: date_, end_date: date_) -> Sequence[Holiday]:
        """Return all active holidays whose date falls within [start_date, end_date] inclusive."""
        stmt = (
            select(Holiday)
            .where(Holiday.is_active.is_(True))
            .where(Holiday.date >= start_date)
            .where(Holiday.date <= end_date)
            .order_by(Holiday.date)
        )
        return self.db.execute(stmt).scalars().all()

    def get_holiday_dates_in_range(self, start_date: date_, end_date: date_) -> set[date_]:
        """Convenience wrapper returning a bare set of dates, for O(1) membership checks
        in working-day calculations (e.g. preview_request())."""
        return {h.date for h in self.get_holidays_in_range(start_date, end_date)}
