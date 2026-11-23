"""Tenant isolation for frozen company profile versions (guided onboarding phase 2)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, signup_workspace
from tests.unit.test_profile_questions import FULL_CORE
from verity.core.db import dispose_engine, session_scope
from verity.modules.tenancy.models import CompanyProfileVersion
from verity.modules.tenancy.schemas import CompanyProfileUpdate
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.isolation, pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


async def _confirmed(company: str, email: str) -> Workspace:
    workspace = await signup_workspace(company=company, email=email)
    async with session_scope(workspace.tenant_id) as session:
        await tenancy_service.update_own_company_profile(
            session,
            tenant_id=workspace.tenant_id,
            actor_membership_id=workspace.membership_id,
            changes=CompanyProfileUpdate(answers=FULL_CORE),
        )
        await tenancy_service.confirm_own_company_profile(
            session, tenant_id=workspace.tenant_id, actor_membership_id=workspace.membership_id
        )
    return workspace


async def test_each_workspace_reads_only_its_own_versions() -> None:
    a = await _confirmed("Alpha Profile", "founder@alpha-pv.example")
    b = await signup_workspace(company="Bravo Profile", email="founder@bravo-pv.example")
    async with session_scope(a.tenant_id) as session:
        owners = list((await session.execute(select(CompanyProfileVersion.tenant_id))).scalars())
    assert owners == [a.tenant_id]
    async with session_scope(b.tenant_id) as session:
        assert await tenancy_service.list_company_profile_versions(session, b.tenant_id) == []
    async with session_scope(None) as session:
        count = (
            await session.execute(select(func.count()).select_from(CompanyProfileVersion))
        ).scalar_one()
    assert count == 0


async def test_a_version_carrying_another_tenant_is_refused() -> None:
    a = await _confirmed("Alpha Forge", "founder@alpha-pf.example")
    b = await signup_workspace(company="Bravo Forge", email="founder@bravo-pf.example")

    async def forge() -> None:
        async with session_scope(a.tenant_id) as session:
            session.add(
                CompanyProfileVersion(
                    id=uuid7(),
                    tenant_id=b.tenant_id,
                    version=1,
                    answers={},
                    details={},
                    confirmed_at=datetime.now(UTC),
                )
            )
            await session.flush()

    with pytest.raises(DBAPIError, match="row-level security"):
        await forge()
