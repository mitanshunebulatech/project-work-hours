"""
app/schemas/leave_type.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeaveTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    display_name: str
    is_paid: bool
    requires_attachment_after_days: int | None
    allows_half_day: bool
    is_active: bool
    created_at: datetime
