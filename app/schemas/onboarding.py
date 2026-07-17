"""
app/schemas/onboarding.py
The single combined "onboard a new employee" request — PM item 7: create
User, generate a secure password, assign role + department, create
EmployeeProfile, send the welcome email — one transaction, one entry
point. Distinct from EmployeeProfileAdminCreate (app/schemas/employee_profile.py),
which assumes a User already exists.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.employee_profile import _validate_pan_format


class EmployeeOnboardingRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=75)
    last_name: str | None = Field(default=None, max_length=75)
    email: EmailStr
    personal_phone_number: str | None = Field(default=None, max_length=20)
    emergency_phone_number: str | None = Field(default=None, max_length=20)
    present_address: str | None = Field(default=None, max_length=500)
    joining_date: date | None = None
    birth_date: date | None = None
    department_id: int | None = None
    designation: str | None = Field(default=None, max_length=100)
    years_of_experience: Decimal | None = None
    pan_number: str | None = Field(default=None, min_length=10, max_length=10)
    # Mandatory per decision — PM item 7 lists "Assign Role" as a required
    # onboarding step, not an optional afterthought.
    role_id: int

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_pan_format(value)


class EmployeeOnboardingResponse(BaseModel):
    user_id: int
    employee_profile_id: int
    username: str
    email: str
    employee_code: str
    email_sent: bool
    # Shown once, here, right after creation — never returned by any other
    # endpoint afterward. If email_sent is False (no SMTP configured yet),
    # this is the ONLY way the admin ever sees it, so the frontend must
    # display it in a one-time modal and make clear it won't be shown again.
    temp_password: str
