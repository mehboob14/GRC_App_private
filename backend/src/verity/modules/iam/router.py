"""Identity and access routes. HTTP only: parse, authorise, call the service,
shape the response.

Three routers. ``auth_router`` holds the unauthenticated and partially-
authenticated flows — no permission dependency appears there, because the
challenge / selection / invite token *is* the partial credential and the service
refuses everything else. The management routers declare a permission on every
route (deny by default); the tenant comes from the session's
:class:`TenantContext`, never from a parameter. ``provider_router`` is the one
provider-plane action this module owns: putting a company's first admin inside
it.

The response shapes are the frontend contract — see ``schemas.py``.
"""

from __future__ import annotations

import urllib.parse
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core import ratelimit
from verity.core.config import get_settings
from verity.core.deps import (
    PlatformAdminPrincipal,
    Principal,
    TenantContext,
    get_current_principal,
    get_provider_session,
    get_session_token,
    get_tenant_context,
    get_tenant_session,
    require,
    require_provider,
)
from verity.core.logging import get_logger
from verity.modules.iam import idp_templates, sso
from verity.modules.iam.schemas import (
    AcceptInvitationRequest,
    AcceptInvitationResponse,
    AdminInviteRequest,
    AuthenticatedResponse,
    EmailVerificationRequiredResponse,
    EnrollmentConfirmedResponse,
    GroupCreate,
    GroupMemberAdd,
    GroupOut,
    GroupUpdate,
    InviteMemberRequest,
    InviteMemberResponse,
    LoginRequest,
    LoginResponse,
    MemberOut,
    MemberRolesPut,
    MemberUpdate,
    MfaConfirmRequest,
    MfaEnrollmentRequiredResponse,
    MfaEnrollRequest,
    MfaEnrollStartResponse,
    MfaRequiredResponse,
    MfaVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PrincipalOut,
    ResendVerificationRequest,
    RoleAssignmentCreate,
    RoleAssignmentOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    SecuritySettingsOut,
    SecuritySettingsPatch,
    SelectWorkspaceResponse,
    SignupRequest,
    SsoCompleteRequest,
    SsoEndSessionOut,
    SsoGroupRolePost,
    SsoProviderPut,
    SsoSetupOut,
    SsoStartOut,
    SsoStatusOut,
    SsoSyncOut,
    TenantSsoPut,
    UserOut,
    VerifyEmailRequest,
    WorkspaceOut,
    WorkspaceSelectRequest,
    WorkspaceSwitchRequest,
)
from verity.modules.iam.service import (
    AuthOutcome,
    ChallengeIssued,
    EmailVerificationRequired,
    InviteResult,
    SelectionIssued,
    SessionIssued,
    iam_auth_service,
    iam_service,
)
from verity.modules.iam.sso_setup import sso_setup_service
from verity.modules.iam.sso_sync import sso_sync_service

auth_router = APIRouter(prefix="/auth", tags=["auth"])
members_router = APIRouter(prefix="/members", tags=["members"])
groups_router = APIRouter(prefix="/groups", tags=["groups"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])
security_router = APIRouter(prefix="/tenant/security", tags=["tenant security"])
provider_router = APIRouter(prefix="/provider/tenants", tags=["provider tenants"])

# Named rather than inlined so tests can target the exact dependency objects.
require_members_read = require("members:read")
require_members_invite = require("members:invite")
require_members_disable = require("members:disable")
require_members_manage = require("members:manage")
require_groups_read = require("groups:read")
require_groups_manage = require("groups:manage")
require_roles_read = require("roles:read")
require_roles_manage = require("roles:manage")
require_security_read = require("tenant:read")
require_security_manage = require("security:manage")

require_provider_admin_invite = require_provider("tenants:provision")

logger = get_logger(__name__)


