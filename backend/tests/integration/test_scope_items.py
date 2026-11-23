"""Shared scope items, in or out decided per framework (guided onboarding SC-0, SC-2, D-6)."""

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
from verity.modules.audit.service import audit_service
from verity.modules.compliance.scope_service import NOTICE_CERTIFICATION, NOTICE_PERIOD

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
    return await signup_workspace(company="Scope Ltd", email="founder@scope.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _framework(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    found: dict[str, Any] = next(
        f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == code
    )
    return found


async def _soc2_type_2_running(api: httpx.AsyncClient) -> None:
    today = datetime.now(UTC).date()
    soc2 = await _framework(api, "SOC2")
    response = await api.put(
        "/engagement",
        json={
            "name": "SOC 2",
            "framework_version_id": soc2["version_id"],
            "audit_type": "type_2",
            "categories_in_scope": [],
            "window_start": str(today - timedelta(days=10)),
            "window_end": str(today + timedelta(days=80)),
        },
    )
    assert response.status_code == 200, response.text


async def _iso_with_body(api: httpx.AsyncClient) -> None:
    iso = await _framework(api, "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    iso = await _framework(api, "ISO27001")
    response = await api.put(
        "/engagement",
        json={
            "name": "ISO 27001",
            "framework_version_id": iso["version_id"],
            "audit_type": "initial_certification",
            "categories_in_scope": [],
            "scope_statement": "The platform and the team that runs it.",
            "certification_body": "Example Certification Ltd",
        },
    )
    assert response.status_code == 200, response.text


async def _item(api: httpx.AsyncClient, kind: str, name: str) -> str:
    response = await api.post("/engagement/scope-items", json={"kind": kind, "name": name})
    assert response.status_code == 201, response.text
    item_id: str = response.json()["id"]
    return item_id


async def _decide(
    api: httpx.AsyncClient,
    item_id: str,
    framework: str,
    *,
    in_scope: bool,
    reason: str | None = None,
) -> httpx.Response:
    return await api.put(
        f"/engagement/scope-items/{item_id}/decision",
        params={"framework": framework},
        json={"in_scope": in_scope, "reason": reason},
    )


async def _listed(api: httpx.AsyncClient, framework: str) -> dict[str, dict[str, Any]]:
    response = await api.get("/engagement/scope-items", params={"framework": framework})
    assert response.status_code == 200, response.text
    return {item["name"]: item for item in response.json()}


async def test_one_item_two_decisions_that_never_share_a_flag(api: httpx.AsyncClient) -> None:
    await _soc2_type_2_running(api)
    await _iso_with_body(api)
    staging = await _item(api, "environment", "Staging environment")

    refused = await _decide(api, staging, "SOC2", in_scope=False)
    assert refused.status_code == 422
    assert "Say why" in refused.json()["error"]["message"]

    assert (
        await _decide(api, staging, "SOC2", in_scope=False, reason="Holds no customer data.")
    ).status_code == 200
    assert (await _decide(api, staging, "ISO27001", in_scope=True)).status_code == 200

    soc2 = (await _listed(api, "SOC2"))["Staging environment"]
    assert (soc2["in_scope"], soc2["reason"]) == (False, "Holds no customer data.")
    assert soc2["others"] == [{"framework_code": "ISO27001", "in_scope": True}]
    iso = (await _listed(api, "ISO27001"))["Staging environment"]
    assert iso["in_scope"] is True
    assert iso["others"] == [{"framework_code": "SOC2", "in_scope": False}]


async def test_a_change_says_what_each_framework_must_do(api: httpx.AsyncClient) -> None:
    await _soc2_type_2_running(api)
    await _iso_with_body(api)
    payroll = await _item(api, "system", "Payroll database")
    first = await _decide(api, payroll, "SOC2", in_scope=True)
    assert first.json()["notices"] == [], "a first decision is not a change"
    await _decide(api, payroll, "ISO27001", in_scope=True)

    soc2_change = await _decide(api, payroll, "SOC2", in_scope=False, reason="Moved to a vendor.")
    assert soc2_change.json()["notices"] == [NOTICE_PERIOD]
    iso_change = await _decide(
        api, payroll, "ISO27001", in_scope=False, reason="Moved to a vendor."
    )
    assert iso_change.json()["notices"] == [NOTICE_CERTIFICATION]


async def test_retiring_an_item_keeps_it_and_lists_what_to_do(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    await _soc2_type_2_running(api)
    await _iso_with_body(api)
    office = await _item(api, "site", "London office")
    await _decide(api, office, "SOC2", in_scope=True)
    await _decide(api, office, "ISO27001", in_scope=True)

    retired = await api.post(
        f"/engagement/scope-items/{office}/retire", json={"reason": "Office closed."}
    )
    assert retired.status_code == 200, retired.text
    assert set(retired.json()["notices"]) == {NOTICE_PERIOD, NOTICE_CERTIFICATION}
    assert "London office" not in await _listed(api, "SOC2")
    again = await _decide(api, office, "SOC2", in_scope=True)
    assert again.status_code == 404

    async with session_scope(workspace.tenant_id) as session:
        items, _ = await audit_service.list_page(
            session, tenant_id=workspace.tenant_id, limit=20, object_type="scope_item"
        )
        decisions, _ = await audit_service.list_page(
            session, tenant_id=workspace.tenant_id, limit=20, object_type="scope_decision"
        )
    assert sorted(e.action for e in items) == ["create", "update"]
    assert len(decisions) == 2


async def test_no_decision_before_the_framework_has_an_audit(api: httpx.AsyncClient) -> None:
    item = await _item(api, "service", "Hosted payroll")
    response = await _decide(api, item, "SOC2", in_scope=True)
    assert response.status_code == 409
    assert "Set up this framework's audit first" in response.json()["error"]["message"]
