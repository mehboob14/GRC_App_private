"""Sign in is rate limited, through the real app and the real Redis.

The counters are cleared before each test by the autouse fixture in ``conftest``. The
limits asserted are the shipped ones, except the address limit, which a test lowers so
a hundred requests are not needed to reach it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import SIGNUP_PASSWORD, signup_workspace
from tests.support.tenancy import totp_code
from verity.core import ratelimit
from verity.core.config import Settings
from verity.core.db import dispose_engine
from verity.main import create_app

pytestmark = pytest.mark.integration

WRONG_PASSWORD = "wrong-password-1"  # noqa: S105 — test value, never a real credential
LOGIN_URL = "/api/v1/auth/login"
VERIFY_URL = "/api/v1/auth/mfa/verify"
RESET_URL = "/api/v1/auth/password-reset"
PROVIDER_LOGIN_URL = "/api/v1/provider/login"


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
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _login(
    client: httpx.AsyncClient, email: str, password: str = WRONG_PASSWORD
) -> httpx.Response:
    return await client.post(LOGIN_URL, json={"email": email, "password": password})


async def test_the_eleventh_attempt_on_one_account_is_429_with_a_retry_time(
    client: httpx.AsyncClient,
) -> None:
    for _ in range(ratelimit.LOGIN_ACCOUNT.requests):
        assert (await _login(client, "ada@example.com")).status_code == 401

    blocked = await _login(client, "ada@example.com")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= ratelimit.LOGIN_ACCOUNT.window_seconds
    # The wall does not depend on the account existing, so it tells a prober nothing.
    assert "ada@example.com" not in blocked.text


async def test_a_blocked_account_is_blocked_even_with_the_right_password(
    client: httpx.AsyncClient,
) -> None:
    workspace = await signup_workspace()
    for _ in range(ratelimit.LOGIN_ACCOUNT.requests):
        await _login(client, workspace.email)

    right = await _login(client, workspace.email, SIGNUP_PASSWORD)
    assert right.status_code == 429


async def test_another_account_is_not_affected(client: httpx.AsyncClient) -> None:
    for _ in range(ratelimit.LOGIN_ACCOUNT.requests + 1):
        await _login(client, "ada@example.com")

    other = await _login(client, "grace@example.com")
    assert other.status_code == 401, "a different account has its own allowance"


async def test_one_address_trying_many_accounts_is_stopped(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ratelimit, "LOGIN_ADDRESS", ratelimit.Limit(requests=3, window_seconds=900))
    for index in range(3):
        assert (await _login(client, f"user{index}@example.com")).status_code == 401

    blocked = await _login(client, "user99@example.com")
    assert blocked.status_code == 429


async def test_code_guesses_are_limited_per_challenge(client: httpx.AsyncClient) -> None:
    workspace = await signup_workspace()
    login = await client.post(
        LOGIN_URL, json={"email": workspace.email, "password": SIGNUP_PASSWORD}
    )
    challenge = login.json()["challenge_token"]

    for _ in range(ratelimit.MFA_ATTEMPTS.requests):
        guess = await client.post(VERIFY_URL, json={"challenge_token": challenge, "code": "000000"})
        assert guess.status_code == 401

    # Past the limit even the right code is refused: the challenge is spent.
    right = totp_code(workspace.totp_secret, step_offset=1)
    refused = await client.post(VERIFY_URL, json={"challenge_token": challenge, "code": right})
    assert refused.status_code == 429


async def test_reset_mail_is_limited_per_recipient(client: httpx.AsyncClient) -> None:
    for _ in range(ratelimit.EMAIL_ACTIONS.requests):
        sent = await client.post(RESET_URL, json={"email": "ada@example.com"})
        assert sent.status_code == 202

    bombed = await client.post(RESET_URL, json={"email": "ada@example.com"})
    assert bombed.status_code == 429
    other = await client.post(RESET_URL, json={"email": "grace@example.com"})
    assert other.status_code == 202


async def test_provider_login_is_limited_the_same_way(client: httpx.AsyncClient) -> None:
    body = {"email": "admin@verity.example", "password": WRONG_PASSWORD}
    for _ in range(ratelimit.LOGIN_ACCOUNT.requests):
        assert (await client.post(PROVIDER_LOGIN_URL, json=body)).status_code == 401

    blocked = await client.post(PROVIDER_LOGIN_URL, json=body)
    assert blocked.status_code == 429
