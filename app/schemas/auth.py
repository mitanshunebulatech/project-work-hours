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


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_complexity(value)
