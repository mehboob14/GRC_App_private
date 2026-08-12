"""Secret redaction in the log pipeline (rule 6)."""

from __future__ import annotations

import pytest

from verity.core.logging import REDACTED, TRUNCATED, is_sensitive_key, redact_sensitive

SENSITIVE_VALUE = "s3cr3t-value-that-must-never-be-written"


def _process(event: dict[str, object]) -> dict[str, object]:
    return dict(redact_sensitive(None, "info", event))


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "passwd",
        "passphrase",
        "secret",
        "client_secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "connector_credentials",
        "cookie",
        "set-cookie",
        "private_key",
        "encryption_key",
        "master_key",
        "mfa_secret",
        "totp_seed",
        "signature",
        "key",
        "keys",
        "dek",
        "otp",
        "pwd",
        "auth",
        "AUTHORIZATION",
        "Password",
    ],
)
def test_sensitive_names_are_recognised(key: str) -> None:
    assert is_sensitive_key(key)


@pytest.mark.parametrize(
    "key",
    ["tenant_id", "user_id", "control_code", "status", "monkey", "keyboard_layout", "path"],
)
def test_ordinary_names_are_left_alone(key: str) -> None:
    assert not is_sensitive_key(key)


def test_top_level_secret_is_replaced() -> None:
    assert _process({"event": "login", "password": SENSITIVE_VALUE}) == {
        "event": "login",
        "password": REDACTED,
    }


def test_nested_secret_is_replaced() -> None:
    processed = _process(
        {"connection": {"host": "db.internal", "credentials": {"password": SENSITIVE_VALUE}}}
    )
    assert processed == {
        "connection": {"host": "db.internal", "credentials": REDACTED},
    }


def test_secret_inside_a_list_is_replaced() -> None:
    processed = _process({"attempts": [{"user": "a@example.com", "password": SENSITIVE_VALUE}]})
    assert processed == {"attempts": [{"user": "a@example.com", "password": REDACTED}]}


def test_secret_does_not_survive_anywhere_in_the_rendered_event() -> None:
    """The assertion that actually matters: the value is gone, wherever it was."""
    processed = _process(
        {
            "event": "connector.sync",
            "api_key": SENSITIVE_VALUE,
            "config": {"nested": {"deeper": {"token": SENSITIVE_VALUE}}},
            "history": [[{"secret": SENSITIVE_VALUE}]],
        }
    )
    assert SENSITIVE_VALUE not in repr(processed)


def test_deep_nesting_is_truncated_rather_than_recursed_forever() -> None:
    event: dict[str, object] = {"level": "leaf"}
    for _ in range(20):
        event = {"level": event}
    assert TRUNCATED in repr(_process(event))


def test_ordinary_values_pass_through_unchanged() -> None:
    event = {"event": "control.updated", "tenant_id": "abc", "count": 3, "ok": True}
    assert _process(dict(event)) == event
