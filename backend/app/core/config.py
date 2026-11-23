# Why: Central configuration loaded from environment variables.
# pydantic-settings reads .env automatically so secrets never live in code.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Every field maps to an environment variable (case-insensitive).
    pydantic-settings reads the .env file in the backend/ directory.
    """

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://stylify:stylify_pass@localhost:5432/stylify_db"

    # ── JWT ──
    SECRET_KEY: str = "change-me-to-a-random-64-char-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── App ──
    APP_ENV: str = "development"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",        # auto-load .env from working directory
        env_file_encoding="utf-8",
        extra="ignore",         # ignore env vars we don't declare
    )


# Singleton: import this everywhere instead of re-creating Settings()
settings = Settings()

