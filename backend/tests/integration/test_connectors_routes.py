"""GitHub through the real app, against recorded GitHub responses (never a live account).

The build plan's week 7 exit: connect GitHub and watch controls marked pass or fail
from repository data. One healthy repository and one careless one: SD-06 fails on
the careless one, the snapshot is filed as evidence on the mapped controls, a
revoked token turns results into ``error`` rather than ``fail`` (rule 7), and a
second workspace sees none of it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app
from verity.modules.connectors.service import connector_service

pytestmark = [pytest.mark.integration]

TOKEN = "github_pat_recorded_fixture_0000"  # noqa: S105 — a fixture, not a credential


def _repo(name: str, *, scanning: str | None) -> dict[str, Any]:
    repo: dict[str, Any] = {
        "id": {"api": 101, "web": 102, "old": 103}[name],
        "full_name": f"acme/{name}",
        "html_url": f"https://github.com/acme/{name}",
        "private": True,
        "fork": False,
        "archived": name == "old",
        "default_branch": "main",
    }
    if scanning is not None:
        repo["security_and_analysis"] = {"secret_scanning": {"status": scanning}}
    return repo


class RecordedGitHub:
    """The GitHub API as recorded for one organisation, with a switch to revoke the token."""

    def __init__(self) -> None:
        self.revoked = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.revoked or request.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"message": "Bad credentials"})
        path = request.url.path
        recent = "2099-01-01T00:00:00Z"
        routes: dict[str, httpx.Response] = {
            "/user": httpx.Response(
                200,
                json={"login": "octocat", "name": "Octo Cat"},
                headers={"github-authentication-token-expiration": "2027-01-01 00:00:00 UTC"},
            ),
            "/orgs/acme": httpx.Response(
                200,
                json={"login": "acme", "name": "Acme Inc", "two_factor_requirement_enabled": True},
            ),
            "/orgs/acme/repos": httpx.Response(
                200,
                json=[
                    _repo("api", scanning="enabled"),
                    _repo("web", scanning=None),
                    _repo("old", scanning=None),
                ],
            ),
            "/repos/acme/web": httpx.Response(
                200, json={"security_and_analysis": {"secret_scanning": {"status": "disabled"}}}
            ),
            "/repos/acme/api/vulnerability-alerts": httpx.Response(204),
            "/repos/acme/web/vulnerability-alerts": httpx.Response(
                404, json={"message": "Not Found"}
            ),
            "/repos/acme/api/branches/main/protection": httpx.Response(
                200,
                json={
                    "allow_force_pushes": {"enabled": False},
                    "required_pull_request_reviews": {"required_approving_review_count": 1},
                    "required_status_checks": {"contexts": ["ci"]},
                },
            ),
            "/repos/acme/web/branches/main/protection": httpx.Response(
                404, json={"message": "Branch not protected"}
            ),
            "/repos/acme/api/rules/branches/main": httpx.Response(200, json=[]),
            "/repos/acme/web/rules/branches/main": httpx.Response(200, json=[]),
            "/repos/acme/api/pulls": httpx.Response(
                200,
                json=[
                    {
                        "number": 7,
                        "title": "Add rate limits",
                        "user": {"login": "alice"},
                        "merged_at": recent,
                        "updated_at": recent,
                        "html_url": "https://github.com/acme/api/pull/7",
                    }
                ],
            ),
            "/repos/acme/web/pulls": httpx.Response(
                200,
                json=[
                    {
                        "number": 3,
                        "title": "Hotfix",
                        "user": {"login": "bob"},
                        "merged_at": recent,
                        "updated_at": recent,
                        "html_url": "https://github.com/acme/web/pull/3",
                    }
                ],
            ),
            "/repos/acme/api/pulls/7/reviews": httpx.Response(
                200, json=[{"state": "APPROVED", "user": {"login": "carol"}}]
            ),
            "/repos/acme/web/pulls/3/reviews": httpx.Response(200, json=[]),
        }
        return routes.get(path, httpx.Response(404, json={"message": "Not Found"}))


@pytest.fixture
def github() -> Iterator[RecordedGitHub]:
    recorded = RecordedGitHub()

    async def no_wait(_seconds: float) -> None:
        return None

    connector_service.transport = httpx.MockTransport(recorded)
    connector_service.sleep = no_wait
    yield recorded
    connector_service.transport = None
    connector_service.sleep = None


@pytest.fixture
async def workspaces(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> tuple[Workspace, Workspace]:
    home = await signup_workspace(company="Octo Ltd", email="octo@example.test")
    other = await signup_workspace(company="Elsewhere Ltd", email="else@example.test")
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
    return next(c["id"] for c in controls if c["code"] == code)


async def test_connect_run_and_read_pass_and_fail_on_the_control(  # noqa: PLR0915 — one end to end story
    app: FastAPI, workspaces: tuple[Workspace, Workspace], github: RecordedGitHub
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        sd06 = await _control(api, "SD-06")
        before = (await api.get(f"/controls/{sd06}/automation")).json()
        assert before["status"] == "not_connected"
        version_control = next(c for c in before["capabilities"] if c["key"] == "version_control")
        assert {p["key"]: p["status"] for p in version_control["providers"]}[
            "github"
        ] == "available"

        wrong = await api.post(
            "/connections", json={"provider": "github", "token": "nope", "account": "acme"}
        )
        assert wrong.status_code == 422

        created = await api.post(
            "/connections", json={"provider": "github", "token": TOKEN, "account": "acme"}
        )
        assert created.status_code == 201, created.text
        connection = created.json()
        assert connection["account_login"] == "acme"
        assert connection["account_type"] == "organization"
        assert TOKEN not in created.text

        assert (await api.post(f"/connections/{connection['id']}/runs")).status_code == 202
        listed = (await api.get("/connections")).json()
        run = listed[0]["latest_run"]
        assert run["status"] == "completed", run
        assert run["failed"] > 0
        assert run["passed"] > 0
        assert run["evidence_id"]

        automation = (await api.get(f"/controls/{sd06}/automation")).json()
        assert automation["status"] == "failing"
        tests = {t["key"]: t for t in automation["tests"]}
        protected = tests["vcs.default_branch_protected"]
        assert protected["status"] == "fail"
        outcome = {r["resource_name"]: r["outcome"] for r in protected["results"]}
        assert outcome == {"acme/api": "pass", "acme/web": "fail"}  # archived repo is out of scope
        assert tests["vcs.merged_changes_reviewed"]["counts"]["fail"] == 1
        assert automation["history"][-1]["status"] == "fail"

        sd11 = await _control(api, "SD-11")
        scanning = (await api.get(f"/controls/{sd11}/automation")).json()
        assert {r["resource_name"]: r["outcome"] for r in scanning["tests"][0]["results"]} == {
            "acme/api": "pass",
            "acme/web": "fail",
        }

        evidence = (await api.get("/evidence", params={"control_id": sd06})).json()
        assert any(item["source_label"] == "GitHub connector" for item in evidence)

        # A second run with the same results files no second evidence item.
        await api.post(f"/connections/{connection['id']}/runs")
        again = (await api.get("/evidence", params={"control_id": sd06})).json()
        assert len([e for e in again if e["source_label"] == "GitHub connector"]) == 1

        # The token is revoked: results become error, never fail (rule 7).
        github.revoked = True
        await api.post(f"/connections/{connection['id']}/runs")
        health = (await api.get("/connections")).json()[0]
        assert health["latest_run"]["status"] == "failed"
        assert health["error_streak"] == 1
        assert "rejected" in health["last_error"]
        broken = (await api.get(f"/controls/{sd06}/automation")).json()
        assert broken["status"] == "error"
        assert {t["status"] for t in broken["tests"] if t["results"]} == {"error"}

        # The other workspace sees nothing and cannot act on it.
        assert (await outsider.get("/connections")).json() == []
        assert (await outsider.post(f"/connections/{connection['id']}/runs")).status_code == 404

        # Disconnecting destroys the token; a run is refused.
        gone = await api.post(
            f"/connections/{connection['id']}/disconnect", json={"reason": "Moving to GitLab"}
        )
        assert gone.json()["status"] == "disconnected"
        assert (await api.post(f"/connections/{connection['id']}/runs")).status_code == 409


async def test_a_workspace_can_request_an_integration_for_a_control(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        ep03 = await _control(api, "EP-03")
        automation = (await api.get(f"/controls/{ep03}/automation")).json()
        management = next(c for c in automation["capabilities"] if c["key"] == "device_management")
        assert {p["status"] for p in management["providers"]} == {"not_planned"}

        made = await api.post(
            "/integration-requests",
            json={
                "provider_name": "Hexnode",
                "capability_key": "device_management",
                "control_id": ep03,
                "note": "All laptops are in Hexnode.",
            },
        )
        assert made.status_code == 201, made.text
        again = (await api.get(f"/controls/{ep03}/automation")).json()
        assert [r["provider_name"] for r in again["requests"]] == ["Hexnode"]
        assert (await outsider.get("/integration-requests")).json() == []
