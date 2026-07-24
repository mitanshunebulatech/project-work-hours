"""
tests/integration/test_user_preferences_service.py

Settings page — timezone + email_notifications_enabled self-service.
"""

from sqlalchemy.orm import Session

from app.schemas.user_preferences import UserPreferencesUpdate
from app.services.user_preferences_service import UserPreferencesService


def test_get_preferences_returns_defaults_for_new_user(db_session: Session, seeded_users):
    prefs = UserPreferencesService(db_session).get_preferences(seeded_users["alice"])
    assert prefs.timezone == "UTC"
    assert prefs.email_notifications_enabled is True


def test_update_preferences_sets_timezone(db_session: Session, seeded_users):
    service = UserPreferencesService(db_session)
    updated = service.update_preferences(
        seeded_users["alice"], UserPreferencesUpdate(timezone="Asia/Kolkata")
    )
    assert updated.timezone == "Asia/Kolkata"
    # email_notifications_enabled untouched since it wasn't in the payload
    assert updated.email_notifications_enabled is True


def test_update_preferences_toggles_email_notifications(db_session: Session, seeded_users):
    service = UserPreferencesService(db_session)
    updated = service.update_preferences(
        seeded_users["alice"], UserPreferencesUpdate(email_notifications_enabled=False)
    )
    assert updated.email_notifications_enabled is False
    assert updated.timezone == "UTC"  # untouched


def test_update_preferences_does_not_affect_other_users(db_session: Session, seeded_users):
    service = UserPreferencesService(db_session)
    service.update_preferences(seeded_users["alice"], UserPreferencesUpdate(timezone="America/New_York"))

    bob_prefs = service.get_preferences(seeded_users["bob"])
    assert bob_prefs.timezone == "UTC"
