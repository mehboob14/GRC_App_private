"""Tenant isolation for scope items and per framework scope decisions."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.modules.audit.service import Membership
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.models import (
    Framework,
    FrameworkVersion,
    ScopeDecision,
    ScopeItem,
)
from verity.modules.compliance.scope_service import scope_service
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


async def _with_scope(company: str, email: str) -> Workspace:
    workspace = await signup_workspace(company=company, email=email)
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        version_id = (
            await session.execute(
                select(FrameworkVersion.id)
                .join(Framework, Framework.id == FrameworkVersion.framework_id)
                .where(Framework.code == "SOC2", FrameworkVersion.is_current.is_(True))
            )
        ).scalar_one()
        await engagement_service.upsert(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            name="SOC 2",
            framework_version_id=version_id,
            audit_type="type_1",
            categories_in_scope=[],
        )
        item = await scope_service.add_item(
            session, tenant_id=workspace.tenant_id, actor=actor, kind="system", name="Core API"
        )
        await scope_service.decide(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            membership_id=workspace.membership_id,
            item_id=item.id,
            framework_code="SOC2",
            in_scope=True,
            reason=None,
        )
    return workspace


async def test_each_workspace_reads_only_its_own_scope() -> None:
    a = await _with_scope("Alpha Scope", "founder@alpha-scope.example")
    b = await _with_scope("Bravo Scope", "founder@bravo-scope.example")
    for workspace in (a, b):
        async with session_scope(workspace.tenant_id) as session:
            for model in (ScopeItem, ScopeDecision):
                owners = set((await session.execute(select(model.tenant_id))).scalars())
                assert owners == {workspace.tenant_id}, model.__name__
    async with session_scope(None) as session:
        for model in (ScopeItem, ScopeDecision):
            count = (await session.execute(select(func.count()).select_from(model))).scalar_one()
            assert count == 0, model.__name__


async def test_a_scope_item_for_another_tenant_is_refused() -> None:
    a = await _with_scope("Alpha Forge Scope", "founder@alpha-fs.example")
    b = await signup_workspace(company="Bravo Forge Scope", email="founder@bravo-fs.example")

    async def forge() -> None:
        async with session_scope(a.tenant_id) as session:
            session.add(ScopeItem(id=uuid7(), tenant_id=b.tenant_id, kind="site", name="Forged"))
            await session.flush()

    with pytest.raises(DBAPIError, match="row-level security"):
        await forge()
