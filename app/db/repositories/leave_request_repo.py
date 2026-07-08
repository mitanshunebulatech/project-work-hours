"""
app/db/repositories/leave_request_repo.py
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.db.repositories.base import BaseRepository
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.user import User


class LeaveRequestRepository(BaseRepository[LeaveRequest]):
    model = LeaveRequest

    def get_with_relations(self, request_id: int) -> LeaveRequest | None:
        stmt = (
            select(LeaveRequest)
            .options(
                joinedload(LeaveRequest.employee),
                joinedload(LeaveRequest.leave_type),
                joinedload(LeaveRequest.reviewer),
            )
            .where(LeaveRequest.id == request_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        employee_id: int | None = None,
        status: str | None = None,
        leave_type_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        oldest_first: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[LeaveRequest], int]:
        """
        employee_id=None means 'no restriction' (admin viewing all requests).
        The service layer decides whether to pass None or the current
        employee's id — this repository has no concept of roles, same
        boundary as WorkEntryRepository.search().
        """
        stmt = select(LeaveRequest).options(
            joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type)
        )
        count_stmt = select(func.count()).select_from(LeaveRequest)

        conditions = []
        if employee_id is not None:
            conditions.append(LeaveRequest.employee_id == employee_id)
        if status is not None:
            conditions.append(LeaveRequest.status == status)
        if leave_type_id is not None:
            conditions.append(LeaveRequest.leave_type_id == leave_type_id)
        if date_from is not None:
            conditions.append(LeaveRequest.end_date >= date_from)
        if date_to is not None:
            conditions.append(LeaveRequest.start_date <= date_to)

        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.join(User, LeaveRequest.employee_id == User.id)
            count_stmt = count_stmt.join(User, LeaveRequest.employee_id == User.id)
            conditions.append(func.lower(User.username).like(pattern))

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = self.db.execute(count_stmt).scalar_one()

        # Admin triage queues want oldest-pending-first (Phase 3's "manual
        # escalation substitute"); every other view wants newest-first.
        order = (
            LeaveRequest.created_at.asc() if oldest_first else LeaveRequest.created_at.desc()
        )
        stmt = stmt.order_by(order, LeaveRequest.id.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def find_overlapping(
        self,
        *,
        employee_id: int,
        start_date: date,
        end_date: date,
        exclude_request_id: int | None = None,
    ) -> list[LeaveRequest]:
        """
        Conflict detection (Phase 3): does this employee already have a
        pending or approved request whose date range overlaps the one being
        submitted. Only checks the SAME employee — cross-employee overlap is
        informational-only for the admin calendar view, never a block,
        since approval is admin-only here (no auto-scheduling concerns).
        """
        stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if exclude_request_id is not None:
            stmt = stmt.where(LeaveRequest.id != exclude_request_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_calendar_entries(self, *, month: int, year: int) -> list[LeaveRequest]:
        """Approved-only leave overlapping the given month, for the org-wide calendar view."""
        from calendar import monthrange

        month_start = date(year, month, 1)
        month_end = date(year, month, monthrange(year, month)[1])

        stmt = (
            select(LeaveRequest)
            .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
            .where(
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= month_end,
                LeaveRequest.end_date >= month_start,
            )
        )
        return list(self.db.execute(stmt).unique().scalars().all())
