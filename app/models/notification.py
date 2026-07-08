"""
app/models/notification.py
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Notification(Base):
    """
    reference_id is a plain int (not a strict FK) rather than pointing at
    leave_requests.id specifically — this keeps the table generic enough to
    serve other notification types later (work-entry-related, etc.) without
    a schema change, resolved by (type, reference_id) together, similar in
    spirit to how AuditLog uses (table_name, record_id) generically.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_recipient_read_created", "recipient_id", "is_read", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User", foreign_keys=[recipient_id])

    def __repr__(self) -> str:
        return f"<Notification id={self.id} recipient_id={self.recipient_id} type={self.type!r}>"
