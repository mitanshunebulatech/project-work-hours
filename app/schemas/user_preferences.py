"""
app/schemas/user_preferences.py

Settings page — account-level preferences, distinct from EmployeeProfile
(personal/HR info, see app/schemas/employee_profile.py). Theme isn't here:
it's client-side only (localStorage), nothing for the backend to store.
"""

from pydantic import BaseModel, Field


class UserPreferencesResponse(BaseModel):
    timezone: str
    email_notifications_enabled: bool


class UserPreferencesUpdate(BaseModel):
    timezone: str | None = Field(default=None, min_length=1, max_length=50)
    email_notifications_enabled: bool | None = None
