"""Provider authentication through the real app: password → challenge → TOTP → session.

No dependency overrides anywhere in this file — the routes, the services, the token
validation, the database rows, and the audit trail are all real. The suites commit
rows (failed attempts must outlive their 401), so the clean fixtures truncate as the
owner around each test.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from tests.support.tenancy import (
    ADMIN_PASSWORD,
    bearer,
    provider_session_headers,
    seed_admin,
    totp_code,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine, provider_session_scope
from verity.core.errors import InvalidToken
from verity.core.security import decode_token
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import audit_service

pytestmark = pytest.mark.integration

LOGIN_URL = "/api/v1/provider/login"
VERIFY_URL = "/api/v1/provider/mfa/verify"
ENROLL_URL = "/api/v1/provider/mfa/enroll"
CONFIRM_URL = "/api/v1/provider/mfa/confirm"
TENANTS_URL = "/api/v1/provider/tenants"


@pytest.fixture(autouse=True)
async def _clean_state(clean_tenancy: None, clean_audit_log: None) -> AsyncIterator[None]:
    """Empty tables and a per-test process engine for the routes' session scopes."""
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _provider_stream() -> list[AuditLog]:
    """Every committed provider-plane audit row (tenant_id IS NULL), newest first."""
    async with provider_session_scope() as session:
        entries, _ = await audit_service.list_page(session, tenant_id=None, limit=100)
    return entries


def _attempt_outcomes(entries: list[AuditLog]) -> list[str]:
    return [
        str(entry.after["outcome"])
        for entry in entries
        if entry.object_type == "auth_attempt" and entry.after
    ]


