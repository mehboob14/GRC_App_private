"""Tenancy isolation: the provider plane's tables against tenant-bound sessions.

Everything goes through the real entry points — ``session_scope`` /
``provider_session_scope``, the tenancy service and repositories — as the
application role, against the migrated tables with their policies. The unfiltered
raw queries are deliberate: RLS has to hold when the application filter is absent.

The approved policy shape (add-provider-plane/design.md):

    platform_admins           tenant plane: invisible          provider: full
    tenants                   tenant plane: SELECT own row     provider: full
    tenant_branding           tenant plane: SELECT own row     provider: full
    tenant_provisioning       tenant plane: SELECT own rows    provider: full
    tenant_registration_keys  tenant plane: invisible          provider: full

The tenant plane gets SELECT only, everywhere: a tenant changing its own plan is a
business-logic hole the database itself closes.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.tenancy import (
    ADMIN_PASSWORD,
    registration_payload,
    seed_admin,
)
from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.core.deps import get_current_platform_admin
from verity.core.errors import AuthenticationRequired
from verity.core.security import decode_token
from verity.db.base import Base
from verity.modules.tenancy.models import (
    PlatformAdmin,
    Tenant,
    TenantBranding,
    TenantProvisioningStep,
    TenantRegistrationKey,
)
from verity.modules.tenancy.schemas import TenantRegistration
from verity.modules.tenancy.service import provider_auth_service, tenancy_service

pytestmark = [pytest.mark.isolation, pytest.mark.integration]

ALL_TABLES = (PlatformAdmin, Tenant, TenantBranding, TenantProvisioningStep, TenantRegistrationKey)


@pytest.fixture(autouse=True)
async def _fresh_state(clean_tenancy: None, clean_audit_log: None) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Seeded:
    admin_id: uuid.UUID
    tenant_a: uuid.UUID
    tenant_b: uuid.UUID


@pytest.fixture
async def seeded() -> Seeded:
    """One platform admin and two tenants, registered through the real service —
    each with its branding row, its four provisioning steps, and (for A) an
    idempotency record."""
    admin = await seed_admin()
    async with provider_session_scope() as session:
        tenant_a = await tenancy_service.register_tenant(
            session,
            actor_admin_id=admin.id,
            profile=TenantRegistration.model_validate(registration_payload("tenant-a")),
            idempotency_key="seed-a",
        )
        tenant_b = await tenancy_service.register_tenant(
            session,
            actor_admin_id=admin.id,
            profile=TenantRegistration.model_validate(registration_payload("tenant-b")),
        )
    return Seeded(admin_id=admin.id, tenant_a=tenant_a.id, tenant_b=tenant_b.id)


async def _count(session: AsyncSession, model: type[Base]) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_a_tenant_session_sees_only_its_own_rows(seeded: Seeded) -> None:
    """No WHERE clause anywhere: the policy, not the query, bounds every row set."""
    async with session_scope(seeded.tenant_a) as session:
        tenants = (await session.execute(select(Tenant))).scalars().all()
        assert [t.id for t in tenants] == [seeded.tenant_a]

        branding = (await session.execute(select(TenantBranding))).scalars().all()
        assert [b.tenant_id for b in branding] == [seeded.tenant_a]

        steps = (await session.execute(select(TenantProvisioningStep))).scalars().all()
        assert len(steps) == 4
        assert {step.tenant_id for step in steps} == {seeded.tenant_a}


async def test_a_tenant_session_sees_no_platform_admin_and_no_registration_keys(
    seeded: Seeded,
) -> None:
    async with session_scope(seeded.tenant_a) as session:
        assert await _count(session, PlatformAdmin) == 0
        assert await _count(session, TenantRegistrationKey) == 0


async def test_another_tenants_row_is_absent_by_id_not_forbidden(seeded: Seeded) -> None:
    """404-not-403 at the API is this database fact: the row simply is not there."""
    async with session_scope(seeded.tenant_a) as session:
        assert await session.get(Tenant, seeded.tenant_b) is None
        assert await session.get(TenantBranding, seeded.tenant_b) is None


async def test_an_unbound_session_sees_nothing_on_any_of_the_five_tables(
    seeded: Seeded,
) -> None:
    """Fail closed: no tenant bound, not provider plane — zero rows, no error."""
    async with session_scope(None) as session:
        for model in ALL_TABLES:
            assert await _count(session, model) == 0, model.__name__


async def test_a_tenant_session_cannot_insert_into_any_provider_table(
    seeded: Seeded,
) -> None:
    """There is no tenant INSERT policy, so every insert is refused outright —
    including a branding row forged for the tenant's own id."""
    attempts = (
        PlatformAdmin(
            email="mole@evil.example",
            full_name="Mole",
            role="super_admin",
            status="active",
            password_hash="x",  # noqa: S106 — never stored; the insert is refused
        ),
        Tenant(legal_name="Forged", slug="forged", plan="starter", status="active"),
        TenantBranding(tenant_id=seeded.tenant_a),
        TenantProvisioningStep(tenant_id=seeded.tenant_b, step="verify", status="pending"),
    )

    async def forge(instance: Base) -> None:
        async with session_scope(seeded.tenant_a) as session:
            session.add(instance)
            await session.flush()

    for instance in attempts:
        with pytest.raises(DBAPIError, match="row-level security"):
            await forge(instance)


