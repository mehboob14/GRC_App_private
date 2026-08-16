"""Identity and access: authentication flows, RBAC management, provisioning gates.

Two services, mirroring the tenancy module. ``IamAuthService`` runs the
unauthenticated and partially-authenticated flows and therefore owns its units of
work — a failed attempt's audit row must **commit** while the request still fails
with 401, and signup must be one transaction end to end. ``IamService`` runs behind
``require(...)`` on the caller's tenant-bound session like every other
authenticated service.

Where the auth flows get their visibility
-----------------------------------------
A login knows an email; an invite token knows a membership id. Neither knows a
tenant until the membership row answers, and the membership row is tenant-scoped.
So the auth flows enter ``core.db.provider_session_scope`` — the same dual-plane
mechanism ``audit_log`` uses — under the identity-resolution **SELECT-only**
policies the iam migration adds. Writes still require the tenant: once the row
has named it, ``bind_tenant_context`` binds it *in the same transaction* (both
settings coexist; this is the deliberate, service-controlled exception that lets
signup write the tenant register and the tenant's first membership atomically).

Every state-changing path writes its audit rows through ``AuditService`` on the
same session, inside the same transaction. Authentication events follow
week1-review-decisions.md items 2-3, exactly as the provider plane does: a
completed login is ``create`` on ``session`` with the token's ``jti`` in the
membership's tenant stream; failures are ``create`` on ``auth_attempt``; a
completed enrollment is ``create`` on ``mfa_enrollment``. Never an email address
or any credential material in an attempt snapshot.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from html import escape as _html_escape
from typing import Final, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.config import get_settings
from verity.core.crypto import CryptoError, get_secret_box
from verity.core.db import provider_session_scope
from verity.core.deps import (
    active_role_ids,
    assignment_window_active,
    fetch_grants_for_membership,
    resolve_effective_permissions,
)
from verity.core.email import Mailer, OutboundEmail, get_mailer
from verity.core.errors import AuthenticationRequired, InvalidInput, InvalidToken, NotFound
from verity.core.rls import bind_tenant_context
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
from verity.modules.audit.service import Actor, AuditService, System, audit_service
from verity.modules.audit.service import Membership as MembershipActor
from verity.modules.audit.service import PlatformAdmin as PlatformAdminActor
from verity.modules.iam.exceptions import (
    AlreadyMember,
    BuiltInRoleImmutable,
    DuplicateAssignment,
    EmailTaken,
    InvalidInvite,
    InviteAlreadyAccepted,
    MfaEnrollmentConflict,
    NameConflict,
    WeakPassword,
)
from verity.modules.iam.models import (
    ADMIN_ROLE_NAME,
    ASSIGNEE_TYPE_GROUP,
    ASSIGNEE_TYPE_MEMBERSHIP,
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_DISABLED,
    MEMBERSHIP_STATUS_INVITED,
    USER_STATUS_ACTIVE,
    Credentials,
    Group,
    GroupMember,
    Role,
    RoleAssignment,
    TenantMembership,
    User,
)
from verity.modules.iam.repository import (
    GroupRepository,
    MembershipRepository,
    RoleRepository,
    TenantSettingsRepository,
    UserRepository,
)
from verity.modules.tenancy.exceptions import SlugConflict
from verity.modules.tenancy.schemas import TenantRegistration
from verity.modules.tenancy.service import (
    consume_recovery_code,
    generate_recovery_codes,
    hash_recovery_codes,
    tenancy_service,
)
from verity.shared.ids import uuid7

__all__ = [
    "MIN_PASSWORD_LENGTH",
    "AuthOutcome",
    "ChallengeIssued",
    "EnrollmentStarted",
    "GroupView",
    "IamAuthService",
    "IamMembershipGates",
    "IamService",
    "InvitationAccepted",
    "InviteResult",
    "MemberView",
    "PrincipalSnapshot",
    "RoleView",
    "SelectionIssued",
    "SessionIssued",
    "WorkspaceEntry",
    "iam_auth_service",
    "iam_service",
]

MIN_PASSWORD_LENGTH: Final = 10
TRIAL_PLAN: Final = "trial"

_UNIFORM_LOGIN_DETAIL: Final = "tenant login refused; see the auth_attempt audit row"

_TENANT_STATUS_ACTIVE: Final = "active"
"""Mirrors ``tenancy.models.TENANT_STATUS_ACTIVE`` by value: iam reaches tenancy
through its service interface only, never its models (import-linter enforces)."""

BUILT_IN_ROLE_KEYS: Final[dict[str, tuple[str, ...] | None]] = {
    ADMIN_ROLE_NAME: None,  # every key that exists, resolved at check time (decision 13)
    "Compliance Manager": (
        "members:read",
        "groups:read",
        "roles:read",
        "tenant:read",
        "audit:read",
    ),
    "Control Owner": ("tenant:read",),
    "Employee": ("tenant:read",),
    "Auditor": ("tenant:read", "audit:read"),
}
"""The five built-in roles and their Week 1 keys (design.md). Keys for modules
that do not exist yet are simply absent from ``permissions`` and are attached by
the module change that introduces them."""

_USER_SNAPSHOT: Final = ("id", "email", "full_name", "status", "mfa_enabled")
_CREDENTIALS_SNAPSHOT: Final = (
    "user_id",
    "password_hash",
    "mfa_secret_encrypted",
    "mfa_enrolled_at",
)
_MEMBERSHIP_SNAPSHOT: Final = (
    "id",
    "tenant_id",
    "user_id",
    "status",
    "invited_at",
    "accepted_at",
    "disabled_at",
)
_GROUP_SNAPSHOT: Final = ("id", "tenant_id", "name")
_GROUP_MEMBER_SNAPSHOT: Final = ("id", "tenant_id", "group_id", "tenant_membership_id")
_ROLE_SNAPSHOT: Final = ("id", "tenant_id", "name", "built_in")
_ASSIGNMENT_SNAPSHOT: Final = (
    "id",
    "tenant_id",
    "role_id",
    "assignee_type",
    "assignee_id",
    "engagement_id",
    "valid_from",
    "valid_until",
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    """The platform password policy. Raised as ``weak_password`` so the client
    gets the stable code it switches on rather than a generic 422."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(detail=f"password shorter than {MIN_PASSWORD_LENGTH} characters")


def _credentials_aad(user_id: uuid.UUID) -> str:
    """The AAD binding a stored MFA secret to the credentials row that owns it —
    ciphertext moved onto another user's row refuses to decrypt."""
    return f"credentials:{user_id}"


_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def derive_slug_candidates(company_name: str, email: str) -> tuple[str, str]:
    """The slug for a self-service signup, plus a deterministic fallback.

    Deterministic on purpose: an idempotent retry of the same signup must derive
    the same slug both times, or the recorded request hash would not match.
    """
    base = _SLUG_STRIP.sub("-", company_name.lower()).strip("-")[:40].strip("-") or "workspace"
    digest = hashlib.sha256(f"{company_name}\x00{email}".encode()).hexdigest()[:6]
    return base, f"{base}-{digest}"


def _validate_window(valid_from: date | None, valid_until: date | None) -> None:
    if valid_from is not None and valid_until is not None and valid_from > valid_until:
        raise InvalidInput(detail="valid_from is after valid_until")


def tenant_display_name(legal_name: str, trading_name: str | None) -> str:
    return trading_name or legal_name


# ---------------------------------------------------------------------------
# Outcome types — domain shapes the router maps onto the response contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    membership_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role_name: str
    status: str


@dataclass(frozen=True, slots=True)
class PrincipalSnapshot:
    """What the frontend's ``SessionPrincipal`` is built from."""

    user_id: uuid.UUID
    email: str
    full_name: str
    user_status: str
    mfa_enabled: bool
    membership_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    permissions: list[str]
    role_names: list[str]


@dataclass(frozen=True, slots=True)
class SessionIssued:
    """A completed authentication: the session token and who it belongs to."""

    token: str
    expires_at: datetime
    principal: PrincipalSnapshot
    workspaces: list[WorkspaceEntry]
    recovery_codes: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ChallengeIssued:
    """The second factor stands between this caller and a session."""

    next_step: Literal["mfa_required", "mfa_enrollment_required"]
    challenge_token: str
    expires_at: datetime
    membership_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class SelectionIssued:
    """More than one active membership: the caller picks a workspace first."""

    selection_token: str
    expires_at: datetime
    workspaces: list[WorkspaceEntry]


@dataclass(frozen=True, slots=True)
class EmailVerificationRequired:
    """The work email is not confirmed yet. No session, no MFA step — the caller
    must click the link mailed to ``email`` first. Carries the email only so the
    UI can say which address to check; it is never a credential."""

    email: str


AuthOutcome = SessionIssued | ChallengeIssued | SelectionIssued | EmailVerificationRequired


@dataclass(frozen=True, slots=True)
class EnrollmentStarted:
    challenge_token: str
    secret: str
    otpauth_url: str


@dataclass(frozen=True, slots=True)
class InvitationAccepted:
    tenant_name: str


@dataclass(frozen=True, slots=True)
class MemberView:
    membership_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    status: str
    role_names: list[str]
    group_names: list[str]
    mfa_enabled: bool
    # Last successful sign-in (credentials.last_login_at); None until they log in.
    last_login_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class InviteResult:
    member: MemberView
    invite_token: str
    accept_url: str


@dataclass(frozen=True, slots=True)
class GroupView:
    id: uuid.UUID
    name: str
    member_count: int
    member_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RoleView:
    id: uuid.UUID
    name: str
    built_in: bool
    permission_keys: list[str]
    assignment_count: int


# ---------------------------------------------------------------------------
# Provisioning gates — the seam tenancy left for this module (decision 10)
# ---------------------------------------------------------------------------


