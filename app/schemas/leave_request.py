"""
app/schemas/leave_request.py
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeavePreviewRequest(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    is_half_day: bool = False

    @model_validator(mode="after")
    def _validate_range(self) -> "LeavePreviewRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        if self.is_half_day and self.end_date != self.start_date:
            raise ValueError("is_half_day only applies to a single-day request")
        return self


class LeavePreviewResponse(BaseModel):
    """
    Pure calculation result — never written to the database. Warnings are
    returned as data, not raised as errors: preview informs, it never blocks
    (only actual submission enforces business rules as hard failures).
    """

    working_days_count: Decimal
    holidays_in_range: list[date]
    weekends_in_range: list[date]
    current_balance: Decimal | None
    balance_after: Decimal | None
    attachment_required: bool
    warnings: list[str]


class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    is_half_day: bool = False
    reason: str = Field(min_length=3, max_length=2000)
    attachment_path: str | None = None  # populated by the endpoint after file upload (task 31)

    @model_validator(mode="after")
    def _validate_range(self) -> "LeaveRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        if self.is_half_day and self.end_date != self.start_date:
            raise ValueError("is_half_day only applies to a single-day request")
        return self


class LeaveRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    is_half_day: bool
    working_days_count: Decimal
    reason: str
    status: str
    admin_comment: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    attachment_path: str | None
    created_at: datetime
    cancelled_at: datetime | None


class AttachmentUploadResponse(BaseModel):
    """Returned by POST /leave-requests/attachments — pass attachment_path
    straight into LeaveRequestCreate.attachment_path on the follow-up submit."""

    attachment_path: str


class LeaveRejectRequest(BaseModel):
    admin_comment: str = Field(min_length=3, max_length=2000)


class BulkApproveRequest(BaseModel):
    request_ids: list[int] = Field(min_length=1, max_length=200)
    admin_comment: str | None = None


class BulkApproveResultItem(BaseModel):
    request_id: int
    success: bool
    detail: str | None = None


class BulkApproveResponse(BaseModel):
    results: list[BulkApproveResultItem]
    approved_count: int
    failed_count: int


class LeaveCalendarEntryResponse(BaseModel):
    employee_username: str
    leave_type_code: str
    leave_type_display_name: str
    start_date: date
    end_date: date


class EmployeeLeaveDaysSummary(BaseModel):
    employee_username: str
    total_days: Decimal


class LeaveTypeDaysSummary(BaseModel):
    leave_type_code: str
    total_days: Decimal


class LeaveStatisticsResponse(BaseModel):
    total_requests: int
    total_days: Decimal
    by_employee: list[EmployeeLeaveDaysSummary]
    by_leave_type: list[LeaveTypeDaysSummary]
