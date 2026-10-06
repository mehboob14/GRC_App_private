"""The public demo-request form, without a database or a mail server.

What needs Postgres, Redis and the real route is in ``tests/integration/test_demo_requests.py``.
Here: what the schema accepts and cleans, what the two messages say and refuse to say,
the one-route CORS policy, the order the rate limits are charged in, and the settings.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError
from starlette.middleware import Middleware
from starlette.requests import Request

from verity.core import email as email_module
from verity.core import ratelimit
from verity.core.config import LeadsSettings, Settings
from verity.core.email import OutboundEmail, SmtpMailer, render_email
from verity.core.errors import RateLimited, ServiceUnavailable
from verity.core.middleware import ScopedCorsMiddleware, origin_allowed
from verity.modules.leads import service as leads_module
from verity.modules.leads.models import DemoRequest
from verity.modules.leads.schemas import DemoRequestIn, clean_line, clean_text
from verity.modules.leads.service import (
    SUBJECT_MAX_LENGTH,
    Delivery,
    LeadInput,
    LeadsService,
    owner_message,
    requester_message,
    sanitise_subject,
)

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
NUL = chr(0)
WEBSITE = "https://website.example"
RECEIVED = datetime(2026, 10, 6, 12, 34, tzinfo=UTC)


def _body(**overrides: object) -> dict[str, Any]:
    body: dict[str, Any] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "company": "Analytical Engines Ltd",
    }
    body.update(overrides)
    return body


def _lead(**overrides: object) -> LeadInput:
    fields: dict[str, Any] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "company": "Analytical Engines Ltd",
    }
    fields.update(overrides)
    return LeadInput(**fields)


# ---------------------------------------------------------------------------
# The request schema
# ---------------------------------------------------------------------------


def test_a_minimal_request_is_accepted_and_normalised() -> None:
    parsed = DemoRequestIn.model_validate(
        _body(full_name="  Ada   Lovelace ", email="  Ada.Lovelace+Demo@Example.CO.uk  ")
    )
    assert parsed.full_name == "Ada Lovelace"
    assert parsed.email == "ada.lovelace+demo@example.co.uk"
    assert (parsed.message, parsed.interest, parsed.source, parsed.page, parsed.website) == (
        None,
        None,
        None,
        None,
        None,
    )


def test_every_field_is_taken_when_given() -> None:
    parsed = DemoRequestIn.model_validate(
        _body(
            message="We need SOC 2 by spring.",
            interest="pricing:team",
            source="hero_cta",
            page="/pricing?plan=team",
            website="",
        )
    )
    assert parsed.message == "We need SOC 2 by spring."
    assert parsed.interest == "pricing:team"
    assert parsed.source == "hero_cta"
    assert parsed.page == "/pricing?plan=team"


@pytest.mark.parametrize(
    "email",
    [
        "",
        "ada",
        "ada@",
        "@example.com",
        "ada@example",
        "ada@@example.com",
        "ada @example.com",
        "ada@exa mple.com",
        "ada@example..com",
        ".ada@example.com",
        "ada.@example.com",
        "ada..lovelace@example.com",
        "ada@-example.com",
        "ada@example-.com",
        "ada@example.c",
        "ada@example.123",
        "ada@example.com\nBcc: attacker@example.net",
        "ada@example.com,grace@example.com",
        "<ada@example.com>",
        "Ada <ada@example.com>",
        "ad" + chr(0xE4) + "@example.com",
        "a" * 65 + "@example.com",
        "a" * 250 + "@example.com",
    ],
)
def test_a_malformed_email_is_refused(email: str) -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(email=email))


@pytest.mark.parametrize("name", ["", " ", "A", "a" * 121, NUL * 3])
def test_a_name_that_is_empty_or_the_wrong_size_is_refused(name: str) -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(full_name=name))


def test_a_name_and_a_company_at_their_limits_are_accepted() -> None:
    parsed = DemoRequestIn.model_validate(_body(full_name="a" * 120, company="c" * 160))
    assert len(parsed.full_name) == 120
    assert len(parsed.company) == 160


@pytest.mark.parametrize("company", ["", "   ", "c" * 161])
def test_a_company_that_is_empty_or_too_long_is_refused(company: str) -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(company=company))


def test_control_characters_never_reach_a_name_or_a_company() -> None:
    parsed = DemoRequestIn.model_validate(
        _body(full_name="Ada" + NUL + "\r\nLovelace", company="Acme\x07\tLtd\x1b")
    )
    assert parsed.full_name == "Ada Lovelace"
    assert parsed.company == "Acme Ltd"


def test_a_message_is_bounded_and_cleaned_but_keeps_its_lines() -> None:
    assert DemoRequestIn.model_validate(_body(message="m" * 2000)).message == "m" * 2000
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(message="m" * 2001))

    cleaned = DemoRequestIn.model_validate(_body(message="one\r\ntwo" + NUL + "\rthree\x1b\n\n"))
    assert cleaned.message == "one\ntwo\nthree"


@pytest.mark.parametrize("empty", ["", "   ", "\n\t"])
def test_an_optional_field_left_empty_is_a_field_not_given(empty: str) -> None:
    parsed = DemoRequestIn.model_validate(
        _body(message=empty, interest=empty, source=empty, page=empty)
    )
    assert (parsed.message, parsed.interest, parsed.source, parsed.page) == (None,) * 4


@pytest.mark.parametrize(
    "interest",
    [
        "Third-Party",  # upper case
        "-leading",
        ":leading",
        "has space",
        "third-party\nrisk",  # a line break inside must not slip through a "$"
        "with/slash",
        "x" * 65,
    ],
)
def test_an_interest_outside_its_pattern_is_refused(interest: str) -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(interest=interest))


@pytest.mark.parametrize("interest", ["third-party-risk", "pricing:team", "a", "x" * 64, "a:b_c-d"])
def test_an_interest_inside_its_pattern_is_accepted(interest: str) -> None:
    assert DemoRequestIn.model_validate(_body(interest=interest)).interest == interest


def test_whitespace_around_a_label_is_not_part_of_it() -> None:
    parsed = DemoRequestIn.model_validate(
        _body(interest=" third-party-risk\n", source="\thero ", page=" /pricing ")
    )
    assert (parsed.interest, parsed.source, parsed.page) == ("third-party-risk", "hero", "/pricing")


@pytest.mark.parametrize(
    "source",
    ["Hero", "-hero", "hero cta", "hero:cta", "hero\ncta", "x" * 33],
)
def test_a_source_outside_its_pattern_is_refused(source: str) -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(source=source))


@pytest.mark.parametrize("source", ["hero", "nav_cta", "footer-cta", "a", "x" * 32])
def test_a_source_inside_its_pattern_is_accepted(source: str) -> None:
    assert DemoRequestIn.model_validate(_body(source=source)).source == source


@pytest.mark.parametrize(
    "page",
    ["pricing", "https://example.com/pricing", "/a b", "/a\nb", "/a" + NUL, "/" + "p" * 200],
)
def test_a_page_that_is_not_a_path_is_refused(page: str) -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(page=page))


@pytest.mark.parametrize("page", ["/", "/pricing", "/solutions/third-party-risk?ref=nav#top"])
def test_a_page_that_is_a_path_is_accepted(page: str) -> None:
    assert DemoRequestIn.model_validate(_body(page=page)).page == page


def test_an_unknown_field_is_refused_like_everywhere_else_in_the_api() -> None:
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(_body(phone="+44 20 7946 0000"))


@pytest.mark.parametrize("missing", ["full_name", "email", "company"])
def test_the_three_required_fields_are_required(missing: str) -> None:
    body = _body()
    del body[missing]
    with pytest.raises(ValidationError):
        DemoRequestIn.model_validate(body)


def test_our_own_error_messages_never_echo_the_value() -> None:
    """Pydantic's error dicts carry the input, and the API's handler drops that. The
    messages written here must not put it back."""
    for field, value in (("email", "ada-lovelace-secret"), ("page", "private path")):
        with pytest.raises(ValidationError) as caught:
            DemoRequestIn.model_validate(_body(**{field: value}))
        for error in caught.value.errors():
            assert "secret" not in error["msg"]
            assert "private" not in error["msg"]


def test_the_cleaners_agree_with_what_they_promise() -> None:
    assert clean_line(" a \t b\r\nc\x00d ") == "a b c d"
    assert clean_line("lone" + chr(0xD800) + "surrogate") == "lonesurrogate"
    assert clean_text("a\r\nb\rc\x0bd\x0ce" + chr(0x2028) + "f") == "a\nb\nc\nd\ne\nf"
    assert clean_text("  keep\ttab  ") == "keep\ttab"


# ---------------------------------------------------------------------------
# The honeypot and the things a service holds
# ---------------------------------------------------------------------------


def test_only_a_filled_in_honeypot_counts() -> None:
    assert LeadsService.is_honeypot(_lead(website="http://spam.example"))
    assert not LeadsService.is_honeypot(_lead(website=None))
    assert not LeadsService.is_honeypot(_lead(website=""))
    assert not LeadsService.is_honeypot(_lead(website="   "))


def test_nothing_the_service_holds_prints_a_visitors_details() -> None:
    lead = _lead(message="a private message")
    delivery = Delivery(lead_id=uuid.uuid4(), received_at=RECEIVED, confirm=True, lead=lead)
    row = DemoRequest(
        id=uuid.uuid4(), full_name="Ada Lovelace", email="ada@example.com", company="Analytical"
    )
    shown = " ".join([repr(lead), repr(delivery), repr(row)])
    for private in ("Ada", "Lovelace", "ada@example.com", "Analytical", "a private message"):
        assert private not in shown


# ---------------------------------------------------------------------------
# The owner's notification
# ---------------------------------------------------------------------------


def test_the_subject_cannot_carry_a_second_header() -> None:
    subject = sanitise_subject("New demo request: Acme\r\nBcc: evil@example.net\x00 (Ada)")
    assert "\r" not in subject
    assert "\n" not in subject
    assert NUL not in subject
    assert subject == "New demo request: Acme Bcc: evil@example.net (Ada)"


def test_the_subject_collapses_whitespace_and_is_capped() -> None:
    assert sanitise_subject("  a \t\t b   c  ") == "a b c"
    long = sanitise_subject("New demo request: " + "x" * 500)
    assert len(long) == SUBJECT_MAX_LENGTH
    assert not long.endswith(" ")
    # Cut inside a gap of spaces: the trailing one goes, so no header ends in blank space.
    padded = sanitise_subject("a" * (SUBJECT_MAX_LENGTH - 1) + " b")
    assert padded == "a" * (SUBJECT_MAX_LENGTH - 1)


def test_the_notification_goes_to_the_owner_and_a_reply_reaches_the_visitor() -> None:
    message = owner_message(_lead(), to="owner@verity.example", received_at=RECEIVED)
    assert message.to == "owner@verity.example"
    assert message.reply_to == "ada@example.com"
    assert message.subject == "New demo request: Analytical Engines Ltd (Ada Lovelace)"


def test_the_notification_lists_every_fact_in_text_and_html() -> None:
    message = owner_message(
        _lead(
            message="Line one\nLine two",
            interest="third-party-risk",
            source="hero_cta",
            page="/pricing",
        ),
        to="owner@verity.example",
        received_at=RECEIVED,
    )
    for expected in (
        "Name: Ada Lovelace",
        "Email: ada@example.com",
        "Company: Analytical Engines Ltd",
        "Interest: third-party-risk",
        "Source: hero_cta",
        "Page: /pricing",
        "Received (UTC): 2026-10-06 12:34",
        "Line one\nLine two",
    ):
        assert expected in message.text
    assert message.html is not None
    for expected in ("Ada Lovelace", "ada@example.com", "third-party-risk", "/pricing"):
        assert expected in message.html
    assert "Line one<br>Line two" in message.html


def test_the_notification_reads_in_the_agreed_order() -> None:
    message = owner_message(
        _lead(message="Hello", interest="pricing", source="nav", page="/p"),
        to="owner@verity.example",
        received_at=RECEIVED,
    )
    labels = ["Name", "Email", "Company", "Interest", "Message", "Source", "Page", "Received (UTC)"]
    in_text = [message.text.index(f"{label}:") for label in labels]
    assert in_text == sorted(in_text)
    assert message.html is not None
    in_html = [message.html.index(f"<strong>{label}</strong>") for label in labels]
    assert in_html == sorted(in_html)


def test_what_the_visitor_did_not_give_says_so() -> None:
    message = owner_message(_lead(), to="owner@verity.example", received_at=RECEIVED)
    assert "Interest: Not given" in message.text
    assert "Source: Not given" in message.text
    assert "Page: Not given" in message.text
    assert "Message:\nNot given" in message.text


def test_markup_in_a_visitors_words_is_escaped_in_the_html_part() -> None:
    hostile = _lead(
        full_name='<img src=x onerror="alert(1)">Ada',
        company="<script>alert('company')</script> & Co",
        message="<script>alert('message')</script>\n<a href=\"https://evil.example\">click</a>",
        interest="a<b",
        source="x>y",
        page="/<svg onload=alert(1)>",
    )
    message = owner_message(hostile, to="owner@verity.example", received_at=RECEIVED)
    assert message.html is not None
    html = message.html
    for raw in ("<script", "<img", "<svg", '<a href="https://evil.example', "</script>"):
        assert raw not in html, raw
    for escaped in (
        "&lt;script&gt;alert(&#x27;company&#x27;)&lt;/script&gt; &amp; Co",
        "&lt;script&gt;alert(&#x27;message&#x27;)&lt;/script&gt;<br>&lt;a href=&quot;https://evil.example",
        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;Ada",
        "a&lt;b",
        "x&gt;y",
    ):
        assert escaped in html, escaped
    # The plain-text part is read as text, so it carries the words as typed.
    assert "<script>alert('company')</script> & Co" in message.text


def test_a_value_with_line_breaks_cannot_forge_a_line_of_the_text_part() -> None:
    forged = _lead(company="Acme\r\nEmail: boss@victim.example", page="/p\nSource: forged")
    message = owner_message(forged, to="owner@verity.example", received_at=RECEIVED)
    lines = message.text.splitlines()
    assert sum(line.startswith("Email: ") for line in lines) == 1
    assert sum(line.startswith("Source: ") for line in lines) == 1
    assert "\n" not in message.subject
    assert "\r" not in message.subject


def test_the_notification_footer_is_honest_and_the_default_is_gone() -> None:
    message = owner_message(_lead(), to="owner@verity.example", received_at=RECEIVED)
    assert message.html is not None
    assert "someone sent the demo request form on the Verity website" in message.html
    assert "this address was used on Verity" not in message.html


def test_the_notification_is_logged_by_a_label_and_not_by_its_subject() -> None:
    message = owner_message(_lead(), to="owner@verity.example", received_at=RECEIVED)
    assert message.log_subject == "demo_request_notification"
    assert "Ada" not in message.log_subject
    # An ordinary message still logs its subject, as before.
    plain = OutboundEmail(to="a@example.com", subject="Confirm your email address", text="x")
    assert plain.log_subject == "Confirm your email address"


async def test_the_real_mailer_logs_the_label_and_never_the_visitor(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    seen: list[dict[str, object]] = []

    class Recorder:
        def info(self, event: str, **fields: object) -> None:
            seen.append({"event": event, **fields})

        warning = info

    monkeypatch.setattr(email_module, "logger", Recorder())
    sent = await SmtpMailer(settings).send(
        owner_message(_lead(), to="owner@verity.example", received_at=RECEIVED)
    )
    assert sent is False, "the test process runs with SMTP off"
    assert seen == [
        {
            "event": "email.skipped",
            "reason": "smtp_not_configured",
            "subject": "demo_request_notification",
        }
    ]


# ---------------------------------------------------------------------------
# The visitor's receipt
# ---------------------------------------------------------------------------


def test_the_receipt_is_the_agreed_copy_and_replies_reach_the_owner() -> None:
    message = requester_message(to="ada@example.com", reply_to="owner@verity.example")
    assert message.to == "ada@example.com"
    assert message.reply_to == "owner@verity.example"
    assert message.subject == "We received your Verity demo request"
    assert message.html is not None
    for body in (message.text, message.html):
        assert (
            "Thanks for asking about Verity. We received your demo request and will reply by "
            "email to find a time that suits you, usually within one business day. If you did "
            "not make this request you can ignore this email."
        ) in body
    assert "a demo request was made on the Verity website using this address" in message.html
    assert "this address was used on Verity." not in message.html


def test_the_receipt_has_no_way_to_carry_what_a_visitor_typed() -> None:
    """The visitor's name and message are not parameters, so they cannot be echoed to an
    address that may belong to somebody else."""
    assert set(inspect.signature(requester_message).parameters) == {"to", "reply_to"}
    message = requester_message(to="ada@example.com", reply_to="owner@verity.example")
    assert message.html is not None
    assert "http" not in message.text
    assert "http" not in message.html.split("<body", 1)[1]
    assert "Ada" not in message.text


def test_neither_message_contains_a_visible_dash() -> None:
    notification = owner_message(
        _lead(message="Plain words.", interest="pricing", source="nav", page="/pricing"),
        to="owner@verity.example",
        received_at=RECEIVED,
    )
    receipt = requester_message(to="ada@example.com", reply_to="owner@verity.example")
    for message in (notification, receipt):
        for part in (message.subject, message.text, message.html or ""):
            assert EM_DASH not in part
            assert EN_DASH not in part
            assert " - " not in part


# ---------------------------------------------------------------------------
# render_email's footer
# ---------------------------------------------------------------------------


def test_the_default_footer_is_unchanged() -> None:
    html = render_email(heading="Hello", paragraphs=("Body.",))
    assert "You received this because this address was used on Verity." in html
    assert "Verity &middot; SOC 2 compliance automation" in html


def test_a_footer_replaces_the_reason_line_and_is_escaped() -> None:
    html = render_email(
        heading="Hello", paragraphs=("Body.",), footer="Sent <b>because</b> & so on"
    )
    assert "Sent &lt;b&gt;because&lt;/b&gt; &amp; so on" in html
    assert "<b>because</b>" not in html
    assert "this address was used on Verity" not in html
    assert "Verity &middot; SOC 2 compliance automation" in html


def test_an_empty_footer_is_still_a_footer_and_not_the_default() -> None:
    html = render_email(heading="Hello", paragraphs=("Body.",), footer="")
    assert "this address was used on Verity" not in html


# ---------------------------------------------------------------------------
# The one route's CORS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("origin", "allowed", "expected"),
    [
        (WEBSITE, (WEBSITE,), True),
        (WEBSITE, ("https://other.example", WEBSITE), True),
        ("http://localhost:5174", ("http://localhost:5174",), True),
        (None, (WEBSITE,), False),
        ("null", (WEBSITE,), False),
        ("", (WEBSITE,), False),
        (WEBSITE, (), False),
        ("https://website.example.evil.test", (WEBSITE,), False),
        ("https://evil-website.example", (WEBSITE,), False),
        ("https://sub.website.example", (WEBSITE,), False),
        ("https://website.example:8443", (WEBSITE,), False),
        ("http://website.example", (WEBSITE,), False),
        ("https://WEBSITE.example", (WEBSITE,), False),
        ("https://website.example/", (WEBSITE,), False),
        ("https://anything.example", ("*",), False),
        ("https://anything.example", ("https://*.example",), False),
    ],
)
def test_an_origin_is_allowed_only_by_an_exact_entry(
    origin: str | None, allowed: tuple[str, ...], expected: bool
) -> None:
    assert origin_allowed(origin, allowed) is expected


PATH = "/api/v1/public/demo-requests"


def _cors_app(*, allow: tuple[str, ...] = (WEBSITE,), leaky: bool = False) -> FastAPI:
    app = FastAPI(middleware=[Middleware(ScopedCorsMiddleware, path=PATH, allow_origins=allow)])

    @app.post(PATH)
    async def accept() -> JSONResponse:
        headers = (
            {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true"}
            if leaky
            else None
        )
        return JSONResponse({"status": "received"}, status_code=202, headers=headers)

    @app.post("/api/v1/elsewhere")
    async def elsewhere() -> dict[str, str]:
        return {"ok": "yes"}

    return app


@pytest.fixture
async def cors_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=_cors_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _cors_headers(response: httpx.Response) -> dict[str, str]:
    return {k: v for k, v in response.headers.items() if k.startswith("access-control-")}


async def test_a_preflight_from_an_allowed_origin_gets_the_policy_and_nothing_wider(
    cors_client: httpx.AsyncClient,
) -> None:
    response = await cors_client.options(
        PATH,
        headers={
            "Origin": WEBSITE,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 204
    assert _cors_headers(response) == {
        "access-control-allow-origin": WEBSITE,
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "Content-Type",
        "access-control-max-age": "600",
    }
    assert response.headers["vary"] == "Origin"
    assert "access-control-allow-credentials" not in response.headers


async def test_a_preflight_from_any_other_origin_gets_no_cors_headers(
    cors_client: httpx.AsyncClient,
) -> None:
    for origin in ("https://evil.example", "https://website.example.evil.test", "null"):
        response = await cors_client.options(
            PATH, headers={"Origin": origin, "Access-Control-Request-Method": "POST"}
        )
        assert response.status_code == 403
        assert _cors_headers(response) == {}
        assert response.headers["vary"] == "Origin"


async def test_an_options_request_that_is_not_a_preflight_is_left_to_the_app(
    cors_client: httpx.AsyncClient,
) -> None:
    for headers in ({}, {"Origin": WEBSITE}):
        response = await cors_client.options(PATH, headers=headers)
        assert response.status_code == 405
        assert response.headers.get("access-control-allow-methods") is None


async def test_an_answer_to_an_allowed_origin_carries_its_allow_header_and_exposes_retry_after(
    cors_client: httpx.AsyncClient,
) -> None:
    response = await cors_client.post(PATH, headers={"Origin": WEBSITE})
    assert response.status_code == 202
    assert _cors_headers(response) == {
        "access-control-allow-origin": WEBSITE,
        "access-control-expose-headers": "Retry-After",
    }
    assert response.headers["vary"] == "Origin"


async def test_an_answer_to_any_other_origin_has_no_cors_header_at_all(
    cors_client: httpx.AsyncClient,
) -> None:
    for headers in ({"Origin": "https://evil.example"}, {"Origin": "null"}, {}):
        response = await cors_client.post(PATH, headers=headers)
        assert response.status_code == 202
        assert _cors_headers(response) == {}
        assert response.headers["vary"] == "Origin"


async def test_other_paths_are_not_touched() -> None:
    app = _cors_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/elsewhere", headers={"Origin": WEBSITE})
        assert _cors_headers(response) == {}
        assert "vary" not in response.headers
        preflight = await client.options(
            "/api/v1/elsewhere",
            headers={"Origin": WEBSITE, "Access-Control-Request-Method": "POST"},
        )
        assert _cors_headers(preflight) == {}


async def test_the_policy_is_this_one_whatever_another_layer_wrote() -> None:
    """A global CORS layer that put credentials on the response must not leak them onto
    this route: the policy here is the whole policy."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_cors_app(leaky=True)), base_url="http://test"
    ) as client:
        allowed = await client.post(PATH, headers={"Origin": WEBSITE})
        assert _cors_headers(allowed) == {
            "access-control-allow-origin": WEBSITE,
            "access-control-expose-headers": "Retry-After",
        }
        refused = await client.post(PATH, headers={"Origin": "https://evil.example"})
        assert _cors_headers(refused) == {}


