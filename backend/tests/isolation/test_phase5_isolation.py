"""Tenant isolation for the guided onboarding phase 5 and 6 tables.

Rows are written through the real services in workspace A. A session for B, and a session with
no tenant bound, see none of them; a write carrying B's ``tenant_id`` from an A session is refused.
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
from verity.modules.compliance.control_service import control_service
from verity.modules.objectives.models import ObjectiveDecision
from verity.modules.objectives.service import objectives_service
from verity.modules.onboarding.models import (
    Baseline,
    BaselineAnswer,
    OnboardingState,
    ProposalDecision,
    ReadinessSnapshot,
)
from verity.modules.onboarding.plan_service import plan_service
from verity.modules.onboarding.proposals_service import proposals_service
from verity.modules.regulations.models import RegulationDecision
from verity.modules.regulations.service import regulations_service
from verity.modules.tenancy.schemas import CompanyProfileUpdate
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TABLES = (
    ProposalDecision,
    Baseline,
    BaselineAnswer,
    ReadinessSnapshot,
    OnboardingState,
    RegulationDecision,
    ObjectiveDecision,
)


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
    a = await signup_workspace(company="Alpha Plan", email="founder@alpha-plan.example")
    b = await signup_workspace(company="Bravo Plan", email="founder@bravo-plan.example")
    actor = Membership(a.membership_id)
    async with session_scope(a.tenant_id) as session:
        await tenancy_service.update_own_company_profile(
            session,
            tenant_id=a.tenant_id,
            actor_membership_id=a.membership_id,
            changes=CompanyProfileUpdate(answers={"offices": "none"}),
        )
    async with session_scope(a.tenant_id) as session:
        await proposals_service.decide(
            session,
            tenant_id=a.tenant_id,
            actor=actor,
            membership_id=a.membership_id,
            keys=["no_offices.controls:PE-02"],
            accept=True,
            reason=None,
        )
        control = (await control_service.states_by_code(session, tenant_id=a.tenant_id))["IAM-01"]
        await plan_service.answer(
            session,
            tenant_id=a.tenant_id,
            actor=actor,
            membership_id=a.membership_id,
            control_id=control[0],
            answer="in_place",
            note=None,
        )
        await plan_service.complete(session, tenant_id=a.tenant_id, actor=actor)
        await regulations_service.decide(
            session,
            tenant_id=a.tenant_id,
            actor=actor,
            membership_id=a.membership_id,
            key="SA-01",
            relevance="relevant",
            note=None,
        )
        await objectives_service.mark_not_applicable(
            session,
            tenant_id=a.tenant_id,
            actor=actor,
            membership_id=a.membership_id,
            objective_code="PE-01.E",
            reason="No physical media held.",
        )
        await plan_service.save_setup(
            session,
            tenant_id=a.tenant_id,
            actor=actor,
            start_point="fresh",
            setup_step="start",
            complete=False,
        )
    return Two(a=a, b=b)


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.__tablename__)
async def test_only_the_owning_tenant_reads_its_rows(tenants: Two, table: type) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        owners = set((await session.execute(select(table.tenant_id))).scalars())  # type: ignore[attr-defined]
    assert owners == {tenants.a.tenant_id}
    for scope in (tenants.b.tenant_id, None):
        async with session_scope(scope) as session:
            count = (await session.execute(select(func.count()).select_from(table))).scalar_one()
        assert count == 0


async def test_a_forged_tenant_is_refused(tenants: Two) -> None:
    async def forge() -> None:
        async with session_scope(tenants.a.tenant_id) as session:
            session.add(OnboardingState(id=uuid7(), tenant_id=tenants.b.tenant_id))
            await session.flush()

    with pytest.raises(DBAPIError, match="row-level security"):
        await forge()
