"""
app/db/repositories/refresh_token_repo.py
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.refresh_token import RefreshToken


def hash_token(raw_token: str) -> str:
    """Never store the raw JWT — only its SHA-256 hash, so a DB leak alone is not enough to forge sessions."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_valid_by_raw_token(self, raw_token: str) -> RefreshToken | None:
        token_hash = hash_token(raw_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke_by_raw_token(self, raw_token: str) -> None:
        token = self.get_valid_by_raw_token(raw_token)
        if token:
            token.is_revoked = True
            self.update(token)

    def revoke_all_for_user(self, user_id: int) -> None:
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
        for token in self.db.execute(stmt).scalars().all():
            token.is_revoked = True
            self.db.add(token)
        self.db.flush()
