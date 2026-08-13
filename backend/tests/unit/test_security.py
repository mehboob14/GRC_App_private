"""The shared authentication primitives: passwords, TOTP, signed tokens.

No database. The properties asserted here are the ones both planes' login flows
lean on: timing-indistinguishable unknown-email handling, TOTP replay refusal, and
tokens that fail closed with one uniform error.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest
from argon2 import PasswordHasher

from verity.core import security
from verity.core.config import get_settings
from verity.core.errors import AuthenticationRequired, InvalidToken
from verity.core.security import (
    TOKEN_PLANES,
    TOKEN_TYPES,
    TokenClaims,
    decode_token,
    hash_password,
    issue_token,
    new_totp_secret,
    totp_provisioning_uri,
    verify_password,
    verify_totp,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_a_password_round_trips() -> None:
    hashed = hash_password("correct horse battery staple")
    result = verify_password(hashed, "correct horse battery staple")
    assert result.ok is True
    assert result.needs_rehash is False


def test_a_wrong_password_is_refused() -> None:
    hashed = hash_password("correct horse battery staple")
    result = verify_password(hashed, "wrong horse")
    assert result.ok is False
    assert result.needs_rehash is False


def test_parameters_are_pinned_to_the_approved_values() -> None:
    """argon2id, t=3, m=64 MiB, p=4 — add-provider-plane/design.md. The encoded hash
    carries its parameters, so the pin is observable rather than trusted."""
    hashed = hash_password("anything")
    assert hashed.startswith("$argon2id$")
    assert "m=65536,t=3,p=4" in hashed


def test_a_hash_under_older_parameters_reports_needs_rehash() -> None:
    weaker = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2)
    hashed = weaker.hash("still the right password")
    result = verify_password(hashed, "still the right password")
    assert result.ok is True
    assert result.needs_rehash is True


@pytest.mark.parametrize("bad_hash", ["", "not-a-hash", "$argon2id$corrupt"])
def test_a_malformed_or_absent_hash_refuses_without_raising(bad_hash: str) -> None:
    result = verify_password(bad_hash, "whatever")
    assert result.ok is False
    assert result.needs_rehash is False


def test_a_missing_hash_costs_a_real_verification() -> None:
    """The unknown-email path must take comparable time to a wrong password.

    A miss that returns in microseconds while a mismatch takes tens of milliseconds
    enumerates which emails exist. Argon2 at these parameters is four orders of
    magnitude above a string check, so a generous margin still catches a skipped
    dummy verification without being flaky.
    """
    hashed = hash_password("a real password")
    verify_password("", "warm the cached dummy hash")

    real = min(_timed(lambda: verify_password(hashed, "wrong")) for _ in range(3))
    miss = min(_timed(lambda: verify_password("", "wrong")) for _ in range(3))
    assert miss >= real * 0.2, f"unknown-email path too fast: {miss:.4f}s vs {real:.4f}s"


def _timed(action: Callable[[], object]) -> float:
    start = time.perf_counter()
    action()
    return time.perf_counter() - start


# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------

# A fixed, published test vector so every assertion is deterministic — not a credential.
_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"  # noqa: S105
_FIXED_TIME = 1_700_000_000
_FIXED_STEP = _FIXED_TIME // 30


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(security, "_now", lambda: float(_FIXED_TIME))
    return _FIXED_TIME


def _code_at(timestamp: int) -> str:
    """What an authenticator app would show at ``timestamp`` (pyotp defaults match
    the module's period, digits, and digest)."""
    return str(pyotp.TOTP(_SECRET).at(timestamp))


def test_a_new_secret_is_fresh_base32() -> None:
    first, second = new_totp_secret(), new_totp_secret()
    assert first != second
    assert len(first) == 32
    assert set(first) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def test_the_provisioning_uri_names_account_and_issuer() -> None:
    uri = totp_provisioning_uri(_SECRET, "admin@example.com")
    assert uri.startswith("otpauth://totp/")
    assert "admin%40example.com" in uri
    assert "issuer=Verity" in uri


def test_a_current_code_verifies_and_reports_its_counter(frozen_clock: int) -> None:
    result = verify_totp(_SECRET, _code_at(_FIXED_TIME), None)
    assert result.ok is True
    assert result.counter == _FIXED_STEP


def test_a_wrong_code_is_refused(frozen_clock: int) -> None:
    wrong = "000000" if _code_at(_FIXED_TIME) != "000000" else "999999"
    result = verify_totp(_SECRET, wrong, None)
    assert result.ok is False
    assert result.counter is None


@pytest.mark.parametrize("junk", ["", "12345", "1234567", "abcdef", "12 34"])
def test_junk_input_is_refused(frozen_clock: int, junk: str) -> None:
    assert verify_totp(_SECRET, junk, None).ok is False


def test_a_code_with_spaces_is_accepted(frozen_clock: int) -> None:
    """Authenticator apps display '123 456'; people type what they see."""
    code = _code_at(_FIXED_TIME)
    spaced = f"{code[:3]} {code[3:]}"
    assert verify_totp(_SECRET, spaced, None).ok is True


def test_one_step_of_clock_skew_is_tolerated_either_side(frozen_clock: int) -> None:
    previous = verify_totp(_SECRET, _code_at(_FIXED_TIME - 30), None)
    upcoming = verify_totp(_SECRET, _code_at(_FIXED_TIME + 30), None)
    assert previous.ok is True
    assert previous.counter == _FIXED_STEP - 1
    assert upcoming.ok is True
    assert upcoming.counter == _FIXED_STEP + 1


@pytest.mark.parametrize("offset", [-60, 60])
def test_two_steps_away_is_refused(frozen_clock: int, offset: int) -> None:
    assert verify_totp(_SECRET, _code_at(_FIXED_TIME + offset), None).ok is False


def test_a_replayed_code_is_refused_even_though_still_in_window(frozen_clock: int) -> None:
    """The 30-second replay hole pyotp leaves open, closed by the stored counter."""
    code = _code_at(_FIXED_TIME)
    first = verify_totp(_SECRET, code, None)
    assert first.ok is True
    replay = verify_totp(_SECRET, code, first.counter)
    assert replay.ok is False
    assert replay.counter is None


def test_a_code_at_or_before_the_last_counter_is_refused(frozen_clock: int) -> None:
    stale = verify_totp(_SECRET, _code_at(_FIXED_TIME - 30), _FIXED_STEP)
    assert stale.ok is False


def test_a_code_after_the_last_counter_is_accepted(frozen_clock: int) -> None:
    result = verify_totp(_SECRET, _code_at(_FIXED_TIME), _FIXED_STEP - 1)
    assert result.ok is True
    assert result.counter == _FIXED_STEP


# ---------------------------------------------------------------------------
# Signed tokens
# ---------------------------------------------------------------------------


def _secret_key() -> str:
    return get_settings().secret_key.get_secret_value()


def test_a_token_round_trips_with_its_claims() -> None:
    subject = uuid.uuid4()
    issued = issue_token(subject=subject, plane="tenant", typ="session")
    claims = decode_token(issued.token, expected_typ="session", expected_plane="tenant")
    assert claims.subject == subject
    assert claims.plane == "tenant"
    assert claims.typ == "session"
    assert claims.jti == issued.jti
    assert claims.expires_at == issued.expires_at


def test_the_claim_set_is_exactly_the_documented_six() -> None:
    issued = issue_token(subject=uuid.uuid4(), plane="provider", typ="session")
    payload = jwt.decode(issued.token, _secret_key(), algorithms=["HS256"])
    assert set(payload) == {"sub", "plane", "typ", "iat", "exp", "jti"}


def test_the_jti_is_a_uuid7_for_the_audit_stream() -> None:
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ="session")
    assert issued.jti.version == 7


