"""
app/db/repositories/notification_repo.py
"""

from sqlalchemy import func, select, update

from app.db.repositories.base import BaseRepository
from app.models.notification import Notification


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def list_for_recipient(
        self,
        *,
        recipient_id: int,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.recipient_id == recipient_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))

        count_stmt = select(func.count()).select_from(Notification)
        for cond in conditions:
            count_stmt = count_stmt.where(cond)
        total = self.db.execute(count_stmt).scalar_one()

        stmt = select(Notification)
        for cond in conditions:
            stmt = stmt.where(cond)
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def unread_count(self, *, recipient_id: int) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.recipient_id == recipient_id,
            Notification.is_read.is_(False),
        )
        return self.db.execute(stmt).scalar_one()

    def mark_read(self, *, notification_id: int, recipient_id: int) -> bool:
        """
        Always filters by recipient_id — even if a service method forgot an
        ownership check upstream, this repository physically cannot mark
        someone else's notification as read. Returns False if no matching
        row was found (either it doesn't exist, or it belongs to someone else).
        """
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.recipient_id == recipient_id)
            .values(is_read=True)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount > 0

    def mark_all_read(self, *, recipient_id: int) -> int:
        stmt = (
            update(Notification)
            .where(Notification.recipient_id == recipient_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount
