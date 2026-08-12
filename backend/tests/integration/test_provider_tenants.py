"""The tenants register through the real app: registration, profile, branding,
provisioning — real tokens, real dependencies, real policies, real audit rows."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from tests.support.tenancy import (
    bearer,
    provider_session_headers,
    registration_payload,
    seed_admin,
)
from verity.core.config import Settings
from verity.core.crypto import get_secret_box
from verity.core.db import dispose_engine, provider_session_scope
from verity.core.security import issue_token
from verity.main import create_app
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import audit_service
from verity.modules.tenancy.models import Tenant, TenantBranding
from verity.modules.tenancy.repository import PlatformAdminRepository, TenantRepository
from verity.modules.tenancy.service import (
    AllProvisioningGates,
    NoMembershipsYet,
    tenancy_service,
)

pytestmark = pytest.mark.integration

TENANTS_URL = "/api/v1/provider/tenants"


@pytest.fixture(autouse=True)
async def _clean_state(clean_tenancy: None, clean_audit_log: None) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


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
    """An authenticated onboarding admin's headers."""
    admin = await seed_admin(role="onboarding")
    return provider_session_headers(admin.id)


async def _tenant_stream(tenant_id: uuid.UUID) -> list[AuditLog]:
    async with provider_session_scope() as session:
        entries, _ = await audit_service.list_page(session, tenant_id=tenant_id, limit=100)
    return entries


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


