"""
tests/integration/test_department_service.py
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.department_service import DepartmentService


def test_create_department(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    result = service.create_department(
        DepartmentCreate(name="Engineering", description="Builds the product"),
        actor_id=seeded_users["alice"].id,
        ip_address="127.0.0.1",
    )
    assert result.id is not None
    assert result.name == "Engineering"
    assert result.is_active is True


def test_create_department_duplicate_name_raises_conflict(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    service.create_department(
        DepartmentCreate(name="Engineering"), actor_id=seeded_users["alice"].id, ip_address=None
    )
    with pytest.raises(ConflictError):
        service.create_department(
            DepartmentCreate(name="Engineering"), actor_id=seeded_users["alice"].id, ip_address=None
        )


def test_update_department_name(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    created = service.create_department(
        DepartmentCreate(name="Sales"), actor_id=seeded_users["alice"].id, ip_address=None
    )
    updated = service.update_department(
        created.id,
        DepartmentUpdate(name="Sales & Marketing"),
        actor_id=seeded_users["alice"].id,
        ip_address=None,
    )
    assert updated.name == "Sales & Marketing"


def test_update_nonexistent_department_raises_not_found(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    with pytest.raises(NotFoundError):
        service.update_department(
            9999, DepartmentUpdate(name="Ghost"), actor_id=seeded_users["alice"].id, ip_address=None
        )


def test_update_department_to_duplicate_name_raises_conflict(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    service.create_department(
        DepartmentCreate(name="HR"), actor_id=seeded_users["alice"].id, ip_address=None
    )
    finance = service.create_department(
        DepartmentCreate(name="Finance"), actor_id=seeded_users["alice"].id, ip_address=None
    )
    with pytest.raises(ConflictError):
        service.update_department(
            finance.id, DepartmentUpdate(name="HR"), actor_id=seeded_users["alice"].id, ip_address=None
        )


def test_deactivate_department_sets_is_active_false(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    created = service.create_department(
        DepartmentCreate(name="Legal"), actor_id=seeded_users["alice"].id, ip_address=None
    )
    service.deactivate_department(created.id, actor_id=seeded_users["alice"].id, ip_address=None)

    items, _ = service.department_repo.search(is_active=True, limit=100, offset=0)
    assert created.id not in {d.id for d in items}

    items_all, _ = service.department_repo.search(is_active=False, limit=100, offset=0)
    assert created.id in {d.id for d in items_all}


def test_list_departments_pagination(db_session: Session, seeded_users):
    service = DepartmentService(db_session)
    for name in ["Dept A", "Dept B", "Dept C"]:
        service.create_department(
            DepartmentCreate(name=name), actor_id=seeded_users["alice"].id, ip_address=None
        )
    page = service.list_departments(page=1, size=2, is_active=None)
    assert page.total == 3
    assert len(page.items) == 2
