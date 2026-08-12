"""Seeding and token helpers for the tenancy suites.

Everything here goes through the real entry points — ``provider_session_scope``, the
repositories, ``core.security`` — as the application role. Nothing bypasses RLS and
nothing writes a table directly.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import pyotp

from verity.core.crypto import get_secret_box
from verity.core.db import provider_session_scope
from verity.core.security import hash_password, issue_token, new_totp_secret
from verity.modules.tenancy.models import PlatformAdmin, Tenant
from verity.modules.tenancy.repository import PlatformAdminRepository
from verity.modules.tenancy.schemas import TenantRegistration
from verity.modules.tenancy.service import tenancy_service
from verity.shared.ids import uuid7

ADMIN_PASSWORD = "correct-horse-battery-staple"  # noqa: S105 — test credential


@dataclass(frozen=True, slots=True)
class SeededAdmin:
    id: uuid.UUID
    email: str
    role: str
    totp_secret: str | None


async def seed_admin(
    *,
    email: str = "ops@example.com",
    role: str = "onboarding",
    status: str = "active",
    enrolled: bool = True,
    password: str = ADMIN_PASSWORD,
) -> SeededAdmin:
    """One platform admin, committed, optionally with TOTP already enrolled."""
    admin = PlatformAdmin(
        # Assigned here, not left to the column default: the default applies at
        # flush, and the AAD below must name the id the row will actually have.
        id=uuid7(),
        email=email,
        full_name="Test Operator",
        role=role,
        status=status,
        mfa_enabled=enrolled,
        password_hash=hash_password(password),
    )
    secret: str | None = None
    if enrolled:
        secret = new_totp_secret()
        admin.mfa_secret_encrypted = get_secret_box().encrypt(
            secret, aad=f"platform_admin:{admin.id}"
        )
    async with provider_session_scope() as session:
        await PlatformAdminRepository().add(session, admin)
    return SeededAdmin(id=admin.id, email=email, role=role, totp_secret=secret)


def provider_session_headers(admin_id: uuid.UUID) -> dict[str, str]:
    """A real provider-plane session token, minted directly.

    The full login flow is proven in the auth suite; the other suites only need an
    authenticated caller, and the dependency validates this token against the
    database exactly as it would one from ``/mfa/verify``.
    """
    issued = issue_token(subject=admin_id, plane="provider", typ="session")
    return {"Authorization": f"Bearer {issued.token}"}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def totp_code(secret: str, *, step_offset: int = 0) -> str:
    """The TOTP code for now, or a neighbouring window when ``step_offset`` is set."""
    return str(pyotp.TOTP(secret).at(int(time.time()) + 30 * step_offset))


def registration_payload(slug: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "legal_name": f"{slug.title()} Pty Ltd",
        "slug": slug,
        "plan": "starter",
        "country": "AU",
        "primary_contact_email": f"admin@{slug}.example",
    }
    body.update(overrides)
    return body


async def register_tenant_directly(
    actor_admin_id: uuid.UUID, slug: str, **overrides: object
) -> Tenant:
    """Register through the real service on a provider-plane unit of work."""
    profile = TenantRegistration.model_validate(registration_payload(slug, **overrides))
    async with provider_session_scope() as session:
        return await tenancy_service.register_tenant(
            session, actor_admin_id=actor_admin_id, profile=profile
        )
