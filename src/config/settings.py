"""
Centralised application configuration.
All values are sourced from environment variables (.env) — never hardcoded.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str
    async_database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    redis_url: str = "redis://redis:6379/0"

    idempotency_key_ttl_hours: int = 24
    fx_rate_stale_threshold_hours: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
