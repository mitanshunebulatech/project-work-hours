"""
app/models/__init__.py
Importing every model here ensures Base.metadata is fully populated
before Alembic's env.py calls target_metadata for autogenerate.
"""

from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.work_entry import WorkEntry

__all__ = ["User", "Project", "WorkEntry", "AuditLog", "RefreshToken"]
