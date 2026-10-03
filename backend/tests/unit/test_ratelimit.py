"""The address and identity helpers the sign in limits depend on. The counting itself
needs Redis and is covered through the app in ``tests/integration/test_auth_rate_limit.py``."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from verity.core import ratelimit
from verity.core.errors import RateLimited


def _request(peer: str | None, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (peer, 5000) if peer else None,
    }
    return Request(scope)


def test_the_real_address_is_believed_only_from_a_proxy_on_our_network() -> None:
    forwarded = {"X-Real-IP": "203.0.113.9"}
    assert ratelimit.client_address(_request("172.18.0.5", forwarded)) == "203.0.113.9"
    assert ratelimit.client_address(_request("127.0.0.1", forwarded)) == "203.0.113.9"
    # A caller reaching the API directly cannot pick their own bucket with a header.
    assert ratelimit.client_address(_request("8.8.8.8", forwarded)) == "8.8.8.8"


def test_a_garbled_or_missing_forwarded_address_falls_back_to_the_peer() -> None:
    garbled = _request("172.18.0.5", {"X-Real-IP": "not-an-ip"})
    assert ratelimit.client_address(garbled) == "172.18.0.5"
    assert ratelimit.client_address(_request("172.18.0.5")) == "172.18.0.5"
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
