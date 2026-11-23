"""Tenant isolation for Get Started's one stored decision: a skipped step.

1. An unfiltered read from tenant A's session returns only A's rows.
2. A session with no tenant bound sees nothing.
3. A write carrying B's ``tenant_id`` from an A-bound session is refused by ``WITH CHECK``.
4. A step skipped in one workspace still reads open in the other, through the service.

Rows are written through the real service, never directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.modules.audit.service import Membership
from verity.modules.onboarding.models import OnboardingStepSkip
from verity.modules.onboarding.service import onboarding_service
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
    a = await signup_workspace(company="Alpha Onboarding", email="founder@alpha-ob.example")
    b = await signup_workspace(company="Bravo Onboarding", email="founder@bravo-ob.example")
    async with session_scope(a.tenant_id) as session:
        await onboarding_service.skip(
            session,
            tenant_id=a.tenant_id,
            actor=Membership(a.membership_id),
            membership_id=a.membership_id,
            step_key="connect",
            reason="No systems to connect yet.",
        )
    return Two(a=a, b=b)


async def test_an_a_session_reads_only_a_rows(tenants: Two) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        owners = list((await session.execute(select(OnboardingStepSkip.tenant_id))).scalars())
    assert owners == [tenants.a.tenant_id]
    async with session_scope(tenants.b.tenant_id) as session:
        count = (
            await session.execute(select(func.count()).select_from(OnboardingStepSkip))
        ).scalar_one()
    assert count == 0


async def test_an_unbound_session_sees_nothing(tenants: Two) -> None:
    async with session_scope(None) as session:
        count = (
            await session.execute(select(func.count()).select_from(OnboardingStepSkip))
        ).scalar_one()
    assert count == 0


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(tenants: Two) -> None:
    async def forge() -> None:
        async with session_scope(tenants.a.tenant_id) as session:
            session.add(
                OnboardingStepSkip(
                    id=uuid7(),
                    tenant_id=tenants.b.tenant_id,
                    step_key="connect",
                    reason="Forged from the other workspace.",
                    skipped_by_membership_id=None,
                )
            )
            await session.flush()

    with pytest.raises(DBAPIError, match="row-level security"):
        await forge()


async def test_a_skip_in_one_workspace_leaves_the_other_open(tenants: Two) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        skips_a = await onboarding_service._open_skips(session, tenants.a.tenant_id)
    async with session_scope(tenants.b.tenant_id) as session:
        skips_b = await onboarding_service._open_skips(session, tenants.b.tenant_id)
    assert set(skips_a) == {"connect"}
    assert skips_b == {}
