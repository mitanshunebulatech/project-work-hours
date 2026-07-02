"""
app/services/entry_service.py
Core business logic for work entries. Enforces BR-01 through BR-05 from the PRD:
  BR-01: one entry per employee+project+day
  BR-02: hours in (0, 24]  -- enforced at Pydantic + DB CHECK constraint layers
  BR-03: employee can edit own entry only same-day and while pending
  BR-04: approved entries are immutable to the employee
  BR-05: admin can edit/delete any entry regardless of status
"""

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
from app.schemas.entry import WorkEntryCreate, WorkEntryResponse, WorkEntryUpdate


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
        project_id: int | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
    ) -> PaginatedResponse[WorkEntryResponse]:
        # Role scoping happens here, not in the repository — repositories are role-agnostic.
        scoped_employee_id = employee_id if current_user.is_admin else current_user.id

        items, total = self.entry_repo.search(
            employee_id=scoped_employee_id,
            project_id=project_id,
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

        existing = self.entry_repo.get_by_employee_project_date(
            current_user.id, payload.project_id, payload.entry_date
        )
        if existing is not None:
            raise ConflictError(
                "An entry for this project and date already exists. Edit the existing entry instead."
            )

        entry = WorkEntry(
            employee_id=current_user.id,
            project_id=payload.project_id,
            entry_date=payload.entry_date,
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
            after_data={"hours_worked": float(created.hours_worked), "status": created.status},
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

        before = {"hours_worked": float(entry.hours_worked), "remarks": entry.remarks, "status": entry.status}

        if payload.hours_worked is not None:
            entry.hours_worked = payload.hours_worked
        if payload.remarks is not None:
            entry.remarks = payload.remarks

        updated = self.entry_repo.update(entry)

        self.audit_repo.log(
            actor_id=current_user.id,
            table_name="work_entries",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={"hours_worked": float(updated.hours_worked), "remarks": updated.remarks},
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

    @staticmethod
    def _enforce_employee_edit_window(entry: WorkEntry, current_user: User) -> None:
        """BR-03 / BR-04: employees can only edit their own pending, same-day entries."""
        if entry.employee_id != current_user.id:
            raise ForbiddenError("You can only edit your own entries")
        if entry.status != "pending":
            raise ForbiddenError("Only pending entries can be edited")
        if entry.entry_date != date.today():
            raise ForbiddenError("Entries can only be edited on the day they were submitted")
