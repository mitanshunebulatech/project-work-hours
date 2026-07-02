"""
app/db/repositories/project_repo.py
"""

from sqlalchemy import func, select

from app.db.repositories.base import BaseRepository
from app.models.project import Project


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def get_by_name(self, project_name: str) -> Project | None:
        stmt = select(Project).where(
            func.lower(Project.project_name) == project_name.lower(),
            Project.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Project], int]:
        stmt = select(Project).where(Project.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Project).where(Project.deleted_at.is_(None))

        if search:
            pattern = f"%{search.lower()}%"
            condition = func.lower(Project.project_name).like(pattern)
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if is_active is not None:
            stmt = stmt.where(Project.is_active == is_active)
            count_stmt = count_stmt.where(Project.is_active == is_active)

        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(Project.project_name.asc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
