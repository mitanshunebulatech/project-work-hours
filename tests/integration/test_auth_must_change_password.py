"""
tests/integration/test_auth_must_change_password.py
Covers the AuthService side of PM V2 Part 4 (must_change_password):
login() surfaces the flag, change_password() clears it. The enforcement
itself (403 from every other endpoint while the flag is true) lives in
app/core/deps.py and is covered separately by
tests/unit/test_must_change_password.py — this file is specifically about
whether the flag round-trips through the database correctly via the real
service + repository stack, not the FastAPI-dependency layer.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest
from app.services.auth_service import AuthService


@pytest.fixture
def user_requiring_password_change(db_session: Session) -> User:
    user = User(
        username="newhire",
        email="newhire@test.local",
        password_hash=hash_password("TempPass1"),
        role="employee",
        must_change_password=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def normal_user(db_session: Session) -> User:
    user = User(
        username="regular",
        email="regular@test.local",
        password_hash=hash_password("Password1"),
        role="employee",
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_login_returns_must_change_password_true_when_flag_set(
    db_session: Session, user_requiring_password_change: User
) -> None:
    result = AuthService(db_session).login("newhire", "TempPass1")
    assert result.must_change_password is True


def test_login_returns_must_change_password_false_for_normal_account(
    db_session: Session, normal_user: User
) -> None:
    result = AuthService(db_session).login("regular", "Password1")
    assert result.must_change_password is False


def test_change_password_clears_the_flag(
    db_session: Session, user_requiring_password_change: User
) -> None:
    service = AuthService(db_session)
    assert user_requiring_password_change.must_change_password is True

    service.change_password(
        user_requiring_password_change,
        ChangePasswordRequest(current_password="TempPass1", new_password="NewPassword1"),
    )

    db_session.refresh(user_requiring_password_change)
    assert user_requiring_password_change.must_change_password is False

    # And a fresh login with the new password no longer reports the flag —
    # confirms the clear actually persisted, not just the in-memory object.
    result = service.login("newhire", "NewPassword1")
    assert result.must_change_password is False


def test_change_password_with_wrong_current_password_leaves_flag_untouched(
    db_session: Session, user_requiring_password_change: User
) -> None:
    service = AuthService(db_session)

    with pytest.raises(BusinessRuleError):
        service.change_password(
            user_requiring_password_change,
            ChangePasswordRequest(current_password="WrongPassword", new_password="NewPassword1"),
        )

    db_session.refresh(user_requiring_password_change)
    assert user_requiring_password_change.must_change_password is True


def test_voluntary_password_change_also_clears_flag_even_if_already_false(
    db_session: Session, normal_user: User
) -> None:
    """A normal (non-forced) password change should never leave a stray
    True behind — change_password() clears the flag unconditionally on
    success, not just in the forced-first-login path."""
    service = AuthService(db_session)
    service.change_password(
        normal_user,
        ChangePasswordRequest(current_password="Password1", new_password="NewPassword1"),
    )
    db_session.refresh(normal_user)
    assert normal_user.must_change_password is False
