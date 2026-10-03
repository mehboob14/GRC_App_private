"""Branding through the real app: the logo upload and its limits, the register search,
the credential that survives a round trip, and what a workspace's own members can read.

Real tokens, real dependencies, real policies, real audit rows. The only substitution is
the object store, which is pointed at a temp directory so no test writes into a
developer's own store.
"""

from __future__ import annotations

import struct
import uuid
import zlib
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from tests.support.audit import full_stream
from tests.support.iam import (
    INVITEE_PASSWORD,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from tests.support.tenancy import (
    bearer,
    provider_session_headers,
    registration_payload,
    seed_admin,
)
from verity.core.config import Settings, reset_settings_cache
from verity.core.crypto import get_secret_box
from verity.core.db import dispose_engine, provider_session_scope
from verity.core.security import issue_token
from verity.core.storage import get_object_store, reset_object_store_cache
from verity.main import create_app
from verity.modules.iam.service import iam_auth_service
from verity.modules.tenancy.models import TenantBranding
from verity.modules.tenancy.service import LOGO_MAX_BYTES

pytestmark = pytest.mark.integration

TENANTS_URL = "/api/v1/provider/tenants"
BRANDING_URL = "/api/v1/tenant/branding"
LOGO_URL = "/api/v1/tenant/branding/logo"

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def _png(*, pad_to: int | None = None, marker: bytes = b"") -> bytes:
    """A real 1x1 PNG. ``marker`` trails the image so two logos differ; ``pad_to`` fills
    the file with trailing zeros to an exact size."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        + chunk(b"IEND", b"")
        + marker
    )
    return png if pad_to is None else png + b"\x00" * (pad_to - len(png))


@pytest.fixture(autouse=True)
async def _clean_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture(autouse=True)
def object_store_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "objects"
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(root))
    reset_settings_cache()
    reset_object_store_cache()
    yield root
    monkeypatch.undo()
    reset_settings_cache()
    reset_object_store_cache()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
async def onboarding() -> dict[str, str]:
    admin = await seed_admin(role="onboarding")
    return provider_session_headers(admin.id)


async def _register(
    client: httpx.AsyncClient, headers: dict[str, str], slug: str = "acme", **overrides: object
) -> uuid.UUID:
    response = await client.post(
        TENANTS_URL, json=registration_payload(slug, **overrides), headers=headers
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


async def _upload(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    tenant_id: uuid.UUID,
    data: bytes,
    claim: tuple[str, str] = ("logo.png", "image/png"),
) -> httpx.Response:
    """Upload ``data`` claiming the given (filename, content type), true or not."""
    filename, content_type = claim
    return await client.post(
        f"{TENANTS_URL}/{tenant_id}/branding/logo",
        headers=headers,
        files={"file": (filename, data, content_type)},
    )


def _stored_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


# ---------------------------------------------------------------------------
# Provider: upload, serve, remove
# ---------------------------------------------------------------------------


async def test_a_logo_upload_is_stored_served_back_audited_and_removable(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant_id = await _register(client, onboarding)
    logo_url = f"{TENANTS_URL}/{tenant_id}/branding/logo"
    logo = _png(marker=b"acme")

    response = await _upload(client, onboarding, tenant_id, logo)
    assert response.status_code == 200
    branding = response.json()
    assert branding["logo_ref"].startswith(f"{tenant_id}/")
    assert "smtp_config_ref" not in branding

    served = await client.get(logo_url, headers=onboarding)
    assert served.status_code == 200
    assert served.content == logo
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"

    updates = [
        entry
        for entry in await full_stream(tenant_id)
        if entry.object_type == "tenant_branding" and entry.action == "update"
    ]
    assert len(updates) == 1
    assert updates[0].actor_type == "platform_admin"
    assert updates[0].before is not None
    assert updates[0].before["logo_ref"] is None
    assert updates[0].after is not None
    assert updates[0].after["logo_ref"] == branding["logo_ref"]

    removed = await client.delete(logo_url, headers=onboarding)
    assert removed.status_code == 200
    assert removed.json()["logo_ref"] is None
    gone = await client.get(logo_url, headers=onboarding)
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "not_found"

    # Removing what is already gone is not a change, so it writes no audit row.
    assert (await client.delete(logo_url, headers=onboarding)).status_code == 200
    updates = [
        entry
        for entry in await full_stream(tenant_id)
        if entry.object_type == "tenant_branding" and entry.action == "update"
    ]
    assert len(updates) == 2


async def test_a_logo_over_the_limit_or_of_the_wrong_type_is_refused_and_stores_nothing(
    client: httpx.AsyncClient, onboarding: dict[str, str], object_store_root: Path
) -> None:
    tenant_id = await _register(client, onboarding)

    too_big = await _upload(client, onboarding, tenant_id, _png(pad_to=LOGO_MAX_BYTES + 1))
    assert too_big.status_code == 422
    assert too_big.json()["error"]["code"] == "file_too_large"
    assert "512 KB" in too_big.json()["error"]["message"]

    refused = {
        "svg": (SVG, "logo.svg", "image/svg+xml"),
        "svg named and typed as a png": (SVG, "logo.png", "image/png"),
        "svg with an xml prolog": (b'<?xml version="1.0"?>' + SVG, "logo.svg", "image/svg+xml"),
        "gif": (b"GIF89a" + b"\x00" * 16, "logo.gif", "image/gif"),
        "pdf": (b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", "logo.pdf", "application/pdf"),
        "html": (b"<!doctype html><title>x</title>", "logo.html", "text/html"),
        "text": (b"not an image at all", "logo.txt", "text/plain"),
        "empty": (b"", "logo.png", "image/png"),
    }
    for label, (data, filename, content_type) in refused.items():
        response = await _upload(client, onboarding, tenant_id, data, (filename, content_type))
        assert response.status_code == 422, label
        assert response.json()["error"]["code"] == "unsupported_file_type", label

    # Nothing reached the store, the row, or the trail.
    assert _stored_files(object_store_root) == []
    branding = (await client.get(f"{TENANTS_URL}/{tenant_id}/branding", headers=onboarding)).json()
    assert branding["logo_ref"] is None
    assert not [
        entry
        for entry in await full_stream(tenant_id)
        if entry.object_type == "tenant_branding" and entry.action == "update"
    ]

    # The limit is inclusive, and the type is read from the bytes: a real PNG is accepted
    # whatever name and content type the client dressed it in.
    assert (
        await _upload(client, onboarding, tenant_id, _png(pad_to=LOGO_MAX_BYTES))
    ).status_code == 200
    disguised = await _upload(client, onboarding, tenant_id, _png(), ("logo.svg", "image/svg+xml"))
    assert disguised.status_code == 200


async def test_the_logo_routes_follow_the_permissions_of_the_rest_of_branding(
    client: httpx.AsyncClient, onboarding: dict[str, str], object_store_root: Path
) -> None:
    tenant_id = await _register(client, onboarding)
    assert (await _upload(client, onboarding, tenant_id, _png())).status_code == 200
    logo_url = f"{TENANTS_URL}/{tenant_id}/branding/logo"

    # A read-only operator can see the logo and cannot change it.
    support = await seed_admin(email="support@example.com", role="support")
    reader = provider_session_headers(support.id)
    assert (await client.get(logo_url, headers=reader)).status_code == 200
    refused = await _upload(client, reader, tenant_id, _png(marker=b"x"))
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "permission_denied"
    assert (await client.delete(logo_url, headers=reader)).status_code == 403

    # A workspace member's token is not an operator's, and no token is not either.
    member = bearer(issue_token(subject=uuid.uuid4(), plane="tenant", typ="session").token)
    for headers, expected in ((member, 403), ({}, 401)):
        assert (await client.get(logo_url, headers=headers)).status_code == expected
        assert (await _upload(client, headers, tenant_id, _png())).status_code == expected
        assert (await client.delete(logo_url, headers=headers)).status_code == expected

    # An unknown workspace is absent everywhere, and an upload to it stores nothing.
    before = len(_stored_files(object_store_root))
    ghost = uuid.uuid4()
    ghost_url = f"{TENANTS_URL}/{ghost}/branding/logo"
    assert (await _upload(client, onboarding, ghost, _png())).status_code == 404
    assert (await client.get(ghost_url, headers=onboarding)).status_code == 404
    assert (await client.delete(ghost_url, headers=onboarding)).status_code == 404
    assert len(_stored_files(object_store_root)) == before


# ---------------------------------------------------------------------------
# Provider: the register search, and the credential on a round trip
# ---------------------------------------------------------------------------


async def test_the_register_search_matches_names_and_slug_and_takes_wildcards_literally(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    await _register(client, onboarding, "acme", trading_name="Roadrunner Traps")
    await _register(client, onboarding, "globex")
    await _register(client, onboarding, "fifty-corp", legal_name="Fifty% Corp")

    async def slugs(**params: str) -> list[str]:
        response = await client.get(TENANTS_URL, params=params, headers=onboarding)
        assert response.status_code == 200
        return [item["slug"] for item in response.json()["items"]]

    assert await slugs(search="acme") == ["acme"]
    assert await slugs(search="ACME") == ["acme"], "case does not matter"
    assert await slugs(search="roadrunner") == ["acme"], "the trading name counts"
    assert await slugs(search="glob") == ["globex"], "a substring of the slug or name"
    assert await slugs(search="%") == ["fifty-corp"], "a percent sign is text, not a wildcard"
    assert await slugs(search="_") == [], "an underscore is text, not a wildcard"
    assert await slugs(search="nobody") == []
    assert await slugs(search="acme", status="active") == [], "the filters combine"
    assert await slugs(search="acme", status="provisioning") == ["acme"]
    assert len(await slugs()) == 3, "no search means the whole register"

    too_long = await client.get(TENANTS_URL, params={"search": "x" * 101}, headers=onboarding)
    assert too_long.status_code == 422


async def test_saving_branding_without_the_credential_keeps_it_and_null_clears_it(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    """The record is write-only for its credential, so a client round-tripping the
    branding form cannot send it back; a save of the colours must not destroy it."""
    tenant_id = await _register(client, onboarding)
    url = f"{TENANTS_URL}/{tenant_id}/branding"
    secret = "smtp://mailer:s3cret@smtp.acme.example:587"  # noqa: S105 — test value

    async def stored() -> str | None:
        async with provider_session_scope() as session:
            return (
                await session.execute(
                    select(TenantBranding.smtp_config_ref).where(
                        TenantBranding.tenant_id == tenant_id
                    )
                )
            ).scalar_one()

    assert (
        await client.put(url, json={"smtp_config_ref": secret}, headers=onboarding)
    ).status_code == 200
    first = await stored()
    assert first is not None

    saved = await client.put(url, json={"primary_color": "#7c3aed"}, headers=onboarding)
    assert saved.status_code == 200
    assert saved.json()["primary_color"] == "#7c3aed"
    assert await stored() == first, "ciphertext untouched: omitted means keep"
    assert get_secret_box().decrypt(first, aad=f"tenant_branding:{tenant_id}") == secret

    cleared = await client.put(url, json={"smtp_config_ref": None}, headers=onboarding)
    assert cleared.status_code == 200
    assert await stored() is None, "an explicit null clears it"


async def test_branding_refuses_a_colour_that_is_not_six_hex_digits(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant_id = await _register(client, onboarding)
    url = f"{TENANTS_URL}/{tenant_id}/branding"
    for colour in ("red", "#abc", "#12345g", "#0f172a;}body{display:none"):
        for field in ("primary_color", "secondary_color"):
            response = await client.put(url, json={field: colour}, headers=onboarding)
            assert response.status_code == 422, f"{field}={colour}"
    assert (
        await client.put(url, json={"primary_color": "#0F172A"}, headers=onboarding)
    ).status_code == 200


async def test_a_profile_patch_cannot_null_a_required_column(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant_id = await _register(client, onboarding)
    for body in ({"legal_name": None}, {"plan": None}):
        response = await client.patch(f"{TENANTS_URL}/{tenant_id}", json=body, headers=onboarding)
        assert response.status_code == 422, body
    cleared = await client.patch(
        f"{TENANTS_URL}/{tenant_id}", json={"city": None}, headers=onboarding
    )
    assert cleared.status_code == 200
    assert cleared.json()["city"] is None


# ---------------------------------------------------------------------------
# Tenant plane: a member reads their own workspace's branding and logo, no one else's
# ---------------------------------------------------------------------------


async def test_a_member_reads_their_own_branding_and_logo_and_never_another_workspaces(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    acme = await signup_workspace(company="Acme Compliance", email="founder@acme.example")
    globex = await signup_workspace(company="Globex Security", email="founder@globex.example")
    # The Chief Executive Officer role holds tenant:read and nothing else: the least
    # any member of a workspace can hold.
    invited = await invite_directly(
        acme, email="ceo@acme.example", full_name="Chief Exec", role_name="Chief Executive Officer"
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Chief Exec", password=INVITEE_PASSWORD
    )
    acme_admin = tenant_session_headers(acme.membership_id)
    acme_member = tenant_session_headers(invited.member.membership_id)
    globex_admin = tenant_session_headers(globex.membership_id)

    # Before anything is set: branding reads empty, and there is no logo to fetch.
    empty = (await client.get(BRANDING_URL, headers=acme_admin)).json()
    assert empty["logo_ref"] is None
    assert (await client.get(LOGO_URL, headers=acme_admin)).status_code == 404

    # The provider brands both. The PUT replaces the whole record, so it goes first and
    # the upload, which only sets the logo, goes second.
    acme_logo, globex_logo = _png(marker=b"acme"), _png(marker=b"globex")
    for tenant, logo, colour in (
        (acme.tenant_id, acme_logo, "#7c3aed"),
        (globex.tenant_id, globex_logo, "#0f766e"),
    ):
        put = await client.put(
            f"{TENANTS_URL}/{tenant}/branding",
            json={"primary_color": colour, "document_footer": f"Confidential {colour}"},
            headers=onboarding,
        )
        assert put.status_code == 200
        assert (await _upload(client, onboarding, tenant, logo)).status_code == 200

    for headers in (acme_admin, acme_member):
        branding = (await client.get(BRANDING_URL, headers=headers)).json()
        assert branding["tenant_id"] == str(acme.tenant_id)
        assert branding["primary_color"] == "#7c3aed"
        assert branding["document_footer"] == "Confidential #7c3aed"
        assert "smtp_config_ref" not in branding
        served = await client.get(LOGO_URL, headers=headers)
        assert served.status_code == 200
        assert served.content == acme_logo
        assert served.headers["content-type"] == "image/png"
        assert served.headers["cache-control"] == "private, max-age=300"
        assert served.headers["x-content-type-options"] == "nosniff"
    assert (await client.get(LOGO_URL, headers=globex_admin)).content == globex_logo
    assert (await client.get(BRANDING_URL, headers=globex_admin)).json()[
        "primary_color"
    ] == "#0f766e"

    # Authentication comes first, and a provider token is not a member's.
    provider_token = bearer(
        issue_token(subject=uuid.uuid4(), plane="provider", typ="session").token
    )
    for url in (BRANDING_URL, LOGO_URL):
        assert (await client.get(url)).status_code == 401
        assert (await client.get(url, headers=provider_token)).status_code == 403

    # No tenant route takes an identifier, so the only way across is a stored reference.
    # Point Acme's logo at Globex's object: the store refuses a key outside the tenant
    # asking, which reads as absent, and Globex is untouched.
    globex_ref = (await client.get(BRANDING_URL, headers=globex_admin)).json()["logo_ref"]
    crossed = await client.put(
        f"{TENANTS_URL}/{acme.tenant_id}/branding",
        json={"logo_ref": globex_ref},
        headers=onboarding,
    )
    assert crossed.status_code == 200
    stolen = await client.get(LOGO_URL, headers=acme_admin)
    assert stolen.status_code == 404
    assert globex_logo not in stolen.content
    assert (await client.get(LOGO_URL, headers=globex_admin)).content == globex_logo

    # A reference to one of Acme's own objects that is not an image is not served either.
    document = get_object_store().put(
        acme.tenant_id, "report.pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    )
    await client.put(
        f"{TENANTS_URL}/{acme.tenant_id}/branding",
        json={"logo_ref": document.key},
        headers=onboarding,
    )
    not_an_image = await client.get(LOGO_URL, headers=acme_admin)
    assert not_an_image.status_code == 404
    assert b"%PDF" not in not_an_image.content
