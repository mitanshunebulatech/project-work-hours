"""
app/schemas/leave_policy.py
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeavePolicyUpdate(BaseModel):
    """Admin-only partial update. Every field optional; only what's provided changes."""

    annual_quota_days: Decimal | None = Field(default=None, gt=0)
    max_consecutive_days: int | None = Field(default=None, gt=0)
    min_notice_days: int | None = Field(default=None, ge=0)
    carry_forward_cap_days: Decimal | None = Field(default=None, ge=0)
    carry_forward_expiry_month: int | None = Field(default=None, ge=1, le=12)
    accrual_frequency: str | None = None

    @model_validator(mode="after")
    def _validate_carry_forward_pair(self) -> "LeavePolicyUpdate":
        # Mirrors the DB-level chk_carry_forward_not_exceed_quota constraint —
        # only checkable here when both values are present in the same update;
        # the DB constraint remains the final source of truth (defense in depth,
        # same dual-layer pattern as WorkEntryCreate's hours validation).
        if (
            self.carry_forward_cap_days is not None
            and self.annual_quota_days is not None
            and self.carry_forward_cap_days > self.annual_quota_days
        ):
            raise ValueError("carry_forward_cap_days cannot exceed annual_quota_days")
        return self


class LeavePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    leave_type_id: int
    annual_quota_days: Decimal
    max_consecutive_days: int
    min_notice_days: int
    carry_forward_cap_days: Decimal | None
    carry_forward_expiry_month: int | None
    accrual_frequency: str
    effective_year: int
    created_at: datetime
