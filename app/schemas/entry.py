"""
app/schemas/entry.py
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["pending", "approved", "rejected"]


class WorkEntryCreate(BaseModel):
    project_id: int
    entry_date: date
    start_time: time
    end_time: time
    hours_worked: Decimal = Field(gt=0, le=24, decimal_places=2)
    remarks: str | None = Field(default=None, max_length=2000)

    @field_validator("entry_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("entry_date cannot be in the future")
        return value

    @model_validator(mode="after")
    def end_after_start(self) -> "WorkEntryCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class WorkEntryUpdate(BaseModel):
    start_time: time | None = None
    end_time: time | None = None
    hours_worked: Decimal | None = Field(default=None, gt=0, le=24, decimal_places=2)
    remarks: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def end_after_start(self) -> "WorkEntryUpdate":
        if self.start_time is not None and self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class WorkEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_username: str
    project_id: int
    project_name: str
    entry_date: date
    start_time: time | None
    end_time: time | None
    hours_worked: Decimal
    remarks: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_with_relations(cls, entry) -> "WorkEntryResponse":
        """Builds the flattened response from a WorkEntry ORM object with employee/project eagerly loaded."""
        return cls(
            id=entry.id,
            employee_id=entry.employee_id,
            employee_username=entry.employee.username,
            project_id=entry.project_id,
            project_name=entry.project.project_name,
            entry_date=entry.entry_date,
            start_time=entry.start_time,
            end_time=entry.end_time,
            hours_worked=entry.hours_worked,
            remarks=entry.remarks,
            status=entry.status,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class EmployeeHoursSummary(BaseModel):
    employee_username: str
    total_hours: float


class ProjectHoursSummary(BaseModel):
    project_name: str
    total_hours: float


class WorkEntrySummaryResponse(BaseModel):
    total_hours: float
    total_entries: int
    by_employee: list[EmployeeHoursSummary]
    by_project: list[ProjectHoursSummary]
