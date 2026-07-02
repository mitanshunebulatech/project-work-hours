"""
tests/integration/test_ui_pages_render.py
Exercises actual page rendering through NiceGUI's test harness (not just
import success). This is the only way to catch bugs in component
construction (e.g. invalid Quasar props, bad event handler signatures)
since @ui.page bodies only execute when a client actually connects.

NiceGUI's `user` fixture depends on `nicegui_reset_globals`, which wipes
all registered routes before each test for isolation. That means pages
must be registered with @ui.page INSIDE each test function (after the
fixture chain has already run for that test), not at module import time —
a module-level @ui.page would be wiped before the first test even runs.
"""

from nicegui import ui
from nicegui.testing import User

from ui.pages.admin_dashboard import render_admin_dashboard
from ui.pages.employee_dashboard import render_employee_dashboard
from ui.pages.login import render_login_page


async def test_login_page_renders(user: User) -> None:
    @ui.page("/test/login")
    def _login_page() -> None:
        render_login_page()

    await user.open("/test/login")
    await user.should_see("WorkHours")
    await user.should_see("Sign In")


async def test_login_form_submit_calls_api_with_entered_credentials(user: User, monkeypatch) -> None:
    """
    Fills the username/password inputs and clicks Sign In, mocking the
    underlying httpx call so this exercises the real NiceGUI event-handler
    wiring (do_login's click binding, value reads from the input widgets)
    without depending on a live backend.
    """
    captured: dict = {}

    def fake_post(url: str, json: dict | None = None) -> object:
        captured["url"] = url
        captured["json"] = json

        class _FakeResponse:
            status_code = 200

            def json(self):
                return {"access_token": "fake-access", "refresh_token": "fake-refresh", "role": "employee"}

        return _FakeResponse()

    # login.py calls api_client.post(...), which internally calls httpx.post via _request.
    # Patching at the httpx level (rather than api_client.post) exercises the real
    # _request()/_auth_headers() code path, catching bugs in that plumbing too.
    import httpx

    monkeypatch.setattr(httpx, "request", lambda method, url, **kw: fake_post(url, kw.get("json")))

    @ui.page("/test/login-submit")
    def _login_page() -> None:
        render_login_page()

    await user.open("/test/login-submit")

    user.find("Username").type("mitanshu")
    user.find("Password").type("SecurePass1")
    user.find("Sign In").click()

    assert "auth/login" in captured.get("url", "")
    assert captured["json"] == {"username": "mitanshu", "password": "SecurePass1"}


async def test_employee_dashboard_redirects_when_logged_out(user: User) -> None:
    """With no token in app.storage.user, the page must redirect to /login rather than crash."""

    @ui.page("/test/dashboard")
    def _employee_dashboard_page() -> None:
        render_employee_dashboard()

    await user.open("/test/dashboard")
    # render_employee_dashboard() calls ui.navigate.to('/login') and returns immediately —
    # the assertion here is simply that opening the page did not raise.


async def test_admin_dashboard_redirects_when_logged_out(user: User) -> None:
    @ui.page("/test/admin")
    def _admin_dashboard_page() -> None:
        render_admin_dashboard()

    await user.open("/test/admin")
    # Same as above: redirect-on-no-auth is the expected, non-crashing behaviour.


async def test_employee_dashboard_redirects_on_genuinely_expired_session(user: User, monkeypatch) -> None:
    """
    Closes the fourth gap from Document 11 §11.7: previously, a fully
    expired refresh token surfaced as a generic in-page error rather than
    a clean redirect to /login. This simulates exactly that scenario —
    an access_token IS present in storage (so is_logged_in() passes) but
    every server call returns 401 and the refresh attempt also fails —
    and asserts the page calls require_active_session(), which redirects,
    rather than falling through to render dashboard content on a dead
    session.
    """
    from nicegui import app as nicegui_app

    call_log: list[str] = []

    class _FakeResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.headers: dict[str, str] = {}
            self.content = b"1"

        def json(self):
            return self._payload

    def fake_request(method: str, url: str, **kwargs):
        call_log.append(url)
        # Every real API call 401s (access token expired)...
        if "/auth/refresh" in url:
            # ...and the refresh attempt itself also fails (refresh token expired too).
            return _FakeResponse(401, {"detail": "Refresh token has been revoked or expired"})
        return _FakeResponse(401, {"detail": "Token expired or invalid"})

    import httpx

    monkeypatch.setattr(httpx, "request", fake_request)
    monkeypatch.setattr(httpx, "post", lambda url, **kw: fake_request("POST", url, **kw))

    @ui.page("/test/expired-session")
    def _dashboard_with_stale_token() -> None:
        # Simulate a session that LOOKS valid in storage (access + refresh
        # tokens present) but is actually dead server-side.
        nicegui_app.storage.user["access_token"] = "stale-access-token"
        nicegui_app.storage.user["refresh_token"] = "stale-refresh-token"
        nicegui_app.storage.user["role"] = "employee"
        nicegui_app.storage.user["username"] = "stale_user"
        render_employee_dashboard()

    await user.open("/test/expired-session")

    # The dashboard's "Submit Work Hours" heading must NOT have rendered —
    # require_active_session() should have redirected before any dashboard
    # content was built, which is the actual fix: catching this BEFORE the
    # user sees a half-rendered page, not reactively after a click.
    await user.should_not_see("My Timesheet")
    assert any("/profile/me" in u for u in call_log), "require_active_session should have called /profile/me"
