"""
app/schemas/onboarding.py
The single combined "onboard a new employee" request — PM item 7: create
User, generate a secure password, assign role + department, create
EmployeeProfile, send the welcome email — one transaction, one entry
point. Distinct from EmployeeProfileAdminCreate (app/schemas/employee_profile.py),
which assumes a User already exists.

joining_date / department_id / designation / last_name are required here
(PM req #7: onboarding must properly capture DOJ, Department, Designation,
and a full identity — a single-word name isn't sufficient on an HR
record) — enforced at this schema layer only. The underlying
employee_profiles columns stay nullable=True at the DB level for now:
existing rows onboarded before this change may already have NULLs there,
and flipping the columns to NOT NULL without first auditing/backfilling
that data would break migrations against real data. DB-level enforcement
is a deliberate follow-up, not done here.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.employee_profile import _validate_pan_format


class EmployeeOnboardingRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=75)
    last_name: str = Field(min_length=1, max_length=75)
    email: EmailStr
    personal_phone_number: str | None = Field(default=None, max_length=20)
    emergency_phone_number: str | None = Field(default=None, max_length=20)
    present_address: str | None = Field(default=None, max_length=500)
    joining_date: date
    birth_date: date | None = None
    department_id: int
    designation: str = Field(min_length=1, max_length=100)
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
