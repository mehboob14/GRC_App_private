"""The vendors API through the real app: real token, real permissions, real RLS.

The other three vendor integration suites drive ``vendor_service`` directly and
make zero HTTP calls, which is how three GET routes shipped unreachable --
declared after ``GET /{vendor_id}``, captured by the path parameter, answering
422 forever. A green service-level suite says nothing about whether the API can
be reached.

So this file is deliberately shallow and wide: it proves every read route
resolves to its own handler and returns its own shape, and walks the smallest
write path that gets an engagement to the approval gate. Depth belongs in the
service suites; reachability belongs here.

``test_route_shadowing`` proves the ordering rule statically for every router.
This proves it dynamically for this one, which is the router that broke.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]

API = "/api/v1/vendors"


@pytest.fixture
async def workspace(clean_iam: None, clean_tenancy: None, clean_audit_log: None) -> Workspace:
    """A real tenant whose admin holds every permission, including all four
    vendors keys. Nothing is stubbed: the token is minted by the real login
    flow and the routes resolve it through the real dependency chain."""
    return await signup_workspace(company="Routes Ltd", email="routes@example.test")


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {workspace.session_token}"},
    ) as http_client:
        yield http_client


async def _vendor(client: httpx.AsyncClient) -> tuple[str, str]:
    """One vendor with one engagement, created through the API."""
    response = await client.post(
        API,
        json={
            "name": "Routed Analytics",
            "vendor_type": "vendor",
            "data_classification": "confidential",
            "engagement": {"name": "Attribution"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["id"], body["engagements"][0]["id"]


# ---------------------------------------------------------------------------
# Reachability — the failure this file exists for
# ---------------------------------------------------------------------------


async def test_the_collection_routes_are_not_captured_by_the_vendor_id_route(
    client: httpx.AsyncClient,
) -> None:
    """These three shipped after ``GET /{vendor_id}`` and answered 422 forever.

    A 422 here does not mean "bad request" -- it means the literal segment was
    parsed as a UUID, which is the shadowing bug wearing a validation error's
    clothes. Asserting on the body shape, not just the status, is what makes
    this test catch a re-ordering rather than a coincidence.
    """
    findings = await client.get(f"{API}/findings")
    assert findings.status_code == 200, findings.text
    assert set(findings.json()) == {"items", "total"}

    intake = await client.get(f"{API}/intake")
    assert intake.status_code == 200, intake.text
    assert set(intake.json()) == {"items", "total"}

    roster = await client.get(f"{API}/roster")
    assert roster.status_code == 200, roster.text
    assert set(roster.json()) == {"roles"}


async def test_every_read_route_resolves_to_its_own_handler(
    client: httpx.AsyncClient,
) -> None:
    vendor_id, engagement_id = await _vendor(client)

    register = await client.get(API)
    assert register.status_code == 200, register.text
    assert register.json()["total"] == 1

    facets = await client.get(f"{API}/facets")
    assert facets.status_code == 200, facets.text
    facet_body = facets.json()
    # The lifecycle vocabulary is served rather than reimplemented in TypeScript.
    assert len(facet_body["stages"]) == 12
    assert len(facet_body["tiering_factors"]) == 5
    assert "critical" in facet_body["reviewer_roles_by_tier"]

    duplicates = await client.get(f"{API}/duplicate-check", params={"name": "Routed Analytics"})
    assert duplicates.status_code == 200, duplicates.text
    assert [m["name"] for m in duplicates.json()["matches"]] == ["Routed Analytics"]

    detail = await client.get(f"{API}/{vendor_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["engagements"][0]["id"] == engagement_id

    approvers = await client.get(f"{API}/{vendor_id}/engagements/{engagement_id}/approvers")
    assert approvers.status_code == 200, approvers.text
    assert "items" in approvers.json()


async def test_a_vendor_that_is_not_there_is_a_404_not_a_500(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(f"{API}/{uuid.uuid4()}")
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"]


async def test_an_unauthenticated_caller_gets_401_on_every_collection_route(
    app: FastAPI,
) -> None:
    """Rule 7 is deny-by-default, and the three formerly-shadowed routes have to
    prove it too -- a shadowed route inherits the *other* route's guard."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as anonymous:
        for path in ("", "/facets", "/findings", "/intake", "/roster"):
            response = await anonymous.get(f"{API}{path}")
            assert response.status_code == 401, f"{path}: {response.status_code}"


