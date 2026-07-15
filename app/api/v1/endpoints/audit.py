"""
app/api/v1/endpoints/audit.py
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.db.repositories.audit_repo import AuditRepository
from app.db.session import get_db
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PageParams

router = APIRouter(prefix="/audit", tags=["Audit"], dependencies=[Depends(require_permission("audit_logs:view"))])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    pagination: PageParams = Depends(),
    table_name: str | None = None,
    operation: str | None = None,
    actor_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    repo = AuditRepository(db)
    items, total = repo.search(
        table_name=table_name,
        operation=operation,
        actor_id=actor_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.size,
        offset=(pagination.page - 1) * pagination.size,
    )
    return PaginatedResponse(
        items=[AuditLogResponse.from_orm_with_relations(log) for log in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )
