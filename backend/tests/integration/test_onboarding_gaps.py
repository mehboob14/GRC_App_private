"""The guided onboarding gaps closed on 2026-11-23: Your part, prefill, section tasks, scope
notes, guidance notes, periodic controls, the asset id filter, scope statement approval,
planning from a certificate, milestone snapshots and offline document tailoring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings, get_settings
from verity.core.db import dispose_engine
from verity.main import create_app
from verity.modules.onboarding import assist

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
    return await signup_workspace(company="Gaps Ltd", email="founder@gaps.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _framework(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    found: dict[str, Any] = next(
        f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == code
    )
    return found


async def test_people_side(api: httpx.AsyncClient, workspace: Workspace) -> None:
    prefill = (await api.get("/onboarding/profile-prefill")).json()
    assert {
        "key": "headcount_band",
        "value": "1_10",
        "source": "From your member list, at least",
    } in prefill
    me = str(workspace.membership_id)
    sent = await api.post("/onboarding/profile-sections/data/assign", json={"membership_id": me})
    assert sent.json() == {"raised": 1}
    again = await api.post("/onboarding/profile-sections/data/assign", json={"membership_id": me})
    assert again.json() == {"raised": 0}, "asking twice makes nothing new"
    assert (
        await api.post("/onboarding/profile-sections/nope/assign", json={"membership_id": me})
    ).status_code == 404
    part = (await api.get("/onboarding/my-part")).json()["items"]
    assert any(i["kind"] == "task" and "Data and privacy" in i["title"] for i in part)

    await api.patch("/tenant/profile", json={"answers": {"oversight_body": "executive_team"}})
    notes = (await api.get("/onboarding/guidance-notes/GOV-02")).json()
    assert notes
    assert "executive team" in notes[0]
    assert (await api.get("/onboarding/guidance-notes/IAM-01")).json() == []

    owners = (await api.get("/onboarding/owner-functions")).json()
    assert owners["reassign"] == [], "nobody has left"


async def test_programme_side(api: httpx.AsyncClient) -> None:
    today = datetime.now(UTC).date()
    soc2 = await _framework(api, "SOC2")
    assert (await api.get("/onboarding/scope-notes")).json() == [], "no scope decided yet"
    saved = await api.put(
        "/engagement",
        json={
            "name": "SOC 2",
            "framework_version_id": soc2["version_id"],
            "audit_type": "type_2",
            "categories_in_scope": [],
            "window_start": str(today - timedelta(days=30)),
            "window_end": str(today + timedelta(days=150)),
        },
    )
    assert saved.status_code == 200, saved.text
    notes = (await api.get("/onboarding/scope-notes")).json()
    assert "DM-02" in notes, "a Privacy only control is not needed with Security alone"
    assert "IAM-01" not in notes

    periodic = (await api.get("/engagement/periodic")).json()
    assert periodic["label"] == "observation period"
    review = next(r for r in periodic["rows"] if r["code"] == "IAM-02")
    assert (review["cadence"], review["found"]) == ("quarterly", 0)
    assert review["needed"] == 2

    reached = await api.put(
        "/engagement/milestones",
        json={"milestones": [{"kind": "policies_approved", "actual_on": str(today)}]},
    )
    assert reached.status_code == 200, reached.text
    labels = [s["label"] for s in (await api.get("/onboarding/snapshots")).json()]
    assert labels == ["SOC2: Policies approved"]

    asset = (await api.post("/assets", json={"name": "Billing API"})).json()["id"]
    await api.post("/assets", json={"name": "Old box"})
    only = (await api.get("/assets", params={"ids": [asset]})).json()
    assert [a["id"] for a in only["items"]] == [asset]
    assert (await api.get("/engagement/in-scope-for", params={"ref_type": "asset"})).json() == {}


async def test_iso_scope_statement_approval_and_certificate(api: httpx.AsyncClient) -> None:
    iso = await _framework(api, "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    iso = await _framework(api, "ISO27001")
    body = {
        "name": "ISO 27001 surveillance",
        "framework_version_id": iso["version_id"],
        "audit_type": "surveillance",
        "categories_in_scope": [],
        "scope_statement": "The platform and the people who run it.",
        "scope_statement_ai": True,
    }
    assert (await api.put("/engagement", json=body)).status_code == 200
    q = {"framework": "ISO27001"}
    engagement = (await api.get("/engagement", params=q)).json()
    assert engagement["scope_statement_ai"] is True
    assert engagement["scope_statement_approved_at"] is None
    step = next(
        s
        for s in (await api.get("/onboarding/status")).json()["steps"]
        if s["key"] == "scope_statement:ISO27001"
    )
    assert (step["state"], step["detail"]) == ("in_progress", "Waiting for approval")
    approved = await api.post("/engagement/scope-statement/approve", params=q)
    assert approved.status_code == 200, approved.text
    assert approved.json()["scope_statement_approved_at"] is not None
    # New wording needs approving again.
    assert (
        await api.put(
            "/engagement",
            json={**body, "scope_statement": "Only the platform.", "scope_statement_ai": False},
        )
    ).status_code == 200
    assert (await api.get("/engagement", params=q)).json()["scope_statement_approved_at"] is None

    record = await api.post(
        "/engagement/assurance",
        params=q,
        json={"kind": "prior_certificate", "starts_on": "2026-03-01", "ends_on": "2029-02-28"},
    )
    assert record.status_code == 201, record.text
    assert (
        record.json()["notice"] == "Surveillance audit planned for 2027-03-01 from the certificate."
    )
    assert (await api.get("/engagement", params=q)).json()["audit_on"] == "2027-03-01"


async def test_offline_tailoring_returns_the_draft_untouched(
    api: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    keyless = get_settings().model_copy(
        update={"ai": get_settings().ai.model_copy(update={"api_key": None})}
    )
    monkeypatch.setattr(assist, "get_settings", lambda: keyless)
    doc = (
        await api.post("/documents/from-template", json={"template_key": "access-control-policy"})
    ).json()
    draft = await api.post(
        "/onboarding/assist", json={"kind": "document_tailoring", "subject": doc["id"]}
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["source"] == "template"
    assert "<" in draft.json()["text"]
