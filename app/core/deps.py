"""
app/core/deps.py
Shared FastAPI dependencies for DB session access and JWT-based auth/RBAC.
This is the ONLY place in the codebase that should import both FastAPI's
security utilities and the security/token module — it's the seam between
the web framework and the domain layer.
"""

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db
from app.models.user import User

# tokenUrl is documentation-only (shown in /docs); the actual login endpoint is /api/v1/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Token expired or invalid")

    if payload.token_type != "access":
        raise UnauthorizedError("Invalid token type")

    user_repo = UserRepository(db)
    user = user_repo.get(payload.user_id)

    if user is None or user.deleted_at is not None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """
    Usage: Depends(require_role("admin"))
    Raises 403 if the current user's role is not in allowed_roles.
    """

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(f"Requires one of roles: {', '.join(allowed_roles)}")
        return current_user

    return _checker


def get_client_ip(request: Request) -> str | None:
    """Used for audit log ip_address column; respects X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# Convenience pre-bound dependencies for the common cases used across routers
require_admin = require_role("admin")
require_any_role = require_role("admin", "employee")
