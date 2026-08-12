"""Deployment configuration, read from the environment exactly once.

Nothing else in the codebase reads ``os.environ`` for configuration. One validated
object means one place to look, one place to add a guard, and a process that refuses
to start rather than one that starts wrong.

Secrets are held as ``SecretStr`` so that a stray f-string, a traceback, or a log
line renders ``**********`` instead of the value.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Final, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "ci", "staging", "production"]

DEPLOYED_ENVIRONMENTS: Final[frozenset[str]] = frozenset({"staging", "production"})

MIN_SECRET_KEY_BYTES: Final = 32
"""HS256's hash width. A deployed SECRET_KEY shorter than this is refused: it signs
every session token, and a short key is brute-forceable offline from one capture."""

# Values that are fine on a laptop and must never reach a deployed environment. The
# validator below refuses to construct Settings if one of them survives into staging
# or production, because "we forgot to set the key" should be a failed deploy and not
# a quiet downgrade of every secret in the database to a published constant.
# At least 32 bytes: SECRET_KEY signs HS256 tokens, and PyJWT (correctly) warns on
# anything shorter than the hash width. The dev value satisfies that so the warning
# stays meaningful — if it ever fires, a real deployment has a genuinely weak key.
DEV_SECRET_KEY: Final = "dev-only-secret-change-me-before-deploying"  # noqa: S105
DEV_APP_ENCRYPTION_KEY: Final = (
    "dev:" + base64.urlsafe_b64encode(b"verity-local-development-key-32b").decode()
)

# Loaded lowest-priority first, so a backend/.env overrides the repository-root one.
_ENV_FILES: Final = ("../.env", ".env")


class _Section(BaseSettings):
    """Base for a grouped set of settings read under a common environment prefix."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class DatabaseSettings(_Section):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str
    """Async DSN for the application role. Must not hold BYPASSRLS (ADR-0001)."""

    migration_url: str | None = None
    """Async DSN for the migration role, which owns the schema. Falls back to ``url``
    locally; required and distinct in a deployed environment."""

    app_role: str = "verity_app"
    """Role the application authenticates as. Migrations grant to it and revoke
    UPDATE/DELETE from it on append-only tables."""

    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=5, ge=0)
    pool_timeout_seconds: float = Field(default=30.0, gt=0)
    pool_recycle_seconds: int = Field(default=1800, gt=0)
    connect_timeout_seconds: float = Field(default=10.0, gt=0)
    statement_timeout_ms: int = Field(default=30_000, gt=0)
    echo: bool = False

    @model_validator(mode="after")
    def _reject_blocking_drivers(self) -> DatabaseSettings:
        candidates = (
            (self.url, "DATABASE_URL"),
            (self.migration_url, "DATABASE_MIGRATION_URL"),
        )
        for dsn, label in candidates:
            if dsn and "+asyncpg" not in dsn:
                raise ValueError(
                    f"{label} must use the asyncpg driver "
                    f"(postgresql+asyncpg://...). A blocking driver on the event loop "
                    f"stalls every concurrent request and only shows up under load."
                )
        return self

    @property
    def effective_migration_url(self) -> str:
        return self.migration_url or self.url


class RedisSettings(_Section):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    socket_timeout_seconds: float = Field(default=5.0, gt=0)


class CelerySettings(_Section):
    model_config = SettingsConfigDict(env_prefix="CELERY_")

    broker_url: str | None = None
    result_backend: str | None = None
    task_default_queue: str = "verity"
    beat_enabled: bool = True


class S3Settings(_Section):
    model_config = SettingsConfigDict(env_prefix="S3_")

    endpoint_url: str | None = None
    """Set for MinIO; leave unset for real S3."""

    region: str = "us-east-1"
    bucket: str = "verity-evidence"
    access_key_id: SecretStr | None = None
    secret_access_key: SecretStr | None = None
    use_path_style: bool = True
    connect_timeout_seconds: float = Field(default=10.0, gt=0)
    read_timeout_seconds: float = Field(default=30.0, gt=0)
    max_attempts: int = Field(default=3, ge=1)


class AISettings(_Section):
    model_config = SettingsConfigDict(env_prefix="AI_")

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    api_key: SecretStr | None = None