class IamMembershipGates:
    """The real answers to tenancy's provisioning questions.

    ``invite_admin`` completes when the tenant has at least one membership
    holding the built-in Admin role recorded (any status); ``verify`` completes
    only when such a membership is **active**. Wired once, below, via
    ``tenancy_service.use_gates``.
    """

    def __init__(self, roles: RoleRepository | None = None) -> None:
        self._roles = roles or RoleRepository()

    async def admin_membership_recorded(
        self, session: AsyncSession, tenant_id: uuid.UUID, /
    ) -> bool:
        return await self._roles.admin_membership_exists(session, tenant_id, require_active=False)

    async def active_admin_membership_exists(
        self, session: AsyncSession, tenant_id: uuid.UUID, /
    ) -> bool:
        return await self._roles.admin_membership_exists(session, tenant_id, require_active=True)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def _verification_message(email: str, link: str) -> OutboundEmail:
    """The signup email-verification message. Plain and unbranded for Week 1 —
    real templates and per-tenant from-addresses land with the notifications
    module. The link carries a single-purpose ``email_verify`` token."""
    subject = "Confirm your email for Verity"
    text = (
        "Welcome to Verity.\n\n"
        "Confirm this email address to finish setting up your workspace:\n"
        f"{link}\n\n"
        "The link expires in 24 hours. If you did not start a Verity trial, "
        "you can ignore this message."
    )
    html = (
        "<p>Welcome to Verity.</p>"
        "<p>Confirm this email address to finish setting up your workspace:</p>"
        f'<p><a href="{link}">Confirm my email</a></p>'
        "<p>The link expires in 24 hours. If you did not start a Verity trial, "
        "you can ignore this message.</p>"
    )
    return OutboundEmail(to=email, subject=subject, text=text, html=html)


def _password_reset_message(email: str, link: str) -> OutboundEmail:
    """The reset-link email. Plain and unbranded for Week 1, like verification."""
    subject = "Reset your Verity password"
    text = (
        "We received a request to reset your Verity password.\n\n"
        "Set a new password here:\n"
        f"{link}\n\n"
        "The link expires soon and works once. If you did not request this, you "
        "can ignore this message — your password stays unchanged."
    )
    html = (
        "<p>We received a request to reset your Verity password.</p>"
        f'<p><a href="{link}">Set a new password</a></p>'
        "<p>The link expires soon and works once. If you did not request this, "
        "you can ignore this message — your password stays unchanged.</p>"
    )
    return OutboundEmail(to=email, subject=subject, text=text, html=html)


def _password_changed_message(email: str) -> OutboundEmail:
    """Security notice after a successful reset, so a victim of email compromise
    notices a change they did not make."""
    subject = "Your Verity password was changed"
    text = (
        "Your Verity password was just changed, and any signed-in sessions were "
        "logged out.\n\nIf this was you, nothing more is needed. If it wasn't, "
        "contact your administrator immediately."
    )
    html = (
        "<p>Your Verity password was just changed, and any signed-in sessions "
        "were logged out.</p><p>If this was you, nothing more is needed. If it "
        "wasn't, contact your administrator immediately.</p>"
    )
    return OutboundEmail(to=email, subject=subject, text=text, html=html)


def _invite_message(to_email: str, invitee_name: str, accept_url: str) -> OutboundEmail:
    """The membership-invitation email, so an admin never has to hand the accept
    link over by hand. Plain and unbranded for Week 1 — real templates and
    per-tenant from-addresses arrive with the notifications module. The link
    carries a single-use ``invite`` token (7-day expiry)."""
    name = invitee_name.strip() or "there"
    subject = "You've been invited to Verity"
    text = (
        f"Hi {name},\n\n"
        "You've been invited to a workspace on Verity. Accept your invitation "
        "to get started:\n"
        f"{accept_url}\n\n"
        "The link expires in 7 days. If you weren't expecting this, you can "
        "ignore this message."
    )
    html = (
        f"<p>Hi {_html_escape(name)},</p>"
        "<p>You've been invited to a workspace on Verity. "
        "Accept your invitation to get started:</p>"
        f'<p><a href="{accept_url}">Accept invitation</a></p>'
        "<p>The link expires in 7 days. If you weren't expecting this, you can "
        "ignore this message.</p>"
    )
    return OutboundEmail(to=to_email, subject=subject, text=text, html=html)


