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

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from verity.core.db import provider_session_scope, session_scope
from verity.core.logging import get_logger
from verity.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _active_tenant_ids() -> list[uuid.UUID]:
    """Every active tenant's id, read on the provider plane.

    The ``tenants`` registry is provider-plane and RLS-guarded: a plain
    ``session_scope(None)`` binds neither a tenant nor the provider flag and so
    sees zero rows. A per-tenant job then binds context once per tenant inside
    that tenant's own transaction (see the module docstring); this is only the
    enumeration step.
    """
    async with provider_session_scope() as session:
        rows = await session.execute(text("SELECT id FROM tenants WHERE status = 'active'"))
        return [row[0] for row in rows]


@celery_app.task(name="verity.workers.tasks.heartbeat")
def heartbeat() -> dict[str, Any]:
    """Prove the worker, the broker, and the scheduler are wired to each other.

    Touches no database and no tenant, so it is safe to run at any time and needs no
    tenant context. It is the only task in the system that does not.
    """
    now = datetime.now(UTC)
    logger.info("worker.heartbeat", at=now.isoformat())
    return {"status": "ok", "at": now.isoformat()}


@celery_app.task(name="verity.workers.tasks.scan_slas")
def scan_slas() -> dict[str, Any]:
    """Notify owners and assignees of tasks that have breached, or are about to
    breach, their SLA. Idempotent: ``notify_once`` means one breach alert and one
    due alert per task per person however often the sweep runs (rule for
    scheduled jobs, CLAUDE.md), so it is safe on redelivery."""
    return asyncio.run(_scan_slas())


async def _scan_slas() -> dict[str, Any]:
    from verity.modules.notifications.service import notification_service  # noqa: PLC0415
    from verity.modules.tasks.service import task_service  # noqa: PLC0415

    written = 0
    for tenant_id in await _active_tenant_ids():
        async with session_scope(tenant_id) as session:
            for alert in await task_service.sla_watchlist(session, tenant_id=tenant_id):
                kind = "sla_breach" if alert.breached else "sla_due"
                verb = "has breached its SLA" if alert.breached else "is due soon"
                for mid in alert.recipients:
                    wrote = await notification_service.notify_once(
                        session,
                        tenant_id=tenant_id,
                        recipient_membership_id=mid,
                        kind=kind,
                        title=f"{alert.code} {verb}",
                        body=alert.title,
                        object_type="task",
                        object_id=alert.task_id,
                        email=True,
                    )
                    written += int(wrote)
    logger.info("worker.scan_slas", notifications_written=written)
    return {"notifications_written": written}


@celery_app.task(name="verity.workers.tasks.flush_notification_emails")
def flush_notification_emails() -> dict[str, Any]:
    """Deliver the email copy of any notification that asked for one. The outbox
    only ever holds committed rows, so this is the "after commit" of the email
    rule (core.email) by construction; a stamped row is never resent."""
    return asyncio.run(_flush_notification_emails())


async def _flush_notification_emails() -> dict[str, Any]:
    from verity.core.email import OutboundEmail, get_mailer, render_email  # noqa: PLC0415
    from verity.modules.iam.service import iam_service  # noqa: PLC0415
    from verity.modules.notifications.service import notification_service  # noqa: PLC0415

    mailer = get_mailer()
    sent = 0
    for tenant_id in await _active_tenant_ids():
        async with session_scope(tenant_id) as session:
            pending = await notification_service.pending_emails(session, tenant_id=tenant_id)
            if not pending:
                continue
            emails = {
                m.membership_id: m.email
                for m in await iam_service.list_members(session, tenant_id=tenant_id)
            }
            done: list[uuid.UUID] = []
            for note in pending:
                to = emails.get(note.recipient_membership_id)
                if to is None:
                    # Recipient is gone; stop retrying this one forever.
                    done.append(note.id)
                    continue
                html = render_email(
                    heading=note.title, paragraphs=(note.body,) if note.body else ()
                )
                ok = await mailer.send(
                    OutboundEmail(
                        to=to, subject=note.title, text=note.body or note.title, html=html
                    )
                )
                # ponytail: a permanently-failing address retries every tick;
                # add an attempt cap if a dead mailbox ever floods the sweep.
                if ok:
                    done.append(note.id)
                    sent += 1
            await notification_service.mark_emailed(session, tenant_id=tenant_id, ids=done)
    logger.info("worker.flush_notification_emails", emails_sent=sent)
    return {"emails_sent": sent}
