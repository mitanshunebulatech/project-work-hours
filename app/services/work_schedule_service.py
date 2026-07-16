"""
app/services/work_schedule_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.work_schedule_policy_repo import WorkSchedulePolicyRepository
from app.schemas.work_schedule_policy import WorkSchedulePolicyResponse, WorkSchedulePolicyUpdate


class WorkSchedulePolicyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkSchedulePolicyRepository(db)
        self.audit_repo = AuditRepository(db)

    def get_policy(self) -> WorkSchedulePolicyResponse:
        policy = self.repo.get_singleton()
        if policy is None:
            # Should never happen outside a broken/partial migration state —
            # the singleton row is seeded by migration 0024 itself.
            raise NotFoundError("Work schedule policy is not configured")
        return WorkSchedulePolicyResponse.model_validate(policy, from_attributes=True)

    def update_policy(
        self, payload: WorkSchedulePolicyUpdate, *, actor_id: int, ip_address: str | None
    ) -> WorkSchedulePolicyResponse:
        policy = self.repo.get_singleton()
        if policy is None:
            raise NotFoundError("Work schedule policy is not configured")

        before = {
            "first_half_start": str(policy.first_half_start),
            "first_half_end": str(policy.first_half_end),
            "second_half_start": str(policy.second_half_start),
            "second_half_end": str(policy.second_half_end),
        }

        policy.first_half_start = payload.first_half_start
        policy.first_half_end = payload.first_half_end
        policy.second_half_start = payload.second_half_start
        policy.second_half_end = payload.second_half_end
        updated = self.repo.update(policy)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="work_schedule_policy",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "first_half_start": str(updated.first_half_start),
                "first_half_end": str(updated.first_half_end),
                "second_half_start": str(updated.second_half_start),
                "second_half_end": str(updated.second_half_end),
            },
            ip_address=ip_address,
        )
        self.db.commit()

        return WorkSchedulePolicyResponse.model_validate(updated, from_attributes=True)
