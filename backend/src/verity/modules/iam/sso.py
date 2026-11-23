"""The OpenID Connect side of signing in through Keycloak (openspec/changes/add-keycloak-sso).

Protocol only: build the authorization request, finish the callback (state, code exchange, ID token
validation) and hold the short lived values between steps. Who the person is, and which session they
get, is decided by ``IamService.sso_sign_in``. Nothing here touches the database.

Short lived values live in Redis, each single use:

- ``sso:state:<state>`` for ten minutes: the nonce and the PKCE verifier;
- ``sso:handoff:<code>`` for sixty seconds: the validated identity, until the web app claims it;
- ``sso:idt:<user id>`` for a session's lifetime: the ID token, used only as ``id_token_hint``
  when the person signs out, so the Keycloak session ends too.

Keycloak's tokens never reach the browser. Any failure is an ``SsoFailed`` with a fixed code the web
app turns into one sentence; the details go to the log.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from typing import Any, Final

import httpx
import jwt
import redis.asyncio as aioredis

from verity.core.config import get_settings
from verity.core.errors import AuthenticationRequired
from verity.core.logging import get_logger

logger = get_logger(__name__)

STATE_TTL: Final = 600
HANDOFF_TTL: Final = 60
_ALGORITHMS: Final = ["RS256", "PS256", "ES256"]
_CACHE_SECONDS: Final = 3600
LOGOUT_EVENT: Final = "http://schemas.openid.net/event/backchannel-logout"
LOGOUT_TOKEN_MAX_AGE: Final = 300

FAILURES: Final[dict[str, str]] = {
    "unavailable": "Single sign on is not available right now. Try again, or use your password.",
    "state": "That sign in link has expired. Start again.",
    "denied": "Your organisation's sign in did not complete. Start again.",
    "token": "We could not confirm your sign in. Start again.",
    "no_account": "There is no Verity account for this email. Ask your admin to invite you.",
    "unverified": "Your organisation has not confirmed this email address. Ask your IT team.",
    "disabled": "Your account is not active. Ask a workspace admin to restore your access.",
    "no_workspace": "You are not an active member of any Verity workspace. Ask your admin.",
    "wrong_domain": "This sign in only works for your organisation's own email domains.",
}


class SsoFailed(AuthenticationRequired):
    """A sign in through Keycloak that cannot go on. ``code`` is one of ``FAILURES``."""

    def __init__(self, code: str, *, detail: str) -> None:
        super().__init__(FAILURES.get(code, FAILURES["token"]), detail=detail)
        self.code = code


@dataclass(frozen=True, slots=True)
class SsoIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool
    name: str | None
    organizations: list[str] = field(default_factory=list)
    acr: str | None = None
    amr: list[str] = field(default_factory=list)
    id_token: str = ""
    idp: str | None = None
    """The Keycloak identity provider that authenticated the person (``identity_provider``
    claim); None for an account kept in Keycloak itself."""


# -- discovery and keys -------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}


def _redis() -> aioredis.Redis:
    settings = get_settings().redis
    client: aioredis.Redis = aioredis.from_url(
        settings.url,
        socket_timeout=settings.socket_timeout_seconds,
        socket_connect_timeout=settings.socket_timeout_seconds,
    )
    return client


async def _put(key: str, value: str, ttl: int) -> None:
    client = _redis()
    try:
        await client.set(key, value, ex=ttl)
    finally:
        await client.aclose()


async def _take(key: str) -> bytes | None:
    """Read and delete in one step: every value kept here is single use."""
    client = _redis()
    try:
        value: bytes | None = await client.getdel(key)
    finally:
        await client.aclose()
    return value


async def _get_json(url: str) -> Any:  # noqa: ANN401 — a provider's JSON document
    async with httpx.AsyncClient(timeout=get_settings().oidc.timeout_seconds) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def _cached(key: str, url: str, *, refresh: bool = False) -> Any:  # noqa: ANN401
    hit = _cache.get(key)
    if hit and not refresh and hit[0] > time.monotonic():
        return hit[1]
    value = await _get_json(url)
    _cache[key] = (time.monotonic() + _CACHE_SECONDS, value)
    return value


async def discovery() -> dict[str, Any]:
    issuer = get_settings().oidc.issuer_url.rstrip("/")
    try:
        doc: dict[str, Any] = await _cached(
            "discovery", f"{issuer}/.well-known/openid-configuration"
        )
    except httpx.HTTPError as exc:
        raise SsoFailed("unavailable", detail=f"discovery failed: {type(exc).__name__}") from exc
    return doc


async def _signing_key(kid: str | None) -> Any:  # noqa: ANN401 — a PyJWT key object
    doc = await discovery()
    for refresh in (False, True):
        jwks = await _cached("jwks", doc["jwks_uri"], refresh=refresh)
        for key in jwt.PyJWKSet.from_dict(jwks).keys:
            if kid is None or key.key_id == kid:
                return key.key
    raise SsoFailed("token", detail=f"no signing key for kid {kid!r}")


# -- the authorization request --------------------------------------------------------------


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


async def authorization_url(*, email: str | None, organization: str | None = None) -> str:
    """Where to send the browser. ``organization`` (a Keycloak organization alias) narrows the
    request to that organization, so its identity provider is used without asking again."""
    settings = get_settings().oidc
    if not settings.enabled or settings.client_secret is None:
        raise SsoFailed("unavailable", detail="OIDC is not configured")
    doc = await discovery()
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    verifier, challenge = _pkce()
    scopes = settings.scopes.split()
    if organization:
        scopes = [s for s in scopes if s != "organization"] + [f"organization:{organization}"]
    await _put(f"sso:state:{state}", json.dumps({"nonce": nonce, "verifier": verifier}), STATE_TTL)
    params = {
        "response_type": "code",
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_url,
        "scope": " ".join(scopes),
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if email:
        params["login_hint"] = email
    return f"{doc['authorization_endpoint']}?{urllib.parse.urlencode(params)}"


# -- the callback ---------------------------------------------------------------------------


def _organizations(claim: Any) -> list[str]:  # noqa: ANN401 — the organization claim's shapes
    if isinstance(claim, dict):
        return sorted(str(k) for k in claim)
    if isinstance(claim, list):
        return sorted(str(v) for v in claim)
    return []


async def finish(*, code: str | None, state: str | None, error: str | None) -> SsoIdentity:
    """Check the state, exchange the code and validate the ID token."""
    settings = get_settings().oidc
    if not state:
        raise SsoFailed("state", detail="callback without state")
    stored = await _take(f"sso:state:{state}")
    if stored is None:
        raise SsoFailed("state", detail="unknown or expired state")
    if error or not code:
        raise SsoFailed("denied", detail=f"provider returned error {error!r}")
    saved = json.loads(stored)
    doc = await discovery()
    secret = settings.client_secret.get_secret_value() if settings.client_secret else ""
    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.post(
                doc["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.redirect_url,
                    "code_verifier": saved["verifier"],
                },
                auth=(settings.client_id, secret),
            )
    except httpx.HTTPError as exc:
        raise SsoFailed("unavailable", detail=f"token call failed: {type(exc).__name__}") from exc
    if response.status_code != 200:  # noqa: PLR2004
        raise SsoFailed("token", detail=f"token endpoint answered {response.status_code}")
    id_token = str(response.json().get("id_token") or "")
    claims = await validate_id_token(id_token, nonce=saved["nonce"])
    return SsoIdentity(
        issuer=str(claims["iss"]),
        subject=str(claims["sub"]),
        email=(str(claims["email"]).strip().lower() if claims.get("email") else None),
        email_verified=bool(claims.get("email_verified")),
        name=str(claims["name"]) if claims.get("name") else None,
        organizations=_organizations(claims.get("organization")),
        acr=str(claims["acr"]) if claims.get("acr") else None,
        amr=[str(a) for a in claims.get("amr") or []],
        idp=str(claims["identity_provider"]) if claims.get("identity_provider") else None,
        id_token=id_token,
    )


async def _decode(token: str, *, require: list[str]) -> dict[str, Any]:
    """A token Keycloak signed for this client: signature, issuer, audience, required claims."""
    settings = get_settings().oidc
    header = jwt.get_unverified_header(token)
    key = await _signing_key(header.get("kid"))
    claims: dict[str, Any] = jwt.decode(
        token,
        key,
        algorithms=_ALGORITHMS,
        audience=settings.client_id,
        issuer=settings.issuer_url.rstrip("/"),
        options={"require": require},
        leeway=30,
    )
    return claims


async def validate_id_token(id_token: str, *, nonce: str) -> dict[str, Any]:
    settings = get_settings().oidc
    if not id_token:
        raise SsoFailed("token", detail="no id_token in the token response")
    try:
        claims = await _decode(id_token, require=["exp", "iat", "iss", "aud", "sub"])
    except jwt.PyJWTError as exc:
        raise SsoFailed("token", detail=f"id_token rejected ({type(exc).__name__})") from exc
    if claims.get("nonce") != nonce:
        raise SsoFailed("token", detail="nonce mismatch")
    if claims.get("azp") not in (None, settings.client_id):
        raise SsoFailed("token", detail="azp is another client")
    return claims


async def validate_logout_token(token: str) -> str:
    """The Keycloak subject a back-channel logout token signs out (OpenID Connect Back-Channel
    Logout 1.0, section 2.6): signed for this client, carrying the logout event and no nonce,
    recent, and used once. Keycloak always names the subject; a token naming only ``sid`` is
    refused."""
    try:
        claims = await _decode(token, require=["iat", "iss", "aud", "jti", "sub"])
    except jwt.PyJWTError as exc:
        raise SsoFailed("token", detail=f"logout token rejected ({type(exc).__name__})") from exc
    events = claims.get("events")
    if not isinstance(events, dict) or LOGOUT_EVENT not in events or "nonce" in claims:
        raise SsoFailed("token", detail="not a back-channel logout token")
    if time.time() - float(claims["iat"]) > LOGOUT_TOKEN_MAX_AGE:
        raise SsoFailed("token", detail="logout token too old")
    client = _redis()
    try:
        fresh = await client.set(
            f"sso:logout:{claims['jti']}", "1", ex=2 * LOGOUT_TOKEN_MAX_AGE, nx=True
        )
    finally:
        await client.aclose()
    if not fresh:
        raise SsoFailed("token", detail="logout token replayed")
    return str(claims["sub"])


# -- between steps --------------------------------------------------------------------------


async def put_handoff(identity: SsoIdentity) -> str:
    handoff = secrets.token_urlsafe(32)
    await _put(f"sso:handoff:{handoff}", json.dumps(asdict(identity)), HANDOFF_TTL)
    return handoff


async def take_handoff(handoff: str) -> SsoIdentity:
    stored = await _take(f"sso:handoff:{handoff}")
    if stored is None:
        raise SsoFailed("state", detail="unknown or expired handoff")
    return SsoIdentity(**json.loads(stored))


async def remember_selection(jti: str, *, memberships: list[str], verify: list[str]) -> None:
    """Which workspaces an SSO sign in may open, under its workspace choice token. Read (not
    taken) on each choice, so a person can go back and pick again until the token expires."""
    ttl = get_settings().auth.selection_ttl_minutes * 60
    await _put(f"sso:sel:{jti}", json.dumps({"memberships": memberships, "verify": verify}), ttl)


async def selection(jti: str) -> dict[str, list[str]] | None:
    client = _redis()
    try:
        raw = await client.get(f"sso:sel:{jti}")
    finally:
        await client.aclose()
    if raw is None:
        return None
    value: dict[str, list[str]] = json.loads(raw)
    return value


async def remember_id_token(user_id: str, id_token: str) -> None:
    ttl = get_settings().auth.session_ttl_hours * 3600
    await _put(f"sso:idt:{user_id}", id_token, ttl)


async def end_session_url(user_id: str) -> str | None:
    """Keycloak's sign out URL for this person, or None when they did not sign in through it."""
    settings = get_settings().oidc
    if not settings.enabled:
        return None
    id_token = await _take(f"sso:idt:{user_id}")
    if id_token is None:
        return None
    doc = await discovery()
    endpoint = doc.get("end_session_endpoint")
    if not endpoint:
        return None
    params = {
        "id_token_hint": id_token.decode(),
        "post_logout_redirect_uri": f"{settings.web_url.rstrip('/')}/sign-in",
        "client_id": settings.client_id,
    }
    return f"{endpoint}?{urllib.parse.urlencode(params)}"


def failure_redirect(code: str) -> str:
    return (
        f"{get_settings().oidc.web_url.rstrip('/')}/sso/complete?error={urllib.parse.quote(code)}"
    )


def handoff_redirect(handoff: str) -> str:
    return f"{get_settings().oidc.web_url.rstrip('/')}/sso/complete?handoff={handoff}"
