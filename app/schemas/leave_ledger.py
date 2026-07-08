"""
app/schemas/leave_ledger.py
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LedgerTransactionType(str, Enum):
    ANNUAL_GRANT = "annual_grant"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    CARRY_FORWARD = "carry_forward"
    CORRECTION = "correction"
    CANCELLATION_REVERSAL = "cancellation_reversal"
    LEAVE_DEBIT = "leave_debit"


class LedgerAdjustmentCreate(BaseModel):
    employee_id: int
    leave_type_id: int
    year: int | None = Field(default=None, description="Defaults to current year if omitted")
    amount_days: Decimal = Field(
        decimal_places=2, description="Signed: positive to credit, negative to debit"
    )
    transaction_type: LedgerTransactionType
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def amount_not_zero(self) -> "LedgerAdjustmentCreate":
        if self.amount_days == 0:
            raise ValueError("amount_days cannot be zero")
        return self


class LeaveLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    leave_type_id: int
    leave_request_id: int | None
    transaction_type: str
    amount_days: Decimal
    reason: str | None
    created_at: datetime


class LeaveBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    leave_type_id: int
    year: int
    total_credited_days: Decimal
    total_debited_days: Decimal
    remaining_days: Decimal
    updated_at: datetime


class LedgerAdjustmentResponse(BaseModel):
    ledger_entry: LeaveLedgerEntryResponse
    balance: LeaveBalanceResponse


class AnnualGrantRunResponse(BaseModel):
    year: int
    granted: int
    skipped: int
    errors: list[str]
