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