# ---------------------------------------------------------------------------
# The smallest write walk that reaches the gate
# ---------------------------------------------------------------------------


async def test_tiering_plans_twelve_stages_and_a_low_tier_skips_four(
    client: httpx.AsyncClient,
) -> None:
    vendor_id, engagement_id = await _vendor(client)

    response = await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={
            "data_sensitivity": 0,
            "business_criticality": 1,
            "system_access": 0,
            "regulatory_scope": 0,
            "fourth_party_reliance": 0,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["tier"] == "low"

    stages = body["stages"]
    assert len(stages) == 12
    # Every row lands not_started: nothing is in_progress until an advance.
    assert {s["status"] for s in stages} == {"not_started", "skipped"}
    skipped = {s["stage"] for s in stages if s["status"] == "skipped"}
    assert skipped == {"diligence", "questionnaire", "scoring", "findings"}
    # A gate is never skipped, whatever the tier.
    assert [s["stage"] for s in stages if s["is_gate"]] == ["approval"]
    assert all(s["status"] != "skipped" for s in stages if s["is_gate"])


async def test_a_low_tier_advance_walks_over_the_skipped_stages(
    client: httpx.AsyncClient,
) -> None:
    """Intake to tiering to *contracting* -- the proportionality is visible in
    the rows rather than implied by an absent one."""
    vendor_id, engagement_id = await _vendor(client)
    membership = (await client.get(f"{API}/{vendor_id}")).json()["ownership"]

    # Intake needs a named business owner before it will clear.
    assert membership["business_owner_membership_id"] is None
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200, me.text
    await client.patch(
        f"{API}/{vendor_id}",
        json={
            "name": "Routed Analytics",
            "vendor_type": "vendor",
            "data_classification": "confidential",
            "business_owner_membership_id": me.json()["membership_id"],
        },
    )
    await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={
            "data_sensitivity": 0,
            "business_criticality": 1,
            "system_access": 0,
            "regulatory_scope": 0,
            "fourth_party_reliance": 0,
        },
    )

    reached = []
    for _ in range(3):
        detail = (await client.get(f"{API}/{vendor_id}")).json()
        current = next(s for s in detail["stages"] if s["status"] not in {"complete", "skipped"})
        reached.append(current["stage"])
        response = await client.post(
            f"{API}/{vendor_id}/stages/{current['id']}/advance", json={"note": None}
        )
        assert response.status_code == 200, response.text

    assert reached == ["intake", "tiering", "contracting"]


async def test_the_gate_refuses_the_vendors_own_business_owner(
    client: httpx.AsyncClient,
) -> None:
    """Segregation of duties, visible before the decision rather than after it."""
    vendor_id, engagement_id = await _vendor(client)
    me = (await client.get("/api/v1/auth/me")).json()
    await client.patch(
        f"{API}/{vendor_id}",
        json={
            "name": "Routed Analytics",
            "vendor_type": "vendor",
            "data_classification": "confidential",
            "business_owner_membership_id": me["membership_id"],
        },
    )
    await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={
            "data_sensitivity": 0,
            "business_criticality": 1,
            "system_access": 0,
            "regulatory_scope": 0,
            "fourth_party_reliance": 0,
        },
    )

    approvers = await client.get(f"{API}/{vendor_id}/engagements/{engagement_id}/approvers")
    assert approvers.status_code == 200, approvers.text
    items = approvers.json()["items"]
    mine = next(a for a in items if a["membership_id"] == me["membership_id"])
    assert mine["disqualified_reason"] is not None
