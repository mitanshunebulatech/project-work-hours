"""
app/schemas/auth.py
"""

import re

from pydantic import BaseModel, Field, field_validator

_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def _validate_password_complexity(value: str) -> str:
    """BR-09: >= 8 chars, at least one letter and one digit."""
    if not _PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be at least 8 characters and contain at least one letter and one digit"
        )
    return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    # PM req (Part 4): frontend redirects to a forced-change screen instead
    # of the dashboard when this is true. The backend enforces this
    # independently too (see app/core/deps.py get_current_user) — this
    # field is a UX convenience, not the actual security boundary.
    must_change_password: bool = False


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Included so a token refresh (e.g. on page reload) doesn't require an
    # extra round-trip 403 before the frontend knows to show the forced-
    # change screen again.
    must_change_password: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_complexity(value)
