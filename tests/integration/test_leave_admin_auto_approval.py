"""
tests/integration/test_leave_admin_auto_approval.py
Covers the branching logic added to LeaveService.create_request(): an
admin's own leave request auto-approves instead of sitting pending forever
(since approve_request() deliberately blocks self-approval). Also covers
the shared _finalize_approval() path this reuses (ledger debit for a paid
type with a policy row), since that's genuinely new-behavior-adjacent
(extracted from approve_request(), never previously exercised via this
second entry point).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.leave_policy import LeavePolicy
from app.models.user import User
from app.schemas.leave_request import LeaveRequestCreate
from app.services.leave_service import LeaveService


@pytest.fixture
def admin_user(db_session: Session) -> User:
    admin = User(
        username="carol_admin",
        email="carol@test.local",
        password_hash=hash_password("Password1"),
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()
    return admin


def _future_dates(days_from_today: int = 10) -> tuple[date, date]:
    d = date.today() + timedelta(days=days_from_today)
    while d.weekday() >= 5:  # Sat=5, Sun=6 — must be a working day for a non-zero working_days_count
        d += timedelta(days=1)
    return d, d


def test_admin_self_request_auto_approves(db_session: Session, admin_user: User, seeded_leave_type):
    """seeded_leave_type has no LeavePolicy row, so the balance-debit branch
    inside _finalize_approval() is skipped here — that path is covered
    separately below with a policy in place."""
    start, end = _future_dates()
    service = LeaveService(db_session)

    result = service.create_request(
        employee_id=admin_user.id,
        payload=LeaveRequestCreate(
            leave_type_id=seeded_leave_type.id,
            start_date=start,
            end_date=end,
            is_half_day=False,
            reason="Admin personal leave",
        ),
        requester_is_admin=True,
    )

    assert result.status == "approved"
    assert result.reviewed_by == admin_user.id
    assert result.reviewed_at is not None
    assert result.admin_comment == "Auto-approved — admin self-submitted leave"


def test_employee_self_request_stays_pending(db_session: Session, seeded_users, seeded_leave_type):
    start, end = _future_dates()
    service = LeaveService(db_session)

    result = service.create_request(
        employee_id=seeded_users["alice"].id,
        payload=LeaveRequestCreate(
            leave_type_id=seeded_leave_type.id,
            start_date=start,
            end_date=end,
            is_half_day=False,
            reason="Regular employee leave",
        ),
        requester_is_admin=False,
    )

    assert result.status == "pending"
    assert result.reviewed_by is None


def test_requester_is_admin_defaults_to_false(db_session: Session, seeded_users, seeded_leave_type):
    """The endpoint always passes requester_is_admin explicitly, but the
    parameter default itself must be the safe (non-auto-approving) choice —
    guards against a future caller that forgets to pass it."""
    start, end = _future_dates()
    service = LeaveService(db_session)

    result = service.create_request(
        employee_id=seeded_users["bob"].id,
        payload=LeaveRequestCreate(
            leave_type_id=seeded_leave_type.id,
            start_date=start,
            end_date=end,
            is_half_day=False,
            reason="No requester_is_admin passed",
        ),
    )

    assert result.status == "pending"


def test_admin_self_request_debits_balance_when_type_is_paid_with_a_policy(
    db_session: Session, admin_user: User, seeded_leave_type
):
    """The auto-approve path must go through the exact same ledger-debit
    mechanics as a normal admin approval — not a lighter-weight shortcut
    that skips balance accounting."""
    db_session.add(
        LeavePolicy(
            leave_type_id=seeded_leave_type.id,
            annual_quota_days=Decimal("12"),
            max_consecutive_days=7,
            min_notice_days=0,
            effective_year=date.today().year,
        )
    )
    db_session.commit()

    start, end = _future_dates()
    service = LeaveService(db_session)

    # get_or_create_for_year starts a balance at zero credited days —
    # crediting from the policy's annual_quota_days is a separate
    # AnnualGrantService concern, out of scope here. Simulate "the employee
    # already has an annual grant" directly.
    balance = service.leave_balance_repo.get_or_create_for_year(
        employee_id=admin_user.id, leave_type_id=seeded_leave_type.id, year=start.year
    )
    service.leave_balance_repo.adjust_balance(balance, credit_delta=Decimal("12"))
    db_session.commit()

    result = service.create_request(
        employee_id=admin_user.id,
        payload=LeaveRequestCreate(
            leave_type_id=seeded_leave_type.id,
            start_date=start,
            end_date=end,
            is_half_day=False,
            reason="Admin personal leave, paid type with policy",
        ),
        requester_is_admin=True,
    )

    assert result.status == "approved"
    balance = service.leave_balance_repo.get_or_create_for_year(
        employee_id=admin_user.id, leave_type_id=seeded_leave_type.id, year=start.year
    )
    assert balance.remaining_days == Decimal("11")  # 12 quota - 1 working day debited
