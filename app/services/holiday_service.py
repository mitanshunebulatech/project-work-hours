"""
app/services/holiday_service.py
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.holiday_repo import HolidayRepository
from app.models.holiday import Holiday
from app.schemas.common import PaginatedResponse
from app.schemas.holiday import HolidayCreate, HolidayResponse, HolidayUpdate

_MAX_HOLIDAYS_PER_YEAR = 1000


class HolidayService:
    def __init__(self, db: Session):
        self.db = db
        self.holiday_repo = HolidayRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_holidays(
        self, *, page: int, size: int, year: int | None, is_active: bool | None
    ) -> PaginatedResponse[HolidayResponse]:
        items, total = self.holiday_repo.search(
            year=year, is_active=is_active, limit=size, offset=(page - 1) * size
        )
        return PaginatedResponse(
            items=[HolidayResponse.model_validate(h) for h in items], total=total, page=page, size=size
        )

    def list_published_for_year(self, year: int) -> list[HolidayResponse]:
        holidays = self.holiday_repo.get_published_for_year(year)
        return [HolidayResponse.model_validate(h) for h in holidays]

    def create_holiday(
        self, payload: HolidayCreate, *, actor_id: int, ip_address: str | None
    ) -> HolidayResponse:
        if self.holiday_repo.get_by_date(payload.date):
            raise ConflictError("A holiday already exists on this date")

        holiday = Holiday(name=payload.name, date=payload.date, year=payload.date.year)
        created = self.holiday_repo.create(holiday)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="holidays",
            operation="INSERT",
            record_id=created.id,
            after_data={"name": created.name, "date": str(created.date), "year": created.year},
            ip_address=ip_address,
        )
        self.db.commit()
        return HolidayResponse.model_validate(created)

    def update_holiday(
        self, holiday_id: int, payload: HolidayUpdate, *, actor_id: int, ip_address: str | None
    ) -> HolidayResponse:
        holiday = self.holiday_repo.get(holiday_id)
        if holiday is None:
            raise NotFoundError("Holiday not found")

        before = {
            "name": holiday.name, "date": str(holiday.date), "year": holiday.year,
            "is_active": holiday.is_active,
        }

        if payload.date is not None and payload.date != holiday.date:
            existing = self.holiday_repo.get_by_date(payload.date)
            if existing and existing.id != holiday_id:
                raise ConflictError("A holiday already exists on this date")
            holiday.date = payload.date
            holiday.year = payload.date.year
        if payload.name is not None:
            holiday.name = payload.name
        if payload.is_active is not None:
            holiday.is_active = payload.is_active

        updated = self.holiday_repo.update(holiday)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="holidays",
            operation="UPDATE",
            record_id=updated.id,
            before_data=before,
            after_data={
                "name": updated.name, "date": str(updated.date), "year": updated.year,
                "is_active": updated.is_active,
            },
            ip_address=ip_address,
        )
        self.db.commit()
        return HolidayResponse.model_validate(updated)

    def deactivate_holiday(self, holiday_id: int, *, actor_id: int, ip_address: str | None) -> None:
        holiday = self.holiday_repo.get(holiday_id)
        if holiday is None:
            raise NotFoundError("Holiday not found")

        holiday.is_active = False
        self.holiday_repo.update(holiday)

        self.audit_repo.log(
            actor_id=actor_id,
            table_name="holidays",
            operation="UPDATE",
            record_id=holiday.id,
            before_data={"is_active": True},
            after_data={"is_active": False},
            ip_address=ip_address,
        )
        self.db.commit()

    def publish_year(self, year: int, *, actor_id: int, ip_address: str | None) -> int:
        holidays, _ = self.holiday_repo.search(
            year=year, is_active=True, limit=_MAX_HOLIDAYS_PER_YEAR, offset=0
        )
        changed = 0
        for holiday in holidays:
            if holiday.is_published:
                continue
            holiday.is_published = True
            self.holiday_repo.update(holiday)
            self.audit_repo.log(
                actor_id=actor_id,
                table_name="holidays",
                operation="UPDATE",
                record_id=holiday.id,
                before_data={"is_published": False},
                after_data={"is_published": True},
                ip_address=ip_address,
            )
            changed += 1
        self.db.commit()
        return changed

    def unpublish_year(self, year: int, *, actor_id: int, ip_address: str | None) -> int:
        holidays, _ = self.holiday_repo.search(
            year=year, is_active=True, limit=_MAX_HOLIDAYS_PER_YEAR, offset=0
        )
        changed = 0
        for holiday in holidays:
            if not holiday.is_published:
                continue
            holiday.is_published = False
            self.holiday_repo.update(holiday)
            self.audit_repo.log(
                actor_id=actor_id,
                table_name="holidays",
                operation="UPDATE",
                record_id=holiday.id,
                before_data={"is_published": True},
                after_data={"is_published": False},
                ip_address=ip_address,
            )
            changed += 1
        self.db.commit()
        return changed
