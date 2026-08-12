"""Append-only enforcement on ``audit_log``, all three layers, plus atomicity.

The three layers cover what the others miss (add-audit-trail/design.md):

1. **Revoked grant** — refuses the application role with ``permission denied``.
2. **Trigger** — binds the roles the grant does not, the table's owner included.
   On ``audit_log`` itself an owner ``UPDATE`` matches nothing first, because RLS
   has no UPDATE policy and ``FORCE`` applies to the owner — so the trigger is
   proven where it is reachable: a throwaway owner table carrying the same shared
   guard function, with no RLS in front of it.
3. **ORM listeners** — raise before a flush emits any SQL.

Nothing here disables row-level security or connects as a bypassing role.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.db.rls import append_only_function_ddl, append_only_trigger_ddl
from verity.modules.audit.models import AuditLog, AuditLogAppendOnlyError
from verity.modules.audit.service import Membership, audit_service
from verity.shared.ids import uuid7

pytestmark = pytest.mark.integration

TENANT = uuid.UUID("0198f0c0-0000-7000-8000-0000000000cc")


@pytest.fixture(autouse=True)
async def _fresh_process_engine(clean_audit_log: None) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
async def recorded_row_id() -> uuid.UUID:
    """One committed audit row in the tenant's stream, written the real way."""
    async with session_scope(TENANT) as session:
        await audit_service.record(
            session,
            action="create",
            object_type="control",
            object_id=uuid7(),
            actor=Membership(uuid7()),
            tenant_id=TENANT,
            after={"status": "draft"},
        )
        # Read back inside the scope: the id is needed after the commit, and the
        # scope's exit is what makes the row visible to later sessions.
        row_id: uuid.UUID = (await session.execute(select(AuditLog.id))).scalar_one()
    return row_id


async def _count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(AuditLog))).scalar_one()


# ---------------------------------------------------------------------------
# Layer 1 — the revoked grant refuses the application role outright
# ---------------------------------------------------------------------------


async def test_an_update_by_the_application_role_is_refused(
    recorded_row_id: uuid.UUID,
) -> None:
    async def attempt() -> None:
        async with session_scope(TENANT) as session:
            await session.execute(
                text("UPDATE audit_log SET action = 'update' WHERE id = :id"),
                {"id": recorded_row_id},
            )

    with pytest.raises(DBAPIError) as raised:
        await attempt()
    assert "permission denied" in str(raised.value).lower()

    async with session_scope(TENANT) as session:
        row = await session.get(AuditLog, recorded_row_id)
    assert row is not None
    assert row.action == "create", "the record must be unchanged"


async def test_a_delete_by_the_application_role_is_refused(
    recorded_row_id: uuid.UUID,
) -> None:
    async def attempt() -> None:
        async with session_scope(TENANT) as session:
            await session.execute(
                text("DELETE FROM audit_log WHERE id = :id"), {"id": recorded_row_id}
            )

    with pytest.raises(DBAPIError) as raised:
        await attempt()
    assert "permission denied" in str(raised.value).lower()

    async with session_scope(TENANT) as session:
        assert await session.get(AuditLog, recorded_row_id) is not None


# ---------------------------------------------------------------------------
# Layer 2 — the owner role. The grant does not bind it; RLS and the trigger do.
# ---------------------------------------------------------------------------


@pytest.fixture
async def owner_engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(settings.database.effective_migration_url, poolclass=None)
    try:
        yield engine
    finally:
        await engine.dispose()


async def test_the_owner_role_cannot_update_or_delete_an_audit_row(
    recorded_row_id: uuid.UUID,
    owner_engine: AsyncEngine,
) -> None:
    """No UPDATE or DELETE policy exists, and FORCE applies RLS to the owner too:
    the statement matches nothing, touches nothing, and the row survives."""
    async with owner_engine.begin() as connection:
        updated = await connection.execute(
            text("UPDATE audit_log SET action = 'update' WHERE id = :id"),
            {"id": recorded_row_id},
        )
        deleted = await connection.execute(
            text("DELETE FROM audit_log WHERE id = :id"), {"id": recorded_row_id}
        )
    assert updated.rowcount == 0
    assert deleted.rowcount == 0

    async with session_scope(TENANT) as session:
        row = await session.get(AuditLog, recorded_row_id)
    assert row is not None
    assert row.action == "create"


