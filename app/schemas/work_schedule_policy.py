"""
app/schemas/work_schedule_policy.py
"""

from datetime import time

from pydantic import BaseModel, model_validator


class WorkSchedulePolicyResponse(BaseModel):
    first_half_start: time
    first_half_end: time
    second_half_start: time
    second_half_end: time


class WorkSchedulePolicyUpdate(BaseModel):
    first_half_start: time
    first_half_end: time
    second_half_start: time
    second_half_end: time

    @model_validator(mode="after")
    def _validate_ranges(self) -> "WorkSchedulePolicyUpdate":
        if self.first_half_end <= self.first_half_start:
            raise ValueError("first_half_end must be after first_half_start")
        if self.second_half_end <= self.second_half_start:
            raise ValueError("second_half_end must be after second_half_start")
        if self.second_half_start < self.first_half_end:
            raise ValueError("second_half_start cannot be before first_half_end")
        return self
