"""
app/services/project_service.py
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.project_repo import ProjectRepository
from app.models.project import Project
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_projects(
        self, *, page: int, size: int, search: str | None, is_active: bool | None
    ) -> PaginatedResponse[ProjectResponse]:
        items, total = self.project_repo.search(
            search=search, is_active=is_active, limit=size, offset=(page - 1) * size
        )
        return PaginatedResponse(
            items=[ProjectResponse.model_validate(p) for p in items], total=total, page=page, size=size
        )

    def create_project(
        self, payload: ProjectCreate, *, actor_id: int, ip_address: str | None
    ) -> ProjectResponse:
        if self.project_repo.get_by_name(payload.project_name):
            raise ConflictError("Project name already exists")

        project = Project(project_name=payload.project_name, description=payload.description)
        created = self.project_repo.create(project)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="projects",
            operation="INSERT",
            record_id=created.id,
            after_data={"project_name": created.project_name},
            ip_address=ip_address,
        )
        self.db.commit()
        return ProjectResponse.model_validate(created)

    def update_project(
        self, project_id: int, payload: ProjectUpdate, *, actor_id: int, ip_address: str | None
    ) -> ProjectResponse:
        project = self.project_repo.get(project_id)
        if project is None or project.deleted_at is not None:
            raise NotFoundError("Project not found")

        before = {
            "project_name": project.project_name,
            "description": project.description,
            "is_active": project.is_active,
        }

        if payload.project_name is not None:
            existing = self.project_repo.get_by_name(payload.project_name)
            if existing and existing.id != project_id:
                raise ConflictError("Project name already exists")
            project.project_name = payload.project_name
        if payload.description is not None:
            project.description = payload.description
        if payload.is_active is not None:
            project.is_active = payload.is_active

        updated = self.project_repo.update(project)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="projects",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "project_name": updated.project_name,
                "description": updated.description,
                "is_active": updated.is_active,
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return ProjectResponse.model_validate(updated)

    def soft_delete_project(self, project_id: int, *, actor_id: int, ip_address: str | None) -> None:
        project = self.project_repo.get(project_id)
        if project is None or project.deleted_at is not None:
            raise NotFoundError("Project not found")

        project.deleted_at = datetime.now(timezone.utc)
        project.is_active = False
        self.project_repo.update(project)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="projects",
            operation="DELETE",
            record_id=project.id,
            before_data={"is_active": True},
            after_data={"is_active": False},
            ip_address=ip_address,
        )
        self.db.commit()
