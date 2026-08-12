"""The tenant-context primitive, against a real Postgres as the application role.

Every RLS policy in this system reads ``app.tenant_id``. These tests assert the
properties that make it safe to rely on; if any of them regresses, isolation is gone
everywhere at once and nothing else would notice.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from verity.core.config import Settings
from verity.core.db import create_engine_from_settings
from verity.core.rls import (
    TENANT_ID_SETTING,
    TenantContextError,
    bind_tenant_context,
    current_tenant_id,
    require_tenant_context,
)

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

READ_SETTING = text(f"SELECT current_setting('{TENANT_ID_SETTING}', true)")


async def test_application_role_cannot_bypass_row_level_security(
    app_connection: AsyncConnection,
) -> None:
    """The precondition every other assertion in this directory depends on.

    A suite running as a superuser or a ``BYPASSRLS`` role proves nothing while
    appearing to prove everything, which is worse than having no suite. conftest also
    refuses to run the database fixtures at all in that case; this makes it a visible
    result rather than only a refusal.
    """
    row = (
        await app_connection.execute(
            text(
                "SELECT current_user AS role_name, rolsuper, rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            )
        )
    ).one()
    assert row.rolsuper is False, f"{row.role_name} is a superuser and bypasses every policy"
    assert row.rolbypassrls is False, f"{row.role_name} holds BYPASSRLS"


async def test_bound_tenant_is_readable_inside_its_transaction(
    app_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    async with app_session.begin():
        await bind_tenant_context(app_session, tenant_id)
        assert await current_tenant_id(app_session) == tenant_id
        assert await require_tenant_context(app_session) == tenant_id


async def test_no_tenant_is_bound_by_default(app_session: AsyncSession) -> None:
    async with app_session.begin():
        assert await current_tenant_id(app_session) is None


async def test_binding_none_means_no_rows_rather_than_an_error(
    app_session: AsyncSession,
) -> None:
    """Provider-plane work binds "no tenant", which is not the same as binding nothing.

    ``set_config`` has no NULL, so it stores an empty string, and the policy predicate
    turns that into NULL so nothing matches. The read side must report it as ``None``.
    """
    async with app_session.begin():
        await bind_tenant_context(app_session, None)
        assert (await app_session.execute(READ_SETTING)).scalar_one() == ""
        assert await current_tenant_id(app_session) is None
        with pytest.raises(TenantContextError, match="no tenant is bound"):
            await require_tenant_context(app_session)


async def test_context_does_not_survive_a_commit(app_session: AsyncSession) -> None:
    """``is_local=true`` is what makes this true. It is the whole reason for it."""
    tenant_id = uuid.uuid4()
    async with app_session.begin():
        await bind_tenant_context(app_session, tenant_id)
    async with app_session.begin():
        assert await current_tenant_id(app_session) is None


async def test_context_does_not_survive_a_rollback(app_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    transaction = await app_session.begin()
    await bind_tenant_context(app_session, tenant_id)
    await transaction.rollback()
    async with app_session.begin():
        assert await current_tenant_id(app_session) is None


async def test_rebinding_within_a_transaction_replaces_the_value(
    app_session: AsyncSession,
) -> None:
    first, second = uuid.uuid4(), uuid.uuid4()
    async with app_session.begin():
        await bind_tenant_context(app_session, first)
        await bind_tenant_context(app_session, second)
        assert await current_tenant_id(app_session) == second


async def test_binding_outside_a_transaction_is_refused(app_session: AsyncSession) -> None:
    """Silently discarding it would leave the caller reading nothing and none the wiser."""
    assert not app_session.in_transaction()
    with pytest.raises(TenantContextError, match="requires an open transaction"):
        await bind_tenant_context(app_session, uuid.uuid4())


async def test_a_pooled_connection_carries_no_context_from_its_previous_user(
    settings: Settings,
    assert_app_role_cannot_bypass_rls: None,
) -> None:
    """The failure that pooling introduces, which no query review would catch.

    A pool of exactly one connection with no overflow, so the second unit of work is
    guaranteed to be handed the same physical connection the first one used.
    """
    engine: AsyncEngine = create_engine_from_settings(settings, pool_size=1, max_overflow=0)
    try:
        factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        tenant_id = uuid.uuid4()

        async with factory() as first, first.begin():
            await bind_tenant_context(first, tenant_id)
            assert await current_tenant_id(first) == tenant_id

        async with factory() as second, second.begin():
            assert await current_tenant_id(second) is None, (
                "the pooled connection inherited the previous unit of work's tenant"
            )
    finally:
        await engine.dispose()


async def test_two_concurrent_units_of_work_do_not_see_each_other(
    app_engine: AsyncEngine,
    assert_app_role_cannot_bypass_rls: None,
) -> None:
    """Each transaction has its own setting, on its own connection, simultaneously."""
    factory = async_sessionmaker(bind=app_engine, expire_on_commit=False, autoflush=False)
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()

    async with (
        factory() as session_a,
        factory() as session_b,
        session_a.begin(),
        session_b.begin(),
    ):
        await bind_tenant_context(session_a, tenant_a)
        await bind_tenant_context(session_b, tenant_b)
        assert await current_tenant_id(session_a) == tenant_a
        assert await current_tenant_id(session_b) == tenant_b
