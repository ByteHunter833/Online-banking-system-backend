from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Online Banking Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/banking"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = Field(
        default="change-me-in-production-change-me-in-production",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    auth_rate_limit_requests: int = 5
    auth_rate_limit_window_seconds: int = 60
    login_max_attempts: int = 5
    account_lock_minutes: int = 15

    otp_ttl_seconds: int = 300
    password_reset_otp_ttl_seconds: int = 300
    challenge_ttl_seconds: int = 300
    mfa_setup_ttl_seconds: int = 600
    sensitive_transfer_threshold: Decimal = Decimal("1000.00")
    default_daily_transfer_limit: Decimal = Decimal("5000.00")
    idempotency_ttl_hours: int = 24
    totp_issuer: str = "Example Bank"
    risk_challenge_threshold: int = 50
    risk_queue_threshold: int = 80
    storage_root: str = "storage"

    default_currency: str = "USD"
    iban_country_code: str = "GB"

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    allowed_hosts: Annotated[list[str], NoDecode] = ["*"]

    mail_from: EmailStr = "noreply@example-bank.com"
    mail_from_name: str = "Example Bank"
    mail_enabled: bool = False
    mail_host: str = "smtp.gmail.com"
    mail_port: int = 587
    mail_username: str | None = None
    mail_password: str | None = None
    mail_use_tls: bool = False
    mail_use_starttls: bool = True
    sms_enabled: bool = False

    initial_admin_email: EmailStr | None = None
    initial_admin_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def split_env_list(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("default_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        if len(value) != 3:
            raise ValueError("default_currency must be a 3-letter ISO code")
        return value.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
