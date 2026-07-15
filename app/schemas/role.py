"""
app/schemas/role.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: str | None


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """
    name/description are editable on any role. permission_codes is accepted
    here too, but RoleService rejects it for system roles (admin/employee) —
    see app/core/permissions.py for why: their permission sets are mirrored
    in a hardcoded fallback used for legacy (role_id=NULL) users, and editing
    them via this endpoint would silently desync that fallback.
    """

    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] | None = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_system_role: bool
    permissions: list[PermissionResponse]
    created_at: datetime

    @classmethod
    def from_model(cls, role) -> "RoleResponse":  # noqa: ANN001 — avoids circular import on Role
        return cls(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            permissions=[PermissionResponse.model_validate(p) for p in role.permissions],
            created_at=role.created_at,
        )
