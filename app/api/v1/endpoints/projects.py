"""
app/api/v1/endpoints/projects.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_admin, require_any_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse[ProjectResponse], dependencies=[Depends(require_any_role)])
def list_projects(
    pagination: PageParams = Depends(),
    search: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> PaginatedResponse[ProjectResponse]:
    return ProjectService(db).list_projects(
        page=pagination.page, size=pagination.size, search=search, is_active=is_active
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ProjectResponse:
    return ProjectService(db).create_project(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ProjectResponse:
    return ProjectService(db).update_project(
        project_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> MessageResponse:
    ProjectService(db).soft_delete_project(
        project_id, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return MessageResponse(message="Project deactivated")
