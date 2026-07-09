"""
app/services/leave_service.py

Business rules (documented here, same convention as EntryService):
BR-01: working_days_count excludes weekends (Sat/Sun) and active company
       holidays — a date range can span 7 calendar days and still only
       count as 3 working days.
BR-02: a half-day request must be a single-day range (enforced at the
       schema level too — this is defense in depth).
BR-03: balance/attachment checks only apply when the leave type is paid
       AND has a policy row for the relevant year (LOP has neither, by
       design — see migration 0013's docstring).
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
BR-07: GLOBAL_MAX_CONSECUTIVE_DAYS is a hard, company-wide ceiling on
       working_days_count that applies to every leave type unconditionally
       — including types with no policy row at all (e.g. LOP) and as a
       backstop even for types whose own policy allows more. A type's own
       policy.max_consecutive_days can be stricter than this (e.g. Casual
       Leave's 3, Birthday's 1) but can never effectively raise the ceiling
       above GLOBAL_MAX_CONSECUTIVE_DAYS.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.holiday_repo import HolidayRepository
from app.db.repositories.leave_balance_repo import LeaveBalanceRepository
from app.db.repositories.leave_ledger_repo import LeaveLedgerRepository
from app.db.repositories.leave_policy_repo import LeavePolicyRepository
from app.db.repositories.leave_request_repo import LeaveRequestRepository
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.repositories.notification_repo import NotificationRepository
from app.db.repositories.user_repo import UserRepository
from app.models.leave_ledger import LeaveLedgerEntry
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.notification import Notification
from app.schemas.leave_ledger import LedgerTransactionType
from app.schemas.leave_request import LeavePreviewRequest, LeavePreviewResponse, LeaveRequestCreate
from app.utils.csv_export import leave_requests_to_csv
from app.utils.file_storage import resolve_attachment_path, save_attachment_file

WEEKEND_WEEKDAYS = {5, 6}  # Monday=0 ... Saturday=5, Sunday=6

# BR-07: company-wide hard ceiling, independent of per-type policy rows.
# Applies to every leave type, including ones with no policy row (e.g. LOP)
# and acts as a backstop even for a type whose own policy allows more.
GLOBAL_MAX_CONSECUTIVE_DAYS = 7

NOTIFICATION_TYPE_SUBMITTED = "leave_request_submitted"
NOTIFICATION_TYPE_APPROVED = "leave_request_approved"
NOTIFICATION_TYPE_REJECTED = "leave_request_rejected"
NOTIFICATION_TYPE_CANCELLED = "leave_request_cancelled"


class LeaveService:
    def __init__(self, db: Session):
        self.db = db
        self.leave_type_repo = LeaveTypeRepository(db)
        self.leave_policy_repo = LeavePolicyRepository(db)
        self.leave_balance_repo = LeaveBalanceRepository(db)
        self.leave_request_repo = LeaveRequestRepository(db)
        self.leave_ledger_repo = LeaveLedgerRepository(db)
        self.holiday_repo = HolidayRepository(db)
        self.audit_repo = AuditRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.user_repo = UserRepository(db)

    def _notify_admins(self, *, type_: str, reference_id: int, message: str) -> None:
        """
        Notifies every active admin — this codebase has no per-employee admin
        assignment (no manager hierarchy), so a new/cancelled request is
        broadcast to the whole admin pool, same flat structure RBAC already
        assumes elsewhere (require_admin, not require_specific_manager).
        """
        admins, _ = self.user_repo.search(role="admin", is_active=True, limit=100)
        for admin in admins:
            self.notification_repo.create(
                Notification(
                    recipient_id=admin.id, type=type_, reference_id=reference_id, message=message
                )
            )

    def _notify_employee(self, *, employee_id: int, type_: str, reference_id: int, message: str) -> None:
        self.notification_repo.create(
            Notification(
                recipient_id=employee_id, type=type_, reference_id=reference_id, message=message
            )
        )

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

        # BR-07: unconditional global cap, checked regardless of whether this
        # leave type has a policy row at all.
        if working_days_count > GLOBAL_MAX_CONSECUTIVE_DAYS:
            warnings.append(
                f"This request exceeds the company-wide maximum of "
                f"{GLOBAL_MAX_CONSECUTIVE_DAYS} consecutive working day(s)."
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

        # BR-07: unconditional global cap — applies even to leave types with
        # no policy row (e.g. LOP), and acts as a hard backstop regardless of
        # what a type's own policy allows.
        if working_days_count > GLOBAL_MAX_CONSECUTIVE_DAYS:
            raise BusinessRuleError(
                f"Leave requests cannot exceed {GLOBAL_MAX_CONSECUTIVE_DAYS} consecutive "
                f"working day(s), company-wide."
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

        self._notify_admins(
            type_=NOTIFICATION_TYPE_SUBMITTED,
            reference_id=created.id,
            message=(
                f"New leave request #{created.id} submitted by employee #{employee_id} "
                f"({payload.start_date} to {payload.end_date})"
            ),
        )

        return created

    def upload_attachment(self, file) -> str:
        """Validates and saves a leave-request attachment, returning the
        relative path to pass into LeaveRequestCreate.attachment_path."""
        return save_attachment_file(file)

    def get_attachment_path(self, *, request_id: int, requesting_user_id: int, is_admin: bool):
        """
        Returns the absolute filesystem path for a request's attachment,
        after confirming the caller is the request's own employee or an
        admin (same ownership rule used by cancel_request).
        """
        leave_request = self.leave_request_repo.get(request_id)
        if leave_request is None:
            raise NotFoundError("Leave request not found")
        if not is_admin and leave_request.employee_id != requesting_user_id:
            raise ForbiddenError("You cannot access another employee's attachment")
        if not leave_request.attachment_path:
            raise NotFoundError("This leave request has no attachment")

        return resolve_attachment_path(leave_request.attachment_path)

    def cancel_request(
        self,
        *,
        request_id: int,
        requesting_user_id: int,
        is_admin: bool,
        ip_address: str | None = None,
    ) -> LeaveRequest:
        """
        Two distinct branches (Phase 3's design):
        - status='pending' -> straight cancel, zero ledger effect (nothing
          was ever debited).
        - status='approved' AND start_date still in the future -> cancel +
          write a CANCELLATION_REVERSAL ledger credit that undoes the
          original LEAVE_DEBIT, and update the cached balance to match.
        - status='approved' AND start_date has already passed -> rejected
          outright (400). You cannot self-service "un-take" leave that
          already happened — that needs a manual admin ledger adjustment
          (Task 18's endpoint), not a cancel action.
        - status in ('rejected', 'cancelled') -> rejected outright (409),
          idempotency guard, same pattern as approve/reject will use later.
        """
        request = self.leave_request_repo.get_with_relations(request_id)
        if request is None:
            raise NotFoundError("Leave request not found")

        if not is_admin and request.employee_id != requesting_user_id:
            raise ForbiddenError("You can only cancel your own leave requests")

        if request.status in ("rejected", "cancelled"):
            raise ConflictError(f"This request is already {request.status}; nothing to cancel")

        before_status = request.status
        now = datetime.now(timezone.utc)

        if request.status == "pending":
            request.status = "cancelled"
            request.cancelled_at = now
            self.leave_request_repo.update(request)

        elif request.status == "approved":
            if request.start_date <= date.today():
                raise BusinessRuleError(
                    "This leave has already started or passed and cannot be self-service "
                    "cancelled. Contact an admin for a manual ledger correction."
                )

            leave_type = self.leave_type_repo.get(request.leave_type_id)
            if leave_type is not None and leave_type.is_paid:
                policy = self.leave_policy_repo.get_for_type_year(
                    leave_type_id=leave_type.id, year=request.start_date.year
                )
                if policy is not None:
                    balance = self.leave_balance_repo.get_or_create_for_year(
                        employee_id=request.employee_id,
                        leave_type_id=leave_type.id,
                        year=request.start_date.year,
                    )
                    # Reverse the original debit: reduce total_debited_days by
                    # the same amount, which raises remaining_days back up.
                    self.leave_balance_repo.adjust_balance(
                        balance, debit_delta=-request.working_days_count
                    )
                    self.leave_ledger_repo.create(
                        LeaveLedgerEntry(
                            employee_id=request.employee_id,
                            leave_type_id=leave_type.id,
                            leave_request_id=request.id,
                            transaction_type=LedgerTransactionType.CANCELLATION_REVERSAL.value,
                            amount_days=request.working_days_count,
                            reason=f"Reversal: leave request #{request.id} cancelled after approval",
                        )
                    )

            request.status = "cancelled"
            request.cancelled_at = now
            self.leave_request_repo.update(request)

        self.db.commit()

        self._notify_admins(
            type_=NOTIFICATION_TYPE_CANCELLED,
            reference_id=request.id,
            message=(
                f"Leave request #{request.id} (was {before_status}) was cancelled by "
                f"{'an admin' if is_admin else 'the employee'}"
            ),
        )

        return request

    def approve_request(
        self,
        *,
        request_id: int,
        admin_user_id: int,
        admin_comment: str | None = None,
        ip_address: str | None = None,
    ) -> LeaveRequest:
        """
        - Idempotency guard: must currently be 'pending', else 409. Approving
          an already-actioned request is a real conflict to surface to the
          admin UI ("someone else already actioned this"), not a silent no-op.
        - Self-approval prevention: an admin cannot approve their own request
          (Phase 5's internal-controls gap — RBAC alone doesn't catch this).
        - Balance is re-checked HERE, not just trusted from submission time —
          time may have passed between submit and approve, and the balance
          could have changed (another request approved in between, an admin
          ledger adjustment, etc).
        - The ledger debit + balance update + status change all happen in
          the same transaction (one commit at the end) so they can never
          drift out of sync from a partial failure.
        """
        request = self.leave_request_repo.get_with_relations(request_id)
        if request is None:
            raise NotFoundError("Leave request not found")

        if request.status != "pending":
            raise ConflictError(
                f"This request is already {request.status}; it cannot be approved again"
            )

        if request.employee_id == admin_user_id:
            raise ForbiddenError("You cannot approve your own leave request")

        leave_type = self.leave_type_repo.get(request.leave_type_id)
        if leave_type is None:
            raise NotFoundError("Leave type for this request no longer exists")

        if leave_type.is_paid:
            policy = self.leave_policy_repo.get_for_type_year(
                leave_type_id=leave_type.id, year=request.start_date.year
            )
            if policy is not None:
                balance = self.leave_balance_repo.get_or_create_for_year(
                    employee_id=request.employee_id,
                    leave_type_id=leave_type.id,
                    year=request.start_date.year,
                )
                if balance.remaining_days < request.working_days_count:
                    raise BusinessRuleError(
                        f"Insufficient balance at approval time: {balance.remaining_days} "
                        f"day(s) remaining, {request.working_days_count} requested."
                    )

                self.leave_balance_repo.adjust_balance(
                    balance, debit_delta=request.working_days_count
                )
                self.leave_ledger_repo.create(
                    LeaveLedgerEntry(
                        employee_id=request.employee_id,
                        leave_type_id=leave_type.id,
                        leave_request_id=request.id,
                        transaction_type=LedgerTransactionType.LEAVE_DEBIT.value,
                        amount_days=-request.working_days_count,
                        reason=f"Leave request #{request.id} approved",
                    )
                )

        before_status = request.status
        request.status = "approved"
        request.reviewed_by = admin_user_id
        request.reviewed_at = datetime.now(timezone.utc)
        request.admin_comment = admin_comment
        self.leave_request_repo.update(request)

        self.audit_repo.log(
            actor_id=admin_user_id,
            table_name="leave_requests",
            operation="UPDATE",
            record_id=request.id,
            before_data={"status": before_status},
            after_data={"status": "approved", "reviewed_by": admin_user_id},
            ip_address=ip_address,
        )
        self.db.commit()

        self._notify_employee(
            employee_id=request.employee_id,
            type_=NOTIFICATION_TYPE_APPROVED,
            reference_id=request.id,
            message=f"Your leave request #{request.id} was approved",
        )

        return request

    def reject_request(
        self,
        *,
        request_id: int,
        admin_user_id: int,
        admin_comment: str,
        ip_address: str | None = None,
    ) -> LeaveRequest:
        """
        Mirrors approve_request()'s idempotency guard (must be pending) and
        self-review prevention — same internal-controls reasoning applies:
        an admin shouldn't be able to reject their own submitted request
        either, even though it has no ledger effect. No ledger/balance write
        happens at all here (BR-05 still applies: only approval ever debits).
        """
        request = self.leave_request_repo.get_with_relations(request_id)
        if request is None:
            raise NotFoundError("Leave request not found")

        if request.status != "pending":
            raise ConflictError(
                f"This request is already {request.status}; it cannot be rejected"
            )

        if request.employee_id == admin_user_id:
            raise ForbiddenError("You cannot reject your own leave request")

        before_status = request.status
        request.status = "rejected"
        request.reviewed_by = admin_user_id
        request.reviewed_at = datetime.now(timezone.utc)
        request.admin_comment = admin_comment
        self.leave_request_repo.update(request)

        self.audit_repo.log(
            actor_id=admin_user_id,
            table_name="leave_requests",
            operation="UPDATE",
            record_id=request.id,
            before_data={"status": before_status},
            after_data={"status": "rejected", "reviewed_by": admin_user_id},
            ip_address=ip_address,
        )
        self.db.commit()

        self._notify_employee(
            employee_id=request.employee_id,
            type_=NOTIFICATION_TYPE_REJECTED,
            reference_id=request.id,
            message=f"Your leave request #{request.id} was rejected: {admin_comment}",
        )

        return request

    def get_calendar(self, *, month: int, year: int) -> list[LeaveRequest]:
        """Thin pass-through — the query logic itself lives in the repository."""
        return self.leave_request_repo.get_calendar_entries(month=month, year=year)

    def get_statistics(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        leave_type_id: int | None = None,
    ) -> dict:
        return self.leave_request_repo.aggregate_statistics(
            date_from=date_from, date_to=date_to, leave_type_id=leave_type_id
        )

    def export_requests_csv(
        self,
        *,
        status: str | None = None,
        leave_type_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> str:
        # No pagination for export — same "pull everything matching filters"
        # approach as ReportService.export_csv; a real production system
        # would stream this in chunks for very large datasets.
        items, _ = self.leave_request_repo.search(
            employee_id=None,  # admin-only export, always org-wide
            status=status,
            leave_type_id=leave_type_id,
            date_from=date_from,
            date_to=date_to,
            limit=100_000,
            offset=0,
        )
        return leave_requests_to_csv(items)