async def test_an_error_answer_carries_the_allow_header_too() -> None:
    """A route's own headers are lost when it raises, which is why this is middleware:
    the site has to be able to read a 429 and its Retry-After."""
    app = FastAPI(
        middleware=[
            Middleware(
                ScopedCorsMiddleware, path="/api/v1/public/refused", allow_origins=(WEBSITE,)
            )
        ]
    )

    @app.post("/api/v1/public/refused")
    async def refused() -> None:
        raise HTTPException(status_code=429, headers={"Retry-After": "30"})

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/public/refused", headers={"Origin": WEBSITE})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    assert response.headers["access-control-allow-origin"] == WEBSITE
    assert response.headers["access-control-expose-headers"] == "Retry-After"


# ---------------------------------------------------------------------------
# The rate limits
# ---------------------------------------------------------------------------


def _request(peer: str | None, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 5000) if peer else None})


def test_the_three_limits_are_the_agreed_ones() -> None:
    assert ratelimit.DEMO_ADDRESS == ratelimit.Limit(requests=5, window_seconds=3600)
    assert ratelimit.DEMO_EMAIL == ratelimit.Limit(requests=3, window_seconds=86400)
    assert ratelimit.DEMO_CEILING == ratelimit.Limit(requests=300, window_seconds=86400)


