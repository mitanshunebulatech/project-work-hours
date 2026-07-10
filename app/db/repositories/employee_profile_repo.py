"""
app/db/repositories/employee_profile_repo.py
"""

from sqlalchemy import func, select

from app.db.repositories.base import BaseRepository
from app.models.employee_profile import EmployeeProfile


class EmployeeProfileRepository(BaseRepository[EmployeeProfile]):
    model = EmployeeProfile

    def get_by_user_id(self, user_id: int) -> EmployeeProfile | None:
        stmt = select(EmployeeProfile).where(EmployeeProfile.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        department_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[EmployeeProfile], int]:
        stmt = select(EmployeeProfile)
        count_stmt = select(func.count()).select_from(EmployeeProfile)
        if department_id is not None:
            stmt = stmt.where(EmployeeProfile.department_id == department_id)
            count_stmt = count_stmt.where(EmployeeProfile.department_id == department_id)
        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(EmployeeProfile.full_name.asc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
