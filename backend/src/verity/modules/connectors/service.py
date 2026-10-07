"""Connectors: connect a provider, run its checks, and say what they mean for a control.

A run is three short steps on purpose. Starting it takes a row lock on the
connection, so two clicks cannot start two runs. Collecting talks to the provider
for as long as it takes, outside any database transaction. Finishing writes the
results, the evidence files and the connection's health together in one
transaction, so a half finished run never leaves half its results behind.

Rule 7 runs through all of it: a token the provider refuses, a permission the
token lacks, a rate limit or an outage is recorded as ``error``, never ``fail``,
and the control page reads "could not check", never "failing".
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.config import get_settings
from verity.core.crypto import get_secret_box
from verity.core.db import session_scope
from verity.core.errors import Conflict, InvalidInput, NotFound, UpstreamUnavailable
from verity.core.logging import get_logger
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.modules.compliance.control_service import MappingView, control_service
from verity.modules.connectors import composition as comp
from verity.modules.connectors import github
from verity.modules.connectors.http import (
    AccessDenied,
    CredentialRejected,
    NotFoundError,
    ProviderError,
    ProviderHttp,
    RateLimitExhausted,
)
from verity.modules.connectors.models import (
    PROVIDERS,
    SCOPE_STATES,
    Check,
    CheckResult,
    CheckRun,
    Connection,
    ConnectionResource,
    ControlTemplateCheck,
    IntegrationCapability,
    IntegrationRequest,
)
from verity.modules.evidence.service import evidence_service
from verity.modules.iam.service import iam_service
from verity.shared.ids import uuid7

logger = get_logger(__name__)

STALE_RUN: Final = timedelta(minutes=30)
"""A run still marked running after this stopped without finishing (a restart)."""
SCHEDULE_INTERVAL: Final = timedelta(hours=20)
"""A daily check is due once its connection's last run is older than this."""
EVIDENCE_REFRESH: Final = timedelta(hours=20)
STALE_AFTER: Final = timedelta(hours=48)
"""A result older than this says nothing about now. The schedule runs about
daily, so one missed run is tolerated and two are not: a passing control whose
last check was last week is out of date, not passing (AU-5)."""
EVIDENCE_VALIDITY_DAYS: Final = 7
HISTORY_DAYS: Final = 30

_CONNECTION_SNAPSHOT: Final = (
    "provider",
    "account_login",
    "account_type",
    "display_name",
    "status",
    "credential_hint",
    "credential_expires_at",
    "disconnected_reason",
)
_RUN_SNAPSHOT: Final = ("trigger", "status", "resources", "passed", "failed", "errored", "error")
_REQUEST_SNAPSHOT: Final = ("provider_name", "capability_key", "control_id", "note", "status")
_PROVIDER_NAMES: Final = {"github": "GitHub"}
_STATUS_RANK: Final = {"available": 0, "planned": 1, "not_planned": 2}


def _aad(tenant_id: uuid.UUID, connection_id: uuid.UUID) -> str:
    """Binds the ciphertext to its row: copied anywhere else, it will not decrypt."""
    return f"connections:{tenant_id}:{connection_id}"


def _hint(token: str) -> str:
    return f"ends {token[-4:]}" if len(token) >= 12 else "set"  # noqa: PLR2004


def _run_error(exc: ProviderError, name: str) -> str:
    if isinstance(exc, CredentialRejected):
        return (
            f"{name} rejected the stored token. It may have expired or been revoked. "
            "Reconnect with a new token."
        )
    if isinstance(exc, AccessDenied):
        return f"The token cannot read this {name} account. Check its permissions and reconnect."
    if isinstance(exc, RateLimitExhausted):
        return f"{name}'s hourly request allowance is used up. The next run will try again."
    if isinstance(exc, NotFoundError):
        return f"{name} no longer shows this account to the token."
    return f"{name} could not be reached. The next run will try again."


# -- views --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunView:
    id: uuid.UUID
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    resources: int
    passed: int
    failed: int
    errored: int
    error: str | None
    evidence_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class ScopeView:
    """How much of a connection's inventory the checks actually look at."""

    listed: int
    in_scope: int
    excluded: int


@dataclass(frozen=True, slots=True)
class ConnectionScopeView:
    connection_id: uuid.UUID
    account: str
    listed: int
    in_scope: int
    excluded: int


@dataclass(frozen=True, slots=True)
class ResourceView:
    """One repository a connection can see, and whether it is checked."""

    external_id: str
    name: str
    url: str | None
    private: bool
    fork: bool
    archived: bool
    empty: bool
    scope: str
    reason: str | None
    decided_by: str
    decided_by_name: str | None
    decided_at: datetime | None


@dataclass(frozen=True, slots=True)
class ConnectionView:
    id: uuid.UUID
    provider: str
    provider_name: str
    account_login: str
    account_type: str
    display_name: str
    status: str
    credential_hint: str | None
    credential_expires_at: datetime | None
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    error_streak: int
    created_at: datetime
    disconnected_at: datetime | None
    latest_run: RunView | None
    scope: ScopeView | None = None


@dataclass(frozen=True, slots=True)
class ProviderView:
    key: str
    name: str
    status: str
    phase: str | None
    capabilities: list[str]


@dataclass(frozen=True, slots=True)
class ProviderOption:
    key: str
    name: str
    status: str
    phase: str | None
    connected: bool
    runs_check: bool


@dataclass(frozen=True, slots=True)
class CapabilityView:
    key: str
    name: str
    description: str
    providers: list[ProviderOption]


@dataclass(frozen=True, slots=True)
class ResultView:
    connection_id: uuid.UUID
    account: str
    resource_type: str
    resource_name: str
    outcome: str
    summary: str
    url: str | None
    detail: dict[str, Any]
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class TestView:
    key: str
    name: str
    description: str
    remediation: str
    frequency: str
    coverage: str
    capabilities: list[str]
    status: str
    """pass, fail, error, not_applicable, pending, not_connected or not_available."""
    results: list[ResultView]
    counts: dict[str, int]
    last_run_at: datetime | None
    rationale: str | None = None
    """Why this check is evidence for this control, and what it does not prove."""
    evidence_kinds: list[str] = field(default_factory=list)
    source: str = "connector"
    """``connector`` (a system the workspace connects) or ``platform`` (Verity modules)."""
    availability: str = "planned"
    """running, ready, planned or not_planned: whether this workspace can have it run."""
    needs: list[CapabilityView] = field(default_factory=list)
    """The capabilities this check needs, each with the providers that can supply it."""


@dataclass(frozen=True, slots=True)
class CheckRef:
    key: str
    name: str
    availability: str


@dataclass(frozen=True, slots=True)
class ExpectedEvidenceView:
    """Something an auditor expects to see for a control, and how it gets there."""

    key: str
    name: str
    assurance: str
    """``design`` (it exists) or ``operating`` (it was followed)."""
    cadence: str
    source: str
    """``upload`` (a person provides it) or ``platform`` (a Verity module holds it)."""
    module: str | None
    state: str
    """automatic, when_connected, planned, platform or manual."""
    automated_by: list[CheckRef] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ControlComposition:
    """One control's evidence composition and monitoring status, for the register."""

    control_id: uuid.UUID
    code: str
    name: str
    composition: comp.Composition
    automation_status: str | None


@dataclass(frozen=True, slots=True)
class ChainCheck:
    key: str
    name: str
    source: str
    availability: str
    status: str
    coverage: str
    rationale: str | None
    evidence_kinds: list[str]
    capabilities: list[str]


