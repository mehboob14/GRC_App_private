"""Suggested mappings and the maturity check through the real app, with no model key set:
the offline matcher still answers, and the maturity check says it is unavailable rather than
inventing a score."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


async def test_suggestions_work_offline_and_maturity_is_not_invented(
    app: FastAPI, clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> None:
    home: Workspace = await signup_workspace(company="Ai Ltd", email="ai@example.test")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test/api/v1",
        headers={"Authorization": f"Bearer {home.session_token}"},
    ) as api:
        made = await api.post(
            "/evidence/file",
            data={
                "title": "Secret scanning report",
                "evidence_type": "log_export",
                "collected_at": "2026-10-01",
                "description": "secret scanning of repositories",
            },
            files={"file": ("scan.txt", b"0 secrets found in 12 repositories", "text/plain")},
        )
        assert made.status_code == 201, made.text
        evidence_id = made.json()["id"]

        suggested = (await api.post(f"/evidence/{evidence_id}/suggest-mappings")).json()
        assert suggested["source"] == "heuristic"
        row = suggested["suggestions"][0]
        assert {"maturity", "verdict", "gaps", "requirements"} <= set(row)
        assert row["maturity"] is None

        control = row["control_id"]
        judged = await api.post(f"/evidence/{evidence_id}/maturity", json={"control_id": control})
        assert judged.status_code == 200, judged.text
        assert judged.json()["available"] is False
        gone = await api.post(
            f"/evidence/{evidence_id}/maturity",
            json={"control_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert gone.status_code == 404
