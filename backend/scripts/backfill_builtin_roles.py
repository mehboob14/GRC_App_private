"""Bring every existing tenant onto the current built-in role set.

New tenants get the right roles from ``ensure_built_in_roles`` at provisioning.
Tenants created before that table changed keep whatever was seeded at the time,
so this walks them and reconciles:

  * creates any missing built-in role, with its starting permissions and
    description;
  * fills in the description on a built-in role that predates the field, unless
    an admin already wrote one — an edit is never overwritten;
  * retires built-in roles the platform no longer ships, but **only when nobody
    holds them**. A role with live assignments is left alone and reported, so
    the run can never silently strip someone's access. Reassign those members,
    then run again.

This is a script and not a migration on purpose: ``roles`` is tenant-owned with
FORCE row-level security and neither database role holds BYPASSRLS, so DML from
a migration matches zero rows and still reports success. Binding RLS per tenant
is what makes the writes land.

Usage (from backend/, with the venv active)::

    python -m scripts.backfill_builtin_roles           # report only
    python -m scripts.backfill_builtin_roles --apply   # write
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import func, select

from verity.core.db import dispose_engine, provider_session_scope, session_scope
from verity.modules.audit.service import System

# Register every module's models before the mapper resolves cross-module FKs —
# same reason as backfill_adopt_soc2.
from verity.modules.compliance import models as _compliance_models  # noqa: F401
from verity.modules.iam import models as _iam_models  # noqa: F401
from verity.modules.iam.models import Role, RoleAssignment
from verity.modules.iam.service import (
    BUILT_IN_ROLE_DESCRIPTIONS,
    BUILT_IN_ROLE_KEYS,
    iam_service,
)
from verity.modules.tenancy import models as _tenancy_models  # noqa: F401
from verity.modules.tenancy.models import Tenant


async def _tenant_ids() -> list[uuid.UUID]:
    async with provider_session_scope() as session:
        return [row[0] for row in await session.execute(select(Tenant.id))]


async def _reconcile(tenant_id: uuid.UUID, *, apply: bool) -> tuple[int, int, list[str]]:
    """Return (created, described, kept) for one tenant."""
    shipped = set(BUILT_IN_ROLE_KEYS)
    async with session_scope(tenant_id=tenant_id) as session:
        if apply:
            # Idempotent: creates whatever is missing, with permissions and
            # description, and audits nothing on a rerun.
            await iam_service.seed_built_in_roles(session, tenant_id=tenant_id, actor=System())

        rows = (await session.execute(select(Role).where(Role.tenant_id == tenant_id))).scalars()
        roles = list(rows)

        created = sum(1 for r in roles if r.built_in and r.name in shipped)
        described = 0
        kept: list[str] = []

        for role in roles:
            if not role.built_in:
                continue
            if role.name in shipped:
                # Fill a blank description; never overwrite an admin's wording.
                if not (role.description or "").strip() and apply:
                    role.description = BUILT_IN_ROLE_DESCRIPTIONS.get(role.name)
                    described += 1
                continue

            # No longer shipped. Retire it only if nobody holds it.
            holders = (
                await session.execute(
                    select(func.count())
                    .select_from(RoleAssignment)
                    .where(RoleAssignment.role_id == role.id)
                )
            ).scalar_one()
            if holders:
                kept.append(f"{role.name} ({holders} assignment(s))")
                continue
            if apply:
                await session.delete(role)

    return created, described, kept


async def main() -> None:
    apply = "--apply" in sys.argv
    tenant_ids = await _tenant_ids()
    print(f"{'applying to' if apply else 'checking'} {len(tenant_ids)} tenant(s)…")
    blocked: list[str] = []
    for tenant_id in tenant_ids:
        created, described, kept = await _reconcile(tenant_id, apply=apply)
        note = f"  {tenant_id}: {created} built-in role(s) present"
        if described:
            note += f", {described} description(s) filled"
        if kept:
            note += f" — KEPT (still assigned): {', '.join(kept)}"
            blocked.extend(kept)
        print(note)
    if blocked:
        print(
            "\nSome retired roles still have holders and were left in place. "
            "Reassign those members, then run again."
        )
    elif not apply:
        print("\nnothing blocking — re-run with --apply to write")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
