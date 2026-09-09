from functools import lru_cache
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = Field(repr=False)
    outbox_key: SecretStr
    rate_limit_key: SecretStr
    access_minutes: int = Field(default=10, ge=1, le=60)
    refresh_days: int = Field(default=7, ge=1, le=30)
    session_days: int = Field(default=30, ge=1, le=90)
    default_curve_version: int = Field(default=1, ge=1)
    public_app_url: str = "http://localhost:8000"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_starttls: bool = False
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str = "no-reply@example.test"

    @model_validator(mode="after")
    def secure_config(self):
        url = make_url(self.database_url)
        if url.drivername != "postgresql+psycopg":
            raise ValueError("PostgreSQL with psycopg is required")
        if url.username != "racing_app":
            raise ValueError("Runtime must use the restricted racing_app role")
        Fernet(self.outbox_key.get_secret_value().encode())
        if len(self.rate_limit_key.get_secret_value()) < 32:
            raise ValueError("RATE_LIMIT_KEY must contain at least 32 random characters")
        if self.smtp_username and self.smtp_password is None:
            raise ValueError("SMTP_PASSWORD is required when SMTP_USERNAME is configured")
        if self.app_env == "production":
            if not self.public_app_url.startswith("https://") or not self.smtp_starttls:
                raise ValueError("Production requires an HTTPS application URL and SMTP TLS")
            if url.query.get("sslmode") != "verify-full":
                raise ValueError("Production database connections require sslmode=verify-full")
        return self


@lru_cache
def get_settings():
    return Settings()
