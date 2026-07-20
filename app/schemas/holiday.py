"""
app/schemas/holiday.py
"""
from datetime import date as date_, datetime

from pydantic import BaseModel, ConfigDict, Field


class HolidayCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    date: date_
    # Deliberately no year field here — always derived from date in
    # HolidayService.create_holiday, never admin-entered, so the two can
    # never drift apart (PM req #1).


class HolidayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    date: date_ | None = None
    is_active: bool | None = None
    # No is_published here either — publishing is a dedicated bulk action
    # (HolidayService.publish_year/unpublish_year, PM req #3), not a field
    # an admin flips per-holiday, so a single holiday can't accidentally
    # become visible to employees while the rest of its year stays hidden.


class HolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date_
    year: int
    is_active: bool
    is_published: bool
    created_at: datetime
