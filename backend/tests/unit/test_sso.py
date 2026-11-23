"""Signing in through Keycloak, protocol side: a fake issuer, no network, no Redis."""

from __future__ import annotations

import json
import time
import urllib.parse
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from verity.core.config import get_settings
from verity.modules.iam import sso

ISSUER = "http://idp.test/realms/verity"
CLIENT = "verity-web"


class _Redis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def set(
        self, key: str, value: str, ex: int | None = None, nx: bool = False
    ) -> bool | None:
        if nx and key in self.data:
            return None
        self.data[key] = value.encode()
        return True

    async def getdel(self, key: str) -> bytes | None:
        return self.data.pop(key, None)

    async def aclose(self) -> None:
        return None


@pytest.fixture
def key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, key: rsa.RSAPrivateKey) -> _Redis:
    fake = _Redis()
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "k1", "use": "sig", "alg": "RS256"})
    documents: dict[str, Any] = {
        "discovery": {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
            "token_endpoint": f"{ISSUER}/protocol/openid-connect/token",
            "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
            "end_session_endpoint": f"{ISSUER}/protocol/openid-connect/logout",
        },
        "jwks": {"keys": [jwk]},
    }

    async def cached(name: str, url: str, *, refresh: bool = False) -> Any:  # noqa: ANN401
        return documents[name]

    settings = get_settings().model_copy(
        update={
            "oidc": get_settings().oidc.model_copy(
                update={
                    "enabled": True,
                    "issuer_url": ISSUER,
                    "client_id": CLIENT,
                    "client_secret": SecretStr("s"),
                }
            )
        }
    )
    monkeypatch.setattr(sso, "_redis", lambda: fake)
    monkeypatch.setattr(sso, "_cached", cached)
    monkeypatch.setattr(sso, "get_settings", lambda: settings)
    return fake


def _token(key: rsa.RSAPrivateKey, **override: Any) -> str:  # noqa: ANN401
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": CLIENT,
        "azp": CLIENT,
        "sub": "subject-1",
        "iat": now,
        "exp": now + 300,
        "nonce": "n1",
        "email": "Person@Example.com",
        "email_verified": True,
        "organization": {"northwind": {}},
    }
    claims.update(override)
    kid = claims.pop("_kid", "k1")
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


async def test_a_good_id_token_passes(store: _Redis, key: rsa.RSAPrivateKey) -> None:
    claims = await sso.validate_id_token(_token(key), nonce="n1")
    assert claims["sub"] == "subject-1"


@pytest.mark.parametrize(
    "override",
    [
        {"aud": "another-client"},
        {"iss": "http://evil.test/realms/verity"},
        {"nonce": "replayed"},
        {"exp": int(time.time()) - 600, "iat": int(time.time()) - 900},
        {"azp": "another-client"},
        {"_kid": "unknown"},
    ],
    ids=["audience", "issuer", "nonce", "expired", "azp", "kid"],
)
async def test_a_bad_id_token_is_refused(
    store: _Redis, key: rsa.RSAPrivateKey, override: dict[str, Any]
) -> None:
    with pytest.raises(sso.SsoFailed) as failed:
        await sso.validate_id_token(_token(key, **override), nonce="n1")
    assert failed.value.code == "token"


async def test_a_token_signed_by_another_key_is_refused(store: _Redis) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(sso.SsoFailed):
        await sso.validate_id_token(_token(other), nonce="n1")


async def test_the_request_carries_pkce_and_the_state_is_single_use(store: _Redis) -> None:
    url = await sso.authorization_url(email="a@northwind.example", organization="northwind")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert query["code_challenge_method"] == "S256"
    assert query["login_hint"] == "a@northwind.example"
    assert "organization:northwind" in query["scope"].split()
    assert "organization" not in query["scope"].split()
    state = query["state"]
    with pytest.raises(sso.SsoFailed) as denied:
        await sso.finish(code=None, state=state, error="access_denied")
    assert denied.value.code == "denied"
    with pytest.raises(sso.SsoFailed) as again:
        await sso.finish(code="c", state=state, error=None)
    assert again.value.code == "state", "the state was spent by the first callback"


async def test_a_handoff_is_single_use(store: _Redis) -> None:
    identity = sso.SsoIdentity(
        issuer=ISSUER, subject="s", email="a@b.c", email_verified=True, name=None
    )
    code = await sso.put_handoff(identity)
    assert (await sso.take_handoff(code)).subject == "s"
    with pytest.raises(sso.SsoFailed):
        await sso.take_handoff(code)


async def test_sign_out_url_names_the_id_token_once(store: _Redis) -> None:
    await sso.remember_id_token("u1", "the-id-token")
    url = await sso.end_session_url("u1")
    assert url is not None
    assert "id_token_hint=the-id-token" in url
    assert await sso.end_session_url("u1") is None


def _logout_token(key: rsa.RSAPrivateKey, **override: Any) -> str:  # noqa: ANN401
    claims = {
        "iss": ISSUER,
        "aud": CLIENT,
        "sub": "subject-1",
        "sid": "session-1",
        "iat": int(time.time()),
        "jti": "logout-1",
        "events": {sso.LOGOUT_EVENT: {}},
    }
    claims.update(override)
    return jwt.encode(
        {k: v for k, v in claims.items() if v is not None},
        key,
        algorithm="RS256",
        headers={"kid": "k1"},
    )


async def test_a_logout_token_names_its_subject_once(
    store: _Redis, key: rsa.RSAPrivateKey
) -> None:
    token = _logout_token(key)
    assert await sso.validate_logout_token(token) == "subject-1"
    with pytest.raises(sso.SsoFailed):
        await sso.validate_logout_token(token)  # replayed


@pytest.mark.parametrize(
    "override",
    [
        {"events": None},
        {"events": {"http://other.test/event": {}}},
        {"nonce": "n1"},
        {"iat": int(time.time()) - 3600},
        {"aud": "another-client"},
        {"sub": None},
    ],
    ids=["no-event", "other-event", "nonce", "stale", "audience", "no-subject"],
)
async def test_a_bad_logout_token_is_refused(
    store: _Redis, key: rsa.RSAPrivateKey, override: dict[str, Any]
) -> None:
    with pytest.raises(sso.SsoFailed):
        await sso.validate_logout_token(_logout_token(key, jti="x", **override))

