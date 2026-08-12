"""``provider_session_scope`` — the one entry point that binds ``app.provider_plane``."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.core.rls import current_tenant_id, is_provider_plane_bound

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _dispose_process_engine(app_engine: object) -> None:
    """The scope uses the cached process engine; drop it between modules."""
    await dispose_engine()


async def test_the_scope_binds_the_provider_plane_and_no_tenant() -> None:
    async with provider_session_scope() as session:
        assert session.in_transaction()
        assert await is_provider_plane_bound(session) is True
        assert await current_tenant_id(session) is None


async def test_the_scope_commits_on_a_clean_exit() -> None:
    async with provider_session_scope() as session:
        pass
    assert not session.in_transaction()


async def test_the_scope_rolls_back_when_the_body_raises() -> None:
    escaped: list[AsyncSession] = []

    async def failing_unit_of_work() -> None:
        async with provider_session_scope() as session:
            escaped.append(session)
            await session.execute(text("SELECT 1"))
            raise RuntimeError("deliberate")

    with pytest.raises(RuntimeError, match="deliberate"):
        await failing_unit_of_work()
    assert not escaped[0].in_transaction()


async def test_the_widened_visibility_dies_with_the_scope() -> None:
    """A later plain unit of work must start from nothing, even on a reused pool."""
    async with provider_session_scope():
        pass
    async with session_scope(None) as later:
        assert await is_provider_plane_bound(later) is False