@dataclass(frozen=True, slots=True)
class ControlChain:
    """Everything that evidences one control: checks, systems, and what people provide."""

    control_id: uuid.UUID
    composition: comp.Composition
    automation_status: str | None
    checks: list[ChainCheck]
    evidence: list[ExpectedEvidenceView]


@dataclass(frozen=True, slots=True)
class DayView:
    day: date
    status: str


@dataclass(frozen=True, slots=True)
class RequestView:
    id: uuid.UUID
    provider_name: str
    capability_key: str | None
    control_id: uuid.UUID | None
    note: str | None
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AutomationView:
    control_id: uuid.UUID
    mode: str
    status: str
    """passing, failing, error, not_applicable, pending, not_connected, or manual."""
    tests_total: int
    tests_running: int
    last_run_at: datetime | None
    running: bool
    connection_ids: list[uuid.UUID]
    capabilities: list[CapabilityView]
    tests: list[TestView]
    history: list[DayView]
    requests: list[RequestView] = field(default_factory=list)
    scopes: list[ConnectionScopeView] = field(default_factory=list)
    composition: comp.Composition | None = None
    evidence: list[ExpectedEvidenceView] = field(default_factory=list)
    mappings: list[MappingView] = field(default_factory=list)


def _run_view(run: CheckRun | None, now: datetime) -> RunView | None:
    if run is None:
        return None
    status = run.status
    if status == "running" and run.started_at < now - STALE_RUN:
        status = "failed"
    return RunView(
        id=run.id,
        trigger=run.trigger,
        status=status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        resources=run.resources,
        passed=run.passed,
        failed=run.failed,
        errored=run.errored,
        error=run.error,
        evidence_id=run.evidence_id,
    )


def _connection_view(
    row: Connection, run: CheckRun | None, now: datetime, scope: ScopeView | None = None
) -> ConnectionView:
    return ConnectionView(
        id=row.id,
        provider=row.provider,
        provider_name=_PROVIDER_NAMES.get(row.provider, row.provider),
        account_login=row.account_login,
        account_type=row.account_type,
        display_name=row.display_name,
        status=row.status,
        credential_hint=row.credential_hint,
        credential_expires_at=row.credential_expires_at,
        last_run_at=row.last_run_at,
        last_success_at=row.last_success_at,
        last_error=row.last_error,
        error_streak=row.error_streak,
        created_at=row.created_at,
        disconnected_at=row.disconnected_at,
        latest_run=_run_view(run, now),
        scope=scope,
    )


def _worst(outcomes: list[str]) -> str:
    """Fail beats error beats pass (rule 7 keeps error from ever reading as fail)."""
    for outcome in ("fail", "error", "pass"):
        if outcome in outcomes:
            return outcome
    return "not_applicable"


def _test_status(
    *,
    implemented: bool,
    runners: bool,
    outcomes: list[str],
    stale: bool = False,
    ran: bool = False,
) -> str:
    """One test, from what can run it and what it last found.

    ``stale`` when what it last found is too old to say anything about now. ``ran``
    when a system that can run it has finished a run: a run that left no result for
    this test (a personal account with no repositories) found nothing to check, which
    is "not applicable", not "still waiting for the first run".
    """
    if not implemented:
        return "not_available"
    if not runners:
        return "not_connected"
    if not outcomes:
        return "not_applicable" if ran else "pending"
    if stale:
        return "stale"
    return _worst(outcomes)


def _control_status(states: list[str]) -> str:
    """A control's automated status (AU-6).

    Failing if any test fails, else error if any could not be read, else out of
    date if any result is too old to count, else passing only if at least one test
    actually passed. A test that found nothing to check
    (not applicable) is not a pass: a control whose every result is "not
    applicable" has been verified by nothing, and says so (AU-5).
    """
    if not states:
        return "manual"
    for state, label in (
        ("fail", "failing"),
        ("error", "error"),
        ("stale", "stale"),
        ("pass", "passing"),
    ):
        if state in states:
            return label
    if "not_applicable" in states:
        return "not_applicable"
    if "pending" in states:
        return "pending"
    return "not_connected"


def _digest(results: list[github.Result]) -> str:
    """What this run found, for deciding whether it is worth a new evidence file.

    The detail is part of it: a reviewer, a setting or a population that changed
    under an unchanged pass or fail is still a different observation, and an
    auditor must be able to retrieve the one that was true on the day.
    """
    rows = sorted(
        (
            r.check_key,
            r.resource_type,
            r.resource_id,
            r.outcome,
            json.dumps(r.detail, sort_keys=True, default=str),
        )
        for r in results
    )
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


_DIGEST_LENGTH: Final = 16
"""How much of a check's digest is kept in the id its evidence is filed under."""


def _rows_digest(rows: Sequence[CheckResult]) -> str:
    """What one check found in a run, for deciding whether it is worth a new evidence file."""
    ordered = sorted(
        (
            row.resource_type,
            row.resource_id,
            row.outcome,
            json.dumps(row.detail, sort_keys=True, default=str),
        )
        for row in rows
    )
    return hashlib.sha256(json.dumps(ordered).encode()).hexdigest()


def _external_id(
    connection_id: uuid.UUID,
    check_key: str,
    digest: str | None = None,
    run_id: uuid.UUID | None = None,
) -> str:
    """The id a check's evidence is filed under: ``connection:check:digest:run``.

    The digest is of what the check found, so the next run can tell a new result from a
    repeat; the run keeps the id unique when the same result is filed again a day later.
    Without a digest and a run this is the prefix every file of that check starts with.
    ``connection:check`` is the item's series (evidence_service.series_of): the newest
    file of a series replaces the rest, and the older ones read as history.
    """
    prefix = f"{connection_id}:{check_key}:"
    if digest is None or run_id is None:
        return prefix
    return f"{prefix}{digest[:_DIGEST_LENGTH]}:{run_id}"


def _filed_digest(external_id: str) -> str | None:
    """The digest an evidence file was filed under, or None for an id of another shape."""
    parts = external_id.split(":")
    return parts[2] if len(parts) == 4 else None  # noqa: PLR2004 — connection:check:digest:run


def _slug(check_key: str) -> str:
    """A check key as a file name part: ``vcs.secret_scanning_enabled`` becomes dashes."""
    return re.sub(r"[^a-z0-9]+", "-", check_key.lower()).strip("-")


@dataclass(frozen=True, slots=True)
class _Outcomes:
    """What the latest finished runs found, and which providers have gone quiet."""

    by_check: dict[uuid.UUID, list[str]] = field(default_factory=dict)
    stale_providers: set[str] = field(default_factory=set)
    ran_providers: set[str] = field(default_factory=set)

    def stale(self, implementations: Sequence[str]) -> bool:
        """Whether a check's results come from a provider whose last run is too old."""
        return bool(self.stale_providers & set(implementations))

    def ran(self, implementations: Sequence[str]) -> bool:
        """Whether a provider that can run a check has finished a run."""
        return bool(self.ran_providers & set(implementations))


