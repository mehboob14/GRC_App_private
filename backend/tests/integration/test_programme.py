"""The programme around an audit (guided onboarding phase 3): milestones, cycles, changes in the
period, commitments, vendors that count, scope suggestions, turning a framework off."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.main import create_app
from verity.modules.audit.service import Membership
from verity.modules.vendors.service import TieringAnswers, VendorInput, vendor_service

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
    return await signup_workspace(company="Programme Ltd", email="founder@programme.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _framework(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    found: dict[str, Any] = next(
        f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == code
    )
    return found


async def _soc2(api: httpx.AsyncClient, **fields: object) -> None:
    soc2 = await _framework(api, "SOC2")
    body = {
        "name": "SOC 2",
        "framework_version_id": soc2["version_id"],
        "audit_type": "type_1",
        "categories_in_scope": [],
        **fields,
    }
    response = await api.put("/engagement", json=body)
    assert response.status_code == 200, response.text


async def _critical_vendor(workspace: Workspace, name: str) -> str:
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        vendor = await vendor_service.create_vendor(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            data=VendorInput(
                name=name,
                data_classification="confidential",
                business_owner_membership_id=workspace.membership_id,
            ),
        )
        await vendor_service.tier_engagement(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            engagement_id=vendor.engagements[0].id,
            answers=TieringAnswers(
                override_tier="critical", override_justification="Hosts production."
            ),
        )
    return str(vendor.id)


async def test_milestones_keep_engagement_dates_on_the_engagement(api: httpx.AsyncClient) -> None:
    today = datetime.now(UTC).date()
    await _soc2(
        api,
        audit_type="type_2",
        window_start=str(today),
        window_end=str(today + timedelta(days=90)),
    )
    plan = (await api.get("/engagement/milestones")).json()
    kinds = {m["kind"]: m for m in plan}
    assert kinds["period_start"]["from_engagement"] is True
    assert kinds["period_start"]["planned_on"] == str(today)
    assert kinds["fieldwork"]["planned_on"] is None

    saved = await api.put(
        "/engagement/milestones",
        json={
            "milestones": [{"kind": "fieldwork", "planned_on": str(today + timedelta(days=100))}]
        },
    )
    assert saved.status_code == 200, saved.text
    assert {m["kind"]: m for m in saved.json()}["fieldwork"]["planned_on"] == str(
        today + timedelta(days=100)
    )
    refused = await api.put(
        "/engagement/milestones", json={"milestones": [{"kind": "period_start"}]}
    )
    assert refused.status_code == 422


async def test_a_new_cycle_keeps_history_and_carries_the_scope(api: httpx.AsyncClient) -> None:
    await _soc2(api, certification_body="Example CPA LLP")
    item = (
        await api.post("/engagement/scope-items", json={"kind": "system", "name": "Core API"})
    ).json()
    await api.put(f"/engagement/scope-items/{item['id']}/decision", json={"in_scope": True})
    nxt = await api.post(
        "/engagement/next-cycle", json={"name": "SOC 2 2028", "audit_type": "type_1"}
    )
    assert nxt.status_code == 201, nxt.text
    cycles = (await api.get("/engagement/cycles")).json()
    assert [(c["name"], c["is_current"], c["status"]) for c in cycles] == [
        ("SOC 2 2028", True, "draft"),
        ("SOC 2", False, "closed"),
    ]
    assert (await api.get("/engagement")).json()["name"] == "SOC 2 2028"
    listed = (await api.get("/engagement/scope-items")).json()
    assert listed[0]["in_scope"] is True, "the scope decision carried over"


async def test_changes_inside_the_period_are_listed(api: httpx.AsyncClient) -> None:
    today = datetime.now(UTC).date()
    await _soc2(
        api,
        audit_type="type_2",
        window_start=str(today - timedelta(days=5)),
        window_end=str(today + timedelta(days=60)),
    )
    item = (
        await api.post("/engagement/scope-items", json={"kind": "site", "name": "Office"})
    ).json()
    await api.put(
        f"/engagement/scope-items/{item['id']}/decision",
        json={"in_scope": False, "reason": "Fully remote."},
    )
    changes = (await api.get("/engagement/changes")).json()
    assert any("out of scope" in c["summary"] for c in changes)


async def test_commitments_are_added_edited_and_retired(api: httpx.AsyncClient) -> None:
    added = await api.post(
        "/commitments",
        json={
            "statement": "99.9 percent monthly uptime for the hosted service.",
            "source_kind": "service_levels",
            "source_ref": "Customer terms, section 4",
            "points_at": ["availability"],
        },
    )
    assert added.status_code == 201, added.text
    commitment = added.json()
    edited = await api.put(
        f"/commitments/{commitment['id']}",
        json={"statement": "99.95 percent uptime.", "source_kind": "contract"},
    )
    assert edited.json()["statement"] == "99.95 percent uptime."
    retired = await api.post(
        f"/commitments/{commitment['id']}/retire", json={"reason": "Replaced by new terms."}
    )
    assert retired.status_code == 204
    assert (await api.get("/commitments")).json() == []


async def test_vendors_that_count_and_scope_suggestions(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    await _soc2(api)
    vendor_id = await _critical_vendor(workspace, "Acme Cloud")
    await api.post("/assets", json={"name": "Payments API"})

    suggestions = (await api.get("/engagement/scope-suggestions")).json()
    names = {s["name"]: s for s in suggestions}
    assert names["Acme Cloud"]["kind"] == "vendor"
    assert names["Payments API"]["kind"] == "system"
    accepted = await api.post(
        "/engagement/scope-suggestions/accept",
        json={"refs": [{"ref_type": s["ref_type"], "ref_id": s["ref_id"]} for s in suggestions]},
    )
    assert accepted.json()["added"] == len(suggestions)
    assert (await api.get("/engagement/scope-suggestions")).json() == []

    refused = await api.put(f"/engagement/vendors/{vendor_id}", json={"role": "subservice"})
    assert refused.status_code == 422
    marked = await api.put(
        f"/engagement/vendors/{vendor_id}", json={"role": "subservice", "method": "carve_out"}
    )
    assert marked.status_code == 204, marked.text
    listed = (await api.get("/engagement/vendors")).json()
    assert [(v["name"], v["role"], v["method"]) for v in listed] == [
        ("Acme Cloud", "subservice", "carve_out")
    ]
    removed = await api.post(
        f"/engagement/vendors/{vendor_id}/remove", json={"reason": "Migrated away."}
    )
    assert removed.status_code == 204
    assert (await api.get("/engagement/vendors")).json() == []


async def test_turning_a_framework_off_lists_its_own_controls_and_keeps_one(
    api: httpx.AsyncClient,
) -> None:
    soc2 = await _framework(api, "SOC2")
    last = await api.post(
        f"/tenant-frameworks/{soc2['framework_id']}/deactivate", json={"reason": "Not needed."}
    )
    assert last.status_code == 409

    iso = await _framework(api, "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    off = await api.post(
        f"/tenant-frameworks/{iso['framework_id']}/deactivate",
        json={"reason": "Customer no longer asks for it."},
    )
    assert off.status_code == 200, off.text
    only_here = off.json()["controls_only_here"]
    assert only_here, "ISO adds controls SOC 2 does not need"
    assert not (await _framework(api, "ISO27001"))["added"]
