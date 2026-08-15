"""Data access for the provider plane. No business rules, no commits.

Every method runs on the caller's session; the transaction boundary belongs to
``core.db`` (backend/CLAUDE.md). These tables are provider-plane, so there is no
``tenant_id`` filter to apply — visibility is bounded by the RLS policies keyed on
``app.provider_plane`` and, for the tenant-readable tables, ``app.tenant_id``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.tenancy.models import (
    PROVISIONING_STEPS,
    CompanyProfile,
    PlatformAdmin,
    Tenant,
    TenantBranding,
    TenantProvisioningStep,
    TenantRegistrationKey,
    TenantSmtp,
)

_STEP_ORDER = {step: position for position, step in enumerate(PROVISIONING_STEPS)}


class CompanyProfileRepository:
    """The tenant's own organisation profile. Tenant-owned: RLS bounds every
    query to the acting tenant, so there is no tenant_id filter to apply here."""

    async def get(self, session: AsyncSession, tenant_id: uuid.UUID) -> CompanyProfile | None:
        return await session.get(CompanyProfile, tenant_id)

    async def add(self, session: AsyncSession, profile: CompanyProfile) -> None:
        session.add(profile)
        await session.flush([profile])


class TenantSmtpRepository:
    """The tenant's own SMTP config. Tenant-owned: RLS bounds every query to the
    acting tenant, so there is no tenant_id filter to apply here."""

    async def get(self, session: AsyncSession, tenant_id: uuid.UUID) -> TenantSmtp | None:
        return await session.get(TenantSmtp, tenant_id)

    async def add(self, session: AsyncSession, smtp: TenantSmtp) -> None:
        session.add(smtp)
        await session.flush([smtp])


class PlatformAdminRepository:
    async def add(self, session: AsyncSession, admin: PlatformAdmin) -> None:
        session.add(admin)
        await session.flush([admin])

    async def get(self, session: AsyncSession, admin_id: uuid.UUID) -> PlatformAdmin | None:
        return await session.get(PlatformAdmin, admin_id)

    async def get_for_update(
        self, session: AsyncSession, admin_id: uuid.UUID
    ) -> PlatformAdmin | None:
        """Like :meth:`get`, but takes a row lock (SELECT ... FOR UPDATE).

        The MFA verify path reads ``last_totp_counter`` / ``recovery_codes_encrypted``,
        then writes the advanced counter or the consumed recovery list. Locking the row
        first serializes that guard-then-update, so a second concurrent submission of a
        captured code blocks, re-reads the advanced counter, and refuses the replay."""
        result = await session.execute(
            select(PlatformAdmin).where(PlatformAdmin.id == admin_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, session: AsyncSession, email: str) -> PlatformAdmin | None:
        result = await session.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
        return result.scalar_one_or_none()

    async def count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(PlatformAdmin))
        return result.scalar_one()


class TenantRepository:
    async def add(self, session: AsyncSession, tenant: Tenant) -> None:
        session.add(tenant)
        await session.flush([tenant])

    async def get(self, session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
        return await session.get(Tenant, tenant_id)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> Tenant | None:
        result = await session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def list_page(
        self,
        session: AsyncSession,
        *,
        limit: int,
        before_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Tenant]:
        """Newest first, keyed on the UUIDv7 ``id`` — time-ordered by construction.

        Keyset rather than offset (docs/conventions/api.md): tenants registered while
        a client pages must not shift or repeat what it sees.
        """
        statement = select(Tenant).order_by(Tenant.id.desc()).limit(limit)
        if before_id is not None:
            statement = statement.where(Tenant.id < before_id)
        if status is not None:
            statement = statement.where(Tenant.status == status)
        result = await session.execute(statement)
        return list(result.scalars())

    async def add_branding(self, session: AsyncSession, branding: TenantBranding) -> None:
        session.add(branding)
        await session.flush([branding])

    async def get_branding(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> TenantBranding | None:
        return await session.get(TenantBranding, tenant_id)

    async def add_step(self, session: AsyncSession, step: TenantProvisioningStep) -> None:
        session.add(step)
        await session.flush([step])

    async def get_steps(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[TenantProvisioningStep]:
        """The tenant's steps in canonical order, not insertion order."""
        result = await session.execute(
            select(TenantProvisioningStep).where(TenantProvisioningStep.tenant_id == tenant_id)
        )
        steps = list(result.scalars())
        steps.sort(key=lambda step: _STEP_ORDER.get(step.step, len(_STEP_ORDER)))
        return steps

    async def get_registration_key(
        self, session: AsyncSession, *, platform_admin_id: uuid.UUID | None, idempotency_key: str
    ) -> TenantRegistrationKey | None:
        """``platform_admin_id=None`` addresses the self-service population, whose
        keys are deduplicated by the partial unique index rather than the pair."""
        admin_predicate = (
            TenantRegistrationKey.platform_admin_id.is_(None)
            if platform_admin_id is None
            else TenantRegistrationKey.platform_admin_id == platform_admin_id
        )
        result = await session.execute(
            select(TenantRegistrationKey).where(
                admin_predicate,
                TenantRegistrationKey.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def add_registration_key(
        self, session: AsyncSession, record: TenantRegistrationKey
    ) -> None:
        session.add(record)
        await session.flush([record])
