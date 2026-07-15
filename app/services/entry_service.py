"""
app/services/entry_service.py
Core business logic for work entries. Enforces BR-01 through BR-05 from the PRD:
  BR-01 (Sprint 3): an employee's time-blocks may not overlap each other on
        a given day, across any project. Previously this was "one entry per
        employee+project+day" (a DB unique constraint); that constraint was
        dropped in migration 0022 to allow multiple time-blocks against the
        same project on the same day (e.g. 9-12 and 2-5). Overlap is now an
        application-layer check, not a DB constraint, because it has to
        compare against every project the employee logged that day.
  BR-02: hours in (0, 24]  -- enforced at Pydantic + DB CHECK constraint layers
  BR-03: employee can edit own entry only same-day and while pending
  BR-04: approved entries are immutable to the employee
  BR-05: admin can edit/delete any entry regardless of status
"""

import csv
import io
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.entry_repo import WorkEntryRepository
from app.db.repositories.project_repo import ProjectRepository
from app.models.user import User
from app.models.work_entry import WorkEntry
from app.schemas.common import PaginatedResponse
from app.schemas.entry import (
    WorkEntryCreate,
    WorkEntryResponse,
    WorkEntrySummaryResponse,
    WorkEntryUpdate,
)


class EntryService:
    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = WorkEntryRepository(db)
        self.project_repo = ProjectRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_entries(
        self,
        *,
        current_user: User,
        page: int,
        size: int,
        employee_id: int | None,
        employee_ids: list[int] | None = None,
        project_id: int | None,
        project_ids: list[int] | None = None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
    ) -> PaginatedResponse[WorkEntryResponse]:
        # Role scoping happens here, not in the repository — repositories are role-agnostic.
        # A non-admin's employee_ids selection is ignored entirely (not narrowed to their
        # own id inside the list) — an employee has no "other employees" to multi-select
        # in the first place, so silently dropping the filter is correct, not a downgrade.
        scoped_employee_id = employee_id if current_user.is_admin else current_user.id
        scoped_employee_ids = employee_ids if current_user.is_admin else None

        items, total = self.entry_repo.search(
            employee_id=scoped_employee_id,
            employee_ids=scoped_employee_ids,
            project_id=project_id,
            project_ids=project_ids,
            status=status,
            date_from=date_from,
            date_to=date_to,
            search=search if current_user.is_admin else None,
            limit=size,
            offset=(page - 1) * size,
        )
        return PaginatedResponse(
            items=[WorkEntryResponse.from_orm_with_relations(e) for e in items],
            total=total,
            page=page,
            size=size,
        )

    def create_entry(
        self, payload: WorkEntryCreate, *, current_user: User, ip_address: str | None
    ) -> WorkEntryResponse:
        project = self.project_repo.get(payload.project_id)
        if project is None or not project.is_active or project.deleted_at is not None:
            raise NotFoundError("Project not found or inactive")

        self._enforce_no_overlap(
            employee_id=current_user.id,
            entry_date=payload.entry_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )

        entry = WorkEntry(
            employee_id=current_user.id,
            project_id=payload.project_id,
            entry_date=payload.entry_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            hours_worked=payload.hours_worked,
            remarks=payload.remarks,
            status="pending",
        )
        created = self.entry_repo.create(entry)

        self.audit_repo.log(
            actor_id=current_user.id,
            table_name="work_entries",
            operation="INSERT",
            record_id=created.id,
            after_data={
                "hours_worked": float(created.hours_worked),
                "start_time": str(created.start_time),
                "end_time": str(created.end_time),
                "status": created.status,
            },
            ip_address=ip_address,
        )
        self.db.commit()

        full = self.entry_repo.get_with_relations(created.id)
        return WorkEntryResponse.from_orm_with_relations(full)

    def update_entry(
        self, entry_id: int, payload: WorkEntryUpdate, *, current_user: User, ip_address: str | None
    ) -> WorkEntryResponse:
        entry = self.entry_repo.get_with_relations(entry_id)
        if entry is None:
            raise NotFoundError("Entry not found")

        if not current_user.is_admin:
            self._enforce_employee_edit_window(entry, current_user)

        new_start = payload.start_time if payload.start_time is not None else entry.start_time
        new_end = payload.end_time if payload.end_time is not None else entry.end_time
        if new_start is not None and new_end is not None:
            self._enforce_no_overlap(
                employee_id=entry.employee_id,
                entry_date=entry.entry_date,
                start_time=new_start,
                end_time=new_end,
                exclude_entry_id=entry.id,
            )

        before = {
            "hours_worked": float(entry.hours_worked),
            "start_time": str(entry.start_time),
            "end_time": str(entry.end_time),
            "remarks": entry.remarks,
            "status": entry.status,
        }

        if payload.hours_worked is not None:
            entry.hours_worked = payload.hours_worked
        if payload.remarks is not None:
            entry.remarks = payload.remarks
        if payload.start_time is not None:
            entry.start_time = payload.start_time
        if payload.end_time is not None:
            entry.end_time = payload.end_time

        updated = self.entry_repo.update(entry)

        self.audit_repo.log(
            actor_id=current_user.id,
            table_name="work_entries",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "hours_worked": float(updated.hours_worked),
                "start_time": str(updated.start_time),
                "end_time": str(updated.end_time),
                "remarks": updated.remarks,
            },
            ip_address=ip_address,
        )
        self.db.commit()

        full = self.entry_repo.get_with_relations(updated.id)
        return WorkEntryResponse.from_orm_with_relations(full)

    def delete_entry(self, entry_id: int, *, current_user: User, ip_address: str | None) -> None:
        # Only admins reach this — router enforces require_admin — but we double check defensively.
        if not current_user.is_admin:
            raise ForbiddenError("Only admins can delete entries")

        entry = self.entry_repo.get(entry_id)
        if entry is None:
            raise NotFoundError("Entry not found")

        self.audit_repo.log(
            actor_id=current_user.id,
            table_name="work_entries",
            operation="DELETE",
            record_id=entry.id,
            before_data={"hours_worked": float(entry.hours_worked), "status": entry.status},
            ip_address=ip_address,
        )
        self.entry_repo.delete(entry)
        self.db.commit()

    def approve_entry(
        self, entry_id: int, *, current_user: User, ip_address: str | None
    ) -> WorkEntryResponse:
        return self._set_status(entry_id, "approved", current_user=current_user, ip_address=ip_address)

    def reject_entry(
        self, entry_id: int, reason: str, *, current_user: User, ip_address: str | None
    ) -> WorkEntryResponse:
        return self._set_status(
            entry_id, "rejected", current_user=current_user, ip_address=ip_address, reason=reason
        )

    def get_summary(
        self,
        *,
        current_user: User,
        employee_id: int | None,
        project_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> WorkEntrySummaryResponse:
        # Same scoping rule as list_entries: employees only ever see their own totals.
        scoped_employee_id = employee_id if current_user.is_admin else current_user.id
        data = self.entry_repo.aggregate_summary(
            date_from=date_from,
            date_to=date_to,
            employee_id=scoped_employee_id,
            project_id=project_id,
        )
        return WorkEntrySummaryResponse(**data)

    def export_entries_csv(
        self,
        *,
        employee_id: int | None,
        employee_ids: list[int] | None = None,
        project_id: int | None,
        project_ids: list[int] | None = None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> str:
        entries = self.entry_repo.search_all_for_export(
            employee_id=employee_id,
            employee_ids=employee_ids,
            project_id=project_id,
            project_ids=project_ids,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "employee_username",
                "project_name",
                "entry_date",
                "start_time",
                "end_time",
                "hours_worked",
                "status",
                "remarks",
            ]
        )
        for e in entries:
            writer.writerow(
                [
                    e.id,
                    e.employee.username,
                    e.project.project_name,
                    e.entry_date.isoformat(),
                    e.start_time.isoformat() if e.start_time else "",
                    e.end_time.isoformat() if e.end_time else "",
                    float(e.hours_worked),
                    e.status,
                    e.remarks or "",
                ]
            )
        return buffer.getvalue()

    def _set_status(
        self,
        entry_id: int,
        new_status: str,
        *,
        current_user: User,
        ip_address: str | None,
        reason: str | None = None,
    ) -> WorkEntryResponse:
        entry = self.entry_repo.get_with_relations(entry_id)
        if entry is None:
            raise NotFoundError("Entry not found")

        before_status = entry.status
        entry.status = new_status
        updated = self.entry_repo.update(entry)

        after_data = {"status": new_status}
        if reason:
            after_data["reason"] = reason

        self.audit_repo.log(
            actor_id=current_user.id,
            table_name="work_entries",
            operation="UPDATE",
            record_id=updated.id,
            before_data={"status": before_status},
            after_data=after_data,
            ip_address=ip_address,
        )
        self.db.commit()

        full = self.entry_repo.get_with_relations(updated.id)
        return WorkEntryResponse.from_orm_with_relations(full)

    def _enforce_no_overlap(
        self,
        *,
        employee_id: int,
        entry_date: date,
        start_time,
        end_time,
        exclude_entry_id: int | None = None,
    ) -> None:
        """BR-01 (Sprint 3): this employee's time-blocks may not overlap each
        other on this date, across any project — replaces the old DB unique
        constraint that only allowed one entry per project per day."""
        existing = self.entry_repo.get_timed_entries_for_day(
            employee_id, entry_date, exclude_entry_id=exclude_entry_id
        )
        for other in existing:
            if start_time < other.end_time and other.start_time < end_time:
                raise ConflictError(
                    f"This time overlaps an existing entry ({other.start_time}-{other.end_time}) "
                    f"on {entry_date}. Adjust the times or edit the existing entry instead."
                )

    @staticmethod
    def _enforce_employee_edit_window(entry: WorkEntry, current_user: User) -> None:
        """BR-03 / BR-04: employees can only edit their own pending, same-day entries."""
        if entry.employee_id != current_user.id:
            raise ForbiddenError("You can only edit your own entries")
        if entry.status != "pending":
            raise ForbiddenError("Only pending entries can be edited")
        if entry.entry_date != date.today():
            raise ForbiddenError("Entries can only be edited on the day they were submitted")
