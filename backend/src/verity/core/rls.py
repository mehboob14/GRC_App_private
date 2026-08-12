"""Tenant context — the primitive every row-level security policy keys on.

This is the most security-sensitive file in the codebase. ADR-0001 makes RLS the
second wall behind the repository's explicit ``tenant_id`` filter; this is where the
database is told which tenant the current unit of work belongs to.

Why ``set_config`` and not ``SET LOCAL``
---------------------------------------
docs/architecture/multi-tenancy.md describes the mechanism as::

    SET LOCAL app.tenant_id = '<uuid>';

Postgres ``SET`` takes a literal, never a bind parameter, so that statement can only
be produced by interpolating a value into SQL text — on the one statement in this
system where an injection would cross the tenant boundary. ``set_config`` is the same
operation as a function call, so the tenant id travels as a bound parameter::

    SELECT set_config('app.tenant_id', $1, true)

The third argument is ``is_local``. ``true`` is what makes the setting die with the
transaction. Without it the value stays on the connection, and the next unit of work
to borrow that connection from the pool inherits another tenant's context — which is
a cross-tenant read produced by pooling rather than by any bug in a query.
"""

from __future__ import annotations

import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TENANT_ID_SETTING: Final = "app.tenant_id"
"""The session variable every tenant policy reads. Changing it is a migration of
every policy in the database."""

NO_TENANT: Final = ""
"""``set_config`` has no NULL. An empty string means "no tenant bound", and the policy
predicate in verity.db.rls turns it into NULL so that nothing matches."""

PROVIDER_PLANE_SETTING: Final = "app.provider_plane"
"""The session variable the provider-plane policies on dual-plane tables read
(openspec/changes/add-audit-trail/design.md). Changing it is a policy migration."""

PROVIDER_PLANE_ON: Final = "on"
"""The only value that satisfies a provider-plane policy predicate."""

_BIND = text("SELECT set_config(:setting, :value, true)")
_READ = text("SELECT current_setting(:setting, true)")


class TenantContextError(RuntimeError):
    """Tenant context was used incorrectly.

    A defect, not a domain condition — deliberately not a ``VerityError``, so it
    surfaces through the catch-all handler as a generic 500 rather than as a
    machine-readable code a client could branch on.
    """


async def bind_tenant_context(session: AsyncSession, tenant_id: uuid.UUID | None) -> None:
    """Bind ``tenant_id`` for the remainder of the current transaction.

    Pass ``None`` for provider-plane and global-content work. That binds "no tenant",
    which is not the same as binding nothing: it means any query that touches a
    tenant-scoped table returns no rows, rather than raising.

    Raises:
        TenantContextError: if no transaction is open. A transaction-local setting
            applied outside a transaction is discarded immediately, so the caller
            would run with no tenant bound and silently read nothing.
    """
    if not session.in_transaction():
        raise TenantContextError(
            "bind_tenant_context requires an open transaction: the setting is "
            "transaction-local and would be discarded. Use core.db.session_scope."
        )
    value = NO_TENANT if tenant_id is None else str(tenant_id)
    await session.execute(_BIND, {"setting": TENANT_ID_SETTING, "value": value})


async def bind_provider_plane(session: AsyncSession) -> None:
    """Widen this transaction to provider-plane visibility.

    Honestly a switch that widens what RLS shows, so it is set from exactly one
    place — ``core.db.provider_session_scope``, entered only for an authenticated
    platform admin — and never derived from a request parameter, header, or claim a
    tenant user can influence (add-audit-trail/design.md, decision 4 in the Week 1
    review record).

    Raises:
        TenantContextError: if no transaction is open. The setting is
            transaction-local and would be discarded, leaving the caller silently
            reading nothing across streams.
    """
    if not session.in_transaction():
        raise TenantContextError(
            "bind_provider_plane requires an open transaction: the setting is "
            "transaction-local and would be discarded. Use core.db.provider_session_scope."
        )
    await session.execute(_BIND, {"setting": PROVIDER_PLANE_SETTING, "value": PROVIDER_PLANE_ON})


async def is_provider_plane_bound(session: AsyncSession) -> bool:
    """Whether this transaction is running with provider-plane visibility."""
    result = await session.execute(_READ, {"setting": PROVIDER_PLANE_SETTING})
    return bool(result.scalar_one_or_none() == PROVIDER_PLANE_ON)


async def current_tenant_id(session: AsyncSession) -> uuid.UUID | None:
    """The tenant bound to this transaction, or ``None`` if there is none."""
    result = await session.execute(_READ, {"setting": TENANT_ID_SETTING})
    raw = result.scalar_one_or_none()
    if not raw:
        return None
    return uuid.UUID(raw)


async def require_tenant_context(session: AsyncSession) -> uuid.UUID:
    """The bound tenant, or raise.

    For a repository or service that must not proceed unscoped. The explicit
    ``tenant_id`` filter is still the first wall — this asserts the second one is up.
    """
    tenant_id = await current_tenant_id(session)
    if tenant_id is None:
        raise TenantContextError(
            "no tenant is bound to this transaction; tenant-scoped work cannot proceed"
        )
    return tenant_id
