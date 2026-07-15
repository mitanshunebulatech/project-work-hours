"""
app/api/v1/endpoints/leave_types.py
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, user_permission_codes
from app.db.repositories.leave_type_repo import LeaveTypeRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave_type import LeaveTypeResponse

router = APIRouter(prefix="/leave-types", tags=["Leave Types"])


@router.get("", response_model=list[LeaveTypeResponse])
def list_leave_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LeaveTypeResponse]:
    """
    Powers the Apply Leave dropdown. Only holders of leave_types:manage may
    request inactive types included — non-admins silently get the
    active-only list regardless of the query param, same "don't trust the
    client's role claim" posture used elsewhere (e.g. employee_id scoping
    in leave request search).
    """
    repo = LeaveTypeRepository(db)
    want_inactive = include_inactive and "leave_types:manage" in user_permission_codes(current_user)
    types = repo.list_active(include_inactive=want_inactive)
    return [LeaveTypeResponse.model_validate(t) for t in types]
