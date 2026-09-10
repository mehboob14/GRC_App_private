"""A fixed-window rate limiter, backed by the Redis this app already runs.

Built for the vendor portal, which is the platform's only unauthenticated write
path. ``docs/conventions/api.md`` promises *"rate limits on all authenticated
routes, tighter on auth and portal-token routes"* and nothing in the codebase
delivered any of it; ``RateLimited`` existed in ``core.errors`` and was never
raised. This is the smallest thing that makes the promise true where it matters
most, and the seam every other route can adopt later.

No new dependency. ``redis`` is already pinned, and
``openspec/changes/add-backend-foundation/design.md`` justifies it as *"direct
client for the readiness probe and future rate limiting"* — this is that.

**It fails closed.** If Redis is unreachable the limiter refuses the request
rather than waving it through. That is the uncomfortable direction, and it is the
right one here: the portal is low-volume and a vendor retrying in a minute has
lost nothing, while a limiter that disappears exactly when infrastructure is
already degraded is a limiter that is absent during the incident it exists for.
Redis is a hard dependency of this deployment anyway — ``/readyz`` reports it.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Final

import redis.asyncio as aioredis
import structlog

from verity.core.config import get_settings
from verity.core.errors import RateLimited, ServiceUnavailable

logger: Final = structlog.get_logger(__name__)

_KEY_PREFIX: Final = "verity:rl"


@dataclass(frozen=True, slots=True)
class Limit:
    """How many requests a bucket may make, and over how long."""

    requests: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.requests < 1 or self.window_seconds < 1:
            raise ValueError("a limit needs at least one request and a window of at least a second")


# Deliberately strict, because these guard the only endpoints an unauthenticated
# caller can reach. A vendor filling in a questionnaire saves an answer at a time
# and will not notice; a script guessing tokens will.
PORTAL_TOKEN_FAILURES: Final = Limit(requests=10, window_seconds=300)
"""Per client address, and consumed **only by a failed resolve**.

This is the brute-force wall: a token is 32 random bytes, so ten guesses per five
minutes never finds one. Counting successful resolves against it would be the
obvious implementation and the wrong one — a vendor answering fifteen questions
resolves their token fifteen times, and would lock themselves out of their own
questionnaire on the tenth answer."""

PORTAL_LOOKUPS: Final = Limit(requests=300, window_seconds=300)
"""Consumed by every resolve, **keyed on the presented token** and not on the caller.

Keying this one on the client address is the obvious choice and the wrong one. The
API sits behind a reverse proxy and does not run with ``--proxy-headers``, so every
portal request arrives from the same bridge address: a per-address bucket collapses
into a single platform-wide one, and roughly three hundred junk requests would then
lock every tenant's vendors out for the rest of the window. Keying on the token
gives each link its own allowance, which no other caller can consume.

Guessing is bounded by ``PORTAL_TOKEN_FAILURES`` instead, which is charged per
address — and *that* one collapsing under the proxy makes it stricter rather than
weaker, because a legitimate token holder never charges it."""

PORTAL_WRITES: Final = Limit(requests=120, window_seconds=60)
"""Per token, once resolved. Generous for a person answering questions, mean for
anything automating against a token it already holds."""

PORTAL_UPLOADS: Final = Limit(requests=20, window_seconds=3600)
"""Per token. Uploads are the expensive path — they cost storage and a hash."""


def _client() -> aioredis.Redis:
    settings = get_settings().redis
    client: aioredis.Redis = aioredis.from_url(
        settings.url,
        socket_timeout=settings.socket_timeout_seconds,
        socket_connect_timeout=settings.socket_timeout_seconds,
    )
    return client


async def check(bucket: str, identity: str, limit: Limit) -> None:
    """Count one request against ``bucket:identity``; raise if it is over.

    Args:
        bucket: what is being limited, e.g. ``portal_resolve``.
        identity: who is being limited — a client address, or a token hash.
            **Never a raw token**: this string reaches Redis and the logs.
        limit: the allowance.

    Raises:
        RateLimited: the bucket is over its allowance for this window.
        ServiceUnavailable: Redis could not be reached, so the limit cannot be
            enforced and the request is refused rather than waved through.
    """
    # ponytail: fixed window, so a caller can land 2x the allowance across a
    # boundary. That is fine for a brute-force wall and wrong for billing; move to
    # a sliding window (a sorted set of timestamps) if this ever guards something
    # where the exact count matters.
    window = int(_now() // limit.window_seconds)
    key = f"{_KEY_PREFIX}:{bucket}:{identity}:{window}"

    client = _client()
    try:
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            # Set the expiry every time rather than only on the first hit: an
            # INCR that raced a key expiring between the two commands would
            # otherwise leave a counter with no TTL, and that bucket would then
            # deny its identity forever.
            pipe.expire(key, limit.window_seconds)
            count, _ = await pipe.execute()
    except RateLimited:
        raise
    except Exception as exc:
        logger.warning("ratelimit.backend_unavailable", bucket=bucket, exc_info=True)
        raise ServiceUnavailable(
            "We could not verify this request right now. Try again in a moment.",
            detail=f"rate-limit backend unavailable for bucket {bucket}",
        ) from exc
    finally:
        await client.aclose()

    if int(count) > limit.requests:
        logger.info("ratelimit.exceeded", bucket=bucket, limit=limit.requests)
        raise RateLimited(
            "Too many requests. Wait a few minutes and try again.",
            detail=f"{bucket} exceeded {limit.requests} per {limit.window_seconds}s",
        )


def client_identity(client_host: str | None) -> str:
    """A stable, log-safe identity for an unauthenticated caller.

    A missing address means the request arrived without one the server could see,
    which is not a licence to skip the limit — those all share one bucket, so the
    unattributable traffic is limited together rather than not at all.
    """
    return client_host or "unattributed"


def token_identity(token_hash: str) -> str:
    """Bucket a resolved token by its hash, never by the token itself."""
    return token_hash


def _now() -> float:
    """Indirected so a test can pin the window boundary without patching time
    globally."""
    return time.time()


def new_opaque_token() -> str:
    """A portal token: 32 random bytes, URL-safe, unguessable, meaningless.

    Deliberately not a JWT. A signed token would carry claims that have to be
    trusted, and there is nothing here worth claiming — the row it resolves to
    holds every fact, is checked for expiry and revocation on every request, and
    can be revoked in a way an ``exp`` cannot.
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """The stored form of a portal token.

    sha256 rather than argon2, deliberately, and this is the one place that choice
    is defensible: the token is 32 bytes from ``secrets``, so it has no structure
    to guess and stretching buys nothing, while the portal has to hash-and-look-up
    on every single request. A password would be the opposite call.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_fingerprint(token: str) -> str:
    """A short, non-reversible tag for logging that a specific token was used."""
    return hash_token(token)[:12]
