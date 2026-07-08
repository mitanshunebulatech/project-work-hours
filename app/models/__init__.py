"""
app/models/__init__.py
Importing every model here ensures Base.metadata is fully populated
before Alembic's env.py calls target_metadata for autogenerate.
"""

from app.models.audit_log import AuditLog
from app.models.leave_balance import LeaveBalance
from app.models.leave_ledger import LeaveLedgerEntry
from app.models.leave_policy import LeavePolicy
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.work_entry import WorkEntry

__all__ = [
    "User",
    "Project",
    "WorkEntry",
    "AuditLog",
    "RefreshToken",
    "LeaveType",
    "LeavePolicy",
    "LeaveBalance",
    "LeaveLedgerEntry",
    "LeaveRequest",
]
