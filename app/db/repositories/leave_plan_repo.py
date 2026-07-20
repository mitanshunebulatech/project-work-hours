"""
app/db/repositories/leave_plan_repo.py
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.db.repositories.base import BaseRepository
from app.models.leave_plan import LeavePlan
from app.models.leave_type import LeaveType
from app.models.user import User


class LeavePlanRepository(BaseRepository[LeavePlan]):
    model = LeavePlan

    def get_with_relations(self, plan_id: int) -> LeavePlan | None:
        stmt = (
            select(LeavePlan)
            .options(joinedload(LeavePlan.employee), joinedload(LeavePlan.leave_type))
            .where(LeavePlan.id == plan_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        employee_id: int | None = None,
        year: int | None = None,
        leave_type_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LeavePlan], int]:
        """
        employee_id=None means 'no restriction' (admin/HR viewing all
        plans for a year) — same boundary as LeaveRequestRepository.search():
        this repository has no concept of roles, the service layer decides
        whether to pass None or the current employee's id.
        """
        stmt = select(LeavePlan).options(
            joinedload(LeavePlan.employee), joinedload(LeavePlan.leave_type)
        )
        count_stmt = select(func.count()).select_from(LeavePlan)

        conditions = []
        if employee_id is not None:
            conditions.append(LeavePlan.employee_id == employee_id)
        if year is not None:
            conditions.append(LeavePlan.year == year)
        if leave_type_id is not None:
            conditions.append(LeavePlan.leave_type_id == leave_type_id)

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = self.db.execute(count_stmt).scalar_one()
        stmt = (
            stmt.order_by(LeavePlan.planned_start_date.asc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def find_overlapping(
        self,
        *,
        employee_id: int,
        year: int,
        planned_start_date: date,
        planned_end_date: date,
        exclude_plan_id: int | None = None,
    ) -> list[LeavePlan]:
        """
        Informational-only overlap check (matches LeavePlan's whole design:
        no approval workflow, so this is a UI hint — 'you already planned
        something in this window' — not a hard block, same non-blocking
        posture LeaveRequestRepository.find_overlapping's cross-employee
        case takes).
        """
        stmt = select(LeavePlan).where(
            LeavePlan.employee_id == employee_id,
            LeavePlan.year == year,
            LeavePlan.planned_start_date <= planned_end_date,
            LeavePlan.planned_end_date >= planned_start_date,
        )
        if exclude_plan_id is not None:
            stmt = stmt.where(LeavePlan.id != exclude_plan_id)
        return list(self.db.execute(stmt).scalars().all())

    def aggregate_by_employee_for_year(self, year: int) -> list[dict]:
        """
        Planned-days-per-employee for the year, for a future 'team leave
        planning overview' widget (PM req #6: 'design so planning
        integrates cleanly with future ... workflows' — this is that
        integration surface, read-only and additive, not wired into any
        endpoint yet).

        Day counts are summed in Python, not SQL: date-minus-date
        arithmetic isn't portable across dialects — it returns the correct
        day count in Postgres but silently returns 0 in SQLite (confirmed
        by hand — no error, just wrong data). Since this codebase's tests
        run against a SQLite fixture (see tests/integration/conftest.py)
        while production is Postgres-only, doing the subtraction here
        keeps this method correct under both without relying on a
        dialect-specific SQL expression that only one of them supports.
        """
        stmt = (
            select(LeavePlan.employee_id, LeavePlan.planned_start_date, LeavePlan.planned_end_date)
            .where(LeavePlan.year == year)
        )
        rows = self.db.execute(stmt).all()

        by_employee: dict[int, dict] = {}
        for employee_id, start, end in rows:
            entry = by_employee.setdefault(employee_id, {"plan_count": 0, "planned_days": 0})
            entry["plan_count"] += 1
            entry["planned_days"] += (end - start).days + 1

        if not by_employee:
            return []

        usernames = dict(
            self.db.execute(
                select(User.id, User.username).where(User.id.in_(by_employee.keys()))
            ).all()
        )
        return [
            {
                "employee_username": usernames.get(employee_id, f"user_{employee_id}"),
                "plan_count": data["plan_count"],
                "planned_days": data["planned_days"],
            }
            for employee_id, data in sorted(by_employee.items(), key=lambda kv: usernames.get(kv[0], ""))
        ]
