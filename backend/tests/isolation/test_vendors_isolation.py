"""Tenant isolation for the vendor register.

Four properties, each a different way the wall can be missing:

1. An unfiltered read from tenant A's session returns only A's rows — the policy
   bounds the row set, not the query.
2. A B row is *absent* by id, and the service raises ``NotFound`` for it —
   404-not-403 at the API is this database fact.
3. A session with no tenant bound sees nothing at all — fail closed.
4. A write carrying B's ``tenant_id`` from an A-bound session is refused by the
   policy's ``WITH CHECK``, including the cross-tenant (engagement in A, vendor in
   B) pair the denormalised ``tenant_id`` exists to catch.

Everything is seeded through the real service, never by writing a table.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import NotFound
from verity.db.base import Base
from verity.modules.audit.service import Membership
from verity.modules.vendors.models import Vendor, VendorContact, VendorEngagement
from verity.modules.vendors.service import (
    ContactInput,
    EngagementInput,
    VendorFilters,
    VendorInput,
    vendor_service,
)
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TenantModel = Vendor | VendorEngagement | VendorContact
TENANT_TABLES: tuple[type[TenantModel], ...] = (Vendor, VendorEngagement, VendorContact)


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Seeded:
    workspace: Workspace
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TwoTenants:
    a: Seeded
    b: Seeded


async def _populate(workspace: Workspace, vendor_name: str) -> Seeded:
    """A vendor with its implicit default engagement and one contact — a row on
    every one of the three tables, written through the real service."""
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        vendor = await vendor_service.create_vendor(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            data=VendorInput(name=vendor_name, data_classification="confidential"),
        )
        await vendor_service.add_contact(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            data=ContactInput(name="Dana Reed", email="dana@example.test", contact_type="security"),
        )
    return Seeded(
        workspace=workspace,
        vendor_id=vendor.id,
        engagement_id=vendor.engagements[0].id,
    )


@pytest.fixture
async def tenants() -> TwoTenants:
    a = await signup_workspace(company="Alpha Compliance", email="founder@alpha.example")
    b = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    return TwoTenants(a=await _populate(a, "Acme Cloud"), b=await _populate(b, "Acme Cloud"))


async def _count(session: AsyncSession, model: type[Base]) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_creating_a_vendor_writes_its_default_engagement(tenants: TwoTenants) -> None:
    """V10: every vendor has at least one engagement, in the same transaction."""
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        detail = await vendor_service.get_vendor(
            session, tenant_id=tenants.a.workspace.tenant_id, vendor_id=tenants.a.vendor_id
        )
    assert len(detail.engagements) == 1
    assert detail.engagement_count == 1
    assert detail.engagements[0].vendor_id == tenants.a.vendor_id


async def test_an_a_session_lists_only_a_rows_on_every_vendor_table(
    tenants: TwoTenants,
) -> None:
    """No WHERE clause anywhere: the policy, not the query, bounds every row set."""
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        for model in TENANT_TABLES:
            owners = list((await session.execute(select(model.tenant_id))).scalars())
            assert owners, f"{model.__name__}: the seed should have written rows"
            assert set(owners) == {tenants.a.workspace.tenant_id}, model.__name__


async def test_the_register_and_duplicate_check_never_cross_the_boundary(
    tenants: TwoTenants,
) -> None:
    """Both tenants have a vendor named "Acme Cloud"; neither can see the other's.

    The duplicate check is the interesting half: it reads every vendor in the
    tenant by design, so a missing policy would surface as a cross-tenant name
    leak in a warning message rather than as a failed query.
    """
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        items, total = await vendor_service.list_vendors(
            session, tenant_id=tenants.a.workspace.tenant_id, filters=VendorFilters()
        )
        assert total == 1
        assert [v.id for v in items] == [tenants.a.vendor_id]

        matches = await vendor_service.find_duplicates(
            session, tenant_id=tenants.a.workspace.tenant_id, name="Acme Cloud, Inc."
        )
        assert [m.id for m in matches] == [tenants.a.vendor_id]


async def test_a_b_row_reads_as_absent_by_id_not_forbidden(tenants: TwoTenants) -> None:
    """404-not-403 at the API is this database fact: the row simply is not there."""
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        assert await session.get(Vendor, tenants.b.vendor_id) is None

    async with session_scope(tenants.a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await vendor_service.get_vendor(
                session, tenant_id=tenants.a.workspace.tenant_id, vendor_id=tenants.b.vendor_id
            )

    async with session_scope(tenants.a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await vendor_service.update_engagement(
                session,
                tenant_id=tenants.a.workspace.tenant_id,
                actor=Membership(tenants.a.workspace.membership_id),
                vendor_id=tenants.b.vendor_id,
                engagement_id=tenants.b.engagement_id,
                data=EngagementInput(name="Hijacked"),
            )


async def test_an_unbound_session_sees_nothing_on_any_vendor_table(
    tenants: TwoTenants,
) -> None:
    """Fail closed: no tenant bound, not provider plane — zero rows, no error."""
    async with session_scope(None) as session:
        for model in TENANT_TABLES:
            assert await _count(session, model) == 0, model.__name__


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(
    tenants: TwoTenants,
) -> None:
    """Forgeries from an A-bound session, including the cross-tenant
    (engagement in A's stream, vendor in B) pair the denormalised tenant_id
    exists for."""
    forgeries: tuple[Base, ...] = (
        Vendor(id=uuid7(), tenant_id=tenants.b.workspace.tenant_id, name="Forged"),
        VendorEngagement(
            id=uuid7(),
            tenant_id=tenants.b.workspace.tenant_id,
            vendor_id=tenants.a.vendor_id,
            name="Forged engagement",
        ),
        VendorContact(
            id=uuid7(),
            tenant_id=tenants.b.workspace.tenant_id,
            vendor_id=tenants.a.vendor_id,
            name="Forged contact",
        ),
    )

    async def forge(instance: Base) -> None:
        async with session_scope(tenants.a.workspace.tenant_id) as session:
            session.add(instance)
            await session.flush()

    for instance in forgeries:
        with pytest.raises(DBAPIError, match="row-level security"):
            await forge(instance)
