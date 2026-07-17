"""
tests/integration/test_profile_identity_documents_endpoint.py

The only HTTP-level (TestClient) tests in this suite — added deliberately
here because the bug being fixed (document_type/document_number binding as
query params instead of multipart form fields when placed next to
`file: UploadFile = File(...)`) can ONLY be caught by an actual HTTP
request going through FastAPI's request parsing. A service-level call like
`EmployeeProfileService(db).upload_identity_document(...)` (see
test_onboarding_service.py) calls the Python function directly and
therefore can never exercise — or catch a regression in — the endpoint's
parameter declarations. Everything else in this suite tests at the
service/repository layer by convention; this file is the one deliberate,
narrow exception.

Uses a local, self-contained TestClient + dependency overrides (get_db ->
the existing SQLite db_session fixture, get_current_user -> a fixed user)
rather than touching the shared conftest.py, so this doesn't change
behavior for any other test in the suite.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.employee_profile import EmployeeProfile
from app.models.user import User
from tests.integration.conftest import _build_test_metadata


@pytest.fixture
def db_session() -> Session:  # noqa: F811 — deliberately shadows conftest's db_session
    """
    A StaticPool-backed variant of conftest.py's db_session, needed only
    here: Starlette dispatches sync `def` endpoints to a worker thread, and
    plain sqlite:///:memory: hands each thread a *different*, empty
    database (SingletonThreadPool is per-thread by default) — so the
    request thread would see "no such table: users" even though this same
    test's setup thread populated it. StaticPool pins everything to one
    real connection regardless of which thread asks for it, which is
    exactly what a synchronous TestClient call needs.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_metadata = _build_test_metadata()
    test_metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client_as(db_session: Session):
    """Returns a factory: call it with a User to get a TestClient
    authenticated as that user (bypassing real JWT auth entirely — this is
    a dependency-injection swap, not a security test)."""

    def _make(user: User) -> TestClient:
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture
def alice_with_profile(db_session: Session, seeded_users) -> User:
    alice = seeded_users["alice"]
    profile = EmployeeProfile(
        user_id=alice.id, employee_code="EMP-0001", first_name="Alice", last_name="Employee"
    )
    db_session.add(profile)
    db_session.commit()
    return alice


def test_upload_reads_document_type_and_number_from_form_body_not_query_string(
    client_as, alice_with_profile: User
) -> None:
    """
    The actual regression test for the bug: document_type/document_number
    are sent ONLY as multipart form fields, with nothing in the query
    string. If the endpoint regressed back to plain `str` parameters
    (instead of Form(...)), FastAPI would either 422 (required query
    params missing) or silently receive None/empty — either way this
    assertion catches it.
    """
    client = client_as(alice_with_profile)
    response = client.post(
        "/api/v1/profile/me/identity-documents",
        data={"document_type": "PAN", "document_number": "ABCDE1234F"},
        files={"file": ("pan_card.pdf", io.BytesIO(b"%PDF-1.4 fake pan bytes"), "application/pdf")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document_type"] == "PAN"
    assert body["document_number_masked"] is not None
    assert "ABCDE1234F" not in body["document_number_masked"]


def test_upload_rejects_invalid_document_type(client_as, alice_with_profile: User) -> None:
    client = client_as(alice_with_profile)
    response = client.post(
        "/api/v1/profile/me/identity-documents",
        data={"document_type": "DRIVERS_LICENSE"},
        files={"file": ("doc.pdf", io.BytesIO(b"bytes"), "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_without_existing_profile_returns_404(client_as, seeded_users) -> None:
    bob = seeded_users["bob"]  # no EmployeeProfile row created for bob
    client = client_as(bob)
    response = client.post(
        "/api/v1/profile/me/identity-documents",
        data={"document_type": "PAN"},
        files={"file": ("doc.pdf", io.BytesIO(b"bytes"), "application/pdf")},
    )
    assert response.status_code == 404


def test_list_and_delete_are_scoped_to_the_caller_own_profile(
    client_as, db_session: Session, seeded_users
) -> None:
    """A second employee's identity documents must never be visible or
    deletable through another user's self-service session — cross-employee
    isolation is the entire point of scoping profile_id from
    get_current_user rather than trusting a path/query param."""
    alice = seeded_users["alice"]
    bob = seeded_users["bob"]
    alice_profile = EmployeeProfile(
        user_id=alice.id, employee_code="EMP-0001", first_name="Alice"
    )
    bob_profile = EmployeeProfile(user_id=bob.id, employee_code="EMP-0002", first_name="Bob")
    db_session.add_all([alice_profile, bob_profile])
    db_session.commit()

    alice_client = client_as(alice)
    upload = alice_client.post(
        "/api/v1/profile/me/identity-documents",
        data={"document_type": "AADHAAR"},
        files={"file": ("aadhaar.pdf", io.BytesIO(b"bytes"), "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    # Bob must see zero documents through his own self-service session.
    bob_client = client_as(bob)
    bob_list = bob_client.get("/api/v1/profile/me/identity-documents")
    assert bob_list.status_code == 200
    assert bob_list.json() == []

    # Bob must not be able to delete Alice's document by guessing its id.
    bob_delete = bob_client.delete(f"/api/v1/profile/me/identity-documents/{document_id}")
    assert bob_delete.status_code == 404

    # Alice can see and delete her own.
    alice_client_2 = client_as(alice)
    alice_list = alice_client_2.get("/api/v1/profile/me/identity-documents")
    assert len(alice_list.json()) == 1
    alice_delete = alice_client_2.delete(f"/api/v1/profile/me/identity-documents/{document_id}")
    assert alice_delete.status_code == 204
