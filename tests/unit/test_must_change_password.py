"""
tests/unit/test_must_change_password.py
Pure-Python tests for the must_change_password enforcement split in
app/core/deps.py (PM V2 Part 4). Follows the same stub-based convention as
tests/unit/test_permissions.py: get_current_user's actual signature is
`get_current_user(user: User = Depends(authenticate_user))`, so calling it
directly as `get_current_user(user=stub)` exercises the real enforcement
logic without needing a live JWT, DB session, or TestClient — the
Depends() wiring is a FastAPI-request-time concern, not something these
functions need to be invoked through to test their own bodies.
"""

import pytest

from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenError


class _StubUser:
    def __init__(self, must_change_password: bool):
        self.must_change_password = must_change_password


def test_get_current_user_allows_when_password_change_not_required():
    user = _StubUser(must_change_password=False)
    result = get_current_user(user=user)
    assert result is user


def test_get_current_user_denies_when_password_change_required():
    user = _StubUser(must_change_password=True)
    with pytest.raises(ForbiddenError):
        get_current_user(user=user)


def test_get_current_user_denial_message_is_actionable():
    """Not just that it 403s, but that the message tells the caller what to
    do — this is what a frontend error toast would actually show."""
    user = _StubUser(must_change_password=True)
    with pytest.raises(ForbiddenError) as exc_info:
        get_current_user(user=user)
    assert "password" in str(exc_info.value).lower()
