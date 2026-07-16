"""
app/models/employee_profile.py
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.db.base import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_employee_profiles_user_id"),
        UniqueConstraint("employee_code", name="uq_employee_profiles_employee_code"),
        Index("idx_employee_profiles_department_id", "department_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)

    # Business-facing identifier (e.g. "EMP-0001") shown on badges/records —
    # distinct from the internal auto-increment `id`. Auto-generated
    # sequentially by OnboardingService, never user-editable.
    employee_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # full_name was a stored column through migration 0024. As of 0025 it's a
    # computed property below — first_name/last_name are the source of truth,
    # and full_name is derived for display/back-compat only.
    first_name: Mapped[str] = mapped_column(String(75), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(75), nullable=True)

    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    present_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_of_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)

    # Path on disk (not encrypted — a profile photo isn't sensitive PII the
    # way PAN/Aadhaar/Passport are), same posture as other file paths stored
    # in this app (see app/utils/file_storage.py).
    profile_picture_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Encrypted at rest via app.core.encryption.EncryptedString (Fernet). The column
    # itself is a plain String — ciphertext, not plaintext PAN, is what's ever stored.
    pan_number: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="employee_profile")
    department = relationship("Department", back_populates="employee_profiles")
    identity_documents = relationship(
        "IdentityDocument", back_populates="employee_profile", cascade="all, delete-orphan"
    )

    @hybrid_property
    def full_name(self) -> str:
        """Derived display name — first_name/last_name are the stored columns."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @full_name.expression
    def full_name(cls):  # noqa: N805 — SQLAlchemy hybrid_property convention
        # SQL-level equivalent, so EmployeeProfile.full_name still works inside
        # .order_by() / .filter() (e.g. EmployeeProfileRepository.search()).
        return func.trim(
            func.concat(cls.first_name, " ", func.coalesce(cls.last_name, ""))
        )

    def __repr__(self) -> str:
        return f"<EmployeeProfile id={self.id} user_id={self.user_id}>"
