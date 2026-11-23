"""Company profile answers, confirmation and versions (guided onboarding phase 2).

PR-2: confirming needs every core question answered and names what is missing.
PR-3: editing a confirmed profile returns it to draft; confirming again writes the next
version, and earlier versions stay readable and cannot be changed.
GS: Get Started's profile step reads done only on a confirmed profile.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.support.documents import client
from tests.support.iam import Workspace, signup_workspace, tenant_session_headers
from tests.unit.test_profile_questions import FULL_CORE
from verity.core.config import Settings
from verity.core.db import dispose_engine, session_scope
from verity.main import create_app
from verity.modules.audit.service import audit_service

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
    return await signup_workspace(company="Profile Ltd", email="founder@profile.example")


@pytest.fixture
async def api(app: FastAPI, workspace: Workspace) -> AsyncIterator[httpx.AsyncClient]:
    async with client(app, tenant_session_headers(workspace.membership_id)) as admin:
        yield admin


async def _patch(api: httpx.AsyncClient, answers: dict[str, Any]) -> dict[str, Any]:
    response = await api.patch("/tenant/profile", json={"answers": answers})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _profile_step(api: httpx.AsyncClient) -> dict[str, Any]:
    status = await api.get("/onboarding/status")
    assert status.status_code == 200, status.text
    step: dict[str, Any] = next(s for s in status.json()["steps"] if s["key"] == "profile")
    return step


async def test_the_questions_are_served_with_what_each_is_used_for(api: httpx.AsyncClient) -> None:
    response = await api.get("/tenant/profile/questions")
    assert response.status_code == 200, response.text
    sections = response.json()
    assert [s["key"] for s in sections][:2] == ["about", "where"]
    hq = next(q for s in sections for q in s["questions"] if q["key"] == "hq_country")
    assert hq["core"] is True
    assert hq["kind"] == "country"
    assert hq["used_for"]


async def test_confirming_names_what_is_missing_then_freezes_version_one(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    first = await _patch(api, {"industry": "software", "hq_country": "PK"})
    assert (first["status"], first["version"], first["core_answered"]) == ("draft", 0, 2)
    step = await _profile_step(api)
    assert (step["state"], step["done_count"], step["total_count"]) == ("in_progress", 2, 16)

    refused = await api.post("/tenant/profile/confirm")
    assert refused.status_code == 422, refused.text
    assert "What do you sell" in refused.json()["error"]["message"]

    await _patch(api, FULL_CORE)
    confirmed = await api.post("/tenant/profile/confirm")
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert (body["status"], body["version"]) == ("confirmed", 1)
    assert body["confirmed_by_membership_id"] == str(workspace.membership_id)
    assert (await _profile_step(api))["state"] == "done"

    again = await api.post("/tenant/profile/confirm")
    assert again.status_code == 409


async def test_an_edit_reopens_the_profile_and_the_next_confirmation_is_version_two(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    await _patch(api, FULL_CORE)
    assert (await api.post("/tenant/profile/confirm")).status_code == 200

    edited = await _patch(api, {"offices": "own_premises"})
    assert (edited["status"], edited["version"]) == ("draft", 1)
    step = await _profile_step(api)
    assert step["state"] == "in_progress"
    assert "since version 1" in step["detail"]

    second = await api.post("/tenant/profile/confirm")
    assert second.json()["version"] == 2
    versions = (await api.get("/tenant/profile/versions")).json()
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[1]["answers"]["offices"] == "none"
    assert versions[0]["answers"]["offices"] == "own_premises"

    async with session_scope(workspace.tenant_id) as session:
        entries, _ = await audit_service.list_page(
            session, tenant_id=workspace.tenant_id, limit=20, object_type="company_profile"
        )
    assert sorted(e.action for e in entries).count("approve") == 2


async def test_an_unchanged_save_keeps_the_profile_confirmed(api: httpx.AsyncClient) -> None:
    await _patch(api, FULL_CORE)
    await api.post("/tenant/profile/confirm")
    same = await _patch(api, {"offices": FULL_CORE["offices"]})
    assert same["status"] == "confirmed"


async def test_a_frozen_version_cannot_be_changed(
    api: httpx.AsyncClient, workspace: Workspace
) -> None:
    await _patch(api, FULL_CORE)
    await api.post("/tenant/profile/confirm")

    async def rewrite() -> None:
        async with session_scope(workspace.tenant_id) as session:
            await session.execute(text("UPDATE company_profile_versions SET version = 99"))

    with pytest.raises(DBAPIError):
        await rewrite()


async def test_a_bad_answer_is_refused_and_nothing_is_saved(api: httpx.AsyncClient) -> None:
    response = await api.patch(
        "/tenant/profile", json={"answers": {"industry": "software", "hq_country": "XX"}}
    )
    assert response.status_code == 422, response.text
    profile = (await api.get("/tenant/profile")).json()
    assert profile["answers"] == {}
