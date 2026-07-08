"""
app/db/repositories/leave_type_repo.py
"""

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.leave_type import LeaveType


class LeaveTypeRepository(BaseRepository[LeaveType]):
    model = LeaveType

    def get_by_code(self, code: str) -> LeaveType | None:
        stmt = select(LeaveType).where(LeaveType.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_active(self, *, include_inactive: bool = False) -> list[LeaveType]:
        stmt = select(LeaveType).order_by(LeaveType.display_name)
        if not include_inactive:
            stmt = stmt.where(LeaveType.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())