def _login_response(outcome: AuthOutcome) -> LoginResponse:
    """Map a service outcome onto the frontend's discriminated union."""
    if isinstance(outcome, SessionIssued):
        return _authenticated(outcome)
    if isinstance(outcome, ChallengeIssued):
        if outcome.next_step == "mfa_required":
            return MfaRequiredResponse(
                challenge_token=outcome.challenge_token,
                expires_at=outcome.expires_at,
                membership_id=outcome.membership_id,
            )
        return MfaEnrollmentRequiredResponse(
            challenge_token=outcome.challenge_token,
            expires_at=outcome.expires_at,
            membership_id=outcome.membership_id,
        )
    if isinstance(outcome, SelectionIssued):
        return SelectWorkspaceResponse(
            selection_token=outcome.selection_token,
            expires_at=outcome.expires_at,
            workspaces=[WorkspaceOut.model_validate(entry) for entry in outcome.workspaces],
        )
    if isinstance(outcome, EmailVerificationRequired):
        return EmailVerificationRequiredResponse(email=outcome.email)
    raise TypeError(f"unexpected auth outcome {type(outcome).__name__}")  # pragma: no cover


def _authenticated(issued: SessionIssued) -> AuthenticatedResponse:
    snapshot = issued.principal
    principal = PrincipalOut(
        user=UserOut(
            id=snapshot.user_id,
            email=snapshot.email,
            full_name=snapshot.full_name,
            status=snapshot.user_status,
            mfa_enabled=snapshot.mfa_enabled,
        ),
        membership_id=snapshot.membership_id,
        tenant_id=snapshot.tenant_id,
        tenant_name=snapshot.tenant_name,
        permissions=snapshot.permissions,
        role_names=snapshot.role_names,
    )
    workspaces = [WorkspaceOut.model_validate(entry) for entry in issued.workspaces]
    if issued.recovery_codes is not None:
        return EnrollmentConfirmedResponse(
            access_token=issued.token,
            expires_at=issued.expires_at,
            principal=principal,
            workspaces=workspaces,
            recovery_codes=issued.recovery_codes,
        )
    return AuthenticatedResponse(
        access_token=issued.token,
        expires_at=issued.expires_at,
        principal=principal,
        workspaces=workspaces,
    )


def _invite_response(result: InviteResult) -> InviteMemberResponse:
    return InviteMemberResponse(
        member=MemberOut.model_validate(result.member),
        invite_token=result.invite_token,
        accept_url=result.accept_url,
        email_sent=result.email_sent,
    )


# ---------------------------------------------------------------------------
# Authentication flows
# ---------------------------------------------------------------------------


@auth_router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=LoginResponse,
    summary="Self-service trial signup: company, first admin, one transaction",
)
async def signup(
    body: SignupRequest,
    request: Request,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="A repeat with the same key and body returns the same account's next step.",
        ),
    ] = None,
) -> LoginResponse:
    await ratelimit.limit_mail(request, body.email)
    outcome = await iam_auth_service.signup(
        company_name=body.company_name,
        full_name=body.full_name,
        email=body.email,
        password=body.password,
        accept_terms=body.accept_terms,
        idempotency_key=idempotency_key,
    )
    return _login_response(outcome)


@auth_router.post(
    "/verify-email",
    response_model=LoginResponse,
    summary="Confirm a work email from the signup link, then open MFA enrollment",
)
async def verify_email(body: VerifyEmailRequest) -> LoginResponse:
    outcome = await iam_auth_service.verify_email(token=body.token)
    return _login_response(outcome)


@auth_router.post(
    "/verify-email/resend",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-mail the verification link (always the same response — no disclosure)",
)
async def resend_verification(body: ResendVerificationRequest, request: Request) -> None:
    await ratelimit.limit_mail(request, body.email)
    await iam_auth_service.resend_verification(email=body.email)


@auth_router.post(
    "/password-reset",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Mail a password-reset link (always the same response — no disclosure)",
)
async def request_password_reset(body: PasswordResetRequest, request: Request) -> None:
    await ratelimit.limit_mail(request, body.email)
    await iam_auth_service.request_password_reset(email=body.email)


@auth_router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password from a reset link; revokes all existing sessions",
)
async def confirm_password_reset(body: PasswordResetConfirm) -> None:
    await iam_auth_service.reset_password(token=body.token, new_password=body.new_password)


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="Password first; then a session, an MFA step, or a workspace choice",
)
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    await ratelimit.limit_sign_in(request, body.email)
    outcome = await iam_auth_service.login(email=body.email, password=body.password)
    return _login_response(outcome)


