"""Tenancy's business rules: provider authentication and the tenant lifecycle.

Two services, deliberately separate. ``ProviderAuthService`` runs the unauthenticated
login flows and therefore owns its units of work — it enters
``core.db.provider_session_scope`` itself, because a failed attempt's audit row must
**commit** while the request still fails with 401. A session injected by a dependency
would roll that row back with the rejection, which is exactly the record that must
survive. ``TenancyService`` runs behind ``require_provider`` and works on the caller's
session like every other authenticated service.

Every state-changing path writes its audit rows through ``AuditService`` on the same
session, inside the same transaction (backend/CLAUDE.md). Authentication events follow
week1-review-decisions.md items 2-3: a completed login is ``create`` on ``session``
with the token's ``jti``; failures are ``create`` on ``auth_attempt`` with a minted id
and a minimal outcome map; a completed enrollment is ``create`` on ``mfa_enrollment``.
Never an email address or any credential material in a snapshot.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal, Protocol

import orjson
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.crypto import CryptoError, get_secret_box
from verity.core.db import provider_session_scope
from verity.core.errors import AuthenticationRequired, Conflict, InvalidInput, NotFound
from verity.core.security import (
    IssuedToken,
    TotpVerification,
    decode_token,
    hash_password,
    issue_token,
    new_totp_secret,
    totp_provisioning_uri,
    verify_password,
    verify_totp,
)
from verity.modules.audit.service import AuditService, System, audit_service
from verity.modules.audit.service import PlatformAdmin as PlatformAdminActor
from verity.modules.tenancy.exceptions import (
    CustomDomainConflict,
    EnrollmentConflict,
    IdempotencyKeyConflict,
    SlugConflict,
)
from verity.modules.tenancy.models import (
    PLATFORM_ADMIN_STATUS_ACTIVE,
    PROVISIONING_STATUS_DONE,
    PROVISIONING_STATUS_PENDING,
    PROVISIONING_STEPS,
    STEP_CREATE_TENANT,
    STEP_INVITE_ADMIN,
    STEP_SEED_CONTENT,
    STEP_VERIFY,
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_PROVISIONING,
    PlatformAdmin,
    Tenant,
    TenantBranding,
    TenantProvisioningStep,
    TenantRegistrationKey,
)
from verity.modules.tenancy.repository import PlatformAdminRepository, TenantRepository
from verity.modules.tenancy.schemas import BrandingPut, TenantRegistration, TenantUpdate
from verity.shared.ids import uuid7

__all__ = [
    "AllProvisioningGates",
    "EnrollmentGrant",
    "EnrollmentStart",
    "LoginChallenge",
    "MembershipGates",
    "ProviderAuthService",
    "SessionGrant",
    "TenancyService",
    "generate_recovery_codes",
    "provider_auth_service",
    "tenancy_service",
]

_UNIFORM_LOGIN_DETAIL: Final = "provider login refused; see the auth_attempt audit row"

# ---------------------------------------------------------------------------
# Recovery codes — single-use, returned once in plaintext, stored as argon2id
# hashes (add-provider-plane/design.md: nothing ever needs to read one back,
# only to check one). Generation lives here rather than core.security because
# the storage shape (a JSONB list on the owning row) is this module's concern.
# ---------------------------------------------------------------------------

RECOVERY_CODE_COUNT: Final = 8
_RECOVERY_CODE_GROUP: Final = 5
# No 0/O, 1/l/i: a code read over the phone must survive the reading.
_RECOVERY_CODE_ALPHABET: Final = "abcdefghjkmnpqrstuvwxyz23456789"


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    """Mint ``count`` single-use recovery codes, e.g. ``"kv3nq-8wzp2"``."""

    def one() -> str:
        chars = [secrets.choice(_RECOVERY_CODE_ALPHABET) for _ in range(2 * _RECOVERY_CODE_GROUP)]
        return "".join(chars[:_RECOVERY_CODE_GROUP]) + "-" + "".join(chars[_RECOVERY_CODE_GROUP:])

    return [one() for _ in range(count)]


def hash_recovery_codes(codes: list[str]) -> list[str]:
    return [hash_password(code) for code in codes]


def consume_recovery_code(hashes: list[str], candidate: str) -> list[str] | None:
    """The remaining hashes after consuming ``candidate``, or ``None`` on no match.

    Consuming is what makes the code single-use: the caller stores the returned list,
    and the spent hash is gone.
    """
    normalized = candidate.strip().lower()
    for position, stored in enumerate(hashes):
        if verify_password(stored, normalized).ok:
            return hashes[:position] + hashes[position + 1 :]
    return None


# ---------------------------------------------------------------------------
# Provider authentication
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoginChallenge:
    """The outcome of a correct password. Never a session — TOTP is mandatory."""

    next_step: Literal["mfa_verify", "mfa_enroll"]
    challenge_token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class SessionGrant:
    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class EnrollmentStart:
    """The secret and URI the authenticator app enrolls from. Returned once."""

    secret: str
    otpauth_uri: str


@dataclass(frozen=True, slots=True)
class EnrollmentGrant:
    """A confirmed enrollment: the first session plus the one-time recovery codes."""

    token: str
    expires_at: datetime
    recovery_codes: list[str]


def _mfa_aad(admin_id: uuid.UUID) -> str:
    """The AAD binding a stored MFA secret to the admin row that owns it.

    Without the binding, ciphertext copied from one admin's row onto another's
    decrypts cleanly — a write into the table would move a known secret onto a
    target account (add-provider-plane/design.md, "The MFA secret").
    """
    return f"platform_admin:{admin_id}"


class ProviderAuthService:
    """Password → challenge → TOTP → session, with no shortcut past the second factor.

    Each public method is one committed unit of work followed, on failure, by the
    raise: the audit row describing the refused attempt must outlive the refusal.
    """

    def __init__(
        self,
        admins: PlatformAdminRepository | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._admins = admins or PlatformAdminRepository()
        self._audit = audit or audit_service

    async def login(self, *, email: str, password: str) -> LoginChallenge:
        """Verify the password and issue a challenge — never a session.

        The unknown-email path verifies against a dummy hash inside
        ``core.security.verify_password``, so its wall time matches a wrong
        password and the route does not disclose which addresses exist.
        """
        challenge: LoginChallenge | None = None
        async with provider_session_scope() as session:
            admin = await self._admins.get_by_email(session, email.strip().lower())
            verification = verify_password(admin.password_hash if admin else "", password)
            if admin is None:
                await self._record_attempt(
                    session, actor=System(), outcome="failed_password", reason="unknown_email"
                )
            elif not verification.ok:
                await self._record_attempt(
                    session, actor=PlatformAdminActor(admin.id), outcome="failed_password"
                )
            elif admin.status != PLATFORM_ADMIN_STATUS_ACTIVE:
                await self._record_attempt(
                    session, actor=PlatformAdminActor(admin.id), outcome="admin_disabled"
                )
            else:
                if verification.needs_rehash:
                    # Part of the successful authentication step, not a separate
                    # auditable action: the credential is unchanged, its parameters
                    # caught up with the pinned configuration.
                    admin.password_hash = hash_password(password)
                issued = issue_token(subject=admin.id, plane="provider", typ="challenge")
                next_step: Literal["mfa_verify", "mfa_enroll"] = (
                    "mfa_verify" if admin.mfa_enabled else "mfa_enroll"
                )
                challenge = LoginChallenge(
                    next_step=next_step,
                    challenge_token=issued.token,
                    expires_at=issued.expires_at,
                )
        if challenge is None:
            raise AuthenticationRequired(detail=_UNIFORM_LOGIN_DETAIL)
        return challenge

    async def verify_mfa(
        self,
        *,
        challenge_token: str,
        code: str | None = None,
        recovery_code: str | None = None,
    ) -> SessionGrant:
        """Exchange a challenge plus a second factor for a session.

        Exactly one of ``code`` and ``recovery_code`` must be given. A TOTP code at or
        before the stored counter is refused — replay protection — and a recovery code
        is consumed by the check that accepts it.
        """
        if (code is None) == (recovery_code is None):
            raise InvalidInput(detail="exactly one of code and recovery_code is required")
        claims = decode_token(challenge_token, expected_typ="challenge", expected_plane="provider")

        grant: SessionGrant | None = None
        async with provider_session_scope() as session:
            admin = await self._admins.get(session, claims.subject)
            if admin is None:
                await self._record_attempt(
                    session, actor=System(), outcome="failed_totp", reason="unknown_admin"
                )
            elif admin.status != PLATFORM_ADMIN_STATUS_ACTIVE:
                await self._record_attempt(
                    session, actor=PlatformAdminActor(admin.id), outcome="admin_disabled"
                )
            elif not admin.mfa_enabled or admin.mfa_secret_encrypted is None:
                # A challenge for an unenrolled admin only opens enrollment. No code
                # was checked against a secret, so there is no attempt to record.
                pass
            elif code is not None:
                secret = self._decrypt_mfa_secret(admin)
                result = (
                    TotpVerification(ok=False, counter=None)
                    if secret is None
                    else verify_totp(secret, code, admin.last_totp_counter)
                )
                if result.ok:
                    admin.last_totp_counter = result.counter
                    grant = await self._grant_session(session, admin, method="totp")
                else:
                    await self._record_attempt(
                        session,
                        actor=PlatformAdminActor(admin.id),
                        outcome="failed_totp",
                        reason="secret_unreadable" if secret is None else None,
                    )
            elif recovery_code is not None:
                remaining = consume_recovery_code(
                    admin.recovery_codes_encrypted or [], recovery_code
                )
                if remaining is None:
                    await self._record_attempt(
                        session,
                        actor=PlatformAdminActor(admin.id),
                        outcome="failed_recovery_code",
                    )
                else:
                    admin.recovery_codes_encrypted = remaining
                    grant = await self._grant_session(session, admin, method="recovery_code")
        if grant is None:
            raise AuthenticationRequired(detail="provider MFA verification refused")
        return grant

    async def start_enrollment(self, *, challenge_token: str) -> EnrollmentStart:
        """Mint and store a pending TOTP secret; enabled only when confirmed.

        Re-running before confirmation replaces the pending secret. An admin whose
        MFA is already enabled is refused — a re-enrollment resets a credential and
        Week 1 has no audited flow for that.
        """
        claims = decode_token(challenge_token, expected_typ="challenge", expected_plane="provider")
        conflict = False
        start: EnrollmentStart | None = None
        async with provider_session_scope() as session:
            admin = await self._admins.get(session, claims.subject)
            if admin is None or admin.status != PLATFORM_ADMIN_STATUS_ACTIVE:
                pass
            elif admin.mfa_enabled:
                conflict = True
            else:
                before = AuditService.snapshot(admin, fields=_MFA_SNAPSHOT_FIELDS)
                secret = new_totp_secret()
                admin.mfa_secret_encrypted = get_secret_box().encrypt(
                    secret, aad=_mfa_aad(admin.id)
                )
                await self._audit.record(
                    session,
                    action="update",
                    object_type="platform_admin",
                    object_id=admin.id,
                    actor=PlatformAdminActor(admin.id),
                    tenant_id=None,
                    before=before,
                    after=AuditService.snapshot(admin, fields=_MFA_SNAPSHOT_FIELDS),
                )
                start = EnrollmentStart(
                    secret=secret,
                    otpauth_uri=totp_provisioning_uri(secret, admin.email),
                )
        if conflict:
            raise EnrollmentConflict(detail="MFA is already enabled for this admin")
        if start is None:
            raise AuthenticationRequired(detail="enrollment refused: admin missing or disabled")
        return start

    async def confirm_enrollment(self, *, challenge_token: str, code: str) -> EnrollmentGrant:
        """Prove the authenticator holds the pending secret, then enable MFA.

        On success, in one transaction: MFA is enabled, the accepted counter stored,
        the recovery codes minted and hashed, the enrollment and the login audited.
        The plaintext codes leave the process exactly once, in the return value.
        """
        claims = decode_token(challenge_token, expected_typ="challenge", expected_plane="provider")
        conflict = False
        grant: EnrollmentGrant | None = None
        async with provider_session_scope() as session:
            admin = await self._admins.get(session, claims.subject)
            if admin is None or admin.status != PLATFORM_ADMIN_STATUS_ACTIVE:
                pass
            elif admin.mfa_enabled or admin.mfa_secret_encrypted is None:
                conflict = True
            else:
                secret = self._decrypt_mfa_secret(admin)
                result = (
                    TotpVerification(ok=False, counter=None)
                    if secret is None
                    else verify_totp(secret, code, admin.last_totp_counter)
                )
                if not result.ok:
                    await self._record_attempt(
                        session,
                        actor=PlatformAdminActor(admin.id),
                        outcome="failed_totp",
                        reason="secret_unreadable" if secret is None else None,
                    )
                else:
                    admin.mfa_enabled = True
                    admin.last_totp_counter = result.counter
                    codes = generate_recovery_codes()
                    admin.recovery_codes_encrypted = hash_recovery_codes(codes)
                    await self._audit.record(
                        session,
                        action="create",
                        object_type="mfa_enrollment",
                        object_id=uuid7(),
                        actor=PlatformAdminActor(admin.id),
                        tenant_id=None,
                        after={"outcome": "completed"},
                    )
                    session_grant = await self._grant_session(session, admin, method="totp")
                    grant = EnrollmentGrant(
                        token=session_grant.token,
                        expires_at=session_grant.expires_at,
                        recovery_codes=codes,
                    )
        if conflict:
            raise EnrollmentConflict(
                detail="already enabled, or confirmation before enrollment started"
            )
        if grant is None:
            raise AuthenticationRequired(detail="provider MFA confirmation refused")
        return grant

    @staticmethod
    def _decrypt_mfa_secret(admin: PlatformAdmin) -> str | None:
        """The stored TOTP secret, or ``None`` when its ciphertext refuses to
        authenticate.

        A ciphertext failing under this row's AAD was moved from another row,
        corrupted, or tampered with — precisely what the binding exists to catch —
        so the login fails closed as an ordinary refusal rather than surfacing a
        500 that would tell a prober something interesting happened.
        """
        if admin.mfa_secret_encrypted is None:
            return None
        try:
            return get_secret_box().decrypt(admin.mfa_secret_encrypted, aad=_mfa_aad(admin.id))
        except CryptoError:
            return None

    async def _grant_session(
        self, session: AsyncSession, admin: PlatformAdmin, *, method: str
    ) -> SessionGrant:
        """Issue the session token and write the login's audit row (decision 2:
        ``create`` on ``session``, ``object_id`` = the token's ``jti``)."""
        issued: IssuedToken = issue_token(subject=admin.id, plane="provider", typ="session")
        await self._audit.record(
            session,
            action="create",
            object_type="session",
            object_id=issued.jti,
            actor=PlatformAdminActor(admin.id),
            tenant_id=None,
            after={"method": method, "plane": "provider"},
        )
        return SessionGrant(token=issued.token, expires_at=issued.expires_at)

    async def _record_attempt(
        self,
        session: AsyncSession,
        *,
        actor: PlatformAdminActor | System,
        outcome: str,
        reason: str | None = None,
    ) -> None:
        """Decision 3: a failed attempt is an event — ``create`` on ``auth_attempt``,
        minted id, minimal outcome map, never an email address in the snapshot."""
        after: dict[str, str] = {"outcome": outcome}
        if reason is not None:
            after["reason"] = reason
        await self._audit.record(
            session,
            action="create",
            object_type="auth_attempt",
            object_id=uuid7(),
            actor=actor,
            tenant_id=None,
            after=after,
        )


