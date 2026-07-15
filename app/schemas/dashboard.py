"""
app/schemas/dashboard.py
Response contract for the admin operations dashboard (GET /dashboard/summary
— PM req #1). Deliberately one composed response rather than one endpoint
per widget: the dashboard renders every widget on load, so one round trip
beats six, and there's no case where a caller wants only one widget's data.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TodayTimesheetSummary(BaseModel):
    total_entries: int
    total_hours: float
    pending_approvals: int  # today-scoped, per PM decision — not the full backlog


class EmployeeOnLeaveToday(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    employee_name: str
    leave_type_code: str
    leave_type_name: str
    is_half_day: bool
    half_day_slot: str | None = None


class MissingTimesheetEmployee(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    employee_name: str


class RecentActivityItem(BaseModel):
    activity_type: str  # "timesheet" | "leave_request"
    description: str
    actor_name: str
    status: str
    occurred_at: datetime


class DashboardLeaveCalendarEntry(BaseModel):
    employee_name: str
    leave_type_code: str
    start_date: date
    end_date: date
    is_half_day: bool


class DashboardSummaryResponse(BaseModel):
    today: date
    today_timesheets: TodayTimesheetSummary
    employees_on_leave_today: list[EmployeeOnLeaveToday]
    missing_timesheets: list[MissingTimesheetEmployee]
    recent_activities: list[RecentActivityItem]
    leave_calendar_this_month: list[DashboardLeaveCalendarEntry]
