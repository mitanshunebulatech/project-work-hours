"""
app/db/repositories/department_repo.py
"""

from sqlalchemy import func, select

from app.db.repositories.base import BaseRepository
from app.models.department import Department


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    def get_by_name(self, name: str) -> Department | None:
        stmt = select(Department).where(Department.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Department], int]:
        stmt = select(Department)
        count_stmt = select(func.count()).select_from(Department)
        if is_active is not None:
            stmt = stmt.where(Department.is_active == is_active)
            count_stmt = count_stmt.where(Department.is_active == is_active)
        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(Department.name.asc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
