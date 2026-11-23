"""Baseline, snapshot, work plan, setup state and approved SoA versions (guided onboarding phase 5)."""

from __future__ import annotations

from collections.abc import AsyncIterator
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
    return await signup_workspace(company="Plan Ltd", email="founder@plan.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _controls(api: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    return {c["code"]: c for c in (await api.get("/controls")).json()}


async def test_baseline_to_plan_to_tasks_once(api: httpx.AsyncClient, workspace: Workspace) -> None:
    empty = (await api.get("/onboarding/baseline")).json()
    assert empty["status"] == "none"
    assert empty["total"] > 0
    assert (await api.post("/onboarding/plan/approve")).status_code == 409

    controls = await _controls(api)
    me = str(workspace.membership_id)
    assert (await api.put("/onboarding/owner-functions/it_lead", json={"membership_id": me})).status_code == 204  # noqa: E501
    for code, answer in (("IAM-01", "in_place"), ("IAM-02", "not_in_place"), ("HR-01", "not_sure")):
        r = await api.put(
            f"/onboarding/baseline/controls/{controls[code]['id']}", json={"answer": answer}
        )
        assert r.status_code == 204, r.text
    bad = await api.put(
        f"/onboarding/baseline/controls/{controls['IAM-01']['id']}", json={"answer": "yes"}
    )
    assert bad.status_code == 422

    view = (await api.get("/onboarding/baseline")).json()
    assert view["status"] == "open"
    assert view["answered"] == 3
    assert view["counts"]["not_in_place"] == 1
    # The person's view never moves the control's status.
    assert (await _controls(api))["IAM-01"]["status"] == controls["IAM-01"]["status"]

    done = await api.post("/onboarding/baseline/complete")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "complete"
    snaps = (await api.get("/onboarding/snapshots")).json()
    assert [s["label"] for s in snaps] == ["Baseline"]
    assert snaps[0]["figures"]["controls_total"] > 0

    plan = (await api.get("/onboarding/plan")).json()
    keys = {i["key"]: i for i in plan["items"]}
    assert set(keys) == {"evidence:IAM-01", "control:IAM-02", "control:HR-01"}
    assert keys["control:IAM-02"]["owner_membership_id"] == me, "owner from the IT lead function"

    first = await api.post("/onboarding/plan/approve")
    assert first.status_code == 200, first.text
    assert first.json()["raised"] == 3
    again = await api.post("/onboarding/plan/approve")
    assert again.json()["raised"] == 0, "approving twice raises nothing new"
    assert all(i["raised"] for i in (await api.get("/onboarding/plan")).json()["items"])


async def test_connection_suggestions_follow_the_profile(api: httpx.AsyncClient) -> None:
    assert (await api.get("/onboarding/connections")).json() == []
    await api.patch(
        "/tenant/profile",
        json={"answers": {"identity_provider": "okta", "builds_software": "yes"}},
    )
    found = {c["key"]: c for c in (await api.get("/onboarding/connections")).json()}
    assert set(found) == {"okta", "github"}
    assert found["github"]["status"] == "available"
    assert found["github"]["connected"] is False


async def test_setup_state_and_statement_versions(api: httpx.AsyncClient) -> None:
    assert (await api.get("/onboarding/setup")).json()["start_point"] is None
    saved = await api.put("/onboarding/setup", json={"start_point": "fresh", "setup_step": "profile"})
    assert saved.status_code == 200, saved.text
    assert (await api.put("/onboarding/setup", json={"setup_step": "nowhere"})).status_code == 422
    finished = await api.put("/onboarding/setup", json={"setup_step": "suggestions", "complete": True})
    assert finished.json()["completed_at"] is not None
    assert finished.json()["start_point"] == "fresh"

    iso = next(f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    base = f"/frameworks/{iso['framework_id']}/applicability"
    refused = await api.post(f"{base}/versions", json={})
    assert refused.status_code == 409, "nothing reviewed yet"
    statement = (await api.get(base)).json()
    for row in statement["rows"]:
        if row["locked"]:
            continue
        r = await api.put(
            f"{base}/{row['requirement_id']}",
            json={"applicable": True, "provided_by": "organization", "reviewed": True},
        )
        assert r.status_code == 200, r.text
    v1 = await api.post(f"{base}/versions", json={"note": "First statement"})
    assert v1.status_code == 201, v1.text
    assert v1.json()["number"] == 1
    v2 = await api.post(f"{base}/versions", json={})
    assert v2.json()["number"] == 2
    listed = (await api.get(f"{base}/versions")).json()
    assert [v["number"] for v in listed] == [2, 1]
    workbook = await api.get(f"{base}/versions/1.xlsx")
    assert workbook.status_code == 200
    assert workbook.content[:2] == b"PK"
    assert (await api.get(f"{base}/versions/9.xlsx")).status_code == 404
