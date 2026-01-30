from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "sample-auth-api"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "local"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = "sqlite+aiosqlite:///./test.db"
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_timeout: int = Field(default=30)

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_issuer: str = "sample-auth-api"
    jwt_audience: str = "sample-app"
    jwt_access_token_expire_seconds: int = 1800
    jwt_refresh_token_expire_seconds: int = 2592000
    jwt_private_key_path: Path = Path("keys/private.pem")
    jwt_public_key_path: Path = Path("keys/public.pem")
    jwt_algorithm: str = "RS256"

    # Security
    bcrypt_rounds: int = 12
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Rate Limiting
    rate_limit_login: str = "5/minute"
    rate_limit_signup: str = "3/minute"
    rate_limit_refresh: str = "10/minute"
    rate_limit_default: str = "100/minute"

    # Logging
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