@pytest.fixture
async def append_only_probe(owner_engine: AsyncEngine) -> AsyncIterator[None]:
    """An owner-owned table carrying the same shared guard audit_log carries,
    with no RLS in front — the one place the trigger is reachable in a test that
    never disables a policy and never uses a bypassing role."""
    async with owner_engine.begin() as connection:
        await connection.execute(text("DROP TABLE IF EXISTS append_probe"))
        await connection.execute(text("CREATE TABLE append_probe (id int PRIMARY KEY)"))
        await connection.execute(text(append_only_function_ddl()))
        await connection.execute(text(append_only_trigger_ddl("append_probe")))
        await connection.execute(text("INSERT INTO append_probe (id) VALUES (1)"))
    try:
        yield
    finally:
        async with owner_engine.begin() as connection:
            await connection.execute(text("DROP TABLE IF EXISTS append_probe"))


async def test_the_trigger_refuses_the_owner_where_rls_does_not_stand_in_front(
    append_only_probe: None,
    owner_engine: AsyncEngine,
) -> None:
    """The trigger half of ``make_append_only``, fired as the owner: this is the
    layer that holds even for a role the revoked grant cannot bind."""
    async with owner_engine.connect() as connection:
        with pytest.raises(DBAPIError) as update_refused:
            await connection.execute(text("UPDATE append_probe SET id = 2 WHERE id = 1"))
        await connection.rollback()
        assert "append-only" in str(update_refused.value)

        with pytest.raises(DBAPIError) as delete_refused:
            await connection.execute(text("DELETE FROM append_probe WHERE id = 1"))
        await connection.rollback()
        assert "append-only" in str(delete_refused.value)


# ---------------------------------------------------------------------------
# Layer 3 — the ORM listeners raise before a flush reaches the database
# ---------------------------------------------------------------------------


async def test_an_orm_update_is_refused_before_any_sql_is_emitted(
    recorded_row_id: uuid.UUID,
) -> None:
    async def attempt() -> None:
        async with session_scope(TENANT) as session:
            row = await session.get(AuditLog, recorded_row_id)
            assert row is not None
            row.action = "approve"
            await session.flush()

    # The ORM error, not a DBAPIError: the flush never reached the database.
    with pytest.raises(AuditLogAppendOnlyError, match="append-only"):
        await attempt()

    async with session_scope(TENANT) as session:
        row = await session.get(AuditLog, recorded_row_id)
    assert row is not None
    assert row.action == "create"


async def test_an_orm_delete_is_refused_before_any_sql_is_emitted(
    recorded_row_id: uuid.UUID,
) -> None:
    async def attempt() -> None:
        async with session_scope(TENANT) as session:
            row = await session.get(AuditLog, recorded_row_id)
            assert row is not None
            await session.delete(row)
            await session.flush()

    with pytest.raises(AuditLogAppendOnlyError, match="append-only"):
        await attempt()

    async with session_scope(TENANT) as session:
        assert await session.get(AuditLog, recorded_row_id) is not None


# ---------------------------------------------------------------------------
# Atomicity — the audit record and the change succeed or fail together
# ---------------------------------------------------------------------------


async def test_a_unit_of_work_that_raises_leaves_no_audit_row() -> None:
    """The write joined the caller's transaction and was already flushed; the
    rollback takes it away with everything else. No committed audit row may
    describe a change that did not happen."""

    async def failing_unit_of_work() -> None:
        async with session_scope(TENANT) as session:
            await audit_service.record(
                session,
                action="update",
                object_type="control",
                object_id=uuid7(),
                actor=Membership(uuid7()),
                tenant_id=TENANT,
                before={"status": "draft"},
                after={"status": "active"},
            )
            assert await _count(session) == 1, "flushed and visible inside the transaction"
            raise RuntimeError("the unit of work fails after recording")

    with pytest.raises(RuntimeError, match="fails after recording"):
        await failing_unit_of_work()

    async with session_scope(TENANT) as session:
        assert await _count(session) == 0


async def test_a_retried_unit_of_work_leaves_exactly_one_row() -> None:
    """The spec's 'runs twice' scenario: a retry after a rollback commits once."""

    async def unit_of_work(fail: bool) -> None:
        async with session_scope(TENANT) as session:
            await audit_service.record(
                session,
                action="transition",
                object_type="task",
                object_id=uuid7(),
                actor=Membership(uuid7()),
                tenant_id=TENANT,
                after={"state": "done"},
            )
            if fail:
                raise RuntimeError("first attempt fails")

    with pytest.raises(RuntimeError):
        await unit_of_work(fail=True)
    await unit_of_work(fail=False)

    async with session_scope(TENANT) as session:
        assert await _count(session) == 1
