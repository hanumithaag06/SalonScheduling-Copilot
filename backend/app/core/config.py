# Why: Central configuration loaded from environment variables.
# pydantic-settings reads .env automatically so secrets never live in code.

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Every field maps to an environment variable (case-insensitive).
    pydantic-settings reads the .env file in the backend/ directory.
    """

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://stylify:stylify_pass@localhost:5432/stylify_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── JWT ──
    SECRET_KEY: str = "change-me-to-a-random-64-char-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── App ──
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ── Email / SMTP ──
    EMAIL_BACKEND: str = "console"  # "console" | "smtp"
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@stylify.salon"
    SMTP_FROM_NAME: str = "Stylify Salon"
    SMTP_TLS: bool = True

    # ── AI Assistant (LLM) ──
    LLM_API_KEY: str | None = None
    LLM_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/chat/completions"
    LLM_MODEL: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",        # auto-load .env from working directory
        env_file_encoding="utf-8",
        extra="ignore",         # ignore env vars we don't declare
    )


# Singleton: import this everywhere instead of re-creating Settings()
settings = Settings()

