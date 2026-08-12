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
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Final

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.db import session_scope

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
