"""
app/schemas/user.py
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import _validate_password_complexity

Role = Literal["admin", "employee"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr | None = None
    password: str = Field(min_length=8)
    role: Role = "employee"

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_complexity(value)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    created_at: datetime


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None
    role: str
