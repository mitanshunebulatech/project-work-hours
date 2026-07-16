"""
app/api/v1/endpoints/work_schedule_policy.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.work_schedule_policy import WorkSchedulePolicyResponse, WorkSchedulePolicyUpdate
from app.services.work_schedule_service import WorkSchedulePolicyService

router = APIRouter(prefix="/work-schedule-policy", tags=["Work Schedule Policy"])


@router.get("", response_model=WorkSchedulePolicyResponse)
def get_policy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkSchedulePolicyResponse:
    """
    Readable by any authenticated user (not just admins): the employee Leave
    form needs these times to label "First Half (11:00 AM-4:00 PM)" instead
    of a hardcoded string, so every employee applying for half-day leave
    needs this — not just whoever can edit it.
    """
    return WorkSchedulePolicyService(db).get_policy()


@router.patch(
    "", response_model=WorkSchedulePolicyResponse,
    dependencies=[Depends(require_permission("work_schedule:manage"))],
)
def update_policy(
    payload: WorkSchedulePolicyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("work_schedule:manage")),
) -> WorkSchedulePolicyResponse:
    return WorkSchedulePolicyService(db).update_policy(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
