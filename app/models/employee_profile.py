"""
app/models/employee_profile.py
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.db.base import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_employee_profiles_user_id"),
        Index("idx_employee_profiles_department_id", "department_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Encrypted at rest via app.core.encryption.EncryptedString (Fernet). The column
    # itself is a plain String — ciphertext, not plaintext PAN, is what's ever stored.
    pan_number: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="employee_profile")
    department = relationship("Department", back_populates="employee_profiles")

    def __repr__(self) -> str:
        return f"<EmployeeProfile id={self.id} user_id={self.user_id}>"
