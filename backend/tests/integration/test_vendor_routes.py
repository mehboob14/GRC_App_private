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
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]


def _today() -> date:
    """Timezone-explicit "today": every date this product stores is UTC."""
    return datetime.now(UTC).date()


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


# ---------------------------------------------------------------------------
# The edits a reviewer needs after the first write
# ---------------------------------------------------------------------------


async def test_a_draft_contract_is_edited_into_an_active_one(client: httpx.AsyncClient) -> None:
    """A contract recorded as a draft could never become active, so it could never
    satisfy the contracting check."""
    vendor_id, _ = await _vendor(client)
    created = await client.post(
        f"{API}/{vendor_id}/contracts", json={"title": "MSA 2026", "status": "draft"}
    )
    assert created.status_code == 201, created.text
    contract_id = created.json()["id"]
    edited = await client.put(
        f"{API}/{vendor_id}/contracts/{contract_id}",
        json={"title": "MSA 2026 (signed)", "status": "active", "right_to_audit": True},
    )
    assert edited.status_code == 200, edited.text
    assert (edited.json()["status"], edited.json()["right_to_audit"]) == ("active", True)


async def test_a_contact_is_corrected_in_place(client: httpx.AsyncClient) -> None:
    vendor_id, _ = await _vendor(client)
    detail = await client.post(
        f"{API}/{vendor_id}/contacts",
        json={"name": "Dana Reed", "email": "dana@old.test", "contact_type": "portal"},
    )
    contact_id = detail.json()["contacts"][0]["id"]
    edited = await client.put(
        f"{API}/{vendor_id}/contacts/{contact_id}",
        json={"name": "Dana Reed", "email": "dana@new.test", "contact_type": "portal"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["contacts"][0]["email"] == "dana@new.test"
    # A portal contact still needs somewhere to send the link.
    refused = await client.put(
        f"{API}/{vendor_id}/contacts/{contact_id}",
        json={"name": "Dana Reed", "email": None, "contact_type": "portal"},
    )
    assert refused.status_code == 422, refused.text


async def test_a_removed_subprocessor_stays_on_the_record(client: httpx.AsyncClient) -> None:
    vendor_id, _ = await _vendor(client)
    added = await client.post(
        f"{API}/{vendor_id}/subprocessors", json={"name": "Northwind Hosting"}
    )
    sub_id = added.json()["items"][0]["id"]
    removed = await client.post(f"{API}/{vendor_id}/subprocessors/{sub_id}/remove")
    assert removed.status_code == 200, removed.text
    assert [s["status"] for s in removed.json()["items"]] == ["removed"]


async def test_a_roster_role_can_be_taken_away_again(client: httpx.AsyncClient) -> None:
    me = (await client.get("/api/v1/auth/me")).json()["membership_id"]
    await client.post(f"{API}/roster", json={"role": "legal", "membership_id": me})
    removed = await client.delete(f"{API}/roster/legal/{me}")
    assert removed.status_code == 200, removed.text
    assert removed.json()["roles"].get("legal", []) == []


async def test_notifying_the_next_reviewer_lands_in_their_inbox(
    client: httpx.AsyncClient,
) -> None:
    vendor_id, engagement_id = await _vendor(client)
    await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={"data_sensitivity": 4, "business_criticality": 4, "system_access": 4},
    )
    detail = (await client.get(f"{API}/{vendor_id}")).json()
    gate = next(s for s in detail["stages"] if s["stage"] == "approval")
    me = (await client.get("/api/v1/auth/me")).json()["membership_id"]
    sent = await client.post(
        f"{API}/{vendor_id}/stages/{gate['id']}/notify", json={"membership_ids": [me]}
    )
    assert sent.status_code == 200, sent.text
    assert sent.json() == {"sent": 1}


async def test_the_register_leaves_archived_vendors_out_unless_asked(
    client: httpx.AsyncClient,
) -> None:
    vendor_id, _ = await _vendor(client)
    started = await client.post(f"{API}/{vendor_id}/offboarding", json={"reason": "Replaced."})
    exit_id = started.json()["offboardings"][0]["id"]
    done = await client.post(
        f"{API}/{vendor_id}/offboarding/{exit_id}",
        json={
            "access_revoked": True,
            "data_returned": True,
            "contract_provisions_reviewed": True,
            "final_payments_settled": True,
            "complete": True,
        },
    )
    assert done.json()["lifecycle_status"] == "archived", done.text
    listed = {v["id"] for v in (await client.get(API)).json()["items"]}
    assert vendor_id not in listed
    archived = await client.get(API, params={"statuses": "archived"})
    assert vendor_id in {v["id"] for v in archived.json()["items"]}
    summary = (await client.get(f"{API}/summary")).json()
    assert summary["unowned"] == 0, "an archived vendor is not an ownership gap"


# ---------------------------------------------------------------------------
# Monitoring, policy, manual findings, document files and service levels
# ---------------------------------------------------------------------------


async def test_the_policy_is_editable_but_the_gate_is_not(client: httpx.AsyncClient) -> None:
    """A workspace tunes what a tier is worth in work. It cannot tune away the gate."""
    policy = (await client.get(f"{API}/policy")).json()
    assert policy["is_customised"] is False
    assert policy["cadence_days_by_tier"]["critical"] == 180
    assert "approval" not in policy["skippable_stages"]

    body = {
        "tier_thresholds": policy["tier_thresholds"],
        "cadence_days_by_tier": {**policy["cadence_days_by_tier"], "critical": 90},
        "finding_sla_days_by_severity": {**policy["finding_sla_days_by_severity"], "critical": 3},
        "stage_skip_matrix_by_tier": policy["stage_skip_matrix_by_tier"],
        "required_reviewer_roles_by_tier": policy["required_reviewer_roles_by_tier"],
    }
    saved = await client.put(f"{API}/policy", json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()["cadence_days_by_tier"]["critical"] == 90
    assert saved.json()["is_customised"] is True

    refused = await client.put(
        f"{API}/policy", json={**body, "stage_skip_matrix_by_tier": {"low": ["approval"]}}
    )
    assert refused.status_code == 422, refused.text
    too_short = await client.put(
        f"{API}/policy", json={**body, "cadence_days_by_tier": {"critical": 2}}
    )
    assert too_short.status_code == 422, too_short.text


async def test_a_finding_raised_by_hand_takes_the_policy_window(
    client: httpx.AsyncClient,
) -> None:
    vendor_id, engagement_id = await _vendor(client)
    policy = (await client.get(f"{API}/policy")).json()
    await client.put(
        f"{API}/policy",
        json={
            "tier_thresholds": policy["tier_thresholds"],
            "cadence_days_by_tier": policy["cadence_days_by_tier"],
            "finding_sla_days_by_severity": {
                **policy["finding_sla_days_by_severity"],
                "critical": 3,
            },
            "stage_skip_matrix_by_tier": policy["stage_skip_matrix_by_tier"],
            "required_reviewer_roles_by_tier": policy["required_reviewer_roles_by_tier"],
        },
    )
    raised = await client.post(
        f"{API}/{vendor_id}/findings",
        json={
            "title": "No MFA on their support console",
            "severity": "critical",
            "engagement_id": engagement_id,
            "is_blocking": True,
        },
    )
    assert raised.status_code == 201, raised.text
    body = raised.json()
    assert body["finding_source"] == "manual"
    assert body["sla_due"] == str(_today() + timedelta(days=3))


async def test_a_signal_is_recorded_decided_and_can_raise_a_finding(
    client: httpx.AsyncClient,
) -> None:
    vendor_id, _ = await _vendor(client)
    recorded = await client.post(
        f"{API}/{vendor_id}/signals",
        json={
            "signal_type": "breach",
            "title": "Customer data exposed in their support tool",
            "severity": "high",
            "source_class": "media",
            "raise_finding": True,
        },
    )
    assert recorded.status_code == 201, recorded.text
    signal = recorded.json()["signals"][0]
    assert signal["status"] == "new"

    findings = (await client.get(f"{API}/findings")).json()["items"]
    assert [f["finding_source"] for f in findings] == ["signal"]

    decided = await client.post(
        f"{API}/{vendor_id}/signals/{signal['id']}/status", json={"status": "acknowledged"}
    )
    assert decided.status_code == 200, decided.text
    settled = decided.json()["signals"][0]
    assert settled["status"] == "acknowledged"
    assert settled["acknowledged_by_name"] is not None

    future = await client.post(
        f"{API}/{vendor_id}/signals",
        json={
            "signal_type": "breach",
            "title": "Next year's breach",
            "observed_on": str(_today() + timedelta(days=2)),
        },
    )
    assert future.status_code == 422, future.text


async def test_a_document_is_reviewed_and_carries_its_file(client: httpx.AsyncClient) -> None:
    vendor_id, _ = await _vendor(client)
    created = await client.post(
        f"{API}/{vendor_id}/documents", json={"title": "SOC 2 Type II", "doc_type": "soc_report"}
    )
    document_id = created.json()["id"]
    reviewed = await client.put(
        f"{API}/{vendor_id}/documents/{document_id}",
        json={
            "title": "SOC 2 Type II 2026",
            "doc_type": "soc_report",
            "collection_status": "reviewed",
            "review_notes": "Clean opinion, user entity controls checked.",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    row = next(d for d in reviewed.json()["documents"] if d["id"] == document_id)
    assert (row["collection_status"], row["title"]) == ("reviewed", "SOC 2 Type II 2026")
    assert row["reviewed_by_name"] is not None

    pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
    attached = await client.post(
        f"{API}/{vendor_id}/documents/{document_id}/file",
        files={"file": ("soc2.pdf", pdf, "application/pdf")},
    )
    assert attached.status_code == 200, attached.text
    assert next(d for d in attached.json()["documents"] if d["id"] == document_id)["evidence_id"]


async def test_a_service_level_records_its_measurement(client: httpx.AsyncClient) -> None:
    vendor_id, _ = await _vendor(client)
    contract = await client.post(
        f"{API}/{vendor_id}/contracts", json={"title": "Hosting agreement", "status": "active"}
    )
    contract_id = contract.json()["id"]
    added = await client.post(
        f"{API}/{vendor_id}/slas",
        json={
            "contract_id": contract_id,
            "name": "Uptime",
            "target": "99.9% monthly",
            "measurement": "99.2%",
            "measured_on": str(_today()),
            "status": "breached",
        },
    )
    assert added.status_code == 201, added.text
    sla = added.json()["items"][0]
    assert (sla["status"], sla["contract_title"]) == ("breached", "Hosting agreement")

    fixed = await client.put(
        f"{API}/{vendor_id}/slas/{sla['id']}",
        json={
            "contract_id": contract_id,
            "name": "Uptime",
            "target": "99.9% monthly",
            "measurement": "99.95%",
            "status": "on_track",
        },
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["items"][0]["measurement"] == "99.95%"
    detail = (await client.get(f"{API}/{vendor_id}")).json()
    assert [s["name"] for s in detail["slas"]] == ["Uptime"]


# ---------------------------------------------------------------------------
# Reviewing together, alert rules and shadow IT
# ---------------------------------------------------------------------------


async def test_an_alert_rule_fires_on_a_matching_signal(client: httpx.AsyncClient) -> None:
    """A rule that matches nothing until every box is ticked is a rule people
    stop using, so an empty filter means "any"."""
    vendor_id, engagement_id = await _vendor(client)
    await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={"data_sensitivity": 4, "business_criticality": 4, "system_access": 4},
    )
    made = await client.post(
        f"{API}/alert-rules",
        json={
            "name": "Breach anywhere",
            "signal_types": ["breach"],
            "min_severity": "medium",
            "action": "create_task",
        },
    )
    assert made.status_code == 201, made.text
    rule_id = made.json()["items"][0]["id"]

    recorded = await client.post(
        f"{API}/{vendor_id}/signals",
        json={"signal_type": "breach", "title": "Data exposed", "severity": "high"},
    )
    assert recorded.status_code == 201, recorded.text
    tasks = await client.get("/api/v1/tasks", params={"category": "vendor"})
    assert tasks.status_code == 200, tasks.text
    assert any("Data exposed" in t["title"] for t in tasks.json()["items"])

    off = await client.put(
        f"{API}/alert-rules/{rule_id}",
        json={
            "name": "Breach anywhere",
            "signal_types": ["breach"],
            "min_severity": "medium",
            "action": "create_task",
            "is_enabled": False,
        },
    )
    assert off.json()["items"][0]["is_enabled"] is False
    assert (await client.delete(f"{API}/alert-rules/{rule_id}")).json()["items"] == []


async def test_two_people_review_different_domains_at_once(client: httpx.AsyncClient) -> None:
    vendor_id, engagement_id = await _vendor(client)
    me = (await client.get("/api/v1/auth/me")).json()["membership_id"]
    await client.post(
        f"{API}/{vendor_id}/contacts",
        json={"name": "Dana Reed", "email": "dana@routed.test", "contact_type": "portal"},
    )
    await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={"data_sensitivity": 4, "business_criticality": 4, "system_access": 4},
    )
    issued = await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/questionnaire", json={}
    )
    assert issued.status_code == 201, issued.text
    assessment_id = issued.json()["assessment_id"]

    first = await client.post(
        f"{API}/{vendor_id}/assessments/{assessment_id}/reviewers",
        json={"membership_id": me, "domain": "access_control"},
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"{API}/{vendor_id}/assessments/{assessment_id}/reviewers",
        json={"membership_id": me, "domain": "compliance_legal"},
    )
    assert {r["domain"] for r in second.json()["items"]} == {"access_control", "compliance_legal"}

    reviewer_id = first.json()["items"][0]["id"]
    done = await client.post(
        f"{API}/{vendor_id}/assessments/{assessment_id}/reviewers/{reviewer_id}",
        json={"status": "done", "note": "Answers check out."},
    )
    by_domain = {r["domain"]: r["status"] for r in done.json()["items"]}
    assert by_domain == {"access_control": "done", "compliance_legal": "assigned"}

    refused = await client.post(
        f"{API}/{vendor_id}/assessments/{assessment_id}/reviewers",
        json={"membership_id": me, "domain": "not_a_domain"},
    )
    assert refused.status_code == 422, refused.text


async def test_an_internal_comment_never_reaches_the_portal(client: httpx.AsyncClient) -> None:
    """Visibility is a security boundary, so it is enforced in the query rather
    than by what the portal chooses to render."""
    vendor_id, engagement_id = await _vendor(client)
    await client.post(
        f"{API}/{vendor_id}/contacts",
        json={"name": "Dana Reed", "email": "dana@routed.test", "contact_type": "portal"},
    )
    await client.post(
        f"{API}/{vendor_id}/engagements/{engagement_id}/tiering",
        json={"data_sensitivity": 4, "business_criticality": 4, "system_access": 4},
    )
    issued = (
        await client.post(f"{API}/{vendor_id}/engagements/{engagement_id}/questionnaire", json={})
    ).json()
    assessment_id, token = issued["assessment_id"], issued["portal_url"].rsplit("/", 1)[-1]

    await client.post(
        f"{API}/{vendor_id}/assessments/{assessment_id}/comments",
        json={"body": "Their SOC report is a year old.", "visibility": "internal_only"},
    )
    shared = await client.post(
        f"{API}/{vendor_id}/assessments/{assessment_id}/comments",
        json={"body": "Could you send the current pen test?", "visibility": "vendor_shared"},
    )
    assert shared.status_code == 201, shared.text
    assert len(shared.json()["items"]) == 2

    portal = await client.get(f"/api/v1/vendor-portal/{token}")
    assert portal.status_code == 200, portal.text
    bodies = [c["body"] for c in portal.json()["comments"]]
    assert bodies == ["Could you send the current pen test?"]

    replied = await client.post(
        f"/api/v1/vendor-portal/{token}/comments", json={"body": "Sent this morning."}
    )
    assert replied.status_code == 200, replied.text
    assert [c["from_vendor"] for c in replied.json()["comments"]] == [False, True]

    internal = await client.get(f"{API}/{vendor_id}/assessments/{assessment_id}/comments")
    assert len(internal.json()["items"]) == 3, "the team sees both sides"


async def test_a_discovered_app_goes_through_the_front_door(client: httpx.AsyncClient) -> None:
    recorded = await client.post(
        f"{API}/discovered-apps",
        json={"app_name": "Figma", "authorizing_users": 34, "oauth_scopes": ["files.read"]},
    )
    assert recorded.status_code == 201, recorded.text
    app_id = recorded.json()["items"][0]["id"]
    # Recording it again is the same app, not a second row.
    again = await client.post(f"{API}/discovered-apps", json={"app_name": "figma"})
    assert len(again.json()["items"]) == 1

    triaged = await client.post(
        f"{API}/discovered-apps/{app_id}/triage", json={"disposition": "added_as_vendor"}
    )
    assert triaged.status_code == 200, triaged.text
    assert triaged.json()["items"][0]["disposition"] == "added_as_vendor"
    intake = await client.get(f"{API}/intake")
    assert "Figma" in [r["vendor_name"] for r in intake.json()["items"]]
