"""Platform-level tasks.

Setting tenant context per unit of work
--------------------------------------
Rule 1 and ADR-0001 apply to a worker exactly as they apply to a request, and a worker
has no session to resolve a tenant from — so it must bind one explicitly. A job that
forgets to is the reference implementation's actual bug: its tasks opened a session and
queried, which under the application role returns nothing, and under a superuser
connection returns *every tenant's rows*.

A job that touches one tenant::

    async def _run(tenant_id: uuid.UUID) -> None:
        async with session_scope(tenant_id) as session:
            ...

A job that iterates tenants binds context once per tenant, inside that tenant's own
transaction — never once for the whole job::

    async def _run_all() -> None:
        async with session_scope(None) as session:      # provider plane: no tenant
            tenant_ids = await list_active_tenant_ids(session)
        for tenant_id in tenant_ids:                    # one unit of work each
            async with session_scope(tenant_id) as session:
                ...

One transaction per tenant is also what makes a partially failed job resumable without
double-writing: the tenants already committed stay committed, and re-running skips them
because every scheduled job is idempotent (backend/CLAUDE.md).

Celery tasks are synchronous callables, so an async unit of work is driven with
``asyncio.run(...)`` from inside the task body.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from verity.core.logging import get_logger
from verity.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="verity.workers.tasks.heartbeat")
def heartbeat() -> dict[str, Any]:
    """Prove the worker, the broker, and the scheduler are wired to each other.

    Touches no database and no tenant, so it is safe to run at any time and needs no
    tenant context. It is the only task in the system that does not.
    """
    now = datetime.now(UTC)
    logger.info("worker.heartbeat", at=now.isoformat())
    return {"status": "ok", "at": now.isoformat()}