@pytest.mark.parametrize(
    ("typ", "ttl"),
    [
        ("session", timedelta(hours=12)),
        ("challenge", timedelta(minutes=5)),
        ("selection", timedelta(minutes=5)),
        ("invite", timedelta(days=7)),
    ],
)
def test_each_type_gets_its_configured_lifetime(typ: str, ttl: timedelta) -> None:
    before = datetime.now(tz=UTC)
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ=typ)
    drift = issued.expires_at - before - ttl
    assert abs(drift.total_seconds()) < 5


def test_an_unknown_plane_or_typ_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="unknown token plane"):
        issue_token(subject=uuid.uuid4(), plane="galactic", typ="session")
    with pytest.raises(ValueError, match="unknown token type"):
        issue_token(subject=uuid.uuid4(), plane="tenant", typ="refresh")


def test_a_typ_mismatch_is_refused() -> None:
    """An MFA challenge accepted by a session-consuming route bypasses the second
    factor, which is why decode has no type-agnostic mode at all."""
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ="challenge")
    with pytest.raises(InvalidToken):
        decode_token(issued.token, expected_typ="session")


def test_a_plane_mismatch_is_refused() -> None:
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ="session")
    with pytest.raises(InvalidToken):
        decode_token(issued.token, expected_typ="session", expected_plane="provider")


