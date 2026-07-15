"""
tests/integration/test_role_service.py
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.permission import Permission
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.role_service import RoleService


@pytest.fixture
def seeded_permissions(db_session: Session) -> dict[str, Permission]:
    perms = {
        "leave_requests:approve": Permission(code="leave_requests:approve", description="Approve leave"),
        "departments:manage": Permission(code="departments:manage", description="Manage departments"),
    }
    db_session.add_all(perms.values())
    db_session.commit()
    return perms


@pytest.fixture
def seeded_system_roles(db_session: Session, seeded_permissions: dict[str, Permission]) -> dict[str, Role]:
    admin = Role(name="admin", is_system_role=True)
    admin.permissions = list(seeded_permissions.values())
    employee = Role(name="employee", is_system_role=True)
    db_session.add_all([admin, employee])
    db_session.commit()
    return {"admin": admin, "employee": employee}


def test_create_role(db_session: Session, seeded_users, seeded_permissions):
    service = RoleService(db_session)
    result = service.create_role(
        RoleCreate(
            name="HR Manager", description="Manages employee records", permission_codes=["departments:manage"]
        ),
        actor_id=seeded_users["alice"].id,
        ip_address="127.0.0.1",
    )
    assert result.id is not None
    assert result.is_system_role is False
    assert [p.code for p in result.permissions] == ["departments:manage"]


def test_create_role_duplicate_name_raises_conflict(db_session: Session, seeded_users, seeded_permissions):
    service = RoleService(db_session)
    service.create_role(RoleCreate(name="HR Manager"), actor_id=seeded_users["alice"].id, ip_address=None)
    with pytest.raises(ConflictError):
        service.create_role(RoleCreate(name="HR Manager"), actor_id=seeded_users["alice"].id, ip_address=None)


def test_create_role_unknown_permission_code_raises(db_session: Session, seeded_users, seeded_permissions):
    service = RoleService(db_session)
    with pytest.raises(BusinessRuleError):
        service.create_role(
            RoleCreate(name="HR Manager", permission_codes=["does_not_exist:anywhere"]),
            actor_id=seeded_users["alice"].id,
            ip_address=None,
        )


def test_update_custom_role_permissions(db_session: Session, seeded_users, seeded_permissions):
    service = RoleService(db_session)
    created = service.create_role(
        RoleCreate(name="HR Manager", permission_codes=["departments:manage"]),
        actor_id=seeded_users["alice"].id,
        ip_address=None,
    )
    updated = service.update_role(
        created.id,
        RoleUpdate(permission_codes=["leave_requests:approve"]),
        actor_id=seeded_users["alice"].id,
        ip_address=None,
    )
    assert [p.code for p in updated.permissions] == ["leave_requests:approve"]


def test_update_system_role_permissions_raises(db_session: Session, seeded_users, seeded_system_roles):
    """The one rule this sprint exists to protect: editing a system role's
    permissions here would desync app/core/permissions.py's hardcoded
    fallback for legacy (role_id=NULL) users."""
    service = RoleService(db_session)
    with pytest.raises(BusinessRuleError):
        service.update_role(
            seeded_system_roles["employee"].id,
            RoleUpdate(permission_codes=["departments:manage"]),
            actor_id=seeded_users["alice"].id,
            ip_address=None,
        )


def test_update_system_role_description_is_allowed(db_session: Session, seeded_users, seeded_system_roles):
    """Only permission_codes is blocked for system roles — name/description
    aren't part of the legacy-fallback coupling, so they stay editable."""
    service = RoleService(db_session)
    updated = service.update_role(
        seeded_system_roles["employee"].id,
        RoleUpdate(description="Standard self-service access"),
        actor_id=seeded_users["alice"].id,
        ip_address=None,
    )
    assert updated.description == "Standard self-service access"


def test_delete_system_role_raises(db_session: Session, seeded_users, seeded_system_roles):
    service = RoleService(db_session)
    with pytest.raises(BusinessRuleError):
        service.delete_role(seeded_system_roles["admin"].id, actor_id=seeded_users["alice"].id, ip_address=None)


def test_delete_role_with_assigned_users_raises(db_session: Session, seeded_users, seeded_permissions):
    service = RoleService(db_session)
    created = service.create_role(RoleCreate(name="HR Manager"), actor_id=seeded_users["alice"].id, ip_address=None)

    seeded_users["alice"].role_id = created.id
    db_session.add(seeded_users["alice"])
    db_session.commit()

    with pytest.raises(BusinessRuleError):
        service.delete_role(created.id, actor_id=seeded_users["bob"].id, ip_address=None)


def test_delete_unassigned_custom_role_succeeds(db_session: Session, seeded_users, seeded_permissions):
    service = RoleService(db_session)
    created = service.create_role(RoleCreate(name="HR Manager"), actor_id=seeded_users["alice"].id, ip_address=None)
    service.delete_role(created.id, actor_id=seeded_users["alice"].id, ip_address=None)

    with pytest.raises(NotFoundError):
        service.get_role(created.id)


def test_get_nonexistent_role_raises_not_found(db_session: Session, seeded_users):
    service = RoleService(db_session)
    with pytest.raises(NotFoundError):
        service.get_role(99999)
