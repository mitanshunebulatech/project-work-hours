"""
tests/integration/conftest.py
A real (SQLite-backed) database fixture for integration tests that need
actual constraint enforcement — not just unit-level Python assertions.

`users`, `projects`, and `work_entries` use only portable column types and
are cloned directly from the production Base.metadata via to_metadata().

`audit_logs` is different: every mutating service method (including
EntryService.create_entry, which every test in this file calls) writes an
audit row as part of its own transaction (see Document 9 §9.7 — the
mutation and its audit record commit atomically). That means audit_logs
must exist in this test database too, or every single service call fails
with "no such table: audit_logs" before the business rule under test is
even reached.

The production audit_logs model uses PostgreSQL's JSONB and INET types,
which SQLite's compiler cannot render. Rather than weaken the production
model to satisfy SQLite, a second Table object is defined here — same
name and same columns, but with portable JSON/String types — in a
separate MetaData object. This is purely a test-time stand-in; the
production Base.metadata (and the real PostgreSQL schema it generates)
is never touched by anything in this file.
"""

import pytest
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.db.base import Base
from app.models.project import Project
from app.models.user import User


def _build_test_metadata() -> MetaData:
    test_metadata = MetaData()

    # Clone the portable tables as-is from production metadata. roles must be
    # cloned too — users.role_id carries an FK to roles.id (Sprint 1).
    Base.metadata.tables["roles"].to_metadata(test_metadata)
    Base.metadata.tables["users"].to_metadata(test_metadata)
    Base.metadata.tables["projects"].to_metadata(test_metadata)
    Base.metadata.tables["work_entries"].to_metadata(test_metadata)

    # Stand-in audit_logs: same shape as app/models/audit_log.py, with
    # SQLite-compatible types swapped in for JSONB/INET only.
    Table(
        "audit_logs",
        test_metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("actor_id", Integer, ForeignKey("users.id"), nullable=True),
        Column("table_name", String(100), nullable=False),
        Column("operation", String(20), nullable=False),
        Column("record_id", Integer, nullable=False),
        Column("before_data", JSON, nullable=True),
        Column("after_data", JSON, nullable=True),
        Column("ip_address", String(45), nullable=True),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    return test_metadata


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    test_metadata = _build_test_metadata()
    test_metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def seeded_users(db_session: Session) -> dict[str, User]:
    """Two distinct employees, for role-scoping tests that need to confirm cross-employee isolation."""
    alice = User(
        username="alice", email="alice@test.local", password_hash=hash_password("Password1"), role="employee"
    )
    bob = User(
        username="bob", email="bob@test.local", password_hash=hash_password("Password1"), role="employee"
    )
    db_session.add_all([alice, bob])
    db_session.commit()
    return {"alice": alice, "bob": bob}


@pytest.fixture
def seeded_project(db_session: Session) -> Project:
    project = Project(project_name="Test Project", description="Fixture project for integration tests")
    db_session.add(project)
    db_session.commit()
    return project
