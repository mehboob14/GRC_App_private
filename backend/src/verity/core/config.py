"""Deployment configuration, read from the environment exactly once.

Nothing else in the codebase reads ``os.environ`` for configuration. One validated
object means one place to look, one place to add a guard, and a process that refuses
to start rather than one that starts wrong.

Secrets are held as ``SecretStr`` so that a stray f-string, a traceback, or a log
line renders ``**********`` instead of the value.
"""

from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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


class StorageSettings(_Section):
    """The object-storage seam in ``core.storage``.

    Which backing store holds evidence files is a deployment choice, so it is one
    setting and not a code path: everything above works against the ``ObjectStore``
    protocol. ``S3Settings`` above stays the *credentials* for the s3 driver; these
    are the properties of the seam itself, which the local driver needs too.
    """

    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    driver: Literal["local", "s3"] = "local"

    local_root: Path = Path(".data/objects")
    """Filesystem root for the local driver. Development and test only — a container
    filesystem is not durable, and two API replicas do not share one."""

    max_upload_mb: int = Field(default=25, ge=1)
    """Refused above this while reading, before the bytes are written anywhere."""

    signed_url_ttl_seconds: int = Field(default=900, ge=1)


class AISettings(_Section):
    model_config = SettingsConfigDict(env_prefix="AI_")

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    api_key: SecretStr | None = None


class ConnectorSettings(_Section):
    """Outbound connector calls. The GitHub base URL is a setting so GitHub
    Enterprise Server, or a recorded fixture server in a local check, can stand in
    for github.com."""

    model_config = SettingsConfigDict(env_prefix="CONNECTORS_")

    github_api_url: str = "https://api.github.com"
    timeout_seconds: float = Field(default=20.0, gt=0)


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

    email_verify_ttl_hours: int = Field(default=24, ge=1)
    """The verification link mailed on signup, before the account can be used."""

    password_reset_ttl_minutes: int = Field(default=45, ge=5)
    """The password-reset link mailed on request. Short-lived, and single-use in
    effect: a reset bumps ``credentials_changed_at``, which the link is checked
    against, so a used or superseded link no longer validates."""


class EmailSettings(_Section):
    """Outbound email over SMTP. When ``host`` (or ``from_email``) is unset the mailer
    is a no-op: local and test environments never reach for a server that isn't there,
    and a missing configuration disables sending rather than crashing a request."""

    model_config = SettingsConfigDict(env_prefix="SMTP_")

    host: str | None = None
    port: int = Field(default=587, ge=1)
    user: str | None = None
    password: SecretStr | None = None
    from_email: str | None = None
    from_name: str = "Verity"
    use_tls: bool = True
    """STARTTLS, the submission default on port 587."""
    timeout_seconds: float = Field(default=15.0, gt=0)

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.from_email)


# One address and nothing else: this lands in a ``To:`` header, so no list, no display
# name, no whitespace for a header to be split on.
_SINGLE_ADDRESS: Final = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+$")

# ``scheme://host[:port]``, which is the only shape a browser sends in ``Origin``.
_EXACT_ORIGIN: Final = re.compile(r"^https?://[a-z0-9.-]+(?::[0-9]{1,5})?$")


class LeadsSettings(_Section):
    """The public demo-request form on the marketing website (``modules/leads``).

    The website is another origin from the API and calls exactly one route, so that
    route has an allow-list of its own here instead of a wider ``CORS_ALLOW_ORIGINS``.
    """

    model_config = SettingsConfigDict(env_prefix="LEADS_")

    notify_email: str | None = "mehboobarshad300@gmail.com"
    """Where each new request is announced, and where a reply to the visitor's
    confirmation lands. Empty (``LEADS_NOTIFY_EMAIL=``) turns both mails off; the request
    is still stored. Sending needs the ``SMTP_*`` settings."""

    allowed_origins: tuple[str, ...] = ()
    """Exact origins a browser may call the endpoint from, as a JSON list in the
    environment. An entry that is not ``https://host[:port]`` (a wildcard, a path, a
    trailing slash) refuses to load rather than silently matching nothing."""

    confirm_requester: bool = True
    """Mail the visitor a short generic receipt, at most once per address per 24 hours."""

    @field_validator("notify_email")
    @classmethod
    def _one_address_or_none(cls, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        if not cleaned:
            return None
        if not _SINGLE_ADDRESS.match(cleaned):
            raise ValueError(
                "LEADS_NOTIFY_EMAIL must be one email address, or empty to turn mail off"
            )
        return cleaned

    @field_validator("allowed_origins")
    @classmethod
    def _exact_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(origin.strip().lower() for origin in value)
        if not all(_EXACT_ORIGIN.match(origin) for origin in cleaned):
            raise ValueError(
                "LEADS_ALLOWED_ORIGINS entries must be exact origins such as "
                "https://example.com or http://localhost:5174: no wildcard, path or trailing slash"
            )
        return cleaned


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
    email: EmailSettings = Field(default_factory=EmailSettings)
    leads: LeadsSettings = Field(default_factory=LeadsSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    ai: AISettings = Field(default_factory=AISettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)
    connectors: ConnectorSettings = Field(default_factory=ConnectorSettings)

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