class IamAuthService:
    """Signup, login, MFA, workspaces, and invitation acceptance.

    Each public method is one committed unit of work followed, on failure, by
    the raise: the audit row describing a refused attempt must outlive the
    refusal (the ``ProviderAuthService`` pattern).
    """

    def __init__(  # noqa: PLR0913, PLR0917 — injectable collaborators, all optional
        self,
        users: UserRepository | None = None,
        memberships: MembershipRepository | None = None,
        groups: GroupRepository | None = None,
        roles: RoleRepository | None = None,
        audit: AuditService | None = None,
        mailer: Mailer | None = None,
    ) -> None:
        self._users = users or UserRepository()
        self._memberships = memberships or MembershipRepository()
        self._groups = groups or GroupRepository()
        self._roles = roles or RoleRepository()
        self._settings = TenantSettingsRepository()
        self._audit = audit or audit_service
        self._mailer = mailer or get_mailer()

    # -- signup ----------------------------------------------------------------

    async def signup(  # noqa: PLR0913 — the signup contract's fields, all keyword-only
        self,
        *,
        company_name: str,
        full_name: str,
        email: str,
        password: str,
        accept_terms: bool = False,
        idempotency_key: str | None = None,
    ) -> AuthOutcome:
        """Trial signup: tenant, user, credentials, Admin membership, built-in
        roles, and a completed provisioning run — one transaction, no partials.

        The work email is unverified at this point, so the outcome is an
        email-verification step: a link is mailed, and clicking it is what opens
        MFA enrollment (the real order — verify the address, then set up the second
        factor). An idempotent replay returns the account's current step instead.
        """
        if not accept_terms:
            raise InvalidInput(detail="the Terms and Privacy Policy must be accepted")
        email_n = normalize_email(email)
        validate_password(password)
        base_slug, fallback_slug = derive_slug_candidates(company_name.strip(), email_n)

        outcome: AuthOutcome
        # (user_id, email) to mail a verification link to, sent after the commit.
        verify: tuple[uuid.UUID, str] | None = None
        async with provider_session_scope() as session:
            existing_user = await self._users.get_by_email(session, email_n)
            try:
                tenant = await tenancy_service.register_tenant(
                    session,
                    actor_admin_id=None,
                    profile=TenantRegistration(
                        legal_name=company_name.strip(), slug=base_slug, plan=TRIAL_PLAN
                    ),
                    idempotency_key=idempotency_key,
                )
            except SlugConflict:
                # Someone else's company owns the plain slug. Fall back to the
                # deterministic suffixed one, so an idempotent retry of this same
                # signup derives the same slug and matches its recorded key.
                tenant = await tenancy_service.register_tenant(
                    session,
                    actor_admin_id=None,
                    profile=TenantRegistration(
                        legal_name=company_name.strip(), slug=fallback_slug, plan=TRIAL_PLAN
                    ),
                    idempotency_key=idempotency_key,
                )
            # The deliberate dual-GUC exception: the tenant register was written
            # under the provider setting; the iam rows below are written under
            # the tenant policy of the tenant that now exists.
            await bind_tenant_context(session, tenant.id)

            if existing_user is not None:
                membership = await self._memberships.get_by_tenant_user(
                    session, tenant.id, existing_user.id
                )
                if membership is None:
                    # A different signup owns this email. Raising rolls the
                    # whole transaction back — including the tenant row above.
                    raise EmailTaken(detail=f"user {existing_user.id} already exists")
                # Idempotent replay: return the step the account is actually at —
                # still verify the email, or move on to MFA if it is done.
                if existing_user.email_verified_at is None:
                    verify = (existing_user.id, email_n)
                    outcome = EmailVerificationRequired(email=email_n)
                else:
                    credentials = await self._users.get_credentials(session, existing_user.id)
                    outcome = self._mfa_step(membership, existing_user, credentials)
            else:
                now = datetime.now(UTC)
                user = User(
                    id=uuid7(),
                    email=email_n,
                    full_name=full_name.strip(),
                    terms_accepted_at=now,
                )
                await self._users.add(session, user)
                credentials = Credentials(user_id=user.id, password_hash=hash_password(password))
                await self._users.add_credentials(session, credentials)

                membership = TenantMembership(
                    id=uuid7(),
                    tenant_id=tenant.id,
                    user_id=user.id,
                    status=MEMBERSHIP_STATUS_ACTIVE,
                    accepted_at=now,
                )
                await self._memberships.add(session, membership)

                actor = MembershipActor(membership.id)
                await self._record_create(
                    session, actor, tenant.id, "user", user.id, user, _USER_SNAPSHOT
                )
                await self._record_create(
                    session,
                    actor,
                    tenant.id,
                    "credentials",
                    user.id,
                    credentials,
                    _CREDENTIALS_SNAPSHOT,
                )
                await self._record_create(
                    session,
                    actor,
                    tenant.id,
                    "tenant_membership",
                    membership.id,
                    membership,
                    _MEMBERSHIP_SNAPSHOT,
                )

                roles = await iam_service.seed_built_in_roles(
                    session, tenant_id=tenant.id, actor=actor
                )
                assignment = RoleAssignment(
                    id=uuid7(),
                    tenant_id=tenant.id,
                    role_id=roles[ADMIN_ROLE_NAME].id,
                    assignee_type=ASSIGNEE_TYPE_MEMBERSHIP,
                    assignee_id=membership.id,
                )
                await self._roles.add_assignment(session, assignment)
                await self._record_create(
                    session,
                    actor,
                    tenant.id,
                    "role_assignment",
                    assignment.id,
                    assignment,
                    _ASSIGNMENT_SNAPSHOT,
                )

                # Decision 10: a self-signup tenant reaches `active` inside the
                # signup transaction — the gates above are now satisfied.
                await tenancy_service.run_provisioning(session, tenant_id=tenant.id, actor=actor)
                verify = (user.id, email_n)
                outcome = EmailVerificationRequired(email=email_n)

        # External call after commit: a slow mail server must never hold the
        # signup transaction open, and a failed send is recoverable by resend.
        if verify is not None:
            await self._send_verification_email(*verify)
        return outcome

    async def verify_email(self, *, token: str) -> AuthOutcome:
        """Confirm a work email from the signup link, then open MFA enrollment.

        Single-use in effect: the flip to ``email_verified_at`` is idempotent, so
        a second click simply returns the next step. Verifying is what lets the
        account reach a session at all.
        """
        try:
            claims = decode_token(token, expected_typ="email_verify", expected_plane="tenant")
        except InvalidToken as exc:
            raise InvalidInput(detail="verification token failed validation") from exc

        async with provider_session_scope() as session:
            user = await self._users.get(session, claims.subject)
            if user is None or user.status != USER_STATUS_ACTIVE:
                raise InvalidInput(detail=f"user {claims.subject} is gone or disabled")
            memberships = await self._active_memberships(session, user)
            if not memberships:
                raise InvalidInput(detail=f"user {user.id} has no membership to verify into")
            membership = memberships[0]
            await bind_tenant_context(session, membership.tenant_id)

            if user.email_verified_at is None:
                before = AuditService.snapshot(user, fields=_USER_SNAPSHOT)
                user.email_verified_at = datetime.now(UTC)
                await session.flush([user])
                await self._audit.record(
                    session,
                    action="update",
                    object_type="user",
                    object_id=user.id,
                    actor=MembershipActor(membership.id),
                    tenant_id=membership.tenant_id,
                    before=before,
                    after=AuditService.snapshot(user, fields=_USER_SNAPSHOT),
                )

            credentials = await self._users.get_credentials(session, user.id)
            # Verifying the email is the login: a session unless the tenant
            # requires admin MFA, in which case the enrollment/challenge step.
            return await self._post_password_step(session, membership, user, credentials)

    async def resend_verification(self, *, email: str) -> None:
        """Re-mail the verification link. Best-effort and quiet: it does the same
        observable thing whether or not an unverified account exists, so it never
        discloses which addresses are registered."""
        email_n = normalize_email(email)
        target: tuple[uuid.UUID, str] | None = None
        async with provider_session_scope() as session:
            user = await self._users.get_by_email(session, email_n)
            if (
                user is not None
                and user.status == USER_STATUS_ACTIVE
                and user.email_verified_at is None
            ):
                target = (user.id, email_n)
        if target is not None:
            await self._send_verification_email(*target)

    async def _send_verification_email(self, user_id: uuid.UUID, email: str) -> None:
        token = issue_token(subject=user_id, plane="tenant", typ="email_verify").token
        link = f"{get_settings().frontend_base_url}/verify-email?token={token}"
        await self._mailer.send(_verification_message(email, link))

    # -- password reset ------------------------------------------------------------

    async def request_password_reset(self, *, email: str) -> None:
        """Mail a reset link. Quiet by design: it does the same observable thing
        whether or not a resettable local account exists, so it never discloses
        which addresses are registered. A user with no local password (federated
        via their IdP) is silently skipped — their reset lives on that IdP."""
        email_n = normalize_email(email)
        target: tuple[uuid.UUID, str] | None = None
        async with provider_session_scope() as session:
            user = await self._users.get_by_email(session, email_n)
            if user is not None and user.status == USER_STATUS_ACTIVE:
                credentials = await self._users.get_credentials(session, user.id)
                if credentials is not None:
                    target = (user.id, email_n)
        # After the read closes; a slow mail server never holds a transaction.
        if target is not None:
            await self._send_password_reset_email(*target)

    async def _send_password_reset_email(self, user_id: uuid.UUID, email: str) -> None:
        token = issue_token(subject=user_id, plane="tenant", typ="password_reset").token
        base = get_settings().frontend_base_url.rstrip("/")
        link = f"{base}/reset-password?token={token}"
        await self._mailer.send(_password_reset_message(email, link))

    async def reset_password(self, *, token: str, new_password: str) -> None:
        """Redeem a reset link and set a new password. Bumping
        ``credentials_changed_at`` both revokes every existing session and makes
        the link single-use — a link issued before the last change is spent. MFA
        is untouched: the user still completes it at next sign-in."""
        try:
            claims = decode_token(token, expected_typ="password_reset", expected_plane="tenant")
        except InvalidToken as exc:
            raise InvalidInput(detail="password-reset token failed validation") from exc
        validate_password(new_password)

        notify: str | None = None
        async with provider_session_scope() as session:
            user = await self._users.get(session, claims.subject)
            if user is None or user.status != USER_STATUS_ACTIVE:
                raise InvalidInput(detail="this reset link is no longer valid")
            credentials = await self._users.get_credentials_for_update(session, user.id)
            if credentials is None:
                raise InvalidInput(detail="this account has no password to reset")
            if (
                credentials.credentials_changed_at is not None
                and claims.issued_at < credentials.credentials_changed_at
            ):
                raise InvalidInput(detail="this reset link has already been used")

            credentials.password_hash = hash_password(new_password)
            credentials.credentials_changed_at = datetime.now(UTC)
            # Clicking an emailed link proves the address: a never-verified user
            # who resets is verified by construction.
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
                await session.flush([user])
            membership = next(iter(await self._active_memberships(session, user)), None)
            if membership is not None:
                await self._audit.record(
                    session,
                    action="update",
                    object_type="credentials",
                    object_id=user.id,
                    actor=MembershipActor(membership.id),
                    tenant_id=membership.tenant_id,
                    before=None,
                    after={"event": "password_reset"},
                )
            notify = user.email
        if notify is not None:
            await self._mailer.send(_password_changed_message(notify))

    # -- login -------------------------------------------------------------------

    async def login(self, *, email: str, password: str) -> AuthOutcome:
        """Password first, then whatever the resolved membership demands.

        The unknown-email path verifies against a dummy hash inside
        ``core.security.verify_password``, so its wall time matches a wrong
        password and the route does not disclose which addresses exist.
        """
        email_n = normalize_email(email)
        outcome: AuthOutcome | None = None
        async with provider_session_scope() as session:
            user = await self._users.get_by_email(session, email_n)
            credentials = (
                await self._users.get_credentials(session, user.id) if user is not None else None
            )
            verification = verify_password(
                credentials.password_hash if credentials is not None else "", password
            )
            if user is None or credentials is None:
                await self._record_attempt(
                    session,
                    actor=System(),
                    tenant_id=None,
                    outcome="failed_password",
                    reason="unknown_email",
                )
            elif not verification.ok:
                actor, stream = await self._attempt_attribution(session, user)
                await self._record_attempt(
                    session, actor=actor, tenant_id=stream, outcome="failed_password"
                )
            elif user.status != USER_STATUS_ACTIVE:
                actor, stream = await self._attempt_attribution(session, user)
                await self._record_attempt(
                    session, actor=actor, tenant_id=stream, outcome="user_disabled"
                )
            elif user.email_verified_at is None:
                # No session until the work email is confirmed. The link was mailed
                # at signup; a lost one is re-sent via the explicit resend, not here
                # — so the client can poll login without spawning an email each time.
                actor, stream = await self._attempt_attribution(session, user)
                await self._record_attempt(
                    session, actor=actor, tenant_id=stream, outcome="email_unverified"
                )
                outcome = EmailVerificationRequired(email=email_n)
            else:
                if verification.needs_rehash:
                    # The credential is unchanged; its parameters caught up with
                    # the pinned configuration. Not a separate auditable action.
                    credentials.password_hash = hash_password(password)
                memberships = await self._active_memberships(session, user)
                if not memberships:
                    await self._record_attempt(
                        session,
                        actor=System(),
                        tenant_id=None,
                        outcome="no_active_membership",
                    )
                elif len(memberships) > 1:
                    issued = issue_token(subject=user.id, plane="tenant", typ="selection")
                    outcome = SelectionIssued(
                        selection_token=issued.token,
                        expires_at=issued.expires_at,
                        workspaces=await self._workspaces(session, user),
                    )
                else:
                    outcome = await self._post_password_step(
                        session, memberships[0], user, credentials
                    )
        if outcome is None:
            raise AuthenticationRequired(detail=_UNIFORM_LOGIN_DETAIL)
        return outcome

    # -- MFA -----------------------------------------------------------------------

    async def verify_mfa(
        self,
        *,
        challenge_token: str,
        code: str | None = None,
        recovery_code: str | None = None,
    ) -> SessionIssued:
        """Exchange a challenge plus a second factor for a session.

        A TOTP code at or before the stored counter is refused — replay
        protection — and a recovery code is consumed by the check that accepts it.
        """
        if (code is None) == (recovery_code is None):
            raise InvalidInput(detail="exactly one of code and recovery_code is required")
        claims = decode_token(challenge_token, expected_typ="challenge", expected_plane="tenant")

        grant: SessionIssued | None = None
        async with provider_session_scope() as session:
            # Lock the credentials row: the counter/recovery guard-then-update below
            # must be serialized so a replayed code cannot mint two sessions (FIX 3).
            loaded = await self._load_challenge_subject(session, claims.subject, for_update=True)
            if loaded is None:
                await self._record_attempt(
                    session,
                    actor=System(),
                    tenant_id=None,
                    outcome="failed_totp",
                    reason="unknown_membership",
                )
            else:
                membership, user, credentials = loaded
                if not user.mfa_enabled or credentials.mfa_secret_encrypted is None:
                    # A challenge for an unenrolled account only opens enrollment;
                    # no code was checked against a secret, nothing to record.
                    pass
                elif code is not None:
                    secret = self._decrypt_mfa_secret(user, credentials)
                    result = (
                        TotpVerification(ok=False, counter=None)
                        if secret is None
                        else verify_totp(secret, code, credentials.last_totp_counter)
                    )
                    if result.ok:
                        credentials.last_totp_counter = result.counter
                        grant = await self._grant_session(
                            session, membership, user, credentials, method="totp"
                        )
                    else:
                        await self._record_attempt(
                            session,
                            actor=MembershipActor(membership.id),
                            tenant_id=membership.tenant_id,
                            outcome="failed_totp",
                            reason="secret_unreadable" if secret is None else None,
                        )
                elif recovery_code is not None:
                    remaining = consume_recovery_code(
                        credentials.recovery_codes_encrypted or [], recovery_code
                    )
                    if remaining is None:
                        await self._record_attempt(
                            session,
                            actor=MembershipActor(membership.id),
                            tenant_id=membership.tenant_id,
                            outcome="failed_recovery_code",
                        )
                    else:
                        credentials.recovery_codes_encrypted = remaining
                        grant = await self._grant_session(
                            session, membership, user, credentials, method="recovery_code"
                        )
        if grant is None:
            raise AuthenticationRequired(detail="tenant MFA verification refused")
        return grant

    async def start_enrollment(self, *, challenge_token: str) -> EnrollmentStarted:
        """Mint and store a pending TOTP secret; enabled only when confirmed.

        Re-running before confirmation replaces the pending secret. An account
        whose MFA is already enabled is refused — a re-enrollment resets a
        credential and Week 1 has no audited flow for that.
        """
        claims = decode_token(challenge_token, expected_typ="challenge", expected_plane="tenant")
        conflict = False
        started: EnrollmentStarted | None = None
        async with provider_session_scope() as session:
            loaded = await self._load_challenge_subject(session, claims.subject)
            if loaded is None:
                pass
            else:
                membership, user, credentials = loaded
                if user.mfa_enabled:
                    conflict = True
                else:
                    before = AuditService.snapshot(credentials, fields=_CREDENTIALS_SNAPSHOT)
                    secret = new_totp_secret()
                    credentials.mfa_secret_encrypted = get_secret_box().encrypt(
                        secret, aad=_credentials_aad(user.id)
                    )
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="credentials",
                        object_id=user.id,
                        actor=MembershipActor(membership.id),
                        tenant_id=membership.tenant_id,
                        before=before,
                        after=AuditService.snapshot(credentials, fields=_CREDENTIALS_SNAPSHOT),
                    )
                    started = EnrollmentStarted(
                        challenge_token=challenge_token,
                        secret=secret,
                        otpauth_url=totp_provisioning_uri(secret, user.email),
                    )
        if conflict:
            raise MfaEnrollmentConflict(detail="MFA is already enabled for this user")
        if started is None:
            raise AuthenticationRequired(detail="enrollment refused: subject missing or disabled")
        return started

    async def confirm_enrollment(self, *, challenge_token: str, code: str) -> SessionIssued:
        """Prove the authenticator holds the pending secret, then enable MFA.

        On success, in one transaction: MFA enabled, the accepted counter stored,
        recovery codes minted and hashed, the enrollment and the login audited.
        The plaintext codes leave the process exactly once, in the return value.
        """
        claims = decode_token(challenge_token, expected_typ="challenge", expected_plane="tenant")
        conflict = False
        grant: SessionIssued | None = None
        async with provider_session_scope() as session:
            loaded = await self._load_challenge_subject(session, claims.subject)
            if loaded is None:
                pass
            else:
                membership, user, credentials = loaded
                if user.mfa_enabled or credentials.mfa_secret_encrypted is None:
                    conflict = True
                else:
                    secret = self._decrypt_mfa_secret(user, credentials)
                    result = (
                        TotpVerification(ok=False, counter=None)
                        if secret is None
                        else verify_totp(secret, code, credentials.last_totp_counter)
                    )
                    if not result.ok:
                        await self._record_attempt(
                            session,
                            actor=MembershipActor(membership.id),
                            tenant_id=membership.tenant_id,
                            outcome="failed_totp",
                            reason="secret_unreadable" if secret is None else None,
                        )
                    else:
                        user.mfa_enabled = True
                        credentials.mfa_enrolled_at = datetime.now(UTC)
                        credentials.last_totp_counter = result.counter
                        codes = generate_recovery_codes()
                        credentials.recovery_codes_encrypted = hash_recovery_codes(codes)
                        await self._audit.record(
                            session,
                            action="create",
                            object_type="mfa_enrollment",
                            object_id=uuid7(),
                            actor=MembershipActor(membership.id),
                            tenant_id=membership.tenant_id,
                            after={"outcome": "completed"},
                        )
                        issued = await self._grant_session(
                            session, membership, user, credentials, method="totp"
                        )
                        grant = SessionIssued(
                            token=issued.token,
                            expires_at=issued.expires_at,
                            principal=issued.principal,
                            workspaces=issued.workspaces,
                            recovery_codes=codes,
                        )
        if conflict:
            raise MfaEnrollmentConflict(
                detail="already enabled, or confirmation before enrollment started"
            )
        if grant is None:
            raise AuthenticationRequired(detail="tenant MFA confirmation refused")
        return grant

    # -- workspaces -----------------------------------------------------------------

    async def list_workspaces(self, *, user_id: uuid.UUID) -> list[WorkspaceEntry]:
        async with provider_session_scope() as session:
            user = await self._users.get(session, user_id)
            if user is None:
                raise AuthenticationRequired(detail=f"user {user_id} not found")
            return await self._workspaces(session, user)

    async def select_workspace(
        self, *, selection_token: str, membership_id: uuid.UUID
    ) -> AuthOutcome:
        """Selection token (subject: the user) plus a membership choice → the
        next step for that membership: a session, or its MFA challenge."""
        claims = decode_token(selection_token, expected_typ="selection", expected_plane="tenant")
        async with provider_session_scope() as session:
            return await self._step_into_membership(
                session, user_id=claims.subject, membership_id=membership_id
            )

    async def switch_workspace(
        self, *, user_id: uuid.UUID, membership_id: uuid.UUID
    ) -> AuthOutcome:
        """A new session for another of the caller's memberships — never a
        parameter on the old one. Audited in the **target** tenant's stream;
        MFA rules apply to the target membership (decision 2)."""
        async with provider_session_scope() as session:
            return await self._step_into_membership(
                session, user_id=user_id, membership_id=membership_id
            )

    async def _step_into_membership(
        self, session: AsyncSession, *, user_id: uuid.UUID, membership_id: uuid.UUID
    ) -> AuthOutcome:
        membership = await self._memberships.get(session, membership_id)
        if (
            membership is None
            or membership.user_id != user_id
            or membership.status != MEMBERSHIP_STATUS_ACTIVE
        ):
            # Not this user's membership, or not usable: absent, not forbidden.
            raise NotFound(detail=f"membership {membership_id} not usable for user {user_id}")
        user = await self._users.get(session, user_id)
        if user is None or user.status != USER_STATUS_ACTIVE:
            raise AuthenticationRequired(detail=f"user {user_id} missing or disabled")
        if not await self._tenant_is_active(session, membership.tenant_id):
            raise NotFound(detail=f"tenant {membership.tenant_id} is not active")
        if not await self._has_active_role(session, membership):
            # The membership's only role assignment is out of window (the expired
            # guest-auditor): not usable, and absent rather than forbidden.
            raise NotFound(
                detail=f"membership {membership_id} holds no in-window role for user {user_id}"
            )
        credentials = await self._users.get_credentials(session, user.id)
        return await self._post_password_step(session, membership, user, credentials)

    # -- invitations -------------------------------------------------------------------

    async def accept_invitation(
        self, *, token: str, full_name: str | None = None, password: str | None = None
    ) -> InvitationAccepted:
        """Decision 15: unauthenticated, single-use. New users supply a name and
        password (their credentials are created here); existing users accept with
        the token alone, and any extra fields they send are ignored. Accepting
        flips the membership ``invited → active`` — that flip is the consumption
        record, so a second accept of the same membership is a 409.

        Afterwards the inviting tenant's provisioning verify hook runs: a
        provider-created tenant whose first admin just accepted reaches
        ``active`` here, in the same transaction (decision 10).
        """
        try:
            claims = decode_token(token, expected_typ="invite", expected_plane="tenant")
        except InvalidToken as exc:
            raise InvalidInvite(detail="invite token failed validation") from exc

        async with provider_session_scope() as session:
            membership = await self._memberships.get(session, claims.subject)
            if membership is None:
                raise InvalidInvite(detail=f"membership {claims.subject} is gone")
            if membership.status == MEMBERSHIP_STATUS_ACTIVE:
                raise InviteAlreadyAccepted(detail=f"membership {membership.id} already active")
            if membership.status == MEMBERSHIP_STATUS_DISABLED:
                raise InvalidInvite(detail=f"membership {membership.id} is disabled")
            user = await self._users.get(session, membership.user_id)
            if user is None or user.status != USER_STATUS_ACTIVE:
                raise InvalidInvite(detail=f"user for membership {membership.id} unusable")

            await bind_tenant_context(session, membership.tenant_id)
            actor = MembershipActor(membership.id)

            credentials = await self._users.get_credentials(session, user.id)
            if credentials is None:
                if password is None:
                    raise InvalidInput(detail="a new user must set a password on accept")
                validate_password(password)
                # Accepting an invitation proves control of the address it was
                # issued for, so a new invited user is email-verified by that act —
                # no separate verification step, unlike self-service signup.
                user.email_verified_at = datetime.now(UTC)
                if full_name is not None and full_name.strip():
                    # The global users row changes; it is a state change and is audited
                    # like every other write here, in this tenant's stream.
                    user_before = AuditService.snapshot(user, fields=_USER_SNAPSHOT)
                    user.full_name = full_name.strip()
                    await session.flush([user])
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="user",
                        object_id=user.id,
                        actor=actor,
                        tenant_id=membership.tenant_id,
                        before=user_before,
                        after=AuditService.snapshot(user, fields=_USER_SNAPSHOT),
                    )
                credentials = Credentials(user_id=user.id, password_hash=hash_password(password))
                await self._users.add_credentials(session, credentials)
                await self._record_create(
                    session,
                    actor,
                    membership.tenant_id,
                    "credentials",
                    user.id,
                    credentials,
                    _CREDENTIALS_SNAPSHOT,
                )

            before = AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT)
            membership.status = MEMBERSHIP_STATUS_ACTIVE
            membership.accepted_at = datetime.now(UTC)
            await session.flush([membership])
            await session.refresh(membership)
            await self._audit.record(
                session,
                action="update",
                object_type="tenant_membership",
                object_id=membership.id,
                actor=actor,
                tenant_id=membership.tenant_id,
                before=before,
                after=AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT),
            )

            # The verify hook: an invited-then-accepted admin may complete
            # provisioning and flip a provider-created tenant to active.
            await tenancy_service.run_provisioning(
                session, tenant_id=membership.tenant_id, actor=actor
            )
            tenant = await tenancy_service.get_tenant(session, membership.tenant_id)
            return InvitationAccepted(
                tenant_name=tenant_display_name(tenant.legal_name, tenant.trading_name)
            )

    async def logout(self, *, token: str, membership_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Record a sign-out as ``delete`` on the session object (decisions 2 and 17).

        Sessions are stateless — there is no server-side token to revoke — so this
        writes the audit row and nothing else: the trail is the point. The ``jti`` in
        the presented token is the session's identity and the object_id, matching the
        ``create``-on-``session`` written when it was issued.
        """
        claims = decode_token(token, expected_typ="session", expected_plane="tenant")
        async with provider_session_scope() as session:
            await bind_tenant_context(session, tenant_id)
            await self._audit.record(
                session,
                action="delete",
                object_type="session",
                object_id=claims.jti,
                actor=MembershipActor(membership_id),
                tenant_id=tenant_id,
                before={"membership_id": str(membership_id)},
                after=None,
            )

    # -- shared internals -----------------------------------------------------------

    async def _post_password_step(
        self,
        session: AsyncSession,
        membership: TenantMembership,
        user: User,
        credentials: Credentials | None,
    ) -> AuthOutcome:
        """After the password (or an existing session) has vouched for the user:
        either the membership demands TOTP, or a session is granted."""
        if await self._requires_mfa(session, membership):
            return self._mfa_step(membership, user, credentials)
        if credentials is None:
            raise AuthenticationRequired(detail=f"user {user.id} has no credentials")
        return await self._grant_session(session, membership, user, credentials, method="password")

    def _mfa_step(
        self,
        membership: TenantMembership,
        user: User,
        credentials: Credentials | None,
    ) -> ChallengeIssued:
        issued = issue_token(subject=membership.id, plane="tenant", typ="challenge")
        enrolled = (
            user.mfa_enabled
            and credentials is not None
            and credentials.mfa_secret_encrypted is not None
        )
        return ChallengeIssued(
            next_step="mfa_required" if enrolled else "mfa_enrollment_required",
            challenge_token=issued.token,
            expires_at=issued.expires_at,
            membership_id=membership.id,
        )

    async def _requires_mfa(self, session: AsyncSession, membership: TenantMembership) -> bool:
        """TOTP is required only when the tenant has turned it on *and* the
        membership holds the built-in Admin role. Off by default — a trial admin
        signs up with email verification alone and enables MFA later if they want."""
        if not await self._settings.require_admin_mfa(session, membership.tenant_id):
            return False
        grants, group_ids = await fetch_grants_for_membership(
            session, tenant_id=membership.tenant_id, membership_id=membership.id
        )
        role_ids = active_role_ids(
            grants,
            membership_id=membership.id,
            group_ids=group_ids,
            today=datetime.now(UTC).date(),
        )
        if not role_ids:
            return False
        roles = await self._roles.get_many(session, membership.tenant_id, list(role_ids))
        return any(role.built_in and role.name == ADMIN_ROLE_NAME for role in roles)

    async def _grant_session(
        self,
        session: AsyncSession,
        membership: TenantMembership,
        user: User,
        credentials: Credentials,
        *,
        method: str,
    ) -> SessionIssued:
        """Issue the session token and write the login's audit row (decision 2:
        ``create`` on ``session``, object id = the token's ``jti``, in the
        membership's tenant stream)."""
        issued: IssuedToken = issue_token(subject=membership.id, plane="tenant", typ="session")
        credentials.last_login_at = datetime.now(UTC)
        await self._audit.record(
            session,
            action="create",
            object_type="session",
            object_id=issued.jti,
            actor=MembershipActor(membership.id),
            tenant_id=membership.tenant_id,
            after={"method": method, "plane": "tenant"},
        )
        principal = await self._principal_snapshot(session, membership, user)
        workspaces = await self._workspaces(session, user)
        return SessionIssued(
            token=issued.token,
            expires_at=issued.expires_at,
            principal=principal,
            workspaces=workspaces,
        )

    async def _principal_snapshot(
        self, session: AsyncSession, membership: TenantMembership, user: User
    ) -> PrincipalSnapshot:
        permissions = await resolve_effective_permissions(
            session, tenant_id=membership.tenant_id, membership_id=membership.id
        )
        tenant = await tenancy_service.get_tenant(session, membership.tenant_id)
        return PrincipalSnapshot(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            user_status=user.status,
            mfa_enabled=user.mfa_enabled,
            membership_id=membership.id,
            tenant_id=membership.tenant_id,
            tenant_name=tenant_display_name(tenant.legal_name, tenant.trading_name),
            permissions=sorted(permissions),
            role_names=await self._direct_role_names(session, membership),
        )

    async def _direct_role_names(
        self, session: AsyncSession, membership: TenantMembership
    ) -> list[str]:
        assignments = await self._roles.list_direct_for_membership(
            session, membership.tenant_id, membership.id
        )
        today = datetime.now(UTC).date()
        role_ids = [
            a.role_id
            for a in assignments
            if assignment_window_active(a.valid_from, a.valid_until, today)
        ]
        roles = await self._roles.get_many(session, membership.tenant_id, role_ids)
        return sorted(role.name for role in roles)

    async def _workspaces(self, session: AsyncSession, user: User) -> list[WorkspaceEntry]:
        entries: list[WorkspaceEntry] = []
        for membership in await self._active_memberships(session, user):
            tenant = await tenancy_service.get_tenant(session, membership.tenant_id)
            role_names = await self._direct_role_names(session, membership)
            role_name = (
                ADMIN_ROLE_NAME
                if ADMIN_ROLE_NAME in role_names
                else (role_names[0] if role_names else "Member")
            )
            entries.append(
                WorkspaceEntry(
                    membership_id=membership.id,
                    tenant_id=membership.tenant_id,
                    tenant_name=tenant_display_name(tenant.legal_name, tenant.trading_name),
                    tenant_slug=tenant.slug,
                    role_name=role_name,
                    status=membership.status,
                )
            )
        return entries

    async def _active_memberships(
        self, session: AsyncSession, user: User
    ) -> list[TenantMembership]:
        """The memberships a session could bind: active rows, in active tenants,
        that hold at least one in-window role assignment.

        The role-window check is the guest-auditor expiry guard (spec: "The
        membership is disabled or outside its window" → 401): a membership whose
        sole role assignment has expired grants nothing, so it must not yield a
        session with empty roles. The window logic is core.deps', resolved against
        today (decision 10 — a provisioning or suspended tenant also refuses login)."""
        memberships = [
            m
            for m in await self._memberships.list_for_user(session, user.id)
            if m.status == MEMBERSHIP_STATUS_ACTIVE
        ]
        usable: list[TenantMembership] = []
        for membership in memberships:
            if not await self._tenant_is_active(session, membership.tenant_id):
                continue
            if not await self._has_active_role(session, membership):
                continue
            usable.append(membership)
        return usable

    async def _has_active_role(self, session: AsyncSession, membership: TenantMembership) -> bool:
        """Whether the membership holds at least one role assignment inside its
        window right now — direct or via a group (core.deps' resolution). An
        empty result is the expired guest-auditor: the membership grants nothing."""
        grants, group_ids = await fetch_grants_for_membership(
            session, tenant_id=membership.tenant_id, membership_id=membership.id
        )
        return bool(
            active_role_ids(
                grants,
                membership_id=membership.id,
                group_ids=group_ids,
                today=datetime.now(UTC).date(),
            )
        )

    async def _tenant_is_active(self, session: AsyncSession, tenant_id: uuid.UUID) -> bool:
        tenant = await tenancy_service.get_tenant(session, tenant_id)
        return bool(tenant.status == _TENANT_STATUS_ACTIVE)

    async def _load_challenge_subject(
        self, session: AsyncSession, membership_id: uuid.UUID, *, for_update: bool = False
    ) -> tuple[TenantMembership, User, Credentials] | None:
        """The rows behind a challenge token, or ``None`` when any of them no
        longer permits authentication — checked per request, not per token.

        ``for_update`` takes a row lock on the credentials row (the verify path),
        so the TOTP-counter / recovery-code guard-then-update is serialized."""
        membership = await self._memberships.get(session, membership_id)
        if membership is None or membership.status != MEMBERSHIP_STATUS_ACTIVE:
            return None
        if not await self._tenant_is_active(session, membership.tenant_id):
            return None
        user = await self._users.get(session, membership.user_id)
        if user is None or user.status != USER_STATUS_ACTIVE:
            return None
        credentials = (
            await self._users.get_credentials_for_update(session, user.id)
            if for_update
            else await self._users.get_credentials(session, user.id)
        )
        if credentials is None:
            return None
        return membership, user, credentials

    async def _attempt_attribution(
        self, session: AsyncSession, user: User
    ) -> tuple[Actor, uuid.UUID | None]:
        """Decision 3: the actor is the matched membership when the identity
        resolves to exactly one; otherwise the event is unattributable to a
        tenant stream and is recorded as system on the provider stream."""
        memberships = await self._memberships.list_for_user(session, user.id)
        active = [m for m in memberships if m.status == MEMBERSHIP_STATUS_ACTIVE]
        if len(active) == 1:
            return MembershipActor(active[0].id), active[0].tenant_id
        return System(), None

    @staticmethod
    def _decrypt_mfa_secret(user: User, credentials: Credentials) -> str | None:
        """The stored TOTP secret, or ``None`` when its ciphertext refuses to
        authenticate under this row's AAD — moved, corrupted, or tampered with —
        in which case the login fails closed as an ordinary refusal."""
        if credentials.mfa_secret_encrypted is None:
            return None
        try:
            return get_secret_box().decrypt(
                credentials.mfa_secret_encrypted, aad=_credentials_aad(user.id)
            )
        except CryptoError:
            return None

    async def _record_attempt(
        self,
        session: AsyncSession,
        *,
        actor: Actor,
        tenant_id: uuid.UUID | None,
        outcome: str,
        reason: str | None = None,
    ) -> None:
        """Decision 3: a failed attempt is an event — ``create`` on
        ``auth_attempt``, minted id, minimal outcome map, never an email."""
        after: dict[str, str] = {"outcome": outcome}
        if reason is not None:
            after["reason"] = reason
        await self._audit.record(
            session,
            action="create",
            object_type="auth_attempt",
            object_id=uuid7(),
            actor=actor,
            tenant_id=tenant_id,
            after=after,
        )

    async def _record_create(  # noqa: PLR0913, PLR0917 — one audit row's facts
        self,
        session: AsyncSession,
        actor: Actor,
        tenant_id: uuid.UUID,
        object_type: str,
        object_id: uuid.UUID,
        instance: object,
        fields: tuple[str, ...],
    ) -> None:
        await self._audit.record(
            session,
            action="create",
            object_type=object_type,
            object_id=object_id,
            actor=actor,
            tenant_id=tenant_id,
            after=AuditService.snapshot(instance, fields=fields),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Management — members, groups, roles, on the caller's tenant-bound session
# ---------------------------------------------------------------------------


class IamService:
    """Membership, group, and role management behind ``require(...)``.

    Methods run on the caller's session and never commit; every write lands its
    audit rows on the same session. Every by-id lookup filters ``tenant_id``
    explicitly, so a cross-tenant identifier reads as absent — 404, never 403.
    """

    def __init__(  # noqa: PLR0913, PLR0917 — injectable collaborators, all optional
        self,
        users: UserRepository | None = None,
        memberships: MembershipRepository | None = None,
        groups: GroupRepository | None = None,
        roles: RoleRepository | None = None,
        audit: AuditService | None = None,
        mailer: Mailer | None = None,
    ) -> None:
        self._users = users or UserRepository()
        self._memberships = memberships or MembershipRepository()
        self._groups = groups or GroupRepository()
        self._roles = roles or RoleRepository()
        self._settings = TenantSettingsRepository()
        self._audit = audit or audit_service
        self._mailer = mailer or get_mailer()

    # -- security settings ------------------------------------------------------

    async def get_require_admin_mfa(self, session: AsyncSession, tenant_id: uuid.UUID) -> bool:
        return await self._settings.require_admin_mfa(session, tenant_id)

    async def set_require_admin_mfa(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        value: bool,
    ) -> bool:
        """Turn the admin-MFA requirement on or off. Audited; a no-op change
        writes nothing."""
        before = await self._settings.require_admin_mfa(session, tenant_id)
        if before == value:
            return value
        row = await self._settings.set_require_admin_mfa(session, tenant_id, value)
        await self._audit.record(
            session,
            action="update",
            object_type="tenant_settings",
            object_id=tenant_id,
            actor=MembershipActor(actor_membership_id),
            tenant_id=tenant_id,
            before={"require_admin_mfa": before},
            after={"require_admin_mfa": row.require_admin_mfa},
        )
        return row.require_admin_mfa

    # -- built-in roles ---------------------------------------------------------

    async def seed_built_in_roles(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor
    ) -> dict[str, Role]:
        """Create whichever of the five built-in roles are missing. Idempotent:
        runs on both the signup and the provider-registration paths (decision 14),
        and a rerun creates and audits nothing."""
        existing = {
            role.name: role for role in await self._roles.list_for_tenant(session, tenant_id)
        }
        shipped_keys = await self._roles.existing_permission_keys(session)
        for name, keys in BUILT_IN_ROLE_KEYS.items():
            if name in existing:
                continue
            role = Role(id=uuid7(), tenant_id=tenant_id, name=name, built_in=True)
            await self._roles.add(session, role)
            attach = [] if keys is None else sorted(k for k in keys if k in shipped_keys)
            if attach:
                await self._roles.add_permission_keys(session, role.id, attach)
            snapshot = AuditService.snapshot(role, fields=_ROLE_SNAPSHOT)
            snapshot["permission_keys"] = attach
            await self._audit.record(
                session,
                action="create",
                object_type="role",
                object_id=role.id,
                actor=actor,
                tenant_id=tenant_id,
                after=snapshot,
            )
            existing[name] = role
        return existing

    # -- members -----------------------------------------------------------------

    async def list_members(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[MemberView]:
        memberships = await self._memberships.list_for_tenant(session, tenant_id)
        users = {
            user.id: user
            for user in await self._users.get_many(session, [m.user_id for m in memberships])
        }
        role_names = await self._roles.direct_role_names_by_membership(session, tenant_id)
        group_names = await self._groups.group_names_by_membership(session, tenant_id)
        last_login = await self._users.last_login_by_users(session, list(users))
        views: list[MemberView] = []
        for membership in memberships:
            user = users.get(membership.user_id)
            if user is None:
                continue
            views.append(
                self._member_view(
                    membership,
                    user,
                    role_names.get(membership.id, []),
                    group_names.get(membership.id, []),
                    last_login.get(user.id),
                )
            )
        return views

    async def invite_member(  # noqa: PLR0913 — the invite contract's fields, no more
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        email: str,
        full_name: str,
        role_id: uuid.UUID,
        valid_from: date | None = None,
        valid_until: date | None = None,
    ) -> InviteResult:
        """Idempotent on ``(tenant_id, user_id)``: a pending invite is re-issued
        with a fresh token, a disabled membership is reactivated (audited as an
        update), and an active membership is a 409 — the frontend's
        ``already_member``. The optional window lands on the role assignment:
        the guest-auditor path."""
        _validate_window(valid_from, valid_until)
        role = await self._roles.get_for_tenant(session, tenant_id, role_id)
        if role is None:
            raise NotFound(detail=f"role {role_id} not in tenant {tenant_id}")
        actor = MembershipActor(actor_membership_id)
        email_n = normalize_email(email)

        user = await self._users.get_by_email(session, email_n)
        membership = (
            await self._memberships.get_by_tenant_user(session, tenant_id, user.id)
            if user is not None
            else None
        )
        if membership is not None and membership.status == MEMBERSHIP_STATUS_ACTIVE:
            raise AlreadyMember(detail=f"membership {membership.id} is already active")

        if user is None:
            # The person does not exist yet: a user row with **no credentials**.
            # Until they accept and set a password, login burns a dummy verify
            # and refuses — there is nothing to authenticate against.
            user = User(id=uuid7(), email=email_n, full_name=full_name.strip())
            await self._users.add(session, user)
            await self._record(
                session,
                actor,
                tenant_id,
                "create",
                "user",
                user.id,
                None,
                AuditService.snapshot(user, fields=_USER_SNAPSHOT),
            )

        now = datetime.now(UTC)
        if membership is None:
            membership = TenantMembership(
                id=uuid7(),
                tenant_id=tenant_id,
                user_id=user.id,
                status=MEMBERSHIP_STATUS_INVITED,
                invited_at=now,
            )
            await self._memberships.add(session, membership)
            await self._record(
                session,
                actor,
                tenant_id,
                "create",
                "tenant_membership",
                membership.id,
                None,
                AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT),
            )
            await self._assign_role(
                session,
                actor,
                tenant_id,
                role,
                membership.id,
                valid_from=valid_from,
                valid_until=valid_until,
            )
        elif membership.status == MEMBERSHIP_STATUS_DISABLED:
            before = AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT)
            membership.status = MEMBERSHIP_STATUS_INVITED
            membership.invited_at = now
            membership.disabled_at = None
            await session.flush([membership])
            await session.refresh(membership)
            await self._record(
                session,
                actor,
                tenant_id,
                "update",
                "tenant_membership",
                membership.id,
                before,
                AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT),
            )
            await self._replace_direct_roles(
                session,
                actor,
                tenant_id,
                membership.id,
                role,
                valid_from=valid_from,
                valid_until=valid_until,
            )
        # A membership still in 'invited' needs no row change: re-issuing the
        # token below is the whole re-invite.

        issued = issue_token(subject=membership.id, plane="tenant", typ="invite")
        accept_url = (
            f"{get_settings().frontend_base_url.rstrip('/')}/accept-invite?token={issued.token}"
        )
        member = await self._member_view_for(session, tenant_id, membership, user)
        # Email the accept link so the admin never has to hand it over by hand.
        # Best-effort: the mailer never raises and no-ops without SMTP; the link
        # is still returned as a fallback and for the "copy link" affordance.
        # ponytail: in-transaction send; move to the notifications outbox later.
        await self._mailer.send(_invite_message(email_n, full_name, accept_url))
        return InviteResult(member=member, invite_token=issued.token, accept_url=accept_url)

    async def disable_member(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> MemberView:
        membership = await self._memberships.get_for_tenant(session, tenant_id, membership_id)
        if membership is None:
            raise NotFound(detail=f"membership {membership_id} not in tenant {tenant_id}")
        user = await self._users.get(session, membership.user_id)
        if user is None:
            raise NotFound(detail=f"user behind membership {membership_id} is gone")
        if membership.status != MEMBERSHIP_STATUS_DISABLED:
            before = AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT)
            membership.status = MEMBERSHIP_STATUS_DISABLED
            membership.disabled_at = datetime.now(UTC)
            await session.flush([membership])
            await session.refresh(membership)
            await self._record(
                session,
                MembershipActor(actor_membership_id),
                tenant_id,
                "update",
                "tenant_membership",
                membership.id,
                before,
                AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT),
            )
        return await self._member_view_for(session, tenant_id, membership, user)

    async def set_member_roles(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> MemberView:
        """Replace the membership's direct role assignments with the one role
        the caller named — the Week 1 contract is single-role members."""
        membership = await self._memberships.get_for_tenant(session, tenant_id, membership_id)
        if membership is None:
            raise NotFound(detail=f"membership {membership_id} not in tenant {tenant_id}")
        user = await self._users.get(session, membership.user_id)
        if user is None:
            raise NotFound(detail=f"user behind membership {membership_id} is gone")
        role = await self._roles.get_for_tenant(session, tenant_id, role_id)
        if role is None:
            raise NotFound(detail=f"role {role_id} not in tenant {tenant_id}")
        actor = MembershipActor(actor_membership_id)
        await self._replace_direct_roles(session, actor, tenant_id, membership.id, role)
        return await self._member_view_for(session, tenant_id, membership, user)

    # -- groups --------------------------------------------------------------------

    async def list_groups(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[GroupView]:
        groups = await self._groups.list_for_tenant(session, tenant_id)
        members = await self._groups.list_members(session, tenant_id)
        by_group: dict[uuid.UUID, list[uuid.UUID]] = {}
        for row in members:
            by_group.setdefault(row.group_id, []).append(row.tenant_membership_id)
        return [self._group_view(group, by_group.get(group.id, [])) for group in groups]

    async def create_group(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        name: str,
    ) -> GroupView:
        name = name.strip()
        if await self._groups.get_by_name(session, tenant_id, name) is not None:
            raise NameConflict(detail=f"group {name!r} exists in tenant {tenant_id}")
        group = Group(id=uuid7(), tenant_id=tenant_id, name=name)
        await self._groups.add(session, group)
        await self._record(
            session,
            MembershipActor(actor_membership_id),
            tenant_id,
            "create",
            "group",
            group.id,
            None,
            AuditService.snapshot(group, fields=_GROUP_SNAPSHOT),
        )
        return self._group_view(group, [])

    async def add_group_member(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        group_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> GroupView:
        """Members are membership ids. An id that is not a membership **in this
        tenant** — another tenant's membership, or a users.id — reads as absent
        and is refused with 404; the schema-level walls (FKs, WITH CHECK) stand
        behind this check, not instead of it."""
        group = await self._groups.get_for_tenant(session, tenant_id, group_id)
        if group is None:
            raise NotFound(detail=f"group {group_id} not in tenant {tenant_id}")
        membership = await self._memberships.get_for_tenant(session, tenant_id, membership_id)
        if membership is None:
            raise NotFound(detail=f"membership {membership_id} not in tenant {tenant_id}")
        existing = await self._groups.get_member(session, tenant_id, group_id, membership_id)
        if existing is None:
            member = GroupMember(
                id=uuid7(),
                tenant_id=tenant_id,
                group_id=group_id,
                tenant_membership_id=membership_id,
            )
            await self._groups.add_member(session, member)
            await self._record(
                session,
                MembershipActor(actor_membership_id),
                tenant_id,
                "create",
                "group_member",
                member.id,
                None,
                AuditService.snapshot(member, fields=_GROUP_MEMBER_SNAPSHOT),
            )
        members = await self._groups.list_members(session, tenant_id)
        ids = [row.tenant_membership_id for row in members if row.group_id == group_id]
        return self._group_view(group, ids)

    # -- roles ----------------------------------------------------------------------

    async def list_roles(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[RoleView]:
        roles = await self._roles.list_for_tenant(session, tenant_id)
        keys_by_role = await self._roles.permission_keys_by_role(session, [r.id for r in roles])
        counts = await self._roles.assignment_counts(session, tenant_id)
        all_keys: list[str] | None = None
        views: list[RoleView] = []
        for role in roles:
            if role.built_in and role.name == ADMIN_ROLE_NAME:
                if all_keys is None:
                    all_keys = sorted(await self._roles.existing_permission_keys(session))
                keys = all_keys
            else:
                keys = keys_by_role.get(role.id, [])
            views.append(
                RoleView(
                    id=role.id,
                    name=role.name,
                    built_in=role.built_in,
                    permission_keys=keys,
                    assignment_count=counts.get(role.id, 0),
                )
            )
        return views

    async def create_role(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        name: str,
        permission_keys: list[str],
    ) -> RoleView:
        name = name.strip()
        if await self._roles.get_by_name(session, tenant_id, name) is not None:
            raise NameConflict(detail=f"role {name!r} exists in tenant {tenant_id}")
        requested = sorted(set(permission_keys))
        known = await self._roles.existing_permission_keys(session, requested)
        unknown = sorted(set(requested) - known)
        if unknown:
            raise InvalidInput(detail=f"unknown permission keys: {unknown}")
        role = Role(id=uuid7(), tenant_id=tenant_id, name=name, built_in=False)
        await self._roles.add(session, role)
        if requested:
            await self._roles.add_permission_keys(session, role.id, requested)
        snapshot = AuditService.snapshot(role, fields=_ROLE_SNAPSHOT)
        snapshot["permission_keys"] = requested
        await self._record(
            session,
            MembershipActor(actor_membership_id),
            tenant_id,
            "create",
            "role",
            role.id,
            None,
            snapshot,
        )
        return RoleView(
            id=role.id,
            name=role.name,
            built_in=role.built_in,
            permission_keys=requested,
            assignment_count=0,
        )

    async def update_role(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        role_id: uuid.UUID,
        name: str | None = None,
        permission_keys: list[str] | None = None,
    ) -> RoleView:
        """Rename a custom role and/or replace its permission set. Built-in roles
        are immutable — their keys resolve dynamically (Admin = every key). Only
        the fields supplied are touched; the change is audited before/after."""
        role = await self._roles.get_for_tenant(session, tenant_id, role_id)
        if role is None:
            raise NotFound(detail=f"role {role_id} not in tenant {tenant_id}")
        if role.built_in:
            raise BuiltInRoleImmutable(detail=f"role {role.name!r} is built-in")

        current_keys = sorted(
            (await self._roles.permission_keys_by_role(session, [role_id])).get(role_id, [])
        )
        before = AuditService.snapshot(role, fields=_ROLE_SNAPSHOT)
        before["permission_keys"] = current_keys

        if name is not None:
            new_name = name.strip()
            if not new_name:
                raise InvalidInput(detail="role name must not be empty")
            clash = await self._roles.get_by_name(session, tenant_id, new_name)
            if clash is not None and clash.id != role_id:
                raise NameConflict(detail=f"role {new_name!r} exists in tenant {tenant_id}")
            role.name = new_name
            await session.flush([role])

        final_keys = current_keys
        if permission_keys is not None:
            requested = sorted(set(permission_keys))
            known = await self._roles.existing_permission_keys(session, requested)
            unknown = sorted(set(requested) - known)
            if unknown:
                raise InvalidInput(detail=f"unknown permission keys: {unknown}")
            await self._roles.replace_permission_keys(session, role_id, requested)
            final_keys = requested

        after = AuditService.snapshot(role, fields=_ROLE_SNAPSHOT)
        after["permission_keys"] = final_keys
        await self._record(
            session,
            MembershipActor(actor_membership_id),
            tenant_id,
            "update",
            "role",
            role.id,
            before,
            after,
        )
        assignments = await self._roles.list_for_role(session, tenant_id, role_id)
        return RoleView(
            id=role.id,
            name=role.name,
            built_in=role.built_in,
            permission_keys=final_keys,
            assignment_count=len(assignments),
        )

    async def delete_role(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        """Custom roles only — RBAC configuration, not a compliance object, so a
        hard delete is permitted; every removed assignment is audited first."""
        role = await self._roles.get_for_tenant(session, tenant_id, role_id)
        if role is None:
            raise NotFound(detail=f"role {role_id} not in tenant {tenant_id}")
        if role.built_in:
            raise BuiltInRoleImmutable(detail=f"role {role.name!r} is built-in")
        actor = MembershipActor(actor_membership_id)
        for assignment in await self._roles.list_for_role(session, tenant_id, role_id):
            await self._record(
                session,
                actor,
                tenant_id,
                "delete",
                "role_assignment",
                assignment.id,
                AuditService.snapshot(assignment, fields=_ASSIGNMENT_SNAPSHOT),
                None,
            )
            await self._roles.delete_assignment(session, assignment)
        await self._record(
            session,
            actor,
            tenant_id,
            "delete",
            "role",
            role.id,
            AuditService.snapshot(role, fields=_ROLE_SNAPSHOT),
            None,
        )
        await self._roles.delete(session, role)

    async def create_assignment(  # noqa: PLR0913 — an assignment's own columns
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        role_id: uuid.UUID,
        assignee_type: str,
        assignee_id: uuid.UUID,
        engagement_id: uuid.UUID | None = None,
        valid_from: date | None = None,
        valid_until: date | None = None,
    ) -> RoleAssignment:
        """Assign a role to a membership or group, optionally engagement-scoped
        and time-boxed (the auditor path). A duplicate of the same
        ``(role, assignee, engagement)`` is a 409 — a second row would
        double-count in the permission union."""
        _validate_window(valid_from, valid_until)
        role = await self._roles.get_for_tenant(session, tenant_id, role_id)
        if role is None:
            raise NotFound(detail=f"role {role_id} not in tenant {tenant_id}")
        if assignee_type == ASSIGNEE_TYPE_MEMBERSHIP:
            if await self._memberships.get_for_tenant(session, tenant_id, assignee_id) is None:
                raise NotFound(detail=f"membership {assignee_id} not in tenant {tenant_id}")
        elif assignee_type == ASSIGNEE_TYPE_GROUP:
            if await self._groups.get_for_tenant(session, tenant_id, assignee_id) is None:
                raise NotFound(detail=f"group {assignee_id} not in tenant {tenant_id}")
        else:
            raise InvalidInput(detail=f"unknown assignee_type {assignee_type!r}")
        duplicate = await self._roles.find_assignment(
            session,
            tenant_id,
            role_id=role_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            engagement_id=engagement_id,
        )
        if duplicate is not None:
            raise DuplicateAssignment(detail=f"assignment {duplicate.id} already grants this")
        assignment = RoleAssignment(
            id=uuid7(),
            tenant_id=tenant_id,
            role_id=role_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            engagement_id=engagement_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        await self._roles.add_assignment(session, assignment)
        await self._record(
            session,
            MembershipActor(actor_membership_id),
            tenant_id,
            "create",
            "role_assignment",
            assignment.id,
            None,
            AuditService.snapshot(assignment, fields=_ASSIGNMENT_SNAPSHOT),
        )
        return assignment

    async def delete_assignment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        role_id: uuid.UUID,
        assignment_id: uuid.UUID,
    ) -> None:
        assignment = await self._roles.get_assignment(session, tenant_id, assignment_id)
        if assignment is None or assignment.role_id != role_id:
            raise NotFound(detail=f"assignment {assignment_id} not on role {role_id}")
        await self._record(
            session,
            MembershipActor(actor_membership_id),
            tenant_id,
            "delete",
            "role_assignment",
            assignment.id,
            AuditService.snapshot(assignment, fields=_ASSIGNMENT_SNAPSHOT),
            None,
        )
        await self._roles.delete_assignment(session, assignment)

    # -- provider path -----------------------------------------------------------------

    async def invite_admin(
        self,
        session: AsyncSession,
        *,
        actor_admin_id: uuid.UUID,
        tenant_id: uuid.UUID,
        email: str,
        full_name: str,
    ) -> InviteResult:
        """The provider-plane path that puts a company's first admin inside it.

        Runs on a provider session and binds the target tenant *in addition* —
        the same dual-GUC exception as signup — because the invited membership
        is a tenant-plane row. Seeds the built-in roles idempotently (decision
        14), records the Admin membership (which completes the ``invite_admin``
        provisioning step), and returns the one-time invite token (decision 15).
        The tenant flips to ``active`` later, when this admin accepts.
        """
        tenant = await tenancy_service.get_tenant(session, tenant_id)
        await bind_tenant_context(session, tenant.id)
        actor = PlatformAdminActor(actor_admin_id)
        await self.seed_built_in_roles(session, tenant_id=tenant.id, actor=actor)

        email_n = normalize_email(email)
        user = await self._users.get_by_email(session, email_n)
        if user is None:
            user = User(id=uuid7(), email=email_n, full_name=full_name.strip())
            await self._users.add(session, user)
            await self._record(
                session,
                actor,
                tenant.id,
                "create",
                "user",
                user.id,
                None,
                AuditService.snapshot(user, fields=_USER_SNAPSHOT),
            )
        membership = await self._memberships.get_by_tenant_user(session, tenant.id, user.id)
        if membership is not None and membership.status == MEMBERSHIP_STATUS_ACTIVE:
            raise AlreadyMember(detail=f"membership {membership.id} is already active")
        if membership is None:
            membership = TenantMembership(
                id=uuid7(),
                tenant_id=tenant.id,
                user_id=user.id,
                status=MEMBERSHIP_STATUS_INVITED,
                invited_at=datetime.now(UTC),
            )
            await self._memberships.add(session, membership)
            await self._record(
                session,
                actor,
                tenant.id,
                "create",
                "tenant_membership",
                membership.id,
                None,
                AuditService.snapshot(membership, fields=_MEMBERSHIP_SNAPSHOT),
            )
        admin_role = await self._roles.get_by_name(session, tenant.id, ADMIN_ROLE_NAME)
        if admin_role is None:  # pragma: no cover — seeded three lines above
            raise NotFound(detail=f"Admin role missing in tenant {tenant.id}")
        existing = await self._roles.find_assignment(
            session,
            tenant.id,
            role_id=admin_role.id,
            assignee_type=ASSIGNEE_TYPE_MEMBERSHIP,
            assignee_id=membership.id,
            engagement_id=None,
        )
        if existing is None:
            await self._assign_role(session, actor, tenant.id, admin_role, membership.id)

        # The Admin membership is now recorded: complete what can complete.
        await tenancy_service.run_provisioning(
            session, tenant_id=tenant.id, actor_admin_id=actor_admin_id
        )

        issued = issue_token(subject=membership.id, plane="tenant", typ="invite")
        accept_url = (
            f"{get_settings().frontend_base_url.rstrip('/')}/accept-invite?token={issued.token}"
        )
        member = await self._member_view_for(session, tenant.id, membership, user)
        # Same best-effort accept-link email as invite_member (see there).
        await self._mailer.send(_invite_message(email_n, full_name, accept_url))
        return InviteResult(member=member, invite_token=issued.token, accept_url=accept_url)

    # -- internals ------------------------------------------------------------------------

    async def _assign_role(  # noqa: PLR0913 — the assignment's own columns
        self,
        session: AsyncSession,
        actor: Actor,
        tenant_id: uuid.UUID,
        role: Role,
        membership_id: uuid.UUID,
        *,
        valid_from: date | None = None,
        valid_until: date | None = None,
    ) -> RoleAssignment:
        assignment = RoleAssignment(
            id=uuid7(),
            tenant_id=tenant_id,
            role_id=role.id,
            assignee_type=ASSIGNEE_TYPE_MEMBERSHIP,
            assignee_id=membership_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        await self._roles.add_assignment(session, assignment)
        await self._record(
            session,
            actor,
            tenant_id,
            "create",
            "role_assignment",
            assignment.id,
            None,
            AuditService.snapshot(assignment, fields=_ASSIGNMENT_SNAPSHOT),
        )
        return assignment

    async def _replace_direct_roles(  # noqa: PLR0913 — the assignment's own columns
        self,
        session: AsyncSession,
        actor: Actor,
        tenant_id: uuid.UUID,
        membership_id: uuid.UUID,
        role: Role,
        *,
        valid_from: date | None = None,
        valid_until: date | None = None,
    ) -> None:
        existing = await self._roles.list_direct_for_membership(session, tenant_id, membership_id)
        if (
            len(existing) == 1
            and existing[0].role_id == role.id
            and existing[0].valid_from == valid_from
            and existing[0].valid_until == valid_until
            and existing[0].engagement_id is None
        ):
            return  # nothing changes; nothing is audited
        for assignment in existing:
            await self._record(
                session,
                actor,
                tenant_id,
                "delete",
                "role_assignment",
                assignment.id,
                AuditService.snapshot(assignment, fields=_ASSIGNMENT_SNAPSHOT),
                None,
            )
            await self._roles.delete_assignment(session, assignment)
        await self._assign_role(
            session,
            actor,
            tenant_id,
            role,
            membership_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    async def _member_view_for(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        membership: TenantMembership,
        user: User,
    ) -> MemberView:
        role_names = await self._roles.direct_role_names_by_membership(session, tenant_id)
        group_names = await self._groups.group_names_by_membership(session, tenant_id)
        return self._member_view(
            membership,
            user,
            role_names.get(membership.id, []),
            group_names.get(membership.id, []),
        )

    @staticmethod
    def _member_view(
        membership: TenantMembership,
        user: User,
        role_names: list[str],
        group_names: list[str],
        last_login_at: datetime | None = None,
    ) -> MemberView:
        return MemberView(
            membership_id=membership.id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            status=membership.status,
            role_names=role_names,
            group_names=group_names,
            mfa_enabled=user.mfa_enabled,
            last_login_at=last_login_at,
        )

    @staticmethod
    def _group_view(group: Group, member_ids: list[uuid.UUID]) -> GroupView:
        return GroupView(
            id=group.id, name=group.name, member_count=len(member_ids), member_ids=member_ids
        )

    async def _record(  # noqa: PLR0913, PLR0917 — one audit row's facts
        self,
        session: AsyncSession,
        actor: Actor,
        tenant_id: uuid.UUID,
        action: str,
        object_type: str,
        object_id: uuid.UUID,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> None:
        await self._audit.record(
            session,
            action=action,  # type: ignore[arg-type]
            object_type=object_type,
            object_id=object_id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=after,
        )


iam_auth_service: Final = IamAuthService()
iam_service: Final = IamService()
"""The shared instances the routers call; the classes stay importable for tests
that fake the repositories."""

# The seam tenancy left open (decision 10): provisioning's membership questions
# now have real answers. Wired at import so both the app and any test that
# reaches this module get the same gates.
tenancy_service.use_gates(IamMembershipGates())
