"""
app/api/v1/endpoints/reports.py
"""

from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.db.session import get_db
from app.schemas.report import ReportSummaryResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(require_permission("reports:view"))])


@router.get("/summary", response_model=ReportSummaryResponse)
def report_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    employee_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
) -> ReportSummaryResponse:
    return ReportService(db).summary(
        date_from=date_from, date_to=date_to, employee_id=employee_id, project_id=project_id
    )


@router.get("/export")
def export_csv(
    employee_id: int | None = None,
    project_id: int | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    csv_content = ReportService(db).export_csv(
        employee_id=employee_id, project_id=project_id, status=status, date_from=date_from, date_to=date_to
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=work_entries_export.csv"},
    )