@auth_router.post(
    "/mfa/verify",
    response_model=AuthenticatedResponse,
    summary="Exchange a challenge plus a TOTP or recovery code for a session",
)
async def verify_mfa(body: MfaVerifyRequest) -> AuthenticatedResponse:
    await ratelimit.limit_challenge(body.challenge_token)
    issued = await iam_auth_service.verify_mfa(
        challenge_token=body.challenge_token,
        code=body.code,
        recovery_code=body.recovery_code,
    )
    return _authenticated(issued)


@auth_router.post(
    "/mfa/enroll",
    response_model=MfaEnrollStartResponse,
    summary="Begin TOTP enrollment; the secret is returned exactly once",
)
async def start_mfa_enrollment(body: MfaEnrollRequest) -> MfaEnrollStartResponse:
    started = await iam_auth_service.start_enrollment(challenge_token=body.challenge_token)
    return MfaEnrollStartResponse.model_validate(started)


@auth_router.post(
    "/mfa/confirm",
    response_model=EnrollmentConfirmedResponse,
    summary="Confirm enrollment with a valid code; receive the first session",
)
async def confirm_mfa_enrollment(body: MfaConfirmRequest) -> AuthenticatedResponse:
    await ratelimit.limit_challenge(body.challenge_token)
    issued = await iam_auth_service.confirm_enrollment(
        challenge_token=body.challenge_token, code=body.code
    )
    return _authenticated(issued)