_MFA_SNAPSHOT_FIELDS: Final = ("id", "mfa_enabled", "mfa_secret_encrypted")


# ---------------------------------------------------------------------------
# Tenant lifecycle
# ---------------------------------------------------------------------------

_TENANT_PROFILE_FIELDS: Final = (
    "id",
    "legal_name",
    "trading_name",
    "slug",
    "industry",
    "registration_number",
    "address_line1",
    "address_line2",
    "city",
    "state_region",
    "postal_code",
    "country",
    "primary_contact_name",
    "primary_contact_email",
    "primary_contact_phone",
    "plan",
    "status",
    "created_by",
    "onboarded_at",
    "notes",
)

_STEP_SNAPSHOT_FIELDS: Final = ("id", "tenant_id", "step", "status", "completed_at")

BRANDING_SNAPSHOT_FIELDS: Final = (
    "tenant_id",
    "logo_ref",
    "primary_color",
    "secondary_color",
    "custom_domain",
    "email_from_name",
    "email_from_address",
    "document_footer",
)
"""Every branding column except ``smtp_config_ref``. The credential is **excluded**
from both audit snapshots, not merely redacted — its ciphertext is still a secret's
address (add-provider-plane spec, "Mail credentials are supplied")."""

_BRANDING_REPLACE_FIELDS: Final = (
    "logo_ref",
    "primary_color",
    "secondary_color",
    "custom_domain",
    "email_from_name",
    "email_from_address",
    "document_footer",
)


