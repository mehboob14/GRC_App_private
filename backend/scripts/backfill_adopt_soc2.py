"""Backfill: adopt the full SOC 2 control library for every existing tenant.

One-off and idempotent. New tenants now adopt at signup / provider provisioning
(see ``iam.service._adopt_control_library``); this brings tenants created before
that wiring up to the same baseline: the whole library instantiated, so there is
something to scope, own and evidence. Safe to re-run: ``instantiate_library`` is
idempotent on ``(tenant_id, template_id)``.

    # from backend/, with the venv active
    python -m scripts.backfill_adopt_soc2
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from verity.core.db import dispose_engine, provider_session_scope, session_scope

# Register every module's models on Base.metadata before the mapper resolves
# cross-module FKs (controls.owner_membership_id -> tenant_memberships, etc.).
# Same set the Alembic env imports; a plain script skips the app's router graph
# that would otherwise pull them in.
from verity.modules.audit import models as _audit_models  # noqa: F401
from verity.modules.audit.service import System
from verity.modules.compliance import models as _compliance_models  # noqa: F401
from verity.modules.compliance.control_service import control_service
from verity.modules.iam import models as _iam_models  # noqa: F401
from verity.modules.tenancy import models as _tenancy_models  # noqa: F401
from verity.modules.tenancy.models import Tenant


async def _tenant_ids() -> list[uuid.UUID]:
    async with provider_session_scope() as session:
        rows = await session.execute(select(Tenant.id))
        return [row[0] for row in rows]


async def main() -> None:
    tenant_ids = await _tenant_ids()
    print(f"backfilling {len(tenant_ids)} tenant(s)…")
    created_total = 0
    for tenant_id in tenant_ids:
        # One transaction per tenant, RLS bound to it so the control inserts land.
        async with session_scope(tenant_id=tenant_id) as session:
            result = await control_service.instantiate_library(
                session, tenant_id=tenant_id, actor=System()
            )
        created_total += result.created
        print(f"  {tenant_id}: +{result.created} created, {result.already_present} already present")
    print(f"done — {created_total} control(s) created across {len(tenant_ids)} tenant(s)")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
