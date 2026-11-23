"""Tenant isolation for ``tenant_sso``.

1. A session for tenant A reads only A's row; tenant B's session and an unbound one read none.
2. The provider plane reads every row (sign in needs it before a tenant is known) but cannot write.
3. A write carrying B's ``tenant_id`` from an A session is refused by ``WITH CHECK``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.modules.iam.models import TenantSso
from verity.modules.iam.service import iam_service
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Two:
    a: Workspace
    b: Workspace


@pytest.fixture
async def tenants() -> Two:
    a = await signup_workspace(company="Alpha Sso", email="founder@alpha-sso.example")
    b = await signup_workspace(company="Bravo Sso", email="founder@bravo-sso.example")
    async with session_scope(a.tenant_id) as session:
        await iam_service.save_sso(
            session,
            tenant_id=a.tenant_id,
            actor_membership_id=a.membership_id,
            organization_alias="alpha",
            domains=["alpha-sso.example"],
            enabled=True,
            enforce=False,
            jit_enabled=False,
            default_role_id=None,
        )
    return Two(a=a, b=b)


async def test_only_the_owning_tenant_reads_its_row(tenants: Two) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        owners = list((await session.execute(select(TenantSso.tenant_id))).scalars())
    assert owners == [tenants.a.tenant_id]
    for scope in (tenants.b.tenant_id, None):
        async with session_scope(scope) as session:
            count = (
                await session.execute(select(func.count()).select_from(TenantSso))
            ).scalar_one()
        assert count == 0


async def test_the_provider_plane_reads_but_cannot_write(tenants: Two) -> None:
    async with provider_session_scope() as session:
        aliases = list((await session.execute(select(TenantSso.organization_alias))).scalars())
    assert aliases == ["alpha"]

    async def forge() -> None:
        async with provider_session_scope() as session:
            session.add(
                TenantSso(id=uuid7(), tenant_id=tenants.b.tenant_id, organization_alias="bravo")
            )
            await session.flush()

    with pytest.raises(DBAPIError, match="row-level security"):
        await forge()


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(tenants: Two) -> None:
    async def forge() -> None:
        async with session_scope(tenants.a.tenant_id) as session:
            session.add(
                TenantSso(id=uuid7(), tenant_id=tenants.b.tenant_id, organization_alias="bravo")
            )
            await session.flush()

    with pytest.raises(DBAPIError, match="row-level security"):
        await forge()
