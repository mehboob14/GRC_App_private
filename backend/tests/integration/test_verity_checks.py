"""Verity's built-in checks through the real app and the real scheduler job.

The checks read data the workspace already keeps (assets, policies, the Statement of
Applicability) and judge it the way a connector judges an outside system: a result per
record, evidence filed on the mapped controls, and readiness that can only go down. The
built-in connection is always on: the hourly job creates it for every workspace, and it
cannot be switched off. A second workspace sees none of the first one's results.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.main import create_app
from verity.modules.iam.service import iam_service
from verity.modules.vulnerabilities.models import VulnInstance
from verity.workers import tasks as worker_tasks

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh() -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
async def workspaces(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> tuple[Workspace, Workspace]:
    home = await signup_workspace(company="Built In Ltd", email="built@in.example")
    other = await signup_workspace(company="Elsewhere Ltd", email="else@where.example")
    return home, other


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


def _client(app: FastAPI, workspace: Workspace) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test/api/v1",
        headers={"Authorization": f"Bearer {workspace.session_token}"},
    )


async def _control(api: httpx.AsyncClient, code: str) -> str:
    controls = (await api.get("/controls")).json()
    return str(next(c["id"] for c in controls if c["code"] == code))


async def _test(api: httpx.AsyncClient, code: str, key: str) -> dict[str, Any]:
    automation = (await api.get(f"/controls/{await _control(api, code)}/automation")).json()
    return next(t for t in automation["tests"] if t["key"] == key)


def _outcomes(test: dict[str, Any]) -> dict[str, str]:
    return {r["resource_name"]: r["outcome"] for r in test["results"]}


async def test_the_scheduler_turns_the_checks_on_and_they_judge_the_workspace(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        unowned = (await api.post("/assets", json={"name": "db-1", "asset_type": "data"})).json()
        owned = await api.post(
            "/assets",
            json={
                "name": "web-1",
                "data_classification": "internal",
                "primary_owner_membership_id": str(home.membership_id),
            },
        )
        assert owned.status_code == 201, owned.text
        # A new asset is planned; the checks judge assets in service.
        for asset in (unowned, owned.json()):
            moved = await api.post(
                f"/assets/{asset['id']}/transition", json={"to_status": "active"}
            )
            assert moved.status_code == 200, moved.text

        # The hourly job: every workspace gets its built-in connection and a first run.
        summary = await worker_tasks._run_connector_checks()
        assert summary["runs"] == 2

        connections = (await api.get("/connections")).json()
        assert [c["provider"] for c in connections] == ["verity"]
        built_in = connections[0]
        assert built_in["latest_run"]["status"] == "completed", built_in["latest_run"]
        assert built_in["credential_hint"] is None

        owner_test = await _test(api, "LM-01", "verity.assets.owner_assigned")
        assert _outcomes(owner_test) == {"db-1": "fail", "web-1": "pass"}
        classified = await _test(api, "DM-04", "verity.assets.classified")
        assert _outcomes(classified) == {"db-1": "fail", "web-1": "pass"}

        # Nothing exists yet that a policy check could count: that is a failure, said once.
        policies = await _test(api, "GOV-17", "verity.policies.reviewed")
        assert [(r["outcome"], r["detail"]["reason"]) for r in policies["results"]] == [
            ("fail", "no_policies")
        ]

        # The run files its findings as evidence on the controls each check serves.
        lm01 = await _control(api, "LM-01")
        evidence = (await api.get("/evidence", params={"control_id": lm01})).json()
        filed = [e for e in evidence if e["source_label"] == "Verity built in checks"]
        assert filed, evidence
        assert all(": Verity check, " in e["title"] for e in filed)
        # Those reports are not evidence the control rests on: the controls report counts
        # what people and other systems filed, as the dashboard does.
        report = (await api.get("/controls/report")).json()
        row = next(r for r in report["rows"] if r["code"] == "LM-01")
        assert row["evidence_count"] == 0, row

        # Idempotent: a second ensure keeps the one connection, and nothing is due again yet.
        again = await api.post("/connections/built-in")
        assert again.status_code == 200, again.text
        assert again.json()["id"] == built_in["id"]
        assert (await worker_tasks._run_connector_checks())["runs"] == 0

        # Always on: it cannot be switched off, and the token path never takes it.
        off = await api.post(
            f"/connections/{built_in['id']}/disconnect", json={"reason": "too many failures"}
        )
        assert off.status_code == 409
        assert (
            await api.post("/connections", json={"provider": "verity", "token": "x"})
        ).status_code == 422

        # The other workspace has its own connection and cannot reach this one.
        theirs = (await outsider.get("/connections")).json()
        assert [c["id"] for c in theirs] != [built_in["id"]]
        assert (await outsider.post(f"/connections/{built_in['id']}/runs")).status_code == 404
        their_owner_test = await _test(outsider, "LM-01", "verity.assets.owner_assigned")
        assert their_owner_test["results"] == []

        # Fix the gap and run again: the asset now passes.
        fixed = await api.patch(
            f"/assets/{unowned['id']}",
            json={
                "name": "db-1",
                "asset_type": "data",
                "data_classification": "confidential",
                "primary_owner_membership_id": str(home.membership_id),
            },
        )
        assert fixed.status_code == 200, fixed.text
        assert (await api.post(f"/connections/{built_in['id']}/runs")).status_code == 202
        owner_test = await _test(api, "LM-01", "verity.assets.owner_assigned")
        assert _outcomes(owner_test) == {"db-1": "pass", "web-1": "pass"}


async def test_iso_checks_follow_the_statement_of_applicability(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _other = workspaces
    async with _client(app, home) as api:
        iso = next(
            r for r in (await api.get("/tenant-frameworks")).json() if r["code"] == "ISO27001"
        )
        assert (
            await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
        ).status_code in (
            200,
            201,
        )
        built_in = (await api.post("/connections/built-in")).json()
        assert (await api.post(f"/connections/{built_in['id']}/runs")).status_code == 202

        soa = await _test(api, "GOV-27", "verity.soa.complete")
        assert len(soa["results"]) == 93  # every Annex A requirement, never the clauses
        assert {r["outcome"] for r in soa["results"]} == {"fail"}
        scope = await _test(api, "GOV-23", "verity.isms.scope_recorded")
        assert [r["detail"]["reason"] for r in scope["results"]] == ["no_engagement"]

        # Decide and review one requirement with its reason: that row passes on the next run.
        rows = (await api.get(f"/frameworks/{iso['framework_id']}/applicability")).json()["rows"]
        target = next(r for r in rows if r["code"] == "A.5.1")
        decided = await api.put(
            f"/frameworks/{iso['framework_id']}/applicability/{target['requirement_id']}",
            json={
                "applicable": True,
                "justification": "Our policy set is the basis of every other control.",
                "provided_by": "organization",
                "owner_membership_id": str(home.membership_id),
                "reviewed": True,
            },
        )
        assert decided.status_code == 200, decided.text
        assert (await api.post(f"/connections/{built_in['id']}/runs")).status_code == 202
        soa = await _test(api, "GOV-27", "verity.soa.complete")
        passed = [r["resource_name"] for r in soa["results"] if r["outcome"] == "pass"]
        assert len(passed) == 1
        assert passed[0].startswith("A.5.1 ")


async def test_a_raised_severity_shortens_the_clock_from_the_current_detection(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _other = workspaces
    async with _client(app, home) as api:
        asset = await api.post(
            "/assets/import",
            json={"rows": [{"name": "Payments API", "asset_type": "infrastructure"}]},
        )
        assert asset.status_code == 200, asset.text

        async def scan(severity: str) -> None:
            csv = f"title,severity,asset\nOld bug,{severity},Payments API\n"
            r = await api.post(
                "/vulnerabilities/import",
                files={"file": ("scan.csv", csv.encode())},
                data={"report_name": "Scan"},
            )
            assert r.status_code == 201, r.text

        await scan("medium")
        [row] = (await api.get("/vulnerabilities")).json()
        # An earlier episode: first seen long ago, then fixed.
        async with session_scope(home.tenant_id) as session:
            inst = await session.get(VulnInstance, uuid.UUID(row["id"]))
            assert inst is not None
            inst.first_detected_at = datetime.now(UTC) - timedelta(days=400)
            inst.state = "fixed"
        await scan("medium")  # it came back: the clock restarts now
        await scan("critical")  # and is now critical: the clock shortens from the return
        [row] = (await api.get("/vulnerabilities")).json()
        days = {p["severity"]: p["days"] for p in (await api.get("/vulnerabilities/sla")).json()}
        due = datetime.fromisoformat(row["sla_due_at"])
        now = datetime.now(UTC)
        assert now < due <= now + timedelta(days=days["critical"])


async def test_a_time_boxed_guest_auditor_is_not_staff(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _other = workspaces
    async with _client(app, home) as api:
        roles = (await api.get("/roles")).json()
        role_id = next(r["id"] for r in roles if r["name"] == "Security Officer")
        invited = await api.post(
            "/members/invite",
            json={
                "email": "guest@auditors.example",
                "full_name": "Guest Auditor",
                "role_id": role_id,
                "valid_until": (datetime.now(UTC).date() + timedelta(days=60)).isoformat(),
            },
        )
        assert invited.status_code == 201, invited.text
        guest = uuid.UUID(invited.json()["member"]["membership_id"])
    async with session_scope(home.tenant_id) as session:
        guests = await iam_service.guest_membership_ids(session, tenant_id=home.tenant_id)
    assert guest in guests
    assert home.membership_id not in guests
