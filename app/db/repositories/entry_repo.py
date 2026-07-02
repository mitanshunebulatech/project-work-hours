"""
app/db/repositories/entry_repo.py
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.db.repositories.base import BaseRepository
from app.models.project import Project
from app.models.user import User
from app.models.work_entry import WorkEntry


class WorkEntryRepository(BaseRepository[WorkEntry]):
    model = WorkEntry

    def get_with_relations(self, entry_id: int) -> WorkEntry | None:
        stmt = (
            select(WorkEntry)
            .options(joinedload(WorkEntry.employee), joinedload(WorkEntry.project))
            .where(WorkEntry.id == entry_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_employee_project_date(
        self, employee_id: int, project_id: int, entry_date: date
    ) -> WorkEntry | None:
        stmt = select(WorkEntry).where(
            WorkEntry.employee_id == employee_id,
            WorkEntry.project_id == project_id,
            WorkEntry.entry_date == entry_date,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        employee_id: int | None = None,
        project_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[WorkEntry], int]:
        """
        employee_id=None means 'no restriction' (admin viewing all).
        The service layer is responsible for passing the current employee's id
        when the caller is an employee — this repository has no concept of roles.
        """
        stmt = select(WorkEntry).options(joinedload(WorkEntry.employee), joinedload(WorkEntry.project))
        count_stmt = select(func.count()).select_from(WorkEntry)

        conditions = []
        if employee_id is not None:
            conditions.append(WorkEntry.employee_id == employee_id)
        if project_id is not None:
            conditions.append(WorkEntry.project_id == project_id)
        if status is not None:
            conditions.append(WorkEntry.status == status)
        if date_from is not None:
            conditions.append(WorkEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(WorkEntry.entry_date <= date_to)

        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.join(User, WorkEntry.employee_id == User.id).join(
                Project, WorkEntry.project_id == Project.id
            )
            count_stmt = count_stmt.join(User, WorkEntry.employee_id == User.id).join(
                Project, WorkEntry.project_id == Project.id
            )
            search_condition = func.lower(User.username).like(pattern) | func.lower(
                Project.project_name
            ).like(pattern)
            conditions.append(search_condition)

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(WorkEntry.entry_date.desc(), WorkEntry.id.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def aggregate_summary(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        employee_id: int | None = None,
        project_id: int | None = None,
    ) -> dict:
        base_conditions = []
        if date_from is not None:
            base_conditions.append(WorkEntry.entry_date >= date_from)
        if date_to is not None:
            base_conditions.append(WorkEntry.entry_date <= date_to)
        if employee_id is not None:
            base_conditions.append(WorkEntry.employee_id == employee_id)
        if project_id is not None:
            base_conditions.append(WorkEntry.project_id == project_id)

        totals_stmt = select(
            func.coalesce(func.sum(WorkEntry.hours_worked), 0),
            func.count(WorkEntry.id),
        )
        for cond in base_conditions:
            totals_stmt = totals_stmt.where(cond)
        total_hours, total_entries = self.db.execute(totals_stmt).one()

        by_employee_stmt = (
            select(User.username, func.coalesce(func.sum(WorkEntry.hours_worked), 0))
            .join(User, WorkEntry.employee_id == User.id)
            .group_by(User.username)
            .order_by(func.sum(WorkEntry.hours_worked).desc())
        )
        for cond in base_conditions:
            by_employee_stmt = by_employee_stmt.where(cond)
        by_employee = self.db.execute(by_employee_stmt).all()

        by_project_stmt = (
            select(Project.project_name, func.coalesce(func.sum(WorkEntry.hours_worked), 0))
            .join(Project, WorkEntry.project_id == Project.id)
            .group_by(Project.project_name)
            .order_by(func.sum(WorkEntry.hours_worked).desc())
        )
        for cond in base_conditions:
            by_project_stmt = by_project_stmt.where(cond)
        by_project = self.db.execute(by_project_stmt).all()

        return {
            "total_hours": float(total_hours),
            "total_entries": total_entries,
            "by_employee": [{"employee_username": u, "total_hours": float(h)} for u, h in by_employee],
            "by_project": [{"project_name": p, "total_hours": float(h)} for p, h in by_project],
        }
