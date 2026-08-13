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

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

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
from verity.modules.iam.schemas import (
    AcceptInvitationRequest,
    AcceptInvitationResponse,
    AdminInviteRequest,
    AuthenticatedResponse,
    EnrollmentConfirmedResponse,
    GroupCreate,
    GroupMemberAdd,
    GroupOut,
    InviteMemberRequest,
    InviteMemberResponse,
    LoginRequest,
    LoginResponse,
    MemberOut,
    MemberRolesPut,
    MfaConfirmRequest,
    MfaEnrollmentRequiredResponse,
    MfaEnrollRequest,
    MfaEnrollStartResponse,
    MfaRequiredResponse,
    MfaVerifyRequest,
    PrincipalOut,
    RoleAssignmentCreate,
    RoleAssignmentOut,
    RoleCreate,
    RoleOut,
    SelectWorkspaceResponse,
    SignupRequest,
    UserOut,
    WorkspaceOut,
    WorkspaceSelectRequest,
    WorkspaceSwitchRequest,
)
from verity.modules.iam.service import (
    AuthOutcome,
    ChallengeIssued,
    InviteResult,
    SelectionIssued,
    SessionIssued,
    iam_auth_service,
    iam_service,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
members_router = APIRouter(prefix="/members", tags=["members"])
groups_router = APIRouter(prefix="/groups", tags=["groups"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])
provider_router = APIRouter(prefix="/provider/tenants", tags=["provider tenants"])

# Named rather than inlined so tests can target the exact dependency objects.
require_members_read = require("members:read")
require_members_invite = require("members:invite")
require_members_disable = require("members:disable")
require_groups_read = require("groups:read")
require_groups_manage = require("groups:manage")
require_roles_read = require("roles:read")
require_roles_manage = require("roles:manage")

require_provider_admin_invite = require_provider("tenants:provision")


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
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="A repeat with the same key and body returns the same account's next step.",
        ),
    ] = None,
) -> LoginResponse:
    outcome = await iam_auth_service.signup(
        company_name=body.company_name,
        full_name=body.full_name,
        email=body.email,
        password=body.password,
        idempotency_key=idempotency_key,
    )
    return _login_response(outcome)


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="Password first; then a session, an MFA step, or a workspace choice",
)
async def login(body: LoginRequest) -> LoginResponse:
    outcome = await iam_auth_service.login(email=body.email, password=body.password)
    return _login_response(outcome)


@auth_router.post(
    "/mfa/verify",
    response_model=AuthenticatedResponse,
    summary="Exchange a challenge plus a TOTP or recovery code for a session",
)
async def verify_mfa(body: MfaVerifyRequest) -> AuthenticatedResponse:
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
    issued = await iam_auth_service.confirm_enrollment(
        challenge_token=body.challenge_token, code=body.code
    )
    return _authenticated(issued)


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
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    return _invite_response(result)


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
