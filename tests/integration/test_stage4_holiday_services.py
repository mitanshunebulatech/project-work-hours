"""
tests/integration/test_stage4_holiday_services.py

Stage 4 (Services): HolidayService bug fix + publish workflow.

Renamed from test_stage4_holiday_leaveplan_services.py — the LeavePlan
half of that file was removed here (HRMS V3 PM requirement: "remove the
leave planning module completely"), along with LeavePlanService,
LeavePlanRepository, the leave_plans table/model, and the leave-plans API
endpoint. This file now covers only what's left: HolidayService.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.holiday import HolidayCreate, HolidayUpdate
from app.services.holiday_service import HolidayService


def test_create_holiday_sets_year_regression(db_session: Session, seeded_users: dict[str, User]) -> None:
    service = HolidayService(db_session)
    admin = seeded_users["alice"]

    created = service.create_holiday(
        HolidayCreate(name="Republic Day", date=date(2027, 1, 26)),
        actor_id=admin.id, ip_address="127.0.0.1",
    )

    assert created.year == 2027
    assert created.is_published is False


def test_update_holiday_date_keeps_year_in_sync(db_session: Session, seeded_users: dict[str, User]) -> None:
    service = HolidayService(db_session)
    admin = seeded_users["alice"]

    created = service.create_holiday(
        HolidayCreate(name="New Year", date=date(2026, 12, 31)),
        actor_id=admin.id, ip_address="127.0.0.1",
    )
    assert created.year == 2026

    updated = service.update_holiday(
        created.id, HolidayUpdate(date=date(2027, 1, 1)),
        actor_id=admin.id, ip_address="127.0.0.1",
    )
    assert updated.year == 2027


def test_publish_year_only_touches_active_holidays(db_session: Session, seeded_users: dict[str, User]) -> None:
    service = HolidayService(db_session)
    admin = seeded_users["alice"]

    active = service.create_holiday(
        HolidayCreate(name="Diwali", date=date(2027, 11, 5)), actor_id=admin.id, ip_address=None
    )
    inactive = service.create_holiday(
        HolidayCreate(name="Mistake Entry", date=date(2027, 11, 6)), actor_id=admin.id, ip_address=None
    )
    service.deactivate_holiday(inactive.id, actor_id=admin.id, ip_address=None)

    changed = service.publish_year(2027, actor_id=admin.id, ip_address=None)

    assert changed == 1
    published_ids = {h.id for h in service.list_published_for_year(2027)}
    assert active.id in published_ids
    assert inactive.id not in published_ids


def test_unpublished_holiday_not_visible_via_employee_read_path(
    db_session: Session, seeded_users: dict[str, User]
) -> None:
    service = HolidayService(db_session)
    admin = seeded_users["alice"]
    service.create_holiday(
        HolidayCreate(name="Draft Holiday", date=date(2028, 3, 15)), actor_id=admin.id, ip_address=None
    )
    assert service.list_published_for_year(2028) == []
