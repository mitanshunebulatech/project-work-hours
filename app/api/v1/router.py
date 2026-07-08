"""
app/api/v1/router.py
Aggregates every endpoint router under a single /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import audit, auth, entries, holidays, leave_ledger, profile, projects, reports, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(entries.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(holidays.router)
api_router.include_router(leave_ledger.router)
