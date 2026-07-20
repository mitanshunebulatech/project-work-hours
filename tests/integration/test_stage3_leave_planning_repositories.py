"""
tests/integration/test_stage3_leave_planning_repositories.py

Stage 3 (Repositories) of the Leave Planning / Holiday Publish Workflow
rollout: LeavePlanRepository (new) and HolidayRepository's search()/
get_published_for_year() (year column now used instead of extract()).

Deliberately run against this suite's real db_session fixture (SQLite) —
not just the ad-hoc Postgres check done during development — because the
aggregate method's day-count arithmetic silently returned 0 under SQLite
in its first draft (date-minus-date isn't portable across dialects) and
only a real SQLite-backed test catches that class of bug again in future.
"""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.db.repositories.holiday_repo import HolidayRepository
from app.db.repositories.leave_plan_repo import LeavePlanRepository
from app.models.holiday import Holiday
from app.models.leave_plan import LeavePlan


# --- LeavePlanRepository ---

def test_search_filters_by_year_and_employee(db_session: Session, seeded_users, seeded_leave_type) -> None:
    alice, bob = seeded_users["alice"], seeded_users["bob"]
    db_session.add_all([
        LeavePlan(employee_id=alice.id, leave_type_id=seeded_leave_type.id,
                   planned_start_date=date(2027, 6, 1), planned_end_date=date(2027, 6, 5), year=2027),
        LeavePlan(employee_id=bob.id, leave_type_id=seeded_leave_type.id,
                   planned_start_date=date(2027, 7, 1), planned_end_date=date(2027, 7, 3), year=2027),
        LeavePlan(employee_id=alice.id, leave_type_id=seeded_leave_type.id,
                   planned_start_date=date(2028, 1, 1), planned_end_date=date(2028, 1, 2), year=2028),
    ])
    db_session.commit()

    repo = LeavePlanRepository(db_session)

    items, total = repo.search(year=2027)
    assert total == 2

    items, total = repo.search(employee_id=alice.id, year=2027)
    assert total == 1
    assert items[0].employee_id == alice.id

    # employee_id=None must mean "no restriction" (admin view), not "match nothing"
    items, total = repo.search(employee_id=None, year=2028)
    assert total == 1


def test_find_overlapping_detects_date_range_collision(
    db_session: Session, seeded_users, seeded_leave_type
) -> None:
    alice = seeded_users["alice"]
    existing = LeavePlan(
        employee_id=alice.id, leave_type_id=seeded_leave_type.id,
        planned_start_date=date(2027, 6, 1), planned_end_date=date(2027, 6, 5), year=2027,
    )
    db_session.add(existing)
    db_session.commit()

    repo = LeavePlanRepository(db_session)

    overlapping = repo.find_overlapping(
        employee_id=alice.id, year=2027,
        planned_start_date=date(2027, 6, 3), planned_end_date=date(2027, 6, 10),
    )
    assert len(overlapping) == 1

    non_overlapping = repo.find_overlapping(
        employee_id=alice.id, year=2027,
        planned_start_date=date(2027, 8, 1), planned_end_date=date(2027, 8, 5),
    )
    assert len(non_overlapping) == 0

    # excluding the plan itself (e.g. when editing) must exclude it from the collision check
    self_excluded = repo.find_overlapping(
        employee_id=alice.id, year=2027,
        planned_start_date=date(2027, 6, 3), planned_end_date=date(2027, 6, 10),
        exclude_plan_id=existing.id,
    )
    assert len(self_excluded) == 0


def test_aggregate_by_employee_for_year_computes_correct_day_counts(
    db_session: Session, seeded_users, seeded_leave_type
) -> None:
    """
    The actual regression test for the SQLite date-arithmetic bug found
    during development: a naive SQL date-subtraction aggregate silently
    returned 0 planned_days under SQLite. This must return the real
    inclusive day count (June 1 to June 5 = 5 days, not 4, not 0).
    """
    alice, bob = seeded_users["alice"], seeded_users["bob"]
    db_session.add_all([
        LeavePlan(employee_id=alice.id, leave_type_id=seeded_leave_type.id,
                   planned_start_date=date(2027, 6, 1), planned_end_date=date(2027, 6, 5), year=2027),
        LeavePlan(employee_id=alice.id, leave_type_id=seeded_leave_type.id,
                   planned_start_date=date(2027, 9, 1), planned_end_date=date(2027, 9, 1), year=2027),
        LeavePlan(employee_id=bob.id, leave_type_id=seeded_leave_type.id,
                   planned_start_date=date(2027, 7, 1), planned_end_date=date(2027, 7, 3), year=2027),
    ])
    db_session.commit()

    repo = LeavePlanRepository(db_session)
    result = repo.aggregate_by_employee_for_year(2027)

    by_username = {row["employee_username"]: row for row in result}
    assert by_username["alice"]["plan_count"] == 2
    assert by_username["alice"]["planned_days"] == 6  # 5 (Jun 1-5) + 1 (Sep 1 single day)
    assert by_username["bob"]["plan_count"] == 1
    assert by_username["bob"]["planned_days"] == 3  # Jul 1-3 inclusive


def test_aggregate_returns_empty_list_for_year_with_no_plans(db_session: Session) -> None:
    repo = LeavePlanRepository(db_session)
    assert repo.aggregate_by_employee_for_year(2099) == []


# --- HolidayRepository ---

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
