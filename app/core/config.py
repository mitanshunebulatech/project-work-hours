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

    # --- NiceGUI ---
    UI_HOST: str = "0.0.0.0"
    UI_PORT: int = 8080
    API_BASE_URL: str = "http://localhost:8000/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-parsing env vars on every call."""
    return Settings()


settings = get_settings()