@pytest.fixture
def charged(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, ratelimit.Limit]]:
    calls: list[tuple[str, str, ratelimit.Limit]] = []

    async def record(bucket: str, identity: str, limit: ratelimit.Limit) -> None:
        calls.append((bucket, identity, limit))

    monkeypatch.setattr(ratelimit, "check", record)
    return calls


async def test_a_request_is_charged_to_its_caller_then_its_requester_then_the_day(
    charged: list[tuple[str, str, ratelimit.Limit]],
) -> None:
    await ratelimit.limit_demo_request(
        _request("172.18.0.2", "8.8.8.8, 172.18.0.2"), "Ada@Example.com"
    )
    assert charged == [
        ("demo_address", "8.8.8.8", ratelimit.DEMO_ADDRESS),
        ("demo_email", ratelimit.account_identity("ada@example.com"), ratelimit.DEMO_EMAIL),
        ("demo_ceiling", "all", ratelimit.DEMO_CEILING),
    ]


async def test_an_unknown_caller_is_limited_by_requester_and_day_only(
    charged: list[tuple[str, str, ratelimit.Limit]],
) -> None:
    await ratelimit.limit_demo_request(_request("172.18.0.2"), "ada@example.com")
    assert [bucket for bucket, _, _ in charged] == ["demo_email", "demo_ceiling"]


