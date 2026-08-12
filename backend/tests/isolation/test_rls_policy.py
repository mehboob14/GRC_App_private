"""The policy the migration helper writes, exercised end to end.

There are no tenant-owned tables yet, so this builds a throwaway one as the owner role
— exactly as ``verity.db.rls.enable_rls`` would — and then queries it as the application
role. That proves the two properties the whole isolation story rests on before any real
table depends on them:

- unbound tenant context returns no rows and raises nothing (fail closed);
- the ``WITH CHECK`` half refuses a write into another tenant.

Nothing here disables row-level security or connects as a bypassing role. The table is
a test artifact, not part of the data model, and is dropped afterwards.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

import pytest
from sqlalchemy import CursorResult, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from verity.core.config import Settings
from verity.core.rls import bind_tenant_context
from verity.db.rls import tenant_policy_predicate

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TABLE = "rls_probe"
TENANT_A = uuid.UUID("0198f0c0-0000-7000-8000-00000000000a")
TENANT_B = uuid.UUID("0198f0c0-0000-7000-8000-00000000000b")


@pytest.fixture
async def probe_table(settings: Settings, app_engine: AsyncEngine) -> AsyncIterator[None]:
    """Create a tenant-scoped table as the owner, with the real policy on it."""
    predicate = tenant_policy_predicate()
    app_role = settings.database.app_role
    owner_engine = create_async_engine(settings.database.effective_migration_url, poolclass=None)
    try:
        async with owner_engine.begin() as connection:
            await connection.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))
            await connection.execute(
                text(
                    f"CREATE TABLE {TABLE} ("
                    f"  id uuid PRIMARY KEY,"
                    f"  tenant_id uuid NOT NULL,"
                    f"  label text NOT NULL"
                    f")"
                )
            )
            await connection.execute(
                text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO {app_role}")
            )
            # Seeded before the policy exists. FORCE applies to the owner too — that is
            # the reason it is there — so seeding two tenants afterwards would need the
            # fixture to bind and rebind context, and a fixture doing that is a fixture
            # that can quietly seed the wrong tenant.
            for tenant_id, label in ((TENANT_A, "belongs-to-a"), (TENANT_B, "belongs-to-b")):
                await connection.execute(
                    text(
                        f"INSERT INTO {TABLE} (id, tenant_id, label) "
                        f"VALUES (:id, :tenant_id, :label)"
                    ),
                    {"id": uuid.uuid4(), "tenant_id": tenant_id, "label": label},
                )
            # Both halves, exactly as enable_rls emits them. FORCE matters because the
            # owner created the table and ENABLE alone would not apply to it.
            await connection.execute(text(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY"))
            await connection.execute(text(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY"))
            await connection.execute(
                text(
                    f"CREATE POLICY tenant_isolation ON {TABLE} "
                    f"FOR ALL USING ({predicate}) WITH CHECK ({predicate})"
                )
            )
        yield
    finally:
        async with owner_engine.begin() as connection:
            await connection.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))
        await owner_engine.dispose()


@pytest.fixture
async def app_sessions(
    app_engine: AsyncEngine,
    assert_app_role_cannot_bypass_rls: None,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=app_engine, expire_on_commit=False, autoflush=False)


async def _labels(session: AsyncSession) -> list[str]:
    result = await session.execute(text(f"SELECT label FROM {TABLE} ORDER BY label"))
    return list(result.scalars())


async def _affected_rows(
    session: AsyncSession,
    statement: str,
    params: dict[str, object],
) -> int:
    """How many rows a write touched.

    ``rowcount`` lives on the cursor result; ``Session.execute`` is typed as returning
    the narrower ORM ``Result``.
    """
    result = cast("CursorResult[Any]", await session.execute(text(statement), params))
    return result.rowcount


async def test_unbound_context_returns_no_rows_and_no_error(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Fail closed.

    The shorter predicate — ``current_setting('app.tenant_id')::uuid`` with no
    ``missing_ok`` and no ``NULLIF`` — raises here instead, which surfaces as a 500 and
    makes the provider plane unusable.
    """
    async with app_sessions() as session, session.begin():
        assert await _labels(session) == []


async def test_a_bound_tenant_sees_only_its_own_rows(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_A)
        assert await _labels(session) == ["belongs-to-a"]

    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_B)
        assert await _labels(session) == ["belongs-to-b"]


async def test_a_tenant_cannot_read_another_tenants_row_by_id(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Which is why a cross-tenant fetch is a 404 and not a 403: it is simply absent."""
    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_B)
        row_id = (await session.execute(text(f"SELECT id FROM {TABLE}"))).scalar_one()

    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_A)
        found = (
            await session.execute(text(f"SELECT label FROM {TABLE} WHERE id = :id"), {"id": row_id})
        ).scalar_one_or_none()
        assert found is None


async def test_a_tenant_cannot_update_another_tenants_row(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_A)
        affected = await _affected_rows(
            session,
            f"UPDATE {TABLE} SET label = 'hijacked' WHERE tenant_id = :tenant_id",
            {"tenant_id": TENANT_B},
        )
        assert affected == 0

    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_B)
        assert await _labels(session) == ["belongs-to-b"]


async def test_a_tenant_cannot_delete_another_tenants_row(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_A)
        affected = await _affected_rows(
            session,
            f"DELETE FROM {TABLE} WHERE tenant_id = :tenant_id",
            {"tenant_id": TENANT_B},
        )
        assert affected == 0


async def test_a_tenant_cannot_insert_a_row_into_another_tenant(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    """The ``WITH CHECK`` half.

    Without it reads are isolated and writes are not, which is the more damaging half:
    a forged ``tenant_id`` would plant a row inside someone else's workspace.
    """

    async def insert_row_owned_by_another_tenant() -> None:
        async with app_sessions() as session, session.begin():
            await bind_tenant_context(session, TENANT_A)
            await session.execute(
                text(
                    f"INSERT INTO {TABLE} (id, tenant_id, label) VALUES (:id, :tenant_id, :label)"
                ),
                {"id": uuid.uuid4(), "tenant_id": TENANT_B, "label": "planted"},
            )

    with pytest.raises(DBAPIError) as raised:
        await insert_row_owned_by_another_tenant()
    assert "row-level security" in str(raised.value).lower()


async def test_an_insert_into_the_bound_tenant_succeeds(
    probe_table: None,
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    """The policy must not be so tight that legitimate work fails."""
    async with app_sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_A)
        await session.execute(
            text(f"INSERT INTO {TABLE} (id, tenant_id, label) VALUES (:id, :tenant_id, :label)"),
            {"id": uuid.uuid4(), "tenant_id": TENANT_A, "label": "also-a"},
        )
        assert await _labels(session) == ["also-a", "belongs-to-a"]
