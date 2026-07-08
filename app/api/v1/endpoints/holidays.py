"""
app/api/v1/endpoints/holidays.py
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_admin, require_any_role
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


@router.post("", response_model=HolidayResponse, status_code=201)
def create_holiday(
    payload: HolidayCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
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
    current_user: User = Depends(require_admin),
) -> HolidayResponse:
    return HolidayService(db).update_holiday(
        holiday_id, payload, actor_id=current_user.id, ip_address=get_client_ip(request)
    )


@router.post("/{holiday_id}/deactivate", response_model=MessageResponse)
def deactivate_holiday(
    holiday_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> MessageResponse:
    HolidayService(db).deactivate_holiday(
        holiday_id, actor_id=current_user.id, ip_address=get_client_ip(request)
    )
    return MessageResponse(message="Holiday deactivated")
