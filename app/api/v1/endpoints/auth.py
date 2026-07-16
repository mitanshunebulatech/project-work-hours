"""
app/api/v1/endpoints/auth.py
"""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import authenticate_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService(db).login(payload.username, payload.password)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    return AuthService(db).refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    # authenticate_user, not get_current_user (PM V2 Part 4): a locked-out
    # account must still be able to log out.
    _current_user: User = Depends(authenticate_user),
) -> MessageResponse:
    AuthService(db).logout(payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    # authenticate_user, not get_current_user (PM V2 Part 4): this is the
    # only way OUT of the must_change_password=True locked state, so it
    # can't itself require the flag to already be false.
    current_user: User = Depends(authenticate_user),
) -> MessageResponse:
    AuthService(db).change_password(current_user, payload)
    return MessageResponse(message="Password changed successfully")
