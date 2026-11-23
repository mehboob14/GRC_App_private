"""Owner functions and the Required documents list (guided onboarding phase 4)."""

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
    return await signup_workspace(company="Owners Ltd", email="founder@owners.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _controls(api: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    response = await api.get("/controls")
    assert response.status_code == 200, response.text
    return {c["code"]: c for c in response.json()}


async def test_owner_functions_fill_unowned_controls_and_keep_set_ones(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    me = str(workspace.membership_id)
    controls = await _controls(api)
    kept = controls["IAM-01"]["id"]
    # A person already chose an owner for IAM-01; nothing should overwrite it by default.
    assert (
        await api.patch(f"/controls/{kept}", json={"owner_membership_id": me})
    ).status_code == 200

    for key in ("it_lead", "security_lead"):
        response = await api.put(f"/onboarding/owner-functions/{key}", json={"membership_id": me})
        assert response.status_code == 204, response.text
    view = (await api.get("/onboarding/owner-functions")).json()
    it_lead = next(f for f in view["functions"] if f["key"] == "it_lead")
    assert it_lead["membership_id"] == me
    assert it_lead["controls"] > 0
    assert view["would_change"] > 0

    applied = await api.post("/onboarding/owner-functions/apply", json={"keep_existing": True})
    assert applied.status_code == 200, applied.text
    assert applied.json()["changed"] == view["would_change"]
    after = await _controls(api)
    assert after["IAM-02"]["owner_membership_id"] == me
    assert after["SD-01"]["owner_membership_id"] is None, "engineering lead has nobody yet"

    unknown = await api.put("/onboarding/owner-functions/ceo", json={"membership_id": me})
    assert unknown.status_code == 422

    status = (await api.get("/onboarding/status")).json()
    step = next(s for s in status["steps"] if s["key"] == "functions")
    assert (step["done_count"], step["total_count"]) == (2, 8)


async def test_the_required_list_follows_the_profile_and_starts_linked_drafts(
    api: httpx.AsyncClient,
) -> None:
    patched = await api.patch(
        "/tenant/profile",
        json={"answers": {"offices": "none", "work_arrangement": "remote"}},
    )
    assert patched.status_code == 200, patched.text
    required = (await api.get("/onboarding/required-documents")).json()
    titles = {r["title"]: r for r in required["rows"]}
    hidden = {h["title"] for h in required["hidden"]}
    assert "Physical security policy for offices" in hidden
    assert "Remote working policy" in titles
    assert "ISMS scope statement" not in titles, "ISO 27001 is not active"
    access = titles["Access control policy"]
    assert access["state"] == "not_started"
    assert access["template_available"] is True

    created = await api.post(
        "/documents/from-template", json={"template_key": "access-control-policy"}
    )
    assert created.status_code == 201, created.text
    document = (await api.get(f"/documents/{created.json()['id']}")).json()
    assert {"IAM-01", "IAM-02"} <= set(document["controls"]), document["controls"]

    again = (await api.get("/onboarding/required-documents")).json()
    row = next(r for r in again["rows"] if r["title"] == "Access control policy")
    assert row["state"] == "draft"
    assert row["document_id"] == created.json()["id"]
    assert again["approved"] == 0
