"""
app/core/security.py
JWT issuance/verification and password hashing.
No business logic lives here — pure cryptographic primitives only.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=settings.BCRYPT_ROUNDS)


# ---------- Password hashing ----------


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


# ---------- JWT ----------


def _create_token(
    subject: str, role: str, expires_delta: timedelta, token_type: Literal["access", "refresh"]
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(
        subject=str(user_id),
        role=role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: int, role: str) -> str:
    return _create_token(
        subject=str(user_id),
        role=role,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


class TokenPayload:
    __slots__ = ("user_id", "role", "token_type", "exp")

    def __init__(self, user_id: int, role: str, token_type: str, exp: datetime):
        self.user_id = user_id
        self.role = role
        self.token_type = token_type
        self.exp = exp


def decode_token(token: str) -> TokenPayload:
    """
    Raises jose.JWTError on any failure (expired, malformed, bad signature).
    Caller (deps.py) is responsible for translating that into an HTTP 401.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return TokenPayload(
        user_id=int(payload["sub"]),
        role=payload["role"],
        token_type=payload["type"],
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TokenPayload",
    "JWTError",
]
