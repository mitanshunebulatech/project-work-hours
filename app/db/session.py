"""
app/db/session.py
Engine + sessionmaker + get_db() dependency.
Session-per-request pattern: each API call gets its own Session, closed afterward.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_MIN,
    max_overflow=settings.DB_POOL_MAX - settings.DB_POOL_MIN,
    pool_pre_ping=True,  # detect stale connections before use
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a Session, guarantees it's closed afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
