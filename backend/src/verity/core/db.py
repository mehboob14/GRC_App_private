"""Async engine, session factory, and the transaction boundary.

Where the transaction boundary lives, and why
---------------------------------------------
``session_scope`` opens the transaction, binds tenant context inside it, yields, and
commits on a clean exit. Services do not call ``commit``.

That is not a style preference. The tenant setting is transaction-local, so a service
that commits half way through its work leaves every statement after the commit with no
tenant bound. Under RLS those statements return zero rows and raise nothing — data
that exists appears to be missing, in production, intermittently, depending on where
the commit landed. Owning the boundary one level up makes that failure unreachable.

A service that needs a partial rollback uses ``session.begin_nested()``. A savepoint
does not disturb the transaction-local setting.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from verity.core.config import Settings, get_settings
from verity.core.rls import bind_provider_plane, bind_tenant_context


def create_engine_from_settings(settings: Settings, **overrides: object) -> AsyncEngine:
    """Build an engine. ``get_engine`` is the one the application uses.

    Exposed separately so tests can build an engine with a pool of their own — pooling
    behaviour is part of what the isolation suite has to assert.
    """
    database = settings.database
    options: dict[str, object] = {
        "echo": database.echo,
        # A connection killed by a network blip or a database restart otherwise
        # surfaces as a failed request instead of a transparent reconnect.
        "pool_pre_ping": True,
        "pool_size": database.pool_size,
        "max_overflow": database.max_overflow,
        "pool_timeout": database.pool_timeout_seconds,
        "pool_recycle": database.pool_recycle_seconds,
        "connect_args": {
            "timeout": database.connect_timeout_seconds,
            "server_settings": {
                "application_name": f"{settings.service_name}-{settings.env}",
                # Every statement has an upper bound. One unbounded query holding a
                # connection is how a pool of ten becomes an outage.
                "statement_timeout": str(database.statement_timeout_ms),
            },
        },
    }
    options.update(overrides)
    return create_async_engine(database.url, **options)


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """The process-wide engine, created on first use."""
    return create_engine_from_settings(get_settings())


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


async def dispose_engine() -> None:
    """Close every pooled connection and drop the cached engine.

    Called from the application lifespan and from test teardown.
    """
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()


@asynccontextmanager
async def session_scope(tenant_id: uuid.UUID | None = None) -> AsyncIterator[AsyncSession]:
    """One unit of work, with ``tenant_id`` bound for its whole lifetime.

    Commits on a clean exit, rolls back on an exception. Pass ``None`` for
    provider-plane work; see ``core.rls.bind_tenant_context``.

    This is the entry point for anything that is not an HTTP request — Celery tasks,
    scheduled jobs, management commands. Request handlers get a session through the
    dependencies in ``core.deps``, which are built on this.
    """
    async with get_sessionmaker()() as session, session.begin():
        await bind_tenant_context(session, tenant_id)
        yield session


@asynccontextmanager
async def provider_session_scope() -> AsyncIterator[AsyncSession]:
    """One provider-plane unit of work: no tenant bound, ``app.provider_plane`` on.

    ``session_scope(None)`` with the provider-plane setting bound inside the same
    transaction, so dual-plane tables (``audit_log``) become visible across streams.
    Entered on behalf of an authenticated platform admin, by the iam auth flows for
    identity resolution, and by the leads module's one public route, which writes a
    single provider-plane table and its audit row. Nothing here checks who is asking,
    which is exactly why no other code path may use it.
    """
    async with session_scope(None) as session:
        await bind_provider_plane(session)
        yield session


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for a session with no tenant bound.

    For the provider plane and global content. Anything reading a tenant-scoped table
    uses ``core.deps.get_tenant_session`` instead.
    """
    async with session_scope(None) as session:
        yield session
