"""Assessment objectives end to end: outcomes from documents and tagged evidence, a not
applicable decision with its reason, next steps, the first audit view and the comparison with
today's readiness (AO-1 to AO-5). Nothing here changes readiness itself."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings
from verity.core.db import dispose_engine
from verity.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _clean_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def workspace() -> Workspace:
    return await signup_workspace(company="Objective Ltd", email="founder@objective.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _control(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    found: dict[str, Any] = next(
        c for c in (await api.get("/controls")).json() if c["code"] == code
    )
    return found


async def _objectives(api: httpx.AsyncClient, control_id: str) -> dict[str, Any]:
    r = await api.get(f"/objectives/controls/{control_id}")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


async def test_outcomes_follow_documents_and_tagged_evidence(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    gov18 = await _control(api, "GOV-18")
    view = await _objectives(api, gov18["id"])
    assert view["frameworks"] == ["SOC2"]
    assert view["review_status"] == "draft_unreviewed"
    a = view["objectives"][0]
    assert (a["code"], a["assurance"], a["outcome"]) == ("GOV-18.A", "design", "not_tested")
    assert a["next_step"]["action"] == "assign_owner", "an unowned control asks for an owner first"
    assert not view["design_ready"]

    me = str(workspace.membership_id)
    assert (
        await api.patch(f"/controls/{gov18['id']}", json={"owner_membership_id": me})
    ).status_code == 200
    a = (await _objectives(api, gov18["id"]))["objectives"][0]
    assert a["next_step"]["action"] == "start_document"

    # Approve the risk method outside Verity: the document artifact is satisfied.
    for template in ("risk-assessment-methodology", "risk-management-policy"):
        doc = await api.post("/documents/from-template", json={"template_key": template})
        assert doc.status_code == 201, doc.text
        ok = await api.post(
            f"/documents/{doc.json()['id']}/approved-elsewhere", json={"approved_on": "2026-01-10"}
        )
        assert ok.status_code == 200, ok.text
    view = await _objectives(api, gov18["id"])
    a = view["objectives"][0]
    assert a["outcome"] == "satisfied", a

    # Person evidence counts only once a person says which record it is.
    signoff = next(
        art["key"]
        for o in view["objectives"]
        for art in o["artifacts"]
        if art["key"] == "management-sign-off-on-the-assessment"
    )
    item = await api.post(
        "/evidence/link",
        json={
            "title": "CEO sign off on the 2026 risk assessment",
            "link_url": "https://example.test/signoff",
            "evidence_type": "other",
            "collected_at": str(datetime.now(UTC).date()),
            "control_ids": [gov18["id"]],
        },
    )
    assert item.status_code == 201, item.text
    before = next(
        art for o in view["objectives"] for art in o["artifacts"] if art["key"] == signoff
    )
    assert before["state"] == "not_satisfied"
    tagged = await api.put(
        f"/objectives/artifacts/{signoff}/evidence", json={"evidence_id": item.json()["id"]}
    )
    assert tagged.status_code == 204, tagged.text
    after = await _objectives(api, gov18["id"])
    art = next(a for o in after["objectives"] for a in o["artifacts"] if a["key"] == signoff)
    assert (art["state"], art["reason"]) == ("not_satisfied", "awaiting_review"), (
        "only reviewed counts"
    )
    reviewed = await api.post(
        f"/evidence/{item.json()['id']}/review", json={"decision": "approved"}
    )
    assert reviewed.status_code == 200, reviewed.text
    after = await _objectives(api, gov18["id"])
    art = next(a for o in after["objectives"] for a in o["artifacts"] if a["key"] == signoff)
    assert art["state"] == "satisfied"
    interviews = [o["interview_with"] for o in after["objectives"] if o["interview_with"]]
    assert interviews, "interviews name who is interviewed"

    # A system-only record refuses a person's upload.
    refused = await api.put(
        "/objectives/artifacts/branch-protection-settings/evidence",
        json={"evidence_id": item.json()["id"]},
    )
    assert refused.status_code == 422


async def test_not_applicable_needs_a_reason_and_can_be_withdrawn(api: httpx.AsyncClient) -> None:
    pe01 = await _control(api, "PE-01")
    code = (await _objectives(api, pe01["id"]))["objectives"][-1]["code"]
    empty = await api.post(f"/objectives/{code}/not-applicable", json={"reason": " "})
    assert empty.status_code == 422
    ok = await api.post(
        f"/objectives/{code}/not-applicable", json={"reason": "We hold no physical media."}
    )
    assert ok.status_code == 204, ok.text
    last = (await _objectives(api, pe01["id"]))["objectives"][-1]
    assert (last["outcome"], last["not_applicable_reason"]) == (
        "not_applicable",
        "We hold no physical media.",
    )
    assert (
        await api.post(f"/objectives/{code}/not-applicable", json={"reason": "x"})
    ).status_code == 409
    assert (await api.post(f"/objectives/{code}/applies-again")).status_code == 204
    assert (await _objectives(api, pe01["id"]))["objectives"][-1]["outcome"] != "not_applicable"
    assert (
        await api.post("/objectives/ZZ-99.A/not-applicable", json={"reason": "x"})
    ).status_code == 404


async def test_overview_first_audit_view_and_comparison(api: httpx.AsyncClient) -> None:
    iso = next(f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    overview = (await api.get("/objectives")).json()
    by_code = {f["code"]: f for f in overview["frameworks"]}
    assert set(by_code) == {"SOC2", "ISO27001"}
    assert by_code["SOC2"]["first_audit_label"] == "Type 1 design"
    assert by_code["ISO27001"]["first_audit_label"] == "Stage 1 design"
    assert "Plan the internal audit" in by_code["ISO27001"]["first_audit_notes"]
    assert by_code["ISO27001"]["controls"] >= 6, "the ISO management system controls count"
    assert overview["controls_with_objectives"] == overview["controls_total"], "every control"
    assert overview["next"], "there is always a next objective in a new workspace"
    assert overview["next"][0]["objective"]["assurance"] == "design"

    comparison = (await api.get("/objectives/comparison")).json()
    assert comparison["compared"] == overview["controls_total"]
    assert all(not r["ready_today"] and not r["ready_rule_b"] for r in comparison["rows"])

    status = (await api.get("/onboarding/status")).json()
    step = next(s for s in status["steps"] if s["key"] == "objectives")
    assert step["total_count"]
    assert step["done_count"] == 0