def test_the_plane_check_is_skipped_only_when_not_asked_for() -> None:
    issued = issue_token(subject=uuid.uuid4(), plane="provider", typ="session")
    claims = decode_token(issued.token, expected_typ="session")
    assert claims.plane == "provider"


def test_an_expired_token_is_refused() -> None:
    now = int(time.time())
    payload = _valid_payload(iat=now - 120, exp=now - 60)
    token = jwt.encode(payload, _secret_key(), algorithm="HS256")
    with pytest.raises(InvalidToken):
        decode_token(token, expected_typ="session")


def test_a_tampered_token_is_refused() -> None:
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ="session")
    tampered = issued.token[:-3] + ("AAA" if not issued.token.endswith("AAA") else "BBB")
    with pytest.raises(InvalidToken):
        decode_token(tampered, expected_typ="session")


def test_a_token_signed_with_another_key_is_refused() -> None:
    token = jwt.encode(
        _valid_payload(), "not-the-configured-key-but-just-as-long", algorithm="HS256"
    )
    with pytest.raises(InvalidToken):
        decode_token(token, expected_typ="session")


@pytest.mark.parametrize("missing", ["sub", "plane", "typ", "iat", "exp", "jti"])
def test_a_missing_claim_is_refused(missing: str) -> None:
    payload = _valid_payload()
    del payload[missing]
    token = jwt.encode(payload, _secret_key(), algorithm="HS256")
    with pytest.raises(InvalidToken):
        decode_token(token, expected_typ="session")


def test_a_non_uuid_subject_is_refused() -> None:
    payload = _valid_payload()
    payload["sub"] = "not-a-uuid"
    token = jwt.encode(payload, _secret_key(), algorithm="HS256")
    with pytest.raises(InvalidToken):
        decode_token(token, expected_typ="session")


def test_every_failure_mode_shares_one_uniform_error() -> None:
    """A client probing token structure must learn nothing from the response: same
    code, same message, no PyJWT internals, 401."""
    issued = issue_token(subject=uuid.uuid4(), plane="tenant", typ="challenge")
    attempts: tuple[Callable[[], TokenClaims], ...] = (
        lambda: decode_token("garbage", expected_typ="session"),
        lambda: decode_token(issued.token, expected_typ="session"),
        lambda: decode_token(issued.token, expected_typ="challenge", expected_plane="provider"),
    )
    failures: list[InvalidToken] = []
    for attempt in attempts:
        with pytest.raises(InvalidToken) as excinfo:
            attempt()
        failures.append(excinfo.value)

    messages = {failure.message for failure in failures}
    assert len(messages) == 1
    assert "Signature" not in messages.pop()
    assert all(failure.code == "invalid_token" for failure in failures)
    assert all(failure.http_status == 401 for failure in failures)
    assert all(isinstance(failure, AuthenticationRequired) for failure in failures)


def test_the_documented_planes_and_types_are_the_only_ones() -> None:
    assert {"tenant", "provider"} == TOKEN_PLANES
    assert {"session", "challenge", "selection", "invite", "email_verify"} == TOKEN_TYPES


def _valid_payload(iat: int | None = None, exp: int | None = None) -> dict[str, object]:
    now = int(time.time())
    return {
        "sub": str(uuid.uuid4()),
        "plane": "tenant",
        "typ": "session",
        "iat": iat if iat is not None else now,
        "exp": exp if exp is not None else now + 60,
        "jti": str(uuid.uuid4()),
    }
