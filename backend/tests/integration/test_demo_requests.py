"""The website's demo-request route, through the real app, Postgres and Redis.

The mailer is a recording fake, so nothing is sent. Everything else is real: the
validation, the rate limits (Redis), the provider-plane transaction, the audit trail and
the CORS policy of the one route. The route is unauthenticated, so no test here signs in.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import NoReturn

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update

from tests.support.audit import full_stream
from verity.core import ratelimit
from verity.core.config import LeadsSettings, Settings
from verity.core.db import dispose_engine, provider_session_scope
from verity.core.email import OutboundEmail
from verity.main import API_PREFIX, create_app
from verity.modules.audit.models import AuditLog
from verity.modules.leads import service as leads_module
from verity.modules.leads.models import DemoRequest
from verity.modules.leads.router import DEMO_REQUESTS_PATH
from verity.modules.leads.service import leads_service

pytestmark = pytest.mark.integration

URL = "/api/v1/public/demo-requests"
OWNER = "owner@verity.example"
WEBSITE = "https://website.example"
EVIL = "https://evil.example"

BODY: dict[str, object] = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "company": "Analytical Engines Ltd",
    "message": "We need SOC 2 by spring.",
    "interest": "pricing:team",
    "source": "hero_cta",
    "page": "/pricing",
}
# Things only the visitor typed. None of them may reach a log line or the audit trail.
PRIVATE = ("Ada", "Lovelace", "ada@example.com", "example.com", "Analytical", "SOC 2 by spring")

PREFLIGHT = {
    "Origin": WEBSITE,
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


def _body(**overrides: object) -> dict[str, object]:
    return {**BODY, **overrides}


class Outbox:
    """A mailer that keeps what it was asked to send instead of sending it."""

    def __init__(self, *, delivers: bool = True) -> None:
        self.sent: list[OutboundEmail] = []
        self._delivers = delivers

    async def send(self, message: OutboundEmail) -> bool:
        self.sent.append(message)
        return self._delivers

    def recipients(self) -> list[str]:
        return [message.to for message in self.sent]


class Exploding:
    """A mailer that raises, which the real one never does, to prove it would not matter."""

    async def send(self, message: OutboundEmail) -> bool:
        raise RuntimeError(f"the relay refused {message.to}")


class Recorder:
    """A logger that keeps what it was told, so a test can search it for personal data."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def _keep(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))

    info = warning = error = _keep

    def names(self) -> list[str]:
        return [event for event, _ in self.events]

    def dump(self) -> str:
        return repr(self.events)


@pytest.fixture(autouse=True)
async def _clean_state(clean_demo_requests: None, clean_audit_log: None) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture(autouse=True)
def _frozen_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """The day's limits are fixed windows that roll over at midnight UTC. A run that
    straddled it would see its counters reset half way through a test, so the limiter's
    clock stands still for the length of one."""
    now = time.time()
    monkeypatch.setattr(ratelimit, "_now", lambda: now)