async def test_a_tenant_session_cannot_update_or_delete_even_its_own_rows(
    seeded: Seeded,
) -> None:
    """SELECT-only means UPDATE and DELETE match nothing — a tenant cannot change
    its own plan, status, branding, or provisioning, let alone another tenant's."""
    async with session_scope(seeded.tenant_a) as session:
        writes = (
            update(Tenant).where(Tenant.id == seeded.tenant_a).values(plan="enterprise"),
            update(Tenant).where(Tenant.id == seeded.tenant_a).values(status="active"),
            update(TenantBranding)
            .where(TenantBranding.tenant_id == seeded.tenant_a)
            .values(custom_domain="owned.example"),
            update(TenantProvisioningStep)
            .where(TenantProvisioningStep.tenant_id == seeded.tenant_a)
            .values(status="done", completed_at=func.now()),
            delete(Tenant).where(Tenant.id == seeded.tenant_a),
        )
        for statement in writes:
            result = cast("CursorResult[Any]", await session.execute(statement))
            assert result.rowcount == 0, statement

    # And nothing changed, observed from the plane that sees everything.
    async with provider_session_scope() as session:
        tenant = await session.get(Tenant, seeded.tenant_a)
        assert tenant is not None
        assert tenant.plan == "starter"
        assert tenant.status == "provisioning"


async def test_the_provider_plane_sees_and_reaches_everything(seeded: Seeded) -> None:
    async with provider_session_scope() as session:
        assert await _count(session, PlatformAdmin) == 1
        assert await _count(session, Tenant) == 2
        assert await _count(session, TenantBranding) == 2
        assert await _count(session, TenantProvisioningStep) == 8
        assert await _count(session, TenantRegistrationKey) == 1


async def test_login_is_impossible_without_a_valid_totp_code(seeded: Seeded) -> None:
    """Task 6.4: a correct password buys a challenge, and the challenge opens no
    session-consuming dependency — there is no path around the second factor."""
    admin = await seed_admin(email="mfa-check@example.com")
    challenge = await provider_auth_service.login(email=admin.email, password=ADMIN_PASSWORD)
    assert challenge.next_step == "mfa_verify"

    # The challenge is not a session: the session decoder refuses it, so
    # get_current_platform_admin (which every provider route depends on) refuses it.
    with pytest.raises(AuthenticationRequired):
        decode_token(challenge.challenge_token, expected_typ="session")

    # A wrong code converts the challenge into nothing.
    with pytest.raises(AuthenticationRequired):
        await provider_auth_service.verify_mfa(
            challenge_token=challenge.challenge_token, code="000000"
        )


async def test_the_provider_dependency_refuses_unauthenticated_callers(
    seeded: Seeded,
) -> None:
    with pytest.raises(AuthenticationRequired):
        await get_current_platform_admin(credentials=None)
