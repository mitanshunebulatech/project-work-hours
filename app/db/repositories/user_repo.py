"""
app/db/repositories/user_repo.py
"""

from sqlalchemy import func, or_, select

from app.db.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_username(self, username: str, *, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(func.lower(User.username) == username.lower())
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower(), User.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        stmt = select(User).where(User.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(User).where(User.deleted_at.is_(None))

        if search:
            pattern = f"%{search.lower()}%"
            condition = or_(func.lower(User.username).like(pattern), func.lower(User.email).like(pattern))
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
            count_stmt = count_stmt.where(User.is_active == is_active)

        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def count_by_role_id(self, role_id: int) -> int:
        """Used by RoleService.delete_role to block deleting a role that's
        still assigned to users, rather than orphaning User.role_id."""
        stmt = select(func.count()).select_from(User).where(User.role_id == role_id, User.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one()
