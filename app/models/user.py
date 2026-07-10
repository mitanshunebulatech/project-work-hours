"""
app/models/user.py
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_role_id", "role_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Legacy string role, kept as fallback per F4 decision — full router migration
    # to role_id-based permission checks is a later sprint, not this one.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee")
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Forces a password reset on next login — set true for accounts created via
    # the Sprint 2 onboarding-email flow.
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entries = relationship("WorkEntry", back_populates="employee", foreign_keys="WorkEntry.employee_id")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    role_ref = relationship("Role", back_populates="users", foreign_keys=[role_id])
    employee_profile = relationship(
        "EmployeeProfile", back_populates="user", uselist=False, foreign_keys="EmployeeProfile.user_id"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
