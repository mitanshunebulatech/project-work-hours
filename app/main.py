"""
app/main.py
FastAPI application factory. This is the only file that knows about
both the domain exceptions (app/core/exceptions.py) and HTTP — it's the
translation boundary, keeping every other layer framework-agnostic.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints.auth import limiter
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError


def _run_annual_grant_job() -> None:
    """
    Scheduler entrypoint — opens its own DB session since it runs outside any
    HTTP request's Depends(get_db) lifecycle. Runs for the current calendar
    year; idempotency (AnnualGrantService/has_annual_grant_for_year) means a
    misfire or manual re-trigger the same day won't double-grant anyone.
    """
    from app.db.session import SessionLocal
    from app.services.annual_grant_service import AnnualGrantService

    db = SessionLocal()
    try:
        year = datetime.now(timezone.utc).year
        AnnualGrantService(db).run(year=year)
    finally:
        db.close()


def _run_policy_rollover_job() -> None:
    """
    Fires Dec 31, ahead of _run_annual_grant_job (Jan 1) — creates next
    year's LeavePolicy rows (carrying forward auto_grant_enabled and every
    other field) so the annual grant job has something to read the
    following morning. Idempotent — LeavePolicyRolloverService skips any
    leave_type that already has a row for the target year.
    """
    from app.db.session import SessionLocal
    from app.services.leave_policy_rollover_service import LeavePolicyRolloverService

    db = SessionLocal()
    try:
        current_year = datetime.now(timezone.utc).year
        LeavePolicyRolloverService(db).run(from_year=current_year, to_year=current_year + 1)
    finally:
        db.close()


def _run_wfh_monthly_grant_job() -> None:
    """
    Fires on the 1st of every month — WFH's automatic credit (confirmed:
    no admin action needed, unlike CL/SL/Birthday's admin-manual balance).
    Idempotent per employee/month via has_monthly_grant_for_month, same
    shape as the annual grant job's own guard.
    """
    from app.db.session import SessionLocal
    from app.services.wfh_monthly_grant_service import WfhMonthlyGrantService

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        WfhMonthlyGrantService(db).run(year=now.year, month=now.month)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    if settings.ENABLE_ANNUAL_GRANT_SCHEDULER:
        # Fires once a year, just after midnight Jan 1, in the configured timezone.
        scheduler.add_job(
            _run_annual_grant_job,
            trigger=CronTrigger(month=1, day=1, hour=0, minute=5),
            id="annual_leave_grant",
            replace_existing=True,
        )
    if settings.ENABLE_POLICY_ROLLOVER_SCHEDULER:
        # Fires Dec 31, 23:00 — ahead of the Jan 1 00:05 annual grant job.
        scheduler.add_job(
            _run_policy_rollover_job,
            trigger=CronTrigger(month=12, day=31, hour=23, minute=0),
            id="leave_policy_rollover",
            replace_existing=True,
        )
    if settings.ENABLE_WFH_MONTHLY_GRANT_SCHEDULER:
        # Fires just after midnight on the 1st of every month.
        scheduler.add_job(
            _run_wfh_monthly_grant_job,
            trigger=CronTrigger(day=1, hour=0, minute=10),
            id="wfh_monthly_grant",
            replace_existing=True,
        )
    if (
        settings.ENABLE_ANNUAL_GRANT_SCHEDULER
        or settings.ENABLE_POLICY_ROLLOVER_SCHEDULER
        or settings.ENABLE_WFH_MONTHLY_GRANT_SCHEDULER
    ):
        scheduler.start()
    app.state.scheduler = scheduler

    yield

    # Shutdown: stop the scheduler and dispose the connection pool cleanly.
    scheduler.shutdown(wait=False)
    from app.db.session import engine

    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Employee Work Hours & Timesheet Management System — REST API",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    # slowapi's handler is typed for RateLimitExceeded specifically, while Starlette's
    # add_exception_handler signature expects the broader Exception type — a known
    # variance mismatch in slowapi's public API, not a logic error.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
