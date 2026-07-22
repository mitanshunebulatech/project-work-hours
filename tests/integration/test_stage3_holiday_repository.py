"""
tests/integration/test_stage3_holiday_repository.py

Stage 3 (Repositories): HolidayRepository's search()/get_published_for_year()
(year column used instead of extract()).

Renamed from test_stage3_leave_planning_repositories.py — the
LeavePlanRepository half of that file was removed here (HRMS V3 PM
requirement: "remove the leave planning module completely"), along with
LeavePlanRepository, LeavePlanService, the leave_plans table/model, and
the leave-plans API endpoint. This file now covers only what's left:
HolidayRepository.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories.holiday_repo import HolidayRepository
from app.models.holiday import Holiday


def test_search_by_year_uses_year_column_not_date_extraction(db_session: Session) -> None:
    """Confirms search(year=...) actually filters correctly post-fix — the
    prior version used func.extract('year', Holiday.date), which also
    worked functionally but couldn't use idx_holidays_year. This pins the
    correct *behavior*; the query-plan improvement isn't independently
    testable at this layer."""
    db_session.add_all([
        Holiday(name="New Year", date=date(2027, 1, 1), year=2027, is_active=True, is_published=True),
        Holiday(name="Republic Day", date=date(2027, 1, 26), year=2027, is_active=True, is_published=False),
        Holiday(name="Next Year Holiday", date=date(2028, 1, 1), year=2028, is_active=True, is_published=True),
    ])
    db_session.commit()

    repo = HolidayRepository(db_session)
    items, total = repo.search(year=2027)
    assert total == 2
    assert {h.name for h in items} == {"New Year", "Republic Day"}


def test_search_can_filter_by_is_published(db_session: Session) -> None:
    db_session.add_all([
        Holiday(name="Published", date=date(2027, 1, 1), year=2027, is_active=True, is_published=True),
        Holiday(name="Draft", date=date(2027, 1, 26), year=2027, is_active=True, is_published=False),
    ])
    db_session.commit()

    repo = HolidayRepository(db_session)
    items, total = repo.search(year=2027, is_published=True)
    assert total == 1
    assert items[0].name == "Published"


def test_get_published_for_year_only_returns_published(db_session: Session) -> None:
    """PM req #4: 'Employees should only see published calendars' — the
    actual access-control behavior this method exists to guarantee."""
    db_session.add_all([
        Holiday(name="Published Holiday", date=date(2027, 3, 1), year=2027, is_active=True, is_published=True),
        Holiday(name="Draft Holiday", date=date(2027, 4, 1), year=2027, is_active=True, is_published=False),
    ])
    db_session.commit()

    repo = HolidayRepository(db_session)
    published = repo.get_published_for_year(2027)

    assert len(published) == 1
    assert published[0].name == "Published Holiday"


def test_get_published_for_year_scopes_to_the_requested_year_only(db_session: Session) -> None:
    db_session.add_all([
        Holiday(name="2027 Holiday", date=date(2027, 3, 1), year=2027, is_active=True, is_published=True),
        Holiday(name="2028 Holiday", date=date(2028, 3, 1), year=2028, is_active=True, is_published=True),
    ])
    db_session.commit()

    repo = HolidayRepository(db_session)
    assert len(repo.get_published_for_year(2027)) == 1
    assert len(repo.get_published_for_year(2028)) == 1
    assert len(repo.get_published_for_year(2099)) == 0
