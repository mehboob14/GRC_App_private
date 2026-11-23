"""Assurance records, findings raised as tasks, the description inputs, and documents approved
outside Verity (guided onboarding phase 7)."""

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
    return await signup_workspace(company="Audit Ltd", email="founder@audit.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _iso(api: httpx.AsyncClient) -> None:
    iso = next(f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == "ISO27001")
    assert (
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
    ).status_code == 201
    iso = next(f for f in (await api.get("/tenant-frameworks")).json() if f["code"] == "ISO27001")
    saved = await api.put(
        "/engagement",
        json={
            "name": "ISO 27001",
            "framework_version_id": iso["version_id"],
            "audit_type": "initial_certification",
            "categories_in_scope": [],
            "scope_statement": "The platform.",
        },
    )
    assert saved.status_code == 200, saved.text


async def _step(api: httpx.AsyncClient, key: str) -> dict[str, Any]:
    steps = (await api.get("/onboarding/status")).json()["steps"]
    return next(s for s in steps if s["key"] == key)


async def test_internal_audit_with_findings_and_report(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    await _iso(api)
    q = {"framework": "ISO27001"}
    assert (await api.get("/engagement/assurance", params=q)).json()["records"] == []
    me = str(workspace.membership_id)
    both = await api.post(
        "/engagement/assurance",
        params=q,
        json={"kind": "internal_audit", "performed_by_membership_id": me, "performed_by_name": "X"},
    )
    assert both.status_code == 422
    made = await api.post(
        "/engagement/assurance",
        params=q,
        json={
            "kind": "internal_audit",
            "starts_on": str(datetime.now(UTC).date()),
            "performed_by_name": "Sam Lee",
            "performed_by_firm": "Independent Audits Ltd",
            "independence_confirmed_by_membership_id": me,
            "status": "held",
        },
    )
    assert made.status_code == 201, made.text
    record = made.json()
    assert record["label"] == "Internal audit"
    assert (await _step(api, "internal_audit:ISO27001"))["state"] != "done"

    due = str(datetime.now(UTC).date() - timedelta(days=1))
    minor = await api.post(
        f"/engagement/assurance/{record['id']}/findings",
        json={"grade": "minor", "summary": "Access review not signed", "due_on": due},
    )
    assert minor.status_code == 201, minor.text
    assert minor.json()["task_id"] is not None
    assert minor.json()["overdue"] is True
    note = await api.post(
        f"/engagement/assurance/{record['id']}/findings",
        json={"grade": "observation", "summary": "Consider a second reviewer"},
    )
    finding = note.json()

    no_evidence = await api.put(
        f"/engagement/assurance/findings/{minor.json()['id']}",
        json={"closed_on": str(datetime.now(UTC).date())},
    )
    assert no_evidence.status_code == 422
    early = await api.put(
        f"/engagement/assurance/findings/{finding['id']}",
        json={"verified_on": str(datetime.now(UTC).date())},
    )
    assert early.status_code == 422, "verify needs a closed finding"
    closed = await api.put(
        f"/engagement/assurance/findings/{finding['id']}",
        json={"closed_on": str(datetime.now(UTC).date()), "response": "Added"},
    )
    assert closed.status_code == 200, closed.text
    close_step = await _step(api, "close_findings")
    assert close_step["state"] != "done", "one finding is past due"

    doc = await api.post(
        "/documents/from-template", json={"template_key": "internal-audit-procedure"}
    )
    assert doc.status_code == 201, doc.text
    attached = await api.put(
        f"/engagement/assurance/{record['id']}",
        params=q,
        json={"kind": "internal_audit", "document_id": doc.json()["id"], "status": "held"},
    )
    assert attached.status_code == 200, attached.text
    assert (await _step(api, "internal_audit:ISO27001"))["state"] == "done"


async def test_description_inputs_and_approved_elsewhere(api: httpx.AsyncClient) -> None:
    areas = (await api.get("/engagement/description-inputs")).json()
    assert len(areas) == 9
    assert {a["key"] for a in areas} >= {"commitments", "subservice", "changes"}

    doc = await api.post("/documents", json={"title": "Our access policy", "doc_type": "policy"})
    if doc.status_code != 201:
        doc = await api.post(
            "/documents/from-template", json={"template_key": "access-control-policy"}
        )
    assert doc.status_code == 201, doc.text
    doc_id = doc.json()["id"]
    future = await api.post(
        f"/documents/{doc_id}/approved-elsewhere",
        json={"approved_on": str(datetime.now(UTC).date() + timedelta(days=3))},
    )
    assert future.status_code == 422
    ok = await api.post(
        f"/documents/{doc_id}/approved-elsewhere",
        json={"approved_on": "2025-06-30", "template_key": "access-control-policy"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["lifecycle"] == "approved"
    assert ok.json()["approved_elsewhere_on"] == "2025-06-30"
    assert ok.json()["approved_elsewhere_by_name"]
    again = await api.post(
        f"/documents/{doc_id}/approved-elsewhere", json={"approved_on": "2025-06-30"}
    )
    assert again.status_code == 409
    rows = (await api.get("/onboarding/required-documents")).json()["rows"]
    access = next(r for r in rows if r["template"] == "access-control-policy")
    assert access["state"] == "approved"
