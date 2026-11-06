"""A second framework beside SOC 2, through the real app (rules 1, 2, 5, 6).

One control library. Adding ISO 27001 adopts only the controls it needs and links the ones the
workspace already runs, in one audited step, and SOC 2 keeps answering exactly as it did. The
scope of a framework that works by applicability is a Statement of Applicability: everything is
in unless it is excluded with a reason, and the management system clauses cannot be excluded.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from openpyxl import load_workbook

import verity
from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]

_PACK = Path(verity.__file__).parent / "seed" / "content" / "iso27001"
NEW_CONTROLS = 17
ISO_REQUIREMENTS = 123
ISO_LINKS = len(json.loads((_PACK / "template_requirements.json").read_text(encoding="utf-8")))


@pytest.fixture
async def workspaces(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> tuple[Workspace, Workspace]:
    home = await signup_workspace(company="Two Frameworks Ltd", email="two@example.test")
    other = await signup_workspace(company="Soc Only Ltd", email="soc@example.test")
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


async def _framework(api: httpx.AsyncClient, code: str) -> dict[str, Any]:
    rows = (await api.get("/tenant-frameworks")).json()
    return next(r for r in rows if r["code"] == code)


async def _engage_soc2(api: httpx.AsyncClient) -> None:
    soc2 = await _framework(api, "SOC2")
    put = await api.put(
        "/engagement",
        json={
            "name": "SOC 2 Type II",
            "framework_version_id": soc2["version_id"],
            "audit_type": "type_2",
            "categories_in_scope": ["Availability"],
            "window_start": "2026-01-01",
            "window_end": "2026-12-31",
        },
    )
    assert put.status_code == 200, put.text


def _soc2_numbers(dashboard: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "criteria_total",
        "criteria_covered",
        "controls_total",
        "controls_ready",
        "controls_unmapped",
        "controls_evidenced",
    )
    return {k: dashboard[k] for k in keys} | {"by_category": dashboard["by_category"]}


async def test_a_workspace_starts_on_soc2_alone_and_a_loaded_pack_adds_nothing_to_it(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        frameworks = (await api.get("/tenant-frameworks")).json()
        assert [f["code"] for f in frameworks][:2] == ["SOC2", "ISO27001"]
        added = {f["code"]: f["added"] for f in frameworks}
        assert added["SOC2"] is True
        assert added["ISO27001"] is False

        controls = (await api.get("/controls")).json()
        codes = {c["code"] for c in controls}
        # Signup adopts the library of the frameworks the workspace runs, not every pack.
        assert len(controls) == 116
        assert {"GOV-23", "GOV-27", "LM-12"}.isdisjoint(codes)
        assert all(k.startswith("SOC2:") for c in controls for k in c["requirement_keys"])


async def test_the_overlap_preview_counts_what_the_workspace_already_runs(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        iso = await _framework(api, "ISO27001")
        preview = (await api.get(f"/frameworks/{iso['framework_id']}/overlap")).json()
        assert preview["requirements_total"] == ISO_REQUIREMENTS
        assert preview["added"] is False
        parts = ("covered", "partly", "needs_new", "no_control")
        assert sum(preview[p] for p in parts) == ISO_REQUIREMENTS
        assert preview["no_control"] == 0
        assert preview["covered"] + preview["partly"] > 100
        assert preview["needs_new"] <= NEW_CONTROLS
        assert len(preview["controls_to_adopt"]) == NEW_CONTROLS
        assert preview["controls_in_use"] > 80
        assert sum(g["total"] for g in preview["groups"]) == ISO_REQUIREMENTS


async def test_adding_iso_links_what_is_running_adopts_what_is_new_and_leaves_soc2_alone(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        await _engage_soc2(api)
        before = (await api.get("/engagement/dashboard")).json()
        controls_before = {c["code"]: c for c in (await api.get("/controls")).json()}
        assert "ISO27001:A.8.32" not in controls_before["SD-01"]["requirement_keys"]

        iso = await _framework(api, "ISO27001")
        added = await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
        assert added.status_code == 201, added.text
        body = added.json()
        assert body["framework"]["added"] is True
        assert body["controls_adopted"] == NEW_CONTROLS
        assert body["links_created"] == ISO_LINKS

        controls = {c["code"]: c for c in (await api.get("/controls")).json()}
        assert len(controls) == 116 + NEW_CONTROLS
        # One control, two frameworks: the control already running now answers both.
        assert {"SOC2:CC8.1", "ISO27001:A.8.32"} <= set(controls["SD-01"]["requirement_keys"])
        assert any(k.startswith("ISO27001:") for k in controls["GOV-27"]["requirement_keys"])
        assert not any(k.startswith("SOC2:") for k in controls["GOV-27"]["requirement_keys"])

        # SOC 2 answers as it did: the ISO-only controls are not part of its numbers.
        after = (await api.get("/engagement/dashboard")).json()
        assert _soc2_numbers(after) == _soc2_numbers(before)
        assert after["framework_code"] == "SOC2"

        # Adding twice changes nothing.
        again = await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})
        assert again.status_code == 201
        assert again.json()["controls_adopted"] == 0
        assert len((await api.get("/controls")).json()) == 116 + NEW_CONTROLS

        # Another workspace is untouched (rules 1 and 2).
        theirs = (await outsider.get("/controls")).json()
        assert len(theirs) == 116
        assert (await _framework(outsider, "ISO27001"))["added"] is False
        refused = await outsider.get(f"/frameworks/{iso['framework_id']}/applicability")
        assert refused.status_code == 409


async def test_iso_has_its_own_dashboard_coverage_and_audit_beside_soc2(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        await _engage_soc2(api)
        iso = await _framework(api, "ISO27001")
        empty = (await api.get("/engagement/dashboard", params={"framework": "ISO27001"})).json()
        assert empty["has_engagement"] is False
        await api.post("/tenant-frameworks", json={"framework_id": iso["framework_id"]})

        dashboard = (
            await api.get("/engagement/dashboard", params={"framework": "ISO27001"})
        ).json()
        assert dashboard["has_engagement"] is True
        assert dashboard["scope_model"] == "applicability"
        assert dashboard["criteria_total"] == ISO_REQUIREMENTS
        assert dashboard["criteria_uncovered"] == 0
        assert dashboard["controls_shared"] > 60
        groups = [g["category"] for g in dashboard["by_category"]]
        assert groups[0].startswith("Clause 4")
        assert groups[-1].startswith("Annex A Technological")

        coverage = (await api.get("/engagement/coverage", params={"framework": "ISO27001"})).json()
        assert coverage["criteria_total"] == ISO_REQUIREMENTS

        # The audit: one per framework, each with its own kinds of audit.
        wrong = await api.put(
            "/engagement",
            json={
                "name": "ISO",
                "framework_version_id": iso["version_id"],
                "audit_type": "type_2",
                "categories_in_scope": [],
            },
        )
        assert wrong.status_code == 422
        saved = await api.put(
            "/engagement",
            json={
                "name": "ISO 27001 certification 2026",
                "framework_version_id": iso["version_id"],
                "audit_type": "initial_certification",
                "categories_in_scope": [],
                "scope_statement": "The hosted product and the team that runs it.",
                "certification_body": "Example Certification Ltd",
                "audit_on": "2026-11-30",
                "status": "active",
            },
        )
        assert saved.status_code == 200, saved.text
        iso_audit = (await api.get("/engagement", params={"framework": "ISO27001"})).json()
        assert iso_audit["scope_statement"].startswith("The hosted product")
        soc2_audit = (await api.get("/engagement")).json()
        assert soc2_audit["audit_type"] == "type_2"
        assert soc2_audit["scope_statement"] is None


async def test_the_statement_of_applicability_decides_scope_with_reasons(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        iso = await _framework(api, "ISO27001")
        fid = iso["framework_id"]
        await api.post("/tenant-frameworks", json={"framework_id": fid})

        statement = (await api.get(f"/frameworks/{fid}/applicability")).json()
        rows = {r["code"]: r for r in statement["rows"]}
        assert statement["summary"]["total"] == ISO_REQUIREMENTS
        assert statement["summary"]["excluded"] == 0
        assert [r["code"] for r in statement["rows"]][:3] == ["4.1", "4.2", "4.3"]
        assert rows["4.3"]["locked"] is True
        assert rows["A.7.6"]["locked"] is False
        assert rows["A.8.32"]["controls"], "A.8.32 is answered by controls the workspace runs"

        # A clause cannot be excluded, and an exclusion needs its reason.
        clause = await api.put(
            f"/frameworks/{fid}/applicability/{rows['4.3']['requirement_id']}",
            json={"applicable": False, "justification": "We would rather not."},
        )
        assert clause.status_code == 422
        bare = await api.put(
            f"/frameworks/{fid}/applicability/{rows['A.7.6']['requirement_id']}",
            json={"applicable": False, "justification": "   "},
        )
        assert bare.status_code == 422

        excluded = await api.put(
            f"/frameworks/{fid}/applicability/{rows['A.7.6']['requirement_id']}",
            json={
                "applicable": False,
                "justification": "Fully remote team, no secure areas.",
                "reviewed": True,
            },
        )
        assert excluded.status_code == 200, excluded.text
        assert excluded.json()["state"] == "excluded"
        assert excluded.json()["reviewed_at"] is not None

        inherited = await api.put(
            f"/frameworks/{fid}/applicability/{rows['A.7.1']['requirement_id']}",
            json={"applicable": True, "provided_by": "supplier", "justification": "Hosted."},
        )
        assert inherited.json()["provided_by"] == "supplier"

        # Exclusion is per requirement: it leaves in scope what it should and takes out one row.
        dashboard = (
            await api.get("/engagement/dashboard", params={"framework": "ISO27001"})
        ).json()
        assert dashboard["criteria_total"] == ISO_REQUIREMENTS - 1
        controls = {c["code"]: c for c in (await api.get("/controls")).json()}
        assert controls["PE-02"]["disabled_at"] is None

        summary = (await api.get(f"/frameworks/{fid}/applicability")).json()["summary"]
        assert (summary["excluded"], summary["applicable"]) == (1, ISO_REQUIREMENTS - 1)

        # The statement leaves as a workbook.
        export = await api.get(f"/frameworks/{fid}/soa.xlsx")
        assert export.status_code == 200
        assert "spreadsheetml" in export.headers["content-type"]
        assert "statement-of-applicability-iso27001" in export.headers["content-disposition"]
        sheet = load_workbook(io.BytesIO(export.content)).active
        assert sheet is not None
        references = [sheet.cell(row=r, column=1).value for r in range(6, sheet.max_row + 1)]
        assert len(references) == ISO_REQUIREMENTS
        assert references[0] == "4.1"
        excluded_row = references.index("A.7.6") + 6
        assert sheet.cell(row=excluded_row, column=4).value == "No"
        assert "remote" in sheet.cell(row=excluded_row, column=5).value


async def test_soc2_has_no_statement_of_applicability(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _ = workspaces
    async with _client(app, home) as api:
        soc2 = await _framework(api, "SOC2")
        refused = await api.get(f"/frameworks/{soc2['framework_id']}/applicability")
        assert refused.status_code == 422