@pytest.fixture
def leads_config(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> LeadsSettings:
    """The section the service and the app both read, with nobody's real address in it."""
    config = LeadsSettings(notify_email=OWNER, allowed_origins=(WEBSITE,), confirm_requester=True)
    monkeypatch.setattr(settings, "leads", config)
    return config


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    box = Outbox()
    monkeypatch.setattr(leads_service, "_mailer", box)
    return box


@pytest.fixture
def app(settings: Settings, leads_config: LeadsSettings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _rows() -> list[DemoRequest]:
    async with provider_session_scope() as session:
        found = await session.execute(
            select(DemoRequest).order_by(DemoRequest.created_at, DemoRequest.id)
        )
        return list(found.scalars())


async def _audit() -> list[AuditLog]:
    entries = [e for e in await full_stream(None) if e.object_type == "demo_request"]
    return sorted(entries, key=lambda e: (e.occurred_at, e.id))


def _cors(response: httpx.Response) -> list[str]:
    return [name for name in response.headers if name.startswith("access-control-")]


# ---------------------------------------------------------------------------
# What a request does
# ---------------------------------------------------------------------------


async def test_a_request_is_stored_and_both_mails_go_out(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    response = await client.post(URL, json=BODY)

    assert response.status_code == 202
    assert response.json() == {"status": "received"}

    [row] = await _rows()
    assert (row.full_name, row.email, row.company) == (
        "Ada Lovelace",
        "ada@example.com",
        "Analytical Engines Ltd",
    )
    assert (row.message, row.interest, row.source, row.page) == (
        "We need SOC 2 by spring.",
        "pricing:team",
        "hero_cta",
        "/pricing",
    )
    assert row.notified_at is not None
    assert row.confirmation_sent_at is not None

    notice, receipt = outbox.sent
    assert notice.to == OWNER
    assert notice.reply_to == "ada@example.com"
    assert notice.subject == "New demo request: Analytical Engines Ltd (Ada Lovelace)"
    assert receipt.to == "ada@example.com"
    assert receipt.reply_to == OWNER


async def test_the_address_is_stored_lower_cased_and_stripped(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    await client.post(URL, json=_body(email="  Ada.Lovelace@Example.COM "))
    [row] = await _rows()
    assert row.email == "ada.lovelace@example.com"
    assert outbox.sent[0].reply_to == "ada.lovelace@example.com"


async def test_the_audit_row_is_in_the_provider_stream_and_holds_no_personal_data(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    await client.post(URL, json=BODY)

    [row] = await _rows()
    entries = await _audit()
    assert [(e.action, e.actor_type, e.actor_id, e.tenant_id, e.object_id) for e in entries] == [
        ("create", "system", None, None, row.id),
        ("update", "system", None, None, row.id),
        ("update", "system", None, None, row.id),
    ]
    created = entries[0]
    assert created.before is None
    assert created.after == {
        "id": str(row.id),
        "source": "hero_cta",
        "interest": "pricing:team",
        "page": "/pricing",
    }
    assert [tuple(e.after or {}) for e in entries[1:]] == [
        ("notified_at",),
        ("confirmation_sent_at",),
    ]
    assert all(e.before is not None and set(e.before.values()) == {None} for e in entries[1:])

    everything = json.dumps([[e.before, e.after] for e in entries])
    for private in PRIVATE:
        assert private not in everything


async def test_a_honeypot_hit_is_answered_like_a_request_and_leaves_nothing_behind(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    for _ in range(ratelimit.DEMO_EMAIL.requests + 2):
        response = await client.post(URL, json=_body(website="http://spam.example"))
        assert response.status_code == 202
        assert response.json() == {"status": "received"}

    assert await _rows() == []
    assert outbox.sent == []
    assert await _audit() == []

    # More hits than the per address allowance, and none of them spent any of it.
    for _ in range(ratelimit.DEMO_EMAIL.requests):
        assert (await client.post(URL, json=BODY)).status_code == 202
    assert len(await _rows()) == ratelimit.DEMO_EMAIL.requests


async def test_a_repeat_inside_a_day_notifies_the_owner_again_but_sends_no_second_receipt(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    await client.post(URL, json=BODY)
    await client.post(URL, json=_body(message="Following up on my request."))

    first, second = await _rows()
    assert first.confirmation_sent_at is not None
    assert second.confirmation_sent_at is None
    assert second.notified_at is not None
    assert outbox.recipients() == [OWNER, "ada@example.com", OWNER]

    # Another address has its own receipt.
    await client.post(URL, json=_body(email="grace@example.com"))
    assert outbox.recipients()[-2:] == [OWNER, "grace@example.com"]


@pytest.mark.parametrize(("hours_ago", "receipt_due"), [(23, False), (25, True)])
async def test_a_receipt_is_due_again_only_once_a_day_has_passed(
    client: httpx.AsyncClient, outbox: Outbox, hours_ago: int, receipt_due: bool
) -> None:
    await client.post(URL, json=BODY)
    async with provider_session_scope() as session:
        await session.execute(
            update(DemoRequest).values(
                confirmation_sent_at=datetime.now(UTC) - timedelta(hours=hours_ago)
            )
        )

    await client.post(URL, json=BODY)

    assert outbox.recipients().count("ada@example.com") == (2 if receipt_due else 1)


async def test_with_receipts_switched_off_only_the_owner_is_mailed(
    client: httpx.AsyncClient, outbox: Outbox, leads_config: LeadsSettings
) -> None:
    leads_config.confirm_requester = False

    assert (await client.post(URL, json=BODY)).status_code == 202

    assert outbox.recipients() == [OWNER]
    [row] = await _rows()
    assert row.notified_at is not None
    assert row.confirmation_sent_at is None


async def test_with_no_owner_address_the_request_is_stored_and_nothing_is_mailed(
    client: httpx.AsyncClient, outbox: Outbox, leads_config: LeadsSettings
) -> None:
    leads_config.notify_email = None

    response = await client.post(URL, json=BODY)

    assert response.status_code == 202
    assert outbox.sent == [], "a receipt promises a reply, and nobody was told to give one"
    [row] = await _rows()
    assert row.notified_at is None
    assert row.confirmation_sent_at is None
    assert [e.action for e in await _audit()] == ["create"]


# ---------------------------------------------------------------------------
# What a request is refused for
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"email": "not-an-email"},
        {"email": ""},
        {"full_name": "A"},
        {"company": ""},
        {"interest": "Not Valid"},
        {"source": "bad source"},
        {"page": "no-leading-slash"},
        {"message": "m" * 2001},
        {"phone": "+44 20 7946 0000"},
    ],
)
async def test_an_invalid_request_is_422_in_the_platforms_envelope_and_stores_nothing(
    client: httpx.AsyncClient, outbox: Outbox, bad: dict[str, object]
) -> None:
    response = await client.post(URL, json=_body(**bad))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error) == {"code", "message", "correlation_id"}
    for private in PRIVATE:
        assert private not in response.text
    assert await _rows() == []
    assert outbox.sent == []


async def test_a_body_that_is_not_json_is_refused_too(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    response = await client.post(
        URL, content="full_name=Ada", headers={"Content-Type": "text/plain"}
    )
    assert response.status_code == 422
    assert await _rows() == []


# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------


async def test_the_fourth_request_from_one_address_in_a_day_is_429_with_a_retry_time(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    for _ in range(ratelimit.DEMO_EMAIL.requests):
        assert (await client.post(URL, json=BODY)).status_code == 202

    # The same address written another way is the same bucket.
    blocked = await client.post(URL, json=_body(email="  ADA@Example.com "))

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= ratelimit.DEMO_EMAIL.window_seconds
    assert "ada@example.com" not in blocked.text.lower()
    assert len(await _rows()) == ratelimit.DEMO_EMAIL.requests, "refused before any write"
    assert (await client.post(URL, json=_body(email="grace@example.com"))).status_code == 202


async def test_one_address_asking_with_many_emails_is_stopped(
    client: httpx.AsyncClient, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ratelimit, "DEMO_ADDRESS", ratelimit.Limit(requests=3, window_seconds=3600))
    behind_proxy = {"X-Forwarded-For": "8.8.8.8, 172.18.0.2"}
    for index in range(3):
        sent = await client.post(
            URL, json=_body(email=f"user{index}@example.com"), headers=behind_proxy
        )
        assert sent.status_code == 202

    blocked = await client.post(URL, json=_body(email="user9@example.com"), headers=behind_proxy)

    assert blocked.status_code == 429
    assert len(await _rows()) == 3
    elsewhere = await client.post(
        URL,
        json=_body(email="user10@example.com"),
        headers={"X-Forwarded-For": "1.1.1.1, 172.18.0.2"},
    )
    assert elsewhere.status_code == 202


async def test_a_caller_whose_address_is_unknown_is_not_limited_by_address(
    client: httpx.AsyncClient, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No X-Forwarded-For: every caller looks like the proxy, and a bucket on that would be
    # one bucket for the platform.
    monkeypatch.setattr(ratelimit, "DEMO_ADDRESS", ratelimit.Limit(requests=1, window_seconds=3600))
    for index in range(4):
        sent = await client.post(URL, json=_body(email=f"user{index}@example.com"))
        assert sent.status_code == 202


async def test_the_days_ceiling_stops_everyone_and_a_refused_caller_never_spends_it(
    client: httpx.AsyncClient, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ratelimit, "DEMO_CEILING", ratelimit.Limit(requests=4, window_seconds=86400)
    )
    for _ in range(3):
        assert (await client.post(URL, json=BODY)).status_code == 202  # the ceiling: 3 of 4
    # Refused by the per address limit, which comes first, so the ceiling is not charged.
    assert (await client.post(URL, json=BODY)).status_code == 429
    assert (await client.post(URL, json=_body(email="b@example.com"))).status_code == 202  # 4 of 4

    over = await client.post(URL, json=_body(email="c@example.com"))

    assert over.status_code == 429
    assert 1 <= int(over.headers["retry-after"]) <= 86400
    assert len(await _rows()) == 4


# ---------------------------------------------------------------------------
# When something fails
# ---------------------------------------------------------------------------


async def test_a_mail_that_is_not_sent_never_fails_the_request(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    refusing = Outbox(delivers=False)
    monkeypatch.setattr(leads_service, "_mailer", refusing)
    recorder = Recorder()
    monkeypatch.setattr(leads_module, "logger", recorder)

    response = await client.post(URL, json=BODY)

    assert response.status_code == 202
    assert len(refusing.sent) == 2, "both were tried"
    [row] = await _rows()
    assert row.notified_at is None, "the record that the owner was not told"
    assert row.confirmation_sent_at is None
    assert [e.action for e in await _audit()] == ["create"], "nothing was sent, so nothing marked"
    assert recorder.names() == ["leads.received", "leads.mail_not_sent", "leads.mail_not_sent"]
    assert {fields["lead_id"] for _, fields in recorder.events} == {str(row.id)}
    for private in PRIVATE:
        assert private not in recorder.dump()


async def test_a_mailer_that_raises_never_fails_the_request_and_is_logged_by_class_only(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(leads_service, "_mailer", Exploding())
    recorder = Recorder()
    monkeypatch.setattr(leads_module, "logger", recorder)

    response = await client.post(URL, json=BODY)

    assert response.status_code == 202
    assert len(await _rows()) == 1
    assert recorder.names() == ["leads.received", "leads.mail_failed", "leads.mail_failed"]
    assert {fields.get("error") for event, fields in recorder.events if "failed" in event} == {
        "RuntimeError"
    }
    for private in PRIVATE:
        assert private not in recorder.dump()


async def test_when_the_request_cannot_be_stored_the_answer_is_a_plain_503(
    client: httpx.AsyncClient, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = Recorder()
    monkeypatch.setattr(leads_module, "logger", recorder)

    def unreachable() -> NoReturn:
        raise ConnectionRefusedError(f"no route to the database for {BODY['email']}")

    monkeypatch.setattr(leads_module, "provider_session_scope", unreachable)

    response = await client.post(URL, json=BODY)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert outbox.sent == []
    assert await _rows() == []
    assert recorder.events == [("leads.store_failed", {"error": "ConnectionRefusedError"})]
    for private in PRIVATE:
        assert private not in response.text


# ---------------------------------------------------------------------------
# CORS: this one route, for the website, and nothing else
# ---------------------------------------------------------------------------


def test_the_cors_policy_is_keyed_on_the_path_the_app_really_serves() -> None:
    assert f"{API_PREFIX}{DEMO_REQUESTS_PATH}" == URL


async def test_a_preflight_from_the_website_is_answered(client: httpx.AsyncClient) -> None:
    response = await client.options(URL, headers=PREFLIGHT)

    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == WEBSITE
    assert response.headers["access-control-allow-methods"] == "POST, OPTIONS"
    assert response.headers["access-control-allow-headers"] == "Content-Type"
    assert response.headers["access-control-max-age"] == "600"
    assert response.headers["vary"] == "Origin"
    assert "access-control-allow-credentials" not in response.headers


async def test_an_answer_to_the_website_carries_its_origin_and_never_credentials(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    response = await client.post(URL, json=BODY, headers={"Origin": WEBSITE})

    assert response.status_code == 202
    assert response.headers["access-control-allow-origin"] == WEBSITE
    assert response.headers["access-control-expose-headers"] == "Retry-After"
    assert response.headers["vary"] == "Origin"
    assert "access-control-allow-credentials" not in response.headers


async def test_a_refusal_reaches_the_website_with_its_headers_so_it_can_read_it(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    from_website = {"Origin": WEBSITE}
    invalid = await client.post(URL, json=_body(email="nope"), headers=from_website)
    assert invalid.status_code == 422
    assert invalid.headers["access-control-allow-origin"] == WEBSITE

    for _ in range(ratelimit.DEMO_EMAIL.requests):
        await client.post(URL, json=BODY, headers=from_website)
    limited = await client.post(URL, json=BODY, headers=from_website)
    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == WEBSITE
    assert int(limited.headers["retry-after"]) >= 1
    assert "Retry-After" in limited.headers["access-control-expose-headers"]


async def test_any_other_origin_gets_no_cors_headers(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    preflight = await client.options(URL, headers={**PREFLIGHT, "Origin": EVIL})
    assert preflight.status_code == 403
    assert _cors(preflight) == []

    # The server still answers: it is the browser that refuses to hand the answer to the
    # page. What protects the route from a script is its limits, not this header.
    posted = await client.post(URL, json=BODY, headers={"Origin": EVIL})
    assert posted.status_code == 202
    assert _cors(posted) == []


async def test_the_routes_policy_holds_when_the_platforms_own_cors_is_also_configured(
    settings: Settings, leads_config: LeadsSettings, outbox: Outbox
) -> None:
    both = create_app(settings.model_copy(update={"cors_allow_origins": ("https://app.example",)}))
    transport = httpx.ASGITransport(app=both)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        mine = await client.options(URL, headers=PREFLIGHT)
        assert mine.status_code == 204
        assert mine.headers["access-control-allow-origin"] == WEBSITE
        assert "access-control-allow-credentials" not in mine.headers

        posted = await client.post(URL, json=BODY, headers={"Origin": WEBSITE})
        assert posted.status_code == 202
        assert posted.headers["access-control-allow-origin"] == WEBSITE
        assert "access-control-allow-credentials" not in posted.headers

        # The platform's own origin is not welcome on this route, and is served as before
        # everywhere else.
        own = {"Origin": "https://app.example", "Access-Control-Request-Method": "POST"}
        assert _cors(await client.options(URL, headers=own)) == []
        elsewhere = await client.options("/api/v1/auth/login", headers=own)
        assert elsewhere.headers["access-control-allow-origin"] == "https://app.example"
        assert elsewhere.headers["access-control-allow-credentials"] == "true"


async def test_with_no_allowed_origins_the_route_has_no_cors_at_all(
    settings: Settings, leads_config: LeadsSettings, outbox: Outbox
) -> None:
    leads_config.allowed_origins = ()
    transport = httpx.ASGITransport(app=create_app(settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        preflight = await client.options(URL, headers=PREFLIGHT)
        assert preflight.status_code == 405
        assert _cors(preflight) == []
        posted = await client.post(URL, json=BODY, headers={"Origin": WEBSITE})
        assert posted.status_code == 202
        assert _cors(posted) == []
