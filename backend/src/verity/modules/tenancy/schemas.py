"""Request and response models for the tenancy module.

Requests forbid unknown fields, which is what makes "refuse any write of status,
plan, or slug through these routes" structural: a body carrying ``status`` fails
validation instead of being silently dropped. Responses never expose ORM objects
directly, and ``smtp_config_ref`` appears in **no** response model at all — the
absence is the contract (add-provider-plane spec, "Branding is read back").

Timestamps serialise as ISO 8601 UTC with a ``Z`` suffix (docs/conventions/api.md);
Pydantic's default ``+00:00`` is valid but not what the contract promises.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator


def _iso_utc_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[datetime, PlainSerializer(_iso_utc_z, return_type=str, when_used="json")]

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
"""A DNS label: the slug is the tenant's subdomain."""


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Provider authentication
# ---------------------------------------------------------------------------


class LoginRequest(_Request):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class ChallengeResponse(_Response):
    """A correct password buys a challenge, never a session (TOTP is mandatory)."""

    next_step: Literal["mfa_verify", "mfa_enroll"]
    challenge_token: str
    expires_at: UtcDateTime


class MfaVerifyRequest(_Request):
    challenge_token: str
    code: str | None = None
    recovery_code: str | None = None

    @model_validator(mode="after")
    def _exactly_one_factor(self) -> MfaVerifyRequest:
        if (self.code is None) == (self.recovery_code is None):
            raise ValueError("provide exactly one of code and recovery_code")
        return self


class SessionResponse(_Response):
    token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — a scheme name, not a secret
    expires_at: UtcDateTime


class MfaEnrollRequest(_Request):
    challenge_token: str


class MfaEnrollResponse(_Response):
    """The pending secret, returned exactly once for the authenticator app."""

    secret: str
    otpauth_uri: str


class MfaConfirmRequest(_Request):
    challenge_token: str
    code: str


class MfaConfirmResponse(_Response):
    """The first session plus the recovery codes — plaintext leaves the system once."""

    token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — a scheme name, not a secret
    expires_at: UtcDateTime
    recovery_codes: list[str]


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------


class _TenantProfileFields(_Request):
    """The optional profile, captured at registration where known and completed
    later — a trial signup will not have a registration number to hand."""

    trading_name: str | None = None
    industry: str | None = None
    registration_number: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    primary_contact_name: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    onboarded_at: date | None = None
    notes: str | None = None


class TenantRegistration(_TenantProfileFields):
    legal_name: str = Field(min_length=1)
    slug: str = Field(pattern=SLUG_PATTERN, max_length=63)
    plan: str = Field(min_length=1)


class TenantUpdate(_TenantProfileFields):
    """Profile updates only. ``status`` is a lifecycle transition, not a field write,
    and ``slug`` is the tenant's address — neither is accepted here, and an unknown
    field is a validation error rather than a silent drop."""

    legal_name: str | None = Field(default=None, min_length=1)
    plan: str | None = Field(default=None, min_length=1)


class TenantResponse(_Response):
    id: uuid.UUID
    legal_name: str
    trading_name: str | None
    slug: str
    industry: str | None
    registration_number: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state_region: str | None
    postal_code: str | None
    country: str | None
    primary_contact_name: str | None
    primary_contact_email: str | None
    primary_contact_phone: str | None
    plan: str
    status: str
    created_by: uuid.UUID | None
    onboarded_at: date | None
    notes: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class TenantPage(_Response):
    items: list[TenantResponse]
    next_cursor: str | None
    """Opaque. Pass it back as ``?cursor=`` for the next page; ``None`` means the
    register is exhausted."""


class TenantProfileResponse(_Response):
    """The tenant plane's view of its own registration profile.

    Deliberately narrower than :class:`TenantResponse`: ``created_by`` and ``notes``
    are provider-plane bookkeeping about the customer, not for the customer.
    """

    id: uuid.UUID
    legal_name: str
    trading_name: str | None
    slug: str
    industry: str | None
    registration_number: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state_region: str | None
    postal_code: str | None
    country: str | None
    primary_contact_name: str | None
    primary_contact_email: str | None
    primary_contact_phone: str | None
    plan: str
    status: str
    onboarded_at: date | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


TenantStatusFilter = Literal["provisioning", "active", "suspended", "terminated"]
"""Mirrors ``models.TENANT_STATUSES``; the CHECK constraint is the source of truth."""


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------


class BrandingPut(_Request):
    """A full replace: an omitted field clears its column.

    ``smtp_config_ref`` arrives as the secret value and is envelope-encrypted,
    AAD-bound to the tenant, before it reaches the database. It never comes back.
    """

    logo_ref: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    custom_domain: str | None = None
    email_from_name: str | None = None
    email_from_address: str | None = None
    smtp_config_ref: str | None = None
    document_footer: str | None = None


class BrandingResponse(_Response):
    """No ``smtp_config_ref``, in neither plaintext nor ciphertext — on any route."""

    tenant_id: uuid.UUID
    logo_ref: str | None
    primary_color: str | None
    secondary_color: str | None
    custom_domain: str | None
    email_from_name: str | None
    email_from_address: str | None
    document_footer: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------


class ProvisioningStepResponse(_Response):
    step: str
    status: str
    completed_at: UtcDateTime | None


class ProvisioningResponse(_Response):
    tenant_id: uuid.UUID
    tenant_status: str
    steps: list[ProvisioningStepResponse]
    remaining: list[str]
    """The steps still pending, so a caller need not diff the list to learn them."""
