"""Get Started status (guided onboarding phase 1).

Every step's state is computed from records, the page covers every framework the
workspace runs, and a read only role gets the page instead of an error. The four defects
of the old page each have a test here: security alone is a decision, the connections step
is real, the control steps count every control, and a role without ``members:read`` loads.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.documents import client
from tests.support.iam import (
    INVITEE_PASSWORD,
    Workspace,
    invite_directly,
    signup_workspace,
    tenant_session_headers,
)
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.main import create_app
from verity.modules.audit.service import audit_service
from verity.modules.iam.service import iam_auth_service

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
    return await signup_workspace(company="Onboarding Ltd", email="founder@onboarding.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _status(api: httpx.AsyncClient) -> dict[str, Any]:
    response = await api.get("/onboarding/status")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _steps(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {step["key"]: step for step in body["steps"]}


async def _framework(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    response = await api.get("/tenant-frameworks")
    assert response.status_code == 200, response.text
    found: dict[str, Any] = next(f for f in response.json() if f["code"] == code)
    return found


async def _save_soc2(api: httpx.AsyncClient, **fields: object) -> None:
    soc2 = await _framework(api, "SOC2")
    body = {
        "name": "SOC 2 2027",
        "framework_version_id": soc2["version_id"],
        "audit_type": "type_1",
        "categories_in_scope": [],
        **fields,
    }
    response = await api.put("/engagement", json=body)
    assert response.status_code == 200, response.text


async def test_a_new_workspace_sees_its_soc2_steps_from_records(api: httpx.AsyncClient) -> None:
    body = await _status(api)
    assert [f["code"] for f in body["frameworks"]] == ["SOC2"]
    steps = _steps(body)

    assert steps["report:SOC2"]["state"] == "not_started"
    assert not any("ISO27001" in key for key in steps)
    owners = steps["owners"]
    assert owners["state"] == "not_started"
    assert owners["done_count"] == 0
    assert owners["total_count"] == body["frameworks"][0]["controls_total"] > 0
    assert owners["frameworks"] == ["SOC2"]
    assert "failing" not in steps, "no automated check has run, so nothing can be failing"
    assert steps["connect"]["state"] == "not_started"
    assert body["next_key"] == "profile"
    assert body["phases"] == [
        "describe",
        "organise",
        "assess",
        "build",
        "operate",
        "check",
        "audit",
    ]


async def test_security_alone_is_a_decision_and_a_type_2_period_shows_in_the_header(
    api: httpx.AsyncClient,
) -> None:
    await _save_soc2(api, audit_type="type_1", categories_in_scope=[])
    assert _steps(await _status(api))["report:SOC2"]["state"] == "done"

    await _save_soc2(
        api,
        audit_type="type_2",
        categories_in_scope=[],
        window_start="2027-02-01",
        window_end="2027-04-30",
    )
    body = await _status(api)
    assert _steps(body)["report:SOC2"]["state"] == "done"
    soc2 = body["frameworks"][0]
    assert (soc2["audit_type"], soc2["window_start"], soc2["window_end"]) == (
        "type_2",
        "2027-02-01",
        "2027-04-30",
    )


async def test_adding_iso_27001_adds_its_own_steps_and_shared_steps_count_for_both(
    api: httpx.AsyncClient,
) -> None:
    iso = await _framework(api, "ISO27001")
    added = await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    assert added.status_code == 201, added.text

    body = await _status(api)
    assert [f["code"] for f in body["frameworks"]] == ["SOC2", "ISO27001"]
    steps = _steps(body)
    assert steps["scope_statement:ISO27001"]["state"] == "not_started"
    applicability = steps["applicability:ISO27001"]
    assert applicability["done_count"] == 0
    assert applicability["total_count"] == body["frameworks"][1]["decisions_total"] > 0
    assert applicability["link"] == "/frameworks/soa?framework=ISO27001"
    assert steps["owners"]["frameworks"] == ["SOC2", "ISO27001"]
    assert steps["profile"]["frameworks"] == []


async def test_a_read_only_role_gets_the_page_and_not_an_error(
    app: FastAPI, workspace: Workspace
) -> None:
    invited = await invite_directly(
        workspace,
        email="ceo@onboarding.example",
        full_name="Read Only",
        role_name="Chief Executive Officer",
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Read Only", password=INVITEE_PASSWORD
    )
    async with client(app, tenant_session_headers(invited.member.membership_id)) as reader:
        body = await _status(reader)
        skip = await reader.post("/onboarding/steps/connect/skip", json={"reason": "Not mine"})

    assert body["frameworks"] is None
    steps = _steps(body)
    for key in ("owners", "invite", "evidence", "report", "risks", "connect"):
        assert steps[key]["state"] == "not_permitted", key
    assert steps["profile"]["state"] != "not_permitted"
    assert steps["profile"]["can_act"] is False
    assert skip.status_code == 403


async def test_a_skip_needs_a_reason_names_who_and_can_be_reopened(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    blank = await api.post("/onboarding/steps/connect/skip", json={"reason": "   "})
    assert blank.status_code in {400, 422}, blank.text
    unknown = await api.post("/onboarding/steps/nonsense/skip", json={"reason": "x"})
    assert unknown.status_code == 404

    skipped = await api.post(
        "/onboarding/steps/connect/skip", json={"reason": "No systems to connect yet."}
    )
    assert skipped.status_code == 204, skipped.text
    again = await api.post("/onboarding/steps/connect/skip", json={"reason": "Twice"})
    assert again.status_code == 409

    step = _steps(await _status(api))["connect"]
    assert step["state"] == "skipped"
    assert step["skip"]["reason"] == "No systems to connect yet."
    assert step["skip"]["by_name"] == "Founding Admin"

    reopened = await api.post("/onboarding/steps/connect/reopen")
    assert reopened.status_code == 204, reopened.text
    assert _steps(await _status(api))["connect"]["state"] == "not_started"
    assert (await api.post("/onboarding/steps/connect/reopen")).status_code == 404

    async with session_scope(workspace.tenant_id) as session:
        entries, _ = await audit_service.list_page(
            session, tenant_id=workspace.tenant_id, limit=10, object_type="onboarding_step"
        )
    assert sorted(e.action for e in entries) == ["create", "update"]


async def test_a_compliance_manager_runs_the_programme_but_not_the_workspace(
    app: FastAPI, workspace: Workspace
) -> None:
    """D-12: the built-in role acts on every programme step, never on people or the profile."""
    invited = await invite_directly(
        workspace,
        email="cm@onboarding.example",
        full_name="Compliance Lead",
        role_name="Compliance Manager",
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name="Compliance Lead", password=INVITEE_PASSWORD
    )
    async with client(app, tenant_session_headers(invited.member.membership_id)) as manager:
        body = await _status(manager)
        skip = await manager.post("/onboarding/steps/connect/skip", json={"reason": "Later"})
        profile = await manager.post("/tenant/profile/confirm")

    assert body["frameworks"] is not None
    steps = _steps(body)
    for key in ("report:SOC2", "owners", "risks", "connect", "evidence"):
        assert steps[key]["can_act"] is True, key
    for key in ("profile", "invite", "admin_mfa"):
        assert steps[key]["can_act"] is False, key
    assert skip.status_code == 204
    assert profile.status_code == 403


async def test_soc2_records_its_audit_firm_dates_and_keeps_them_when_a_form_omits_them(
    api: httpx.AsyncClient,
) -> None:
    """EN-2, EN-3: SOC 2 now carries the CPA firm, a Type 1 as of date and a target date, and a
    save that does not send them leaves them as stored."""
    await _save_soc2(api, audit_type="type_1")
    steps = _steps(await _status(api))
    assert steps["auditor:SOC2"]["state"] == "not_started"

    await _save_soc2(api, audit_type="type_1", assessor="undecided", target_date="2027-06-30")
    steps = _steps(await _status(api))
    assert (steps["auditor:SOC2"]["state"], steps["auditor:SOC2"]["detail"]) == (
        "in_progress",
        "Still deciding",
    )

    await _save_soc2(
        api,
        audit_type="type_1",
        as_of_date="2027-03-31",
        certification_body="Example CPA LLP",
        scope_statement="The payroll service and its production environment.",
    )
    # An older form that knows none of these fields saves again.
    await _save_soc2(api, audit_type="type_1", categories_in_scope=["availability"])
    engagement = (await api.get("/engagement")).json()
    assert engagement["certification_body"] == "Example CPA LLP"
    assert engagement["assessor"] == "chosen"
    assert engagement["as_of_date"] == "2027-03-31"
    assert engagement["target_date"] == "2027-06-30"
    assert engagement["scope_statement"].startswith("The payroll service")
    body = await _status(api)
    assert _steps(body)["auditor:SOC2"]["state"] == "done"
    assert body["frameworks"][0]["target_date"] == "2027-06-30"


async def test_dates_that_do_not_belong_to_the_audit_are_refused(api: httpx.AsyncClient) -> None:
    soc2 = await _framework(api, "SOC2")
    base = {"name": "SOC 2", "framework_version_id": soc2["version_id"], "categories_in_scope": []}
    as_of_on_type_2 = await api.put(
        "/engagement",
        json={
            **base,
            "audit_type": "type_2",
            "window_start": "2027-01-01",
            "window_end": "2027-03-31",
            "as_of_date": "2027-03-31",
        },
    )
    assert as_of_on_type_2.status_code == 422
    assert "Type 1" in as_of_on_type_2.json()["error"]["message"]
    live_on_soc2 = await api.put(
        "/engagement", json={**base, "audit_type": "type_1", "live_date": "2027-01-01"}
    )
    assert live_on_soc2.status_code == 422
