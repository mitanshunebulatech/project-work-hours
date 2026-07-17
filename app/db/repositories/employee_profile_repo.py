"""
app/db/repositories/employee_profile_repo.py
"""

from sqlalchemy import func, select, text

from app.db.repositories.base import BaseRepository
from app.models.employee_profile import EmployeeProfile


class EmployeeProfileRepository(BaseRepository[EmployeeProfile]):
    model = EmployeeProfile

    def generate_next_employee_code(self) -> str:
        """
        Pulls from the employee_code_seq Postgres sequence (migration 0026)
        rather than SELECT MAX(...)+1 — nextval() is atomic under
        concurrency; MAX+1 is not (two onboarding requests racing could
        compute the same "next" code before either commits — a real bug
        found in a repo audit, fixed here).

        SQLite (used only by the test suite — production always runs
        Postgres) has no CREATE SEQUENCE/nextval equivalent, so this falls
        back to the old MAX+1 approach there. That fallback is exercised
        only by the synchronous, single-connection test suite, where the
        race condition this method exists to prevent cannot occur — the
        atomicity guarantee that actually matters in production is
        untouched.
        """
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            value = self.db.execute(text("SELECT nextval('employee_code_seq')")).scalar_one()
            return f"EMP-{value:04d}"

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
