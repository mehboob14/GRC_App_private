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


# -- accuracy: what "protected" means, plans, empty repositories -----------------------


def test_protection_that_only_blocks_force_pushes_still_accepts_direct_pushes() -> None:
    """The control is about changes being reviewed. A branch anyone with write
    access can push straight to is not protected, whatever else is switched on."""
    repo = _repo(
        "billing",
        protection={"state": "present", "data": {"allow_force_pushes": {"enabled": False}}},
    )
    result = next(
        r
        for r in github.evaluate(_snapshot(repo))
        if r.check_key == github.DEFAULT_BRANCH_PROTECTED
    )
    assert result.outcome == "fail"
    assert "still accepts direct pushes" in result.detail["summary"]


def test_restricting_who_can_push_counts_as_blocking_direct_pushes() -> None:
    repo = _repo(
        "api",
        protection={
            "state": "present",
            "data": {
                "allow_force_pushes": {"enabled": False},
                "restrictions": {"users": [], "teams": [{"slug": "release"}], "apps": []},
            },
        },
    )
    assert _outcomes(_snapshot(repo))[(github.DEFAULT_BRANCH_PROTECTED, "acme/api")] == "pass"


def test_a_ruleset_that_only_stops_deletion_does_not_protect_the_branch() -> None:
    repo = _repo(
        "svc",
        protection={"state": "absent"},
        rules={"state": "present", "data": [{"type": "deletion"}]},
    )
    assert _outcomes(_snapshot(repo))[(github.DEFAULT_BRANCH_PROTECTED, "acme/svc")] == "fail"


def test_a_plan_that_does_not_offer_protection_fails_and_names_the_plan() -> None:
    """Free plans refuse branch protection on private repositories. That is a
    finding with its own remedy (upgrade, or exclude with a reason), not a
    permission gap and not generic advice to protect a branch that cannot be."""
    repo = _repo("private-app", protection={"state": "absent", "reason": "plan"})
    results = {r.check_key: r for r in github.evaluate(_snapshot(repo))}
    for key in (
        github.DEFAULT_BRANCH_PROTECTED,
        github.REVIEW_REQUIRED,
        github.STATUS_CHECKS_REQUIRED,
    ):
        assert results[key].outcome == "fail", key
        assert results[key].detail["reason"] == "plan", key
        assert "plan" in results[key].detail["summary"], key


def test_missing_secret_scanning_is_the_plan_with_admin_and_the_token_without() -> None:
    plan = _repo("a", security_and_analysis=None, admin=True)
    token = _repo("b", security_and_analysis=None, admin=False)
    outcomes = _outcomes(_snapshot(plan, token))
    assert outcomes[(github.SECRET_SCANNING_ENABLED, "acme/a")] == "fail"
    assert outcomes[(github.SECRET_SCANNING_ENABLED, "acme/b")] == "error"
    scanning = next(
        r for r in github.evaluate(_snapshot(plan)) if r.check_key == github.SECRET_SCANNING_ENABLED
    )
    assert scanning.detail["reason"] == "plan"


def test_a_repository_with_no_commits_has_nothing_to_check() -> None:
    repo = _repo("fresh", protection={"state": "absent", "reason": "no_branch"})
    outcomes = {
        key: outcome
        for (key, name), outcome in _outcomes(_snapshot(repo)).items()
        if name == "acme/fresh"
    }
    assert set(outcomes.values()) == {"not_applicable"}
    assert github.ORG_TWO_FACTOR_REQUIRED not in outcomes


# -- scope (AU-9) -------------------------------------------------------------------------


def _listing(*repos: dict[str, Any]) -> Any:  # noqa: ANN401 — a MockTransport handler
    base = {"private": False, "fork": False, "archived": False, "default_branch": "main"}
    listed = [{**base, "html_url": f"https://github.com/{r['full_name']}", **r} for r in repos]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/user/repos":
            return httpx.Response(200, json=listed)
        if path.endswith("/pulls"):
            return httpx.Response(200, json=[])
        if path.startswith("/repos/") and path.count("/") == 3:
            return httpx.Response(200, json={"security_and_analysis": None})
        return httpx.Response(404, json={"message": "Not Found"})

    return handler


_NOW = datetime(2026, 10, 3, tzinfo=UTC)
_FORKED = {"id": 2, "full_name": "me/forked", "fork": True}
_OLD = {"id": 3, "full_name": "me/old", "archived": True}
_APP = {"id": 1, "full_name": "me/app"}


async def _collect(
    *repos: dict[str, Any], decisions: dict[str, github.ScopeDecision] | None = None
) -> dict[str, Any]:
    async with _http(_listing(*repos)) as http:
        return await github.collect(
            http, login="me", account_type="user", now=_NOW, decisions=decisions
        )


