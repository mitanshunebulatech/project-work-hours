"""
app/api/v1/endpoints/dashboard.py
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.db.session import get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

# Reuses "reports:view" rather than minting a new "dashboard:view" permission
# code — the operations dashboard is, functionally, a live report, and this
# avoids growing the permission catalogue for a capability that already has
# an equivalent gate (see app/core/permissions.py's own warning about keeping
# ALL_PERMISSION_CODES / EMPLOYEE_PERMISSION_CODES in sync with any new code).
router = APIRouter(
    prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_permission("reports:view"))]
)


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    return DashboardService(db).get_summary()
