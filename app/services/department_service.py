"""
app/services/department_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.department_repo import DepartmentRepository
from app.models.department import Department
from app.schemas.common import PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate


class DepartmentService:
    def __init__(self, db: Session):
        self.db = db
        self.department_repo = DepartmentRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_departments(
        self, *, page: int, size: int, is_active: bool | None
    ) -> PaginatedResponse[DepartmentResponse]:
        items, total = self.department_repo.search(
            is_active=is_active, limit=size, offset=(page - 1) * size
        )
        return PaginatedResponse(
            items=[DepartmentResponse.model_validate(d) for d in items], total=total, page=page, size=size
        )

    def create_department(
        self, payload: DepartmentCreate, *, actor_id: int, ip_address: str | None
    ) -> DepartmentResponse:
        if self.department_repo.get_by_name(payload.name):
            raise ConflictError("A department with this name already exists")

        department = Department(name=payload.name, description=payload.description)
        created = self.department_repo.create(department)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="departments",
            operation="INSERT",
            record_id=created.id,
            after_data={"name": created.name, "description": created.description},
            ip_address=ip_address,
        )
        self.db.commit()
        return DepartmentResponse.model_validate(created)

    def update_department(
        self, department_id: int, payload: DepartmentUpdate, *, actor_id: int, ip_address: str | None
    ) -> DepartmentResponse:
        department = self.department_repo.get(department_id)
        if department is None:
            raise NotFoundError("Department not found")

        if payload.name is not None and payload.name != department.name:
            existing = self.department_repo.get_by_name(payload.name)
            if existing is not None and existing.id != department_id:
                raise ConflictError("A department with this name already exists")

        before = {
            "name": department.name,
            "description": department.description,
            "is_active": department.is_active,
        }

        if payload.name is not None:
            department.name = payload.name
        if payload.description is not None:
            department.description = payload.description
        if payload.is_active is not None:
            department.is_active = payload.is_active

        updated = self.department_repo.update(department)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="departments",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "name": updated.name,
                "description": updated.description,
                "is_active": updated.is_active,
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return DepartmentResponse.model_validate(updated)

    def deactivate_department(self, department_id: int, *, actor_id: int, ip_address: str | None) -> None:
        """
        Soft-delete via is_active=False rather than a physical DELETE — the
        model has no deleted_at column, and is_active already exists
        specifically to express this state (mirrors how DepartmentRepository.search
        filters on is_active). Physically deleting would also orphan any
        EmployeeProfile.department_id pointing at this row's history.
        """
        department = self.department_repo.get(department_id)
        if department is None:
            raise NotFoundError("Department not found")

        was_active = department.is_active
        department.is_active = False
        self.department_repo.update(department)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="departments",
            operation="DELETE",
            record_id=department.id,
            before_data={"is_active": was_active},
            after_data={"is_active": False},
            ip_address=ip_address,
        )
        self.db.commit()
