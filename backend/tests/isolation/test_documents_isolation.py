"""Tenant isolation for the document reminders, review notices and the completion export.

These add data and two jobs that run across every workspace, so the wall has more ways to
be missing than a table without a policy:

1. An unfiltered read from tenant A's session returns only A's campaign recipients, review
   dates and notices: the policy bounds the row set, not the query. That includes the new
   ``last_reminded_at``, ``reminder_count`` and ``dedupe_key`` columns.
2. A B campaign is *absent* by id for every new path that takes one: remind, export and read.
   404-not-403 at the API is this database fact.
3. A write against B's recipient row from an A-bound session matches nothing, so a
   reminder count cannot be moved from the wrong workspace.
4. Both daily jobs bind one tenant per unit of work, so each workspace is told about its own
   documents and campaigns and no other.

Everything is seeded through the real services, never by writing a table, except moving the
clock: a lapsed review and a campaign sent days ago are made by rewriting one timestamp.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import select, text

from tests.support.documents import backdate, client, inbox
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import NotFound
from verity.main import create_app
from verity.modules.audit.service import Membership
from verity.modules.documents.models import DocumentAckCampaignRecipient
from verity.modules.documents.service import RecipientSelection, document_service
from verity.modules.notifications.models import Notification
from verity.workers.tasks import _remind_pending_acknowledgements, _sweep_document_reviews

pytestmark = [pytest.mark.isolation, pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    """``session_scope`` runs on the cached process engine; keep it per-test."""
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@dataclass(frozen=True, slots=True)
class Seeded:
    workspace: Workspace
    document_id: uuid.UUID
    campaign_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TwoTenants:
    a: Seeded
    b: Seeded


async def _populate(workspace: Workspace) -> Seeded:
    """A document whose review has lapsed and a campaign due today that was sent ten days
    ago, with the workspace's admin as owner and as the only recipient. Both tenants use
    the same titles, so a name can never be what keeps them apart."""
    actor = Membership(workspace.membership_id)
    today = datetime.now(UTC).date()
    async with session_scope(workspace.tenant_id) as session:
        document = await document_service.create_document(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            title="Acceptable Use Policy",
            doc_type="policy",
            owner_membership_id=workspace.membership_id,
            renewal_date=today + timedelta(days=5),
        )
        campaign = await document_service.create_campaign(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            document_id=document.id,
            title="Annual acknowledgement",
            message=None,
            reviewers=RecipientSelection(user_ids=[workspace.membership_id]),
            approvers=RecipientSelection(),
            due_at=datetime(today.year, today.month, today.day, tzinfo=UTC),
        )
    await backdate(
        workspace,
        "UPDATE documents SET renewal_date = :lapsed WHERE id = :id",
        lapsed=today - timedelta(days=1),
        id=document.id,
    )
    await backdate(
        workspace,
        "UPDATE document_ack_campaigns SET created_at = :sent WHERE id = :id",
        sent=datetime.now(UTC) - timedelta(days=10),
        id=campaign.id,
    )
    return Seeded(workspace=workspace, document_id=document.id, campaign_id=campaign.id)


@pytest.fixture
async def tenants() -> TwoTenants:
    a = await signup_workspace(company="Alpha Compliance", email="founder@alpha.example")
    b = await signup_workspace(company="Bravo Assurance", email="founder@bravo.example")
    return TwoTenants(a=await _populate(a), b=await _populate(b))


async def test_an_a_session_reads_only_a_s_recipients_and_notices(tenants: TwoTenants) -> None:
    """No WHERE clause anywhere: the policy, not the query, bounds every row set."""
    await _sweep_document_reviews()
    await _remind_pending_acknowledgements()

    async with session_scope(tenants.a.workspace.tenant_id) as session:
        recipients = (await session.execute(select(DocumentAckCampaignRecipient))).scalars().all()
        assert [r.tenant_id for r in recipients] == [tenants.a.workspace.tenant_id]
        assert [r.campaign_id for r in recipients] == [tenants.a.campaign_id]
        assert [r.reminder_count for r in recipients] == [1]
        assert all(r.last_reminded_at is not None for r in recipients)

        notices = (await session.execute(select(Notification))).scalars().all()
        owners = {n.tenant_id for n in notices}
        assert owners == {tenants.a.workspace.tenant_id}
        keyed = {n.dedupe_key for n in notices if n.dedupe_key is not None}
        assert len(keyed) == 1, "the one review notice, keyed on the one review date"


async def test_a_b_campaign_reads_as_absent_by_id_on_every_new_path(
    tenants: TwoTenants, app: FastAPI
) -> None:
    a, b = tenants.a, tenants.b
    actor = Membership(a.workspace.membership_id)
    async with session_scope(a.workspace.tenant_id) as session:
        with pytest.raises(NotFound):
            await document_service.remind_campaign(
                session,
                tenant_id=a.workspace.tenant_id,
                actor=actor,
                campaign_id=b.campaign_id,
                is_manager=True,
            )
        with pytest.raises(NotFound):
            await document_service.export_campaign(
                session,
                tenant_id=a.workspace.tenant_id,
                actor=actor,
                campaign_id=b.campaign_id,
                file_format="csv",
            )
        with pytest.raises(NotFound):
            await document_service.get_campaign(
                session, tenant_id=a.workspace.tenant_id, campaign_id=b.campaign_id
            )

    # The same answer over HTTP: not found, never forbidden, so B's id confirms nothing.
    async with client(app, tenant_session_headers(a.workspace.membership_id)) as mine:
        export = await mine.get(
            f"/documents/campaigns/{b.campaign_id}/export", params={"format": "csv"}
        )
        remind = await mine.post(f"/documents/campaigns/{b.campaign_id}/remind")
    assert export.status_code == 404
    assert remind.status_code == 404
    # And nobody in B was chased.
    headers = tenant_session_headers(b.workspace.membership_id)
    assert await inbox(app, headers, "document_ack_reminder") == []


async def test_a_write_to_b_s_recipient_from_an_a_session_matches_nothing(
    tenants: TwoTenants,
) -> None:
    async with session_scope(tenants.a.workspace.tenant_id) as session:
        moved = (
            await session.execute(
                text(
                    "UPDATE document_ack_campaign_recipients SET reminder_count = 99 "
                    "WHERE campaign_id = :campaign RETURNING id"
                ),
                {"campaign": tenants.b.campaign_id},
            )
        ).all()
    assert moved == []

    async with session_scope(tenants.b.workspace.tenant_id) as session:
        untouched = (
            (await session.execute(select(DocumentAckCampaignRecipient.reminder_count)))
            .scalars()
            .all()
        )
    assert untouched == [0]


async def test_the_daily_jobs_tell_each_workspace_about_its_own_documents_and_campaigns_only(
    tenants: TwoTenants, app: FastAPI
) -> None:
    a, b = tenants.a, tenants.b

    assert await _sweep_document_reviews() == {"notices_written": 2}
    assert await _remind_pending_acknowledgements() == {"reminders_sent": 2}

    for mine, theirs in ((a, b), (b, a)):
        headers = tenant_session_headers(mine.workspace.membership_id)
        notices = await inbox(app, headers)
        about = {
            (n["kind"], n["object_type"], n["object_id"])
            for n in notices
            if n["kind"] in ("document_review_overdue", "document_ack_reminder")
        }
        assert about == {
            ("document_review_overdue", "document", str(mine.document_id)),
            ("document_ack_reminder", "document_ack_campaign", str(mine.campaign_id)),
        }
        seen = {n["object_id"] for n in notices}
        assert str(theirs.document_id) not in seen
        assert str(theirs.campaign_id) not in seen
