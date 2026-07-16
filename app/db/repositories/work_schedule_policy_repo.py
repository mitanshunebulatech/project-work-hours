"""
app/db/repositories/work_schedule_policy_repo.py
"""

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.work_schedule_policy import WorkSchedulePolicy

SINGLETON_ID = 1


class WorkSchedulePolicyRepository(BaseRepository[WorkSchedulePolicy]):
    model = WorkSchedulePolicy

    def get_singleton(self) -> WorkSchedulePolicy | None:
        stmt = select(WorkSchedulePolicy).where(WorkSchedulePolicy.id == SINGLETON_ID)
        return self.db.execute(stmt).scalar_one_or_none()