class LangSmithSettings(_Section):
    """Tracing configuration.

    The field names map one-to-one onto the environment variables the LangSmith SDK
    reads for itself, so a single ``.env`` configures both this object and the SDK
    and the two cannot disagree.
    """

    model_config = SettingsConfigDict(env_prefix="LANGSMITH_")

    tracing: bool = False
    api_key: SecretStr | None = None
    project: str = "verity"
    endpoint: str = "https://api.smith.langchain.com"


class AuthSettings(_Section):
    """Token lifetimes (openspec/changes/week1-review-decisions.md, decision 17).

    Only lifetimes live here. The cryptographic parameters — argon2id costs, the
    TOTP window, the JWT algorithm — are pinned in ``core.security`` deliberately,
    so a deployment cannot quietly weaken them.
    """

    model_config = SettingsConfigDict(env_prefix="AUTH_")

    session_ttl_hours: int = Field(default=12, ge=1)
    challenge_ttl_minutes: int = Field(default=5, ge=1)
    """The MFA challenge issued between the password step and the code step."""

    selection_ttl_minutes: int = Field(default=5, ge=1)
    """The workspace-selection token issued on multi-membership login."""

    invite_ttl_days: int = Field(default=7, ge=1)


class Settings(_Section):
    env: Environment = "local"
    service_name: str = "verity-api"

    secret_key: SecretStr = SecretStr(DEV_SECRET_KEY)
    """Signs session tokens. Rotating it invalidates every session."""

    app_encryption_key: SecretStr = SecretStr(DEV_APP_ENCRYPTION_KEY)
    """Active master key, as ``<key_id>:<urlsafe-base64 32 bytes>``. See core.crypto."""

    app_encryption_keys_previous: SecretStr | None = None
    """Retired master keys, comma-separated in the same form, kept for decryption so a
    key can be rotated without re-encrypting every secret row."""

    log_level: str = "INFO"
    log_format: Literal["json", "console"] | None = None
    """Defaults to console locally and JSON everywhere else."""

    cors_allow_origins: tuple[str, ...] = ()

    frontend_base_url: str = "http://localhost:5173"
    """Where the web app lives, for links the API mints (the invite accept URL).
    Week 1 returns that link in the invite response — decision 15 — so the base
    must be configurable per deployment."""

    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    ai: AISettings = Field(default_factory=AISettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)

    @model_validator(mode="after")
    def _reject_development_defaults_when_deployed(self) -> Settings:
        if not self.is_deployed:
            return self
        if self.secret_key.get_secret_value() == DEV_SECRET_KEY:
            raise ValueError(f"SECRET_KEY still holds its development default in ENV={self.env}")
        if len(self.secret_key.get_secret_value().encode()) < MIN_SECRET_KEY_BYTES:
            raise ValueError(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_BYTES} bytes in "
                f"ENV={self.env}: it signs HS256 session tokens, and a short key is "
                f"brute-forceable offline from any captured token."
            )
        if self.app_encryption_key.get_secret_value() == DEV_APP_ENCRYPTION_KEY:
            raise ValueError(
                f"APP_ENCRYPTION_KEY still holds its development default in ENV={self.env}. "
                f"Every secret in the database would be readable by anyone with this source."
            )
        if self.database.migration_url is None:
            raise ValueError(
                f"DATABASE_MIGRATION_URL must be set in ENV={self.env}. The application "
                f"role must not own the tables it reads (docs/architecture/multi-tenancy.md)."
            )
        if self.database.migration_url == self.database.url:
            raise ValueError(
                "DATABASE_MIGRATION_URL must differ from DATABASE_URL: the migration role "
                "owns the schema, the application role does not."
            )
        return self

    @property
    def is_deployed(self) -> bool:
        return self.env in DEPLOYED_ENVIRONMENTS

    @property
    def is_local(self) -> bool:
        return self.env in {"local", "test"}

    @property
    def resolved_log_format(self) -> Literal["json", "console"]:
        if self.log_format is not None:
            return self.log_format
        return "console" if self.is_local else "json"

    @property
    def celery_broker_url(self) -> str:
        return self.celery.broker_url or self.redis.url

    @property
    def celery_result_backend(self) -> str:
        return self.celery.result_backend or self.redis.url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, constructed on first call."""
    return Settings()


def reset_settings_cache() -> None:
    """Discard the cached settings. For tests that vary the environment."""
    get_settings.cache_clear()
