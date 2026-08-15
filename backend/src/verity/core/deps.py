"""Request dependencies: who is calling, which tenant, and may they.

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

Resolution order (add-identity-and-access/design.md), always:

1. Authenticate the session token (401 on anything invalid or expired).
2. Load the membership the token names; reject a missing or disabled membership, a
   disabled user, or a non-active tenant (401 — enforcement is per-request database
   state, decision 17, so a token outlives none of those).
3. Compute effective permissions: the union of keys from direct role assignments and
   from the membership's groups' assignments, excluding any assignment outside its
   ``valid_from``/``valid_until`` window. The built-in Admin role resolves to every
   key that exists at check time (decision 13).
4. Flat check: required key present, else 403.
5. Object scope, where a route declares one: ``filter`` bounds list queries,
   ``allows`` answers by-id access, and denial is **404**, never 403 — a 403 would
   confirm the object exists across a boundary the caller cannot see over.

Membership resolution happens *before* any tenant can be bound — the token names a
membership, and only that row knows its tenant — so steps 2 and 3 run inside
``provider_session_scope``: the iam migration gives the four identity-resolution
tables a SELECT-only policy keyed on ``app.provider_plane``, the same dual-plane
mechanism ``audit_log`` uses. Writes never happen here; the route's own session is
opened afterwards, bound to the membership's tenant and nothing wider.

core cannot import a module's models — the layer contract is modules over core —
so these queries read the handful of columns they need by name, exactly like the
``platform_admins`` lookup below. The iam module owns the tables; these queries are
part of its public shape.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable, Coroutine, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Annotated, Any, Final, Protocol

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select, bindparam, column, false, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from verity.core.db import provider_session_scope, session_scope
from verity.core.errors import AuthenticationRequired, PermissionDenied
from verity.core.security import decode_token

ADMIN_ROLE_NAME: Final = "Admin"
"""The built-in role resolved as "every key that exists" at check time."""

_ACTIVE: Final = "active"


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


# ---------------------------------------------------------------------------
# Effective permissions — the union, the window, and the Admin expansion
# ---------------------------------------------------------------------------


def assignment_window_active(
    valid_from: date | None, valid_until: date | None, today: date
) -> bool:
    """Whether a role assignment's time-box admits ``today``.

    ``None`` on either edge means unbounded on that side. Expired means invisible —
    this runs at permission-resolution time on every request, never as a nightly
    sweep (backend/CLAUDE.md, "Auditor access is time-boxed").
    """
    if valid_from is not None and today < valid_from:
        return False
    return not (valid_until is not None and today > valid_until)


@dataclass(frozen=True, slots=True)
class RoleGrant:
    """One ``role_assignments`` row, reduced to the facts resolution needs."""

    role_id: uuid.UUID
    assignee_type: str
    assignee_id: uuid.UUID
    valid_from: date | None = None
    valid_until: date | None = None
    engagement_id: uuid.UUID | None = None


def active_role_ids(
    grants: Iterable[RoleGrant],
    *,
    membership_id: uuid.UUID,
    group_ids: Iterable[uuid.UUID],
    today: date,
) -> frozenset[uuid.UUID]:
    """The roles a membership holds right now: direct grants union group grants,
    with every out-of-window assignment contributing nothing."""
    groups = set(group_ids)
    active: set[uuid.UUID] = set()
    for grant in grants:
        if not assignment_window_active(grant.valid_from, grant.valid_until, today):
            continue
        direct = grant.assignee_type == "membership" and grant.assignee_id == membership_id
        via_group = grant.assignee_type == "group" and grant.assignee_id in groups
        if direct or via_group:
            active.add(grant.role_id)
    return frozenset(active)


def _today() -> date:
    return datetime.now(UTC).date()


_GROUP_IDS_SQL = text(
    "SELECT group_id FROM group_members "
    "WHERE tenant_id = :tenant_id AND tenant_membership_id = :membership_id"
)

# Fetches every assignment that could concern this membership; the pure functions
# above decide what is actually active. Group grants ride along only when the
# membership has groups, hence the two variants.
_GRANTS_DIRECT_SQL = text(
    "SELECT role_id, assignee_type, assignee_id, valid_from, valid_until, engagement_id "
    "FROM role_assignments WHERE tenant_id = :tenant_id "
    "AND assignee_type = 'membership' AND assignee_id = :membership_id"
)
_GRANTS_WITH_GROUPS_SQL = text(
    "SELECT role_id, assignee_type, assignee_id, valid_from, valid_until, engagement_id "
    "FROM role_assignments WHERE tenant_id = :tenant_id "
    "AND ((assignee_type = 'membership' AND assignee_id = :membership_id) "
    "OR (assignee_type = 'group' AND assignee_id IN :group_ids))"
).bindparams(bindparam("group_ids", expanding=True))

_ROLES_SQL = text(
    "SELECT id, name, built_in FROM roles WHERE tenant_id = :tenant_id AND id IN :role_ids"
).bindparams(bindparam("role_ids", expanding=True))

_KEYS_FOR_ROLES_SQL = text(
    "SELECT DISTINCT permission_key FROM role_permissions WHERE role_id IN :role_ids"
).bindparams(bindparam("role_ids", expanding=True))

_ALL_KEYS_SQL = text("SELECT key FROM permissions")


async def fetch_grants_for_membership(
    session: AsyncSession, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
) -> tuple[list[RoleGrant], list[uuid.UUID]]:
    """Every assignment that could concern the membership, plus its group ids."""
    group_ids = list(
        (
            await session.execute(
                _GROUP_IDS_SQL, {"tenant_id": tenant_id, "membership_id": membership_id}
            )
        ).scalars()
    )
    if group_ids:
        rows = await session.execute(
            _GRANTS_WITH_GROUPS_SQL,
            {"tenant_id": tenant_id, "membership_id": membership_id, "group_ids": group_ids},
        )
    else:
        rows = await session.execute(
            _GRANTS_DIRECT_SQL, {"tenant_id": tenant_id, "membership_id": membership_id}
        )
    grants = [
        RoleGrant(
            role_id=row.role_id,
            assignee_type=row.assignee_type,
            assignee_id=row.assignee_id,
            valid_from=row.valid_from,
            valid_until=row.valid_until,
            engagement_id=row.engagement_id,
        )
        for row in rows
    ]
    return grants, group_ids


async def resolve_effective_permissions(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    membership_id: uuid.UUID,
    today: date | None = None,
) -> frozenset[str]:
    """Steps 3 of the resolution order, against the database.

    The session must be able to see the iam tables for this membership — either
    bound to its tenant or inside ``provider_session_scope`` (the identity-
    resolution SELECT policies).
    """
    today = today or _today()
    grants, group_ids = await fetch_grants_for_membership(
        session, tenant_id=tenant_id, membership_id=membership_id
    )
    role_ids = active_role_ids(
        grants, membership_id=membership_id, group_ids=group_ids, today=today
    )
    if not role_ids:
        return frozenset()
    ids = list(role_ids)
    roles = (await session.execute(_ROLES_SQL, {"tenant_id": tenant_id, "role_ids": ids})).all()
    keys = set((await session.execute(_KEYS_FOR_ROLES_SQL, {"role_ids": ids})).scalars())
    if any(row.built_in and row.name == ADMIN_ROLE_NAME for row in roles):
        # Decision 13: Admin is "every key that exists", resolved now, so a new
        # module's keys are granted without a data migration.
        keys.update((await session.execute(_ALL_KEYS_SQL)).scalars())
    return frozenset(keys)


# ---------------------------------------------------------------------------
# Tenant-plane dependencies
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)

_MEMBERSHIP_FOR_SESSION = text(
    "SELECT m.id AS membership_id, m.tenant_id, m.user_id, "
    "m.status AS membership_status, u.status AS user_status, t.status AS tenant_status, "
    "c.credentials_changed_at AS credentials_changed_at "
    "FROM tenant_memberships m "
    "JOIN users u ON u.id = m.user_id "
    "JOIN tenants t ON t.id = m.tenant_id "
    "LEFT JOIN credentials c ON c.user_id = m.user_id "
    "WHERE m.id = :membership_id"
)


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> Principal:
    """Resolve the calling tenant user from a tenant-plane session token.

    Authorization is per-request database state, never token contents (decision
    17): a disabled membership, a disabled user, or a tenant that is not
    ``active`` is 401 regardless of token validity. A *provider*-plane session
    token is 403, not 401 — the caller is authenticated, just categorically not
    a tenant user — mirroring ``get_current_platform_admin``.
    """
    if credentials is None:
        raise AuthenticationRequired(detail="no bearer token on a tenant route")
    claims = decode_token(credentials.credentials, expected_typ="session")
    if claims.plane != "tenant":
        raise PermissionDenied(detail="provider-plane session token on a tenant route")
    async with provider_session_scope() as session:
        row = (
            await session.execute(_MEMBERSHIP_FOR_SESSION, {"membership_id": claims.subject})
        ).one_or_none()
        if row is None or row.membership_status != _ACTIVE or row.user_status != _ACTIVE:
            raise AuthenticationRequired(
                detail=f"membership {claims.subject} missing, disabled, or user disabled"
            )
        if row.tenant_status != _ACTIVE:
            raise AuthenticationRequired(
                detail=f"tenant {row.tenant_id} is {row.tenant_status}, not active"
            )
        # Revocation: a password change/reset bumps credentials_changed_at, and
        # any session token minted before that instant is dead (decision 17 —
        # authorization is per-request DB state, not token contents).
        if row.credentials_changed_at is not None and claims.issued_at < row.credentials_changed_at:
            raise AuthenticationRequired(
                detail="session predates a credential change; sign in again"
            )
        permissions = await resolve_effective_permissions(
            session, tenant_id=row.tenant_id, membership_id=row.membership_id
        )
    return Principal(
        user_id=row.user_id,
        membership_id=row.membership_id,
        tenant_id=row.tenant_id,
        permissions=permissions,
    )


async def get_session_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> str:
    """The raw bearer token, for the rare route that needs its identity (its ``jti``)
    rather than only the resolved principal — sign-out, which records the session end.
    Pair it with ``get_current_principal`` so the token is still fully validated."""
    if credentials is None:
        raise AuthenticationRequired(detail="no bearer token")
    return credentials.credentials


async def get_tenant_context(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> TenantContext:
    """The tenant the caller is acting inside — from the membership, never the request.

    There is no parameter by which a client can steer this: the token names a
    membership, the membership names its tenant, and that is the whole resolution.
    """
    if principal.tenant_id is None or principal.membership_id is None:
        raise AuthenticationRequired(detail="principal carries no tenant membership")
    return TenantContext(tenant_id=principal.tenant_id, membership_id=principal.membership_id)


async def get_tenant_session(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> AsyncIterator[AsyncSession]:
    """A session whose transaction has the caller's tenant bound.

    Everything reading or writing a tenant-scoped table goes through this. The
    repository still filters ``tenant_id`` explicitly — RLS is the second wall, not
    the mechanism (docs/architecture/multi-tenancy.md).
    """
    async with session_scope(context.tenant_id) as session:
        yield session


# ---------------------------------------------------------------------------
# Object scope — the hook that stops "flat permission" from meaning "every row"
# ---------------------------------------------------------------------------


class ObjectScope(Protocol):
    """Ownership or assignment filtering, applied *after* the flat check.

    ``filter`` bounds a list query; ``allows`` answers a by-id read or write.
    A denial from ``allows`` must surface as **404**, never 403 — a 403 confirms
    the object exists (docs/conventions/api.md).
    """

    async def filter(
        self, session: AsyncSession, principal: Principal, query: Select[Any]
    ) -> Select[Any]: ...

    async def allows(
        self, session: AsyncSession, principal: Principal, object_id: uuid.UUID
    ) -> bool: ...


_ENGAGEMENTS_SQL = text(
    "SELECT engagement_id, assignee_type, assignee_id, valid_from, valid_until, role_id "
    "FROM role_assignments WHERE tenant_id = :tenant_id AND engagement_id IS NOT NULL"
)


@dataclass(frozen=True)
class EngagementScope:
    """Restricts to objects linked to the caller's active ``engagement_id``
    assignments — the Week 1 auditor scope.

    ``allows`` takes the engagement id of the object under access; ``filter``
    narrows a query on its engagement column. Both answer from the assignment
    window as of today, so an expired engagement is invisible the moment it
    expires. Later modules pass their own engagement column; control-owner
    scoping lands with the compliance module, not here.
    """

    engagement_column: ColumnElement[Any] = field(default_factory=lambda: column("engagement_id"))

    async def active_engagement_ids(
        self, session: AsyncSession, principal: Principal
    ) -> frozenset[uuid.UUID]:
        if principal.tenant_id is None or principal.membership_id is None:
            return frozenset()
        rows = (await session.execute(_ENGAGEMENTS_SQL, {"tenant_id": principal.tenant_id})).all()
        group_ids = list(
            (
                await session.execute(
                    _GROUP_IDS_SQL,
                    {
                        "tenant_id": principal.tenant_id,
                        "membership_id": principal.membership_id,
                    },
                )
            ).scalars()
        )
        today = _today()
        groups = set(group_ids)
        engagement_ids: set[uuid.UUID] = set()
        for row in rows:
            if not assignment_window_active(row.valid_from, row.valid_until, today):
                continue
            direct = (
                row.assignee_type == "membership" and row.assignee_id == principal.membership_id
            )
            via_group = row.assignee_type == "group" and row.assignee_id in groups
            if direct or via_group:
                engagement_ids.add(row.engagement_id)
        return frozenset(engagement_ids)

    async def filter(
        self, session: AsyncSession, principal: Principal, query: Select[Any]
    ) -> Select[Any]:
        engagement_ids = await self.active_engagement_ids(session, principal)
        if not engagement_ids:
            # No active engagement: the list is empty, not an error.
            return query.where(false())
        return query.where(self.engagement_column.in_(engagement_ids))

    async def allows(
        self, session: AsyncSession, principal: Principal, object_id: uuid.UUID
    ) -> bool:
        return object_id in await self.active_engagement_ids(session, principal)


def require(
    permission: str, *, scope: ObjectScope | None = None
) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Declare the permission a route requires; deny by default.

    Usage::

        @router.get("", dependencies=[Depends(require("controls:read"))])

    Permissions are flat ``module:action`` keys; roles are named bundles of them.
    The flat check stops here — a declared ``scope`` is the route's statement that
    its service applies ``filter``/``allows`` on top, because the flat model gives
    no row scoping. Returns the principal so a handler can name the actor in its
    audit rows without a second dependency.
    """

    async def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if not principal.has(permission):
            raise PermissionDenied(
                detail=f"{permission} is not granted to membership {principal.membership_id}"
            )
        return principal

    # For introspection: route audits and tests can read what a route demands.
    dependency.required_permission = permission  # type: ignore[attr-defined]
    dependency.object_scope = scope  # type: ignore[attr-defined]
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


__all__ = [
    "ADMIN_ROLE_NAME",
    "PROVIDER_ROLE_PERMISSIONS",
    "EngagementScope",
    "ObjectScope",
    "PlatformAdminPrincipal",
    "Principal",
    "RoleGrant",
    "TenantContext",
    "active_role_ids",
    "assignment_window_active",
    "fetch_grants_for_membership",
    "get_current_platform_admin",
    "get_current_principal",
    "get_provider_session",
    "get_session_token",
    "get_tenant_context",
    "get_tenant_session",
    "require",
    "require_provider",
    "resolve_effective_permissions",
]
