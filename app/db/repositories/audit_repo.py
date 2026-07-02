"""
app/db/repositories/audit_repo.py
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.db.repositories.base import BaseRepository
from app.models.audit_log import AuditLog


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def log(
        self,
        *,
        actor_id: int | None,
        table_name: str,
        operation: str,
        record_id: int,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            table_name=table_name,
            operation=operation,
            record_id=record_id,
            before_data=before_data,
            after_data=after_data,
            ip_address=ip_address,
        )
        return self.create(entry)

    def search(
        self,
        *,
        table_name: str | None = None,
        operation: str | None = None,
        actor_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog).options(joinedload(AuditLog.actor))
        count_stmt = select(func.count()).select_from(AuditLog)

        conditions = []
        if table_name:
            conditions.append(AuditLog.table_name == table_name)
        if operation:
            conditions.append(AuditLog.operation == operation)
        if actor_id is not None:
            conditions.append(AuditLog.actor_id == actor_id)
        if date_from is not None:
            conditions.append(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            conditions.append(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = self.db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
