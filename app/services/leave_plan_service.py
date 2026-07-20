"""
app/services/leave_plan_service.py

PM req #6 (Leave Planning). See app/models/leave_plan.py's own docstring
for the design decision this all follows from: informational-only, zero
coupling to LeaveRequest/LeaveLedgerEntry — no approval step, no balance
impact. This service is deliberately just CRUD + the ownership boundary,
nothing more.

find_overlapping() and aggregate_by_employee_for_year() already exist on
LeavePlanRepository (Stage 3) but aren't called from here — same posture
as that repository's own docstring describes: additive, read-only
surfaces for a future overview/warning UI, not wired into the core CRUD
path yet. Deferred rather than half-built into this stage.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.leave_plan_repo import LeavePlanRepository
from app.models.leave_plan import LeavePlan
from app.schemas.common import PaginatedResponse
from app.schemas.leave_plan import LeavePlanCreate, LeavePlanResponse, LeavePlanUpdate


class LeavePlanService:
    def __init__(self, db: Session):
        self.db = db
        self.plan_repo = LeavePlanRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_plans(
        self,
        *,
        requesting_user_id: int,
        is_admin: bool,
        employee_id: int | None,
        year: int | None,
        leave_type_id: int | None,
        page: int,
        size: int,
    ) -> PaginatedResponse[LeavePlanResponse]:
        scoped_employee_id = employee_id if is_admin else requesting_user_id
        items, total = self.plan_repo.search(
            employee_id=scoped_employee_id,
            year=year,
            leave_type_id=leave_type_id,
            limit=size,
            offset=(page - 1) * size,
        )
        return PaginatedResponse(
            items=[LeavePlanResponse.model_validate(p) for p in items],
            total=total, page=page, size=size,
        )

    def get_plan(self, plan_id: int, *, requesting_user_id: int, is_admin: bool) -> LeavePlanResponse:
        plan = self.plan_repo.get_with_relations(plan_id)
        if plan is None:
            raise NotFoundError("Leave plan not found")
        if not is_admin and plan.employee_id != requesting_user_id:
            raise ForbiddenError("You can only view your own leave plans")
        return LeavePlanResponse.model_validate(plan)

    def create_plan(
        self, payload: LeavePlanCreate, *, employee_id: int, ip_address: str | None
    ) -> LeavePlanResponse:
        plan = LeavePlan(
            employee_id=employee_id,
            leave_type_id=payload.leave_type_id,
            planned_start_date=payload.planned_start_date,
            planned_end_date=payload.planned_end_date,
            year=payload.planned_start_date.year,
            reason=payload.reason,
        )
        created = self.plan_repo.create(plan)

        self.audit_repo.log(
            actor_id=employee_id,
            table_name="leave_plans",
            operation="INSERT",
            record_id=created.id,
            after_data={
                "leave_type_id": created.leave_type_id,
                "planned_start_date": str(created.planned_start_date),
                "planned_end_date": str(created.planned_end_date),
                "year": created.year,
            },
            ip_address=ip_address,
        )
        self.db.commit()

        full = self.plan_repo.get_with_relations(created.id)
        return LeavePlanResponse.model_validate(full)

    def update_plan(
        self,
        plan_id: int,
        payload: LeavePlanUpdate,
        *,
        requesting_user_id: int,
        is_admin: bool,
        ip_address: str | None,
    ) -> LeavePlanResponse:
        plan = self.plan_repo.get_with_relations(plan_id)
        if plan is None:
            raise NotFoundError("Leave plan not found")
        if not is_admin and plan.employee_id != requesting_user_id:
            raise ForbiddenError("You can only edit your own leave plans")

        before = {
            "leave_type_id": plan.leave_type_id,
            "planned_start_date": str(plan.planned_start_date),
            "planned_end_date": str(plan.planned_end_date),
            "year": plan.year,
            "reason": plan.reason,
        }

        if payload.leave_type_id is not None:
            plan.leave_type_id = payload.leave_type_id
        if payload.planned_start_date is not None:
            plan.planned_start_date = payload.planned_start_date
            plan.year = payload.planned_start_date.year
        if payload.planned_end_date is not None:
            plan.planned_end_date = payload.planned_end_date
        if payload.reason is not None:
            plan.reason = payload.reason

        updated = self.plan_repo.update(plan)

        self.audit_repo.log(
            actor_id=requesting_user_id,
            table_name="leave_plans",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "leave_type_id": updated.leave_type_id,
                "planned_start_date": str(updated.planned_start_date),
                "planned_end_date": str(updated.planned_end_date),
                "year": updated.year,
                "reason": updated.reason,
            },
            ip_address=ip_address,
        )
        self.db.commit()

        full = self.plan_repo.get_with_relations(updated.id)
        return LeavePlanResponse.model_validate(full)

    def delete_plan(
        self, plan_id: int, *, requesting_user_id: int, is_admin: bool, ip_address: str | None
    ) -> None:
        plan = self.plan_repo.get(plan_id)
        if plan is None:
            raise NotFoundError("Leave plan not found")
        if not is_admin and plan.employee_id != requesting_user_id:
            raise ForbiddenError("You can only delete your own leave plans")

        self.audit_repo.log(
            actor_id=requesting_user_id,
            table_name="leave_plans",
            operation="DELETE",
            record_id=plan.id,
            before_data={
                "leave_type_id": plan.leave_type_id,
                "planned_start_date": str(plan.planned_start_date),
                "planned_end_date": str(plan.planned_end_date),
                "year": plan.year,
            },
            ip_address=ip_address,
        )
        self.plan_repo.delete(plan)
        self.db.commit()
