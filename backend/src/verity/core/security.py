"""Authentication primitives shared by both planes: passwords, TOTP, signed tokens.

Both authenticating populations — tenant users and platform admins — verify through
this one module (openspec/changes/add-provider-plane/design.md, "Shared authentication
primitives"). The alternative, a hasher in ``tenancy`` and another in ``iam``, is how
two argon2 configurations with different parameters end up in one codebase.

The cryptographic parameters are pinned in code, not configuration, so a deployment
cannot quietly weaken them. The only tunables are the token lifetimes, read from
``settings.auth`` (openspec/changes/week1-review-decisions.md, decision 17).
"""

from __future__ import annotations

import contextlib
import hmac
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Final

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from verity.core.config import get_settings
from verity.core.errors import InvalidToken
from verity.shared.ids import uuid7

# ---------------------------------------------------------------------------
# Password hashing — argon2id, parameters pinned per the approved design
# (add-provider-plane/design.md: OWASP's second recommended option).
# ---------------------------------------------------------------------------

_ARGON2_TIME_COST: Final = 3
_ARGON2_MEMORY_COST: Final = 65536  # KiB — 64 MiB
_ARGON2_PARALLELISM: Final = 4
_ARGON2_HASH_LEN: Final = 32
_ARGON2_SALT_LEN: Final = 16

_hasher: Final = PasswordHasher(
    time_cost=_ARGON2_TIME_COST,
    memory_cost=_ARGON2_MEMORY_COST,
    parallelism=_ARGON2_PARALLELISM,
    hash_len=_ARGON2_HASH_LEN,
    salt_len=_ARGON2_SALT_LEN,
    type=Type.ID,
)


@dataclass(frozen=True, slots=True)
class PasswordVerification:
    """The outcome of checking a password against a stored hash.

    ``needs_rehash`` is true when the stored hash was produced under older parameters
    and should be replaced on this (successful) login.
    """

    ok: bool
    needs_rehash: bool


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A real hash to verify against when the caller has nothing to verify.

    Built once, lazily: hashing costs the same 64 MiB pass as a login, which is the
    point, but it should not be paid at import time.
    """
    return _hasher.hash("verity-timing-equalizer")


def _burn_a_verification(plain: str) -> None:
    """Spend a real verification so an unknown email costs what a wrong password costs.

    Without this, a login against a missing or malformed hash returns in microseconds
    while a real mismatch takes tens of milliseconds, and the difference enumerates
    which emails exist. The result is discarded deliberately.
    """
    with contextlib.suppress(VerificationError):
        _hasher.verify(_dummy_hash(), plain)


def hash_password(plain: str) -> str:
    """Hash a password with the pinned argon2id parameters."""
    return _hasher.hash(plain)


def verify_password(password_hash: str, plain: str) -> PasswordVerification:
    """Check ``plain`` against a stored hash, in constant-ish time on every path.

    A malformed or empty ``password_hash`` — the unknown-email case, where the caller
    has no credential row — verifies against a dummy hash so the response time does
    not reveal whether the account exists. It never raises for bad input; the answer
    is simply ``ok=False``.
    """
    try:
        _hasher.verify(password_hash, plain)
    except VerifyMismatchError:
        return PasswordVerification(ok=False, needs_rehash=False)
    except (InvalidHashError, VerificationError):
        _burn_a_verification(plain)
        return PasswordVerification(ok=False, needs_rehash=False)
    return PasswordVerification(ok=True, needs_rehash=_hasher.check_needs_rehash(password_hash))


# ---------------------------------------------------------------------------
# TOTP — RFC 6238: 30-second period, 6 digits, SHA-1 (pyotp's defaults, and what
# every authenticator app implements), window of one step either side for skew.
# ---------------------------------------------------------------------------

_TOTP_PERIOD_SECONDS: Final = 30
_TOTP_DIGITS: Final = 6
_TOTP_WINDOW_STEPS: Final = 1
_TOTP_SECRET_LENGTH: Final = 32


@dataclass(frozen=True, slots=True)
class TotpVerification:
    """The outcome of checking a TOTP code.

    ``counter`` is the accepted time-step counter, present only on success. The
    caller stores it (``credentials.last_totp_counter``) and passes it back as
    ``last_counter`` next time — that is the replay protection pyotp does not do.
    """

    ok: bool
    counter: int | None


def _now() -> float:
    """The clock, as a module seam so tests can pin it."""
    return time.time()


def new_totp_secret() -> str:
    """Mint a fresh base32 TOTP secret."""
    return str(pyotp.random_base32(length=_TOTP_SECRET_LENGTH))


def totp_provisioning_uri(secret: str, account_name: str, issuer: str = "Verity") -> str:
    """The ``otpauth://`` URI an authenticator app enrolls from."""
    uri = pyotp.TOTP(secret, digits=_TOTP_DIGITS, interval=_TOTP_PERIOD_SECONDS).provisioning_uri(
        name=account_name, issuer_name=issuer
    )
    return str(uri)


