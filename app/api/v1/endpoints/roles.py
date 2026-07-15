"""
app/api/v1/endpoints/roles.py

Unlike departments (reference data, reads open to any authenticated user),
role/permission data controls access itself — so every route here, including
reads, requires roles:manage. There's no legitimate reason for a non-admin
screen to need the full permission catalogue or another role's assignments.

Two routers, not one: the permission catalogue (GET /permissions) is a
separate resource from roles (GET/POST/PATCH/DELETE /roles), so it gets its
own prefix rather than being nested under /roles.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.role import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles"])
permissions_router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("", response_model=list[RoleResponse], dependencies=[Depends(require_permission("roles:manage"))])
def list_roles(db: Session = Depends(get_db)) -> list[RoleResponse]:
    return RoleService(db).list_roles()


@router.get(
    "/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_permission("roles:manage"))]
)
def get_role(role_id: int, db: Session = Depends(get_db)) -> RoleResponse:
    return RoleService(db).get_role(role_id)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=201,
    dependencies=[Depends(require_permission("roles:manage"))],
)
def create_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
) -> RoleResponse:
    return RoleService(db).create_role(payload, actor_id=current_user.id, ip_address=get_client_ip(request))


@router.patch(
    "/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_permission("roles:manage"))]
)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
) -> RoleResponse:
    return RoleService(db).update_role(
        role_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.delete(
    "/{role_id}", response_model=MessageResponse, dependencies=[Depends(require_permission("roles:manage"))]
)
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
) -> MessageResponse:
    RoleService(db).delete_role(role_id, actor_id=current_user.id, ip_address=get_client_ip(request))
    return MessageResponse(message="Role deleted")


@permissions_router.get(
    "", response_model=list[PermissionResponse], dependencies=[Depends(require_permission("roles:manage"))]
)
def list_permissions(db: Session = Depends(get_db)) -> list[PermissionResponse]:
    return RoleService(db).list_permissions()