async def _login(client: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    return await client.post(LOGIN_URL, json={"email": email, "password": password})


async def test_correct_password_yields_a_challenge_and_never_a_session(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin()
    response = await _login(client, admin.email, ADMIN_PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert body["next_step"] == "mfa_verify"
    assert body["challenge_token"]
    assert "token" not in body, "a password alone must never buy a session"
    # The challenge permits the TOTP step and nothing else: it is not a session.
    with pytest.raises(InvalidToken):
        decode_token(body["challenge_token"], expected_typ="session")


async def test_the_full_login_issues_a_session_and_audits_it(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin()
    assert admin.totp_secret is not None
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]

    response = await client.post(
        VERIFY_URL,
        json={"challenge_token": challenge, "code": totp_code(admin.totp_secret)},
    )
    assert response.status_code == 200
    body = response.json()
    claims = decode_token(body["token"], expected_typ="session", expected_plane="provider")
    assert claims.subject == admin.id
    assert body["expires_at"].endswith("Z")

    sessions = [entry for entry in await _provider_stream() if entry.object_type == "session"]
    assert len(sessions) == 1
    assert sessions[0].action == "create"
    assert sessions[0].object_id == claims.jti, "decision 2: object_id is the token's jti"
    assert sessions[0].actor_type == "platform_admin"
    assert sessions[0].actor_id == admin.id


async def test_a_wrong_code_is_401_and_the_attempt_is_recorded(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin()
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]

    response = await client.post(VERIFY_URL, json={"challenge_token": challenge, "code": "000000"})
    assert response.status_code == 401
    assert "failed_totp" in _attempt_outcomes(await _provider_stream())


async def test_a_replayed_code_is_refused(client: httpx.AsyncClient) -> None:
    admin = await seed_admin()
    assert admin.totp_secret is not None
    code = totp_code(admin.totp_secret)

    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    first = await client.post(VERIFY_URL, json={"challenge_token": challenge, "code": code})
    assert first.status_code == 200

    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    replay = await client.post(VERIFY_URL, json={"challenge_token": challenge, "code": code})
    assert replay.status_code == 401, "a code inside its window must not be accepted twice"

    # The *next* window's code is fine — the guard is the counter, not a lockout.
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    fresh = await client.post(
        VERIFY_URL,
        json={"challenge_token": challenge, "code": totp_code(admin.totp_secret, step_offset=1)},
    )
    assert fresh.status_code == 200


async def test_unknown_email_matches_wrong_password_in_content_and_wall_time(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin()

    async def timed(email: str) -> tuple[float, dict[str, str]]:
        start = time.perf_counter()
        response = await _login(client, email, "not-the-password")
        elapsed = time.perf_counter() - start
        assert response.status_code == 401
        return elapsed, response.json()["error"]

    await timed("warm-the-dummy-hash@nowhere.example")  # first call builds the dummy hash

    unknown_times, wrong_times = [], []
    for _ in range(3):
        elapsed, unknown_error = await timed("ghost@nowhere.example")
        unknown_times.append(elapsed)
        elapsed, wrong_error = await timed(admin.email)
        wrong_times.append(elapsed)
        assert unknown_error["code"] == wrong_error["code"]
        assert unknown_error["message"] == wrong_error["message"]

    unknown, wrong = statistics.median(unknown_times), statistics.median(wrong_times)
    # Both paths burn one argon2 verification (~tens of ms); an unknown email that
    # skipped it would return an order of magnitude faster. Loose bound, no flake.
    assert unknown > wrong / 3
    assert wrong > unknown / 3

    outcomes = _attempt_outcomes(await _provider_stream())
    assert outcomes.count("failed_password") == 7  # every attempt above, both kinds


async def test_a_disabled_admin_gets_401_with_correct_credentials(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin(status="disabled")
    response = await _login(client, admin.email, ADMIN_PASSWORD)
    assert response.status_code == 401
    assert "admin_disabled" in _attempt_outcomes(await _provider_stream())


async def test_an_unenrolled_admin_is_directed_to_enrollment_with_no_shortcut(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin(enrolled=False)
    body = (await _login(client, admin.email, ADMIN_PASSWORD)).json()
    assert body["next_step"] == "mfa_enroll"
    # The challenge cannot be spent on the verify route to skip enrollment.
    response = await client.post(
        VERIFY_URL, json={"challenge_token": body["challenge_token"], "code": "123456"}
    )
    assert response.status_code == 401


async def test_enrollment_confirm_enables_mfa_issues_session_and_recovery_codes(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin(enrolled=False)
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]

    enroll = await client.post(ENROLL_URL, json={"challenge_token": challenge})
    assert enroll.status_code == 200
    secret = enroll.json()["secret"]
    assert "otpauth://" in enroll.json()["otpauth_uri"]

    confirm = await client.post(
        CONFIRM_URL, json={"challenge_token": challenge, "code": totp_code(secret)}
    )
    assert confirm.status_code == 200
    body = confirm.json()
    decode_token(body["token"], expected_typ="session", expected_plane="provider")
    assert len(body["recovery_codes"]) == 8

    stream = await _provider_stream()
    assert [e.object_type for e in stream if e.object_type == "mfa_enrollment"] == [
        "mfa_enrollment"
    ]
    assert any(e.object_type == "session" for e in stream)

    # Confirming is what enables MFA: the next login goes down the verify path.
    body = (await _login(client, admin.email, ADMIN_PASSWORD)).json()
    assert body["next_step"] == "mfa_verify"


async def test_a_wrong_code_at_confirm_does_not_enable_mfa(client: httpx.AsyncClient) -> None:
    admin = await seed_admin(enrolled=False)
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    assert (await client.post(ENROLL_URL, json={"challenge_token": challenge})).status_code == 200

    confirm = await client.post(CONFIRM_URL, json={"challenge_token": challenge, "code": "000000"})
    assert confirm.status_code == 401
    assert "failed_totp" in _attempt_outcomes(await _provider_stream())
    body = (await _login(client, admin.email, ADMIN_PASSWORD)).json()
    assert body["next_step"] == "mfa_enroll", "MFA must not be enabled by a failed confirm"


async def test_a_recovery_code_works_exactly_once(client: httpx.AsyncClient) -> None:
    admin = await seed_admin(enrolled=False)
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    secret = (await client.post(ENROLL_URL, json={"challenge_token": challenge})).json()["secret"]
    codes = (
        await client.post(
            CONFIRM_URL, json={"challenge_token": challenge, "code": totp_code(secret)}
        )
    ).json()["recovery_codes"]

    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    first = await client.post(
        VERIFY_URL, json={"challenge_token": challenge, "recovery_code": codes[0]}
    )
    assert first.status_code == 200

    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    second = await client.post(
        VERIFY_URL, json={"challenge_token": challenge, "recovery_code": codes[0]}
    )
    assert second.status_code == 401, "a recovery code is consumed by the use that accepts it"
    assert "failed_recovery_code" in _attempt_outcomes(await _provider_stream())


async def test_verify_requires_exactly_one_second_factor(client: httpx.AsyncClient) -> None:
    admin = await seed_admin()
    assert admin.totp_secret is not None
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    both = await client.post(
        VERIFY_URL,
        json={
            "challenge_token": challenge,
            "code": totp_code(admin.totp_secret),
            "recovery_code": "aaaaa-aaaaa",
        },
    )
    assert both.status_code == 422
    neither = await client.post(VERIFY_URL, json={"challenge_token": challenge})
    assert neither.status_code == 422


async def test_a_challenge_token_opens_no_provider_route(client: httpx.AsyncClient) -> None:
    admin = await seed_admin()
    challenge = (await _login(client, admin.email, ADMIN_PASSWORD)).json()["challenge_token"]
    response = await client.get(TENANTS_URL, headers=bearer(challenge))
    assert response.status_code == 401, "a challenge is not a session and must not act as one"


async def test_a_session_token_is_refused_by_the_challenge_consuming_route(
    client: httpx.AsyncClient,
) -> None:
    admin = await seed_admin()
    session_token = provider_session_headers(admin.id)["Authorization"].removeprefix("Bearer ")
    response = await client.post(
        VERIFY_URL,
        json={"challenge_token": session_token.strip(), "code": "123456"},
    )
    assert response.status_code == 401, "the typ claim keeps the two token kinds apart"
