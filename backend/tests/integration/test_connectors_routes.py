"""GitHub through the real app, against recorded GitHub responses (never a live account).

The build plan's week 7 exit: connect GitHub and watch controls marked pass or fail
from repository data. One healthy repository and one careless one: SD-06 fails on
the careless one, the snapshot is filed as evidence on the mapped controls, a
revoked token turns results into ``error`` rather than ``fail`` (rule 7), and a
second workspace sees none of it.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.support.iam import Workspace, signup_workspace
from verity.core.config import Settings
from verity.main import create_app
from verity.modules.connectors import service as service_module
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
            # A personal account with nothing in it: only the organisation level check
            # has anything to say, and a person cannot require two factor for others.
            "/user/repos": httpx.Response(200, json=[]),
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
                        "head": {"sha": "sha7"},
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
                200,
                json=[
                    {
                        "state": "APPROVED",
                        "user": {"login": "carol"},
                        "submitted_at": "2098-12-31T00:00:00Z",
                        "commit_id": "sha7",
                    }
                ],
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
    return str(next(c["id"] for c in controls if c["code"] == code))


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

        # Each check files its own evidence, named for the check, on the controls that check
        # supports and no others: SD-06 is judged by three checks, SD-11 by one.
        evidence = (await api.get("/evidence", params={"control_id": sd06})).json()
        connector = [e for e in evidence if e["source_label"] == "GitHub connector"]
        assert sorted(e["title"].split(":")[0] for e in connector) == [
            "Default branch is protected",
            "Merged changes were reviewed",
            "Merges need an approving review",
        ]
        assert {e["source"] for e in connector} == {"github"}
        scanning_evidence = (await api.get("/evidence", params={"control_id": sd11})).json()
        assert [e["title"].split(":")[0] for e in scanning_evidence] == ["Secret scanning is on"]
        assert scanning_evidence[0]["control_codes"] == ["SD-11"]

        # A second run with the same results files nothing new.
        await api.post(f"/connections/{connection['id']}/runs")
        again = (await api.get("/evidence", params={"control_id": sd06})).json()
        assert len([e for e in again if e["source_label"] == "GitHub connector"]) == 3

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


async def _connected(api: httpx.AsyncClient, account: str | None = "acme") -> dict[str, Any]:
    body: dict[str, Any] = {"provider": "github", "token": TOKEN}
    if account:
        body["account"] = account
    made = await api.post("/connections", json=body)
    assert made.status_code == 201, made.text
    connection: dict[str, Any] = made.json()
    await api.post(f"/connections/{connection['id']}/runs")
    return connection


async def test_scope_is_chosen_with_a_reason_audited_and_printed_on_the_evidence(  # noqa: PLR0915 — one story
    app: FastAPI, workspaces: tuple[Workspace, Workspace], github: RecordedGitHub
) -> None:
    """AU-9. A repository is checked unless it is out of scope, and out of scope
    needs a reason that is kept, audited and printed on the evidence."""
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        connection = await _connected(api)
        base = f"/connections/{connection['id']}"

        resources = {r["name"]: r for r in (await api.get(f"{base}/resources")).json()}
        assert set(resources) == {"acme/api", "acme/web", "acme/old"}
        assert (resources["acme/old"]["scope"], resources["acme/old"]["decided_by"]) == (
            "excluded",
            "system",
        )
        assert resources["acme/web"]["scope"] == "in_scope"
        assert (await api.get("/connections")).json()[0]["scope"] == {
            "listed": 3,
            "in_scope": 2,
            "excluded": 1,
        }

        web = resources["acme/web"]["external_id"]
        left_out = {"decisions": [{"external_id": web, "scope": "excluded"}]}
        refused = await api.put(f"{base}/scope", json=left_out)
        assert refused.status_code == 422, refused.text
        done = await api.put(
            f"{base}/scope", json={**left_out, "reason": "Prototype, never deployed."}
        )
        assert done.status_code == 200, done.text
        changed = next(r for r in done.json() if r["name"] == "acme/web")
        assert (changed["scope"], changed["decided_by"], changed["reason"]) == (
            "excluded",
            "person",
            "Prototype, never deployed.",
        )
        assert changed["decided_by_name"]

        # An unknown repository and another workspace are both refused.
        nope = {"decisions": [{"external_id": "nope", "scope": "in_scope"}]}
        assert (await api.put(f"{base}/scope", json=nope)).status_code == 404
        assert (await outsider.get(f"{base}/resources")).status_code == 404
        assert (await outsider.put(f"{base}/scope", json=left_out)).status_code == 404

        # The next run checks only what is in scope, and says what it left out.
        await api.post(f"{base}/runs")
        sd06 = await _control(api, "SD-06")
        automation = (await api.get(f"/controls/{sd06}/automation")).json()
        protected = next(
            t for t in automation["tests"] if t["key"] == "vcs.default_branch_protected"
        )
        assert {r["resource_name"] for r in protected["results"]} == {"acme/api"}
        assert automation["status"] == "passing"
        scope = automation["scopes"][0]
        assert (scope["account"], scope["listed"], scope["in_scope"], scope["excluded"]) == (
            "acme",
            3,
            1,
            2,
        )

        evidence = (await api.get("/evidence", params={"control_id": sd06})).json()
        newest = max(
            (e for e in evidence if e["source_label"] == "GitHub connector"),
            key=lambda e: e["id"],  # ids are time ordered
        )
        # Named for the check, where and when: the moment tells apart the several that can
        # land on one day, and the file names its check so a report of it needs nothing else.
        assert re.fullmatch(
            r"[A-Z][^:]+: GitHub acme, \d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2} UTC",
            newest["title"],
        )
        document = json.loads((await api.get(f"/evidence/{newest['id']}/download")).content)
        check = document["verity"]["check"]
        assert newest["title"].startswith(f"{check['name']}: ")
        # The file holds this check's results and the part of the snapshot it read: no other
        # check's results, and not the whole inventory.
        assert document["verity"]["results"]
        assert {row["check"] for row in document["verity"]["results"]} == {check["key"]}
        assert all(row["name"] == check["name"] for row in document["verity"]["results"])
        assert "inventory" not in document["snapshot"]
        assert all(
            "security_and_analysis" not in repo for repo in document["snapshot"]["repositories"]
        )
        printed = {e["resource"]: e for e in document["verity"]["scope"]["excluded"]}
        assert document["verity"]["scope"]["checked"] == 1
        assert printed["acme/web"]["reason"] == "Prototype, never deployed."
        assert printed["acme/web"]["decided_by"] == "person"
        assert printed["acme/old"]["decided_by"] == "system"

        # The six files the second run replaced are history: the dashboard counts the
        # seven that stand (one per check), not the thirteen in the library.
        posture = (await api.get("/engagement/dashboard")).json()
        assert posture["evidence_total"] == 7

        # Only what changed is filed again: the account level two factor check found the same
        # thing both times, so IAM-03 still holds the one file from the first run.
        iam03 = await _control(api, "IAM-03")
        two_factor = (await api.get("/evidence", params={"control_id": iam03})).json()
        assert len(two_factor) == 1
        assert two_factor[0]["control_codes"] == ["IAM-03"]

        trail = (await api.get("/audit-log", params={"object_type": "connection_resource"})).json()
        assert [entry["action"] for entry in trail["items"]] == ["update"]


async def test_a_control_with_nothing_to_verify_is_not_reported_as_passing(
    app: FastAPI, workspaces: tuple[Workspace, Workspace], github: RecordedGitHub
) -> None:
    """AU-5: not applicable counts neither as a pass nor a fail. A personal account
    cannot require two factor, so IAM-03 has been verified by nothing."""
    home, _ = workspaces
    async with _client(app, home) as api:
        await _connected(api, account=None)
        iam03 = await _control(api, "IAM-03")
        automation = (await api.get(f"/controls/{iam03}/automation")).json()
        two_factor = next(
            t for t in automation["tests"] if t["key"] == "vcs.org_two_factor_required"
        )
        assert two_factor["status"] == "not_applicable"
        assert automation["status"] == "not_applicable"
        # An account with no repositories leaves repository checks nothing to judge:
        # that is "nothing to verify", not "still waiting for the first run".
        sd06 = await _control(api, "SD-06")
        review = (await api.get(f"/controls/{sd06}/automation")).json()
        assert review["status"] == "not_applicable"
        assert {t["status"] for t in review["tests"] if t["availability"] == "running"} == {
            "not_applicable"
        }
        dashboard = (await api.get("/engagement/dashboard")).json()
        assert (
            dashboard["automation_passing"],
            dashboard["automation_failing"],
            dashboard["automation_error"],
        ) == (0, 0, 0)


async def test_failing_tests_and_unusable_evidence_keep_a_control_from_being_ready(
    app: FastAPI, workspaces: tuple[Workspace, Workspace], github: RecordedGitHub
) -> None:
    """AU-6 and CF-4. Ready is implemented, evidenced with something that still
    counts, and not contradicted by a test. A requirement is met only when every
    control that applies to it is."""
    home, _ = workspaces
    async with _client(app, home) as api:
        frameworks = (await api.get("/frameworks")).json()
        soc2 = next(f for f in frameworks if f["code"] == "SOC2")
        engaged = await api.put(
            "/engagement",
            json={
                "name": "SOC 2 Type II",
                "framework_version_id": soc2["versions"][0]["id"],
                "audit_type": "type_1",
                "categories_in_scope": [],
            },
        )
        assert engaged.status_code == 200, engaged.text
        await _connected(api)
        sd06, iam03 = await _control(api, "SD-06"), await _control(api, "IAM-03")
        for control_id in (sd06, iam03):
            await api.patch(f"/controls/{control_id}", json={"status": "implemented"})

        async def dashboard() -> dict[str, Any]:
            report: dict[str, Any] = (await api.get("/engagement/dashboard")).json()
            return report

        # SD-06 is evidenced by the connector and marked implemented, but its tests
        # fail: it is not ready. IAM-03's single test passes: it is.
        report = await dashboard()
        assert report["checks_available"] is True
        assert (report["automation_passing"], report["automation_failing"]) == (1, 6)
        assert report["controls_ready"] == 1

        # Evidence a reviewer rejected no longer counts, even though it is attached.
        iam_evidence = (await api.get("/evidence", params={"control_id": iam03})).json()[0]
        rejected = await api.post(
            f"/evidence/{iam_evidence['id']}/review",
            json={"decision": "rejected", "note": "Does not show every member."},
        )
        assert rejected.status_code == 200, rejected.text
        assert (await dashboard())["controls_ready"] == 0

        # Evidence past its renewal date does not count either; current evidence does.
        gov12 = await _control(api, "GOV-12")
        await api.patch(f"/controls/{gov12}", json={"status": "implemented"})

        async def attach(control_id: str, collected: str, renewal: str) -> None:
            made = await api.post(
                "/evidence/link",
                json={
                    "title": f"Evidence {collected}",
                    "link_url": "https://example.test/proof",
                    "evidence_type": "policy_document",
                    "collected_at": collected,
                    "renewal_date": renewal,
                    "control_ids": [control_id],
                },
            )
            assert made.status_code == 201, made.text

        await attach(gov12, "2024-01-01", "2024-06-01")
        assert (await dashboard())["controls_ready"] == 0
        await attach(gov12, "2026-10-01", "2027-10-01")
        report = await dashboard()
        assert report["controls_ready"] == 1

        def ready_in_security(rep: dict[str, Any]) -> int:
            return int(next(c for c in rep["by_category"] if c["category"] == "Security")["ready"])

        # CC3.3 has one control, GOV-12: finished, so the requirement is met.
        assert ready_in_security(report) == 1

        # CC1.2 has two controls. One finished control does not meet it; both do.
        gov02, gov15 = await _control(api, "GOV-02"), await _control(api, "GOV-15")
        for control_id in (gov02, gov15):
            await api.patch(f"/controls/{control_id}", json={"status": "implemented"})
        await attach(gov02, "2026-10-01", "2027-10-01")
        assert ready_in_security(await dashboard()) == 1
        await attach(gov15, "2026-10-01", "2027-10-01")
        assert ready_in_security(await dashboard()) == 2


async def _criterion(api: httpx.AsyncClient, code: str) -> str:
    framework = (await api.get("/frameworks")).json()[0]
    requirements = (await api.get(f"/frameworks/{framework['id']}/requirements")).json()
    return str(next(r["id"] for r in requirements if r["code"] == code))


async def test_a_control_says_what_evidences_it_and_how_that_changes_when_a_system_connects(
    app: FastAPI, workspaces: tuple[Workspace, Workspace], github: RecordedGitHub
) -> None:
    """The control page names every source of evidence: checks and the systems that
    run them, Verity modules, and what people provide, and says which is which."""
    home, _other = workspaces
    async with _client(app, home) as api:
        sd06 = await _control(api, "SD-06")
        before = (await api.get(f"/controls/{sd06}/automation")).json()
        composition = before["composition"]
        assert composition["mode"] == "automated"
        assert (
            composition["checks_total"],
            composition["checks_running"],
            composition["checks_ready"],
            composition["checks_planned"],
        ) == (4, 0, 3, 1)
        [source] = composition["sources"]
        assert (source["key"], source["kind"], source["state"], source["providers"]) == (
            "version_control",
            "connector",
            "available",
            ["GitHub"],
        )

        review = next(t for t in before["tests"] if t["key"] == "vcs.review_required")
        assert review["availability"] == "ready"
        assert review["source"] == "connector"
        assert review["evidence_kinds"] == ["Required review settings"]
        assert review["coverage"] == "partial"
        assert review["rationale"]
        [needs] = review["needs"]
        assert needs["key"] == "version_control"
        assert {p["key"]: p["runs_check"] for p in needs["providers"]} == {
            "github": True,
            "gitlab": False,
            "bitbucket": False,
        }
        unreviewed = next(
            t for t in before["tests"] if t["key"] == "vcs.unreviewed_merges_recorded"
        )
        assert unreviewed["availability"] == "planned"

        sample = next(e for e in before["evidence"] if e["name"] == "Sample of reviewed changes")
        assert (sample["state"], sample["assurance"]) == ("when_connected", "operating")
        assert [c["key"] for c in sample["automated_by"]] == ["vcs.merged_changes_reviewed"]
        policy = next(e for e in before["evidence"] if e["source"] == "platform")
        assert (policy["state"], policy["module"]) == ("platform", "documents")

        mapping = next(m for m in before["mappings"] if m["code"] == "CC8.1")
        assert (mapping["coverage"], mapping["origin"]) == ("partial", "library")
        assert mapping["rationale"]

        await _connected(api)
        after = (await api.get(f"/controls/{sd06}/automation")).json()
        assert after["composition"]["checks_running"] == 3
        assert after["composition"]["sources"][0]["state"] == "connected"
        assert (
            next(e for e in after["evidence"] if e["name"] == "Sample of reviewed changes")["state"]
            == "automatic"
        )

        # The trace from request to release needs a ticket system and a pipeline
        # collector that do not exist yet. Saying so is the point: nothing is faked.
        sd14 = await _control(api, "SD-14")
        trace = (await api.get(f"/controls/{sd14}/automation")).json()
        assert {t["key"]: t["availability"] for t in trace["tests"]} == {
            "tickets.changes_linked": "planned",
            "ci.deployment_history_recorded": "planned",
        }
        assert trace["composition"]["checks_running"] == 0
        assert trace["evidence"][0]["state"] == "planned"


async def test_a_control_with_only_people_and_modules_is_manual_or_platform_not_connected(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, _other = workspaces
    async with _client(app, home) as api:
        gov10 = await _control(api, "GOV-10")  # a named officer: people only
        manual = (await api.get(f"/controls/{gov10}/automation")).json()
        assert manual["composition"]["mode"] == "manual"
        assert manual["composition"]["checks_total"] == 0
        assert manual["composition"]["items_manual"] == 2
        assert {e["state"] for e in manual["evidence"]} == {"manual"}

        gov01 = await _control(api, "GOV-01")  # policy review: Verity documents
        platform = (await api.get(f"/controls/{gov01}/automation")).json()
        [check] = platform["tests"]
        assert (check["source"], check["availability"]) == ("platform", "planned")
        assert platform["composition"]["sources"][0]["kind"] == "platform"


async def test_the_register_says_how_every_control_is_evidenced(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    home, other = workspaces
    async with _client(app, home) as api, _client(app, other) as outsider:
        controls = (await api.get("/controls")).json()
        items = (await api.get("/control-composition")).json()
        assert {i["control_id"] for i in items} == {c["id"] for c in controls}
        modes = {i["composition"]["mode"] for i in items}
        assert modes == {"automated", "hybrid", "manual"}
        sd13_id = await _control(api, "SD-13")
        sd13 = next(i for i in items if i["control_id"] == sd13_id)
        assert sd13["composition"]["checks_total"] == 2
        # Each row names its control, and says which systems have a collector for it, so a
        # page can list the controls a connection checks without a second request.
        assert (sd13["code"], bool(sd13["name"])) == ("SD-13", True)
        sd11_id = await _control(api, "SD-11")
        sd11 = next(i for i in items if i["control_id"] == sd11_id)
        assert "github" in sd11["composition"]["runs_on"]
        assert all(i["code"] and i["name"] for i in items)
        # Another workspace gets its own controls, never this one's.
        theirs = {i["control_id"] for i in (await outsider.get("/control-composition")).json()}
        assert theirs
        assert theirs.isdisjoint({i["control_id"] for i in items})


async def test_a_criterion_shows_the_controls_that_answer_it_and_what_evidences_each(
    app: FastAPI, workspaces: tuple[Workspace, Workspace]
) -> None:
    """The view a buyer's auditor starts from: CC8.1, its controls, the checks and
    the evidence behind each, and whether the criterion is met."""
    home, _other = workspaces
    async with _client(app, home) as api:
        cc81 = await _criterion(api, "CC8.1")
        chain = (await api.get(f"/requirements/{cc81}/chain")).json()
        assert chain["requirement"]["code"] == "CC8.1"
        assert chain["state"] == "not_started"
        assert [c["code"] for c in chain["controls"]] == [
            "SD-01",
            "SD-02",
            "SD-04",
            "SD-06",
            "SD-10",
            "SD-12",
            "SD-13",
            "SD-14",
        ]
        sd01 = next(c for c in chain["controls"] if c["code"] == "SD-01")
        assert (sd01["coverage"], sd01["origin"]) == ("full", "library")
        assert sd01["rationale"]
        keys = {c["key"] for c in sd01["chain"]["checks"]}
        assert {"vcs.review_required", "tickets.changes_linked"} <= keys
        assert all(c["chain"]["evidence"] for c in chain["controls"])
        assert all(c["ready"] is False for c in chain["controls"])

        # Finishing every control and evidencing it meets the criterion; one short of
        # that leaves it partly met.
        controls = {c["code"]: c["control_id"] for c in chain["controls"]}
        for control_id in controls.values():
            await api.patch(f"/controls/{control_id}", json={"status": "implemented"})
            made = await api.post(
                "/evidence/link",
                json={
                    "title": "Proof",
                    "link_url": "https://example.test/proof",
                    "evidence_type": "policy_document",
                    "collected_at": "2026-10-01",
                    "renewal_date": "2027-10-01",
                    "control_ids": [control_id],
                },
            )
            assert made.status_code == 201, made.text
        assert (await api.get(f"/requirements/{cc81}/chain")).json()["state"] == "met"
        await api.patch(f"/controls/{controls['SD-14']}", json={"status": "in_progress"})
        assert (await api.get(f"/requirements/{cc81}/chain")).json()["state"] == "partly"

        missing = await api.get("/requirements/00000000-0000-4000-8000-000000000000/chain")
        assert missing.status_code == 404


async def test_results_that_are_too_old_are_out_of_date_and_stop_a_control_reading_passing(
    app: FastAPI,
    workspaces: tuple[Workspace, Workspace],
    github: RecordedGitHub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AU-5. A connection that stopped running a week ago must not keep a control
    green: past the window its results are out of date, and out of date is not ready."""
    home, _other = workspaces
    async with _client(app, home) as api:
        await _connected(api)
        iam03 = await _control(api, "IAM-03")
        fresh = (await api.get(f"/controls/{iam03}/automation")).json()
        assert fresh["status"] == "passing"

        monkeypatch.setattr(service_module, "STALE_AFTER", timedelta(0))
        old = (await api.get(f"/controls/{iam03}/automation")).json()
        assert old["status"] == "stale"
        assert {t["status"] for t in old["tests"] if t["results"]} == {"stale"}

        # Out of date takes the place of pass and of fail alike: nothing known is
        # current, so neither is claimed.
        sd06 = await _control(api, "SD-06")
        assert (await api.get(f"/controls/{sd06}/automation")).json()["status"] == "stale"

        # The register and the criterion view read the same status.
        items = {i["control_id"]: i for i in (await api.get("/control-composition")).json()}
        assert items[iam03]["automation_status"] == "stale"