async def test_forks_and_archived_repositories_are_out_of_scope_with_a_reason() -> None:
    snapshot = await _collect(_APP, _FORKED, _OLD)
    assert [r["full_name"] for r in snapshot["repositories"]] == ["me/app"]
    inventory = {entry["full_name"]: entry for entry in snapshot["inventory"]}
    assert inventory["me/app"]["scope"] == "in_scope"
    assert inventory["me/forked"]["scope"] == "excluded"
    assert inventory["me/forked"]["reason"].startswith("A fork")
    assert inventory["me/old"]["reason"].startswith("Archived")
    assert {e["decided_by"] for e in inventory.values()} == {"system"}
    assert snapshot["repositories_listed"] == 3
    assert snapshot["repositories_excluded"] == 2


async def test_a_person_can_bring_a_fork_in_and_take_a_repository_out() -> None:
    snapshot = await _collect(
        _APP,
        _FORKED,
        decisions={
            "2": github.ScopeDecision("in_scope"),
            "1": github.ScopeDecision("excluded", "Sandbox, not the audited system."),
        },
    )
    assert [r["full_name"] for r in snapshot["repositories"]] == ["me/forked"]
    inventory = {entry["full_name"]: entry for entry in snapshot["inventory"]}
    assert inventory["me/app"]["decided_by"] == "person"
    assert inventory["me/app"]["reason"] == "Sandbox, not the audited system."
    assert inventory["me/forked"]["decided_by"] == "person"


async def test_an_archived_repository_stays_out_whatever_anyone_decided() -> None:
    snapshot = await _collect(_OLD, decisions={"3": github.ScopeDecision("in_scope")})
    assert snapshot["repositories"] == []
    assert snapshot["inventory"][0]["decided_by"] == "system"


# -- what a review proves: who, when, on which version (F03) -----------------------


def _change(
    *reviews: tuple[str, str, str, str],
    author: str = "alice",
    merged_at: str = "2026-10-01T12:00:00Z",
    head: str = "c2",
) -> dict[str, Any]:
    """A merged change with reviews given as (user, state, submitted_at, commit)."""
    return {
        "number": 9,
        "author": author,
        "merged_at": merged_at,
        "head_sha": head,
        "reviews": [
            {"user": user, "state": state, "submitted_at": at, "commit_id": commit}
            for user, state, at, commit in reviews
        ],
    }


def _merged(*changes: dict[str, Any], complete: bool = True) -> dict[str, Any]:
    return {"state": "ok", "total": len(changes), "items": list(changes), "complete": complete}


def _review_result(repo: dict[str, Any]) -> Any:  # noqa: ANN401 — a Result
    return next(
        r for r in github.evaluate(_snapshot(repo)) if r.check_key == github.MERGED_CHANGES_REVIEWED
    )


def test_an_approval_given_after_the_merge_reviewed_nothing_that_was_merged() -> None:
    late = _change(("carol", "APPROVED", "2026-10-01T13:00:00Z", "c2"))
    result = _review_result(_repo("api", merged_changes=_merged(late)))
    assert result.outcome == "fail"
    assert result.detail["unreviewed"] == [9]


def test_a_later_changes_requested_withdraws_an_earlier_approval() -> None:
    withdrawn = _change(
        ("carol", "APPROVED", "2026-10-01T10:00:00Z", "c1"),
        ("carol", "CHANGES_REQUESTED", "2026-10-01T11:00:00Z", "c2"),
    )
    assert _review_result(_repo("api", merged_changes=_merged(withdrawn))).outcome == "fail"


def test_another_reviewers_approval_stands_beside_a_withdrawn_one() -> None:
    change = _change(
        ("carol", "CHANGES_REQUESTED", "2026-10-01T10:00:00Z", "c2"),
        ("dan", "APPROVED", "2026-10-01T11:00:00Z", "c2"),
    )
    assert _review_result(_repo("api", merged_changes=_merged(change))).outcome == "pass"


def test_a_dismissed_approval_is_gone() -> None:
    dismissed = _change(
        ("carol", "APPROVED", "2026-10-01T10:00:00Z", "c1"),
        ("carol", "DISMISSED", "2026-10-01T11:00:00Z", "c1"),
    )
    assert _review_result(_repo("api", merged_changes=_merged(dismissed))).outcome == "fail"


def test_the_author_cannot_approve_their_own_change() -> None:
    own = _change(("alice", "APPROVED", "2026-10-01T10:00:00Z", "c2"))
    assert _review_result(_repo("api", merged_changes=_merged(own))).outcome == "fail"


def test_comments_are_not_approval() -> None:
    comment = _change(("carol", "COMMENTED", "2026-10-01T10:00:00Z", "c2"))
    assert _review_result(_repo("api", merged_changes=_merged(comment))).outcome == "fail"


