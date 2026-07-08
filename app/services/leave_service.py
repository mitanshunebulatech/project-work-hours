"""
app/services/leave_service.py

Business rules (documented here, same convention as EntryService):
BR-01: working_days_count excludes weekends (Sat/Sun) and active company
       holidays — a date range can span 7 calendar days and still only
       count as 3 working days.
BR-02: a half-day request must be a single-day range (enforced at the
       schema level too — this is defense in depth).
BR-03: balance/attachment checks only apply when the leave type is paid
       AND has a policy row for the relevant year (LOP and WFH have
       neither, by design — see migration 0013's docstring).
BR-04: preview_request() NEVER raises on business-rule violations — it
       reports them as warnings. Only create_request() turns these same
       checks into hard failures.
BR-05: create_request() writes NO ledger/balance changes at all — a
       pending request has zero effect on balance. Only approval (a later
       task) debits the ledger. This is why balance_after in preview can
       go negative without blocking submission — approval is where the
       real enforcement happens, matching Phase 3's admin-approval design.
BR-06: no overlapping pending/approved request for the same employee is
       allowed — checked against LeaveRequestRepository.find_overlapping().
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.holiday_repo import HolidayRepository
from app.db.repositories.leave_balance_repo import LeaveBalanceRepository
from app.db.repositories.leave_policy_repo import LeavePolicyRepository
from app.db.repositories.leave_request_repo import LeaveRequestRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.schemas.leave_request import LeavePreviewRequest, LeavePreviewResponse, LeaveRequestCreate

WEEKEND_WEEKDAYS = {5, 6}  # Monday=0 ... Saturday=5, Sunday=6


class LeaveService:
    def __init__(self, db: Session):
        self.db = db
        self.leave_type_repo = LeaveTypeRepository(db)
        self.leave_policy_repo = LeavePolicyRepository(db)
        self.leave_balance_repo = LeaveBalanceRepository(db)
        self.leave_request_repo = LeaveRequestRepository(db)
        self.holiday_repo = HolidayRepository(db)
        self.audit_repo = AuditRepository(db)

    def _get_active_leave_type(self, leave_type_id: int) -> LeaveType:
        leave_type = self.leave_type_repo.get(leave_type_id)
        if leave_type is None or not leave_type.is_active:
            raise NotFoundError("Leave type not found or inactive")
        return leave_type

    def _iter_dates(self, start: date, end: date):
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    def _calculate_working_days(
        self, *, start_date: date, end_date: date, is_half_day: bool, holiday_dates: set[date]
    ) -> tuple[Decimal, list[date]]:
        """
        Returns (working_days_count, weekends_in_range). Each calendar day in
        the range is checked once: weekend or holiday -> contributes 0,
        otherwise contributes 1 (or 0.5 for a half-day single-day request).
        """
        weekends_in_range: list[date] = []
        working_days = Decimal("0")

        for day in self._iter_dates(start_date, end_date):
            is_weekend = day.weekday() in WEEKEND_WEEKDAYS
            is_holiday = day in holiday_dates

            if is_weekend:
                weekends_in_range.append(day)

            if is_weekend or is_holiday:
                continue

            working_days += Decimal("0.5") if is_half_day else Decimal("1")

        return working_days, weekends_in_range

    def preview_request(self, *, employee_id: int, payload: LeavePreviewRequest) -> LeavePreviewResponse:
        leave_type = self._get_active_leave_type(payload.leave_type_id)

        holiday_dates = self.holiday_repo.get_holiday_dates_in_range(
            payload.start_date, payload.end_date
        )
        working_days_count, weekends_in_range = self._calculate_working_days(
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_half_day=payload.is_half_day,
            holiday_dates=holiday_dates,
        )
        holidays_in_range = sorted(
            d for d in holiday_dates if payload.start_date <= d <= payload.end_date
        )

        warnings: list[str] = []

        if working_days_count == 0:
            warnings.append(
                "The selected date range contains no working days (all weekends/holidays)."
            )

        attachment_required = (
            leave_type.requires_attachment_after_days is not None
            and working_days_count > leave_type.requires_attachment_after_days
        )

        current_balance: Decimal | None = None
        balance_after: Decimal | None = None

        policy = None
        if leave_type.is_paid:
            policy = self.leave_policy_repo.get_for_type_year(
                leave_type_id=leave_type.id, year=payload.start_date.year
            )

        if policy is not None:
            balance = self.leave_balance_repo.get_or_create_for_year(
                employee_id=employee_id, leave_type_id=leave_type.id, year=payload.start_date.year
            )
            current_balance = balance.remaining_days
            balance_after = current_balance - working_days_count

            if balance_after < 0:
                warnings.append(
                    f"Insufficient balance: {current_balance} day(s) remaining, "
                    f"{working_days_count} requested."
                )

            if working_days_count > policy.max_consecutive_days:
                warnings.append(
                    f"This exceeds the maximum of {policy.max_consecutive_days} "
                    f"consecutive day(s) allowed for {leave_type.display_name}."
                )

            notice_days = (payload.start_date - date.today()).days
            if notice_days < policy.min_notice_days:
                warnings.append(
                    f"{leave_type.display_name} normally requires "
                    f"{policy.min_notice_days} day(s) advance notice."
                )

        # BR-02 (schema already enforces this too — defense in depth)
        if payload.is_half_day and payload.start_date != payload.end_date:
            warnings.append("Half-day only applies to a single-day request.")

        return LeavePreviewResponse(
            working_days_count=working_days_count,
            holidays_in_range=holidays_in_range,
            weekends_in_range=weekends_in_range,
            current_balance=current_balance,
            balance_after=balance_after,
            attachment_required=attachment_required,
            warnings=warnings,
        )

    def create_request(
        self,
        *,
        employee_id: int,
        payload: LeaveRequestCreate,
        ip_address: str | None = None,
    ) -> LeaveRequest:
        """
        Runs the same calculation as preview_request(), but every warning
        there becomes a hard BusinessRuleError/ConflictError here. No
        ledger/balance write happens in this method (BR-05) — the request
        is saved as 'pending' only.
        """
        leave_type = self._get_active_leave_type(payload.leave_type_id)

        # --- date sanity beyond the schema's own end>=start check ---
        if payload.start_date < date.today():
            # Only certain types (Sick, retroactive-friendly) would ever be
            # allowed to backdate. With no such exception configured yet,
            # backdating is rejected outright for every type.
            raise BusinessRuleError("Leave cannot be requested for a date in the past.")

        holiday_dates = self.holiday_repo.get_holiday_dates_in_range(
            payload.start_date, payload.end_date
        )
        working_days_count, _weekends = self._calculate_working_days(
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_half_day=payload.is_half_day,
            holiday_dates=holiday_dates,
        )

        if working_days_count == 0:
            raise BusinessRuleError(
                "The selected date range contains no working days (all weekends/holidays)."
            )

        # --- BR-06: conflict detection, same employee only ---
        overlapping = self.leave_request_repo.find_overlapping(
            employee_id=employee_id, start_date=payload.start_date, end_date=payload.end_date
        )
        if overlapping:
            raise ConflictError(
                "You already have a pending or approved leave request overlapping these dates."
            )

        policy = None
        if leave_type.is_paid:
            policy = self.leave_policy_repo.get_for_type_year(
                leave_type_id=leave_type.id, year=payload.start_date.year
            )

        if policy is not None:
            if working_days_count > policy.max_consecutive_days:
                raise BusinessRuleError(
                    f"{leave_type.display_name} allows a maximum of "
                    f"{policy.max_consecutive_days} consecutive day(s)."
                )

            notice_days = (payload.start_date - date.today()).days
            if notice_days < policy.min_notice_days:
                raise BusinessRuleError(
                    f"{leave_type.display_name} requires at least "
                    f"{policy.min_notice_days} day(s) advance notice."
                )

            balance = self.leave_balance_repo.get_or_create_for_year(
                employee_id=employee_id, leave_type_id=leave_type.id, year=payload.start_date.year
            )
            if balance.remaining_days < working_days_count:
                raise BusinessRuleError(
                    f"Insufficient balance: {balance.remaining_days} day(s) remaining, "
                    f"{working_days_count} requested."
                )

        # Attachment requirement is enforced at the API layer (task 31, once
        # multipart file upload exists) — this service method only computes
        # whether one *would* be required, so the endpoint can check
        # `payload` against it before ever calling create_request().
        attachment_required = (
            leave_type.requires_attachment_after_days is not None
            and working_days_count > leave_type.requires_attachment_after_days
        )
        if attachment_required and not payload.attachment_path:
            raise BusinessRuleError(
                f"{leave_type.display_name} requires an attachment for requests longer than "
                f"{leave_type.requires_attachment_after_days} day(s)."
            )

        new_request = LeaveRequest(
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_half_day=payload.is_half_day,
            working_days_count=working_days_count,
            reason=payload.reason,
            status="pending",
            attachment_path=payload.attachment_path,
        )
        created = self.leave_request_repo.create(new_request)

        self.audit_repo.log(
            actor_id=employee_id,
            table_name="leave_requests",
            operation="INSERT",
            record_id=created.id,
            after_data={
                "leave_type_id": leave_type.id,
                "start_date": str(payload.start_date),
                "end_date": str(payload.end_date),
                "working_days_count": str(working_days_count),
                "status": "pending",
            },
            ip_address=ip_address,
        )
        self.db.commit()

        return created
