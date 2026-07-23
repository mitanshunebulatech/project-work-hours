"""
app/api/v1/router.py
Aggregates every endpoint router under a single /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    dashboard,
    departments,
    employees,
    entries,
    holidays,
    leave_balances,
    leave_ledger,
    leave_requests,
    leave_types,
    notifications,
    profile,
    projects,
    reports,
    roles,
    search,
    users,
    work_schedule_policy,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(dashboard.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(roles.permissions_router)
api_router.include_router(projects.router)
api_router.include_router(entries.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(holidays.router)
api_router.include_router(leave_ledger.router)
api_router.include_router(leave_requests.router)
api_router.include_router(leave_types.router)
api_router.include_router(leave_balances.router)
api_router.include_router(notifications.router)
api_router.include_router(departments.router)
api_router.include_router(employees.router)
api_router.include_router(work_schedule_policy.router)
api_router.include_router(search.router)