def test_an_approval_of_an_earlier_commit_counts_but_the_evidence_says_so() -> None:
    earlier = _change(("carol", "APPROVED", "2026-10-01T10:00:00Z", "c1"), head="c2")
    result = _review_result(_repo("api", merged_changes=_merged(earlier)))
    assert result.outcome == "pass"
    assert result.detail["approved_earlier_commit"] == [9]
    assert "approved before a later commit" in result.detail["summary"]


def test_reviews_that_could_not_be_read_are_unknown_not_unreviewed() -> None:
    blind = {"number": 9, "author": "alice", "merged_at": "2026-10-01T12:00:00Z", "reviews": None}
    assert _review_result(_repo("api", merged_changes=_merged(blind))).outcome == "error"


def test_a_population_cut_short_is_not_reported_as_every_change_reviewed() -> None:
    good = _change(("carol", "APPROVED", "2026-10-01T10:00:00Z", "c2"))
    result = _review_result(_repo("api", merged_changes=_merged(good, complete=False)))
    assert result.outcome == "pass"
    assert result.detail["complete"] is False
    assert "More were merged than could be read" in result.detail["summary"]
    assert not result.detail["summary"].startswith("All ")


def test_an_unreviewed_change_fails_even_when_the_population_is_cut_short() -> None:
    bad = _change()
    assert (
        _review_result(_repo("api", merged_changes=_merged(bad, complete=False))).outcome == "fail"
    )


# -- policy that could not be read is never a failure (F05) -------------------------


def test_an_unreadable_ruleset_with_no_classic_protection_is_error_not_fail() -> None:
    repo = _repo(
        "api", protection={"state": "absent"}, rules={"state": "unreadable", "reason": "403"}
    )
    outcomes = _outcomes(_snapshot(repo))
    for key in (
        github.DEFAULT_BRANCH_PROTECTED,
        github.REVIEW_REQUIRED,
        github.STATUS_CHECKS_REQUIRED,
    ):
        assert outcomes[(key, "acme/api")] == "error", key


def test_an_unreadable_ruleset_does_not_undo_protection_that_was_read() -> None:
    repo = _repo("api", rules={"state": "unreadable", "reason": "403"})
    outcomes = _outcomes(_snapshot(repo))
    assert outcomes[(github.DEFAULT_BRANCH_PROTECTED, "acme/api")] == "pass"
    assert outcomes[(github.REVIEW_REQUIRED, "acme/api")] == "pass"


def test_a_weak_classic_rule_beside_an_unreadable_ruleset_is_unknown() -> None:
    repo = _repo(
        "api",
        protection={
            "state": "present",
            "data": {
                "allow_force_pushes": {"enabled": False},
                "required_status_checks": {"contexts": ["ci"]},
            },
        },
        rules={"state": "unreadable", "reason": "403"},
    )
    assert _outcomes(_snapshot(repo))[(github.DEFAULT_BRANCH_PROTECTED, "acme/api")] == "error"


def test_an_absence_that_was_fully_readable_is_still_a_failure() -> None:
    repo = _repo("api", protection={"state": "absent"}, rules={"state": "present", "data": []})
    outcomes = _outcomes(_snapshot(repo))
    for key in (
        github.DEFAULT_BRANCH_PROTECTED,
        github.REVIEW_REQUIRED,
        github.STATUS_CHECKS_REQUIRED,
    ):
        assert outcomes[(key, "acme/api")] == "fail", key


def test_force_pushes_cannot_be_ruled_out_when_the_rules_are_unreadable() -> None:
    repo = _repo("api", rules={"state": "unreadable", "reason": "403"})
    repo["protection"]["data"]["allow_force_pushes"] = {"enabled": True}
    assert _outcomes(_snapshot(repo))[(github.DEFAULT_BRANCH_PROTECTED, "acme/api")] == "error"


# -- what the result leaves visible (F04, F07, F14) ---------------------------------


def test_administrators_who_can_bypass_the_rule_are_said_so() -> None:
    repo = _repo("api")
    repo["protection"]["data"]["enforce_admins"] = {"enabled": False}
    result = next(
        r
        for r in github.evaluate(_snapshot(repo))
        if r.check_key == github.DEFAULT_BRANCH_PROTECTED
    )
    assert result.outcome == "pass"
    assert result.detail["admins_can_bypass"] is True
    assert "Administrators can bypass it" in result.detail["summary"]
    repo["protection"]["data"]["enforce_admins"] = {"enabled": True}
    enforced = next(
        r
        for r in github.evaluate(_snapshot(repo))
        if r.check_key == github.DEFAULT_BRANCH_PROTECTED
    )
    assert enforced.detail["admins_can_bypass"] is False


