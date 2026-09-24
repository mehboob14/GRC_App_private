"""GitHub checks from a recorded snapshot, and the shared provider HTTP behaviour.

Evaluation is a pure function of the snapshot, so every pass, fail and error rule
is pinned here without a network. Rule 7 is the thread: anything Verity could not
read is ``error``, never ``fail``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from verity.modules.connectors import github
from verity.modules.connectors.http import (
    AccessDenied,
    CredentialRejected,
    ProviderHttp,
    ProviderUnavailable,
    RateLimitExhausted,
)


def _repo(name: str, **overrides: Any) -> dict[str, Any]:  # noqa: ANN401 — snapshot fields
    repo: dict[str, Any] = {
        "id": name,
        "full_name": f"acme/{name}",
        "url": f"https://github.com/acme/{name}",
        "private": True,
        "fork": False,
        "default_branch": "main",
        "security_and_analysis": {"secret_scanning": {"status": "enabled"}},
        "protection": {
            "state": "present",
            "data": {
                "allow_force_pushes": {"enabled": False},
                "required_pull_request_reviews": {"required_approving_review_count": 1},
                "required_status_checks": {"contexts": ["ci"]},
            },
        },
        "rules": {"state": "present", "data": []},
        "vulnerability_alerts": "enabled",
        "merged_changes": {
            "state": "ok",
            "total": 1,
            "items": [{"number": 7, "author": "alice", "approvers": ["carol"]}],
        },
    }
    repo.update(overrides)
    return repo


def _outcomes(snapshot: dict[str, Any]) -> dict[tuple[str, str], str]:
    return {(r.check_key, r.resource_name): r.outcome for r in github.evaluate(snapshot)}


def _snapshot(*repos: dict[str, Any], two_factor: bool | None = True) -> dict[str, Any]:
    return {
        "account": {"login": "acme", "type": "organization", "two_factor_required": two_factor},
        "repositories": list(repos),
    }


def test_a_well_run_repository_passes_every_check() -> None:
    outcomes = _outcomes(_snapshot(_repo("api")))
    assert set(outcomes.values()) == {"pass"}
    assert len(outcomes) == len(github.IMPLEMENTED)


def test_an_unprotected_repository_fails_and_says_why() -> None:
    repo = _repo(
        "web",
        protection={"state": "absent"},
        security_and_analysis={"secret_scanning": {"status": "disabled"}},
        vulnerability_alerts="disabled",
        merged_changes={
            "state": "ok",
            "total": 2,
            "items": [
                {"number": 3, "author": "bob", "approvers": []},
                {"number": 4, "author": "bob", "approvers": ["dan"]},
            ],
        },
    )
    results = {r.check_key: r for r in github.evaluate(_snapshot(repo))}
    for key in (
        github.DEFAULT_BRANCH_PROTECTED,
        github.REVIEW_REQUIRED,
        github.STATUS_CHECKS_REQUIRED,
        github.SECRET_SCANNING_ENABLED,
        github.DEPENDENCY_ALERTS_ENABLED,
        github.MERGED_CHANGES_REVIEWED,
    ):
        assert results[key].outcome == "fail", key
    assert results[github.MERGED_CHANGES_REVIEWED].detail["unreviewed"] == [3]
    assert results[github.MERGED_CHANGES_REVIEWED].detail["summary"].startswith("1 of 2")


def test_a_ruleset_counts_as_protection_and_review() -> None:
    repo = _repo(
        "svc",
        protection={"state": "absent"},
        rules={
            "state": "present",
            "data": [
                {"type": "pull_request", "parameters": {"required_approving_review_count": 2}},
                {
                    "type": "required_status_checks",
                    "parameters": {"required_status_checks": [{"context": "ci"}]},
                },
            ],
        },
    )
    outcomes = _outcomes(_snapshot(repo))
    assert outcomes[(github.DEFAULT_BRANCH_PROTECTED, "acme/svc")] == "pass"
    assert outcomes[(github.REVIEW_REQUIRED, "acme/svc")] == "pass"
    assert outcomes[(github.STATUS_CHECKS_REQUIRED, "acme/svc")] == "pass"


def test_force_pushes_allowed_is_a_failure_even_when_protected() -> None:
    repo = _repo("api")
    repo["protection"]["data"]["allow_force_pushes"] = {"enabled": True}
    assert _outcomes(_snapshot(repo))[(github.DEFAULT_BRANCH_PROTECTED, "acme/api")] == "fail"


def test_what_the_token_cannot_read_is_error_never_fail() -> None:
    repo = _repo(
        "api",
        protection={"state": "unreadable", "reason": "403"},
        security_and_analysis=None,
        vulnerability_alerts="unreadable",
        merged_changes={"state": "unreadable", "items": [], "total": 0},
    )
    outcomes = _outcomes(_snapshot(repo, two_factor=None))
    assert set(outcomes.values()) == {"error"}


def test_nothing_merged_is_not_applicable_and_a_person_cannot_require_two_factor() -> None:
    repo = _repo("docs", merged_changes={"state": "ok", "items": [], "total": 0})
    snapshot = _snapshot(repo)
    snapshot["account"] = {"login": "octocat", "type": "user", "two_factor_required": None}
    outcomes = _outcomes(snapshot)
    assert outcomes[(github.MERGED_CHANGES_REVIEWED, "acme/docs")] == "not_applicable"
    assert outcomes[(github.ORG_TWO_FACTOR_REQUIRED, "octocat")] == "not_applicable"


def test_an_unreachable_account_is_an_error_on_every_check() -> None:
    results = github.unreachable("acme", "organization", "GitHub rejected the stored token.")
    assert {r.check_key for r in results} == set(github.IMPLEMENTED)
    assert {r.outcome for r in results} == {"error"}


def test_token_expiry_is_read_from_the_github_header() -> None:
    parsed = github._parse_expiry("2026-12-01 00:00:00 UTC")
    assert parsed == datetime(2026, 12, 1, tzinfo=UTC)
    assert github._parse_expiry("not a date") is None


# -- shared HTTP ---------------------------------------------------------------------


async def _no_wait(_seconds: float) -> None:
    return None


def _http(handler: Any) -> ProviderHttp:  # noqa: ANN401 — a MockTransport handler
    return ProviderHttp(
        "https://api.example",
        headers={},
        timeout=5,
        transport=httpx.MockTransport(handler),
        sleep=_no_wait,
    )


async def test_transient_failures_are_retried_then_succeed() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(502) if calls["n"] < 3 else httpx.Response(200, json={"ok": True})

    async with _http(handler) as http:
        assert await http.get_json("/thing") == {"ok": True}
    assert calls["n"] == 3


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(401), CredentialRejected),
        (httpx.Response(403, json={"message": "no"}), AccessDenied),
        (httpx.Response(403, headers={"x-ratelimit-remaining": "0"}), RateLimitExhausted),
        (httpx.Response(503), ProviderUnavailable),
    ],
)
async def test_failures_are_classified(response: httpx.Response, error: type[Exception]) -> None:
    async with _http(lambda _request: response) as http:
        with pytest.raises(error):
            await http.get("/thing")


async def test_paging_follows_the_link_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json=[3])
        return httpx.Response(
            200, json=[1, 2], headers={"link": '<https://api.example/items?page=2>; rel="next"'}
        )

    async with _http(handler) as http:
        assert [item async for item in http.paginate("/items")] == [1, 2, 3]
