"""
app/schemas/employee_profile.py
"""

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Indian PAN format: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F).
_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _validate_pan_format(value: str) -> str:
    normalized = value.strip().upper()
    if not _PAN_PATTERN.match(normalized):
        raise ValueError("PAN must be in the format AAAAA9999A (5 letters, 4 digits, 1 letter)")
    return normalized


def _mask_pan(value: str | None) -> str | None:
    if not value:
        return None
    return "•" * 5 + value[-5:] if len(value) >= 5 else "••••••"


class EmployeeProfileSelfUpdate(BaseModel):
    """
    Fields an employee may edit on their own profile — PM item 10's
    "editable fields" list: Phone Number, Emergency Contact, Address,
    Profile Picture (separate multipart endpoint, not here), Personal
    Information (years_of_experience/date_of_birth/pan_number fall under
    this). Deliberately excludes department_id, designation,
    date_of_joining, and first_name/last_name — those are
    organizational/HR-of-record data, changed via the admin-facing endpoint
    only (app/api/v1/endpoints/employees.py), matching PM item 10's
    read-only list (Name, Email, Employee ID, Department, Joining Date,
    Designation).
    """

    phone_number: str | None = Field(default=None, max_length=20)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    present_address: str | None = Field(default=None, max_length=500)
    years_of_experience: Decimal | None = None
    date_of_birth: date | None = None
    pan_number: str | None = Field(default=None, min_length=10, max_length=10)

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_pan_format(value)


class EmployeeProfileAdminCreate(BaseModel):
    """Admin-only: onboard an employee profile for an existing user account.
    Prefer POST /employees/onboard (app/schemas/onboarding.py) for new
    hires — this stays for backfilling profiles onto accounts that predate
    the onboarding module, or were created via the plain Users screen."""

    user_id: int
    full_name: str = Field(min_length=1, max_length=150)
    department_id: int | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    present_address: str | None = Field(default=None, max_length=500)
    designation: str | None = Field(default=None, max_length=100)
    years_of_experience: Decimal | None = None
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
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    present_address: str | None = Field(default=None, max_length=500)
    designation: str | None = Field(default=None, max_length=100)
    years_of_experience: Decimal | None = None
    pan_number: str | None = Field(default=None, min_length=10, max_length=10)

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_pan_format(value)


# Free string, not a DB enum (see IdentityDocument model) — validated here
# at the API boundary instead. Shared by both the admin view-only endpoint
# and the employee self-service upload endpoint.
ALLOWED_DOCUMENT_TYPES = frozenset({"PAN", "AADHAAR", "PASSPORT", "OTHER"})


class IdentityDocumentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: int
    document_type: str
    document_number_masked: str | None
    file_path: str
    uploaded_at: datetime

    @classmethod
    def from_model(cls, doc) -> "IdentityDocumentBrief":  # noqa: ANN001
        masked = None
        if doc.document_number:
            masked = (
                "•" * 5 + doc.document_number[-5:]
                if len(doc.document_number) >= 5
                else "••••••"
            )
        return cls(
            id=doc.id,
            document_type=doc.document_type,
            document_number_masked=masked,
            file_path=doc.file_path,
            uploaded_at=doc.uploaded_at,
        )


class EmployeeProfileResponse(BaseModel):
    """
    PAN is always masked on the way out (last 5 characters only) — this is a
    write-oriented field (like a password), not something the API should
    ever hand back in full once stored.
    """

    model_config = ConfigDict(from_attributes=False)

    id: int
    user_id: int
    department_id: int | None
    employee_code: str
    full_name: str
    first_name: str
    last_name: str | None
    date_of_birth: date | None
    date_of_joining: date | None
    phone_number: str | None
    emergency_contact_phone: str | None
    present_address: str | None
    designation: str | None
    years_of_experience: Decimal | None
    profile_picture_path: str | None
    pan_number_masked: str | None
    identity_documents: list[IdentityDocumentBrief] = []
    created_at: datetime

    @classmethod
    def from_model(cls, profile) -> "EmployeeProfileResponse":  # noqa: ANN001
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            department_id=profile.department_id,
            employee_code=profile.employee_code,
            full_name=profile.full_name,
            first_name=profile.first_name,
            last_name=profile.last_name,
            date_of_birth=profile.date_of_birth,
            date_of_joining=profile.date_of_joining,
            phone_number=profile.phone_number,
            emergency_contact_phone=profile.emergency_contact_phone,
            present_address=profile.present_address,
            designation=profile.designation,
            years_of_experience=profile.years_of_experience,
            profile_picture_path=profile.profile_picture_path,
            pan_number_masked=_mask_pan(profile.pan_number),
            identity_documents=[
                IdentityDocumentBrief.from_model(d) for d in profile.identity_documents
            ],
            created_at=profile.created_at,
        )


class MyProfileResponse(BaseModel):
    """
    GET /profile/me response: base User fields merged with EmployeeProfile
    fields (all None if HR hasn't created a profile for this account yet —
    absence of a profile is a normal state, not an error, per FR-E08).
    Read-only (HR-of-record, PM item 10): full_name/first_name/last_name,
    employee_code, department_id, date_of_joining, designation.
    Editable (PM item 10, enforced server-side by EmployeeProfileSelfUpdate,
    not just by what the frontend greys out): phone_number,
    emergency_contact_phone, present_address, years_of_experience,
    date_of_birth, pan_number, profile_picture_path (via its own endpoint).
    """

    model_config = ConfigDict(from_attributes=False)

    id: int
    username: str
    email: str | None
    role: str
    must_change_password: bool

    department_id: int | None = None
    employee_code: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_joining: date | None = None
    designation: str | None = None

    phone_number: str | None = None
    emergency_contact_phone: str | None = None
    present_address: str | None = None
    years_of_experience: Decimal | None = None
    date_of_birth: date | None = None
    profile_picture_path: str | None = None
    pan_number_masked: str | None = None

    @classmethod
    def build(cls, user, profile) -> "MyProfileResponse":  # noqa: ANN001
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            must_change_password=user.must_change_password,
            department_id=profile.department_id if profile else None,
            employee_code=profile.employee_code if profile else None,
            full_name=profile.full_name if profile else None,
            first_name=profile.first_name if profile else None,
            last_name=profile.last_name if profile else None,
            date_of_joining=profile.date_of_joining if profile else None,
            designation=profile.designation if profile else None,
            phone_number=profile.phone_number if profile else None,
            emergency_contact_phone=profile.emergency_contact_phone if profile else None,
            present_address=profile.present_address if profile else None,
            years_of_experience=profile.years_of_experience if profile else None,
            date_of_birth=profile.date_of_birth if profile else None,
            profile_picture_path=profile.profile_picture_path if profile else None,
            pan_number_masked=_mask_pan(profile.pan_number) if profile else None,
        )
