"""
app/schemas/leave_plan.py
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.leave_request import EmployeeBrief


class LeavePlanCreate(BaseModel):
    leave_type_id: int
    planned_start_date: date
    planned_end_date: date
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def end_not_before_start(self) -> "LeavePlanCreate":
        if self.planned_end_date < self.planned_start_date:
            raise ValueError("planned_end_date cannot be before planned_start_date")
        return self


class LeavePlanUpdate(BaseModel):
    leave_type_id: int | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def end_not_before_start(self) -> "LeavePlanUpdate":
        if (
            self.planned_start_date is not None
            and self.planned_end_date is not None
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValueError("planned_end_date cannot be before planned_start_date")
        return self


class LeavePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    leave_type_id: int
    planned_start_date: date
    planned_end_date: date
    year: int
    reason: str | None
    created_at: datetime
    employee: EmployeeBrief | None = None
