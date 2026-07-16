"""
app/core/deps.py
Shared FastAPI dependencies for DB session access and JWT-based auth/RBAC.
This is the ONLY place in the codebase that should import both FastAPI's
security utilities and the security/token module — it's the seam between
the web framework and the domain layer.
"""

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import ALL_PERMISSION_CODES, EMPLOYEE_PERMISSION_CODES
from app.core.security import decode_token
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db
from app.models.user import User

# HTTPBearer (not OAuth2PasswordBearer) is used deliberately: this API's login
# endpoint takes a JSON body (LoginRequest), not the OAuth2 password-grant's
# form-urlencoded contract. OAuth2PasswordBearer makes Swagger UI's "Authorize"
# dialog POST form data to tokenUrl, which this login endpoint would reject —
# leaving every subsequent "Try it out" call unauthenticated (401), even with
# valid credentials. HTTPBearer instead gives Swagger UI a plain "paste your
# token" field, which matches how auth actually works here: call /auth/login
# manually, copy the returned access_token, paste it into Authorize.
bearer_scheme = HTTPBearer(auto_error=False)


def authenticate_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Raw JWT authentication only — deliberately does NOT enforce
    must_change_password (see get_current_user below for that). Used
    directly, instead of get_current_user, by exactly the two endpoints
    that must stay reachable even when a password change is pending:
    POST /auth/change-password (the only way OUT of the locked state) and
    POST /auth/logout (a locked-out user should still be able to log out
    rather than being stuck with no escape but waiting for the token to
    expire). Every other endpoint in the app should depend on
    get_current_user, not this function directly.
    """
    if not credentials:
        raise UnauthorizedError("Not authenticated")

    token = credentials.credentials

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


def get_current_user(user: User = Depends(authenticate_user)) -> User:
    """
    The default auth dependency — nearly every endpoint in the app depends
    on this, not authenticate_user directly. Wraps authenticate_user with
    must_change_password enforcement (PM V2 req, Part 4): a account with
    must_change_password=True gets a 403 from every endpoint except the
    two that use authenticate_user directly instead of this wrapper.
    Checked live against the DB on every request (not baked into the JWT),
    so clearing the flag via POST /auth/change-password takes effect
    immediately without needing a fresh access token.
    """
    if user.must_change_password:
        raise ForbiddenError("Password change required before continuing")
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


def user_permission_codes(user: User) -> set[str]:
    """
    Resolves the effective set of permission codes for a user.

    If role_id has been backfilled (Sprint 1 migration 0020) and points at a
    real Role, permissions come from the DB via Role.permissions — this is
    the long-term path once every user has been migrated off the legacy
    string role.

    If role_id is still NULL (not yet backfilled), falls back to the same
    permission codes the seeded system roles (0018) grant for that legacy
    role string, so access is identical to what the user would get the
    moment a backfill script runs — no silent gain or loss of access here.
    """
    if user.role_id is not None and user.role_ref is not None:
        return {p.code for p in user.role_ref.permissions}
    return set(ALL_PERMISSION_CODES) if user.role == "admin" else set(EMPLOYEE_PERMISSION_CODES)


def require_permission(*required_codes: str) -> Callable[[User], User]:
    """
    Usage: Depends(require_permission("leave_requests:approve"))

    Fine-grained alternative to require_role, for cases Sprint 1 introduced
    real granularity for (approve vs view_all vs manage). Existing
    require_admin / require_any_role gates are intentionally left alone
    elsewhere — this is additive, not a wholesale replacement.
    """

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        user_codes = user_permission_codes(current_user)
        if not set(required_codes).issubset(user_codes):
            raise ForbiddenError(f"Requires permission(s): {', '.join(required_codes)}")
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
