from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated process configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://krada:krada@localhost:5432/krada"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://krada:krada@localhost:5672/"
    session_secret: str = "local-development-secret-change-me"
    max_bot_token: str = ""
    allow_mock_auth: bool = True
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Return the explicit comma-separated CORS allow-list."""
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @model_validator(mode="after")
    def reject_unsafe_production(self) -> "Settings":
        if self.app_env == "production":
            if self.allow_mock_auth:
                raise ValueError("Mock authentication must be disabled in production")
            if len(self.session_secret) < 32 or "change-me" in self.session_secret:
                raise ValueError("A strong SESSION_SECRET is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
