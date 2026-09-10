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
from typing import Any, Final

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


_VENDOR_DOC_HORIZON_DAYS: Final = 30
"""How far ahead to warn about a lapsing vendor document. Long enough to renew a
certificate, short enough that the warning still means something on arrival."""


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


@celery_app.task(name="verity.workers.tasks.refresh_vulnerabilities")
def refresh_vulnerabilities() -> dict[str, Any]:
    """Daily: re-enrich open vulnerability definitions from EPSS/KEV/public-exploit,
    recompute their risk scores, and expire lapsed risk acceptances (ADR-0010).
    Idempotent — re-enriching and re-scoring converge on the same values."""
    return asyncio.run(_refresh_vulnerabilities())


async def _refresh_vulnerabilities() -> dict[str, Any]:
    from verity.modules.vulnerabilities.service import vulnerability_service  # noqa: PLC0415

    totals = {"enriched": 0, "rescored": 0, "expired": 0, "escalated": 0}
    for tenant_id in await _active_tenant_ids():
        async with session_scope(tenant_id) as session:
            result = await vulnerability_service.refresh_and_sweep(session, tenant_id=tenant_id)
            for key in totals:
                totals[key] += result.get(key, 0)
    logger.info("worker.refresh_vulnerabilities", **totals)
    return totals


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


@celery_app.task(name="verity.workers.tasks.queue_vendor_reassessments")
def queue_vendor_reassessments() -> dict[str, Any]:
    """Tell owners which vendor reviews have come round.

    It does **not** open the cycle. Starting a reassessment retiers the engagement
    and lays out fresh stages, which is a decision with consequences — a job doing
    it unasked would move every vendor's lifecycle overnight. Idempotent through
    ``notify_once``: one nudge per vendor per owner, however often this runs.
    """
    return asyncio.run(_queue_vendor_reassessments())


async def _queue_vendor_reassessments() -> dict[str, Any]:
    from verity.modules.notifications.service import notification_service  # noqa: PLC0415
    from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

    written = 0
    for tenant_id in await _active_tenant_ids():
        async with session_scope(tenant_id) as session:
            for vendor_id in await vendor_service.due_for_reassessment(
                session, tenant_id=tenant_id
            ):
                owner = await vendor_service.owner_of(
                    session, tenant_id=tenant_id, vendor_id=vendor_id
                )
                if owner is None:
                    continue
                ref = await vendor_service.get_ref(
                    session, tenant_id=tenant_id, vendor_id=vendor_id
                )
                written += int(
                    await notification_service.notify_once(
                        session,
                        tenant_id=tenant_id,
                        recipient_membership_id=owner,
                        kind="vendor_reassessment_due",
                        title=f"{ref.name} is due for review",
                        body="The reassessment cadence for this vendor has come round.",
                        object_type="vendor",
                        object_id=vendor_id,
                        email=True,
                    )
                )
    logger.info("worker.queue_vendor_reassessments", notifications_written=written)
    return {"notifications_written": written}


@celery_app.task(name="verity.workers.tasks.sweep_vendor_documents")
def sweep_vendor_documents() -> dict[str, Any]:
    """Warn on vendor documents that have lapsed or lapse within thirty days.

    Raises no finding: an expired SOC report is a fact about the paperwork, not a
    failed control, and turning every lapsed certificate into a finding is how a
    findings list stops being read.
    """
    return asyncio.run(_sweep_vendor_documents())


async def _sweep_vendor_documents() -> dict[str, Any]:
    from verity.modules.notifications.service import notification_service  # noqa: PLC0415
    from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

    written = 0
    for tenant_id in await _active_tenant_ids():
        async with session_scope(tenant_id) as session:
            for document in await vendor_service.expiring_documents(
                session, tenant_id=tenant_id, within_days=_VENDOR_DOC_HORIZON_DAYS
            ):
                owner = await vendor_service.owner_of(
                    session, tenant_id=tenant_id, vendor_id=document.vendor_id
                )
                if owner is None:
                    continue
                title = (
                    f"{document.title} has expired"
                    if document.is_expired
                    else f"{document.title} expires in {document.expires_in_days} days"
                )
                written += int(
                    await notification_service.notify_once(
                        session,
                        tenant_id=tenant_id,
                        recipient_membership_id=owner,
                        kind="vendor_document_expiring",
                        title=title,
                        body="Request an updated copy from the vendor.",
                        object_type="vendor",
                        object_id=document.vendor_id,
                        email=True,
                    )
                )
    logger.info("worker.sweep_vendor_documents", notifications_written=written)
    return {"notifications_written": written}


@celery_app.task(name="verity.workers.tasks.sweep_vendor_slas")
def sweep_vendor_slas() -> dict[str, Any]:
    """Raise a finding for each breached vendor service level.

    This one writes, and the difference from the two above is deliberate: a
    breached SLA is a contractual fact the vendor has already caused, not a
    judgement the platform is making. Idempotent per service level — an open
    finding for the same SLA suppresses a second.
    """
    return asyncio.run(_sweep_vendor_slas())


async def _sweep_vendor_slas() -> dict[str, Any]:
    from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

    raised = 0
    for tenant_id in await _active_tenant_ids():
        async with session_scope(tenant_id) as session:
            raised += await vendor_service.raise_sla_findings(session, tenant_id=tenant_id)
    logger.info("worker.sweep_vendor_slas", findings_raised=raised)
    return {"findings_raised": raised}
