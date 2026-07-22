"""
app/models/__init__.py
Importing every model here ensures Base.metadata is fully populated
before Alembic's env.py calls target_metadata for autogenerate.
"""

from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.employee_profile import EmployeeProfile
from app.models.holiday import Holiday
from app.models.identity_document import IdentityDocument
from app.models.leave_balance import LeaveBalance
from app.models.leave_ledger import LeaveLedgerEntry
from app.models.leave_policy import LeavePolicy
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.notification import Notification
from app.models.permission import Permission
from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.role import Role, role_permissions
from app.models.user import User
from app.models.work_entry import WorkEntry
from app.models.work_schedule_policy import WorkSchedulePolicy

__all__ = [
    "User",
    "Project",
    "WorkEntry",
    "AuditLog",
    "RefreshToken",
    "Holiday",
    "LeaveType",
    "LeavePolicy",
    "LeaveBalance",
    "LeaveLedgerEntry",
    "LeaveRequest",
    "Notification",
    "Department",
    "Permission",
    "Role",
    "role_permissions",
    "EmployeeProfile",
    "IdentityDocument",
    "WorkSchedulePolicy",
]
