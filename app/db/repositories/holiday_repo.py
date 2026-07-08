"""
app/db/repositories/holiday_repo.py
"""
from datetime import date as date_
from typing import Sequence

from sqlalchemy import func, select

from app.db.repositories.base import BaseRepository
from app.models.holiday import Holiday


class HolidayRepository(BaseRepository[Holiday]):
    model = Holiday

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

    def get_by_date(self, holiday_date: date_) -> Holiday | None:
        stmt = select(Holiday).where(Holiday.date == holiday_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        year: int | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Holiday], int]:
        stmt = select(Holiday)
        count_stmt = select(func.count()).select_from(Holiday)
        if year is not None:
            condition = func.extract("year", Holiday.date) == year
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        if is_active is not None:
            stmt = stmt.where(Holiday.is_active == is_active)
            count_stmt = count_stmt.where(Holiday.is_active == is_active)
        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(Holiday.date.asc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
