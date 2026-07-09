"""
app/api/v1/endpoints/notifications.py
"""

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.notification import MarkAllReadResponse, NotificationResponse
from app.services.notification_service import NotificationService
from app.utils.pagination import PageParams
from sqlalchemy.orm import Session

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=PaginatedResponse[NotificationResponse])
def list_my_notifications(
    unread_only: bool = False,
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[NotificationResponse]:
    items, total = NotificationService(db).list_for_user(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/me/unread-count")
def unread_count(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, int]:
    return {"unread_count": NotificationService(db).unread_count(user_id=current_user.id)}


@router.patch("/{notification_id}/read", response_model=None, status_code=204)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    NotificationService(db).mark_read(notification_id=notification_id, user_id=current_user.id)


@router.patch("/mark-all-read", response_model=MarkAllReadResponse)
def mark_all_read(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> MarkAllReadResponse:
    count = NotificationService(db).mark_all_read(user_id=current_user.id)
    return MarkAllReadResponse(marked_count=count)
