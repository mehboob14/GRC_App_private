"""Envelope encryption for secrets the database must store and never be able to read.

Rule 6 in CLAUDE.md: connector credentials, MFA secrets, and portal tokens are
encrypted at the application layer before they reach the database.

Shape
-----
A fresh 256-bit data key encrypts each value with AES-256-GCM. The master key encrypts
that data key, also with AES-256-GCM. The stored form carries the id of the master key
that wrapped it::

    v1.<key_id>.<wrapped_dek>.<dek_nonce>.<nonce>.<ciphertext>

The key id is in the ciphertext so that rotating the master key means promoting a new
key and keeping the old one for decryption — not re-encrypting every secret row in the
database. Retrofitting a key id into a format already in production *is* that
migration, which is why it is decided here, before there is a row to migrate.

The caller supplies an ``aad`` context that names the row the ciphertext belongs to.
It is authenticated but not encrypted, so a ciphertext copied from one row to another —
or from one tenant to another — fails to decrypt instead of decrypting into the wrong
place.
"""

from __future__ import annotations

import base64
import re
import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from verity.core.config import Settings, get_settings

CIPHERTEXT_VERSION: Final = "v1"
_MASTER_KEY_BYTES: Final = 32
_DATA_KEY_BYTES: Final = 32
_NONCE_BYTES: Final = 12
_FIELD_COUNT: Final = 6
_KEY_ID_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class CryptoError(Exception):
    """Encryption or decryption failed.

    Carries no key material, no plaintext, and no ciphertext in its message.
    """


class CryptoConfigurationError(CryptoError):
    """A master key is missing or malformed."""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CryptoError("ciphertext is not valid base64") from exc


def _parse_master_key(entry: str) -> tuple[str, bytes]:
    """Parse one ``<key_id>:<urlsafe-base64 32 bytes>`` entry."""
    key_id, separator, encoded = entry.strip().partition(":")
    if not separator:
        raise CryptoConfigurationError("master key must be formatted as '<key_id>:<base64 key>'")
    if not _KEY_ID_PATTERN.match(key_id):
        raise CryptoConfigurationError(
            "master key id must be lowercase alphanumeric with dashes or underscores"
        )
    try:
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CryptoConfigurationError(f"master key {key_id!r} is not valid base64") from exc
    if len(raw) != _MASTER_KEY_BYTES:
        raise CryptoConfigurationError(
            f"master key {key_id!r} must be {_MASTER_KEY_BYTES} bytes, got {len(raw)}"
        )
    return key_id, raw


@dataclass(frozen=True, repr=False)
class Keyring:
    """The active master key plus any retired keys retained for decryption."""

    active_key_id: str
    keys: dict[str, bytes]

    def __repr__(self) -> str:
        return f"Keyring(active_key_id={self.active_key_id!r}, key_count={len(self.keys)})"

    def active(self) -> tuple[str, bytes]:
        return self.active_key_id, self.keys[self.active_key_id]

    def get(self, key_id: str) -> bytes:
        try:
            return self.keys[key_id]
        except KeyError as exc:
            raise CryptoConfigurationError(
                f"no master key with id {key_id!r} is configured; it may have been "
                f"retired before every row encrypted under it was re-encrypted"
            ) from exc

    @classmethod
    def from_settings(cls, settings: Settings) -> Keyring:
        active_id, active_key = _parse_master_key(settings.app_encryption_key.get_secret_value())
        keys = {active_id: active_key}
        previous = settings.app_encryption_keys_previous
        if previous is not None:
            for entry in previous.get_secret_value().split(","):
                if not entry.strip():
                    continue
                key_id, raw = _parse_master_key(entry)
                keys.setdefault(key_id, raw)
        return cls(active_key_id=active_id, keys=keys)


class SecretBox:
    """Encrypts and decrypts values with the configured master keyring."""

    def __init__(self, keyring: Keyring) -> None:
        self._keyring = keyring

    def __repr__(self) -> str:
        return f"SecretBox({self._keyring!r})"

    def encrypt(self, plaintext: str, *, aad: str) -> str:
        """Encrypt ``plaintext``, bound to the ``aad`` context.

        Args:
            plaintext: the value to protect.
            aad: names the row this ciphertext belongs to, for example
                ``"connector_credentials.secret:<id>"``. The same value must be
                supplied to decrypt.
        """
        key_id, master_key = self._keyring.active()
        data_key = AESGCM.generate_key(bit_length=_DATA_KEY_BYTES * 8)
        aad_bytes = aad.encode("utf-8")

        nonce = _random_nonce()
        ciphertext = AESGCM(data_key).encrypt(nonce, plaintext.encode("utf-8"), aad_bytes)

        dek_nonce = _random_nonce()
        wrapped_dek = AESGCM(master_key).encrypt(dek_nonce, data_key, aad_bytes)

        return ".".join(
            (
                CIPHERTEXT_VERSION,
                key_id,
                _b64encode(wrapped_dek),
                _b64encode(dek_nonce),
                _b64encode(nonce),
                _b64encode(ciphertext),
            )
        )

    def decrypt(self, stored: str, *, aad: str) -> str:
        """Decrypt a value produced by :meth:`encrypt` under the same ``aad``.

        Raises:
            CryptoError: if the ciphertext is malformed, was tampered with, or was
                encrypted under a different context.
        """
        parts = stored.split(".")
        if len(parts) != _FIELD_COUNT:
            raise CryptoError("ciphertext is malformed")
        version, key_id, wrapped_dek, dek_nonce, nonce, ciphertext = parts
        if version != CIPHERTEXT_VERSION:
            raise CryptoError(f"unsupported ciphertext version {version!r}")

        master_key = self._keyring.get(key_id)
        aad_bytes = aad.encode("utf-8")
        try:
            data_key = AESGCM(master_key).decrypt(
                _b64decode(dek_nonce), _b64decode(wrapped_dek), aad_bytes
            )
            plaintext = AESGCM(data_key).decrypt(
                _b64decode(nonce), _b64decode(ciphertext), aad_bytes
            )
        except InvalidTag as exc:
            # Deliberately uniform: distinguishing "wrong key" from "wrong context"
            # from "modified" tells an attacker which of the three they achieved.
            raise CryptoError("ciphertext failed authentication") from exc
        return plaintext.decode("utf-8")


def _random_nonce() -> bytes:
    return secrets.token_bytes(_NONCE_BYTES)


@lru_cache(maxsize=1)
def get_secret_box() -> SecretBox:
    """The process-wide secret box, built from settings on first use."""
    return SecretBox(Keyring.from_settings(get_settings()))


def reset_secret_box_cache() -> None:
    """Discard the cached secret box. For tests that vary the keyring."""
    get_secret_box.cache_clear()
