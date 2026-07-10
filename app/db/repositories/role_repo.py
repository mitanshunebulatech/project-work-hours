"""
app/db/repositories/role_repo.py
"""

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.repositories.base import BaseRepository
from app.models.role import Role


class RoleRepository(BaseRepository[Role]):
    model = Role

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_with_permissions(self, role_id: int) -> Role | None:
        stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == role_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()
