import json
import os
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def _get_env_file() -> str:
    env = os.getenv("ENVIRONMENT", "dev")
    return f".env.{env}"


class _CommaListEnvSource(DotEnvSettingsSource):
    """DotEnv source that falls back to raw string when JSON decode fails.

    Allows comma-separated env values (e.g. ``KEY=a,b,c``) to pass through
    to pydantic field validators instead of raising a SettingsError.
    """

    def decode_complex_value(
        self, field_name: str, field: object, value: str
    ) -> object:  # noqa: ARG002
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value


class Configs(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_ignore_empty=True,
    )

    # APP
    ENVIRONMENT: str = "dev"
    APP_NAME: str = "Tiny Api"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # DEPLOY
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    KEEP_ALIVE: int = 5
    LIMIT_CONCURRENCY: int = 1000

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # DATABASES
    DB_AUTO_MIGRATE: bool = False
    DB_ENABLED: bool = True
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    # CORS
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # CACHE
    CACHE_ENABLED: bool = True
    CACHE_URL: str = "redis://localhost:6379/0"
    CACHE_DEFAULT_TTL: int = 3600

    # RATE LIMIT
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "redis://localhost:6379/1"
    RATE_LIMIT_DEFAULT: Optional[str] = None

    # LOG
    LOG_REQUESTS: bool = True
    LOG_REQUEST_BODY: bool = True
    LOG_RESPONSE_BODY: bool = True
    LOG_MAX_BODY_BYTES: int = 10000
    LOG_MAX_LIST_ITEMS: int = 5
    LOG_MAX_STRING_LENGTH: int = 200
    LOG_SKIP_PATHS: list[str] = ["/docs", "/redoc", "/openapi.json"]

    # SSH TUNNEL — HOP 1 (local → jump host or direct to DB host)
    DB_SSH_ENABLED: bool = False
    DB_SSH_HOST: str = ""
    DB_SSH_PORT: int = 22
    DB_SSH_USER: str = ""
    DB_SSH_PRIVATE_KEY_PATH: str = ""

    # SSH TUNNEL — HOP 2 (jump host → DB host, optional)
    DB_SSH_2_ENABLED: bool = False
    DB_SSH_2_HOST: str = ""
    DB_SSH_2_PORT: int = 22
    DB_SSH_2_USER: str = ""
    DB_SSH_2_PRIVATE_KEY_PATH: str = ""

    # SSH TUNNEL — FINAL DESTINATION (used by whichever hop is last)
    DB_SSH_REMOTE_BIND_HOST: str = "127.0.0.1"
    DB_SSH_REMOTE_BIND_PORT: int = 5432

    # CELERY
    CELERY_ENABLED: bool = False
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"

    @field_validator(
        "CORS_ALLOW_ORIGINS",
        "CORS_ALLOW_METHODS",
        "CORS_ALLOW_HEADERS",
        "LOG_SKIP_PATHS",
        mode="before",
    )
    @classmethod
    def _parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            _CommaListEnvSource(settings_cls, env_file=_get_env_file()),
            file_secret_settings,
        )


@lru_cache
def get_configs() -> Configs:
    return Configs()


configs = get_configs()
