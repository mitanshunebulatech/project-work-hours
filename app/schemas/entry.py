"""
app/schemas/entry.py
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["pending", "approved", "rejected"]


class WorkEntryCreate(BaseModel):
    project_id: int
    entry_date: date
    hours_worked: Decimal = Field(gt=0, le=24, decimal_places=2)
    remarks: str | None = Field(default=None, max_length=2000)

    @field_validator("entry_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("entry_date cannot be in the future")
        return value


class WorkEntryUpdate(BaseModel):
    hours_worked: Decimal | None = Field(default=None, gt=0, le=24, decimal_places=2)
    remarks: str | None = Field(default=None, max_length=2000)


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
            hours_worked=entry.hours_worked,
            remarks=entry.remarks,
            status=entry.status,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