def test_repositories_past_the_limit_are_an_explicit_gap_on_every_per_repository_check() -> None:
    snapshot = _snapshot(_repo("api"))
    snapshot["repositories_truncated"] = 12
    gaps = [
        r
        for r in github.evaluate(snapshot)
        if r.resource_id == "acme" and r.check_key != github.ORG_TWO_FACTOR_REQUIRED
    ]
    assert {r.check_key for r in gaps} == {
        key for key in github.IMPLEMENTED if key != github.ORG_TWO_FACTOR_REQUIRED
    }
    assert {r.outcome for r in gaps} == {"error"}
    assert "12 repositories in scope were not read" in gaps[0].detail["summary"]


def test_every_result_names_the_rules_that_judged_it() -> None:
    results = github.evaluate(_snapshot(_repo("api")))
    assert {r.detail["rule"] for r in results} == {github.EVALUATOR}


# -- collection: reviews in full, and whether the population was complete (F03, F06) --


def _pull(number: int, *, merged: str = "2026-10-02T09:00:00Z") -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Change {number}",
        "user": {"login": "alice"},
        "merged_at": merged,
        "updated_at": merged,
        "html_url": f"https://github.com/acme/api/pull/{number}",
        "head": {"sha": f"sha{number}"},
    }


async def _collect_merged(pulls: list[dict[str, Any]], reviews: dict[int, Any]) -> dict[str, Any]:
    def respond(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/api/pulls":
            page = int(request.url.params.get("page", "1"))
            size = int(request.url.params.get("per_page", "30"))
            chunk = pulls[(page - 1) * size : page * size]
            headers = {}
            if page * size < len(pulls):
                following = (
                    f"https://api.github.test/repos/acme/api/pulls?page={page + 1}&per_page={size}"
                )
                headers["link"] = f'<{following}>; rel="next"'
            return httpx.Response(200, json=chunk, headers=headers)
        number = int(path.split("/")[-2])
        return httpx.Response(200, json=reviews[number])

    http = ProviderHttp(
        "https://api.github.test",
        headers={},
        timeout=5,
        transport=httpx.MockTransport(respond),
        sleep=_no_wait,
    )
    async with http:
        return await github._merged_changes(
            http, "acme/api", "main", datetime(2026, 9, 1, tzinfo=UTC)
        )


async def test_the_collector_keeps_who_decided_what_and_when() -> None:
    reviews = {
        1: [
            {
                "user": {"login": "carol"},
                "state": "APPROVED",
                "submitted_at": "2026-10-02T08:00:00Z",
                "commit_id": "sha1",
            },
            {
                "user": {"login": "dan"},
                "state": "PENDING",
                "submitted_at": None,
                "commit_id": "sha1",
            },
        ]
    }
    merged = await _collect_merged([_pull(1)], reviews)
    assert merged["complete"] is True
    [item] = merged["items"]
    assert item["head_sha"] == "sha1"
    assert item["reviews"] == [
        {
            "user": "carol",
            "state": "APPROVED",
            "submitted_at": "2026-10-02T08:00:00Z",
            "commit_id": "sha1",
        }
    ]


async def test_the_collector_says_when_more_was_merged_than_it_read() -> None:
    count = github.MAX_MERGED_PER_REPOSITORY + 1
    pulls = [_pull(n) for n in range(1, count + 1)]
    reviews: dict[int, Any] = {n: [] for n in range(1, count + 1)}
    merged = await _collect_merged(pulls, reviews)
    assert merged["total"] == count
    assert len(merged["items"]) == github.MAX_MERGED_PER_REPOSITORY
    assert merged["complete"] is False


def test_changes_skipped_for_the_request_allowance_are_a_gap_not_a_failure() -> None:
    good = _change(("carol", "APPROVED", "2026-10-01T10:00:00Z", "c2"))
    skipped = {"number": 10, "author": "alice", "reviews": None, "skipped": True}
    result = _review_result(_repo("api", merged_changes=_merged(good, skipped)))
    assert result.outcome == "pass"
    assert result.detail["complete"] is False
    assert result.detail["sampled"] == 1
    assert "More were merged than could be read" in result.detail["summary"]


def test_nothing_read_because_the_allowance_ran_low_is_error_not_pass() -> None:
    skipped = {"number": 10, "author": "alice", "reviews": None, "skipped": True}
    result = _review_result(_repo("api", merged_changes=_merged(skipped)))
    assert result.outcome == "error"
    assert "request allowance" in result.detail["summary"]


def test_a_failed_read_of_one_change_is_still_unknown() -> None:
    good = _change(("carol", "APPROVED", "2026-10-01T10:00:00Z", "c2"))
    blind = {"number": 10, "author": "alice", "merged_at": "2026-10-01T12:00:00Z", "reviews": None}
    assert _review_result(_repo("api", merged_changes=_merged(good, blind))).outcome == "error"
