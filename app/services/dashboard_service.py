"""
app/services/dashboard_service.py
Orchestrates the admin operations dashboard (PM req #1: "operations-focused,
not employee-focused" — today's data by default, no personal stat cards).

Reads only, through WorkEntryRepository and LeaveRequestRepository — no
direct DB access here, keeping the Router -> Service -> Repository boundary
the rest of the codebase follows. Nothing here writes anything, so there's
no audit-log concern for this service (audit logging is for mutations).
"""

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories.entry_repo import WorkEntryRepository
from app.db.repositories.leave_request_repo import LeaveRequestRepository
from app.schemas.dashboard import (
    DashboardLeaveCalendarEntry,
    DashboardSummaryResponse,
    EmployeeOnLeaveToday,
    MissingTimesheetEmployee,
    RecentActivityItem,
    TodayTimesheetSummary,
)

# PM Q&A: "Recent Activities" pulls from timesheets + leave requests only,
# not audit_logs (which is broader/cross-module and would pull in things
# like project or department edits that don't belong on an activity feed
# meant to answer "what are employees doing today").
RECENT_ACTIVITY_LIMIT = 10


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = WorkEntryRepository(db)
        self.leave_repo = LeaveRequestRepository(db)

    def get_summary(self) -> DashboardSummaryResponse:
        today = date.today()

        today_timesheets = self._today_timesheets(today)
        on_leave_today = self.leave_repo.get_on_leave_for_date(today)
        employees_on_leave = [self._to_on_leave_item(req) for req in on_leave_today]

        # Anyone on approved leave today isn't expected to log hours, so
        # they're excluded from "missing" rather than flagged as a gap.
        on_leave_employee_ids = {req.employee_id for req in on_leave_today}
        missing = self.entry_repo.get_missing_timesheet_employees(today, on_leave_employee_ids)
        missing_timesheets = [
            MissingTimesheetEmployee(employee_id=u.id, employee_name=u.username) for u in missing
        ]

        recent_activities = self._recent_activities()
        leave_calendar = self._leave_calendar_this_month(today)

        return DashboardSummaryResponse(
            today=today,
            today_timesheets=today_timesheets,
            employees_on_leave_today=employees_on_leave,
            missing_timesheets=missing_timesheets,
            recent_activities=recent_activities,
            leave_calendar_this_month=leave_calendar,
        )

    def _today_timesheets(self, today: date) -> TodayTimesheetSummary:
        agg = self.entry_repo.aggregate_summary(date_from=today, date_to=today)
        pending_today = self.entry_repo.get_status_count_for_date(today, "pending")
        return TodayTimesheetSummary(
            total_entries=agg["total_entries"],
            total_hours=agg["total_hours"],
            pending_approvals=pending_today,
        )

    @staticmethod
    def _to_on_leave_item(req) -> EmployeeOnLeaveToday:
        return EmployeeOnLeaveToday(
            employee_id=req.employee_id,
            employee_name=req.employee.username,
            leave_type_code=req.leave_type.code,
            leave_type_name=req.leave_type.display_name,
            is_half_day=req.is_half_day,
            half_day_slot=req.half_day_slot,
        )

    def _recent_activities(self) -> list[RecentActivityItem]:
        recent_entries = self.entry_repo.get_recent(RECENT_ACTIVITY_LIMIT)
        recent_leave = self.leave_repo.get_recent(RECENT_ACTIVITY_LIMIT)

        activities = [
            RecentActivityItem(
                activity_type="timesheet",
                description=f"{e.employee.username} logged {e.hours_worked}h on {e.project.project_name}",
                actor_name=e.employee.username,
                status=e.status,
                occurred_at=e.created_at,
            )
            for e in recent_entries
        ]
        activities += [
            RecentActivityItem(
                activity_type="leave_request",
                description=(
                    f"{r.employee.username} requested {r.leave_type.display_name} "
                    f"({r.start_date.isoformat()}..{r.end_date.isoformat()})"
                ),
                actor_name=r.employee.username,
                status=r.status,
                occurred_at=r.created_at,
            )
            for r in recent_leave
        ]
        # Two separately-limited queries merged client-side, then re-sorted
        # and re-capped — simpler and fast enough at this scale than a SQL
        # UNION across two different tables' shapes, and keeps each
        # repository's query un-coupled from the other's table.
        activities.sort(key=lambda a: a.occurred_at, reverse=True)
        return activities[:RECENT_ACTIVITY_LIMIT]

    def _leave_calendar_this_month(self, today: date) -> list[DashboardLeaveCalendarEntry]:
        # Reuses LeaveRequestRepository.get_calendar_entries — the same
        # query the standalone Leave Calendar page uses — rather than a new
        # dashboard-specific query, per PM req #12 (DRY, reuse shared
        # services wherever possible).
        entries = self.leave_repo.get_calendar_entries(month=today.month, year=today.year)
        return [
            DashboardLeaveCalendarEntry(
                employee_name=req.employee.username,
                leave_type_code=req.leave_type.code,
                start_date=req.start_date,
                end_date=req.end_date,
                is_half_day=req.is_half_day,
            )
            for req in entries
        ]
