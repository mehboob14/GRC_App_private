"""Request and response models for identity and access.

The response shapes are a contract with the already-built frontend
(``frontend/src/lib/api/types.ts``): the login union is discriminated on
``status`` with exactly the four members the client switches on, the invite
response carries the one-time token and accept URL (decision 15), and the
accept response carries ``{status: "accepted", tenant_name}``. Extra fields are
additive and ignored by the client; renaming or removing one is a breaking
change.

Requests forbid unknown fields. No response model anywhere in this file carries
a password hash, an MFA secret, or a recovery-code hash — the one exception is
``recovery_codes`` on enrollment confirmation, which is the single, deliberate
moment plaintext codes leave the system.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verity.modules.tenancy.schemas import UtcDateTime

MIN_PASSWORD_LENGTH = 10
"""The platform password policy the frontend mirrors (`weak_password` on 422)."""


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class LoginRequest(_Request):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class SignupRequest(_Request):
    company_name: str = Field(min_length=1, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)
    """Length is policy, not shape: the service raises ``weak_password`` so the
    client gets the stable code rather than a generic validation envelope."""

    accept_terms: bool = False
    """Must be true — the service refuses signup otherwise. Recorded as
    ``users.terms_accepted_at`` for a compliance product's own paper trail."""


class VerifyEmailRequest(_Request):
    token: str


class ResendVerificationRequest(_Request):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetRequest(_Request):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirm(_Request):
    token: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)


class UserOut(_Response):
    id: uuid.UUID
    email: str
    full_name: str
    status: str
    mfa_enabled: bool


class WorkspaceOut(_Response):
    membership_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role_name: str
    status: str


class PrincipalOut(_Response):
    user: UserOut
    membership_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    permissions: list[str]
    role_names: list[str]


class AuthenticatedResponse(_Response):
    status: Literal["authenticated"] = "authenticated"
    access_token: str
    expires_at: UtcDateTime
    principal: PrincipalOut
    workspaces: list[WorkspaceOut]


class MfaRequiredResponse(_Response):
    status: Literal["mfa_required"] = "mfa_required"
    challenge_token: str
    expires_at: UtcDateTime
    membership_id: uuid.UUID


class MfaEnrollmentRequiredResponse(_Response):
    status: Literal["mfa_enrollment_required"] = "mfa_enrollment_required"
    challenge_token: str
    expires_at: UtcDateTime
    membership_id: uuid.UUID


class SelectWorkspaceResponse(_Response):
    status: Literal["select_workspace"] = "select_workspace"
    selection_token: str
    expires_at: UtcDateTime
    workspaces: list[WorkspaceOut]


class EmailVerificationRequiredResponse(_Response):
    status: Literal["email_verification_required"] = "email_verification_required"
    email: str
    """The address a verification link was mailed to — shown so the UI can say
    which inbox to check. Never a credential."""


LoginResponse = Annotated[
    AuthenticatedResponse
    | MfaRequiredResponse
    | MfaEnrollmentRequiredResponse
    | SelectWorkspaceResponse
    | EmailVerificationRequiredResponse,
    Field(discriminator="status"),
]


class MfaVerifyRequest(_Request):
    challenge_token: str
    code: str | None = None
    recovery_code: str | None = None

    @model_validator(mode="after")
    def _exactly_one_factor(self) -> MfaVerifyRequest:
        if (self.code is None) == (self.recovery_code is None):
            raise ValueError("provide exactly one of code and recovery_code")
        return self


class MfaEnrollRequest(_Request):
    challenge_token: str


class MfaEnrollStartResponse(_Response):
    """The pending secret, returned exactly once for the authenticator app."""

    challenge_token: str
    secret: str
    otpauth_url: str


class MfaConfirmRequest(_Request):
    challenge_token: str
    code: str


class EnrollmentConfirmedResponse(AuthenticatedResponse):
    """The first session plus the recovery codes — plaintext leaves once."""

    recovery_codes: list[str]


class WorkspaceSelectRequest(_Request):
    selection_token: str
    membership_id: uuid.UUID


class WorkspaceSwitchRequest(_Request):
    membership_id: uuid.UUID


class AcceptInvitationRequest(_Request):
    token: str
    full_name: str | None = Field(default=None, max_length=200)
    password: str | None = None


class AcceptInvitationResponse(_Response):
    status: Literal["accepted"] = "accepted"
    tenant_name: str


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


class MemberOut(_Response):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    status: str
    role_names: list[str]
    group_names: list[str]
    mfa_enabled: bool
    # Last successful sign-in; null until the member logs in for the first time.
    last_login_at: datetime | None = None


class InviteMemberRequest(_Request):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=200)
    role_id: uuid.UUID
    valid_from: date | None = None
    valid_until: date | None = None
    """The optional time-box lands on the created role assignment — the
    guest-auditor path. Order is validated in the service (422 on inversion)."""


class InviteMemberResponse(_Response):
    """Decision 15: the one-time invite token and accept URL are returned here,
    once, for the inviter to hand over — a deliberate Week 1 affordance removed
    when the notifications module delivers invites itself."""

    member: MemberOut
    invite_token: str
    accept_url: str


class MemberRolesPut(_Request):
    role_id: uuid.UUID


class AdminInviteRequest(_Request):
    """The provider plane inviting a registered tenant's first admin."""

    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


class GroupOut(_Response):
    id: uuid.UUID
    name: str
    member_count: int
    member_ids: list[uuid.UUID]


class GroupCreate(_Request):
    name: str = Field(min_length=1, max_length=200)


class GroupMemberAdd(_Request):
    membership_id: uuid.UUID
    """A membership id, never a user id — an id that is not a membership in this
    tenant is refused with 404 (the column references tenant_memberships.id)."""


# ---------------------------------------------------------------------------
# Roles and assignments
# ---------------------------------------------------------------------------


class RoleOut(_Response):
    id: uuid.UUID
    name: str
    built_in: bool
    permission_keys: list[str]
    assignment_count: int


class RoleCreate(_Request):
    name: str = Field(min_length=1, max_length=200)
    permission_keys: list[str] = Field(default_factory=list)


class RoleAssignmentCreate(_Request):
    assignee_type: Literal["membership", "group"]
    assignee_id: uuid.UUID
    engagement_id: uuid.UUID | None = None
    valid_from: date | None = None
    valid_until: date | None = None


class RoleAssignmentOut(_Response):
    id: uuid.UUID
    role_id: uuid.UUID
    assignee_type: str
    assignee_id: uuid.UUID
    engagement_id: uuid.UUID | None
    valid_from: date | None
    valid_until: date | None
    created_at: UtcDateTime


# ---------------------------------------------------------------------------
# Tenant security settings
# ---------------------------------------------------------------------------


class SecuritySettingsOut(_Response):
    require_admin_mfa: bool


class SecuritySettingsPatch(_Request):
    require_admin_mfa: bool