def _branding_aad(tenant_id: uuid.UUID) -> str:
    return f"tenant_branding:{tenant_id}"


_CURSOR_ERROR: Final = "The pagination cursor is not valid."


def encode_tenant_cursor(tenant_id: uuid.UUID) -> str:
    """Opaque keyset cursor for the register: the last-seen UUIDv7 ``id``, which is
    time-ordered by construction, so "before this id" is "older than this row"."""
    return base64.urlsafe_b64encode(str(tenant_id).encode()).decode()


def decode_tenant_cursor(cursor: str) -> uuid.UUID:
    """Reverse :func:`encode_tenant_cursor`.

    Raises:
        InvalidInput: on any malformed cursor — one code and one message for every
            failure mode, because the cursor is opaque.
    """
    try:
        return uuid.UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidInput(_CURSOR_ERROR, detail=f"tenant cursor failed to decode: {exc}") from exc


def _request_hash(profile: TenantRegistration) -> str:
    """A canonical digest of the registration body, for idempotency comparison."""
    canonical = orjson.dumps(profile.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(canonical).hexdigest()


def _violates(exc: IntegrityError, constraint: str) -> bool:
    return constraint in str(exc.orig)


class MembershipGates(Protocol):
    """The narrow seam provisioning uses to ask about a tenant's admin membership.

    Memberships belong to the IAM module, which does not exist yet. This stage ships
    the honest answer "not satisfiable yet"; ``add-identity-and-access`` supplies the
    real checks through ``TenancyService.use_gates`` without this module changing
    (week1-review-decisions.md, decision 10).
    """

    # The two parameters are positional-only so an implementation whose body does
    # not need them yet (the Week 1 stand-ins below) can underscore them.

    async def admin_membership_recorded(
        self, session: AsyncSession, tenant_id: uuid.UUID, /
    ) -> bool:
        """Whether the tenant has at least one Admin membership recorded."""
        ...

    async def active_admin_membership_exists(
        self, session: AsyncSession, tenant_id: uuid.UUID, /
    ) -> bool:
        """Whether the tenant has at least one **active** Admin membership."""
        ...


class NoMembershipsYet:
    """Week 1 default: the membership tables do not exist, so neither check can pass.

    ``invite_admin`` and ``verify`` therefore stay ``pending`` — honestly, rather than
    pretending completion — and the run completes what it can.
    """

    async def admin_membership_recorded(
        self, _session: AsyncSession, _tenant_id: uuid.UUID, /
    ) -> bool:
        return False

    async def active_admin_membership_exists(
        self, _session: AsyncSession, _tenant_id: uuid.UUID, /
    ) -> bool:
        return False


class AllProvisioningGates:
    """Every gate answers yes. For tests that need a tenant to reach ``active``."""

    async def admin_membership_recorded(
        self, _session: AsyncSession, _tenant_id: uuid.UUID, /
    ) -> bool:
        return True

    async def active_admin_membership_exists(
        self, _session: AsyncSession, _tenant_id: uuid.UUID, /
    ) -> bool:
        return True


class TenancyService:
    """Registration, the register, branding, and provisioning.

    Methods run on the caller's session — ``core.deps.get_provider_session`` for the
    provider plane, ``get_tenant_session`` for the two tenant-plane reads — and never
    commit. Every write lands its audit rows on the same session.
    """

    def __init__(
        self,
        tenants: TenantRepository | None = None,
        audit: AuditService | None = None,
        gates: MembershipGates | None = None,
    ) -> None:
        self._tenants = tenants or TenantRepository()
        self._audit = audit or audit_service
        self._gates: MembershipGates = gates or NoMembershipsYet()

    def use_gates(self, gates: MembershipGates) -> None:
        """Swap in the real membership checks. Called once by the IAM module's wiring."""
        self._gates = gates

    # -- registration -------------------------------------------------------

    async def register_tenant(
        self,
        session: AsyncSession,
        *,
        actor_admin_id: uuid.UUID,
        profile: TenantRegistration,
        idempotency_key: str | None = None,
    ) -> Tenant:
        """Create the tenant, its empty branding, and its provisioning steps.

        ``create_tenant`` is done at registration (decision 10) — the row's existence
        is the step. A repeated ``Idempotency-Key`` with the same body returns the
        original tenant; with a different body it is a 409. The slug's unique
        constraint is the backstop when no key is supplied.
        """
        body_hash = _request_hash(profile)
        if idempotency_key is not None:
            recorded = await self._tenants.get_registration_key(
                session, platform_admin_id=actor_admin_id, idempotency_key=idempotency_key
            )
            if recorded is not None:
                if recorded.request_hash != body_hash:
                    raise IdempotencyKeyConflict(
                        detail=f"key reused with a different body for tenant {recorded.tenant_id}"
                    )
                original = await self._tenants.get(session, recorded.tenant_id)
                if original is None:
                    raise NotFound(detail=f"recorded tenant {recorded.tenant_id} is gone")
                return original

        if await self._tenants.get_by_slug(session, profile.slug) is not None:
            raise SlugConflict(detail=f"slug {profile.slug!r} already registered")

        tenant = Tenant(
            status=TENANT_STATUS_PROVISIONING,
            created_by=actor_admin_id,
            **profile.model_dump(),
        )
        try:
            await self._tenants.add(session, tenant)
        except IntegrityError as exc:
            # The race the pre-check cannot close: two registrations, one slug.
            if _violates(exc, "uq_tenants__slug"):
                raise SlugConflict(
                    detail=f"slug {profile.slug!r} lost a registration race"
                ) from exc
            raise

        actor = PlatformAdminActor(actor_admin_id)
        await self._audit.record(
            session,
            action="create",
            object_type="tenant",
            object_id=tenant.id,
            actor=actor,
            tenant_id=tenant.id,
            after=AuditService.snapshot(tenant, fields=_TENANT_PROFILE_FIELDS),
        )

        branding = TenantBranding(tenant_id=tenant.id)
        await self._tenants.add_branding(session, branding)
        await self._audit.record(
            session,
            action="create",
            object_type="tenant_branding",
            object_id=tenant.id,
            actor=actor,
            tenant_id=tenant.id,
            after=AuditService.snapshot(branding, fields=BRANDING_SNAPSHOT_FIELDS),
        )

        now = datetime.now(UTC)
        for step_name in PROVISIONING_STEPS:
            done = step_name == STEP_CREATE_TENANT
            step = TenantProvisioningStep(
                tenant_id=tenant.id,
                step=step_name,
                status=PROVISIONING_STATUS_DONE if done else PROVISIONING_STATUS_PENDING,
                completed_at=now if done else None,
            )
            await self._tenants.add_step(session, step)
            await self._audit.record(
                session,
                action="create",
                object_type="tenant_provisioning",
                object_id=step.id,
                actor=actor,
                tenant_id=tenant.id,
                after=AuditService.snapshot(step, fields=_STEP_SNAPSHOT_FIELDS),
            )

        if idempotency_key is not None:
            # Request-deduplication bookkeeping, not a compliance object: the tenant's
            # own `create` row above is the audited action.
            await self._tenants.add_registration_key(
                session,
                TenantRegistrationKey(
                    platform_admin_id=actor_admin_id,
                    idempotency_key=idempotency_key,
                    request_hash=body_hash,
                    tenant_id=tenant.id,
                ),
            )
        return tenant

    # -- the register -------------------------------------------------------

    async def get_tenant(self, session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self._tenants.get(session, tenant_id)
        if tenant is None:
            raise NotFound(detail=f"tenant {tenant_id} not found")
        return tenant

    async def list_tenants(
        self,
        session: AsyncSession,
        *,
        limit: int,
        cursor: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        """One page, newest first, plus the keyset cursor for the next or ``None``."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        before_id = None if cursor is None else decode_tenant_cursor(cursor)
        # One row beyond the page answers "is there a next page" without a count.
        tenants = await self._tenants.list_page(
            session, limit=limit + 1, before_id=before_id, status=status
        )
        if len(tenants) <= limit:
            return tenants, None
        page = tenants[:limit]
        return page, encode_tenant_cursor(page[-1].id)

    async def update_tenant(
        self,
        session: AsyncSession,
        *,
        actor_admin_id: uuid.UUID,
        tenant_id: uuid.UUID,
        changes: TenantUpdate,
    ) -> Tenant:
        """Update profile fields. Lifecycle is not a field write: ``status`` and
        ``slug`` are not in the schema, and provisioning owns the ``active`` flip."""
        tenant = await self.get_tenant(session, tenant_id)
        data = changes.model_dump(exclude_unset=True)
        if not data:
            return tenant
        before = AuditService.snapshot(tenant, fields=_TENANT_PROFILE_FIELDS)
        for name, value in data.items():
            setattr(tenant, name, value)
        after = AuditService.snapshot(tenant, fields=_TENANT_PROFILE_FIELDS)
        if after == before:
            return tenant
        await session.flush([tenant])
        # The UPDATE expires the onupdate-computed updated_at; reload it here, on
        # the async session, so serialising the response cannot trigger lazy IO.
        await session.refresh(tenant)
        await self._audit.record(
            session,
            action="update",
            object_type="tenant",
            object_id=tenant.id,
            actor=PlatformAdminActor(actor_admin_id),
            tenant_id=tenant.id,
            before=before,
            after=after,
        )
        return tenant

    # -- branding ------------------------------------------------------------

    async def get_branding(self, session: AsyncSession, tenant_id: uuid.UUID) -> TenantBranding:
        branding = await self._tenants.get_branding(session, tenant_id)
        if branding is None:
            raise NotFound(detail=f"branding for tenant {tenant_id} not found")
        return branding

    async def put_branding(
        self,
        session: AsyncSession,
        *,
        actor_admin_id: uuid.UUID,
        tenant_id: uuid.UUID,
        body: BrandingPut,
    ) -> TenantBranding:
        """Full replace of the one branding row — idempotent by definition.

        The SMTP credential is encrypted before it touches the session, AAD-bound to
        this tenant, and excluded from the response schema and both snapshots. An
        omitted field clears its column; that is what "full replace" means.
        """
        if await self._tenants.get(session, tenant_id) is None:
            raise NotFound(detail=f"tenant {tenant_id} not found")
        branding = await self._tenants.get_branding(session, tenant_id)
        if branding is None:
            # Unreachable for tenants registered here; kept so a future signup path
            # that missed the empty row cannot make branding un-settable.
            branding = TenantBranding(tenant_id=tenant_id)
            await self._tenants.add_branding(session, branding)

        before = AuditService.snapshot(branding, fields=BRANDING_SNAPSHOT_FIELDS)
        smtp_changed = self._replace_smtp(branding, tenant_id, body.smtp_config_ref)
        for name in _BRANDING_REPLACE_FIELDS:
            setattr(branding, name, getattr(body, name))
        after = AuditService.snapshot(branding, fields=BRANDING_SNAPSHOT_FIELDS)
        if after == before and not smtp_changed:
            return branding

        try:
            await session.flush([branding])
        except IntegrityError as exc:
            if _violates(exc, "uq_tenant_branding__custom_domain"):
                raise CustomDomainConflict(
                    detail=f"custom domain taken; tenant {tenant_id}"
                ) from exc
            raise
        # See update_tenant: reload the expired updated_at on the async session.
        await session.refresh(branding)
        await self._audit.record(
            session,
            action="update",
            object_type="tenant_branding",
            object_id=tenant_id,
            actor=PlatformAdminActor(actor_admin_id),
            tenant_id=tenant_id,
            before=before,
            after=after,
        )
        return branding

    @staticmethod
    def _replace_smtp(
        branding: TenantBranding, tenant_id: uuid.UUID, plaintext: str | None
    ) -> bool:
        """Set the ciphertext column from the supplied plaintext; report a change.

        Fresh ciphertext differs on every call (random nonces), so "changed" is
        judged on the decrypted value: replaying an identical PUT keeps the stored
        ciphertext and writes nothing, which is what idempotent means here.
        """
        box = get_secret_box()
        aad = _branding_aad(tenant_id)
        if plaintext is None:
            had = branding.smtp_config_ref is not None
            branding.smtp_config_ref = None
            return had
        if branding.smtp_config_ref is not None:
            with contextlib.suppress(CryptoError):
                if box.decrypt(branding.smtp_config_ref, aad=aad) == plaintext:
                    return False
        branding.smtp_config_ref = box.encrypt(plaintext, aad=aad)
        return True

    # -- provisioning ---------------------------------------------------------

    async def get_provisioning(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[Tenant, list[TenantProvisioningStep]]:
        tenant = await self.get_tenant(session, tenant_id)
        return tenant, await self._tenants.get_steps(session, tenant_id)

    async def run_provisioning(
        self,
        session: AsyncSession,
        *,
        actor_admin_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> tuple[Tenant, list[TenantProvisioningStep]]:
        """Complete every pending step that can complete; flip to active on the last.

        Idempotent by construction: steps are rows under ``UNIQUE (tenant_id, step)``,
        a completed step is never re-run, and a run that completes nothing writes
        nothing — including no audit rows, because no state changed. Week 1 step
        semantics are decision 10; the membership-dependent steps ask ``self._gates``.
        """
        tenant = await self.get_tenant(session, tenant_id)
        steps = await self._tenants.get_steps(session, tenant_id)
        actor = PlatformAdminActor(actor_admin_id)

        by_name = {step.step: step for step in steps}
        for step in steps:
            if step.status != PROVISIONING_STATUS_PENDING:
                continue
            if not await self._step_can_complete(session, tenant, step.step, by_name):
                continue
            before = AuditService.snapshot(step, fields=_STEP_SNAPSHOT_FIELDS)
            step.status = PROVISIONING_STATUS_DONE
            step.completed_at = datetime.now(UTC)
            await session.flush([step])
            await self._audit.record(
                session,
                action="transition",
                object_type="tenant_provisioning",
                object_id=step.id,
                actor=actor,
                tenant_id=tenant.id,
                before=before,
                after=AuditService.snapshot(step, fields=_STEP_SNAPSHOT_FIELDS),
            )

        all_done = all(step.status == PROVISIONING_STATUS_DONE for step in steps)
        if all_done and tenant.status == TENANT_STATUS_PROVISIONING:
            before = AuditService.snapshot(tenant, fields=_TENANT_PROFILE_FIELDS)
            tenant.status = TENANT_STATUS_ACTIVE
            await session.flush([tenant])
            await self._audit.record(
                session,
                action="transition",
                object_type="tenant",
                object_id=tenant.id,
                actor=actor,
                tenant_id=tenant.id,
                before=before,
                after=AuditService.snapshot(tenant, fields=_TENANT_PROFILE_FIELDS),
            )
        return tenant, steps

    async def _step_can_complete(
        self,
        session: AsyncSession,
        tenant: Tenant,
        step_name: str,
        by_name: dict[str, TenantProvisioningStep],
    ) -> bool:
        """Decision 10, step by step."""
        if step_name == STEP_CREATE_TENANT:
            return True  # the tenant row in hand is the step's own evidence
        if step_name == STEP_SEED_CONTENT:
            # An honest no-op: 0 templates instantiated, because the global content
            # library does not exist yet. Real work when the library lands.
            return True
        if step_name == STEP_INVITE_ADMIN:
            return await self._gates.admin_membership_recorded(session, tenant.id)
        if step_name == STEP_VERIFY:
            others_done = all(
                by_name[name].status == PROVISIONING_STATUS_DONE
                for name in (STEP_CREATE_TENANT, STEP_SEED_CONTENT, STEP_INVITE_ADMIN)
            )
            return others_done and await self._gates.active_admin_membership_exists(
                session, tenant.id
            )
        raise Conflict(detail=f"unknown provisioning step {step_name!r}")

    # -- tenant-plane reads ---------------------------------------------------

    async def get_own_tenant(self, session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
        """The calling tenant's profile, on a session already bound to that tenant.

        The RLS SELECT policy on ``tenants`` is what bounds the row set; an id that
        is not the bound tenant reads as absent, so the answer is 404 and never 403.
        """
        return await self.get_tenant(session, tenant_id)

    async def get_own_branding(self, session: AsyncSession, tenant_id: uuid.UUID) -> TenantBranding:
        return await self.get_branding(session, tenant_id)


provider_auth_service: Final = ProviderAuthService()
tenancy_service: Final = TenancyService()
"""The shared instances the routers call. The classes stay importable for tests that
fake the repositories, and ``tenancy_service.use_gates`` is the IAM wiring point."""
