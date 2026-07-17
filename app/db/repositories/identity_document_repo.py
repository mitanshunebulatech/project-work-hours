"""
app/db/repositories/identity_document_repo.py
"""

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.identity_document import IdentityDocument


class IdentityDocumentRepository(BaseRepository[IdentityDocument]):
    model = IdentityDocument

    def list_for_profile(self, employee_profile_id: int) -> list[IdentityDocument]:
        stmt = (
            select(IdentityDocument)
            .where(IdentityDocument.employee_profile_id == employee_profile_id)
            .order_by(IdentityDocument.uploaded_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
