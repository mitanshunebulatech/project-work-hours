"""
app/services/auth_service.py
Business logic for authentication. Routers call this; this calls repositories.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.repositories.refresh_token_repo import RefreshTokenRepository, hash_token
from app.db.repositories.user_repo import UserRepository
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, ChangePasswordRequest, TokenResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    def login(self, username: str, password: str) -> TokenResponse:
        user = self.user_repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")

        access_token = create_access_token(user.id, user.role)
        raw_refresh_token = create_refresh_token(user.id, user.role)

        self.token_repo.create(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh_token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            role=user.role,
            must_change_password=user.must_change_password,
        )

    def refresh(self, raw_refresh_token: str) -> AccessTokenResponse:
        try:
            payload = decode_token(raw_refresh_token)
        except JWTError:
            raise UnauthorizedError("Refresh token expired or invalid")

        if payload.token_type != "refresh":
            raise UnauthorizedError("Invalid token type")

        stored = self.token_repo.get_valid_by_raw_token(raw_refresh_token)
        if stored is None:
            raise UnauthorizedError("Refresh token has been revoked or expired")

        user = self.user_repo.get(payload.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise UnauthorizedError("User not found or inactive")

        new_access_token = create_access_token(user.id, user.role)
        return AccessTokenResponse(
            access_token=new_access_token, must_change_password=user.must_change_password
        )

    def logout(self, raw_refresh_token: str) -> None:
        self.token_repo.revoke_by_raw_token(raw_refresh_token)
        self.db.commit()

    def change_password(self, current_user: User, payload: ChangePasswordRequest) -> None:
        if not verify_password(payload.current_password, current_user.password_hash):
            raise BusinessRuleError("Current password is incorrect")

        current_user.password_hash = hash_password(payload.new_password)
        # PM req (Part 4): this is the only way a must_change_password=True
        # account gets unlocked. Cleared unconditionally on any successful
        # change, not just the forced-first-login case — a normal voluntary
        # password change should never leave a stray True behind either.
        current_user.must_change_password = False
        self.user_repo.update(current_user)
        # Force re-login everywhere after a password change
        self.token_repo.revoke_all_for_user(current_user.id)
        self.db.commit()
