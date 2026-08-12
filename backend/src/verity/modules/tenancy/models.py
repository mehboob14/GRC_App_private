"""The provider plane's tables: operators, the tenants register, branding, provisioning.

Columns follow openspec/changes/add-provider-plane/design.md, which itself follows the
ER Design document §3.1, as amended by openspec/changes/week1-review-decisions.md:

- decision 5: platform-admin credentials live on ``platform_admins`` (``password_hash``,
  ``mfa_secret_encrypted``, ``recovery_codes_encrypted``) — no separate table. The two
  encrypted columns hold application-layer output only: the MFA secret is envelope
  ciphertext AAD-bound to ``platform_admin:<id>``, the recovery codes are argon2id
  hashes of single-use codes. Plaintext never reaches these columns.
- decision 6: ``tenant_branding`` and ``tenant_provisioning`` keep their ``tenant_id``
  per the ER *and* get RLS policies; only ``platform_admins`` and ``tenants`` genuinely
  carry no ``tenant_id``.
- decision 7: ``tenants.created_by`` is nullable — self-service signup has no admin.
- decision 8: provisioning has no ``failed`` status; a failing step stays ``pending``.

``last_totp_counter`` is not in the change's table listing; it is the same replay
protection week1-review-decisions.md item 11 approved as ``credentials.last_totp_counter``
for tenant users, applied to the parallel population. ``core.security.verify_totp``
refuses any code at or before the stored counter, which is what closes the ~90-second
replay window a bare TOTP check leaves open.

``tenant_registration_keys`` is the idempotency record design.md's "what happens if this
runs twice?" section requires: the key, the platform admin, and a hash of the request
body, recorded with the resulting tenant id.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Final

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)

PLATFORM_ADMIN_ROLES: Final[tuple[str, ...]] = ("super_admin", "onboarding", "support")
PLATFORM_ADMIN_STATUSES: Final[tuple[str, ...]] = ("active", "disabled")
PLATFORM_ADMIN_STATUS_ACTIVE: Final = "active"

TENANT_STATUSES: Final[tuple[str, ...]] = ("provisioning", "active", "suspended", "terminated")
TENANT_STATUS_PROVISIONING: Final = "provisioning"
TENANT_STATUS_ACTIVE: Final = "active"

PROVISIONING_STEPS: Final[tuple[str, ...]] = (
    "create_tenant",
    "seed_content",
    "invite_admin",
    "verify",
)
PROVISIONING_STATUSES: Final[tuple[str, ...]] = ("pending", "done")
PROVISIONING_STATUS_PENDING: Final = "pending"
PROVISIONING_STATUS_DONE: Final = "done"

STEP_CREATE_TENANT: Final = "create_tenant"
STEP_SEED_CONTENT: Final = "seed_content"
STEP_INVITE_ADMIN: Final = "invite_admin"
STEP_VERIFY: Final = "verify"


class PlatformAdmin(UUIDPrimaryKey, Timestamped, Base):
    """An operator. A separate population from tenant users, never a membership."""

    __tablename__ = "platform_admins"

    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str]
    role: Mapped[str]
    mfa_enabled: Mapped[bool] = mapped_column(server_default=text("false"), default=False)
    status: Mapped[str]
    password_hash: Mapped[str]
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(default=None)
    recovery_codes_encrypted: Mapped[list[str] | None] = mapped_column(JSONB(), default=None)
    last_totp_counter: Mapped[int | None] = mapped_column(BigInteger, default=None)

    __table_args__ = (
        status_check("platform_admins", "role", PLATFORM_ADMIN_ROLES),
        status_check("platform_admins", "status", PLATFORM_ADMIN_STATUSES),
    )

    def __repr__(self) -> str:
        # Deliberately no credential columns: this string ends up in tracebacks.
        return f"PlatformAdmin(id={self.id!r}, role={self.role!r}, status={self.status!r})"


class Tenant(UUIDPrimaryKey, Timestamped, Base):
    """One customer company. The root object every tenant-owned row hangs off.

    The profile captured at registration — legal name, registered address — is what
    generated documents carry later, which is why it lives here and not in a settings
    blob. Only ``legal_name``, ``slug``, ``plan``, and ``status`` are required; a trial
    signup will not have a registration number to hand.
    """

    __tablename__ = "tenants"

    legal_name: Mapped[str]
    trading_name: Mapped[str | None] = mapped_column(default=None)
    slug: Mapped[str] = mapped_column(unique=True)
    industry: Mapped[str | None] = mapped_column(default=None)
    registration_number: Mapped[str | None] = mapped_column(default=None)
    address_line1: Mapped[str | None] = mapped_column(default=None)
    address_line2: Mapped[str | None] = mapped_column(default=None)
    city: Mapped[str | None] = mapped_column(default=None)
    state_region: Mapped[str | None] = mapped_column(default=None)
    postal_code: Mapped[str | None] = mapped_column(default=None)
    country: Mapped[str | None] = mapped_column(default=None)
    primary_contact_name: Mapped[str | None] = mapped_column(default=None)
    primary_contact_email: Mapped[str | None] = mapped_column(default=None)
    primary_contact_phone: Mapped[str | None] = mapped_column(default=None)
    plan: Mapped[str]
    status: Mapped[str]
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_admins.id"), default=None
    )
    onboarded_at: Mapped[date | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("tenants", "status", TENANT_STATUSES),
        # The provider register's default filter. No tenant_id exists on this table,
        # so a single-column index is not an exception to the leading-tenant_id rule.
        Index("ix_tenants__status", "status"),
    )

    def __repr__(self) -> str:
        return f"Tenant(id={self.id!r}, slug={self.slug!r}, status={self.status!r})"


class TenantBranding(Timestamped, Base):
    """One branding record per tenant, created empty at registration.

    ``smtp_config_ref`` holds application-layer ciphertext only — envelope-encrypted
    AAD-bound to ``tenant_branding:<tenant_id>`` before insert, excluded from every
    response and both audit snapshots. The primary key *is* the tenant, per the ER.
    """

    __tablename__ = "tenant_branding"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    logo_ref: Mapped[str | None] = mapped_column(default=None)
    primary_color: Mapped[str | None] = mapped_column(default=None)
    secondary_color: Mapped[str | None] = mapped_column(default=None)
    custom_domain: Mapped[str | None] = mapped_column(default=None)
    email_from_name: Mapped[str | None] = mapped_column(default=None)
    email_from_address: Mapped[str | None] = mapped_column(default=None)
    smtp_config_ref: Mapped[str | None] = mapped_column(default=None)
    document_footer: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        # Partial: many tenants have no custom domain, and NULLs must not collide.
        Index(
            "uq_tenant_branding__custom_domain",
            "custom_domain",
            unique=True,
            postgresql_where=text("custom_domain IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        # Deliberately no smtp_config_ref, even though it is ciphertext.
        return f"TenantBranding(tenant_id={self.tenant_id!r})"


class TenantProvisioningStep(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One provisioning step for one tenant.

    ``UNIQUE (tenant_id, step)`` is what makes provisioning idempotent: a step is a row,
    not a log entry, so re-running provisioning finds the same rows and completes only
    the pending ones. The paired CHECK keeps ``status`` and ``completed_at`` from
    disagreeing.
    """

    __tablename__ = "tenant_provisioning"

    step: Mapped[str]
    status: Mapped[str] = mapped_column(default=PROVISIONING_STATUS_PENDING)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("tenant_provisioning", "step", PROVISIONING_STEPS),
        status_check("tenant_provisioning", "status", PROVISIONING_STATUSES),
        CheckConstraint(
            "(status = 'done') = (completed_at IS NOT NULL)",
            # conv: the ck naming convention would otherwise wrap this explicit name a
            # second time at table-attach (see db.base.status_check).
            name=conv("ck_tenant_provisioning__done_has_completed_at"),
        ),
        UniqueConstraint("tenant_id", "step"),
        tenant_index("tenant_provisioning", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"TenantProvisioningStep(tenant_id={self.tenant_id!r}, "
            f"step={self.step!r}, status={self.status!r})"
        )


class TenantRegistrationKey(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """The idempotency record for one tenant registration.

    A repeat with the same key and the same body returns the recorded tenant; the same
    key with a different body is a 409, because silently returning the first result
    would hide a client bug (add-provider-plane/design.md, "Idempotency").
    """

    __tablename__ = "tenant_registration_keys"

    platform_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("platform_admins.id"))
    idempotency_key: Mapped[str]
    request_hash: Mapped[str]

    __table_args__ = (
        UniqueConstraint("platform_admin_id", "idempotency_key"),
        # Serves the ON DELETE CASCADE from tenants at teardown; Postgres does not
        # index the referencing side of a foreign key by itself.
        Index("ix_tenant_registration_keys__tenant_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"TenantRegistrationKey(id={self.id!r}, tenant_id={self.tenant_id!r})"
