"""
app/services/notification_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.repositories.notification_repo import NotificationRepository
from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)

    def list_for_user(
        self, *, user_id: int, unread_only: bool = False, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        return self.notification_repo.list_for_recipient(
            recipient_id=user_id, unread_only=unread_only, limit=limit, offset=offset
        )

    def unread_count(self, *, user_id: int) -> int:
        return self.notification_repo.unread_count(recipient_id=user_id)

    def mark_read(self, *, notification_id: int, user_id: int) -> None:
        """
        mark_read()'s own repo method already scopes by recipient_id (can't
        mark someone else's notification), so a False return here means
        either the id doesn't exist or it belongs to someone else — either
        way, surfaced to the caller as 404 rather than leaking which.
        """
        found = self.notification_repo.mark_read(notification_id=notification_id, recipient_id=user_id)
        if not found:
            raise NotFoundError("Notification not found")
        self.db.commit()

    def mark_all_read(self, *, user_id: int) -> int:
        count = self.notification_repo.mark_all_read(recipient_id=user_id)
        self.db.commit()
        return count
