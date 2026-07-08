"""
app/schemas/holiday.py
"""

from datetime import date as date_, datetime

from pydantic import BaseModel, ConfigDict, Field


class HolidayCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    date: date_


class HolidayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    date: date_ | None = None
    is_active: bool | None = None


class HolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date_
    is_active: bool
    created_at: datetime
