"""
app/services/role_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.permission_repo import PermissionRepository
from app.db.repositories.role_repo import RoleRepository
from app.db.repositories.user_repo import UserRepository
from app.models.role import Role
from app.schemas.role import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate


class RoleService:
    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.permission_repo = PermissionRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_roles(self) -> list[RoleResponse]:
        return [RoleResponse.from_model(r) for r in self.role_repo.list_all()]

    def get_role(self, role_id: int) -> RoleResponse:
        role = self.role_repo.get_with_permissions(role_id)
        if role is None:
            raise NotFoundError("Role not found")
        return RoleResponse.from_model(role)

    def list_permissions(self) -> list[PermissionResponse]:
        """Read-only catalogue — permissions themselves aren't created/edited
        through this API, only assigned to roles. The catalogue is seeded by
        migration 0018 and changes only via a new migration, deliberately."""
        return [PermissionResponse.model_validate(p) for p in self.permission_repo.list_all()]

    def _resolve_permissions(self, codes: list[str]) -> list:
        if not codes:
            return []
        found = list(self.permission_repo.get_by_codes(codes))
        found_codes = {p.code for p in found}
        missing = set(codes) - found_codes
        if missing:
            raise BusinessRuleError(f"Unknown permission code(s): {', '.join(sorted(missing))}")
        return found

    def create_role(self, payload: RoleCreate, *, actor_id: int, ip_address: str | None) -> RoleResponse:
        if self.role_repo.get_by_name(payload.name):
            raise ConflictError("A role with this name already exists")

        permissions = self._resolve_permissions(payload.permission_codes)
        role = Role(name=payload.name, description=payload.description, is_system_role=False)
        role.permissions = permissions
        created = self.role_repo.create(role)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="roles",
            operation="INSERT",
            record_id=created.id,
            after_data={"name": created.name, "permission_codes": payload.permission_codes},
            ip_address=ip_address,
        )
        self.db.commit()
        return self.get_role(created.id)

    def update_role(
        self, role_id: int, payload: RoleUpdate, *, actor_id: int, ip_address: str | None
    ) -> RoleResponse:
        role = self.role_repo.get_with_permissions(role_id)
        if role is None:
            raise NotFoundError("Role not found")

        if payload.permission_codes is not None and role.is_system_role:
            raise BusinessRuleError(
                "System role permissions can't be edited here — they're fixed to keep the "
                "legacy-user permission fallback (app/core/permissions.py) in sync. "
                "Create a custom role instead if different access is needed."
            )

        if payload.name is not None and payload.name != role.name:
            existing = self.role_repo.get_by_name(payload.name)
            if existing is not None and existing.id != role_id:
                raise ConflictError("A role with this name already exists")

        before = {"name": role.name, "description": role.description}

        if payload.name is not None:
            role.name = payload.name
        if payload.description is not None:
            role.description = payload.description
        if payload.permission_codes is not None:
            role.permissions = self._resolve_permissions(payload.permission_codes)

        updated = self.role_repo.update(role)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="roles",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={"name": updated.name, "description": updated.description},
            ip_address=ip_address,
        )
        self.db.commit()
        return self.get_role(updated.id)

    def delete_role(self, role_id: int, *, actor_id: int, ip_address: str | None) -> None:
        role = self.role_repo.get(role_id)
        if role is None:
            raise NotFoundError("Role not found")
        if role.is_system_role:
            raise BusinessRuleError("System roles (admin, employee) can't be deleted")

        assigned_count = self.user_repo.count_by_role_id(role_id)
        if assigned_count > 0:
            raise BusinessRuleError(
                f"Can't delete role — {assigned_count} user(s) are still assigned to it. "
                "Reassign them to a different role first."
            )

        self.role_repo.delete(role)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="roles",
            operation="DELETE",
            record_id=role_id,
            before_data={"name": role.name},
            ip_address=ip_address,
        )
        self.db.commit()
