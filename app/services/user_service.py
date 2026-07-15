"""
app/services/user_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.role_repo import RoleRepository
from app.db.repositories.user_repo import UserRepository
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_users(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        role: str | None,
        is_active: bool | None,
    ) -> PaginatedResponse[UserResponse]:
        items, total = self.user_repo.search(
            search=search, role=role, is_active=is_active, limit=size, offset=(page - 1) * size
        )
        return PaginatedResponse(
            items=[UserResponse.model_validate(u) for u in items], total=total, page=page, size=size
        )

    def create_user(self, payload: UserCreate, *, actor_id: int, ip_address: str | None) -> UserResponse:
        if self.user_repo.get_by_username(payload.username):
            raise ConflictError("Username already exists")
        if payload.email and self.user_repo.get_by_email(payload.email):
            raise ConflictError("Email already exists")

        user = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        created = self.user_repo.create(user)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="users",
            operation="INSERT",
            record_id=created.id,
            after_data={"username": created.username, "role": created.role},
            ip_address=ip_address,
        )
        self.db.commit()
        return UserResponse.model_validate(created)

    def update_user(
        self, user_id: int, payload: UserUpdate, *, actor_id: int, ip_address: str | None
    ) -> UserResponse:
        user = self.user_repo.get(user_id)
        if user is None or user.deleted_at is not None:
            raise NotFoundError("User not found")

        before = {"email": user.email, "role": user.role, "role_id": user.role_id, "is_active": user.is_active}

        if payload.email is not None:
            user.email = payload.email
        if payload.role is not None:
            user.role = payload.role
        if payload.role_id is not None:
            if self.role_repo.get(payload.role_id) is None:
                raise NotFoundError("Role not found")
            user.role_id = payload.role_id
        if payload.is_active is not None:
            user.is_active = payload.is_active

        updated = self.user_repo.update(user)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="users",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "email": updated.email,
                "role": updated.role,
                "role_id": updated.role_id,
                "is_active": updated.is_active,
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return UserResponse.model_validate(updated)

    def soft_delete_user(self, user_id: int, *, actor_id: int, ip_address: str | None) -> None:
        if user_id == actor_id:
            raise BusinessRuleError("You cannot deactivate your own account")

        user = self.user_repo.get(user_id)
        if user is None or user.deleted_at is not None:
            raise NotFoundError("User not found")

        from datetime import datetime, timezone

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        self.user_repo.update(user)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="users",
            operation="DELETE",
            record_id=user.id,
            before_data={"is_active": True},
            after_data={"is_active": False, "deleted_at": str(user.deleted_at)},
            ip_address=ip_address,
        )
        self.db.commit()
