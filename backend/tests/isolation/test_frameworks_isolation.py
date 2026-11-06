"""Tenant isolation for the frameworks a workspace runs and its Statement of Applicability.

The same properties as the other suites, over the two tables ISO 27001 support added:

1. An unfiltered read from tenant A's session returns only A's rows.
2. A session with no tenant bound sees nothing at all.
3. A write carrying B's ``tenant_id`` from an A-bound session is refused by the policy's
   ``WITH CHECK``.
4. A decision recorded in one workspace is invisible to the other, through the service.

Both tables are seeded through the real service, never by writing them directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import Conflict
from verity.db.base import Base
from verity.modules.audit.service import Membership
from verity.modules.compliance.framework_service import framework_service
from verity.modules.compliance.models import (
    Framework,
    FrameworkVersion,
    Requirement,
    RequirementApplicability,
    TenantFramework,
)
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

TENANT_TABLES: tuple[type[Base], ...] = (TenantFramework, RequirementApplicability)


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
    a = await signup_workspace(company="Alpha Frameworks", email="founder@alpha-fw.example")
    b = await signup_workspace(company="Bravo Frameworks", email="founder@bravo-fw.example")
    # Each workspace adds ISO 27001 and excludes a different requirement, so both tables hold
    # a row for both tenants.
    for workspace, code in ((a, "A.7.6"), (b, "A.7.12")):
        actor = Membership(workspace.membership_id)
        async with session_scope(workspace.tenant_id) as session:
            iso = (
                await session.execute(select(Framework).where(Framework.code == "ISO27001"))
            ).scalar_one()
            await framework_service.add(
                session, tenant_id=workspace.tenant_id, actor=actor, framework_id=iso.id
            )
            requirement = (
                await session.execute(
                    select(Requirement).where(
                        Requirement.framework_id == iso.id, Requirement.code == code
                    )
                )
            ).scalar_one()
            await framework_service.set_applicability(
                session,
                tenant_id=workspace.tenant_id,
                actor=actor,
                framework_id=iso.id,
                requirement_id=requirement.id,
                applicable=False,
                justification="No such area in a fully remote company.",
                provided_by="organization",
                owner_membership_id=None,
                reviewed=True,
            )
    return Two(a=a, b=b)


async def test_an_a_session_lists_only_a_rows_on_both_tables(tenants: Two) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        for model in TENANT_TABLES:
            owners = list((await session.execute(select(model.tenant_id))).scalars())  # type: ignore[attr-defined]
            assert owners, f"{model.__name__}: the seed should have written rows"
            assert set(owners) == {tenants.a.tenant_id}, model.__name__


async def test_an_unbound_session_sees_nothing_on_either_table(tenants: Two) -> None:
    async with session_scope(None) as session:
        for model in TENANT_TABLES:
            count = (await session.execute(select(func.count()).select_from(model))).scalar_one()
            assert count == 0, model.__name__


async def test_a_decision_in_one_workspace_never_shows_in_the_other(tenants: Two) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        iso = (
            await session.execute(select(Framework).where(Framework.code == "ISO27001"))
        ).scalar_one()
        statement = await framework_service.statement(
            session, tenant_id=tenants.a.tenant_id, framework_id=iso.id
        )
        excluded = [r.code for r in statement.rows if not r.applicable]
        assert excluded == ["A.7.6"]

    async with session_scope(tenants.b.tenant_id) as session:
        statement = await framework_service.statement(
            session, tenant_id=tenants.b.tenant_id, framework_id=iso.id
        )
        assert [r.code for r in statement.rows if not r.applicable] == ["A.7.12"]


async def test_a_workspace_that_never_added_a_framework_has_no_statement(tenants: Two) -> None:
    outsider = await signup_workspace(company="Charlie Frameworks", email="c@charlie-fw.example")
    async with session_scope(outsider.tenant_id) as session:
        iso = (
            await session.execute(select(Framework).where(Framework.code == "ISO27001"))
        ).scalar_one()
        with pytest.raises(Conflict):
            await framework_service.statement(
                session, tenant_id=outsider.tenant_id, framework_id=iso.id
            )


async def test_a_write_carrying_tenant_b_is_refused_by_with_check(tenants: Two) -> None:
    async with session_scope(tenants.a.tenant_id) as session:
        framework_id, version_id = (
            await session.execute(
                select(FrameworkVersion.framework_id, FrameworkVersion.id).where(
                    FrameworkVersion.is_current.is_(True)
                )
            )
        ).first() or (None, None)
        requirement_id = (await session.execute(select(Requirement.id))).scalars().first()
    b_tenant = tenants.b.tenant_id
    forgeries: tuple[Base, ...] = (
        TenantFramework(
            id=uuid7(),
            tenant_id=b_tenant,
            framework_id=framework_id,
            framework_version_id=version_id,
        ),
        RequirementApplicability(
            id=uuid7(), tenant_id=b_tenant, requirement_id=requirement_id, applicable=True
        ),
    )

    async def forge(instance: Base) -> None:
        async with session_scope(tenants.a.tenant_id) as session:
            session.add(instance)
            await session.flush()

    for instance in forgeries:
        with pytest.raises(DBAPIError, match="row-level security"):
            await forge(instance)
