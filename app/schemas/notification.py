"""
app/schemas/notification.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    reference_id: int
    message: str
    is_read: bool
    created_at: datetime


class MarkAllReadResponse(BaseModel):
    marked_count: int
