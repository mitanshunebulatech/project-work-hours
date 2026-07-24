"""
app/services/user_preferences_service.py

Settings page — self-service only (a user reads/updates their own
preferences; there's no admin-facing "edit someone else's timezone").
"""

from sqlalchemy.orm import Session

from app.db.repositories.user_repo import UserRepository
from app.models.user import User
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate


class UserPreferencesService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_preferences(self, user: User) -> UserPreferencesResponse:
        return UserPreferencesResponse(
            timezone=user.timezone,
            email_notifications_enabled=user.email_notifications_enabled,
        )

    def update_preferences(self, user: User, payload: UserPreferencesUpdate) -> UserPreferencesResponse:
        if payload.timezone is not None:
            user.timezone = payload.timezone
        if payload.email_notifications_enabled is not None:
            user.email_notifications_enabled = payload.email_notifications_enabled

        updated = self.user_repo.update(user)
        self.db.commit()
        return UserPreferencesResponse(
            timezone=updated.timezone,
            email_notifications_enabled=updated.email_notifications_enabled,
        )
