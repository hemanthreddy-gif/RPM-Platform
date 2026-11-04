"""Runtime settings loaded only from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Safe defaults for an offline, synthetic-data development environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RPM Platform"
    environment: str = "development"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