@auth_router.get(
    "/me",
    response_model=PrincipalOut,
    summary="The caller's principal, read fresh from the database",
)
async def read_me(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PrincipalOut:
    """Lets a client re-read display data the session token does not carry —
    the workspace name and the person's own name both live in rows that can
    change while a session is open."""
    assert principal.membership_id is not None  # noqa: S101 — tenant route
    snapshot = await iam_auth_service.current_principal(
        user_id=principal.user_id, membership_id=principal.membership_id
    )
    return PrincipalOut(
        user=UserOut(
            id=snapshot.user_id,
            email=snapshot.email,
            full_name=snapshot.full_name,
            status=snapshot.user_status,
            mfa_enabled=snapshot.mfa_enabled,
        ),
        membership_id=snapshot.membership_id,
        tenant_id=snapshot.tenant_id,
        tenant_name=snapshot.tenant_name,
        permissions=snapshot.permissions,
        role_names=snapshot.role_names,
    )


@auth_router.get(
    "/workspaces",
    response_model=list[WorkspaceOut],
    summary="The caller's memberships across tenants (authenticated; no key)",
)
async def list_workspaces(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[WorkspaceOut]:
    entries = await iam_auth_service.list_workspaces(user_id=principal.user_id)
    return [WorkspaceOut.model_validate(entry) for entry in entries]


@auth_router.post(
    "/workspaces/select",
    response_model=LoginResponse,
    summary="Turn a workspace selection into a session (MFA rules still apply)",
)
async def select_workspace(body: WorkspaceSelectRequest) -> LoginResponse:
    outcome = await iam_auth_service.select_workspace(
        selection_token=body.selection_token, membership_id=body.membership_id
    )
    return _login_response(outcome)


@auth_router.post(
    "/workspaces/switch",
    response_model=LoginResponse,
    summary="A new session for another of the caller's memberships, audited",
)
async def switch_workspace(
    body: WorkspaceSwitchRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> LoginResponse:
    outcome = await iam_auth_service.switch_workspace(
        user_id=principal.user_id, membership_id=body.membership_id
    )
    return _login_response(outcome)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End the current session — recorded in the audit trail (decisions 2, 17)",
)
async def logout(
    principal: Annotated[Principal, Depends(get_current_principal)],
    token: Annotated[str, Depends(get_session_token)],
) -> None:
    assert principal.membership_id is not None  # noqa: S101 — guaranteed by the dependency
    assert principal.tenant_id is not None  # noqa: S101
    await iam_auth_service.logout(
        token=token, membership_id=principal.membership_id, tenant_id=principal.tenant_id
    )


# -- sign in through Keycloak (ADR-0015, openspec/changes/add-keycloak-sso) -----------------


@auth_router.get("/sso/status", response_model=SsoStatusOut, summary="Whether SSO sign in is on")
async def sso_status() -> SsoStatusOut:
    settings = get_settings().oidc
    return SsoStatusOut(enabled=settings.enabled and settings.client_secret is not None)


@auth_router.get(
    "/sso/start",
    response_model=SsoStartOut,
    summary="Where to send the browser to sign in through Keycloak",
)
async def sso_start(
    request: Request, email: Annotated[str | None, Query(max_length=320)] = None
) -> SsoStartOut:
    if email:
        await ratelimit.limit_sign_in(request, email)
    # A workspace with SSO on that routes this email's domain names its organization, so
    # Keycloak opens that organization's sign in and the token carries its claim.
    organization = await iam_auth_service.sso_organization_for(email)
    return SsoStartOut(
        authorize_url=await sso.authorization_url(email=email, organization=organization)
    )


@auth_router.get("/sso/callback", include_in_schema=False)
async def sso_callback(
    code: Annotated[str | None, Query(max_length=4096)] = None,
    state: Annotated[str | None, Query(max_length=200)] = None,
    error: Annotated[str | None, Query(max_length=200)] = None,
) -> RedirectResponse:
    """Keycloak sends the browser here. Validated identities are handed to the web app through a
    one time code; failures go back with a fixed error code, never the provider's words."""
    try:
        identity = await sso.finish(code=code, state=state, error=error)
        handoff = await sso.put_handoff(identity)
    except sso.SsoFailed as exc:
        logger.info("sso.callback_refused", code=exc.code, reason=exc.detail)
        return RedirectResponse(sso.failure_redirect(exc.code), status_code=303)
    return RedirectResponse(sso.handoff_redirect(handoff), status_code=303)


@auth_router.post(
    "/sso/complete",
    response_model=LoginResponse,
    summary="Claim the handoff: a session, or a workspace choice",
)
async def sso_complete(body: SsoCompleteRequest) -> LoginResponse:
    identity = await sso.take_handoff(body.handoff)
    return _login_response(await iam_auth_service.sso_sign_in(identity))


@auth_router.post(
    "/sso/end-session",
    response_model=SsoEndSessionOut,
    summary="Keycloak's sign out URL for this person, when they signed in through it",
)
async def sso_end_session(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> SsoEndSessionOut:
    return SsoEndSessionOut(end_session_url=await sso.end_session_url(str(principal.user_id)))


@auth_router.post(
    "/sso/backchannel-logout",
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
)
async def sso_backchannel_logout(request: Request) -> Response:
    """Keycloak calls this when it ends a person's sign in (OpenID Connect Back-Channel Logout):
    every Verity session they hold stops working. A bad token is a 400 with nothing else said."""
    form = urllib.parse.parse_qs((await request.body()).decode(errors="replace"))
    try:
        subject = await sso.validate_logout_token((form.get("logout_token") or [""])[0])
    except sso.SsoFailed as exc:
        logger.info("sso.backchannel_logout_refused", reason=exc.detail)
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    await iam_auth_service.sso_backchannel_logout(subject)
    return Response(status_code=status.HTTP_200_OK, headers={"Cache-Control": "no-store"})


@auth_router.post(
    "/invitations/accept",
    response_model=AcceptInvitationResponse,
    summary="Accept an invitation: single-use token; new users set their password",
)
async def accept_invitation(body: AcceptInvitationRequest) -> AcceptInvitationResponse:
    accepted = await iam_auth_service.accept_invitation(
        token=body.token, full_name=body.full_name, password=body.password
    )
    return AcceptInvitationResponse(tenant_name=accepted.tenant_name)


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@members_router.get(
    "",
    response_model=list[MemberOut],
    summary="The workspace's members with their roles and groups",
)
async def list_members(
    _principal: Annotated[Principal, Depends(require_members_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[MemberOut]:
    members = await iam_service.list_members(session, tenant_id=context.tenant_id)
    return [MemberOut.model_validate(member) for member in members]


@members_router.post(
    "/invite",
    status_code=status.HTTP_201_CREATED,
    response_model=InviteMemberResponse,
    summary="Invite a person; the one-time invite link is returned here (Week 1)",
)
async def invite_member(
    body: InviteMemberRequest,
    principal: Annotated[Principal, Depends(require_members_invite)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> InviteMemberResponse:
    assert principal.membership_id is not None  # noqa: S101 — guaranteed by the dependency
    result = await iam_service.invite_member(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        email=body.email,
        full_name=body.full_name,
        role_id=body.role_id,
        group_id=body.group_id,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    return _invite_response(result)


@members_router.patch(
    "/{membership_id}",
    response_model=MemberOut,
    summary="Edit a member's details (currently the display name)",
)
async def patch_member(
    membership_id: uuid.UUID,
    body: MemberUpdate,
    principal: Annotated[Principal, Depends(require_members_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> MemberOut:
    assert principal.membership_id is not None  # noqa: S101
    member = await iam_service.rename_member(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        membership_id=membership_id,
        full_name=body.full_name,
    )
    return MemberOut.model_validate(member)


@members_router.post(
    "/{membership_id}/disable",
    response_model=MemberOut,
    summary="Disable a membership (never a hard delete)",
)
async def disable_member(
    membership_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_members_disable)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> MemberOut:
    assert principal.membership_id is not None  # noqa: S101
    member = await iam_service.disable_member(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        membership_id=membership_id,
    )
    return MemberOut.model_validate(member)


@members_router.put(
    "/{membership_id}/roles",
    response_model=MemberOut,
    summary="Replace the member's direct role",
)
async def put_member_roles(
    membership_id: uuid.UUID,
    body: MemberRolesPut,
    principal: Annotated[Principal, Depends(require_roles_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> MemberOut:
    assert principal.membership_id is not None  # noqa: S101
    member = await iam_service.set_member_roles(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        membership_id=membership_id,
        role_id=body.role_id,
    )
    return MemberOut.model_validate(member)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


@groups_router.get("", response_model=list[GroupOut], summary="The workspace's groups")
async def list_groups(
    _principal: Annotated[Principal, Depends(require_groups_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[GroupOut]:
    groups = await iam_service.list_groups(session, tenant_id=context.tenant_id)
    return [GroupOut.model_validate(group) for group in groups]


@groups_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=GroupOut,
    summary="Create a group",
)
async def create_group(
    body: GroupCreate,
    principal: Annotated[Principal, Depends(require_groups_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> GroupOut:
    assert principal.membership_id is not None  # noqa: S101
    group = await iam_service.create_group(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        name=body.name,
        description=body.description,
    )
    return GroupOut.model_validate(group)


@groups_router.post(
    "/{group_id}/members",
    response_model=GroupOut,
    summary="Add a membership to a group (membership ids only, never user ids)",
)
async def add_group_member(
    group_id: uuid.UUID,
    body: GroupMemberAdd,
    principal: Annotated[Principal, Depends(require_groups_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> GroupOut:
    assert principal.membership_id is not None  # noqa: S101
    group = await iam_service.add_group_member(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        group_id=group_id,
        membership_id=body.membership_id,
    )
    return GroupOut.model_validate(group)


@groups_router.patch(
    "/{group_id}",
    response_model=GroupOut,
    summary="Rename or re-describe a group",
)
async def update_group(
    group_id: uuid.UUID,
    body: GroupUpdate,
    principal: Annotated[Principal, Depends(require_groups_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> GroupOut:
    assert principal.membership_id is not None  # noqa: S101
    group = await iam_service.update_group(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        group_id=group_id,
        name=body.name,
        description=body.description,
    )
    return GroupOut.model_validate(group)


@groups_router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a group and every role assignment made to it",
)
async def delete_group(
    group_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_groups_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await iam_service.delete_group(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        group_id=group_id,
    )


@groups_router.delete(
    "/{group_id}/members/{membership_id}",
    response_model=GroupOut,
    summary="Remove a membership from a group",
)
async def remove_group_member(
    group_id: uuid.UUID,
    membership_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_groups_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> GroupOut:
    assert principal.membership_id is not None  # noqa: S101
    group = await iam_service.remove_group_member(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        group_id=group_id,
        membership_id=membership_id,
    )
    return GroupOut.model_validate(group)


# ---------------------------------------------------------------------------
# Roles and assignments
# ---------------------------------------------------------------------------


@roles_router.get("", response_model=list[RoleOut], summary="The workspace's roles")
async def list_roles(
    _principal: Annotated[Principal, Depends(require_roles_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[RoleOut]:
    roles = await iam_service.list_roles(session, tenant_id=context.tenant_id)
    return [RoleOut.model_validate(role) for role in roles]


@roles_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RoleOut,
    summary="Create a custom role from shipped permission keys",
)
async def create_role(
    body: RoleCreate,
    principal: Annotated[Principal, Depends(require_roles_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> RoleOut:
    assert principal.membership_id is not None  # noqa: S101
    role = await iam_service.create_role(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        name=body.name,
        description=body.description,
        permission_keys=body.permission_keys,
    )
    return RoleOut.model_validate(role)


@roles_router.patch(
    "/{role_id}",
    response_model=RoleOut,
    summary="Rename a role, edit its description and/or replace its permissions",
)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    principal: Annotated[Principal, Depends(require_roles_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> RoleOut:
    assert principal.membership_id is not None  # noqa: S101
    role = await iam_service.update_role(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        role_id=role_id,
        name=body.name,
        description=body.description,
        permission_keys=body.permission_keys,
    )
    return RoleOut.model_validate(role)


@roles_router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom role; built-in roles refuse with 409",
)
async def delete_role(
    role_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_roles_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await iam_service.delete_role(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        role_id=role_id,
    )


@roles_router.post(
    "/{role_id}/assignments",
    status_code=status.HTTP_201_CREATED,
    response_model=RoleAssignmentOut,
    summary="Assign the role to a membership or group, optionally time-boxed",
)
async def create_role_assignment(
    role_id: uuid.UUID,
    body: RoleAssignmentCreate,
    principal: Annotated[Principal, Depends(require_roles_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> RoleAssignmentOut:
    assert principal.membership_id is not None  # noqa: S101
    assignment = await iam_service.create_assignment(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        role_id=role_id,
        assignee_type=body.assignee_type,
        assignee_id=body.assignee_id,
        engagement_id=body.engagement_id,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    return RoleAssignmentOut.model_validate(assignment)


@roles_router.delete(
    "/{role_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a role assignment",
)
async def delete_role_assignment(
    role_id: uuid.UUID,
    assignment_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_roles_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> None:
    assert principal.membership_id is not None  # noqa: S101
    await iam_service.delete_assignment(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        role_id=role_id,
        assignment_id=assignment_id,
    )


# ---------------------------------------------------------------------------
# Tenant security settings
# ---------------------------------------------------------------------------


@security_router.get("", response_model=SecuritySettingsOut, summary="The tenant's security policy")
async def get_security(
    _principal: Annotated[Principal, Depends(require_security_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SecuritySettingsOut:
    row = await iam_service.get_security_settings(session, context.tenant_id)
    return SecuritySettingsOut.model_validate(row)


@security_router.patch(
    "", response_model=SecuritySettingsOut, summary="Update the security policy (Admin)"
)
async def patch_security(
    body: SecuritySettingsPatch,
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SecuritySettingsOut:
    assert principal.membership_id is not None  # noqa: S101 — guaranteed by the dependency
    # exclude_unset, not exclude_none: the screen sends only what it changed,
    # and every field here has a meaningful non-null value.
    changes = body.model_dump(exclude_unset=True)
    row = await iam_service.update_security_settings(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        changes=changes,
    )
    return SecuritySettingsOut.model_validate(row)


# ---------------------------------------------------------------------------
# Provider plane — the first admin of a provider-registered tenant
# ---------------------------------------------------------------------------


@provider_router.post(
    "/{tenant_id}/admin-invite",
    status_code=status.HTTP_201_CREATED,
    response_model=InviteMemberResponse,
    summary="Invite a tenant's first admin; the tenant activates when they accept",
)
async def invite_tenant_admin(
    tenant_id: uuid.UUID,
    body: AdminInviteRequest,
    admin: Annotated[PlatformAdminPrincipal, Depends(require_provider_admin_invite)],
    session: Annotated[AsyncSession, Depends(get_provider_session)],
) -> InviteMemberResponse:
    result = await iam_service.invite_admin(
        session,
        actor_admin_id=admin.id,
        tenant_id=tenant_id,
        email=body.email,
        full_name=body.full_name,
    )
    return _invite_response(result)


async def _setup_view(session: AsyncSession, tenant_id: uuid.UUID) -> SsoSetupOut:
    return SsoSetupOut.model_validate(await sso_setup_service.view(session, tenant_id=tenant_id))


@security_router.get("/sso", response_model=SsoSetupOut, summary="The workspace's single sign on")
async def get_sso(
    _principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SsoSetupOut:
    return await _setup_view(session, context.tenant_id)


@security_router.put(
    "/sso",
    response_model=SsoSetupOut,
    summary="Set the workspace's single sign on (Admin); enforcing needs a proven sign in",
)
async def put_sso(
    body: TenantSsoPut,
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SsoSetupOut:
    assert principal.membership_id is not None  # noqa: S101 — guaranteed by the dependency
    await iam_service.save_sso(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        organization_alias=body.organization_alias,
        domains=body.domains,
        enabled=body.enabled,
        enforce=body.enforce,
        jit_enabled=body.jit_enabled,
        default_role_id=body.default_role_id,
    )
    return await _setup_view(session, context.tenant_id)


@security_router.post(
    "/sso/domains/{domain}/verify",
    response_model=SsoSetupOut,
    summary="Prove the workspace owns an email domain, by its DNS TXT record",
)
async def verify_sso_domain(
    domain: Annotated[str, Path(max_length=253, pattern=r"^[A-Za-z0-9.-]+$")],
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SsoSetupOut:
    assert principal.membership_id is not None  # noqa: S101
    await sso_setup_service.verify_domain(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        domain=domain,
    )
    return await _setup_view(session, context.tenant_id)


@security_router.put(
    "/sso/provider",
    response_model=SsoSetupOut,
    summary="Connect the workspace's identity provider through Keycloak",
)
async def put_sso_provider(
    body: SsoProviderPut,
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SsoSetupOut:
    assert principal.membership_id is not None  # noqa: S101
    await sso_setup_service.connect(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        provider=body.provider,
        given=idp_templates.ProviderInput(
            tenant_id=body.tenant_id,
            okta_domain=body.okta_domain,
            discovery_url=body.discovery_url,
            metadata_url=body.metadata_url,
            client_id=body.client_id,
            client_secret=body.client_secret.get_secret_value() if body.client_secret else None,
        ),
    )
    return await _setup_view(session, context.tenant_id)


@security_router.post(
    "/sso/groups",
    response_model=SsoSetupOut,
    summary="Give a Verity role to the members of a Keycloak organization group",
)
async def post_sso_group_role(
    body: SsoGroupRolePost,
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SsoSetupOut:
    assert principal.membership_id is not None  # noqa: S101
    await sso_sync_service.add_group_role(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        group_name=body.group_name,
        role_id=body.role_id,
    )
    return await _setup_view(session, context.tenant_id)


@security_router.delete(
    "/sso/groups/{mapping_id}",
    response_model=SsoSetupOut,
    summary="Stop giving a role from a Keycloak group; the next sync takes it back",
)
async def delete_sso_group_role(
    mapping_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> SsoSetupOut:
    assert principal.membership_id is not None  # noqa: S101
    await sso_sync_service.remove_group_role(
        session,
        tenant_id=context.tenant_id,
        actor_membership_id=principal.membership_id,
        mapping_id=mapping_id,
    )
    return await _setup_view(session, context.tenant_id)


@security_router.post(
    "/sso/sync",
    response_model=SsoSyncOut,
    summary="Read the organization's members and groups from Keycloak now",
)
async def post_sso_sync(
    principal: Annotated[Principal, Depends(require_security_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> SsoSyncOut:
    assert principal.membership_id is not None  # noqa: S101
    result = await sso_sync_service.sync_tenant(
        context.tenant_id, actor_membership_id=principal.membership_id
    )
    return SsoSyncOut.model_validate(result)
