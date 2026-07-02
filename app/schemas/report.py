"""
app/schemas/report.py
"""

from pydantic import BaseModel


class EmployeeHoursSummary(BaseModel):
    employee_username: str
    total_hours: float


class ProjectHoursSummary(BaseModel):
    project_name: str
    total_hours: float


class ReportSummaryResponse(BaseModel):
    total_hours: float
    total_entries: int
    by_employee: list[EmployeeHoursSummary]
    by_project: list[ProjectHoursSummary]
