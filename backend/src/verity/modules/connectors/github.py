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
from collections.abc import Mapping
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
MAX_MERGED_PER_REPOSITORY: Final = 20
_REPO_CONCURRENCY: Final = 4
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
    except NotFoundError:
        return {"state": "absent"}
    except AccessDenied as exc:
        # Free plans answer 403 for protection on private repositories: the
        # branch is not protected, which is a finding, not a permission gap.
        if "upgrade to github pro" in exc.provider_message.lower():
            return {"state": "absent", "reason": "The GitHub plan does not offer this."}
        return {"state": "unreadable", "reason": str(exc)}
    except ProviderError as exc:
        return {"state": "unreadable", "reason": str(exc)}
    return {"state": "present", "data": response.json() if response.content else None}


async def _merged_changes(
    http: ProviderHttp, full_name: str, branch: str, since: datetime
) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    try:
        async for pull in http.paginate(
            f"/repos/{full_name}/pulls",
            {
                "state": "closed",
                "base": branch,
                "sort": "updated",
                "direction": "desc",
                "per_page": 50,
            },
            max_pages=4,
        ):
            updated = _when(pull.get("updated_at"))
            if updated is not None and updated < since:
                break
            merged_at = _when(pull.get("merged_at"))
            if merged_at is not None and merged_at >= since:
                merged.append(pull)
    except ProviderError as exc:
        return {"state": "unreadable", "reason": str(exc), "items": [], "total": 0}

    items: list[dict[str, Any]] = []
    for pull in merged[:MAX_MERGED_PER_REPOSITORY]:
        author = (pull.get("user") or {}).get("login")
        item: dict[str, Any] = {
            "number": pull["number"],
            "title": pull.get("title", ""),
            "author": author,
            "merged_at": pull.get("merged_at"),
            "url": pull.get("html_url"),
            "approvers": None,
        }
        remaining = http.rate_limit_remaining
        if remaining is None or remaining > _RATE_LIMIT_FLOOR:
            try:
                reviews = await http.get_json(
                    f"/repos/{full_name}/pulls/{pull['number']}/reviews", {"per_page": 100}
                )
                item["approvers"] = sorted(
                    {
                        review["user"]["login"]
                        for review in reviews
                        if review.get("state") == "APPROVED"
                        and review.get("user")
                        and review["user"].get("login") != author
                    }
                )
            except ProviderError:
                item["approvers"] = None
        items.append(item)
    return {"state": "ok", "items": items, "total": len(merged)}


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


