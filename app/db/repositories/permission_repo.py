"""
app/db/repositories/permission_repo.py
"""

from typing import Sequence

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.permission import Permission


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_codes(self, codes: Sequence[str]) -> Sequence[Permission]:
        stmt = select(Permission).where(Permission.code.in_(codes))
        return self.db.execute(stmt).scalars().all()
