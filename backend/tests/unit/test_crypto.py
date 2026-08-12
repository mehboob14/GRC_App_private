"""Envelope encryption (rule 6)."""

from __future__ import annotations

import base64

import pytest
from pydantic import SecretStr

from verity.core.config import Settings
from verity.core.crypto import (
    CIPHERTEXT_VERSION,
    CryptoConfigurationError,
    CryptoError,
    Keyring,
    SecretBox,
)

AAD = "connector_credentials.secret:0198f0c0-0000-7000-8000-000000000001"

ACTIVE_KEY = b"active-master-key".ljust(32, b".")
RETIRED_KEY = b"retired-master-key".ljust(32, b".")


def _entry(key_id: str, raw: bytes) -> str:
    return f"{key_id}:{base64.urlsafe_b64encode(raw).decode()}"


@pytest.fixture
def keyring() -> Keyring:
    return Keyring(active_key_id="k2", keys={"k2": ACTIVE_KEY, "k1": RETIRED_KEY})


@pytest.fixture
def box(keyring: Keyring) -> SecretBox:
    return SecretBox(keyring)


def test_round_trip(box: SecretBox) -> None:
    plaintext = "otpauth://totp/Verity:someone@example.com?secret=JBSWY3DPEHPK3PXP"
    assert box.decrypt(box.encrypt(plaintext, aad=AAD), aad=AAD) == plaintext


def test_unicode_round_trip(box: SecretBox) -> None:
    plaintext = "pässwörd — 密码 — key"
    assert box.decrypt(box.encrypt(plaintext, aad=AAD), aad=AAD) == plaintext


def test_plaintext_never_appears_in_the_ciphertext(box: SecretBox) -> None:
    plaintext = "a-very-distinctive-secret-value"
    assert plaintext not in box.encrypt(plaintext, aad=AAD)


def test_same_plaintext_encrypts_differently_each_time(box: SecretBox) -> None:
    """A fresh data key and nonce per value.

    Deterministic ciphertext would let anyone with read access to the column see that
    two tenants configured the same credential.
    """
    assert box.encrypt("same", aad=AAD) != box.encrypt("same", aad=AAD)


def test_ciphertext_records_the_active_key_id(box: SecretBox) -> None:
    version, key_id, *_ = box.encrypt("value", aad=AAD).split(".")
    assert version == CIPHERTEXT_VERSION
    assert key_id == "k2"


@pytest.mark.parametrize("field_index", [2, 3, 4, 5])
def test_tampering_is_detected(box: SecretBox, field_index: int) -> None:
    parts = box.encrypt("value", aad=AAD).split(".")
    field = parts[field_index]
    parts[field_index] = ("B" if field[0] != "B" else "C") + field[1:]
    with pytest.raises(CryptoError):
        box.decrypt(".".join(parts), aad=AAD)


def test_ciphertext_moved_to_another_row_does_not_decrypt(box: SecretBox) -> None:
    """The reason for the AAD binding.

    A ciphertext copied to a different row — or a different tenant — must fail rather
    than decrypt into the wrong place.
    """
    stored = box.encrypt("value", aad=AAD)
    with pytest.raises(CryptoError, match="failed authentication"):
        box.decrypt(stored, aad="connector_credentials.secret:some-other-row")


def test_malformed_ciphertext_is_rejected(box: SecretBox) -> None:
    with pytest.raises(CryptoError, match="malformed"):
        box.decrypt("not-a-ciphertext", aad=AAD)


def test_unknown_version_is_rejected(box: SecretBox) -> None:
    parts = box.encrypt("value", aad=AAD).split(".")
    parts[0] = "v99"
    with pytest.raises(CryptoError, match="unsupported ciphertext version"):
        box.decrypt(".".join(parts), aad=AAD)


def test_value_encrypted_under_a_retired_key_still_decrypts(box: SecretBox) -> None:
    """Rotation without re-encrypting every row.

    The old box wrote under ``k1``; the current box has ``k2`` active and keeps ``k1``.
    """
    old = SecretBox(Keyring(active_key_id="k1", keys={"k1": RETIRED_KEY}))
    stored = old.encrypt("secret", aad=AAD)
    assert box.decrypt(stored, aad=AAD) == "secret"
    assert box.encrypt("secret", aad=AAD).split(".")[1] == "k2"


def test_dropping_a_key_that_still_has_rows_fails_loudly() -> None:
    old = SecretBox(Keyring(active_key_id="k1", keys={"k1": RETIRED_KEY}))
    without_k1 = SecretBox(Keyring(active_key_id="k2", keys={"k2": ACTIVE_KEY}))
    stored = old.encrypt("secret", aad=AAD)
    with pytest.raises(CryptoConfigurationError, match="no master key with id 'k1'"):
        without_k1.decrypt(stored, aad=AAD)


def test_repr_reveals_no_key_material(box: SecretBox) -> None:
    """docs/security/baseline.md: never in logs, exception messages, or __repr__."""
    rendered = repr(box)
    assert "k2" in rendered
    assert base64.urlsafe_b64encode(ACTIVE_KEY).decode() not in rendered
    assert ACTIVE_KEY.decode() not in rendered


def test_keyring_is_read_from_settings() -> None:
    settings = Settings(
        app_encryption_key=SecretStr(_entry("k2", ACTIVE_KEY)),
        app_encryption_keys_previous=SecretStr(_entry("k1", RETIRED_KEY)),
    )
    keyring = Keyring.from_settings(settings)
    assert keyring.active_key_id == "k2"
    assert keyring.get("k1") == RETIRED_KEY


@pytest.mark.parametrize(
    "entry",
    [
        "no-separator",
        "BAD_ID:" + base64.urlsafe_b64encode(b"x" * 32).decode(),
        "k1:not-base64!!",
        "k1:" + base64.urlsafe_b64encode(b"too-short").decode(),
    ],
)
def test_malformed_master_key_is_rejected(entry: str) -> None:
    settings = Settings(app_encryption_key=SecretStr(entry))
    with pytest.raises(CryptoConfigurationError):
        Keyring.from_settings(settings)
