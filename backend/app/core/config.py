"""Runtime settings loaded only from the environment."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Safe defaults for an offline, synthetic-data development environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_name: str = "RPM Platform"
    environment: str = "development"
    hosted_demo: bool = False
    backend_gateway_secret: str = ""
    log_level: str = "INFO"
    ai_provider: str = "fake"
    ai_model: str | None = None
    database_url: str = "postgresql+psycopg://rpm:development-only-change-me@localhost:5432/rpm"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-change-me-before-any-deployment"
    mfa_encryption_key: str = "OQ9tNSZpc8hWNgeFU_U8zVgKIkp-RAlQEob4cWKo_6g="
    trusted_admin_provisioning_key: str = "development-only-admin-provisioning-key"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    reset_token_minutes: int = 30
    synthetic_demo_rules_enabled: bool = False
    synthetic_demo_no_data_glucose_days: int = 3
    synthetic_demo_no_data_bp_days: int = 7
    notification_max_attempts: int = 3
    medication_reminder_late_window_minutes: int = 30
    meal_photo_max_bytes: int = 8 * 1024 * 1024
    meal_photo_max_pixels: int = 16_000_000
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "rpm-local-development-only"
    s3_secret_access_key: str = "development-only-change-me"
    s3_bucket: str = "rpm-dev"
    s3_region: str = "us-east-1"
    s3_addressing_style: Literal["path", "virtual"] = "path"
    cors_allowed_origins: str = "http://localhost:3000"
    auth_rate_limit_per_minute: int = 10
    ingestion_rate_limit_per_minute: int = 60

    @model_validator(mode="after")
    def validate_hosted_demo(self) -> "Settings":
        """Fail closed before serving a hosted synthetic preview with unsafe settings."""
        if not self.hosted_demo:
            return self
        if self.ai_provider != "fake" or not self.synthetic_demo_rules_enabled:
            raise ValueError("Hosted demo requires fake AI and synthetic demo rules enabled")

        def strong_secret(value: str | None, name: str, minimum: int = 32) -> None:
            if (
                not value
                or len(value) < minimum
                or any(
                    marker in value.lower() for marker in ("development", "change-me", "changeme")
                )
            ):
                raise ValueError(f"Hosted demo requires a non-development {name}")

        strong_secret(self.jwt_secret, "JWT secret")
        strong_secret(self.backend_gateway_secret, "backend gateway secret")
        strong_secret(self.trusted_admin_provisioning_key, "provisioning key")
        strong_secret(self.s3_secret_access_key, "S3 secret")
        if self.s3_access_key_id == "rpm-local-development-only" or not self.s3_access_key_id:
            raise ValueError("Hosted demo requires a non-development S3 access key")
        if self.mfa_encryption_key == "OQ9tNSZpc8hWNgeFU_U8zVgKIkp-RAlQEob4cWKo_6g=":
            raise ValueError("Hosted demo requires a non-development MFA encryption key")
        try:
            Fernet(self.mfa_encryption_key.encode())
        except (ValueError, TypeError):
            raise ValueError("Hosted demo requires a valid Fernet MFA encryption key") from None
        try:
            database = make_url(self.database_url)
        except Exception:
            raise ValueError("Hosted demo requires a valid PostgreSQL URL") from None
        if database.get_backend_name() != "postgresql" or not database.username:
            raise ValueError("Hosted demo requires an authenticated PostgreSQL connection")
        strong_secret(database.password, "database password", minimum=20)
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or "*" in origin
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Hosted demo requires explicit HTTPS CORS origins")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Parse an explicit browser-origin allow-list; wildcards are not supported."""
        origins = [
            origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()
        ]
        if not origins or "*" in origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must be a non-empty explicit allow-list")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
