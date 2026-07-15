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

    def get_timed_entries_for_day(
        self, employee_id: int, entry_date: date, *, exclude_entry_id: int | None = None
    ) -> list[WorkEntry]:
        """
        All of this employee's entries on this date that have both
        start_time and end_time set (untimed legacy-style entries can't be
        overlap-checked and are excluded). Used by EntryService to enforce
        that a new/updated time-block doesn't overlap an existing one,
        across any project — an employee can't work two things at once.
        """
        conditions = [
            WorkEntry.employee_id == employee_id,
            WorkEntry.entry_date == entry_date,
            WorkEntry.start_time.is_not(None),
            WorkEntry.end_time.is_not(None),
        ]
        if exclude_entry_id is not None:
            conditions.append(WorkEntry.id != exclude_entry_id)
        stmt = select(WorkEntry).where(*conditions)
        return list(self.db.execute(stmt).scalars().all())

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

    def search_all_for_export(
        self,
        *,
        employee_id: int | None = None,
        project_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[WorkEntry]:
        """Unpaginated variant of search(), for CSV export."""
        stmt = select(WorkEntry).options(joinedload(WorkEntry.employee), joinedload(WorkEntry.project))
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
        for cond in conditions:
            stmt = stmt.where(cond)
        stmt = stmt.order_by(WorkEntry.entry_date.desc(), WorkEntry.id.desc())
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_status_count_for_date(self, entry_date: date, status: str) -> int:
        """Used by the dashboard's 'Pending Timesheet Approvals' widget (today-scoped, per PM decision)."""
        stmt = (
            select(func.count())
            .select_from(WorkEntry)
            .where(WorkEntry.entry_date == entry_date, WorkEntry.status == status)
        )
        return self.db.execute(stmt).scalar_one()

    def get_missing_timesheet_employees(
        self, entry_date: date, exclude_employee_ids: set[int] | None = None
    ) -> list[User]:
        """
        Active employees with no work entry on the given date. Best-practice
        definition used in the absence of any 'expected hours' baseline
        (there is none in this schema — confirmed with PM) — an employee who
        logged nothing at all for the date is "missing", not partial-hours
        thresholds.

        exclude_employee_ids is meant for employees on approved leave that
        date — they aren't expected to log hours, so they shouldn't show up
        as "missing". The caller (DashboardService) is responsible for
        supplying that set from LeaveRequestRepository.get_on_leave_for_date().
        """
        entered_subquery = select(WorkEntry.employee_id).where(WorkEntry.entry_date == entry_date).distinct()
        conditions = [User.is_active.is_(True), User.deleted_at.is_(None), User.id.not_in(entered_subquery)]
        if exclude_employee_ids:
            conditions.append(User.id.not_in(exclude_employee_ids))
        stmt = select(User).where(*conditions).order_by(User.username)
        return list(self.db.execute(stmt).scalars().all())

    def get_recent(self, limit: int = 10) -> list[WorkEntry]:
        """Most recently created entries, for the dashboard's Recent Activities feed."""
        stmt = (
            select(WorkEntry)
            .options(joinedload(WorkEntry.employee), joinedload(WorkEntry.project))
            .order_by(WorkEntry.created_at.desc(), WorkEntry.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

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
