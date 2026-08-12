"""Request dependencies: who is calling, which tenant, and may they.

The shapes here are fixed now and the bodies are not. Week 1 implements
authentication and authorization behind them; nothing else in the codebase should need
to change when it does, which is the point of settling the signatures first.

Three rules constrain what these can ever do:

- **The tenant is never a path or query parameter** (docs/conventions/api.md). It is
  resolved from the authenticated session and verified against an actual
  ``tenant_memberships`` row. A ``tenant_id`` accepted from a client is a critical
  security bug.
- **A user is a global identity; membership in a tenant is a membership row**
  (ADR-0011). ``Principal`` therefore carries both a ``user_id`` and, when acting
  inside a tenant, a ``membership_id``. Every in-tenant reference to a person is the
  membership, never the user.
- **Every route declares its required permission** (backend/CLAUDE.md). There is no
  authenticated-only default and no implicit allow. ``require`` is how a route says so.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, Final

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.db import provider_session_scope, session_scope
from verity.core.errors import AuthenticationRequired, PermissionDenied
from verity.core.security import decode_token

WEEK_ONE: Final = (
    "not implemented in the foundation change; the IAM module implements it in Week 1 "
    "(openspec/changes/add-backend-foundation/proposal.md, non-goals)"
)


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller.

    Two populations authenticate against this system and they are deliberately not the
    same type of thing (docs/architecture/multi-tenancy.md): a tenant user, who has a
    membership, and a platform admin, who does not and never gets one. Do not model an
    operator as a tenant user with extra permissions.
    """

    user_id: uuid.UUID
    is_platform_admin: bool = False
    membership_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    def __repr__(self) -> str:
        # Permissions are not secret, but a full dump of them in every traceback is
        # noise that hides the identifiers that matter.
        return (
            f"Principal(user_id={self.user_id}, tenant_id={self.tenant_id}, "
            f"is_platform_admin={self.is_platform_admin})"
        )

    def has(self, permission: str) -> bool:
        """Whether the flat ``module:action`` permission is granted.

        Object-scoped access — a control owner seeing their own controls, an auditor
        seeing one engagement inside its window — is *not* expressible here. The flat
        check runs first and the ownership filter runs in the service
        (backend/CLAUDE.md). Never treat this as row-level scoping.
        """
        return permission in self.permissions


@dataclass(frozen=True, slots=True)
class TenantContext:
    """The tenant a request is acting inside, resolved from the session.

    ``membership_id`` is present whenever a tenant user is acting. It is absent when a
    platform admin is acting inside a tenant through the audit-logged impersonation
    flow, which is a separate path with its own trail.
    """

    tenant_id: uuid.UUID
    membership_id: uuid.UUID | None = None
    via_impersonation: bool = False


async def get_current_principal() -> Principal:
    """Resolve the caller from the request's credentials."""
    raise NotImplementedError(f"get_current_principal is {WEEK_ONE}")


async def get_tenant_context(
    principal: Principal = Depends(get_current_principal),
) -> TenantContext:
    """Resolve and verify the tenant the caller is acting inside.

    Must verify against a live ``tenant_memberships`` row, including the auditor
    time-box, and must never read a tenant identifier from the request.
    """
    raise NotImplementedError(f"get_tenant_context is {WEEK_ONE}")


async def get_tenant_session(
    context: TenantContext = Depends(get_tenant_context),
) -> AsyncIterator[AsyncSession]:
    """A session whose transaction has the caller's tenant bound.

    Everything reading or writing a tenant-scoped table goes through this. The
    repository still filters ``tenant_id`` explicitly — RLS is the second wall, not
    the mechanism (docs/architecture/multi-tenancy.md).
    """
    async with session_scope(context.tenant_id) as session:
        yield session


