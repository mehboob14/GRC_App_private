"""Document review dates through the real app: set, validated, published, flagged and
swept.

The caller is a real signed-up admin whose session is validated against the database on
every request. The daily sweep is the worker's own function, run directly: what matters is
what it does to a workspace, not that Celery called it. Dates are relative to today because
the rules are functions of the clock, and a lapse is made by moving the date back with
``backdate`` since the clock itself cannot be moved.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.audit import full_stream
from tests.support.documents import (
    backdate,
    client,
    create_document,
    inbox,
    publish,
    today,
)
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.core.email import OutboundEmail
from verity.main import create_app
from verity.modules.documents import schedule
from verity.modules.notifications.service import notification_service
from verity.workers.tasks import _flush_notification_emails, _sweep_document_reviews

pytestmark = pytest.mark.integration

AGE_REVIEW = "UPDATE documents SET renewal_date = :renewal WHERE id = :id"


@pytest.fixture(autouse=True)
async def _clean_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def workspace() -> Workspace:
    return await signup_workspace(company="Policies Ltd", email="founder@policies.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


def _in(days: int) -> str:
    return (today() + timedelta(days=days)).isoformat()


async def _lapse(workspace: Workspace, document_id: str, days_ago: int) -> None:
    await backdate(
        workspace,
        AGE_REVIEW,
        renewal=today() - timedelta(days=days_ago),
        id=uuid.UUID(document_id),
    )


async def _notices(
    app: FastAPI, workspace: Workspace, document_id: str | None = None
) -> list[dict[str, Any]]:
    """The review notices in the admin's inbox, optionally for one document."""
    items = await inbox(app, tenant_session_headers(workspace.membership_id))
    return [
        n
        for n in items
        if n["kind"] in ("document_review_due", "document_review_overdue")
        and (document_id is None or n["object_id"] == document_id)
    ]


# ---------------------------------------------------------------------------
# Setting the date
# ---------------------------------------------------------------------------