class ConnectorService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service
        # Tests replay recorded GitHub responses through these; production uses
        # the real network and real waits.
        self.transport: httpx.AsyncBaseTransport | None = None
        self.sleep: Any = None

    def _client(self, token: str) -> ProviderHttp:
        settings = get_settings().connectors
        extra: dict[str, Any] = {"sleep": self.sleep} if self.sleep else {}
        return ProviderHttp(
            settings.github_api_url,
            headers=github.headers(token),
            timeout=settings.timeout_seconds,
            transport=self.transport,
            **extra,
        )

    # -- catalogue ------------------------------------------------------------------

    async def providers(self, session: AsyncSession) -> list[ProviderView]:
        """Every provider any capability names, with its best status and phase."""
        merged: dict[str, dict[str, Any]] = {}
        for capability in (await session.execute(select(IntegrationCapability))).scalars():
            for option in capability.providers:
                entry = merged.setdefault(
                    option["key"],
                    {
                        "name": option["name"],
                        "status": option["status"],
                        "phase": option["phase"],
                        "capabilities": [],
                    },
                )
                entry["capabilities"].append(capability.name)
                if _STATUS_RANK[option["status"]] < _STATUS_RANK[entry["status"]]:
                    entry["status"], entry["phase"] = option["status"], option["phase"]
        return sorted(
            (ProviderView(key=key, **values) for key, values in merged.items()),
            key=lambda view: (_STATUS_RANK[view.status], view.name.lower()),
        )

    # -- connections ----------------------------------------------------------------

    async def _latest_runs(
        self, session: AsyncSession, tenant_id: uuid.UUID, connection_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, CheckRun]:
        if not connection_ids:
            return {}
        rows = await session.execute(
            select(CheckRun)
            .where(CheckRun.tenant_id == tenant_id, CheckRun.connection_id.in_(connection_ids))
            .distinct(CheckRun.connection_id)
            .order_by(CheckRun.connection_id, CheckRun.started_at.desc())
        )
        return {run.connection_id: run for run in rows.scalars()}

    async def list_connections(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[ConnectionView]:
        rows = list(
            (
                await session.execute(
                    select(Connection)
                    .where(Connection.tenant_id == tenant_id)
                    .order_by(Connection.status, Connection.created_at.desc())
                )
            ).scalars()
        )
        runs = await self._latest_runs(session, tenant_id, [row.id for row in rows])
        scopes = await self._scope_summaries(session, tenant_id, [row.id for row in rows])
        now = datetime.now(UTC)
        return [_connection_view(row, runs.get(row.id), now, scopes.get(row.id)) for row in rows]

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, connection_id: uuid.UUID
    ) -> Connection:
        row = await session.get(Connection, connection_id)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(
                "This connection no longer exists.", detail=f"connection {connection_id}"
            )
        return row

    async def connect(  # noqa: PLR0913 — the provider, the credential, the account
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Membership,
        provider: str,
        token: str,
        account: str | None,
    ) -> ConnectionView:
        """Check the token against the provider, then store it encrypted."""
        if provider not in PROVIDERS:
            raise InvalidInput(
                "Verity cannot connect to that system yet. Request it and the team "
                "will be in touch.",
                detail=f"provider {provider!r} has no collector",
            )
        token = token.strip()
        if not token:
            raise InvalidInput("Paste the access token.", detail="empty token")
        try:
            async with self._client(token) as http:
                found = await github.inspect(http, account)
        except CredentialRejected as exc:
            raise InvalidInput(
                "GitHub rejected this token. Check it was copied in full and has not expired.",
                detail="github answered 401 on connect",
            ) from exc
        except NotFoundError as exc:
            raise InvalidInput(
                f"This token cannot see a GitHub organisation called {account}. Check the "
                "name, or leave it empty to use the token's own account.",
                detail="github answered 404 for the organisation",
            ) from exc
        except AccessDenied as exc:
            raise InvalidInput(
                "This token cannot list repositories. Give it read access to the "
                "repositories Verity should check.",
                detail="github answered 403 listing repositories",
            ) from exc
        except ProviderError as exc:
            raise UpstreamUnavailable(
                "GitHub could not be reached. Try again in a minute.", detail=type(exc).__name__
            ) from exc

        taken = await session.scalar(
            select(Connection.id).where(
                Connection.tenant_id == tenant_id,
                Connection.provider == provider,
                Connection.account_login == found.login,
                Connection.status == "active",
            )
        )
        if taken is not None:
            raise Conflict(
                f"{found.login} is already connected.", detail=f"connection {taken} is active"
            )

        connection_id = uuid7()
        row = Connection(
            id=connection_id,
            tenant_id=tenant_id,
            provider=provider,
            account_login=found.login,
            account_type=found.account_type,
            display_name=found.display_name,
            credential_ciphertext=get_secret_box().encrypt(
                token, aad=_aad(tenant_id, connection_id)
            ),
            credential_hint=_hint(token),
            credential_expires_at=found.token_expires_at,
            created_by_membership_id=actor.id,
        )
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="connection",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(row, fields=_CONNECTION_SNAPSHOT),
        )
        await session.refresh(row)
        return _connection_view(row, None, datetime.now(UTC))

    async def disconnect(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Membership,
        connection_id: uuid.UUID,
        reason: str,
    ) -> ConnectionView:
        """Destroy the credential and stop the runs. History stays."""
        row = await self._load(session, tenant_id, connection_id)
        if row.status != "active":
            raise Conflict("This connection is already disconnected.", detail=str(connection_id))
        reason = reason.strip()
        if len(reason) < 3:  # noqa: PLR2004
            raise InvalidInput("Say why it is being disconnected.", detail="reason too short")
        before = AuditService.snapshot(row, fields=_CONNECTION_SNAPSHOT)
        row.status = "disconnected"
        row.credential_ciphertext = None
        row.disconnected_at = datetime.now(UTC)
        row.disconnected_reason = reason
        await session.flush([row])
        await self._audit.record(
            session,
            action="update",
            object_type="connection",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(row, fields=_CONNECTION_SNAPSHOT),
        )
        runs = await self._latest_runs(session, tenant_id, [row.id])
        return _connection_view(row, runs.get(row.id), datetime.now(UTC))

    # -- scope (AU-9) ---------------------------------------------------------------

    async def _scope_decisions(
        self, tenant_id: uuid.UUID, connection_id: uuid.UUID
    ) -> dict[str, github.ScopeDecision]:
        """What people have decided, for the collector. System decisions are not
        carried: the collector derives those fresh on every run."""
        async with session_scope(tenant_id) as session:
            rows = await session.execute(
                select(ConnectionResource).where(
                    ConnectionResource.tenant_id == tenant_id,
                    ConnectionResource.connection_id == connection_id,
                    ConnectionResource.decided_by == "person",
                )
            )
            return {
                row.external_id: github.ScopeDecision(row.scope, row.scope_reason)
                for row in rows.scalars()
            }

    async def _sync_inventory(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        connection: Connection,
        snapshot: dict[str, Any],
        now: datetime,
    ) -> None:
        """Keep the inventory in step with what the run listed.

        A person's decision is never overwritten by a run. A system decision is,
        so a repository that is no longer a fork, or is un-archived, comes back
        into scope on its own. An archived repository is out whatever anyone said.
        """
        inventory = snapshot.get("inventory")
        if inventory is None:
            return
        existing = {
            row.external_id: row
            for row in (
                await session.execute(
                    select(ConnectionResource).where(
                        ConnectionResource.tenant_id == tenant_id,
                        ConnectionResource.connection_id == connection.id,
                    )
                )
            ).scalars()
        }
        collected = {repo["id"]: repo for repo in snapshot.get("repositories", [])}
        for entry in inventory:
            row = existing.get(entry["id"])
            # Emptiness is only learnt by reading the repository, so an excluded
            # one keeps what was last known about it.
            if entry["id"] in collected:
                empty = collected[entry["id"]]["protection"].get("reason") == "no_branch"
            else:
                empty = bool(row.attributes.get("empty")) if row is not None else False
            attributes = {
                "private": entry["private"],
                "fork": entry["fork"],
                "archived": entry["archived"],
                "default_branch": entry["default_branch"],
                "empty": empty,
            }
            if row is None:
                session.add(
                    ConnectionResource(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        connection_id=connection.id,
                        source=connection.provider,
                        external_id=entry["id"],
                        name=entry["full_name"],
                        url=entry["url"],
                        attributes=attributes,
                        scope=entry["scope"],
                        scope_reason=entry["reason"],
                        decided_by="system",
                        first_seen_at=now,
                        synced_at=now,
                    )
                )
                continue
            row.name, row.url, row.attributes, row.synced_at = (
                entry["full_name"],
                entry["url"],
                attributes,
                now,
            )
            if row.decided_by == "system" or entry["archived"]:
                row.scope, row.scope_reason, row.decided_by = (
                    entry["scope"],
                    entry["reason"],
                    "system",
                )
        await session.flush()

    async def _scope_summaries(
        self, session: AsyncSession, tenant_id: uuid.UUID, connection_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, ScopeView]:
        if not connection_ids:
            return {}
        counts: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
        rows = await session.execute(
            select(ConnectionResource.connection_id, ConnectionResource.scope, func.count())
            .where(
                ConnectionResource.tenant_id == tenant_id,
                ConnectionResource.connection_id.in_(connection_ids),
            )
            .group_by(ConnectionResource.connection_id, ConnectionResource.scope)
        )
        for connection_id, scope, number in rows.tuples():
            counts[connection_id][scope] = number
        return {
            connection_id: ScopeView(
                listed=sum(by_scope.values()),
                in_scope=by_scope.get("in_scope", 0),
                excluded=by_scope.get("excluded", 0),
            )
            for connection_id, by_scope in counts.items()
        }

    async def resources(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, connection_id: uuid.UUID
    ) -> list[ResourceView]:
        """Everything this connection can see, in scope or not, with the reason."""
        await self._load(session, tenant_id, connection_id)
        rows = list(
            (
                await session.execute(
                    select(ConnectionResource)
                    .where(
                        ConnectionResource.tenant_id == tenant_id,
                        ConnectionResource.connection_id == connection_id,
                    )
                    .order_by(func.lower(ConnectionResource.name))
                )
            ).scalars()
        )
        names = {
            member.membership_id: member.full_name
            for member in await iam_service.list_members(session, tenant_id=tenant_id)
        }
        return [
            ResourceView(
                external_id=row.external_id,
                name=row.name,
                url=row.url,
                private=bool(row.attributes.get("private")),
                fork=bool(row.attributes.get("fork")),
                archived=bool(row.attributes.get("archived")),
                empty=bool(row.attributes.get("empty")),
                scope=row.scope,
                reason=row.scope_reason,
                decided_by=row.decided_by,
                decided_by_name=names.get(row.decided_by_membership_id)
                if row.decided_by_membership_id
                else None,
                decided_at=row.decided_at,
            )
            for row in rows
        ]

    async def set_scope(  # noqa: PLR0913 — the connection, who, what, and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Membership,
        connection_id: uuid.UUID,
        decisions: Sequence[tuple[str, str]],
        reason: str | None,
    ) -> list[ResourceView]:
        """Put repositories in or out of scope. An exclusion needs a reason.

        The reason is shared by every exclusion in one request, which is how a
        person drops forty sandbox repositories at once without typing it forty
        times. It is recorded on each row, audited, and printed on the evidence.
        """
        connection = await self._load(session, tenant_id, connection_id)
        if connection.status != "active":
            raise Conflict("Reconnect this account before changing what it checks.", detail="gone")
        wanted = dict(decisions)
        bad = {scope for scope in wanted.values() if scope not in SCOPE_STATES}
        if bad:
            raise InvalidInput("Each repository is either checked or excluded.", detail=str(bad))
        clean_reason = (reason or "").strip() or None
        rows = {
            row.external_id: row
            for row in (
                await session.execute(
                    select(ConnectionResource).where(
                        ConnectionResource.tenant_id == tenant_id,
                        ConnectionResource.connection_id == connection_id,
                        ConnectionResource.external_id.in_(list(wanted)),
                    )
                )
            ).scalars()
        }
        unknown = set(wanted) - set(rows)
        if unknown:
            raise NotFound(
                "One of those repositories is no longer part of this connection. "
                "Run the checks again and choose from the refreshed list.",
                detail=f"{len(unknown)} unknown resources on {connection_id}",
            )
        now = datetime.now(UTC)
        for external_id, scope in wanted.items():
            row = rows[external_id]
            if row.attributes.get("archived"):
                continue
            if scope == "excluded" and clean_reason is None:
                raise InvalidInput(
                    "Say why these repositories are left out of the audit. The reason is "
                    "kept on the record and printed on the evidence.",
                    detail="exclusion without a reason",
                )
            new_reason = clean_reason if scope == "excluded" else None
            # Putting back what the system would check anyway is not a decision
            # worth remembering: hand it back to the system.
            default = "excluded" if row.attributes.get("fork") else "in_scope"
            decided_by = "system" if scope == default == "in_scope" else "person"
            unchanged = (
                row.scope == scope
                and row.scope_reason == new_reason
                and row.decided_by == decided_by
            )
            if unchanged:
                continue
            before = {"scope": row.scope, "reason": row.scope_reason, "decided_by": row.decided_by}
            row.scope, row.scope_reason, row.decided_by = scope, new_reason, decided_by
            row.decided_by_membership_id = actor.id if decided_by == "person" else None
            row.decided_at = now if decided_by == "person" else None
            await self._audit.record(
                session,
                action="update",
                object_type="connection_resource",
                object_id=row.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after={
                    "resource": row.name,
                    "scope": row.scope,
                    "reason": row.scope_reason,
                    "decided_by": row.decided_by,
                },
            )
        await session.flush()
        return await self.resources(session, tenant_id=tenant_id, connection_id=connection_id)

    async def ensure_runnable(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, connection_id: uuid.UUID
    ) -> None:
        """Refuse a manual run the background task would only drop."""
        row = await self._load(session, tenant_id, connection_id)
        if row.status != "active":
            raise Conflict(
                "Reconnect this account before running its checks.", detail="disconnected"
            )
        running = await session.scalar(
            select(CheckRun.id).where(
                CheckRun.tenant_id == tenant_id,
                CheckRun.connection_id == connection_id,
                CheckRun.status == "running",
                CheckRun.started_at > datetime.now(UTC) - STALE_RUN,
            )
        )
        if running is not None:
            raise Conflict("A run is already in progress for this account.", detail=str(running))

    # -- runs -------------------------------------------------------------------------

    async def run(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        trigger: str,
        actor: Actor,
    ) -> uuid.UUID | None:
        """Collect, evaluate and record one run. Opens its own sessions.

        Returns the run id, or None when there was nothing to run (disconnected,
        or another run holds the connection).
        """
        started = await self._start(tenant_id, connection_id, trigger, actor)
        if started is None:
            return None
        run_id, login, account_type, token = started
        name = _PROVIDER_NAMES["github"]
        snapshot: dict[str, Any] | None = None
        failure: str | None = None
        decisions = await self._scope_decisions(tenant_id, connection_id)
        try:
            async with self._client(token) as http:
                snapshot = await github.collect(
                    http,
                    login=login,
                    account_type=account_type,
                    now=datetime.now(UTC),
                    decisions=decisions,
                )
            results = github.evaluate(snapshot)
        except ProviderError as exc:
            failure = _run_error(exc, name)
            results = github.unreachable(login, account_type, failure)
        except Exception:
            logger.exception("connectors.run.crashed", run_id=str(run_id))
            failure = "The check run stopped unexpectedly. The next run will try again."
            snapshot = None
            results = github.unreachable(login, account_type, failure)
        await self._finish(tenant_id, run_id, snapshot, results, failure, actor)
        return run_id

    async def _start(
        self, tenant_id: uuid.UUID, connection_id: uuid.UUID, trigger: str, actor: Actor
    ) -> tuple[uuid.UUID, str, str, str] | None:
        now = datetime.now(UTC)
        async with session_scope(tenant_id) as session:
            # The row lock serialises two starts for one connection.
            connection = await session.scalar(
                select(Connection)
                .where(Connection.id == connection_id, Connection.tenant_id == tenant_id)
                .with_for_update()
            )
            if (
                connection is None
                or connection.status != "active"
                or not connection.credential_ciphertext
            ):
                return None
            await session.execute(
                update(CheckRun)
                .where(
                    CheckRun.tenant_id == tenant_id,
                    CheckRun.connection_id == connection_id,
                    CheckRun.status == "running",
                    CheckRun.started_at <= now - STALE_RUN,
                )
                .values(
                    status="failed", finished_at=now, error="The run stopped before it finished."
                )
            )
            busy = await session.scalar(
                select(CheckRun.id).where(
                    CheckRun.tenant_id == tenant_id,
                    CheckRun.connection_id == connection_id,
                    CheckRun.status == "running",
                )
            )
            if busy is not None:
                return None
            run = CheckRun(
                id=uuid7(),
                tenant_id=tenant_id,
                connection_id=connection_id,
                trigger=trigger,
                triggered_by_membership_id=actor.id if isinstance(actor, Membership) else None,
                status="running",
                started_at=now,
            )
            session.add(run)
            await session.flush([run])
            await self._audit.record(
                session,
                action="create",
                object_type="check_run",
                object_id=run.id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after=AuditService.snapshot(run, fields=_RUN_SNAPSHOT),
            )
            token = get_secret_box().decrypt(
                connection.credential_ciphertext, aad=_aad(tenant_id, connection_id)
            )
            return run.id, connection.account_login, connection.account_type, token

    async def _finish(  # noqa: PLR0913, PLR0917 — one run's whole outcome
        self,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        snapshot: dict[str, Any] | None,
        results: list[github.Result],
        failure: str | None,
        actor: Actor,
    ) -> None:
        now = datetime.now(UTC)
        async with session_scope(tenant_id) as session:
            run = await session.get(CheckRun, run_id)
            connection = await session.get(Connection, run.connection_id) if run else None
            if run is None or connection is None:
                return
            before = AuditService.snapshot(run, fields=_RUN_SNAPSHOT)
            keys = {result.check_key for result in results}
            checks = {
                row.key: row
                for row in (
                    await session.execute(select(Check).where(Check.key.in_(keys)))
                ).scalars()
            }
            if keys - set(checks):
                # Content not seeded after a deploy: say so rather than drop silently.
                logger.warning("connectors.checks_missing", keys=sorted(keys - set(checks)))
            rows = [
                CheckResult(
                    id=uuid7(),
                    observed_at=now,
                    tenant_id=tenant_id,
                    run_id=run.id,
                    connection_id=connection.id,
                    check_id=checks[result.check_key].id,
                    resource_type=result.resource_type,
                    resource_id=result.resource_id,
                    resource_name=result.resource_name,
                    outcome=result.outcome,
                    detail=result.detail,
                )
                for result in results
                if result.check_key in checks
            ]
            session.add_all(rows)
            await session.flush()

            outcomes = [row.outcome for row in rows]
            digest = _digest(results)
            run.status = "failed" if failure else "completed"
            run.finished_at = now
            run.resources = len({(row.resource_type, row.resource_id) for row in rows})
            run.passed = outcomes.count("pass")
            run.failed = outcomes.count("fail")
            run.errored = outcomes.count("error")
            run.error = failure
            run.results_digest = digest
            if snapshot is not None:
                await self._sync_inventory(session, tenant_id, connection, snapshot, now)
                # A run files one evidence item per check, so there is no single
                # ``evidence_id`` to record on it: the items name the run they came from.
                await self._evidence(
                    session, tenant_id, run, connection, snapshot, rows, actor, now
                )
            connection.last_run_at = now
            if failure:
                connection.error_streak += 1
                connection.last_error = failure
            else:
                connection.error_streak = 0
                connection.last_error = None
                connection.last_success_at = now
            await session.flush()
            await self._audit.record(
                session,
                action="update",
                object_type="check_run",
                object_id=run.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=AuditService.snapshot(run, fields=_RUN_SNAPSHOT),
            )
        logger.info(
            "connectors.run.finished",
            run_id=str(run_id),
            status="failed" if failure else "completed",
            results=len(results),
        )

    async def _evidence(  # noqa: PLR0913, PLR0917 — the run, its connection, what it read
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        run: CheckRun,
        connection: Connection,
        snapshot: dict[str, Any],
        rows: list[CheckResult],
        actor: Actor,
        now: datetime,
    ) -> list[uuid.UUID]:
        """File what each check found as its own evidence, on the controls that check supports.

        One file per check rather than one per run, so the evidence on a control is what that
        control's checks looked at, named for the check, and never the whole account. A check
        files again only when its results changed or its last file is older than
        ``EVIDENCE_REFRESH``: a person clicking Run now five times gets one file per check,
        not five.
        """
        by_check: dict[uuid.UUID, list[CheckResult]] = defaultdict(list)
        for row in rows:
            by_check[row.check_id].append(row)
        # A check files only when it found something an auditor can use: a pass or a fail.
        found = {
            check_id: check_rows
            for check_id, check_rows in by_check.items()
            if any(row.outcome in ("pass", "fail") for row in check_rows)
        }
        if not found:
            return []
        checks = {
            row.id: row
            for row in (
                await session.execute(select(Check).where(Check.id.in_(list(found))))
            ).scalars()
        }
        templates: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for check_id, template_id in (
            await session.execute(
                select(ControlTemplateCheck.check_id, ControlTemplateCheck.template_id).where(
                    ControlTemplateCheck.check_id.in_(list(found))
                )
            )
        ).tuples():
            templates[check_id].add(template_id)

        name = _PROVIDER_NAMES.get(connection.provider, connection.provider)
        inventory = snapshot.get("inventory") or []
        # What the checks did not look at, and why. An auditor reading a clean result needs
        # to know the population it was clean over.
        scope = {
            "listed": len(inventory),
            "checked": sum(1 for entry in inventory if entry["scope"] == "in_scope"),
            "excluded": [
                {
                    "resource": entry["full_name"],
                    "reason": entry["reason"],
                    "decided_by": entry["decided_by"],
                }
                for entry in inventory
                if entry["scope"] == "excluded"
            ],
        }
        filed: list[uuid.UUID] = []
        for check_id, check_rows in found.items():
            check = checks.get(check_id)
            if check is None:
                continue
            digest = _rows_digest(check_rows)
            latest = await evidence_service.latest_synced(
                session,
                tenant_id=tenant_id,
                source=connection.provider,
                external_id_prefix=_external_id(connection.id, check.key),
            )
            if (
                latest is not None
                and _filed_digest(latest[0]) == digest[:_DIGEST_LENGTH]
                and latest[1] > now - EVIDENCE_REFRESH
            ):
                continue
            # Only the controls this check supports: not every control the account touches.
            control_ids = await control_service.control_ids_for_templates(
                session, tenant_id=tenant_id, template_ids=templates[check_id]
            )
            if not control_ids:
                continue
            outcomes = [row.outcome for row in check_rows]
            document = {
                "verity": {
                    "run_id": str(run.id),
                    "trigger": run.trigger,
                    "connection": {
                        "provider": connection.provider,
                        "account": connection.account_login,
                    },
                    "collected_at": now.isoformat(),
                    "access": "read only",
                    "check": {
                        "key": check.key,
                        "name": check.name,
                        "description": check.description,
                    },
                    "scope": scope,
                    "results": [
                        {
                            "check": check.key,
                            # The name people read, so a report of this file needs no catalogue.
                            "name": check.name,
                            "resource": row.resource_name,
                            "outcome": row.outcome,
                            "summary": row.detail.get("summary"),
                            "reason": row.detail.get("reason"),
                        }
                        for row in check_rows
                    ],
                },
                "snapshot": github.evidence_snapshot(check.key, snapshot),
            }
            data = json.dumps(document, indent=2, default=str).encode()
            resources = len({(row.resource_type, row.resource_id) for row in check_rows})
            view = await evidence_service.add_file(
                session,
                tenant_id=tenant_id,
                actor=actor,
                # Named for what it evidences, where and when. The moment is in the title
                # because a check whose results changed files again within the day, and a
                # list of identical titles tells nobody which is which.
                title=(
                    f"{check.name}: {name} {connection.account_login}, "
                    f"{now.day} {now:%b %Y %H:%M} UTC"
                ),
                filename=(
                    f"{connection.provider}-{connection.account_login}-{_slug(check.key)}-"
                    f"{now:%Y%m%dT%H%MZ}.json"
                ),
                data=data,
                evidence_type="configuration_export",
                collected_at=now.date(),
                description=(
                    f"{outcomes.count('pass')} passed, {outcomes.count('fail')} failed and "
                    f"{outcomes.count('error')} could not be checked across {resources} "
                    f"resources. Collected read only by the {name} connector."
                ),
                source_label=f"{name} connector",
                owner_membership_id=connection.created_by_membership_id,
                renewal_date=now.date() + timedelta(days=EVIDENCE_VALIDITY_DAYS),
                control_ids=control_ids,
                source=connection.provider,
                external_id=_external_id(connection.id, check.key, digest, run.id),
                synced_at=now,
            )
            filed.append(view.id)
        return filed

    async def due_connection_ids(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Active connections whose last run is older than the daily interval."""
        cutoff = datetime.now(UTC) - SCHEDULE_INTERVAL
        rows = await session.execute(
            select(Connection.id).where(
                Connection.tenant_id == tenant_id,
                Connection.status == "active",
                (Connection.last_run_at.is_(None)) | (Connection.last_run_at < cutoff),
            )
        )
        return list(rows.scalars())

    # -- the control page -------------------------------------------------------------

    async def _capability_facts(
        self, session: AsyncSession
    ) -> tuple[dict[str, IntegrationCapability], dict[str, comp.CapabilityFacts]]:
        rows = {
            row.key: row for row in (await session.execute(select(IntegrationCapability))).scalars()
        }
        facts = {
            key: comp.CapabilityFacts(key=key, name=row.name, providers=row.providers)
            for key, row in rows.items()
        }
        return rows, facts

    async def _active_connections(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[Connection]:
        return list(
            (
                await session.execute(
                    select(Connection).where(
                        Connection.tenant_id == tenant_id, Connection.status == "active"
                    )
                )
            ).scalars()
        )

    @staticmethod
    def _needs(
        check: Check,
        rows: dict[str, IntegrationCapability],
        connected: set[str],
    ) -> list[CapabilityView]:
        """The capabilities one check needs, each with who can supply it."""
        return [
            CapabilityView(
                key=key,
                name=rows[key].name,
                description=rows[key].description,
                providers=[
                    ProviderOption(
                        key=option["key"],
                        name=option["name"],
                        status=option["status"],
                        phase=option["phase"],
                        connected=comp.provider_state(option, connected) == "connected",
                        runs_check=option["key"] in check.implementations,
                    )
                    for option in rows[key].providers
                ],
            )
            for key in check.capabilities
            if key in rows
        ]

    @staticmethod
    def _evidence_views(
        items: list[dict[str, Any]], checks: dict[str, tuple[str, str]]
    ) -> list[ExpectedEvidenceView]:
        """Expected evidence with how each item reaches the control right now.

        ``checks`` maps a check key to ``(name, availability)``.
        """
        availability = {key: state for key, (_name, state) in checks.items()}
        return [
            ExpectedEvidenceView(
                key=str(item["key"]),
                name=str(item["name"]),
                assurance=str(item["assurance"]),
                cadence=str(item["cadence"]),
                source=str(item["source"]),
                module=item.get("module"),
                state=comp.item_state(item, availability),
                automated_by=[
                    CheckRef(key=k, name=checks[k][0], availability=checks[k][1])
                    for k in item.get("automated_by", [])
                    if k in checks
                ],
            )
            for item in items
        ]

    async def control_automation(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> AutomationView:
        control = await control_service.get_control(
            session, tenant_id=tenant_id, control_id=control_id
        )
        mode = {"Automated": "automated", "Hybrid": "hybrid"}.get(
            control.control_sub_type or "", "manual"
        )
        mapped: list[tuple[Check, str, str | None]] = []
        if control.template_id is not None:
            mapped = [
                (check, coverage, rationale)
                for check, coverage, rationale in (
                    await session.execute(
                        select(Check, ControlTemplateCheck.coverage, ControlTemplateCheck.rationale)
                        .join(ControlTemplateCheck, ControlTemplateCheck.check_id == Check.id)
                        .where(ControlTemplateCheck.template_id == control.template_id)
                        .order_by(Check.name)
                    )
                ).tuples()
            ]
        capability_rows, facts = await self._capability_facts(session)
        needed = {key for check, _, _ in mapped for key in check.capabilities}
        capabilities = {key: row for key, row in capability_rows.items() if key in needed}
        connections = await self._active_connections(session, tenant_id)
        connected = {connection.provider for connection in connections}
        # Only connections that can run one of this control's checks speak for it:
        # a GitHub run says nothing about when laptops were last checked.
        by_id = {
            connection.id: connection
            for connection in connections
            if any(connection.provider in check.implementations for check, _, _ in mapped)
        }
        now = datetime.now(UTC)
        latest = await self._latest_runs(session, tenant_id, list(by_id))
        running = any(
            run.status == "running" and run.started_at > now - STALE_RUN for run in latest.values()
        )
        finished = await self._latest_finished(session, tenant_id, list(by_id))
        stale_providers = {
            by_id[connection_id].provider
            for connection_id, run in finished.items()
            if run.started_at < now - STALE_AFTER
        }

        results_by_check: dict[uuid.UUID, list[CheckResult]] = defaultdict(list)
        check_ids = [check.id for check, _, _ in mapped]
        if finished and check_ids:
            earliest = min(run.started_at for run in finished.values())
            for row in (
                await session.execute(
                    select(CheckResult).where(
                        CheckResult.tenant_id == tenant_id,
                        CheckResult.run_id.in_([run.id for run in finished.values()]),
                        CheckResult.check_id.in_(check_ids),
                        CheckResult.observed_at >= earliest,
                    )
                )
            ).scalars():
                results_by_check[row.check_id].append(row)

        check_facts = [
            comp.CheckFacts(
                key=check.key,
                capabilities=list(check.capabilities),
                implementations=list(check.implementations),
            )
            for check, _, _ in mapped
        ]
        availability = {fact.key: comp.availability(fact, facts, connected) for fact in check_facts}
        tests: list[TestView] = []
        for check, coverage, rationale in mapped:
            runners = [c for c in connections if c.provider in check.implementations]
            rows = results_by_check.get(check.id, [])
            status = _test_status(
                implemented=bool(check.implementations),
                runners=bool(runners),
                outcomes=[row.outcome for row in rows],
                stale=bool(stale_providers & set(check.implementations)),
                ran=any(c.id in finished for c in runners),
            )
            order = {"fail": 0, "error": 1, "pass": 2, "not_applicable": 3}
            tests.append(
                TestView(
                    key=check.key,
                    name=check.name,
                    description=check.description,
                    remediation=check.remediation,
                    frequency=check.frequency,
                    coverage=coverage,
                    capabilities=list(check.capabilities),
                    status=status,
                    results=[
                        ResultView(
                            connection_id=row.connection_id,
                            account=by_id[row.connection_id].account_login,
                            resource_type=row.resource_type,
                            resource_name=row.resource_name,
                            outcome=row.outcome,
                            summary=str(row.detail.get("summary", "")),
                            url=row.detail.get("url"),
                            detail=row.detail,
                            observed_at=row.observed_at,
                        )
                        for row in sorted(
                            rows, key=lambda r: (order.get(r.outcome, 9), r.resource_name.lower())
                        )
                    ],
                    counts={o: sum(1 for row in rows if row.outcome == o) for o in order},
                    last_run_at=max((row.observed_at for row in rows), default=None),
                    rationale=rationale,
                    evidence_kinds=list(check.evidence_kinds),
                    source="platform" if comp.is_platform(check.capabilities) else "connector",
                    availability=availability[check.key],
                    needs=self._needs(check, capability_rows, connected),
                )
            )

        capability_views = [
            CapabilityView(
                key=key,
                name=capabilities[key].name,
                description=capabilities[key].description,
                providers=[
                    ProviderOption(
                        key=option["key"],
                        name=option["name"],
                        status=option["status"],
                        phase=option["phase"],
                        connected=option["key"] in connected,
                        runs_check=any(
                            option["key"] in check.implementations
                            for check, _, _ in mapped
                            if key in check.capabilities
                        ),
                    )
                    for option in capabilities[key].providers
                ],
            )
            for key in sorted(
                needed, key=lambda k: capabilities[k].name if k in capabilities else k
            )
            if key in capabilities
        ]

        states = [test.status for test in tests]
        ran = [s for s in states if s in ("pass", "fail", "error", "not_applicable")]
        overall = _control_status(states)
        scope_counts = await self._scope_summaries(session, tenant_id, list(by_id))
        expected: list[dict[str, Any]] = []
        if control.template_id is not None:
            expected = (
                await control_service.template_evidence(session, template_ids={control.template_id})
            ).get(control.template_id, [])
        check_names = {check.key: (check.name, availability[check.key]) for check, _, _ in mapped}

        return AutomationView(
            control_id=control.id,
            mode=mode,
            status=overall,
            tests_total=len(tests),
            tests_running=len(ran),
            last_run_at=max(
                (run.finished_at for run in finished.values() if run.finished_at), default=None
            ),
            running=running,
            connection_ids=list(by_id),
            capabilities=capability_views,
            tests=tests,
            history=await self._history(session, tenant_id, check_ids, now),
            requests=await self.list_requests(session, tenant_id=tenant_id, control_id=control.id),
            # Scope is about repositories, so only a control that has a repository
            # level test shows it. An organisation setting has no scope to choose.
            scopes=[
                ConnectionScopeView(
                    connection_id=connection_id,
                    account=by_id[connection_id].account_login,
                    listed=summary.listed,
                    in_scope=summary.in_scope,
                    excluded=summary.excluded,
                )
                for connection_id, summary in scope_counts.items()
                if connection_id in by_id
                and any(c.resource_type == "repository" for c, _, _ in mapped)
            ],
            composition=comp.compose(check_facts, facts, connected, expected),
            evidence=self._evidence_views(expected, check_names),
            mappings=await control_service.control_mappings(
                session, tenant_id=tenant_id, control_id=control.id
            ),
        )

    async def _chain_inputs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        template_ids: set[uuid.UUID],
        *,
        with_outcomes: bool = False,
    ) -> tuple[
        dict[uuid.UUID, list[tuple[Check, str, str | None]]],
        dict[uuid.UUID, list[dict[str, Any]]],
        dict[str, comp.CapabilityFacts],
        set[str],
        _Outcomes,
    ]:
        """Everything the register and the criterion view need about many controls at once."""
        mapped: dict[uuid.UUID, list[tuple[Check, str, str | None]]] = defaultdict(list)
        if template_ids:
            for template_id, check, coverage, rationale in (
                await session.execute(
                    select(
                        ControlTemplateCheck.template_id,
                        Check,
                        ControlTemplateCheck.coverage,
                        ControlTemplateCheck.rationale,
                    )
                    .join(Check, Check.id == ControlTemplateCheck.check_id)
                    .where(ControlTemplateCheck.template_id.in_(template_ids))
                    .order_by(Check.name)
                )
            ).tuples():
                mapped[template_id].append((check, coverage, rationale))
        evidence = await control_service.template_evidence(session, template_ids=template_ids)
        _rows, facts = await self._capability_facts(session)
        connections = await self._active_connections(session, tenant_id)
        connected = {connection.provider for connection in connections}
        outcomes = (
            await self._outcomes_by_check(session, tenant_id, connections)
            if with_outcomes
            else _Outcomes()
        )
        return mapped, evidence, facts, connected, outcomes

    async def compositions(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[ControlComposition]:
        """What evidences each live control, for the register, in one pass."""
        links = await control_service.control_template_ids(session, tenant_id=tenant_id)
        mapped, evidence, facts, connected, _outcomes = await self._chain_inputs(
            session, tenant_id, set(links.values())
        )
        statuses = await self.automation_statuses(session, tenant_id=tenant_id)
        labels = await control_service.control_labels(session, tenant_id=tenant_id)
        out: list[ControlComposition] = []
        for control_id, template_id in links.items():
            code, name = labels.get(control_id, ("", ""))
            check_facts = [
                comp.CheckFacts(
                    key=check.key,
                    capabilities=list(check.capabilities),
                    implementations=list(check.implementations),
                )
                for check, _, _ in mapped.get(template_id, [])
            ]
            out.append(
                ControlComposition(
                    control_id=control_id,
                    code=code,
                    name=name,
                    composition=comp.compose(
                        check_facts, facts, connected, evidence.get(template_id, [])
                    ),
                    automation_status=statuses.get(control_id),
                )
            )
        return out

    async def control_chains(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        controls: list[tuple[uuid.UUID, uuid.UUID | None]],
    ) -> dict[uuid.UUID, ControlChain]:
        """The full chain behind each of these controls: checks, systems, expected evidence."""
        template_ids = {t for _, t in controls if t is not None}
        mapped, evidence, facts, connected, outcomes = await self._chain_inputs(
            session, tenant_id, template_ids, with_outcomes=True
        )
        statuses = await self.automation_statuses(session, tenant_id=tenant_id)
        chains: dict[uuid.UUID, ControlChain] = {}
        for control_id, template_id in controls:
            rows = mapped.get(template_id, []) if template_id is not None else []
            check_facts = [
                comp.CheckFacts(
                    key=check.key,
                    capabilities=list(check.capabilities),
                    implementations=list(check.implementations),
                )
                for check, _, _ in rows
            ]
            availability = {
                fact.key: comp.availability(fact, facts, connected) for fact in check_facts
            }
            items = evidence.get(template_id, []) if template_id is not None else []
            chains[control_id] = ControlChain(
                control_id=control_id,
                composition=comp.compose(check_facts, facts, connected, items),
                automation_status=statuses.get(control_id),
                checks=[
                    ChainCheck(
                        key=check.key,
                        name=check.name,
                        source="platform" if comp.is_platform(check.capabilities) else "connector",
                        availability=availability[check.key],
                        status=_test_status(
                            implemented=bool(check.implementations),
                            runners=availability[check.key] == "running",
                            outcomes=outcomes.by_check.get(check.id, []),
                            stale=outcomes.stale(check.implementations),
                            ran=outcomes.ran(check.implementations),
                        ),
                        coverage=coverage,
                        rationale=rationale,
                        evidence_kinds=list(check.evidence_kinds),
                        capabilities=list(check.capabilities),
                    )
                    for check, coverage, rationale in rows
                ],
                evidence=self._evidence_views(
                    items, {c.key: (c.name, availability[c.key]) for c, _, _ in rows}
                ),
            )
        return chains

    async def _outcomes_by_check(
        self, session: AsyncSession, tenant_id: uuid.UUID, connections: list[Connection]
    ) -> _Outcomes:
        """Each check's distinct outcomes in every connection's latest finished run, and
        which providers have not run recently enough for those outcomes to count."""
        if not connections:
            return _Outcomes()
        finished = await self._latest_finished(session, tenant_id, [c.id for c in connections])
        if not finished:
            return _Outcomes()
        now = datetime.now(UTC)
        stale_providers = {
            connection.provider
            for connection in connections
            if (run := finished.get(connection.id)) is not None
            and run.started_at < now - STALE_AFTER
        }
        earliest = min(run.started_at for run in finished.values())
        outcomes: dict[uuid.UUID, list[str]] = defaultdict(list)
        for check_id, outcome in (
            await session.execute(
                select(CheckResult.check_id, CheckResult.outcome)
                .where(
                    CheckResult.tenant_id == tenant_id,
                    CheckResult.run_id.in_([run.id for run in finished.values()]),
                    CheckResult.observed_at >= earliest,
                )
                .group_by(CheckResult.check_id, CheckResult.outcome)
            )
        ).tuples():
            outcomes[check_id].append(outcome)
        return _Outcomes(
            by_check=dict(outcomes),
            stale_providers=stale_providers,
            ran_providers={c.provider for c in connections if c.id in finished},
        )

    async def automation_statuses(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        """Each live control's automated status (AU-6), for every control at once.

        The dashboard asks this instead of opening each control's page. Only
        controls with real results appear. No test, no connection or no run yet
        is "not configured", which counts neither as passing nor as failing
        (AU-5): the caller falls back to the manual evidence path for those.
        """
        links = await control_service.control_template_ids(session, tenant_id=tenant_id)
        if not links:
            return {}
        connections = list(
            (
                await session.execute(
                    select(Connection).where(
                        Connection.tenant_id == tenant_id, Connection.status == "active"
                    )
                )
            ).scalars()
        )
        if not connections:
            return {}
        outcomes = await self._outcomes_by_check(session, tenant_id, connections)
        if not outcomes.by_check and not await self._latest_finished(
            session, tenant_id, [c.id for c in connections]
        ):
            return {}
        providers = {c.provider for c in connections}
        mapped = (
            await session.execute(
                select(ControlTemplateCheck.template_id, Check.id, Check.implementations).join(
                    Check, Check.id == ControlTemplateCheck.check_id
                )
            )
        ).all()
        checks_by_template: dict[uuid.UUID, list[tuple[uuid.UUID, list[str]]]] = defaultdict(list)
        for template_id, check_id, implementations in mapped:
            checks_by_template[template_id].append((check_id, list(implementations)))

        statuses: dict[uuid.UUID, str] = {}
        for control_id, template_id in links.items():
            states = [
                _test_status(
                    implemented=bool(implementations),
                    runners=bool(providers & set(implementations)),
                    outcomes=outcomes.by_check.get(check_id, []),
                    stale=outcomes.stale(implementations),
                    ran=outcomes.ran(implementations),
                )
                for check_id, implementations in checks_by_template.get(template_id, [])
            ]
            status = _control_status(states)
            if status in ("passing", "failing", "error", "stale", "not_applicable"):
                statuses[control_id] = status
        return statuses

    async def _latest_finished(
        self, session: AsyncSession, tenant_id: uuid.UUID, connection_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, CheckRun]:
        if not connection_ids:
            return {}
        rows = await session.execute(
            select(CheckRun)
            .where(
                CheckRun.tenant_id == tenant_id,
                CheckRun.connection_id.in_(connection_ids),
                CheckRun.status != "running",
            )
            .distinct(CheckRun.connection_id)
            .order_by(CheckRun.connection_id, CheckRun.started_at.desc())
        )
        return {run.connection_id: run for run in rows.scalars()}

    async def _history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        check_ids: list[uuid.UUID],
        now: datetime,
    ) -> list[DayView]:
        """One status per day for the last 30: a failure at any point marks the day."""
        if not check_ids:
            return []
        start = (now - timedelta(days=HISTORY_DAYS - 1)).date()
        # A UTC day, whatever the database session's time zone is.
        day = func.date_trunc("day", func.timezone("UTC", CheckResult.observed_at))
        rows = await session.execute(
            select(day, CheckResult.outcome)
            .where(
                CheckResult.tenant_id == tenant_id,
                CheckResult.check_id.in_(check_ids),
                CheckResult.observed_at >= datetime.combine(start, datetime.min.time(), UTC),
            )
            .group_by(day, CheckResult.outcome)
        )
        outcomes: dict[date, list[str]] = defaultdict(list)
        for when, outcome in rows.tuples():
            outcomes[when.date()].append(outcome)
        return [
            DayView(
                day=start + timedelta(days=offset),
                status=_worst(outcomes[start + timedelta(days=offset)])
                if outcomes.get(start + timedelta(days=offset))
                else "none",
            )
            for offset in range(HISTORY_DAYS)
        ]

    # -- integration requests ---------------------------------------------------------

    async def request_integration(  # noqa: PLR0913 — what is asked for, and why
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Membership,
        provider_name: str,
        capability_key: str | None,
        control_id: uuid.UUID | None,
        note: str | None,
    ) -> RequestView:
        name = provider_name.strip()
        if not name:
            raise InvalidInput("Name the system you use.", detail="empty provider name")
        if capability_key is not None and not await session.scalar(
            select(IntegrationCapability.id).where(IntegrationCapability.key == capability_key)
        ):
            raise InvalidInput(
                "That kind of system is not in the catalogue.", detail=capability_key
            )
        if control_id is not None:
            await control_service.get_control(session, tenant_id=tenant_id, control_id=control_id)
        row = IntegrationRequest(
            id=uuid7(),
            tenant_id=tenant_id,
            provider_name=name[:120],
            capability_key=capability_key,
            control_id=control_id,
            note=(note or "").strip()[:2000] or None,
            requested_by_membership_id=actor.id,
        )
        session.add(row)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="integration_request",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(row, fields=_REQUEST_SNAPSHOT),
        )
        await session.refresh(row)
        logger.info("connectors.integration_requested", capability=capability_key)
        return self._request_view(row)

    async def list_requests(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        control_id: uuid.UUID | None = None,
    ) -> list[RequestView]:
        query = select(IntegrationRequest).where(IntegrationRequest.tenant_id == tenant_id)
        if control_id is not None:
            query = query.where(IntegrationRequest.control_id == control_id)
        rows = await session.execute(query.order_by(IntegrationRequest.created_at.desc()))
        return [self._request_view(row) for row in rows.scalars()]

    @staticmethod
    def _request_view(row: IntegrationRequest) -> RequestView:
        return RequestView(
            id=row.id,
            provider_name=row.provider_name,
            capability_key=row.capability_key,
            control_id=row.control_id,
            note=row.note,
            status=row.status,
            created_at=row.created_at,
        )


connector_service = ConnectorService()
