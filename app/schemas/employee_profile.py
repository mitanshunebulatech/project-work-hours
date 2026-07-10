"""
app/schemas/employee_profile.py
"""

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Indian PAN format: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F).
_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _validate_pan_format(value: str) -> str:
    normalized = value.strip().upper()
    if not _PAN_PATTERN.match(normalized):
        raise ValueError("PAN must be in the format AAAAA9999A (5 letters, 4 digits, 1 letter)")
    return normalized


class EmployeeProfileSelfUpdate(BaseModel):
    """
    Fields an employee may edit on their own profile. Deliberately excludes
    department_id, designation, date_of_joining, and full_name — those are
    organizational/HR-of-record data, changed via the admin-facing endpoint
    only (app/api/v1/endpoints/employees.py), not self-service.
    """

    phone_number: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = None
    pan_number: str | None = Field(default=None, min_length=10, max_length=10)

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_pan_format(value)


class EmployeeProfileAdminCreate(BaseModel):
    """Admin-only: onboard an employee profile for an existing user account."""

    user_id: int
    full_name: str = Field(min_length=1, max_length=150)
    department_id: int | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    designation: str | None = Field(default=None, max_length=100)
    pan_number: str | None = Field(default=None, min_length=10, max_length=10)

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_pan_format(value)


class EmployeeProfileAdminUpdate(BaseModel):
    """Admin-only: same self-service fields, plus org-managed fields."""

    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    department_id: int | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    designation: str | None = Field(default=None, max_length=100)
    pan_number: str | None = Field(default=None, min_length=10, max_length=10)

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_pan_format(value)


class EmployeeProfileResponse(BaseModel):
    """
    PAN is always masked on the way out (last 4 characters only) — this is a
    write-oriented field (like a password), not something the API should
    ever hand back in full once stored. Editing doesn't require reading the
    old value first.
    """

    model_config = ConfigDict(from_attributes=False)

    id: int
    user_id: int
    department_id: int | None
    full_name: str
    date_of_birth: date | None
    date_of_joining: date | None
    phone_number: str | None
    designation: str | None
    pan_number_masked: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, profile) -> "EmployeeProfileResponse":  # noqa: ANN001 — avoids circular import on EmployeeProfile
        masked = None
        if profile.pan_number:
            masked = "•" * 5 + profile.pan_number[-5:] if len(profile.pan_number) >= 5 else "••••••"
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            department_id=profile.department_id,
            full_name=profile.full_name,
            date_of_birth=profile.date_of_birth,
            date_of_joining=profile.date_of_joining,
            phone_number=profile.phone_number,
            designation=profile.designation,
            pan_number_masked=masked,
            created_at=profile.created_at,
        )


class MyProfileResponse(BaseModel):
    """
    GET /profile/me response: base User fields merged with EmployeeProfile
    fields (all None if HR hasn't created a profile for this account yet —
    absence of a profile is a normal state, not an error, per FR-E08).
    """

    model_config = ConfigDict(from_attributes=False)

    id: int
    username: str
    email: str | None
    role: str
    department_id: int | None = None
    full_name: str | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    phone_number: str | None = None
    designation: str | None = None
    pan_number_masked: str | None = None

    @classmethod
    def build(cls, user, profile) -> "MyProfileResponse":  # noqa: ANN001
        masked = None
        if profile is not None and profile.pan_number:
            masked = "•" * 5 + profile.pan_number[-5:] if len(profile.pan_number) >= 5 else "••••••"
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            department_id=profile.department_id if profile else None,
            full_name=profile.full_name if profile else None,
            date_of_birth=profile.date_of_birth if profile else None,
            date_of_joining=profile.date_of_joining if profile else None,
            phone_number=profile.phone_number if profile else None,
            designation=profile.designation if profile else None,
            pan_number_masked=masked,
        )
