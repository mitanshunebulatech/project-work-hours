"""
app/api/v1/endpoints/users.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(require_permission("users:manage"))])


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    request: Request,
    pagination: PageParams = Depends(),
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    return UserService(db).list_users(
        page=pagination.page, size=pagination.size, search=search, role=role, is_active=is_active
    )


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage")),
) -> UserResponse:
    return UserService(db).create_user(payload, actor_id=current_user.id, ip_address=get_client_ip(request))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage")),
) -> UserResponse:
    return UserService(db).update_user(
        user_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage")),
) -> MessageResponse:
    UserService(db).soft_delete_user(user_id, actor_id=current_user.id, ip_address=get_client_ip(request))
    return MessageResponse(message="User deactivated")
