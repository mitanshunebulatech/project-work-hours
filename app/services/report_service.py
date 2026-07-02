"""
app/services/report_service.py
"""

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories.entry_repo import WorkEntryRepository
from app.schemas.report import ReportSummaryResponse
from app.utils.csv_export import entries_to_csv


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = WorkEntryRepository(db)

    def summary(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: int | None,
        project_id: int | None,
    ) -> ReportSummaryResponse:
        data = self.entry_repo.aggregate_summary(
            date_from=date_from, date_to=date_to, employee_id=employee_id, project_id=project_id
        )
        return ReportSummaryResponse(**data)

    def export_csv(
        self,
        *,
        employee_id: int | None,
        project_id: int | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> str:
        # Pull everything matching the filters (no pagination for export); a real production
        # system would stream this in chunks for very large datasets.
        items, _ = self.entry_repo.search(
            employee_id=employee_id,
            project_id=project_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=100_000,
            offset=0,
        )
        return entries_to_csv(items)
