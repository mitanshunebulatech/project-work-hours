"""
app/db/repositories/leave_policy_repo.py
"""

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.leave_policy import LeavePolicy


class LeavePolicyRepository(BaseRepository[LeavePolicy]):
    model = LeavePolicy

    def get_for_type_year(self, *, leave_type_id: int, year: int) -> LeavePolicy | None:
        """
        Returns None for leave types with no policy row by design (LOP and
        WFH — see migration 0013's docstring). Callers must treat that as
        'no quota to check', not as an error.
        """
        stmt = select(LeavePolicy).where(
            LeavePolicy.leave_type_id == leave_type_id,
            LeavePolicy.effective_year == year,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_year(self, *, year: int) -> list[LeavePolicy]:
        stmt = select(LeavePolicy).where(LeavePolicy.effective_year == year)
        return list(self.db.execute(stmt).scalars().all())
