"""The provider-plane setting, against a real Postgres as the application role.

``app.provider_plane`` is honestly a switch that widens visibility across tenant
streams (add-audit-trail/design.md), so it gets the same lifetime proofs as
``app.tenant_id``: transaction-local, dead on commit and rollback, and never
inherited through the connection pool.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from verity.core.config import Settings
from verity.core.db import create_engine_from_settings
from verity.core.rls import (
    PROVIDER_PLANE_ON,
    PROVIDER_PLANE_SETTING,
    TenantContextError,
    bind_provider_plane,
    current_tenant_id,
    is_provider_plane_bound,
)

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

READ_SETTING = text(f"SELECT current_setting('{PROVIDER_PLANE_SETTING}', true)")


async def test_the_provider_plane_is_not_bound_by_default(app_session: AsyncSession) -> None:
    async with app_session.begin():
        assert await is_provider_plane_bound(app_session) is False


async def test_binding_sets_the_guc_inside_its_transaction(app_session: AsyncSession) -> None:
    async with app_session.begin():
        await bind_provider_plane(app_session)
        assert (await app_session.execute(READ_SETTING)).scalar_one() == PROVIDER_PLANE_ON
        assert await is_provider_plane_bound(app_session) is True


async def test_binding_the_provider_plane_binds_no_tenant(app_session: AsyncSession) -> None:
    """The two settings are independent facts. Widening visibility must not also
    impersonate a tenant."""
    async with app_session.begin():
        await bind_provider_plane(app_session)
        assert await current_tenant_id(app_session) is None


async def test_the_setting_does_not_survive_a_commit(app_session: AsyncSession) -> None:
    """``is_local=true`` is what makes this true — the same property the tenant
    setting lives and dies by."""
    async with app_session.begin():
        await bind_provider_plane(app_session)
    async with app_session.begin():
        assert await is_provider_plane_bound(app_session) is False


async def test_the_setting_does_not_survive_a_rollback(app_session: AsyncSession) -> None:
    transaction = await app_session.begin()
    await bind_provider_plane(app_session)
    await transaction.rollback()
    async with app_session.begin():
        assert await is_provider_plane_bound(app_session) is False


async def test_binding_outside_a_transaction_is_refused(app_session: AsyncSession) -> None:
    """Silently discarding it would leave a provider-plane job reading nothing."""
    assert not app_session.in_transaction()
    with pytest.raises(TenantContextError, match="requires an open transaction"):
        await bind_provider_plane(app_session)


async def test_a_pooled_connection_carries_no_provider_plane_from_its_previous_user(
    settings: Settings,
    assert_app_role_cannot_bypass_rls: None,
) -> None:
    """The failure pooling introduces: a tenant-plane unit of work handed the
    connection a platform admin just used must not inherit cross-stream visibility.

    A pool of exactly one connection with no overflow, so the second unit of work is
    guaranteed the same physical connection the first one used.
    """
    engine = create_engine_from_settings(settings, pool_size=1, max_overflow=0)
    try:
        factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

        async with factory() as first, first.begin():
            await bind_provider_plane(first)
            assert await is_provider_plane_bound(first) is True

        async with factory() as second, second.begin():
            assert await is_provider_plane_bound(second) is False, (
                "the pooled connection inherited provider-plane visibility"
            )
    finally:
        await engine.dispose()
