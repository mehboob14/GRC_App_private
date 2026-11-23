"""Country reference panel: drafts held back, matches from the profile, decisions audited."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from verity.core.config import Settings, get_settings
from verity.core.db import dispose_engine
from verity.main import create_app
from verity.modules.regulations import service as regulations_module

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
async def api(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    ws: Workspace = await signup_workspace(company="Laws Ltd", email="founder@laws.example")
    async with client(app, tenant_session_headers(ws.membership_id)) as admin:
        yield admin


async def test_drafts_show_marked_and_can_be_held_back(
    api: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    held_back = get_settings().model_copy(update={"regulations_show_drafts": False})
    monkeypatch.setattr(regulations_module, "get_settings", lambda: held_back)
    await api.patch(
        "/tenant/profile",
        json={"answers": {"hq_country": "SA", "operating_countries": ["SA", "IN"]}},
    )
    held = (await api.get("/regulations")).json()
    assert held["regulations"] == []
    assert held["hidden_drafts"] > 0
    assert held["uncovered"] == ["IN"]
    assert "not legal advice" in held["disclaimer"]
    assert "not yet reviewed by a lawyer" not in held["disclaimer"], "nothing drafted is shown"

    drafts = get_settings().model_copy(update={"regulations_show_drafts": True})
    monkeypatch.setattr(regulations_module, "get_settings", lambda: drafts)
    shown = {r["key"]: r for r in (await api.get("/regulations")).json()["regulations"]}
    assert "not yet reviewed by a lawyer" in (await api.get("/regulations")).json()["disclaimer"]
    pdpl = shown["SA-01"]
    assert pdpl["confidence"] == "applies"
    assert pdpl["because"]
    assert all(not c.endswith("*") for c in pdpl["helps"])
    assert pdpl["review_status"] == "ai_drafted"

    refused = await api.put("/regulations/SA-01", json={"relevance": "not_relevant"})
    assert refused.status_code == 422
    ok = await api.put(
        "/regulations/SA-01", json={"relevance": "relevant", "note": "We hold Saudi customer data."}
    )
    assert ok.status_code == 204, ok.text
    assert (await api.put("/regulations/ZZ-99", json={"relevance": "relevant"})).status_code == 404
    after = {r["key"]: r for r in (await api.get("/regulations")).json()["regulations"]}
    assert after["SA-01"]["relevance"] == "relevant"
    assert after["SA-01"]["decided_by_name"]