async def collect(
    http: ProviderHttp, *, login: str, account_type: str, now: datetime
) -> dict[str, Any]:
    """Read everything the checks need, once, into a snapshot.

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
    active = [repo for repo in listed if not repo.get("archived")]
    since = now - timedelta(days=REVIEW_WINDOW_DAYS)

    gate = asyncio.Semaphore(_REPO_CONCURRENCY)

    async def one(repo: Mapping[str, Any]) -> dict[str, Any]:
        async with gate:
            return await _collect_repository(http, repo, since)

    repositories = await asyncio.gather(*(one(repo) for repo in active[:MAX_REPOSITORIES]))
    return {
        "provider": "github",
        "collected_at": now.isoformat(),
        "account": account,
        "window_days": REVIEW_WINDOW_DAYS,
        "repositories_listed": len(listed),
        "repositories_archived": len(listed) - len(active),
        # No silent caps: a truncated inventory says so in the evidence itself.
        "repositories_truncated": max(0, len(active) - MAX_REPOSITORIES),
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
            **extra,
        },
    )


def _rules(repo: Mapping[str, Any]) -> list[dict[str, Any]]:
    rules = repo["rules"]
    return list(rules.get("data") or []) if rules["state"] == "present" else []


def _classic(repo: Mapping[str, Any]) -> dict[str, Any] | None:
    protection = repo["protection"]
    return protection.get("data") or {} if protection["state"] == "present" else None


def _protected(repo: Mapping[str, Any]) -> Result:
    branch = repo["default_branch"]
    classic = _classic(repo)
    rule_types = {rule.get("type") for rule in _rules(repo)}
    if classic is not None:
        force_allowed = bool((classic.get("allow_force_pushes") or {}).get("enabled"))
        if force_allowed and "non_fast_forward" not in rule_types:
            return _repo_result(
                repo,
                DEFAULT_BRANCH_PROTECTED,
                "fail",
                f"{branch} is protected but allows force pushes.",
            )
        return _repo_result(repo, DEFAULT_BRANCH_PROTECTED, "pass", f"{branch} is protected.")
    if rule_types & _PROTECTING_RULES:
        return _repo_result(repo, DEFAULT_BRANCH_PROTECTED, "pass", f"A ruleset protects {branch}.")
    if repo["protection"]["state"] == "unreadable":
        return _repo_result(
            repo,
            DEFAULT_BRANCH_PROTECTED,
            "error",
            f"Branch protection could not be read. {_NEEDS_ADMIN_READ}",
        )
    return _repo_result(
        repo,
        DEFAULT_BRANCH_PROTECTED,
        "fail",
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
        return _repo_result(
            repo,
            REVIEW_REQUIRED,
            "pass",
            f"{required} approving {noun} required to merge.",
            required=required,
        )
    if classic is None and repo["protection"]["state"] == "unreadable":
        return _repo_result(
            repo,
            REVIEW_REQUIRED,
            "error",
            f"Review settings could not be read. {_NEEDS_ADMIN_READ}",
        )
    return _repo_result(
        repo, REVIEW_REQUIRED, "fail", "Changes can merge without an approving review.", required=0
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
    if classic is None and repo["protection"]["state"] == "unreadable":
        return _repo_result(
            repo,
            STATUS_CHECKS_REQUIRED,
            "error",
            f"Required checks could not be read. {_NEEDS_ADMIN_READ}",
        )
    return _repo_result(
        repo, STATUS_CHECKS_REQUIRED, "fail", "Nothing has to pass before a change merges."
    )


def _secret_scanning(repo: Mapping[str, Any]) -> Result:
    security = repo.get("security_and_analysis")
    if security is None:
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


def _merged_reviewed(repo: Mapping[str, Any]) -> Result:
    changes = repo["merged_changes"]
    branch = repo["default_branch"]
    if changes["state"] != "ok":
        return _repo_result(
            repo,
            MERGED_CHANGES_REVIEWED,
            "error",
            "Merged changes could not be read. Grant the token Pull requests read access.",
        )
    items = changes["items"]
    total = changes["total"]
    if total == 0:
        return _repo_result(
            repo,
            MERGED_CHANGES_REVIEWED,
            "not_applicable",
            f"Nothing merged into {branch} in the last {REVIEW_WINDOW_DAYS} days.",
            sampled=0,
            total=0,
        )
    unreviewed = [item["number"] for item in items if item["approvers"] == []]
    unknown = [item["number"] for item in items if item["approvers"] is None]
    sample = {"sampled": len(items), "total": total}
    scope = f"{len(items)} of {total}" if len(items) < total else f"{total}"
    if unreviewed:
        return _repo_result(
            repo,
            MERGED_CHANGES_REVIEWED,
            "fail",
            f"{len(unreviewed)} of {scope} merged changes had no approving review.",
            unreviewed=unreviewed,
            **sample,
        )
    if unknown:
        return _repo_result(
            repo,
            MERGED_CHANGES_REVIEWED,
            "error",
            f"Reviews could not be read for {len(unknown)} merged changes.",
            unknown=unknown,
            **sample,
        )
    return _repo_result(
        repo,
        MERGED_CHANGES_REVIEWED,
        "pass",
        f"All {scope} merged changes had an approving review.",
        **sample,
    )


def _two_factor(account: Mapping[str, Any]) -> Result:
    login = account["login"]
    base = {"resource_type": "organization", "resource_id": login, "resource_name": login}
    if account["type"] != "organization":
        return Result(
            ORG_TWO_FACTOR_REQUIRED,
            **base,
            outcome="not_applicable",
            detail={"summary": "A personal account cannot require two factor for others."},
        )
    value = account.get("two_factor_required")
    if value is True:
        return Result(
            ORG_TWO_FACTOR_REQUIRED,
            **base,
            outcome="pass",
            detail={"summary": "Every member must use two factor."},
        )
    if value is False:
        return Result(
            ORG_TWO_FACTOR_REQUIRED,
            **base,
            outcome="fail",
            detail={"summary": "Members can sign in without two factor."},
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


_PER_REPOSITORY = (
    _protected,
    _reviews_required,
    _status_checks,
    _merged_reviewed,
    _secret_scanning,
    _dependency_alerts,
)


def evaluate(snapshot: Mapping[str, Any]) -> list[Result]:
    """Every implemented check against every resource in the snapshot."""
    results = [_two_factor(snapshot["account"])]
    for repo in snapshot["repositories"]:
        results += [check(repo) for check in _PER_REPOSITORY]
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
