"""Test fixtures.

Unit tests need nothing from here beyond ``settings``. Integration and isolation tests
connect to a **real Postgres with row-level security on, as the application role** —
never as a superuser, never as a role holding ``BYPASSRLS``, and no fixture disables a
policy (docs/conventions/testing.md). A suite that runs against a bypassing role proves
nothing while appearing to prove everything, which is worse than having no suite.

Locally, an unreachable database skips those suites with a message. In CI,
``VERITY_REQUIRE_DB=1`` turns that skip into a failure, because a silently skipped
isolation suite is exactly the failure mode docs/conventions/git.md calls never
acceptable.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker

from verity.core.config import Settings, get_settings, reset_settings_cache
from verity.core.crypto import reset_secret_box_cache
from verity.core.db import create_engine_from_settings

DB_REQUIRED_ENV_VAR = "VERITY_REQUIRE_DB"

# A test process must never inherit a developer's real DSN or a real master key from an
# ambient .env, so the defaults are set before Settings is first constructed.
_TEST_ENVIRONMENT = {
    "ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://verity_app:verity_app@localhost:5432/verity",
    "DATABASE_MIGRATION_URL": "postgresql+asyncpg://verity_owner:verity_owner@localhost:5432/verity",
    "REDIS_URL": "redis://localhost:6379/1",
    "LANGSMITH_TRACING": "false",
}


def pytest_configure(config: pytest.Config) -> None:
    for key, value in _TEST_ENVIRONMENT.items():
        os.environ.setdefault(key, value)
    reset_settings_cache()
    reset_secret_box_cache()


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture
def isolated_settings() -> Iterator[None]:
    """Let a test mutate the environment and see fresh Settings, then restore."""
    original = os.environ.copy()
    reset_settings_cache()
    reset_secret_box_cache()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)
        reset_settings_cache()
        reset_secret_box_cache()


def _database_required() -> bool:
    return os.environ.get(DB_REQUIRED_ENV_VAR, "").strip().lower() in {"1", "true", "yes"}


@pytest.fixture(scope="session")
async def app_engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """An engine bound to the **application** role."""
    engine = create_engine_from_settings(settings)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        message = (
            "Postgres is not reachable as the application role. Run `make up` and "
            "`make migrate`, or see docs/runbooks/local-setup.md."
        )
        if _database_required():
            pytest.fail(f"{message} ({type(exc).__name__})")
        pytest.skip(message)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
async def assert_app_role_cannot_bypass_rls(app_engine: AsyncEngine) -> None:
    """Refuse to run the database suites at all if the role can bypass RLS.

    This is a guard rather than a test: if the connection can bypass policies, every
    isolation assertion below it becomes vacuously true, and a green suite would be
    actively misleading.
    """
    async with app_engine.connect() as connection:
        row = (
            await connection.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )
        ).one()
    if row.rolsuper or row.rolbypassrls:
        pytest.fail(
            "the test connection can bypass row-level security "
            f"(rolsuper={row.rolsuper}, rolbypassrls={row.rolbypassrls}). "
            "Point DATABASE_URL at the application role; see infra/docker/postgres/init/."
        )


@pytest.fixture
async def app_connection(
    app_engine: AsyncEngine,
    assert_app_role_cannot_bypass_rls: None,
) -> AsyncIterator[AsyncConnection]:
    """A raw connection as the application role, rolled back afterwards."""
    async with app_engine.connect() as connection:
        try:
            yield connection
        finally:
            await connection.rollback()


@pytest.fixture
async def app_session(
    app_engine: AsyncEngine,
    assert_app_role_cannot_bypass_rls: None,
) -> AsyncIterator[AsyncSession]:
    """A session as the application role, with no tenant bound and no transaction open.

    No transaction, so a test can prove what happens before one is opened and can open
    its own to observe the transaction-local lifetime of the tenant setting.
    """
    factory = async_sessionmaker(bind=app_engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
