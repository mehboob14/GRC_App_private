"""Tenant isolation for the risk register.

The same four properties as the vendor suite, over the six risk tables:

1. An unfiltered read from tenant A's session returns only A's rows.
2. A B row is absent by id, and the service raises ``NotFound`` for it.
3. A session with no tenant bound sees nothing at all.
4. A write carrying B's ``tenant_id`` from an A-bound session is refused by the
   policy's ``WITH CHECK``, including the mixed pair (acceptance in B's stream
   pointing at A's risk) the denormalised ``tenant_id`` exists to catch.

Every table is seeded through the real service, never by writing it directly.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import INVITEE_PASSWORD, Workspace, invite_directly, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import NotFound
from verity.db.base import Base
from verity.modules.audit.service import Membership
from verity.modules.compliance.control_service import control_service
from verity.modules.iam.service import iam_auth_service
from verity.modules.risk.models import (
    Risk,
    RiskAcceptance,
    RiskCategory,
    RiskControlMap,
    RiskEvent,
    RiskRegister,
)
from verity.modules.risk.service import RiskFilters, RiskInput, risk_service
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TENANT_TABLES: tuple[type[Base], ...] = (
    RiskRegister,
    RiskCategory,
    Risk,
    RiskControlMap,
    RiskAcceptance,
    RiskEvent,
)


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Seeded:
    workspace: Workspace
    register_id: uuid.UUID
    risk_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TwoTenants:
    a: Seeded
    b: Seeded


async def _populate(workspace: Workspace, domain: str) -> Seeded:
    """A register, a risk with a control and a pending acceptance: a row on every
    risk table."""
    invited = await invite_directly(
        workspace, email=f"approver@{domain}", full_name="Avery Stone", role_name="Admin"
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Avery Stone", password=INVITEE_PASSWORD
    )
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        registers = await risk_service.list_registers(session, tenant_id=workspace.tenant_id)
        register = registers[0]
        category = next(c for c in register.categories if c.name == "Technology")
        risk = await risk_service.create_risk(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            data=RiskInput(
                register_id=register.id,
                title="Unauthorised access",
                category_id=category.id,
                inherent_likelihood=3,
                inherent_impact=4,
            ),
        )
        controls = await control_service.list_controls(session, tenant_id=workspace.tenant_id)
        assert controls, "signup should have adopted the control library"
        await risk_service.link_controls(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            risk_id=risk.id,
            control_ids=[controls[0].id],
        )
        await risk_service.request_acceptance(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            risk_id=risk.id,
            approver_membership_id=invited.member.membership_id,
            rationale="Compensating monitoring in place.",
            expires_on=datetime.now(UTC).date() + timedelta(days=60),
        )
    return Seeded(workspace=workspace, register_id=register.id, risk_id=risk.id)


@pytest.fixture
async def tenants() -> TwoTenants:
    a = await signup_workspace(company="Alpha Compliance", email="founder@alpha.example")
    b = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    return TwoTenants(a=await _populate(a, "alpha.example"), b=await _populate(b, "bravo.example"))


async def test_an_a_session_lists_only_a_rows_on_every_risk_table(tenants: TwoTenants) -> None:
    """No WHERE clause anywhere: the policy, not the query, bounds every row set."""
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        for model in TENANT_TABLES:
            owners = list((await session.execute(select(model.tenant_id))).scalars())  # type: ignore[attr-defined]
            assert owners, f"{model.__name__}: the seed should have written rows"
            assert set(owners) == {tenants.a.workspace.tenant_id}, model.__name__


async def test_the_register_and_refs_never_cross_the_boundary(tenants: TwoTenants) -> None:
    """Both tenants have a risk with the same title; neither sees the other's."""
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        items, total = await risk_service.list_risks(
            session,
            tenant_id=tenants.a.workspace.tenant_id,
            filters=RiskFilters(register_id=tenants.a.register_id),
        )
        assert (total, [r.id for r in items]) == (1, [tenants.a.risk_id])
        refs = await risk_service.refs(
            session, tenant_id=tenants.a.workspace.tenant_id, search="Unauthorised"
        )
        assert [r.id for r in refs] == [tenants.a.risk_id]


async def test_a_b_row_reads_as_absent_by_id_not_forbidden(tenants: TwoTenants) -> None:
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        assert await session.get(Risk, tenants.b.risk_id) is None
        assert await session.get(RiskRegister, tenants.b.register_id) is None

    async with session_scope(tenants.a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await risk_service.get_risk(
                session, tenant_id=tenants.a.workspace.tenant_id, risk_id=tenants.b.risk_id
            )

    async with session_scope(tenants.a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await risk_service.list_risks(
                session,
                tenant_id=tenants.a.workspace.tenant_id,
                filters=RiskFilters(register_id=tenants.b.register_id),
            )


async def test_an_unbound_session_sees_nothing_on_any_risk_table(tenants: TwoTenants) -> None:
    async with session_scope(None) as session:
        for model in TENANT_TABLES:
            count = (await session.execute(select(func.count()).select_from(model))).scalar_one()
            assert count == 0, model.__name__


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(tenants: TwoTenants) -> None:
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        category_id = (
            (
                await session.execute(
                    select(RiskCategory.id).where(RiskCategory.register_id == tenants.a.register_id)
                )
            )
            .scalars()
            .first()
        )
    b_tenant = tenants.b.workspace.tenant_id
    forgeries: tuple[Base, ...] = (
        RiskRegister(id=uuid7(), tenant_id=b_tenant, name="Forged"),
        RiskCategory(id=uuid7(), tenant_id=b_tenant, register_id=tenants.a.register_id, name="X"),
        Risk(
            id=uuid7(),
            tenant_id=b_tenant,
            register_id=tenants.a.register_id,
            code="RSK-9999",
            title="Forged",
            category_id=category_id,
        ),
        RiskAcceptance(
            id=uuid7(),
            tenant_id=b_tenant,
            risk_id=tenants.a.risk_id,
            rationale="Forged",
            expires_on=datetime.now(UTC).date() + timedelta(days=5),
        ),
        RiskEvent(id=uuid7(), tenant_id=b_tenant, risk_id=tenants.a.risk_id, kind="updated"),
    )

    async def forge(instance: Base) -> None:
        async with session_scope(tenants.a.workspace.tenant_id) as session:
            session.add(instance)
            await session.flush()

    for instance in forgeries:
        with pytest.raises(DBAPIError, match="row-level security"):
            await forge(instance)
