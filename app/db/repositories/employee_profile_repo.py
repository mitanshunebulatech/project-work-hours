"""
app/db/repositories/employee_profile_repo.py
"""

from sqlalchemy import func, select

from app.db.repositories.base import BaseRepository
from app.models.employee_profile import EmployeeProfile


class EmployeeProfileRepository(BaseRepository[EmployeeProfile]):
    model = EmployeeProfile

    def generate_next_employee_code(self) -> str:
        """
        Next sequential "EMP-0001" style code. Reads the current max via
        the numeric suffix rather than row count, so a deleted row never
        causes a code to be reissued. Single shared source of truth for
        both admin-create and (later) OnboardingService.
        """
        stmt = select(func.max(EmployeeProfile.employee_code))
        current_max = self.db.execute(stmt).scalar_one_or_none()
        next_number = 1
        if current_max:
            next_number = int(current_max.split("-")[-1]) + 1
        return f"EMP-{next_number:04d}"

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
