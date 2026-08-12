"""``audit_log`` isolation: two tenant streams plus the provider plane.

Everything here goes through the real entry points — ``session_scope`` /
``provider_session_scope`` and ``AuditService`` — as the application role, against the
migrated table with its four policies. The unfiltered raw queries are deliberate: the
repository's explicit ``tenant_id`` filter is the first wall, and a test that only
queries through it would prove the filter rather than the policy. RLS has to hold when
the filter is absent.

Rows are committed on purpose — cross-plane visibility can only be observed between
separate transactions — so ``clean_audit_log`` truncates as the owner around each test.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import Membership, PlatformAdmin, audit_service
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TENANT_A = uuid.UUID("0198f0c0-0000-7000-8000-0000000000aa")
TENANT_B = uuid.UUID("0198f0c0-0000-7000-8000-0000000000bb")


@pytest.fixture(autouse=True)
async def _fresh_process_engine(clean_audit_log: None) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


async def _record_for(session: AsyncSession, tenant_id: uuid.UUID | None, label: str) -> None:
    await audit_service.record(
        session,
        action="create",
        object_type="control",
        object_id=uuid7(),
        actor=Membership(uuid7()),
        tenant_id=tenant_id,
        after={"label": label},
    )


async def _labels_unfiltered(session: AsyncSession) -> set[str]:
    """Every row the policy lets this session see — no application filter at all."""
    result = await session.execute(select(AuditLog))
    return {entry.after["label"] for entry in result.scalars() if entry.after}


async def _count_unfiltered(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(AuditLog))).scalar_one()


@pytest.fixture
async def two_tenant_streams() -> None:
    """One committed row in each tenant's stream, written from that tenant's scope."""
    async with session_scope(TENANT_A) as session:
        await _record_for(session, TENANT_A, "stream-a")
    async with session_scope(TENANT_B) as session:
        await _record_for(session, TENANT_B, "stream-b")


async def test_a_tenant_sees_only_its_own_stream(two_tenant_streams: None) -> None:
    async with session_scope(TENANT_A) as session:
        assert await _labels_unfiltered(session) == {"stream-a"}
    async with session_scope(TENANT_B) as session:
        assert await _labels_unfiltered(session) == {"stream-b"}


async def test_the_read_route_path_returns_only_the_callers_stream(
    two_tenant_streams: None,
) -> None:
    """The same property through the stack the route uses: service over repository."""
    async with session_scope(TENANT_A) as session:
        entries, _cursor = await audit_service.list_page(session, tenant_id=TENANT_A, limit=10)
    assert [entry.after["label"] for entry in entries if entry.after] == ["stream-a"]


async def test_an_unbound_session_sees_nothing_and_raises_nothing(
    two_tenant_streams: None,
) -> None:
    """Fail closed: no tenant bound, not provider plane — zero rows, no error."""
    async with session_scope(None) as session:
        assert await _count_unfiltered(session) == 0


async def test_a_tenant_cannot_read_another_tenants_record_by_id(
    two_tenant_streams: None,
) -> None:
    """Absent, not forbidden — which is why the API answers 404 and never 403."""
    async with session_scope(TENANT_B) as session:
        row_id = (await session.execute(select(AuditLog.id))).scalar_one()
    async with session_scope(TENANT_A) as session:
        found = await session.get(AuditLog, row_id)
    assert found is None


async def test_provider_plane_rows_are_invisible_to_every_tenant(
    two_tenant_streams: None,
) -> None:
    """``tenant_id IS NULL`` never satisfies the tenant predicate — invisible by
    construction, in both a listing and a count, exactly as the spec scenario asks."""
    async with provider_session_scope() as session:
        await audit_service.record(
            session,
            action="create",
            object_type="platform_admin",
            object_id=uuid7(),
            actor=PlatformAdmin(uuid7()),
            tenant_id=None,
            after={"label": "provider-only"},
        )
    for tenant_id in (TENANT_A, TENANT_B):
        async with session_scope(tenant_id) as session:
            assert "provider-only" not in await _labels_unfiltered(session)
            assert await _count_unfiltered(session) == 1


async def test_a_session_bound_to_one_tenant_cannot_insert_into_another(
    two_tenant_streams: None,
) -> None:
    """The WITH CHECK half of the tenant insert policy."""

    async def forge() -> None:
        async with session_scope(TENANT_A) as session:
            await _record_for(session, TENANT_B, "forged")

    with pytest.raises(DBAPIError) as raised:
        await forge()
    assert "row-level security" in str(raised.value).lower()

    async with session_scope(TENANT_B) as session:
        assert "forged" not in await _labels_unfiltered(session)


async def test_a_tenant_session_cannot_write_the_provider_stream() -> None:
    """A NULL ``tenant_id`` fails the tenant WITH CHECK too: the provider stream is
    not reachable from the tenant plane in either direction."""

    async def forge() -> None:
        async with session_scope(TENANT_A) as session:
            await _record_for(session, None, "forged-provider")

    with pytest.raises(DBAPIError) as raised:
        await forge()
    assert "row-level security" in str(raised.value).lower()


async def test_the_provider_plane_writes_both_streams_and_reads_across_them(
    two_tenant_streams: None,
) -> None:
    """A platform admin provisioning tenant A writes into A's stream — the event
    belongs to A's history — and a provider-plane event carries no tenant at all.
    The provider plane reads across every stream (add-audit-trail/design.md)."""
    admin = PlatformAdmin(uuid7())
    async with provider_session_scope() as session:
        await audit_service.record(
            session,
            action="create",
            object_type="tenant",
            object_id=uuid7(),
            actor=admin,
            tenant_id=TENANT_A,
            after={"label": "provisioned-a"},
        )
        await audit_service.record(
            session,
            action="create",
            object_type="session",
            object_id=uuid7(),
            actor=admin,
            tenant_id=None,
            after={"label": "admin-login"},
        )

    # Tenant A sees the event written into its stream, but never the no-tenant one.
    async with session_scope(TENANT_A) as session:
        labels = await _labels_unfiltered(session)
    assert "provisioned-a" in labels
    assert "admin-login" not in labels

    # The provider plane sees every stream, and the no-tenant rows besides.
    async with provider_session_scope() as session:
        labels = await _labels_unfiltered(session)
    assert {"stream-a", "stream-b", "provisioned-a", "admin-login"} <= labels
