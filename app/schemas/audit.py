"""
app/schemas/audit.py
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_username: str | None
    table_name: str
    operation: str
    record_id: int
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime

    @classmethod
    def from_orm_with_relations(cls, log) -> "AuditLogResponse":
        return cls(
            id=log.id,
            actor_username=log.actor.username if log.actor else None,
            table_name=log.table_name,
            operation=log.operation,
            record_id=log.record_id,
            before_data=log.before_data,
            after_data=log.after_data,
            ip_address=str(log.ip_address) if log.ip_address else None,
            created_at=log.created_at,
        )
