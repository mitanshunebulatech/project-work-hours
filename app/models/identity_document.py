"""
app/models/identity_document.py

One-to-many identity document store per employee — built extensible from day
one so Aadhaar/Passport/Other government document types can be added later
without another migration (document_type is a plain string, not an enum).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.db.base import Base


class IdentityDocument(Base):
    __tablename__ = "identity_documents"
    __table_args__ = (
        Index("idx_identity_documents_employee_profile_id", "employee_profile_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employee_profiles.id"), nullable=False
    )

    # e.g. "PAN", "AADHAAR", "PASSPORT", "OTHER" — free string rather than an
    # enum column so new document types never require a schema change.
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Encrypted at rest via app.core.encryption.EncryptedString (Fernet), same
    # pattern as EmployeeProfile.pan_number. Nullable — not every document
    # type necessarily has a distinct "number" (e.g. a scanned photo-only doc).
    document_number: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)

    # Relative path to the encrypted-on-disk file (see
    # app/utils/secure_file_storage.py). No file bytes are ever stored here —
    # only a path + metadata, mirroring the leave-attachment storage pattern.
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee_profile = relationship("EmployeeProfile", back_populates="identity_documents")

    def __repr__(self) -> str:
        return (
            f"<IdentityDocument id={self.id} employee_profile_id={self.employee_profile_id} "
            f"type={self.document_type!r}>"
        )