async def test_the_requester_is_bucketed_by_a_hash_and_never_by_the_address(
    charged: list[tuple[str, str, ratelimit.Limit]],
) -> None:
    await ratelimit.limit_demo_request(_request("8.8.8.8"), "ada@example.com")
    identities = " ".join(identity for _, identity, _ in charged)
    assert "ada" not in identities
    assert "example.com" not in identities


async def test_a_caller_turned_away_early_never_spends_the_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def refuse_the_requester(bucket: str, identity: str, limit: ratelimit.Limit) -> None:
        seen.append(bucket)
        if bucket == "demo_email":
            raise RateLimited(retry_after_seconds=10)

    monkeypatch.setattr(ratelimit, "check", refuse_the_requester)
    with pytest.raises(RateLimited):
        await ratelimit.limit_demo_request(_request("8.8.8.8"), "ada@example.com")
    assert seen == ["demo_address", "demo_email"], "the day's ceiling was never charged"


# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------


def test_the_defaults_notify_the_owner_and_confirm_but_allow_no_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("LEADS_NOTIFY_EMAIL", "LEADS_ALLOWED_ORIGINS", "LEADS_CONFIRM_REQUESTER"):
        monkeypatch.delenv(name, raising=False)
    config = LeadsSettings()
    assert config.notify_email == "mehboobarshad300@gmail.com"
    assert config.confirm_requester is True
    assert config.allowed_origins == ()


