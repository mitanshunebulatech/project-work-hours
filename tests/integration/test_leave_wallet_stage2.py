"""
tests/integration/test_leave_wallet_stage2.py
HRMS V3 Stage 2 (Work Leave Balance): covers the auto_grant_enabled gate on
AnnualGrantService, the balance-visibility fix in
app/api/v1/endpoints/leave_balances.py (WFH — paid, policy-less by design —
must now appear), and LeaveLedgerService.set_balance() (the admin
full-override mechanism the new Work Leave Balance tab is built on). None
of these three had any test coverage before this file.
"""

from datetime import date, timezone, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.api.v1.endpoints.leave_balances import _balances_for_employee
from app.core.exceptions import NotFoundError
from app.models.leave_policy import LeavePolicy
from app.models.leave_type import LeaveType
from app.schemas.leave_ledger import SetBalanceRequest
from app.services.annual_grant_service import AnnualGrantService
from app.services.leave_ledger_service import LeaveLedgerService

CURRENT_YEAR = datetime.now(timezone.utc).year


def _make_policy_type(db_session: Session, *, code: str, auto_grant_enabled: bool) -> LeaveType:
    lt = LeaveType(code=code, display_name=code, is_paid=True, allows_half_day=False)
    db_session.add(lt)
    db_session.commit()
    db_session.add(
        LeavePolicy(
            leave_type_id=lt.id,
            annual_quota_days=Decimal("12"),
            max_consecutive_days=7,
            min_notice_days=0,
            effective_year=CURRENT_YEAR,
            auto_grant_enabled=auto_grant_enabled,
        )
    )
    db_session.commit()
    return lt


# ---------- AnnualGrantService: auto_grant_enabled gate ----------


def test_annual_grant_skips_type_with_auto_grant_disabled(db_session: Session, seeded_users):
    """HRMS V3: CL/SL/Birthday-style types keep their policy row (for
    max_consecutive_days etc.) but stop auto-granting once this flag is off."""
    _make_policy_type(db_session, code="CL", auto_grant_enabled=False)

    result = AnnualGrantService(db_session).run(year=CURRENT_YEAR)

    assert result["granted"] == 0


def test_annual_grant_still_grants_when_enabled(db_session: Session, seeded_users):
    """Regression check: existing auto-grant behavior is untouched for types
    that still want it — the gate only skips when explicitly disabled."""
    _make_policy_type(db_session, code="AL", auto_grant_enabled=True)

    result = AnnualGrantService(db_session).run(year=CURRENT_YEAR)

    assert result["granted"] == len(seeded_users)


# ---------- Balance visibility fix ----------


def test_balances_includes_paid_type_with_no_policy_row(db_session: Session, seeded_users):
    """The actual bug this stage fixes: WFH is_paid=True with no LeavePolicy
    row, by design — it must still appear in the balance list."""
    wfh = LeaveType(code="WFH", display_name="Work From Home", is_paid=True, allows_half_day=False)
    db_session.add(wfh)
    db_session.commit()

    results = _balances_for_employee(db_session, seeded_users["alice"].id, CURRENT_YEAR)

    codes = {r.leave_type_code for r in results}
    assert "WFH" in codes


def test_balances_excludes_unpaid_type(db_session: Session, seeded_users):
    """LOP stays excluded — unpaid/unlimited, no wallet concept applies."""
    lop = LeaveType(code="LOP", display_name="Loss of Pay", is_paid=False, allows_half_day=False)
    db_session.add(lop)
    db_session.commit()

    results = _balances_for_employee(db_session, seeded_users["alice"].id, CURRENT_YEAR)

    codes = {r.leave_type_code for r in results}
    assert "LOP" not in codes


# ---------- set_balance() ----------


def test_set_balance_credits_up_from_zero(db_session: Session, seeded_users, seeded_leave_type):
    service = LeaveLedgerService(db_session)
    result = service.set_balance(
        SetBalanceRequest(
            employee_id=seeded_users["alice"].id,
            leave_type_id=seeded_leave_type.id,
            year=CURRENT_YEAR,
            target_days=Decimal("10"),
            reason="Initial Work Leave Balance allocation at onboarding",
        ),
        actor_id=seeded_users["bob"].id,
        ip_address=None,
    )
    assert result.balance.remaining_days == Decimal("10.00")


def test_set_balance_can_lower_an_existing_balance(db_session: Session, seeded_users, seeded_leave_type):
    service = LeaveLedgerService(db_session)
    service.set_balance(
        SetBalanceRequest(
            employee_id=seeded_users["alice"].id, leave_type_id=seeded_leave_type.id,
            year=CURRENT_YEAR, target_days=Decimal("10"),
        ),
        actor_id=seeded_users["bob"].id, ip_address=None,
    )
    result = service.set_balance(
        SetBalanceRequest(
            employee_id=seeded_users["alice"].id, leave_type_id=seeded_leave_type.id,
            year=CURRENT_YEAR, target_days=Decimal("4"),
        ),
        actor_id=seeded_users["bob"].id, ip_address=None,
    )
    assert result.balance.remaining_days == Decimal("4.00")


def test_set_balance_is_a_noop_when_already_at_target(db_session: Session, seeded_users, seeded_leave_type):
    service = LeaveLedgerService(db_session)
    service.set_balance(
        SetBalanceRequest(
            employee_id=seeded_users["alice"].id, leave_type_id=seeded_leave_type.id,
            year=CURRENT_YEAR, target_days=Decimal("6"),
        ),
        actor_id=seeded_users["bob"].id, ip_address=None,
    )
    # Setting to the exact same value again must not error (create_adjustment
    # rejects amount_days=0) and must not change the balance.
    result = service.set_balance(
        SetBalanceRequest(
            employee_id=seeded_users["alice"].id, leave_type_id=seeded_leave_type.id,
            year=CURRENT_YEAR, target_days=Decimal("6"),
        ),
        actor_id=seeded_users["bob"].id, ip_address=None,
    )
    assert result.balance.remaining_days == Decimal("6.00")


def test_set_balance_rejects_unknown_employee(db_session: Session, seeded_leave_type):
    service = LeaveLedgerService(db_session)
    with pytest.raises(NotFoundError):
        service.set_balance(
            SetBalanceRequest(
                employee_id=999999, leave_type_id=seeded_leave_type.id, target_days=Decimal("5")
            ),
            actor_id=1, ip_address=None,
        )


def test_set_balance_rejects_inactive_leave_type(db_session: Session, seeded_users):
    inactive_type = LeaveType(
        code="OLD", display_name="Retired Type", is_paid=True, is_active=False, allows_half_day=False
    )
    db_session.add(inactive_type)
    db_session.commit()

    service = LeaveLedgerService(db_session)
    with pytest.raises(NotFoundError):
        service.set_balance(
            SetBalanceRequest(
                employee_id=seeded_users["alice"].id,
                leave_type_id=inactive_type.id,
                target_days=Decimal("5"),
            ),
            actor_id=seeded_users["bob"].id, ip_address=None,
        )