async def test_a_review_date_is_set_on_create_changed_and_cleared(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    created = await create_document(api, workspace, renewal_date=_in(90))
    assert created["renewal_date"] == _in(90)
    assert created["review_status"] is None

    soon = await api.patch(f"/documents/{created['id']}", json={"renewal_date": _in(10)})
    assert soon.status_code == 200, soon.text
    assert soon.json()["renewal_date"] == _in(10)
    assert soon.json()["review_status"] == "due_soon"

    # Editing something else leaves the date alone.
    renamed = await api.patch(f"/documents/{created['id']}", json={"title": "Renamed"})
    assert renamed.json()["renewal_date"] == _in(10)

    cleared = await api.patch(f"/documents/{created['id']}", json={"clear_renewal_date": True})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["renewal_date"] is None
    assert cleared.json()["review_status"] is None

    # The change is on the audit trail with the date in before and after.
    updates = [
        e
        for e in await full_stream(workspace.tenant_id)
        if e.object_type == "document"
        and str(e.object_id) == created["id"]
        and e.action == "update"
    ]
    assert any(
        e.before is not None
        and e.after is not None
        and e.before["renewal_date"] == _in(90)
        and e.after["renewal_date"] == _in(10)
        for e in updates
    )


async def test_a_review_date_in_the_past_is_refused_with_copy(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    refused = await api.post(
        "/documents",
        json={"title": "Backdated", "doc_type": "policy", "renewal_date": _in(-1)},
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "invalid_input"
    assert "review date" in refused.json()["error"]["message"]

    created = await create_document(api, workspace)
    patched = await api.patch(f"/documents/{created['id']}", json={"renewal_date": _in(-30)})
    assert patched.status_code == 422
    assert "review date" in patched.json()["error"]["message"]
    assert (await api.get(f"/documents/{created['id']}")).json()["renewal_date"] is None

    # Today is allowed: it is the day the review is due, not a day late.
    today_ok = await api.patch(f"/documents/{created['id']}", json={"renewal_date": _in(0)})
    assert today_ok.status_code == 200, today_ok.text
    assert today_ok.json()["review_status"] == "due_soon"


async def test_saving_the_other_details_of_an_overdue_document_does_not_trip_on_its_date(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    created = await create_document(api, workspace, renewal_date=_in(5))
    await _lapse(workspace, created["id"], 3)

    renamed = await api.patch(f"/documents/{created['id']}", json={"title": "Still editable"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["review_status"] == "overdue"

    # An edit form that sends the unchanged date back is not a change to it.
    resent = await api.patch(
        f"/documents/{created['id']}",
        json={"title": "Edited again", "renewal_date": _in(-3)},
    )
    assert resent.status_code == 200, resent.text
    assert resent.json()["renewal_date"] == _in(-3)

    # Moving it to another past date is a change, and is refused.
    moved = await api.patch(f"/documents/{created['id']}", json={"renewal_date": _in(-10)})
    assert moved.status_code == 422


# ---------------------------------------------------------------------------
# The register's flags and the KPIs
# ---------------------------------------------------------------------------


async def test_the_register_flags_overdue_and_due_soon_and_the_kpis_count_them(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    overdue = await create_document(api, workspace, title="Overdue", renewal_date=_in(5))
    await _lapse(workspace, overdue["id"], 1)
    today_doc = await create_document(api, workspace, title="Today", renewal_date=_in(0))
    edge = await create_document(api, workspace, title="Thirty days", renewal_date=_in(30))
    far = await create_document(api, workspace, title="Far", renewal_date=_in(31))
    none = await create_document(api, workspace, title="No date")
    retired = await create_document(api, workspace, title="Retired", renewal_date=_in(5))
    await _lapse(workspace, retired["id"], 20)
    archived = await api.post(
        f"/documents/{retired['id']}/archive", json={"reason": "No longer used"}
    )
    assert archived.status_code == 200, archived.text

    rows = {d["title"]: d for d in (await api.get("/documents")).json()}
    assert rows["Overdue"]["review_status"] == "overdue"
    assert rows["Today"]["review_status"] == "due_soon"
    assert rows["Thirty days"]["review_status"] == "due_soon"
    assert rows["Far"]["review_status"] is None
    assert rows["No date"]["review_status"] is None
    # A retired document no longer nags, however stale its date.
    assert rows["Retired"]["review_status"] is None
    assert {today_doc["id"], edge["id"], far["id"], none["id"]} <= {d["id"] for d in rows.values()}

    kpis = (await api.get("/documents/kpis")).json()
    assert kpis["renewal_past_due"] == 1
    assert kpis["renewal_soon"] == 2
    # Every key the dashboard already reads is still there.
    assert {"renewal_soon", "renewal_past_due", "needs_approval", "ready_to_publish"} <= set(kpis)


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------


async def test_publishing_sets_a_review_date_a_year_out_when_there_is_none(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    created = await create_document(api, workspace)
    assert created["renewal_date"] is None

    published = await publish(api, created["id"], workspace.membership_id)

    assert published["renewal_date"] == schedule.add_months(today(), 12).isoformat()
    assert published["review_status"] is None
    # The date arrives with the publication, in the audit trail's own words.
    transitions = [
        e
        for e in await full_stream(workspace.tenant_id)
        if str(e.object_id) == created["id"] and e.action == "transition"
    ]
    assert any(
        e.after is not None
        and e.after["lifecycle"] == "published"
        and e.after["renewal_date"] == published["renewal_date"]
        for e in transitions
    )


async def test_publishing_keeps_a_future_review_date_a_person_chose(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    created = await create_document(api, workspace, renewal_date=_in(200))

    published = await publish(api, created["id"], workspace.membership_id)

    assert published["renewal_date"] == _in(200)


async def test_publishing_a_lapsed_review_starts_a_new_year(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    created = await create_document(api, workspace, renewal_date=_in(5))
    await _lapse(workspace, created["id"], 2)
    assert (await api.get(f"/documents/{created['id']}")).json()["review_status"] == "overdue"

    published = await publish(api, created["id"], workspace.membership_id)

    assert published["renewal_date"] == schedule.add_months(today(), 12).isoformat()
    assert published["review_status"] is None


# ---------------------------------------------------------------------------
# The daily sweep
# ---------------------------------------------------------------------------


async def test_the_sweep_notifies_the_owner_once_per_lapse(
    api: httpx.AsyncClient, workspace: Workspace, app: FastAPI
) -> None:
    due = await create_document(api, workspace, title="Due", renewal_date=_in(10))
    edge = await create_document(api, workspace, title="Edge", renewal_date=_in(14))
    late = await create_document(api, workspace, title="Late", renewal_date=_in(5))
    await _lapse(workspace, late["id"], 3)
    await create_document(api, workspace, title="Later", renewal_date=_in(15))
    await create_document(api, workspace, title="Never")

    assert await _sweep_document_reviews() == {"notices_written": 3}
    # A second run, or a redelivered one, writes nothing.
    assert await _sweep_document_reviews() == {"notices_written": 0}

    by_document = {n["object_id"]: n for n in await _notices(app, workspace)}
    assert set(by_document) == {due["id"], edge["id"], late["id"]}
    assert by_document[due["id"]]["kind"] == "document_review_due"
    assert by_document[edge["id"]]["kind"] == "document_review_due"
    assert by_document[late["id"]]["kind"] == "document_review_overdue"
    # The notice names the document and the date, and links to the document.
    assert "POL-" in by_document[due["id"]]["title"]
    assert "overdue" in by_document[late["id"]]["title"]
    assert all(n["object_type"] == "document" for n in by_document.values())


async def test_the_notices_ask_for_an_email_copy(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    created = await create_document(api, workspace, renewal_date=_in(3))
    await _sweep_document_reviews()

    async with session_scope(workspace.tenant_id) as session:
        outbox = await notification_service.pending_emails(session, tenant_id=workspace.tenant_id)
    mine = [n for n in outbox if n.object_id is not None and str(n.object_id) == created["id"]]
    assert [n.kind for n in mine] == ["document_review_due"]
    assert mine[0].email_requested is True
    assert mine[0].emailed_at is None


class _Outbox:
    """A mailer that keeps what it was asked to send instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[OutboundEmail] = []

    async def send(self, message: OutboundEmail) -> bool:
        self.sent.append(message)
        return True


async def test_the_email_copy_shows_a_document_title_as_text_and_never_as_markup(
    api: httpx.AsyncClient, workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A title is typed by a person and ends up in the notice's body. The email layout
    takes paragraphs as markup, so the worker has to escape it on the way in."""
    title = '<a href="https://evil.example/login">Sign in</a> & more'
    await create_document(api, workspace, title=title, renewal_date=_in(3))
    await _sweep_document_reviews()

    outbox = _Outbox()
    monkeypatch.setattr("verity.core.email.get_mailer", lambda: outbox)
    await _flush_notification_emails()

    [email] = [m for m in outbox.sent if m.subject.endswith("is due for review")]
    assert email.html is not None
    assert '<a href="https://evil.example' not in email.html
    assert "&lt;a href=" in email.html
    assert "&amp; more" in email.html
    # The plain text part is read as text, so it carries the title as typed.
    assert title in email.text


async def test_a_changed_review_date_starts_a_new_lapse_and_notifies_again(
    api: httpx.AsyncClient, workspace: Workspace, app: FastAPI
) -> None:
    created = await create_document(api, workspace, renewal_date=_in(10))
    await _sweep_document_reviews()
    assert len(await _notices(app, workspace, created["id"])) == 1

    # Moved a day, still inside the window: a new date is a new occasion.
    moved = await api.patch(f"/documents/{created['id']}", json={"renewal_date": _in(11)})
    assert moved.status_code == 200, moved.text
    assert await _sweep_document_reviews() == {"notices_written": 1}
    assert len(await _notices(app, workspace, created["id"])) == 2

    # And once that date has gone by, the overdue notice is its own, sent once.
    await _lapse(workspace, created["id"], 1)
    assert await _sweep_document_reviews() == {"notices_written": 1}
    assert await _sweep_document_reviews() == {"notices_written": 0}
    kinds = sorted(n["kind"] for n in await _notices(app, workspace, created["id"]))
    assert kinds == ["document_review_due", "document_review_due", "document_review_overdue"]

    # Moving it back to a date that already had its notice is not announced twice.
    again = await api.patch(f"/documents/{created['id']}", json={"renewal_date": _in(10)})
    assert again.status_code == 200
    assert await _sweep_document_reviews() == {"notices_written": 0}


async def test_the_sweep_leaves_alone_what_nobody_can_act_on(
    api: httpx.AsyncClient, workspace: Workspace, app: FastAPI
) -> None:
    ownerless = await api.post(
        "/documents",
        json={"title": "Ownerless", "doc_type": "policy", "renewal_date": _in(3)},
    )
    assert ownerless.status_code == 201, ownerless.text
    retired = await create_document(api, workspace, title="Retired", renewal_date=_in(3))
    await api.post(f"/documents/{retired['id']}/archive", json={"reason": "Replaced"})

    assert await _sweep_document_reviews() == {"notices_written": 0}
    assert await _notices(app, workspace) == []


async def test_the_sweep_never_moves_a_document_out_of_published(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    """A policy past its review date is still the policy in force. Expiring it
    overnight would be the platform making a decision nobody made."""
    created = await create_document(api, workspace)
    await publish(api, created["id"], workspace.membership_id)
    await _lapse(workspace, created["id"], 40)

    await _sweep_document_reviews()

    detail = (await api.get(f"/documents/{created['id']}")).json()
    assert detail["lifecycle"] == "published"
    assert detail["review_status"] == "overdue"
