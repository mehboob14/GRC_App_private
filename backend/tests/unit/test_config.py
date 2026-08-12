"""Settings validation."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from verity.core.config import (
    DEV_APP_ENCRYPTION_KEY,
    DEV_SECRET_KEY,
    DatabaseSettings,
    Settings,
)

ASYNC_DSN = "postgresql+asyncpg://verity_app:pw@localhost:5432/verity"
OWNER_DSN = "postgresql+asyncpg://verity_owner:pw@localhost:5432/verity"

# The test process sets this so the integration suites can reach the owner role. The two
# tests that assert what happens when it is absent have to take it back out.
MIGRATION_URL_ENV_VAR = "DATABASE_MIGRATION_URL"


def test_async_driver_is_accepted() -> None:
    assert DatabaseSettings(url=ASYNC_DSN).url == ASYNC_DSN


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://verity_app:pw@localhost:5432/verity",
        "postgresql+psycopg://verity_app:pw@localhost:5432/verity",
        "postgresql+psycopg2://verity_app:pw@localhost:5432/verity",
    ],
)
def test_blocking_driver_is_rejected(dsn: str) -> None:
    """A sync driver on the event loop is a defect that only appears under load."""
    with pytest.raises(ValidationError, match="asyncpg"):
        DatabaseSettings(url=dsn)


def test_migration_url_falls_back_to_the_application_url_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MIGRATION_URL_ENV_VAR, raising=False)
    database = DatabaseSettings(url=ASYNC_DSN)
    assert database.effective_migration_url == ASYNC_DSN


def test_development_defaults_are_allowed_locally() -> None:
    settings = Settings(env="local", database=DatabaseSettings(url=ASYNC_DSN))
    assert settings.secret_key.get_secret_value() == DEV_SECRET_KEY
    assert not settings.is_deployed


def test_default_secret_key_is_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            env="production",
            secret_key=SecretStr(DEV_SECRET_KEY),
            app_encryption_key=SecretStr("k1:" + "A" * 43 + "="),
            database=DatabaseSettings(url=ASYNC_DSN, migration_url=OWNER_DSN),
        )


def test_default_encryption_key_is_refused_in_production() -> None:
    """Shipping this key would make every secret in the database readable from source."""
    with pytest.raises(ValidationError, match="APP_ENCRYPTION_KEY"):
        Settings(
            env="production",
            secret_key=SecretStr("a-real-secret"),
            app_encryption_key=SecretStr(DEV_APP_ENCRYPTION_KEY),
            database=DatabaseSettings(url=ASYNC_DSN, migration_url=OWNER_DSN),
        )


def test_missing_migration_role_is_refused_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MIGRATION_URL_ENV_VAR, raising=False)
    with pytest.raises(ValidationError, match="DATABASE_MIGRATION_URL must be set"):
        Settings(
            env="production",
            secret_key=SecretStr("a-real-secret"),
            app_encryption_key=SecretStr("k1:" + "A" * 43 + "="),
            database=DatabaseSettings(url=ASYNC_DSN),
        )


def test_application_role_sharing_the_migration_role_is_refused_in_production() -> None:
    """The application must not own the tables it reads.

    If it does, RLS applies to it only because of FORCE, and one missing FORCE opens
    everything (docs/architecture/multi-tenancy.md).
    """
    with pytest.raises(ValidationError, match="must differ"):
        Settings(
            env="production",
            secret_key=SecretStr("a-real-secret"),
            app_encryption_key=SecretStr("k1:" + "A" * 43 + "="),
            database=DatabaseSettings(url=ASYNC_DSN, migration_url=ASYNC_DSN),
        )


def test_a_fully_configured_production_settings_object_constructs() -> None:
    settings = Settings(
        env="production",
        secret_key=SecretStr("a-real-secret"),
        app_encryption_key=SecretStr("k1:" + "A" * 43 + "="),
        database=DatabaseSettings(url=ASYNC_DSN, migration_url=OWNER_DSN),
    )
    assert settings.is_deployed
    assert settings.resolved_log_format == "json"


def test_log_format_defaults_to_console_locally_and_can_be_overridden() -> None:
    database = DatabaseSettings(url=ASYNC_DSN)
    assert Settings(env="local", database=database).resolved_log_format == "console"
    assert Settings(env="local", log_format="json", database=database).resolved_log_format == "json"


def test_secrets_do_not_render_when_formatted() -> None:
    settings = Settings(
        env="local",
        secret_key=SecretStr("do-not-print-me"),
        database=DatabaseSettings(url=ASYNC_DSN),
    )
    assert "do-not-print-me" not in repr(settings)
    assert "do-not-print-me" not in str(settings.secret_key)


def test_celery_falls_back_to_the_redis_url() -> None:
    settings = Settings(env="local", database=DatabaseSettings(url=ASYNC_DSN))
    assert settings.celery_broker_url == settings.redis.url
    assert settings.celery_result_backend == settings.redis.url
