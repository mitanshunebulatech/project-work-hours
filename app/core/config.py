"""
app/core/config.py
Centralised application settings loaded from environment variables.
Follows the Twelve-Factor App principle: config lives in the environment, not in code.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "WorkHours Enterprise"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://workhours:workhours@localhost:5432/workhours_db"
    DB_POOL_MIN: int = 5
    DB_POOL_MAX: int = 20

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_A_LONG_RANDOM_STRING"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://localhost:8080"]

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --- Rate limiting ---
    LOGIN_RATE_LIMIT: str = "10/minute"

    # --- Scheduler ---
    # Disable in tests / when running multiple instances (BackgroundScheduler runs
    # in-process; a multi-instance deployment would need a distributed lock instead).
    ENABLE_ANNUAL_GRANT_SCHEDULER: bool = True
    # Runs Dec 31, ahead of the annual grant job (Jan 1), so next year's
    # policy rows already exist by the time AnnualGrantService needs them.
    ENABLE_POLICY_ROLLOVER_SCHEDULER: bool = True
    # Fires on the 1st of every month — WFH's separate monthly credit,
    # distinct cadence from the annual grant job above.
    ENABLE_WFH_MONTHLY_GRANT_SCHEDULER: bool = True

    # --- Field-level encryption (Sprint 1: encrypted PAN on employee_profiles) ---
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FIELD_ENCRYPTION_KEY: str = "CHANGE_ME_GENERATE_A_FERNET_KEY_IN_PRODUCTION"

    # --- Leave request attachments ---
    # Stored outside anything served statically — retrieval only happens through
    # the authenticated /leave-requests/{id}/attachment endpoint, never a direct URL.
    UPLOAD_DIR: str = "uploads/leave_attachments"
    MAX_ATTACHMENT_SIZE_MB: int = 10
    ALLOWED_ATTACHMENT_EXTENSIONS: list[str] = [".pdf", ".jpg", ".jpeg", ".png", ".docx"]

    # --- Identity documents (Aadhaar/PAN/Passport/Other) ---
    # Encrypted at rest on disk (see app/utils/secure_file_storage.py) — separate
    # directory from leave attachments since these are higher-sensitivity files.
    IDENTITY_DOCS_DIR: str = "uploads/identity_documents"
    MAX_IDENTITY_DOC_SIZE_MB: int = 10
    ALLOWED_IDENTITY_DOC_EXTENSIONS: list[str] = [".pdf", ".jpg", ".jpeg", ".png"]

    # --- Profile pictures ---
    # Not encrypted — a photo isn't sensitive PII the way PAN/Aadhaar/Passport
    # are, same posture as other non-sensitive file paths in this app.
    PROFILE_PICTURES_DIR: str = "uploads/profile_pictures"
    MAX_PROFILE_PICTURE_SIZE_MB: int = 5
    ALLOWED_PROFILE_PICTURE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png"]

    # --- Email (onboarding welcome message, etc.) ---
    # Plain SMTP via the stdlib smtplib — works with any provider (Gmail app
    # password, a self-hosted Postfix/Mailhog box, SES/SendGrid's SMTP
    # interface, etc.) without locking the app to a specific vendor SDK.
    # SMTP_HOST empty means "not configured" — EmailService logs and no-ops
    # instead of failing onboarding outright when nobody's set this up yet.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_ADDRESS: str = "noreply@workhours.local"
    SMTP_FROM_NAME: str = "WorkHours Enterprise"

    # Shown in the onboarding welcome email as the login link — separate
    # from any backend URL since this is what the *person's browser* needs
    # to hit, not the API.
    FRONTEND_BASE_URL: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-parsing env vars on every call."""
    return Settings()


settings = get_settings()