def verify_totp(secret: str, code: str, last_counter: int | None) -> TotpVerification:
    """Check a TOTP code, refusing anything at or before the last accepted counter.

    A code at ``counter <= last_counter`` is refused even if otherwise valid: within
    the ±1-step window a captured code stays usable for up to 90 seconds, and the
    stored counter is what closes that replay hole.
    """
    normalized = code.strip().replace(" ", "")
    if len(normalized) != _TOTP_DIGITS or not normalized.isdigit():
        return TotpVerification(ok=False, counter=None)

    totp = pyotp.TOTP(secret, digits=_TOTP_DIGITS, interval=_TOTP_PERIOD_SECONDS)
    current_step = int(_now()) // _TOTP_PERIOD_SECONDS
    for step in range(current_step - _TOTP_WINDOW_STEPS, current_step + _TOTP_WINDOW_STEPS + 1):
        expected = str(totp.generate_otp(step))
        if hmac.compare_digest(expected, normalized):
            if last_counter is not None and step <= last_counter:
                return TotpVerification(ok=False, counter=None)
            return TotpVerification(ok=True, counter=step)
    return TotpVerification(ok=False, counter=None)


# ---------------------------------------------------------------------------
# Signed tokens — PyJWT HS256 under settings.secret_key. The claim shape and the
# lifetimes are decision 17 in openspec/changes/week1-review-decisions.md. A token
# names *who*, never *what they may do*: no roles, no permissions, no tenant.
# ---------------------------------------------------------------------------

TOKEN_PLANES: Final = frozenset({"tenant", "provider"})
TOKEN_TYPES: Final = frozenset({"session", "challenge", "selection", "invite", "email_verify"})

_JWT_ALGORITHM: Final = "HS256"
_REQUIRED_CLAIMS: Final = ("sub", "plane", "typ", "iat", "exp", "jti")


@dataclass(frozen=True, slots=True)
class IssuedToken:
    """A freshly signed token. ``jti`` doubles as the audit ``session`` object id."""

    token: str
    jti: uuid.UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """The validated claims of a decoded token."""

    subject: uuid.UUID
    plane: str
    typ: str
    jti: uuid.UUID
    issued_at: datetime
    expires_at: datetime


def _token_ttl(typ: str) -> timedelta:
    auth = get_settings().auth
    ttls = {
        "session": timedelta(hours=auth.session_ttl_hours),
        "challenge": timedelta(minutes=auth.challenge_ttl_minutes),
        "selection": timedelta(minutes=auth.selection_ttl_minutes),
        "invite": timedelta(days=auth.invite_ttl_days),
        "email_verify": timedelta(hours=auth.email_verify_ttl_hours),
    }
    return ttls[typ]


def issue_token(*, subject: uuid.UUID, plane: str, typ: str) -> IssuedToken:
    """Sign a token for ``subject`` with the lifetime configured for its type.

    Raises:
        ValueError: on an unknown ``plane`` or ``typ``. Issuing is server-side code,
            so a bad argument is a defect, not a domain condition.
    """
    if plane not in TOKEN_PLANES:
        raise ValueError(f"unknown token plane {plane!r}; expected one of {sorted(TOKEN_PLANES)}")
    if typ not in TOKEN_TYPES:
        raise ValueError(f"unknown token type {typ!r}; expected one of {sorted(TOKEN_TYPES)}")

    issued_at = int(_now())
    expires_at = issued_at + int(_token_ttl(typ).total_seconds())
    jti = uuid7()
    payload = {
        "sub": str(subject),
        "plane": plane,
        "typ": typ,
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(jti),
    }
    token = jwt.encode(
        payload, get_settings().secret_key.get_secret_value(), algorithm=_JWT_ALGORITHM
    )
    return IssuedToken(token=token, jti=jti, expires_at=datetime.fromtimestamp(expires_at, tz=UTC))


def decode_token(
    token: str, *, expected_typ: str, expected_plane: str | None = None
) -> TokenClaims:
    """Validate a token's signature, expiry, type, and (when given) plane.

    Every failure raises the same :class:`~verity.core.errors.InvalidToken` with the
    same message. Which check failed goes into ``detail`` for the log, never to the
    caller — a client probing token structure learns nothing, and no PyJWT internals
    cross the boundary.

    The challenge/session split depends on ``expected_typ`` being enforced here: an
    MFA challenge accepted by a session-consuming route would bypass the second
    factor, so there is deliberately no way to decode without naming the type.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            get_settings().secret_key.get_secret_value(),
            algorithms=[_JWT_ALGORITHM],
            options={"require": list(_REQUIRED_CLAIMS)},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(detail=f"jwt validation failed ({type(exc).__name__})") from exc

    if payload.get("typ") != expected_typ:
        raise InvalidToken(detail=f"typ mismatch: expected {expected_typ!r}")
    plane = payload.get("plane")
    if plane not in TOKEN_PLANES:
        raise InvalidToken(detail="plane claim is not a known plane")
    if expected_plane is not None and plane != expected_plane:
        raise InvalidToken(detail=f"plane mismatch: expected {expected_plane!r}")

    try:
        subject = uuid.UUID(str(payload["sub"]))
        jti = uuid.UUID(str(payload["jti"]))
        issued_at = datetime.fromtimestamp(int(payload["iat"]), tz=UTC)
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidToken(detail="token claims are malformed") from exc

    return TokenClaims(
        subject=subject,
        plane=plane,
        typ=expected_typ,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
    )
