"""``demo_requests`` is a provider-plane table: only a provider-plane unit of work reaches it.

The rows are a prospect's name, address and message, and no tenant owns them. As the
application role, against the migrated table with its policies, these prove the wall the
migration builds: a tenant-bound or unbound session sees no row and can neither add nor
change one, the provider plane can read, add and amend, and nobody can delete through the
application. The raw, unfiltered statements are deliberate: row-level security has to hold
when the application's own filter is absent.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.modules.leads.models import DemoRequest
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh_state(clean_demo_requests: None) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


def _request() -> DemoRequest:
    return DemoRequest(
        id=uuid7(), full_name="Ada Lovelace", email="ada@example.com", company="Analytical Engines"
    )


@pytest.fixture
async def stored() -> uuid.UUID:
    """One request, added the one way the application may: from the provider plane."""
    async with provider_session_scope() as session:
        row = _request()
        session.add(row)
        await session.flush()
    return row.id


async def _count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(DemoRequest))).scalar_one()


async def _add_as(tenant: uuid.UUID | None) -> None:
    async with session_scope(tenant) as session:
        session.add(_request())
        await session.flush()


async def _delete_as_provider(request_id: uuid.UUID) -> None:
    async with provider_session_scope() as session:
        await session.execute(delete(DemoRequest).where(DemoRequest.id == request_id))


async def _truncate_as_provider() -> None:
    async with provider_session_scope() as session:
        await session.execute(text("TRUNCATE demo_requests"))


async def test_the_provider_plane_reads_adds_and_amends(stored: uuid.UUID) -> None:
    async with provider_session_scope() as session:
        assert await _count(session) == 1
        row = await session.get(DemoRequest, stored)
        assert row is not None
        row.company = "Analytical Engines Ltd"
        session.add(_request())
    async with provider_session_scope() as session:
        assert await _count(session) == 2
        assert (await session.get(DemoRequest, stored)) is not None


async def test_a_tenant_bound_session_sees_no_request(stored: uuid.UUID) -> None:
    async with session_scope(uuid.uuid4()) as session:
        assert await _count(session) == 0
        assert await session.get(DemoRequest, stored) is None


async def test_an_unbound_session_sees_no_request(stored: uuid.UUID) -> None:
    """Fail closed: no tenant and not the provider plane means zero rows, and no error."""
    async with session_scope(None) as session:
        assert await _count(session) == 0
        assert await session.get(DemoRequest, stored) is None


@pytest.mark.parametrize("tenant", [uuid.uuid4(), None])
async def test_neither_can_add_one(tenant: uuid.UUID | None) -> None:
    """There is no policy for an insert outside the provider plane, so it is refused
    outright rather than filtered."""
    with pytest.raises(DBAPIError, match="row-level security"):
        await _add_as(tenant)


@pytest.mark.parametrize("tenant", [uuid.uuid4(), None])
async def test_nor_change_one(stored: uuid.UUID, tenant: uuid.UUID | None) -> None:
    async with session_scope(tenant) as session:
        result = cast(
            "CursorResult[Any]",
            await session.execute(
                update(DemoRequest)
                .where(DemoRequest.id == stored)
                .values(email="attacker@example.net")
            ),
        )
        assert result.rowcount == 0

    async with provider_session_scope() as session:
        row = await session.get(DemoRequest, stored)
        assert row is not None
        assert row.email == "ada@example.com"


async def test_nobody_can_delete_a_request_through_the_application(stored: uuid.UUID) -> None:
    """Not even the provider plane: the privilege is missing, which no policy could grant
    back, and the table has no DELETE policy besides."""
    with pytest.raises(DBAPIError, match="permission denied"):
        await _delete_as_provider(stored)

    with pytest.raises(DBAPIError, match="permission denied"):
        await _truncate_as_provider()

    async with provider_session_scope() as session:
        assert await _count(session) == 1


async def test_the_wall_is_in_the_catalogue(app_engine: AsyncEngine) -> None:
    """Enabled, forced, one policy for each command the application may use, no policy
    for any other, and the grants the migration promises."""
    async with app_engine.connect() as connection:
        flags = (
            await connection.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE relname = 'demo_requests'"
                )
            )
        ).one()
        commands = {
            row[0]
            for row in await connection.execute(
                text("SELECT cmd FROM pg_policies WHERE tablename = 'demo_requests'")
            )
        }
        privileges = {
            privilege: (
                await connection.execute(
                    text("SELECT has_table_privilege(current_user, 'demo_requests', :privilege)"),
                    {"privilege": privilege},
                )
            ).scalar_one()
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
        }
        await connection.rollback()

    assert tuple(flags) == (True, True), "row-level security must be enabled and forced"
    assert commands == {"SELECT", "INSERT", "UPDATE"}, "no ALL and no DELETE policy"
    assert privileges == {
        "SELECT": True,
        "INSERT": True,
        "UPDATE": True,
        "DELETE": False,
        "TRUNCATE": False,
    }