def require(permission: str) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Declare the permission a route requires.

    Usage::

        @router.get("", dependencies=[Depends(require("controls:read"))])

    Permissions are flat ``module:action`` keys. Roles are named bundles of them.
    """

    async def dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        raise NotImplementedError(f"require({permission!r}) is {WEEK_ONE}")

    return dependency


# ---------------------------------------------------------------------------
# Provider plane (openspec/changes/add-provider-plane/design.md, "Authorization on
# the provider plane"). The permissions/roles tables are tenant-scoped and cannot
# hold a provider grant, so each platform_admins.role maps to its keys here, in
# code. "Every route declares its permission" holds on both planes; only the
# resolution differs.
# ---------------------------------------------------------------------------

_TENANT_MANAGEMENT_KEYS: Final = frozenset(
    {"tenants:create", "tenants:read", "tenants:update", "tenants:brand", "tenants:provision"}
)

PROVIDER_ROLE_PERMISSIONS: Final[Mapping[str, frozenset[str]]] = {
    "super_admin": _TENANT_MANAGEMENT_KEYS | {"platform_admins:manage"},
    "onboarding": _TENANT_MANAGEMENT_KEYS,
    "support": frozenset({"tenants:read"}),
}


@dataclass(frozen=True, slots=True)
class PlatformAdminPrincipal:
    """An authenticated operator. Deliberately not a :class:`Principal`: a platform
    admin has no membership and never acts inside a tenant except through the
    (future) audit-logged impersonation flow."""

    id: uuid.UUID
    role: str
    status: str

    def has(self, permission: str) -> bool:
        return permission in PROVIDER_ROLE_PERMISSIONS.get(self.role, frozenset())


_bearer = HTTPBearer(auto_error=False)

# core cannot import a module's model — the layer contract is modules over core —
# so the three columns this dependency needs are read by name. The tenancy module
# owns the table; this query is part of its public shape.
_PLATFORM_ADMIN_BY_ID = text("SELECT id, role, status FROM platform_admins WHERE id = :admin_id")

_ACTIVE_PLATFORM_ADMIN_STATUS: Final = "active"


async def get_current_platform_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> PlatformAdminPrincipal:
    """Resolve the calling platform admin from a provider-plane session token.

    Authorization is resolved per request from the database, never from the token
    (decision 17): a disabled admin is 401 regardless of token validity. A
    *tenant*-plane session token is 403, not 401 — the caller is authenticated,
    just categorically not an operator — and the response discloses nothing about
    the provider plane.
    """
    if credentials is None:
        raise AuthenticationRequired(detail="no bearer token on a provider route")
    claims = decode_token(credentials.credentials, expected_typ="session")
    if claims.plane != "provider":
        raise PermissionDenied(detail="tenant-plane session token on a provider route")
    async with provider_session_scope() as session:
        row = (
            await session.execute(_PLATFORM_ADMIN_BY_ID, {"admin_id": claims.subject})
        ).one_or_none()
    if row is None or row.status != _ACTIVE_PLATFORM_ADMIN_STATUS:
        raise AuthenticationRequired(
            detail=f"platform admin {claims.subject} missing or not active"
        )
    return PlatformAdminPrincipal(id=row.id, role=row.role, status=row.status)


def require_provider(
    permission: str,
) -> Callable[..., Coroutine[Any, Any, PlatformAdminPrincipal]]:
    """Declare the permission a provider route requires; deny by default.

    Returns the authenticated admin so a handler can name the actor in its audit
    rows without a second dependency.
    """

    async def dependency(
        admin: Annotated[PlatformAdminPrincipal, Depends(get_current_platform_admin)],
    ) -> PlatformAdminPrincipal:
        if not admin.has(permission):
            raise PermissionDenied(
                detail=f"{permission} is not granted to provider role {admin.role!r}"
            )
        return admin

    return dependency


async def get_provider_session(
    _admin: Annotated[PlatformAdminPrincipal, Depends(get_current_platform_admin)],
) -> AsyncIterator[AsyncSession]:
    """A session whose transaction runs with provider-plane visibility.

    Depends on the authenticated admin so the widened plane can never be bound for
    an unauthenticated request; it binds ``app.provider_plane`` and **never** a
    tenant — provider routes address tenants as resources, and acting *as* one is
    a separate, audit-logged impersonation flow that does not exist yet.
    """
    async with provider_session_scope() as session:
        yield session