async def test_registration_creates_the_tenant_its_steps_and_its_audit_stream(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    response = await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    assert response.status_code == 201
    tenant = response.json()
    assert tenant["status"] == "provisioning"
    assert tenant["slug"] == "acme"
    assert tenant["created_by"] is not None
    assert tenant["created_at"].endswith("Z")

    provisioning = (
        await client.get(f"{TENANTS_URL}/{tenant['id']}/provisioning", headers=onboarding)
    ).json()
    by_step = {step["step"]: step for step in provisioning["steps"]}
    assert set(by_step) == {"create_tenant", "seed_content", "invite_admin", "verify"}
    # Decision 10: create_tenant is done at registration — the row is the step.
    assert by_step["create_tenant"]["status"] == "done"
    assert by_step["create_tenant"]["completed_at"] is not None
    assert provisioning["remaining"] == ["seed_content", "invite_admin", "verify"]

    stream = await _tenant_stream(uuid.UUID(tenant["id"]))
    created = sorted(entry.object_type for entry in stream if entry.action == "create")
    assert created == ["tenant", "tenant_branding"] + ["tenant_provisioning"] * 4
    tenant_row = next(entry for entry in stream if entry.object_type == "tenant")
    assert tenant_row.actor_type == "platform_admin"
    assert tenant_row.after is not None
    assert tenant_row.after["legal_name"] == "Acme Pty Ltd"


async def test_a_repeat_with_the_same_key_and_body_returns_the_original_tenant(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    headers = {**onboarding, "Idempotency-Key": "reg-001"}
    body = registration_payload("acme")
    first = await client.post(TENANTS_URL, json=body, headers=headers)
    second = await client.post(TENANTS_URL, json=body, headers=headers)
    assert first.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    listing = (await client.get(TENANTS_URL, headers=onboarding)).json()
    assert len(listing["items"]) == 1, "no second tenant, no second set of steps"
    stream = await _tenant_stream(uuid.UUID(first.json()["id"]))
    assert len([e for e in stream if e.object_type == "tenant_provisioning"]) == 4


async def test_the_same_key_with_a_different_body_is_409(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    headers = {**onboarding, "Idempotency-Key": "reg-002"}
    assert (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=headers)
    ).status_code == 201
    conflict = await client.post(TENANTS_URL, json=registration_payload("other"), headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_conflict"


async def test_a_taken_slug_is_409_with_no_partial_rows(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    assert (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).status_code == 201
    conflict = await client.post(
        TENANTS_URL,
        json=registration_payload("acme", legal_name="Impostor Ltd"),
        headers=onboarding,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "slug_conflict"

    listing = (await client.get(TENANTS_URL, headers=onboarding)).json()
    assert [item["legal_name"] for item in listing["items"]] == ["Acme Pty Ltd"]


async def test_the_status_check_refuses_a_value_outside_the_lifecycle(
    onboarding: dict[str, str],
) -> None:
    """The database, not only the schema, bounds the status column."""

    async def write_bad_status() -> None:
        async with provider_session_scope() as session:
            await TenantRepository().add(
                session,
                Tenant(legal_name="X", slug="x-corp", plan="starter", status="haunted"),
            )

    with pytest.raises(DBAPIError, match="ck_tenants__status_valid"):
        await write_bad_status()


# ---------------------------------------------------------------------------
# Authorization boundaries
# ---------------------------------------------------------------------------


async def test_a_support_admin_reads_but_cannot_register(client: httpx.AsyncClient) -> None:
    support = await seed_admin(email="support@example.com", role="support")
    headers = provider_session_headers(support.id)
    assert (await client.get(TENANTS_URL, headers=headers)).status_code == 200
    refused = await client.post(TENANTS_URL, json=registration_payload("acme"), headers=headers)
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "permission_denied"


async def test_a_tenant_plane_token_is_403_on_every_provider_route(
    client: httpx.AsyncClient,
) -> None:
    """Authenticated but categorically not an operator — and nothing is disclosed."""
    tenant_token = issue_token(subject=uuid.uuid4(), plane="tenant", typ="session").token
    for method, url in (
        ("GET", TENANTS_URL),
        ("POST", TENANTS_URL),
        ("GET", f"{TENANTS_URL}/{uuid.uuid4()}"),
        ("POST", f"{TENANTS_URL}/{uuid.uuid4()}/provision"),
    ):
        response = await client.request(
            method, url, headers=bearer(tenant_token), json=registration_payload("acme")
        )
        assert response.status_code == 403, f"{method} {url}"
        assert "acme" not in response.text
        assert response.json()["error"]["code"] == "permission_denied"


async def test_no_token_and_garbage_tokens_are_401(client: httpx.AsyncClient) -> None:
    assert (await client.get(TENANTS_URL)).status_code == 401
    assert (await client.get(TENANTS_URL, headers=bearer("not-a-token"))).status_code == 401


async def test_a_disabled_admins_live_session_stops_working(
    client: httpx.AsyncClient,
) -> None:
    """Decision 17: enforcement is per-request database state, not token validity."""
    admin = await seed_admin()
    headers = provider_session_headers(admin.id)
    assert (await client.get(TENANTS_URL, headers=headers)).status_code == 200
    async with provider_session_scope() as session:
        row = await PlatformAdminRepository().get(session, admin.id)
        assert row is not None
        row.status = "disabled"
    assert (await client.get(TENANTS_URL, headers=headers)).status_code == 401


async def test_an_unknown_tenant_is_404_everywhere(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    ghost = uuid.uuid4()
    for method, url, body in (
        ("GET", f"{TENANTS_URL}/{ghost}", None),
        ("PATCH", f"{TENANTS_URL}/{ghost}", {"plan": "growth"}),
        ("GET", f"{TENANTS_URL}/{ghost}/branding", None),
        ("PUT", f"{TENANTS_URL}/{ghost}/branding", {"primary_color": "#123456"}),
        ("POST", f"{TENANTS_URL}/{ghost}/provision", None),
        ("GET", f"{TENANTS_URL}/{ghost}/provisioning", None),
    ):
        response = await client.request(method, url, headers=onboarding, json=body)
        assert response.status_code == 404, f"{method} {url}"
        assert response.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Profile updates and the register
# ---------------------------------------------------------------------------


async def test_patch_updates_the_profile_and_audits_both_snapshots(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    response = await client.patch(
        f"{TENANTS_URL}/{tenant['id']}",
        json={"plan": "growth", "city": "Sydney"},
        headers=onboarding,
    )
    assert response.status_code == 200
    assert response.json()["plan"] == "growth"

    stream = await _tenant_stream(uuid.UUID(tenant["id"]))
    update = next(e for e in stream if e.action == "update" and e.object_type == "tenant")
    assert update.before is not None
    assert update.before["plan"] == "starter"
    assert update.after is not None
    assert update.after["city"] == "Sydney"


async def test_status_and_slug_are_not_writable_through_patch(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    for body in ({"status": "active"}, {"slug": "stolen"}):
        response = await client.patch(
            f"{TENANTS_URL}/{tenant['id']}", json=body, headers=onboarding
        )
        assert response.status_code == 422, f"{body} must be refused, not dropped"


async def test_the_register_paginates_newest_first_without_repeats(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    for slug in ("first", "second", "third"):
        assert (
            await client.post(TENANTS_URL, json=registration_payload(slug), headers=onboarding)
        ).status_code == 201

    page_one = (await client.get(TENANTS_URL, params={"limit": 2}, headers=onboarding)).json()
    assert [item["slug"] for item in page_one["items"]] == ["third", "second"]
    assert page_one["next_cursor"] is not None

    page_two = (
        await client.get(
            TENANTS_URL,
            params={"limit": 2, "cursor": page_one["next_cursor"]},
            headers=onboarding,
        )
    ).json()
    assert [item["slug"] for item in page_two["items"]] == ["first"]
    assert page_two["next_cursor"] is None

    filtered = (
        await client.get(TENANTS_URL, params={"status": "active"}, headers=onboarding)
    ).json()
    assert filtered["items"] == []


# ---------------------------------------------------------------------------
# Branding — the SMTP credential's whole lifecycle
# ---------------------------------------------------------------------------

SMTP_SECRET = "smtp://mailer:hunter2@smtp.acme.example:587"  # noqa: S105 — test value


async def test_branding_put_encrypts_the_credential_and_never_returns_it(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    tenant_id = uuid.UUID(tenant["id"])

    response = await client.put(
        f"{TENANTS_URL}/{tenant_id}/branding",
        json={
            "primary_color": "#0f172a",
            "custom_domain": "trust.acme.example",
            "email_from_address": "compliance@acme.example",
            "smtp_config_ref": SMTP_SECRET,
        },
        headers=onboarding,
    )
    assert response.status_code == 200
    assert "smtp_config_ref" not in response.json()
    assert SMTP_SECRET not in response.text

    read_back = await client.get(f"{TENANTS_URL}/{tenant_id}/branding", headers=onboarding)
    assert "smtp_config_ref" not in read_back.json()

    # What reached the database is ciphertext, decryptable only under this
    # tenant's AAD — moved to another row it would refuse to decrypt.
    async with provider_session_scope() as session:
        stored = (
            await session.execute(
                select(TenantBranding.smtp_config_ref).where(TenantBranding.tenant_id == tenant_id)
            )
        ).scalar_one()
    assert stored is not None
    assert stored != SMTP_SECRET
    assert stored.startswith("v1.")
    box = get_secret_box()
    assert box.decrypt(stored, aad=f"tenant_branding:{tenant_id}") == SMTP_SECRET

    # And the audit snapshots exclude it entirely — absent, not redacted.
    stream = await _tenant_stream(tenant_id)
    updates = [e for e in stream if e.object_type == "tenant_branding" and e.action == "update"]
    assert len(updates) == 1
    for snapshot in (updates[0].before, updates[0].after):
        assert snapshot is not None
        assert "smtp_config_ref" not in snapshot
    assert SMTP_SECRET not in str(stream)


async def test_an_identical_branding_put_writes_nothing(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    body = {"primary_color": "#0f172a", "smtp_config_ref": SMTP_SECRET}
    url = f"{TENANTS_URL}/{tenant['id']}/branding"
    assert (await client.put(url, json=body, headers=onboarding)).status_code == 200
    assert (await client.put(url, json=body, headers=onboarding)).status_code == 200

    stream = await _tenant_stream(uuid.UUID(tenant["id"]))
    updates = [e for e in stream if e.object_type == "tenant_branding" and e.action == "update"]
    assert len(updates) == 1, "a full replace with the same values is not a state change"


async def test_branding_put_is_a_full_replace_and_omitted_fields_clear(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    url = f"{TENANTS_URL}/{tenant['id']}/branding"
    await client.put(
        url,
        json={"primary_color": "#111111", "custom_domain": "trust.acme.example"},
        headers=onboarding,
    )
    replaced = (await client.put(url, json={"logo_ref": "s3://logo"}, headers=onboarding)).json()
    assert replaced["logo_ref"] == "s3://logo"
    assert replaced["primary_color"] is None
    assert replaced["custom_domain"] is None


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------


async def test_provisioning_completes_what_it_can_and_reports_the_rest(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    run = (await client.post(f"{TENANTS_URL}/{tenant['id']}/provision", headers=onboarding)).json()
    # seed_content completes as an honest no-op; the membership-gated steps wait
    # for IAM (decision 10), so the tenant must not become active.
    assert run["tenant_status"] == "provisioning"
    assert run["remaining"] == ["invite_admin", "verify"]
    by_step = {step["step"]: step["status"] for step in run["steps"]}
    assert by_step["seed_content"] == "done"

    stream = await _tenant_stream(uuid.UUID(tenant["id"]))
    transitions = [e.object_type for e in stream if e.action == "transition"]
    assert transitions == ["tenant_provisioning"], "one transition: seed_content, this run"


async def test_a_second_provisioning_run_writes_nothing(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    url = f"{TENANTS_URL}/{tenant['id']}/provision"
    first = (await client.post(url, headers=onboarding)).json()
    audit_after_first = len(await _tenant_stream(uuid.UUID(tenant["id"])))

    second = (await client.post(url, headers=onboarding)).json()
    assert second == first, "no step repeated, no completion time overwritten"
    assert len(await _tenant_stream(uuid.UUID(tenant["id"]))) == audit_after_first, (
        "no state changed, so no audit row was written"
    )


async def test_when_every_gate_passes_the_tenant_activates_in_the_same_run(
    client: httpx.AsyncClient, onboarding: dict[str, str]
) -> None:
    tenant = (
        await client.post(TENANTS_URL, json=registration_payload("acme"), headers=onboarding)
    ).json()
    tenancy_service.use_gates(AllProvisioningGates())
    try:
        run = (
            await client.post(f"{TENANTS_URL}/{tenant['id']}/provision", headers=onboarding)
        ).json()
    finally:
        tenancy_service.use_gates(NoMembershipsYet())

    assert run["remaining"] == []
    assert run["tenant_status"] == "active"

    stream = await _tenant_stream(uuid.UUID(tenant["id"]))
    tenant_transitions = [
        e for e in stream if e.action == "transition" and e.object_type == "tenant"
    ]
    assert len(tenant_transitions) == 1
    assert tenant_transitions[0].before is not None
    assert tenant_transitions[0].before["status"] == "provisioning"
    assert tenant_transitions[0].after is not None
    assert tenant_transitions[0].after["status"] == "active"
