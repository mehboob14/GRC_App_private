"""The address and identity helpers the sign in limits depend on. The counting itself
needs Redis and is covered through the app in ``tests/integration/test_auth_rate_limit.py``."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from verity.core import ratelimit
from verity.core.errors import RateLimited


def _request(peer: str | None, forwarded: list[str] | None = None) -> Request:
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded or []]
    return Request({"type": "http", "headers": headers, "client": (peer, 5000) if peer else None})


def test_the_real_address_is_found_through_one_proxy_or_two() -> None:
    # One proxy hop: it appended the address it saw.
    assert ratelimit.client_address(_request("172.18.0.5", ["8.8.8.8"])) == "8.8.8.8"
    # Two hops, as in production (edge nginx, then the web container's nginx).
    assert ratelimit.client_address(_request("172.18.0.5", ["8.8.8.8, 172.18.0.2"])) == "8.8.8.8"


def test_an_address_a_caller_put_to_the_left_is_never_reached() -> None:
    spoofed = ["6.6.6.6, 8.8.8.8, 172.18.0.2"]
    assert ratelimit.client_address(_request("172.18.0.5", spoofed)) == "8.8.8.8"
    # A header split over several lines reads the same as one joined line.
    split = ["6.6.6.6", "8.8.8.8, 172.18.0.2"]
    assert ratelimit.client_address(_request("172.18.0.5", split)) == "8.8.8.8"


def test_a_caller_reaching_the_api_directly_cannot_choose_their_bucket() -> None:
    assert ratelimit.client_address(_request("1.1.1.1", ["8.8.8.8"])) == "1.1.1.1"


def test_a_garbled_private_or_missing_chain_falls_back_to_the_peer() -> None:
    assert ratelimit.client_address(_request("172.18.0.5", ["not-an-ip"])) == "172.18.0.5"
    assert ratelimit.client_address(_request("172.18.0.5", ["10.1.2.3"])) == "172.18.0.5"
    assert ratelimit.client_address(_request("172.18.0.5")) == "172.18.0.5"
    assert ratelimit.client_address(_request("127.0.0.1")) == "127.0.0.1"
    assert ratelimit.client_address(_request(None)) == "unattributed"


def test_an_account_is_the_same_bucket_however_the_email_is_written() -> None:
    key = ratelimit.account_identity("Ada@Example.com")
    assert key == ratelimit.account_identity("  ada@example.COM ")
    assert key != ratelimit.account_identity("grace@example.com")
    assert "ada" not in key, "the key reaches Redis and the logs: no raw email"


def test_a_challenge_is_bucketed_by_its_hash_not_its_token() -> None:
    token = "challenge.token.value"  # noqa: S105 — a label, not a credential
    key = ratelimit.challenge_identity(token)
    assert token not in key
    assert key == ratelimit.challenge_identity(token)


def test_a_limit_needs_a_request_and_a_window() -> None:
    with pytest.raises(ValueError, match="at least one request"):
        ratelimit.Limit(requests=0, window_seconds=60)
    with pytest.raises(ValueError, match="at least one request"):
        ratelimit.Limit(requests=1, window_seconds=0)


def test_seconds_left_counts_down_to_the_end_of_the_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limit = ratelimit.Limit(requests=1, window_seconds=900)
    monkeypatch.setattr(ratelimit, "_now", lambda: 1_000_000 * 900 + 100)
    assert ratelimit._seconds_left(limit) == 800
    monkeypatch.setattr(ratelimit, "_now", lambda: 1_000_000 * 900)
    assert ratelimit._seconds_left(limit) == 900


def test_a_rate_limited_error_carries_its_retry_time() -> None:
    assert RateLimited(retry_after_seconds=42).retry_after_seconds == 42
    assert RateLimited().retry_after_seconds is None
