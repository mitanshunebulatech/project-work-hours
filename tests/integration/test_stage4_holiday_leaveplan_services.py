"""
tests/integration/test_stage4_holiday_leaveplan_services.py

Stage 4 (Services): HolidayService bug fix + publish workflow,
LeavePlanService CRUD + ownership boundary.
"""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.schemas.holiday import HolidayCreate, HolidayUpdate
from app.schemas.leave_plan import LeavePlanCreate, LeavePlanUpdate
from app.services.holiday_service import HolidayService
from app.services.leave_plan_service import LeavePlanService


# --- HolidayService ---

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


# --- LeavePlanService ---

def test_create_plan_derives_year_from_start_date(
    db_session: Session, seeded_users: dict[str, User], seeded_leave_type
) -> None:
    service = LeavePlanService(db_session)
    alice = seeded_users["alice"]

    created = service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 6, 1),
            planned_end_date=date(2027, 6, 5),
            reason="Family trip",
        ),
        employee_id=alice.id, ip_address="127.0.0.1",
    )

    assert created.year == 2027
    assert created.employee_id == alice.id


def test_employee_cannot_view_another_employees_plan(
    db_session: Session, seeded_users: dict[str, User], seeded_leave_type
) -> None:
    service = LeavePlanService(db_session)
    alice, bob = seeded_users["alice"], seeded_users["bob"]

    plan = service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 7, 1),
            planned_end_date=date(2027, 7, 3),
        ),
        employee_id=alice.id, ip_address=None,
    )

    with pytest.raises(ForbiddenError):
        service.get_plan(plan.id, requesting_user_id=bob.id, is_admin=False)

    fetched = service.get_plan(plan.id, requesting_user_id=bob.id, is_admin=True)
    assert fetched.id == plan.id


def test_employee_cannot_edit_or_delete_another_employees_plan(
    db_session: Session, seeded_users: dict[str, User], seeded_leave_type
) -> None:
    service = LeavePlanService(db_session)
    alice, bob = seeded_users["alice"], seeded_users["bob"]

    plan = service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 8, 1),
            planned_end_date=date(2027, 8, 2),
        ),
        employee_id=alice.id, ip_address=None,
    )

    with pytest.raises(ForbiddenError):
        service.update_plan(
            plan.id, LeavePlanUpdate(reason="hijacked"),
            requesting_user_id=bob.id, is_admin=False, ip_address=None,
        )
    with pytest.raises(ForbiddenError):
        service.delete_plan(plan.id, requesting_user_id=bob.id, is_admin=False, ip_address=None)


def test_update_plan_start_date_keeps_year_in_sync(
    db_session: Session, seeded_users: dict[str, User], seeded_leave_type
) -> None:
    service = LeavePlanService(db_session)
    alice = seeded_users["alice"]

    plan = service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 12, 30),
            planned_end_date=date(2027, 12, 31),
        ),
        employee_id=alice.id, ip_address=None,
    )
    assert plan.year == 2027

    updated = service.update_plan(
        plan.id,
        LeavePlanUpdate(planned_start_date=date(2028, 1, 2), planned_end_date=date(2028, 1, 3)),
        requesting_user_id=alice.id, is_admin=False, ip_address=None,
    )
    assert updated.year == 2028


def test_delete_plan_removes_it(
    db_session: Session, seeded_users: dict[str, User], seeded_leave_type
) -> None:
    service = LeavePlanService(db_session)
    alice = seeded_users["alice"]

    plan = service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 9, 1),
            planned_end_date=date(2027, 9, 1),
        ),
        employee_id=alice.id, ip_address=None,
    )
    service.delete_plan(plan.id, requesting_user_id=alice.id, is_admin=False, ip_address=None)

    with pytest.raises(NotFoundError):
        service.get_plan(plan.id, requesting_user_id=alice.id, is_admin=False)


def test_list_plans_scopes_employee_to_own_plans(
    db_session: Session, seeded_users: dict[str, User], seeded_leave_type
) -> None:
    service = LeavePlanService(db_session)
    alice, bob = seeded_users["alice"], seeded_users["bob"]

    service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 10, 1), planned_end_date=date(2027, 10, 1),
        ),
        employee_id=alice.id, ip_address=None,
    )
    service.create_plan(
        LeavePlanCreate(
            leave_type_id=seeded_leave_type.id,
            planned_start_date=date(2027, 10, 2), planned_end_date=date(2027, 10, 2),
        ),
        employee_id=bob.id, ip_address=None,
    )

    bob_view = service.list_plans(
        requesting_user_id=bob.id, is_admin=False, employee_id=alice.id,
        year=2027, leave_type_id=None, page=1, size=20,
    )
    assert bob_view.total == 1
    assert all(item.employee_id == bob.id for item in bob_view.items)
