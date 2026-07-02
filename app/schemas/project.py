"""
app/schemas/project.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    project_name: str = Field(min_length=2, max_length=200)
    description: str | None = None


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_name: str
    description: str | None
    is_active: bool
    created_at: datetime
