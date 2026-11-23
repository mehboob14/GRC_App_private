"""Suggestions from the profile: accepted through the owning service, rejected with a reason,
batch refused where a person must decide one at a time (guided onboarding PL-1 to PL-5, SC-5)."""

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
    return await signup_workspace(company="Suggest Ltd", email="founder@suggest.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _framework(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    found: dict[str, Any] = next(
        f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == code
    )
    return found


async def _proposals(api: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    response = await api.get("/onboarding/proposals")
    assert response.status_code == 200, response.text
    return {p["key"]: p for p in response.json()["proposals"]}


async def _decide(api: httpx.AsyncClient, **body: Any) -> httpx.Response:
    return await api.post("/onboarding/proposals/decide", json=body)


async def test_answers_propose_changes_that_apply_through_the_owning_service(
    api: httpx.AsyncClient,
) -> None:
    iso = await _framework(api, "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    assert (await api.get("/onboarding/proposals")).json()["open"] == 0
    patched = await api.patch(
        "/tenant/profile",
        json={
            "answers": {
                "offices": "none",
                "builds_software": "not_sure",
                "public_app": "no",
                "hosting_providers": ["aws"],
            }
        },
    )
    assert patched.status_code == 200, patched.text
    found = await _proposals(api)
    assert "no_offices.controls:PE-02" in found
    assert "no_offices.iso:A.7.1" in found
    assert "no_public_app.controls:NS-10" in found
    assert not [k for k in found if k.startswith("no_software")], "not sure proposes nothing"
    assert "AWS" in found["no_offices.iso:A.7.1"]["reason"]

    # Batch accept of the office group is allowed.
    office_iso = [k for k in found if k.startswith("no_offices.iso:")]
    accepted = await _decide(api, keys=office_iso, accept=True, bulk=True)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["decided"] == len(office_iso)
    statement = (await api.get(f"/frameworks/{iso['framework_id']}/applicability")).json()
    a71 = next(r for r in statement["rows"] if r["code"] == "A.7.1")
    assert (a71["applicable"], a71["provided_by"]) == (True, "supplier")
    assert a71["reviewed_at"] is not None

    # One control accepted with an edited reason; the control moves through its own service.
    edited = await _decide(
        api, keys=["no_offices.controls:PE-02"], accept=True, reason="Fully remote since 2024."
    )
    assert edited.status_code == 200, edited.text
    controls = {c["code"]: c for c in (await api.get("/controls")).json()}
    assert controls["PE-02"]["status"] == "not_applicable"

    # Reject needs a reason.
    refused = await _decide(api, keys=["no_public_app.controls:NS-10"], accept=False)
    assert refused.status_code == 422
    rejected = await _decide(
        api, keys=["no_public_app.controls:NS-10"], accept=False, reason="Our API is public."
    )
    assert rejected.status_code == 200, rejected.text

    after = await _proposals(api)
    assert after["no_offices.controls:PE-02"]["state"] == "accepted"
    assert after["no_offices.controls:PE-02"]["reason"] == "Fully remote since 2024."
    assert after["no_public_app.controls:NS-10"]["state"] == "rejected"
    assert controls["NS-10"]["status"] == "not_started"

    # The answer changes: the accepted decision now needs a second look.
    await api.patch("/tenant/profile", json={"answers": {"offices": "own_premises"}})
    lapsed = await _proposals(api)
    assert lapsed["no_offices.controls:PE-02"]["state"] == "review_needed"
    assert (await api.get("/onboarding/proposals")).json()["review_needed"] >= 1


async def test_batch_refused_where_a_person_decides_each(api: httpx.AsyncClient) -> None:
    await api.patch("/tenant/profile", json={"answers": {"builds_software": "no"}})
    found = await _proposals(api)
    software = [k for k in found if k.startswith("no_software.controls:")]
    assert software
    assert found[software[0]]["bulk_ok"] is False
    refused = await _decide(api, keys=software, accept=True, bulk=True)
    assert refused.status_code == 409, refused.text
    one = await _decide(api, keys=[software[0]], accept=True)
    assert one.status_code == 200, one.text

    gone = await _decide(api, keys=["no_offices.controls:PE-02"], accept=True)
    assert gone.status_code == 404


async def test_a_commitment_suggests_its_soc2_category(api: httpx.AsyncClient) -> None:
    soc2 = await _framework(api, "SOC2")
    today = datetime.now(UTC).date()
    saved = await api.put(
        "/engagement",
        json={
            "name": "SOC 2",
            "framework_version_id": soc2["version_id"],
            "audit_type": "type_2",
            "categories_in_scope": [],
            "window_start": str(today),
            "window_end": str(today + timedelta(days=90)),
        },
    )
    assert saved.status_code == 200, saved.text
    made = await api.post(
        "/commitments",
        json={
            "statement": "99.9% monthly uptime",
            "source_kind": "service_levels",
            "points_at": ["Availability"],
        },
    )
    assert made.status_code == 201, made.text
    found = await _proposals(api)
    key = "commitment.category:Availability"
    assert found[key]["change"] == "Add Availability to your SOC 2 scope"
    assert (await _decide(api, keys=[key], accept=True)).status_code == 200
    engagement = (await api.get("/engagement", params={"framework": "SOC2"})).json()
    assert engagement["categories_in_scope"] == ["Availability"]
    assert (await _proposals(api))[key]["state"] == "accepted"
