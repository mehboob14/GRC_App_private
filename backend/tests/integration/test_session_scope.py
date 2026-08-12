"""``session_scope`` — the transaction boundary every unit of work runs inside."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.db import dispose_engine, session_scope
from verity.core.rls import current_tenant_id

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _dispose_process_engine(app_engine: object) -> None:
    """``session_scope`` uses the cached process engine; drop it between modules."""
    await dispose_engine()


async def test_scope_opens_a_transaction_and_binds_the_tenant() -> None:
    tenant_id = uuid.uuid4()
    async with session_scope(tenant_id) as session:
        assert session.in_transaction()
        assert await current_tenant_id(session) == tenant_id


async def test_scope_with_no_tenant_binds_no_tenant() -> None:
    """The provider plane and global content. Not the same as binding nothing."""
    async with session_scope(None) as session:
        assert await current_tenant_id(session) is None


async def test_scope_commits_on_a_clean_exit() -> None:
    async with session_scope(uuid.uuid4()) as session:
        pass
    assert not session.in_transaction()


async def test_scope_rolls_back_when_the_body_raises() -> None:
    escaped: list[AsyncSession] = []

    async def failing_unit_of_work() -> None:
        async with session_scope(uuid.uuid4()) as session:
            escaped.append(session)
            await session.execute(text("SELECT 1"))
            raise RuntimeError("deliberate")

    with pytest.raises(RuntimeError, match="deliberate"):
        await failing_unit_of_work()
    assert not escaped[0].in_transaction()


async def test_a_savepoint_does_not_disturb_the_bound_tenant() -> None:
    """Which is how a service gets a partial rollback without losing tenant context."""
    tenant_id = uuid.uuid4()
    async with session_scope(tenant_id) as session:
        nested = await session.begin_nested()
        await session.execute(text("SELECT 1"))
        await nested.rollback()
        assert await current_tenant_id(session) == tenant_id


async def test_each_scope_is_independent() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()
    async with session_scope(first) as session:
        assert await current_tenant_id(session) == first
    async with session_scope(second) as session:
        assert await current_tenant_id(session) == second
