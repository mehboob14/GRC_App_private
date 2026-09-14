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
            json={"rows": [{"name": "Build server", "asset_type": "infrastructure"}]},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["created"] == 1
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
