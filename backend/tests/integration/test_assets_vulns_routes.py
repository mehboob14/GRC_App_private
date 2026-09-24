"""Assets and vulnerabilities through the real app: real token, permissions and RLS.

Shallow and wide, like ``test_vendor_routes``: every read route answers from its
own handler, the Week 6 review path runs end to end (an asset rated for CIA,
JSON and Excel import, a scanner CSV prioritised against the asset, an SLA and
an exception), and a second workspace can neither see nor touch any of it.
"""

from __future__ import annotations

import io

import httpx
import openpyxl
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]

READ_ROUTES = (
    "/assets",
    "/assets/summary",
    "/assets/facets",
    "/vulnerabilities",
    "/vulnerabilities/kpis",
    "/vulnerabilities/sla",
    "/vulnerabilities/throughput",
    "/vulnerabilities/reports",
)


@pytest.fixture
async def workspaces(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> tuple[Workspace, Workspace]:
    home = await signup_workspace(company="Estate Ltd", email="estate@example.test")
    other = await signup_workspace(company="Other Ltd", email="other@example.test")
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


def _workbook(*rows: list[object]) -> bytes:
    book = openpyxl.Workbook()
    sheet = book.active
    assert sheet is not None
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


async def test_week6_review_path_and_tenant_wall(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        for path in READ_ROUTES:
            response = await api.get(path)
            assert response.status_code == 200, (path, response.text)

        # An asset rated for confidentiality, integrity and availability gets a tier.
        created = await api.post(
            "/assets",
            json={
                "name": "Payments API",
                "hostname": "pay.internal",
                "internet_facing": True,
                "confidentiality": 5,
                "integrity": 5,
                "availability": 4,
            },
        )
        assert created.status_code == 201, created.text
        asset = created.json()
        assert asset["criticality"]["tier"] is not None

        imported = await api.post(
            "/assets/import",
            json={
                "rows": [
                    {"name": "Build server", "asset_type": "infrastructure", "status": "planned"}
                ]
            },
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["created"] == 1
        items = (await api.get("/assets")).json()["items"]
        assert next(a["status"] for a in items if a["name"] == "Build server") == "planned"
        retired = await api.post(
            "/assets/import", json={"rows": [{"name": "Old box", "status": "retired"}]}
        )
        assert retired.status_code == 422, "retiring goes through the decommission flow"
        # A value outside the table's allowed list is refused up front, never a 500.
        bad_type = await api.post(
            "/assets/import", json={"rows": [{"name": "X", "asset_type": "server"}]}
        )
        assert bad_type.status_code == 422, bad_type.text

        # Excel comes back as the same text grid the browser builds from a CSV.
        sheet = await api.post(
            "/assets/import/sheet",
            files={
                "file": (
                    "assets.xlsx",
                    _workbook(
                        ["name", "internet_facing", "confidentiality"], ["Laptops", True, 3.0]
                    ),
                )
            },
        )
        assert sheet.status_code == 200, sheet.text
        assert sheet.json()["rows"] == [
            ["name", "internet_facing", "confidentiality"],
            ["Laptops", "true", "3"],
        ]
        garbage = await api.post(
            "/assets/import/sheet", files={"file": ("assets.xlsx", b"not a workbook")}
        )
        assert garbage.status_code == 422
        assert garbage.json()["error"]["code"] == "invalid_input"

        # A scanner export matched to the asset by name, prioritised critical first.
        csv = (
            "title,severity,asset,cvss_score\n"
            "Weak TLS,medium,Payments API,5.3\n"
            "Open admin panel,critical,Payments API,9.8\n"
        )
        scan = await api.post(
            "/vulnerabilities/import",
            files={"file": ("scan.csv", csv.encode())},
            data={"report_name": "Nightly scan"},
        )
        assert scan.status_code == 201, scan.text
        assert (scan.json()["created"], scan.json()["unmatched"]) == (2, 0)

        register = (await api.get("/vulnerabilities")).json()
        assert [row["title"] for row in register] == ["Open admin panel", "Weak TLS"]
        assert {row["asset_id"] for row in register} == {asset["id"]}
        assert all(row["sla_due_at"] for row in register)
        finding = register[0]

        sla = await api.put("/vulnerabilities/sla", json={"severity": "critical", "days": 3})
        assert sla.status_code == 200, sla.text
        assert any(p["severity"] == "critical" and p["days"] == 3 for p in sla.json())

        exception = await api.post(
            f"/vulnerabilities/{finding['id']}/exception",
            json={
                "duration_days": 30,
                "rationale": "Vendor patch lands next sprint.",
                "potential_risks": "Admin panel reachable from the VPN.",
            },
        )
        assert exception.status_code < 300, exception.text

        # The other workspace sees none of it and cannot reach it by id.
        assert (await outsider.get("/assets")).json()["total"] == 0
        assert (await outsider.get("/vulnerabilities")).json() == []
        assert (await outsider.get(f"/assets/{asset['id']}")).status_code == 404
        assert (await outsider.get(f"/vulnerabilities/{finding['id']}")).status_code == 404


async def test_a_declared_dependency_reads_from_both_ends(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    """One row, two sentences. Storing the inverse separately would let the two
    disagree, and disagreeing edges are worse than none when the question is what
    else goes down with this."""
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        api_asset = (await api.post("/assets", json={"name": "Payments API"})).json()
        cluster = (
            await api.post("/assets", json={"name": "Prod cluster", "asset_type": "infrastructure"})
        ).json()

        declared = await api.post(
            f"/assets/{api_asset['id']}/relationships",
            json={"other_asset_id": cluster["id"], "type": "runs_on", "direction": "outbound"},
        )
        assert declared.status_code == 201, declared.text
        edge = declared.json()["items"][0]
        assert (edge["direction"], edge["type"], edge["other_asset_name"]) == (
            "outbound",
            "runs_on",
            "Prod cluster",
        )

        # The other end reads the same row the other way round, on its detail.
        detail = (await api.get(f"/assets/{cluster['id']}")).json()
        assert [(r["direction"], r["other_asset_name"]) for r in detail["relationships"]] == [
            ("inbound", "Payments API")
        ]

        # Declared twice is one edge; an asset cannot depend on itself.
        again = await api.post(
            f"/assets/{api_asset['id']}/relationships",
            json={"other_asset_id": cluster["id"], "type": "runs_on", "direction": "outbound"},
        )
        assert again.status_code == 409, again.text
        itself = await api.post(
            f"/assets/{api_asset['id']}/relationships",
            json={"other_asset_id": api_asset["id"], "type": "depends_on"},
        )
        assert itself.status_code == 422, itself.text

        # Another tenant can neither see it nor reach it.
        assert (await outsider.get(f"/assets/{cluster['id']}/relationships")).status_code == 404
        assert (
            await outsider.delete(f"/assets/{cluster['id']}/relationships/{edge['id']}")
        ).status_code == 404

        # Either end may withdraw it, and it goes from both.
        removed = await api.delete(f"/assets/{cluster['id']}/relationships/{edge['id']}")
        assert removed.status_code == 200, removed.text
        assert removed.json()["items"] == []
        assert (await api.get(f"/assets/{api_asset['id']}")).json()["relationships"] == []


async def test_a_workspace_defines_its_own_fields_and_its_own_review_cadence(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    """The two halves of the inventory settings screen: extra fields a workspace
    collects, and how long each criticality may go unreviewed."""
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        defined = await api.post(
            "/assets/custom-fields",
            json={
                "label": "Cost centre",
                "field_type": "select",
                "options": ["CC-100", "CC-200"],
                "required": False,
            },
        )
        assert defined.status_code == 201, defined.text
        field = defined.json()
        assert field["key"] == "cost_centre"

        # A choice field with no choices is refused, and so is a value that is
        # not one of them.
        assert (
            await api.post("/assets/custom-fields", json={"label": "Empty", "field_type": "select"})
        ).status_code == 422
        asset = await api.post(
            "/assets", json={"name": "Payments API", "custom_fields": {"cost_centre": "CC-999"}}
        )
        assert asset.status_code == 422, asset.text

        created = await api.post(
            "/assets",
            json={"name": "Payments API", "custom_fields": {"cost_centre": "CC-100"}},
        )
        assert created.status_code == 201, created.text
        assert created.json()["custom_fields"] == {"cost_centre": "CC-100"}

        # A key this workspace never defined does not quietly land in the blob.
        stray = await api.post(
            "/assets", json={"name": "Stray", "custom_fields": {"nobody_defined_this": "x"}}
        )
        assert stray.status_code == 422, stray.text

        # Archived stops the field being offered; the value already written stays.
        archived = await api.post(
            f"/assets/custom-fields/{field['id']}/archive", json={"archived": True}
        )
        assert archived.status_code == 200, archived.text
        assert (await api.get("/assets/custom-fields")).json()["items"] == []
        kept = await api.patch(
            f"/assets/{created.json()['id']}", json={"name": "Payments API", "custom_fields": {}}
        )
        assert kept.status_code == 200, kept.text
        assert kept.json()["custom_fields"] == {"cost_centre": "CC-100"}

        # The cadence is per criticality, and the hygiene panel reports the one
        # this asset was judged against.
        assert (await api.get("/assets/policy")).json()["days_by_tier"]["low"] == 90
        saved = await api.patch("/assets/policy", json={"days_by_tier": {"low": 180}})
        assert saved.status_code == 200, saved.text
        assert saved.json()["days_by_tier"]["low"] == 180
        assert (
            await api.patch("/assets/policy", json={"days_by_tier": {"low": 0}})
        ).status_code == 422
        rated = await api.patch(
            f"/assets/{created.json()['id']}",
            json={
                "name": "Payments API",
                "confidentiality": 1,
                "integrity": 1,
                "availability": 1,
            },
        )
        assert rated.json()["criticality"]["tier"] == "low"
        assert rated.json()["hygiene"]["review_days"] == 180

        # None of it is visible to another workspace.
        assert (await outsider.get("/assets/custom-fields")).json()["items"] == []
        assert (await outsider.get("/assets/policy")).json()["days_by_tier"]["low"] == 90