def test_the_environment_overrides_all_three(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEADS_NOTIFY_EMAIL", "sales@verity.example")
    monkeypatch.setenv("LEADS_CONFIRM_REQUESTER", "false")
    monkeypatch.setenv(
        "LEADS_ALLOWED_ORIGINS",
        '["https://website.37-60-228-227.sslip.io", "http://localhost:5174"]',
    )
    config = LeadsSettings()
    assert config.notify_email == "sales@verity.example"
    assert config.confirm_requester is False
    assert config.allowed_origins == (
        "https://website.37-60-228-227.sslip.io",
        "http://localhost:5174",
    )


@pytest.mark.parametrize("empty", ["", "   "])
def test_an_empty_notify_address_turns_the_mail_off(
    monkeypatch: pytest.MonkeyPatch, empty: str
) -> None:
    monkeypatch.setenv("LEADS_NOTIFY_EMAIL", empty)
    assert LeadsSettings().notify_email is None


@pytest.mark.parametrize(
    "address",
    [
        "no-at-sign",
        "two@example.com, three@example.com",
        "a@example.com;b@example.com",
        "Owner <owner@example.com>",
        "owner@example.com\r\nBcc: x@example.net",
        "owner @example.com",
    ],
)
def test_a_notify_value_that_is_not_one_address_refuses_to_load(address: str) -> None:
    with pytest.raises(ValidationError, match="one email address"):
        LeadsSettings(notify_email=address)


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://example.com/",
        "https://example.com/path",
        "example.com",
        "ftp://example.com",
        "https://",
        "https://example.com:notaport",
        "https://example.com, https://other.example",
    ],
)
def test_an_origin_that_is_not_exact_refuses_to_load(origin: str) -> None:
    with pytest.raises(ValidationError, match="exact origins"):
        LeadsSettings(allowed_origins=(origin,))


