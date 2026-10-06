"""A fixed-window rate limiter, backed by the Redis this app already runs.

Built for the vendor portal, then put in front of the sign-in routes: the places
an unauthenticated caller can write. ``docs/conventions/api.md`` promises *"rate
limits on all authenticated routes, tighter on auth and portal-token routes"*.
This is the smallest thing that makes the promise true where it matters most,
and the seam every other route can adopt later.

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
import ipaddress
import secrets
import time
from dataclasses import dataclass
from typing import Final

import redis.asyncio as aioredis
import structlog
from starlette.requests import Request

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

LOGIN_ACCOUNT: Final = Limit(requests=10, window_seconds=900)
"""Per account, every attempt, successful or not. The wall against guessing one
password: ten tries per quarter hour is under a thousand a day, which the password
policy is written for. Counting successes too keeps it one counter, and nobody signs
in ten times in fifteen minutes. The key is the account and not the caller, so a
person locked out by their own typos does not lock anyone else out."""

LOGIN_ADDRESS: Final = Limit(requests=100, window_seconds=900)
"""Per client address, every attempt. The wall against credential stuffing, which
makes one guess at many accounts and so never trips the per account limit. Generous
because an office shares one address."""

MFA_ATTEMPTS: Final = Limit(requests=10, window_seconds=900)
"""Per challenge token. A six digit code is a million values and the same code is
accepted for about ninety seconds, so ten tries per challenge is hopeless for a
guesser; getting a fresh challenge needs the password, which the login limit bounds."""

MAIL_ADDRESS: Final = Limit(requests=30, window_seconds=3600)
"""Per client address, across every action that sends a mail (signup, password reset,
verification resend). Generous enough for an office; the per recipient limit below is
the tight one."""

EMAIL_ACTIONS: Final = Limit(requests=5, window_seconds=3600)
"""Per recipient. Signup, password reset and verification resend all send a mail to
an address the caller names, so this is what stops the form being a mail bomb."""

DEMO_ADDRESS: Final = Limit(requests=5, window_seconds=3600)
"""Per client address, for the website's demo-request form. A person asks for a demo
once; five an hour is room for a typo and an office sharing one address, and little
else. Skipped when the address cannot be told (see ``client_address``), like
``MAIL_ADDRESS``."""

DEMO_EMAIL: Final = Limit(requests=3, window_seconds=86400)
"""Per requester email, for the same form. The caller names this address and we write
to it, so this is also what stops the form being used to pester one person."""

DEMO_CEILING: Final = Limit(requests=300, window_seconds=86400)
"""For the whole platform, under one fixed identity. Past this a flood from many
addresses would fill the owner's inbox however the other two limits were chosen, so the
form refuses everybody for the rest of the day instead. It is charged last, so a caller
the two limits above already turned away never spends any of it."""


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
            retry_after_seconds=_seconds_left(limit),
        )


def client_identity(client_host: str | None) -> str:
    """A stable, log-safe identity for an unauthenticated caller.

    A missing address means the request arrived without one the server could see,
    which is not a licence to skip the limit — those all share one bucket, so the
    unattributable traffic is limited together rather than not at all.
    """
    return client_host or "unattributed"


async def limit_sign_in(request: Request, email: str) -> None:
    """Count one password attempt against its account and, when known, its address."""
    await check("login_account", account_identity(email), LOGIN_ACCOUNT)
    address = _known_address(request)
    if address is not None:
        await check("login_address", address, LOGIN_ADDRESS)


async def limit_challenge(challenge_token: str) -> None:
    """Count one code attempt against the login challenge it answers."""
    await check("mfa_challenge", challenge_identity(challenge_token), MFA_ATTEMPTS)


async def limit_mail(request: Request, email: str) -> None:
    """Count one request that sends a mail to ``email``, against the recipient and the caller."""
    await check("mail_recipient", account_identity(email), EMAIL_ACTIONS)
    address = _known_address(request)
    if address is not None:
        await check("mail_address", address, MAIL_ADDRESS)


async def limit_demo_request(request: Request, email: str) -> None:
    """Count one demo request against its caller, its requester and the day's ceiling.

    In that order, and the order matters: ``check`` counts as it goes, so the broadest
    bucket is charged last, and a caller one of the narrower limits refuses never
    uses up the allowance of everyone else. Call it before anything is written.
    """
    address = _known_address(request)
    if address is not None:
        await check("demo_address", address, DEMO_ADDRESS)
    await check("demo_email", account_identity(email), DEMO_EMAIL)
    await check("demo_ceiling", "all", DEMO_CEILING)


def client_address(request: Request) -> str | None:
    """The caller's public address, seen through our reverse proxies, or None.

    In production a request crosses two nginx hops (the host's edge proxy, then the web
    container's), and the API's immediate peer is the second one. Reading the peer, or
    ``X-Real-IP`` (which the inner hop sets to the edge proxy's address), would put every
    user of the platform in one bucket, and one caller could then lock everyone out.

    ``X-Forwarded-For`` carries the whole chain, each hop appending the address it saw. It
    is believed only when the immediate peer is itself a private or loopback address (a
    proxy on our network), and read from the right, skipping private addresses: the first
    public one is what our own outermost proxy saw. Anything a caller put to its left is
    never reached, and a caller who reaches the API directly cannot use the header at all.

    When no public address can be found (the proxy sends no usable chain) the answer is
    None, never the proxy's own address: a limit keyed on that would be one bucket for the
    whole platform, which any scanner could fill. The caller is then limited by account.
    """
    peer = request.client.host if request.client else None
    if peer is None:
        return None
    if not _is_private(peer):
        return peer
    chain = ",".join(request.headers.getlist("x-forwarded-for")).split(",")
    for entry in reversed(chain):
        public = _public_address(entry)
        if public:
            return public
    return None


_address_warned = False


def _known_address(request: Request) -> str | None:
    """``client_address``, saying once per process when it is not known, because that
    means the proxy in front is not sending ``X-Forwarded-For`` and the per address
    limits are off for every caller."""
    global _address_warned  # noqa: PLW0603 — once per process is the whole point
    address = client_address(request)
    if address is None and not _address_warned:
        _address_warned = True
        logger.warning(
            "ratelimit.address_unknown",
            peer=request.client.host if request.client else None,
            hint="the proxy in front sends no public X-Forwarded-For; limits are per account only",
        )
    return address


def _is_private(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


def _public_address(text: str) -> str | None:
    """The address in ``text`` if it is a valid public one, else None."""
    try:
        address = ipaddress.ip_address(text.strip())
    except ValueError:
        return None
    return None if address.is_private or address.is_loopback else str(address)


def account_identity(email: str) -> str:
    """Bucket an account by its email, hashed: the key reaches Redis and the logs, and
    an email is personal data. Case and padding do not make a different account."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:32]


def challenge_identity(challenge_token: str) -> str:
    """Bucket a login challenge by its hash, never by the token itself."""
    return hash_token(challenge_token)[:32]


def token_identity(token_hash: str) -> str:
    """Bucket a resolved token by its hash, never by the token itself."""
    return token_hash


def _seconds_left(limit: Limit) -> int:
    """Seconds until this window ends and the bucket starts again."""
    return limit.window_seconds - int(_now() % limit.window_seconds)


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
