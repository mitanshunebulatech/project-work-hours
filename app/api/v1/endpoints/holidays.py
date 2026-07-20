"""
app/api/v1/endpoints/holidays.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_any_role, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.holiday import HolidayCreate, HolidayResponse, HolidayUpdate
from app.services.holiday_service import HolidayService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/holidays", tags=["Holidays"])


@router.get("", response_model=PaginatedResponse[HolidayResponse], dependencies=[Depends(require_any_role)])
def list_holidays(
    pagination: PageParams = Depends(),
    year: int | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> PaginatedResponse[HolidayResponse]:
    return HolidayService(db).list_holidays(
        page=pagination.page, size=pagination.size, year=year, is_active=is_active
    )


@router.get(
    "/published/{year}",
    response_model=list[HolidayResponse],
    dependencies=[Depends(require_any_role)],
)
def list_published_holidays(year: int, db: Session = Depends(get_db)) -> list[HolidayResponse]:
    """Employee-facing calendar (PM req #4) — routes through
    HolidayService.list_published_for_year(), which itself routes through
    the repository's dedicated get_published_for_year(), never search().
    An unpublished year's holidays are simply absent from this response,
    not filtered client-side, so there's nothing to leak here."""
    return HolidayService(db).list_published_for_year(year)


@router.post("", response_model=HolidayResponse, status_code=201)
def create_holiday(
    payload: HolidayCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("holidays:manage")),
) -> HolidayResponse:
    return HolidayService(db).create_holiday(
        payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.patch("/{holiday_id}", response_model=HolidayResponse)
def update_holiday(
    holiday_id: int,
    payload: HolidayUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("holidays:manage")),
) -> HolidayResponse:
    return HolidayService(db).update_holiday(
        holiday_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.post("/{holiday_id}/deactivate", response_model=MessageResponse)
def deactivate_holiday(
    holiday_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("holidays:manage")),
) -> MessageResponse:
    HolidayService(db).deactivate_holiday(
        holiday_id, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return MessageResponse(message="Holiday deactivated")


@router.post("/publish/{year}", response_model=MessageResponse)
def publish_year(
    year: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("holidays:manage")),
) -> MessageResponse:
    """PM req #3: makes the whole year's active holidays visible to
    employees in one action. Gated on holidays:manage — same permission
    as create/update/deactivate, per PM decision that all holiday admin
    actions are admin-only."""
    changed = HolidayService(db).publish_year(
        year, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return MessageResponse(message=f"Published {changed} holiday(s) for {year}")


@router.post("/unpublish/{year}", response_model=MessageResponse)
def unpublish_year(
    year: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("holidays:manage")),
) -> MessageResponse:
    changed = HolidayService(db).unpublish_year(
        year, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return MessageResponse(message=f"Unpublished {changed} holiday(s) for {year}")