def test_an_origin_is_lower_cased_so_it_matches_what_a_browser_sends() -> None:
    config = LeadsSettings(allowed_origins=(" HTTPS://Website.Example ",))
    assert config.allowed_origins == ("https://website.example",)


def test_the_settings_object_carries_the_section() -> None:
    assert Settings.model_fields["leads"].annotation is LeadsSettings


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


class _Recorder:
    """A logger that keeps what it was told, so a test can search it for personal data."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def _keep(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))

    info = warning = error = _keep

    def dump(self) -> str:
        return repr(self.events)


async def test_a_failed_insert_is_a_plain_503_and_the_drivers_message_is_never_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaked = "ada@example.com"

    class Boom:
        async def __aenter__(self) -> None:
            raise DBAPIError(
                "INSERT INTO demo_requests ...",
                {"email": leaked, "full_name": "Ada Lovelace"},
                Exception(f"invalid byte sequence in {leaked}"),
            )

        async def __aexit__(self, *exc: object) -> None:
            return None

    recorder = _Recorder()
    monkeypatch.setattr(leads_module, "logger", recorder)
    monkeypatch.setattr(leads_module, "provider_session_scope", Boom)

    with pytest.raises(ServiceUnavailable) as caught:
        await LeadsService().submit(_lead(email=leaked))

    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True, "the driver's error must not be chained"
    assert recorder.events == [("leads.store_failed", {"error": "DBAPIError"})]
    for private in (leaked, "Ada", "Lovelace", "Analytical"):
        assert private not in recorder.dump()


async def test_a_honeypot_hit_writes_one_nameless_log_line_and_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(leads_module, "logger", recorder)

    def forbidden() -> None:
        raise AssertionError("a honeypot hit must not open a transaction")

    monkeypatch.setattr(leads_module, "provider_session_scope", forbidden)
    assert await LeadsService().submit(_lead(website="http://spam.example")) is None
    assert recorder.events == [("leads.honeypot", {})]
