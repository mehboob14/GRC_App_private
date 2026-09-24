"""Linked records through the real app: one edge per pair, readable from both ends.

Walks what the asset and vulnerability pages do: raise a risk from a finding,
link a second asset to that risk from the asset side, link a control to an
asset, and check every edge reads back from the other end too, including the
risk register's own detail. Then the walls: a type the page does not offer, and
a second workspace that cannot see the links at all.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
async def workspaces(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> tuple[Workspace, Workspace]:
    home = await signup_workspace(company="Links Ltd", email="links@example.test")
    other = await signup_workspace(company="Elsewhere Ltd", email="elsewhere@example.test")
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


def _pairs(body: dict[str, object]) -> set[tuple[str, str, str]]:
    records = body["records"]
    assert isinstance(records, list)
    return {(r["target_type"], r["target_id"], r["relation"]) for r in records}


async def test_links_read_from_both_ends_and_stay_inside_the_workspace(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        payments = (await api.post("/assets", json={"name": "Payments API"})).json()
        ledger = (await api.post("/assets", json={"name": "Ledger DB"})).json()
        scan = await api.post(
            "/vulnerabilities/import",
            files={
                "file": (
                    "scan.csv",
                    b"title,severity,asset\nOpen admin panel,critical,Payments API\n",
                )
            },
            data={"report_name": "Nightly scan"},
        )
        assert scan.status_code == 201, scan.text
        finding = (await api.get("/vulnerabilities")).json()[0]

        # A risk raised from the finding links back to it and to its asset.
        raised = await api.post(f"/vulnerabilities/{finding['id']}/raise-risk", json={})
        assert raised.status_code == 201, raised.text
        risk = raised.json()
        assert risk["code"].startswith("RSK")

        on_finding = (await api.get(f"/vulnerabilities/{finding['id']}/links")).json()
        assert ("risk", risk["id"], "caused_by") in _pairs(on_finding)
        assert "risk" in on_finding["can_link"]
        on_payments = (await api.get(f"/assets/{payments['id']}/links")).json()
        assert ("risk", risk["id"], "relates_to") in _pairs(on_payments)

        # Linking an asset to a risk from the asset is the risk register's edge.
        linked = await api.post(
            f"/assets/{ledger['id']}/links", json={"target_type": "risk", "target_id": risk["id"]}
        )
        assert linked.status_code == 201, linked.text
        detail = (await api.get(f"/risks/{risk['id']}")).json()
        assert {(link["target_type"], link["target_id"]) for link in detail["links"]} >= {
            ("asset", payments["id"]),
            ("asset", ledger["id"]),
            ("vulnerability", finding["id"]),
        }

        # A generic pair reads from the other end too, and unlinks cleanly.
        control = (await api.get("/controls")).json()[0]
        added = await api.post(
            f"/assets/{ledger['id']}/links",
            json={"target_type": "control", "target_id": control["id"]},
        )
        assert added.status_code == 201, added.text
        on_control = (await api.get(f"/controls/{control['id']}/links")).json()
        assert ("asset", ledger["id"], "relates_to") in _pairs(on_control)
        link_id = next(
            r["link_id"] for r in on_control["records"] if r["target_id"] == ledger["id"]
        )
        removed = await api.delete(f"/controls/{control['id']}/links/{link_id}")
        assert removed.status_code == 200, removed.text
        assert ("control", control["id"], "relates_to") not in _pairs(
            (await api.get(f"/assets/{ledger['id']}/links")).json()
        )

        # Only the offered types, and nothing across the tenant wall.
        refused = await api.post(
            f"/controls/{control['id']}/links",
            json={"target_type": "risk", "target_id": risk["id"]},
        )
        assert refused.status_code == 422, refused.text
        assert (await outsider.get(f"/assets/{payments['id']}/links")).status_code == 404
        assert (
            await outsider.post(f"/vulnerabilities/{finding['id']}/raise-risk", json={})
        ).status_code == 404
