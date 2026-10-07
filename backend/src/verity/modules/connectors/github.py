"""GitHub: read only collection, and the version control checks it evaluates.

Collect first, evaluate second. ``collect`` reads what the checks need into one
plain snapshot, which is also the evidence file an auditor downloads.
``evaluate`` is a pure function of that snapshot, so every pass and fail rule is
tested without a network (docs/architecture/integrations.md: recorded fixtures,
never a live account in CI).

Access, read only (fine grained personal access token):
- Repository permissions: Metadata, Administration, Pull requests.
- Organization permissions: Administration, for the two factor check only.
A permission the token lacks turns the checks that need it into ``error``, never
``fail`` (rule 7). See README.md in this package.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Final
from urllib.parse import quote

from verity.modules.connectors.http import (
    AccessDenied,
    NotFoundError,
    ProviderError,
    ProviderHttp,
)

API_VERSION: Final = "2022-11-28"
REVIEW_WINDOW_DAYS: Final = 30
MAX_REPOSITORIES: Final = 300
MAX_MERGED_PER_REPOSITORY: Final = 100
_PULL_PAGES: Final = 10
_PULL_PAGE_SIZE: Final = 50
_REVIEW_PAGES: Final = 3
_REPO_CONCURRENCY: Final = 4
EVALUATOR: Final = "github.2026-10"
"""Which rules judged a result. Definitions can be reworded later; a stored result
keeps the name of the rules that produced it, so it is never silently reinterpreted."""
_RATE_LIMIT_FLOOR: Final = 100
_PROTECTING_RULES: Final = frozenset({"pull_request", "update"})

DEFAULT_BRANCH_PROTECTED: Final = "vcs.default_branch_protected"
REVIEW_REQUIRED: Final = "vcs.review_required"
STATUS_CHECKS_REQUIRED: Final = "vcs.status_checks_required"
MERGED_CHANGES_REVIEWED: Final = "vcs.merged_changes_reviewed"
SECRET_SCANNING_ENABLED: Final = "vcs.secret_scanning_enabled"  # noqa: S105 — a check key
DEPENDENCY_ALERTS_ENABLED: Final = "vcs.dependency_alerts_enabled"
ORG_TWO_FACTOR_REQUIRED: Final = "vcs.org_two_factor_required"

IMPLEMENTED: Final[tuple[str, ...]] = (
    DEFAULT_BRANCH_PROTECTED,
    REVIEW_REQUIRED,
    STATUS_CHECKS_REQUIRED,
    MERGED_CHANGES_REVIEWED,
    SECRET_SCANNING_ENABLED,
    DEPENDENCY_ALERTS_ENABLED,
    ORG_TWO_FACTOR_REQUIRED,
)

_NEEDS_ADMIN_READ: Final = "Grant the token Administration read access, then run again."


def headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "Verity-GRC",
    }


@dataclass(frozen=True, slots=True)
class Account:
    """Who a token reaches, read when a workspace connects."""

    login: str
    account_type: str
    display_name: str
    token_expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ScopeDecision:
    """A person's decision about one repository (AU-9).

    Only a person's decision is carried in. What the collector derives for itself
    (an archived repository, a fork) is recomputed on every run, so a repository
    that is un-archived comes back into scope without anyone remembering to say so.
    """

    scope: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Result:
    """One check on one resource. ``detail['summary']`` is the sentence people read."""

    check_key: str
    resource_type: str
    resource_id: str
    resource_name: str
    outcome: str
    detail: dict[str, Any] = field(default_factory=dict)


def _parse_expiry(value: str | None) -> datetime | None:
    """GitHub sends fine grained token expiry as ``2026-12-01 00:00:00 UTC``."""
    if not value:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S %z"):
        try:
            parsed = datetime.strptime(value.strip(), pattern)  # noqa: DTZ007 — zone handled below
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _when(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _repos_path(account: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    if account["type"] == "organization":
        return f"/orgs/{quote(account['login'])}/repos", {"type": "all", "per_page": 100}
    return "/user/repos", {"affiliation": "owner", "per_page": 100}


async def inspect(http: ProviderHttp, account: str | None) -> Account:
    """Confirm the token works and resolve the account it will read.

    Raises the shared provider errors; the service turns them into messages.
    """
    user = await http.get_json("/user")
    expiry = _parse_expiry(
        http.last_response.headers.get("github-authentication-token-expiration")
        if http.last_response is not None
        else None
    )
    wanted = (account or "").strip()
    if wanted and wanted.lower() != str(user["login"]).lower():
        org = await http.get_json(f"/orgs/{quote(wanted)}")
        resolved = Account(org["login"], "organization", org.get("name") or org["login"], expiry)
    else:
        resolved = Account(user["login"], "user", user.get("name") or user["login"], expiry)
    path, params = _repos_path({"login": resolved.login, "type": resolved.account_type})
    await http.get(path, {**params, "per_page": 1})
    return resolved


# -- collection ------------------------------------------------------------------


async def _probe(http: ProviderHttp, path: str) -> dict[str, Any]:
    """Read one optional setting: present, absent (404) or unreadable (403).

    A 204 (Dependabot alerts on) is present with no body.
    """
    try:
        response = await http.get(path)
    except NotFoundError as exc:
        # "Branch not found" is a repository with no commits yet, which is not the
        # same finding as "Branch not protected".
        if "branch not found" in exc.provider_message.lower():
            return {"state": "absent", "reason": "no_branch"}
        return {"state": "absent"}
    except AccessDenied as exc:
        # Free plans answer 403 for protection on private repositories: the
        # branch cannot be protected, which is a finding with its own remedy, not
        # a permission gap.
        if "upgrade to github pro" in exc.provider_message.lower():
            return {"state": "absent", "reason": "plan"}
        return {"state": "unreadable", "reason": str(exc)}
    except ProviderError as exc:
        return {"state": "unreadable", "reason": str(exc)}
    return {"state": "present", "data": response.json() if response.content else None}


async def _reviews(http: ProviderHttp, full_name: str, number: int) -> list[dict[str, Any]] | None:
    """Every submitted review of one pull request, in the order GitHub lists them.

    Only what the evaluation needs is kept: who, what they decided, when, and on
    which commit. A review is a person's decision at a moment, so the moment and the
    commit are part of what it proves.
    """
    try:
        reviews = [
            review
            async for review in http.paginate(
                f"/repos/{full_name}/pulls/{number}/reviews",
                {"per_page": 100},
                max_pages=_REVIEW_PAGES,
            )
        ]
    except ProviderError:
        return None
    return [
        {
            "user": (review.get("user") or {}).get("login"),
            "state": review.get("state"),
            "submitted_at": review.get("submitted_at"),
            "commit_id": review.get("commit_id"),
        }
        for review in reviews
        if review.get("state") != "PENDING"
    ]


async def _merged_changes(
    http: ProviderHttp, full_name: str, branch: str, since: datetime
) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    reached_window = False
    seen = 0
    try:
        async for pull in http.paginate(
            f"/repos/{full_name}/pulls",
            {
                "state": "closed",
                "base": branch,
                "sort": "updated",
                "direction": "desc",
                "per_page": _PULL_PAGE_SIZE,
            },
            max_pages=_PULL_PAGES,
        ):
            seen += 1
            updated = _when(pull.get("updated_at"))
            if updated is not None and updated < since:
                reached_window = True
                break
            merged_at = _when(pull.get("merged_at"))
            if merged_at is not None and merged_at >= since:
                merged.append(pull)
    except ProviderError as exc:
        return {"state": "unreadable", "reason": str(exc), "items": [], "total": 0}

    items: list[dict[str, Any]] = []
    for pull in merged[:MAX_MERGED_PER_REPOSITORY]:
        item: dict[str, Any] = {
            "number": pull["number"],
            "title": pull.get("title", ""),
            "author": (pull.get("user") or {}).get("login"),
            "merged_at": pull.get("merged_at"),
            "head_sha": (pull.get("head") or {}).get("sha"),
            "url": pull.get("html_url"),
            "reviews": None,
        }
        remaining = http.rate_limit_remaining
        if remaining is None or remaining > _RATE_LIMIT_FLOOR:
            item["reviews"] = await _reviews(http, full_name, pull["number"])
        else:
            # The request allowance is nearly spent, so this change was not read. That
            # is a gap in coverage, which the result states, not a failure to read.
            item["skipped"] = True
        items.append(item)
    # The population is complete only if every merged change in the window was found
    # (the page limit was not hit before the window ended) and every one was read.
    found_all = reached_window or seen < _PULL_PAGES * _PULL_PAGE_SIZE
    return {
        "state": "ok",
        "items": items,
        "total": len(merged),
        "complete": found_all and len(merged) <= MAX_MERGED_PER_REPOSITORY,
    }


async def _collect_repository(
    http: ProviderHttp, repo: Mapping[str, Any], since: datetime
) -> dict[str, Any]:
    full_name = repo["full_name"]
    branch = repo.get("default_branch") or "main"
    encoded = quote(branch, safe="")
    security = repo.get("security_and_analysis")
    if security is None:
        try:
            security = (await http.get_json(f"/repos/{full_name}")).get("security_and_analysis")
        except ProviderError:
            security = None

    alerts = await _probe(http, f"/repos/{full_name}/vulnerability-alerts")
    return {
        "id": str(repo["id"]),
        "full_name": full_name,
        "url": repo.get("html_url"),
        "private": bool(repo.get("private")),
        "fork": bool(repo.get("fork")),
        # Whether the token holds admin on this repository, which is what tells a
        # plan that does not offer a setting apart from a token that cannot read it.
        "admin": (repo.get("permissions") or {}).get("admin"),
        "default_branch": branch,
        "security_and_analysis": security,
        "protection": await _probe(http, f"/repos/{full_name}/branches/{encoded}/protection"),
        "rules": await _probe(http, f"/repos/{full_name}/rules/branches/{encoded}"),
        # 204 when on; the probe records a successful empty body as present.
        "vulnerability_alerts": {
            "present": "enabled",
            "absent": "disabled",
        }.get(alerts["state"], "unreadable"),
        "merged_changes": await _merged_changes(http, full_name, branch, since),
    }


def _default_scope(repo: Mapping[str, Any]) -> tuple[str, str | None]:
    """What the collector decides for itself, before any person has a say."""
    if repo.get("archived"):
        return "excluded", "Archived, so nothing in it can change."
    if repo.get("fork"):
        return "excluded", "A fork of another repository, so the code is not this account's own."
    return "in_scope", None


def _inventory_entry(repo: Mapping[str, Any], decision: ScopeDecision | None) -> dict[str, Any]:
    scope, reason = _default_scope(repo)
    decided_by = "system"
    # An archived repository stays out whatever anyone decided: it cannot change.
    if decision is not None and not repo.get("archived"):
        scope, reason, decided_by = decision.scope, decision.reason, "person"
    return {
        "id": str(repo["id"]),
        "full_name": repo["full_name"],
        "url": repo.get("html_url"),
        "private": bool(repo.get("private")),
        "fork": bool(repo.get("fork")),
        "archived": bool(repo.get("archived")),
        "default_branch": repo.get("default_branch"),
        "scope": scope,
        "reason": reason,
        "decided_by": decided_by,
    }


async def collect(
    http: ProviderHttp,
    *,
    login: str,
    account_type: str,
    now: datetime,
    decisions: Mapping[str, ScopeDecision] | None = None,
) -> dict[str, Any]:
    """Read everything the checks need, once, into a snapshot.

    Only repositories in scope are read in depth. Every repository the token can
    see is still listed in ``inventory`` with its scope and the reason, so the
    evidence says what was left out and why (AU-9).

    Raises the shared provider errors only when the account itself cannot be
    read; anything narrower is recorded per repository as unreadable.
    """
    account: dict[str, Any] = {"login": login, "type": account_type, "two_factor_required": None}
    if account_type == "organization":
        org = await http.get_json(f"/orgs/{quote(login)}")
        account["two_factor_required"] = org.get("two_factor_requirement_enabled")
        account["name"] = org.get("name") or login

    path, params = _repos_path(account)
    # One page past the cap, so a truncated inventory is visible rather than silent.
    pages = MAX_REPOSITORIES // 100 + 1
    listed = [repo async for repo in http.paginate(path, params, max_pages=pages)]
    chosen = decisions or {}
    inventory = [_inventory_entry(repo, chosen.get(str(repo["id"]))) for repo in listed]
    in_scope_ids = {entry["id"] for entry in inventory if entry["scope"] == "in_scope"}
    active = [repo for repo in listed if str(repo["id"]) in in_scope_ids]
    since = now - timedelta(days=REVIEW_WINDOW_DAYS)

    gate = asyncio.Semaphore(_REPO_CONCURRENCY)

    async def one(repo: Mapping[str, Any]) -> dict[str, Any]:
        async with gate:
            return await _collect_repository(http, repo, since)

    repositories = await asyncio.gather(*(one(repo) for repo in active[:MAX_REPOSITORIES]))
    return {
        "provider": "github",
        "evaluator": EVALUATOR,
        "collected_at": now.isoformat(),
        "account": account,
        "window_days": REVIEW_WINDOW_DAYS,
        "repositories_listed": len(listed),
        "repositories_archived": sum(1 for repo in listed if repo.get("archived")),
        "repositories_excluded": len(listed) - len(active),
        # No silent caps: a truncated inventory says so in the evidence itself.
        "repositories_truncated": max(0, len(active) - MAX_REPOSITORIES),
        "inventory": sorted(inventory, key=lambda entry: entry["full_name"].lower()),
        "repositories": sorted(repositories, key=lambda repo: repo["full_name"].lower()),
    }


# -- evaluation (pure) -------------------------------------------------------------


def _repo_result(
    repo: Mapping[str, Any], key: str, outcome: str, summary: str, **extra: object
) -> Result:
    return Result(
        check_key=key,
        resource_type="repository",
        resource_id=repo["id"],
        resource_name=repo["full_name"],
        outcome=outcome,
        detail={
            "summary": summary,
            "branch": repo["default_branch"],
            "url": repo.get("url"),
            "rule": EVALUATOR,
            **extra,
        },
    )


def _unknown_policy(repo: Mapping[str, Any]) -> bool:
    """Whether a source of branch policy could not be read.

    A branch can be protected by classic protection, by a ruleset, or both. When one
    of them is unreadable, a repository that looks unprotected from the other may
    simply be protected by the one nobody could see, and saying "fails" about a
    setting Verity could not read is the mistake rule 7 exists to prevent.
    """
    return bool(
        repo["protection"]["state"] == "unreadable" or repo["rules"]["state"] == "unreadable"
    )


def _fail_or_unknown(repo: Mapping[str, Any], key: str, summary: str, **extra: object) -> Result:
    """A finding that holds only if every source of policy was readable."""
    if _unknown_policy(repo):
        return _repo_result(
            repo,
            key,
            "error",
            f"Branch protection or rules could not be read. {_NEEDS_ADMIN_READ}",
        )
    return _repo_result(repo, key, "fail", summary, **extra)


def _plan_summary(repo: Mapping[str, Any], feature: str) -> str:
    """The sentence for a repository whose plan does not offer a setting, with the ways out.

    A private repository on a free plan is the usual case. Making it public is only
    offered for a private one, and leaving it out of the audit, which is the way out for a
    repository that is not part of the audited system, is always offered. The word
    "plan" stays in the sentence: the panel groups these results by their ``reason``, and
    people search for the word.
    """
    private = bool(repo.get("private"))
    where = "this private repository" if private else "this repository"
    ways = "Upgrade the plan, make the repository public" if private else "Upgrade the plan"
    return (
        f"GitHub does not offer {feature} for {where} on its current plan. "
        f"{ways}, or exclude it with a reason."
    )


def _plan_limited(repo: Mapping[str, Any]) -> bool:
    return bool(repo["protection"].get("reason") == "plan")


def _empty(repo: Mapping[str, Any]) -> bool:
    """A repository with no commits has no branch to protect or review."""
    return bool(repo["protection"].get("reason") == "no_branch")


def _rules(repo: Mapping[str, Any]) -> list[dict[str, Any]]:
    rules = repo["rules"]
    return list(rules.get("data") or []) if rules["state"] == "present" else []


def _classic(repo: Mapping[str, Any]) -> dict[str, Any] | None:
    protection = repo["protection"]
    return protection.get("data") or {} if protection["state"] == "present" else None


def _blocks_direct_pushes(classic: Mapping[str, Any] | None, rule_types: set[Any]) -> bool:
    """Whether a change can reach the branch only by going through review.

    Protection that merely stops deletions or force pushes still lets anyone with
    write access push straight to the branch, so it does not count: the control is
    about changes being reviewed, and a branch that takes direct pushes is not.
    """
    if classic is not None and (
        classic.get("required_pull_request_reviews")
        or classic.get("restrictions")
        or (classic.get("lock_branch") or {}).get("enabled")
    ):
        return True
    return bool(rule_types & _PROTECTING_RULES)


def _protected(repo: Mapping[str, Any]) -> Result:
    branch = repo["default_branch"]
    classic = _classic(repo)
    rule_types = {rule.get("type") for rule in _rules(repo)}
    if (
        classic is not None
        and bool((classic.get("allow_force_pushes") or {}).get("enabled"))
        and "non_fast_forward" not in rule_types
    ):
        return _fail_or_unknown(
            repo,
            DEFAULT_BRANCH_PROTECTED,
            f"{branch} is protected but allows force pushes.",
        )
    if _blocks_direct_pushes(classic, rule_types):
        summary = (
            f"{branch} is protected." if classic is not None else f"A ruleset protects {branch}."
        )
        # Whether administrators can still bypass the rule is what an auditor asks
        # next. Classic protection says so; a ruleset's bypass list is not read.
        bypass = (
            None
            if classic is None
            else (classic.get("enforce_admins") or {}).get("enabled") is False
        )
        if bypass:
            summary += " Administrators can bypass it."
        return _repo_result(
            repo, DEFAULT_BRANCH_PROTECTED, "pass", summary, admins_can_bypass=bypass
        )
    if classic is not None or rule_types:
        return _fail_or_unknown(
            repo,
            DEFAULT_BRANCH_PROTECTED,
            f"{branch} has protection rules but still accepts direct pushes. "
            "Require a pull request.",
        )
    if _plan_limited(repo):
        return _repo_result(
            repo,
            DEFAULT_BRANCH_PROTECTED,
            "fail",
            _plan_summary(repo, "branch protection"),
            reason="plan",
        )
    return _fail_or_unknown(
        repo,
        DEFAULT_BRANCH_PROTECTED,
        f"{branch} accepts direct pushes. Protect it or add a ruleset.",
    )


def _reviews_required(repo: Mapping[str, Any]) -> Result:
    classic = _classic(repo)
    counts = [0]
    if classic is not None:
        counts.append(
            int(
                (classic.get("required_pull_request_reviews") or {}).get(
                    "required_approving_review_count", 0
                )
            )
        )
    counts += [
        int((rule.get("parameters") or {}).get("required_approving_review_count", 0))
        for rule in _rules(repo)
        if rule.get("type") == "pull_request"
    ]
    required = max(counts)
    if required >= 1:
        noun = "review" if required == 1 else "reviews"
        reviews = (classic or {}).get("required_pull_request_reviews") or {}
        return _repo_result(
            repo,
            REVIEW_REQUIRED,
            "pass",
            f"{required} approving {noun} required to merge.",
            required=required,
            dismiss_stale=reviews.get("dismiss_stale_reviews"),
            last_push_approval=reviews.get("require_last_push_approval"),
        )
    if _plan_limited(repo):
        return _repo_result(
            repo,
            REVIEW_REQUIRED,
            "fail",
            _plan_summary(repo, "branch protection, which is what requires reviews"),
            required=0,
            reason="plan",
        )
    return _fail_or_unknown(
        repo, REVIEW_REQUIRED, "Changes can merge without an approving review.", required=0
    )


def _status_checks(repo: Mapping[str, Any]) -> Result:
    classic = _classic(repo)
    if classic is not None:
        required = classic.get("required_status_checks") or {}
        if required.get("contexts") or required.get("checks"):
            return _repo_result(
                repo, STATUS_CHECKS_REQUIRED, "pass", "Required checks must pass before merge."
            )
    for rule in _rules(repo):
        if rule.get("type") == "required_status_checks" and (rule.get("parameters") or {}).get(
            "required_status_checks"
        ):
            return _repo_result(
                repo, STATUS_CHECKS_REQUIRED, "pass", "A ruleset requires checks to pass."
            )
    if _plan_limited(repo):
        return _repo_result(
            repo,
            STATUS_CHECKS_REQUIRED,
            "fail",
            _plan_summary(repo, "branch protection, which is what requires status checks"),
            reason="plan",
        )
    return _fail_or_unknown(
        repo, STATUS_CHECKS_REQUIRED, "Nothing has to pass before a change merges."
    )


def _secret_scanning(repo: Mapping[str, Any]) -> Result:
    security = repo.get("security_and_analysis")
    if security is None:
        # With admin on the repository the setting is simply not there, which means
        # the plan does not offer it. Without admin the token cannot see it.
        if repo.get("admin") is True:
            return _repo_result(
                repo,
                SECRET_SCANNING_ENABLED,
                "fail",
                _plan_summary(repo, "secret scanning"),
                reason="plan",
            )
        return _repo_result(
            repo,
            SECRET_SCANNING_ENABLED,
            "error",
            f"Security settings could not be read. {_NEEDS_ADMIN_READ}",
        )
    if (security.get("secret_scanning") or {}).get("status") == "enabled":
        return _repo_result(repo, SECRET_SCANNING_ENABLED, "pass", "Secret scanning is on.")
    return _repo_result(repo, SECRET_SCANNING_ENABLED, "fail", "Secret scanning is off.")


def _dependency_alerts(repo: Mapping[str, Any]) -> Result:
    state = repo["vulnerability_alerts"]
    if state == "enabled":
        return _repo_result(repo, DEPENDENCY_ALERTS_ENABLED, "pass", "Dependabot alerts are on.")
    if state == "disabled":
        return _repo_result(repo, DEPENDENCY_ALERTS_ENABLED, "fail", "Dependabot alerts are off.")
    return _repo_result(
        repo,
        DEPENDENCY_ALERTS_ENABLED,
        "error",
        f"Dependabot settings could not be read. {_NEEDS_ADMIN_READ}",
    )


def _effective_approvers(item: Mapping[str, Any]) -> tuple[list[str] | None, list[str]]:
    """Who had approved a merged change at the moment it merged, and who approved a
    version that was later changed.

    Only the last decision each reviewer made before the merge counts. An approval
    given after the merge reviewed nothing that was merged, one withdrawn by a later
    "changes requested" no longer stands, and a dismissed one is gone. The author
    cannot approve their own change.

    ``None`` when the reviews could not be read. The second list names reviewers
    whose approval was of an earlier commit than the one that merged: it still
    counts, because GitHub does not require otherwise unless a repository asks it to,
    but the evidence says so.
    """
    if "reviews" not in item:  # a snapshot taken before reviews were kept in full
        return item.get("approvers"), []
    reviews = item["reviews"]
    if reviews is None:
        return None, []
    merged_at = _when(item.get("merged_at"))
    latest: dict[str, Mapping[str, Any]] = {}
    ordered = sorted(
        (r for r in reviews if r.get("user") and r.get("submitted_at")),
        key=lambda r: str(r["submitted_at"]),
    )
    for review in ordered:
        submitted = _when(review["submitted_at"])
        if review["user"] == item.get("author") or (
            merged_at is not None and submitted is not None and submitted > merged_at
        ):
            continue
        if review.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[str(review["user"])] = review
    approved = {user: r for user, r in latest.items() if r.get("state") == "APPROVED"}
    head = item.get("head_sha")
    earlier = sorted(
        user for user, r in approved.items() if head and r.get("commit_id") not in (None, head)
    )
    return sorted(approved), earlier


def _merged_reviewed(repo: Mapping[str, Any]) -> Result:
    changes = repo["merged_changes"]
    branch = repo["default_branch"]
    key = MERGED_CHANGES_REVIEWED
    if changes["state"] != "ok":
        return _repo_result(
            repo,
            key,
            "error",
            "Merged changes could not be read. Grant the token Pull requests read access.",
        )
    items = changes["items"]
    total = changes["total"]
    if total == 0:
        return _repo_result(
            repo,
            key,
            "not_applicable",
            f"Nothing merged into {branch} in the last {REVIEW_WINDOW_DAYS} days.",
            sampled=0,
            total=0,
            complete=True,
        )
    read = [item for item in items if not item.get("skipped")]
    if not read:
        return _repo_result(
            repo,
            key,
            "error",
            "Reviews could not be read: the provider's request allowance ran low. "
            "The next run will try again.",
            sampled=0,
            total=total,
            complete=False,
        )
    judged = {item["number"]: _effective_approvers(item) for item in read}
    unreviewed = [n for n, (approvers, _earlier) in judged.items() if approvers == []]
    unknown = [n for n, (approvers, _earlier) in judged.items() if approvers is None]
    earlier = [n for n, (_approvers, stale) in judged.items() if stale]
    complete = bool(changes.get("complete", len(items) >= total)) and len(read) == len(items)
    extra: dict[str, object] = {
        "sampled": len(read),
        "total": total,
        "complete": complete,
        "approved_earlier_commit": earlier,
    }
    scope = f"{total}" if complete else f"{len(read)} read of {total}"
    if unreviewed:
        outcome = "fail"
        summary = (
            f"{len(unreviewed)} of {scope} merged changes had no approving review "
            "before they merged."
        )
        extra["unreviewed"] = unreviewed
    elif unknown:
        outcome = "error"
        summary = f"Reviews could not be read for {len(unknown)} merged changes."
        extra["unknown"] = unknown
    else:
        outcome = "pass"
        note = ""
        if len(earlier) > 1:
            note = f" {len(earlier)} were approved before later commits."
        elif earlier:
            note = " One was approved before a later commit."
        summary = (
            f"All {scope} merged changes had an approving review before they merged.{note}"
            if complete
            else f"None of the {len(read)} merged changes read lacked an approving review. "
            f"More were merged than could be read.{note}"
        )
    return _repo_result(repo, key, outcome, summary, **extra)


def _two_factor(account: Mapping[str, Any]) -> Result:
    login = account["login"]
    base = {"resource_type": "organization", "resource_id": login, "resource_name": login}
    if account["type"] != "organization":
        return Result(
            ORG_TWO_FACTOR_REQUIRED,
            **base,
            outcome="not_applicable",
            detail={
                "summary": "A personal account cannot require two factor for others.",
                "rule": EVALUATOR,
            },
        )
    value = account.get("two_factor_required")
    if value is True:
        return Result(
            ORG_TWO_FACTOR_REQUIRED,
            **base,
            outcome="pass",
            detail={"summary": "Every member must use two factor.", "rule": EVALUATOR},
        )
    if value is False:
        return Result(
            ORG_TWO_FACTOR_REQUIRED,
            **base,
            outcome="fail",
            detail={"summary": "Members can sign in without two factor.", "rule": EVALUATOR},
        )
    return Result(
        ORG_TWO_FACTOR_REQUIRED,
        **base,
        outcome="error",
        detail={
            "summary": "The two factor setting could not be read. Grant the token "
            "Organization Administration read access."
        },
    )


_PER_REPOSITORY: tuple[tuple[str, Callable[[Mapping[str, Any]], Result]], ...] = (
    (DEFAULT_BRANCH_PROTECTED, _protected),
    (REVIEW_REQUIRED, _reviews_required),
    (STATUS_CHECKS_REQUIRED, _status_checks),
    (MERGED_CHANGES_REVIEWED, _merged_reviewed),
    (SECRET_SCANNING_ENABLED, _secret_scanning),
    (DEPENDENCY_ALERTS_ENABLED, _dependency_alerts),
)


def evaluate(snapshot: Mapping[str, Any]) -> list[Result]:
    """Every implemented check against every resource in the snapshot."""
    results = [_two_factor(snapshot["account"])]
    # A population cut short is a gap in what was checked, not a clean result over the
    # part that was read: say so on every per repository check.
    skipped = int(snapshot.get("repositories_truncated") or 0)
    if skipped:
        login = snapshot["account"]["login"]
        results += [
            Result(
                key,
                "organization" if snapshot["account"]["type"] == "organization" else "account",
                login,
                login,
                "error",
                {
                    "summary": f"{skipped} repositories in scope were not read: Verity reads "
                    f"at most {MAX_REPOSITORIES}. Choose which repositories count.",
                    "rule": EVALUATOR,
                },
            )
            for key, _check in _PER_REPOSITORY
        ]
    for repo in snapshot["repositories"]:
        if _empty(repo):
            results += [
                _repo_result(
                    repo, key, "not_applicable", "No commits yet, so there is nothing to check."
                )
                for key, _check in _PER_REPOSITORY
            ]
        else:
            results += [check(repo) for _key, check in _PER_REPOSITORY]
    return results


def unreachable(login: str, account_type: str, reason: str) -> list[Result]:
    """One ``error`` per check when the account itself could not be read.

    The control page then reads "could not check", never "failing" (rule 7).
    """
    resource_type = "organization" if account_type == "organization" else "account"
    return [
        Result(key, resource_type, login, login, "error", {"summary": reason})
        for key in IMPLEMENTED
    ]
