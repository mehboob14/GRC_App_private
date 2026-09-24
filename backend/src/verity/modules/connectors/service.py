"""Connectors: connect a provider, run its checks, and say what they mean for a control.

A run is three short steps on purpose. Starting it takes a row lock on the
connection, so two clicks cannot start two runs. Collecting talks to the provider
for as long as it takes, outside any database transaction. Finishing writes the
results, the evidence file and the connection's health together in one
transaction, so a half finished run never leaves half its results behind.

Rule 7 runs through all of it: a token the provider refuses, a permission the
token lacks, a rate limit or an outage is recorded as ``error``, never ``fail``,
and the control page reads "could not check", never "failing".
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
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
from verity.modules.compliance.control_service import control_service
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
    Check,
    CheckResult,
    CheckRun,
    Connection,
    ControlTemplateCheck,
    IntegrationCapability,
    IntegrationRequest,
)
from verity.modules.evidence.service import evidence_service
from verity.shared.ids import uuid7

logger = get_logger(__name__)

STALE_RUN: Final = timedelta(minutes=30)
"""A run still marked running after this stopped without finishing (a restart)."""
SCHEDULE_INTERVAL: Final = timedelta(hours=20)
"""A daily check is due once its connection's last run is older than this."""
EVIDENCE_REFRESH: Final = timedelta(hours=20)
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
    """passing, failing, error, pending, not_connected, or manual."""
    tests_total: int
    tests_running: int
    last_run_at: datetime | None
    running: bool
    connection_ids: list[uuid.UUID]
    capabilities: list[CapabilityView]
    tests: list[TestView]
    history: list[DayView]
    requests: list[RequestView] = field(default_factory=list)


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


def _connection_view(row: Connection, run: CheckRun | None, now: datetime) -> ConnectionView:
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
    )


def _worst(outcomes: list[str]) -> str:
    """Fail beats error beats pass (rule 7 keeps error from ever reading as fail)."""
    for outcome in ("fail", "error", "pass"):
        if outcome in outcomes:
            return outcome
    return "not_applicable"


def _digest(results: list[github.Result]) -> str:
    rows = sorted((r.check_key, r.resource_type, r.resource_id, r.outcome) for r in results)
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


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
        now = datetime.now(UTC)
        return [_connection_view(row, runs.get(row.id), now) for row in rows]

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
        try:
            async with self._client(token) as http:
                snapshot = await github.collect(
                    http, login=login, account_type=account_type, now=datetime.now(UTC)
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
                run.evidence_id = await self._evidence(
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
    ) -> uuid.UUID | None:
        """File the snapshot as evidence on every control its checks map to.

        At most one file a day per connection unless the results changed: a person
        clicking Run now five times gets one evidence item, not five.
        """
        previous = (
            await session.execute(
                select(CheckRun.results_digest, CheckRun.finished_at)
                .where(
                    CheckRun.tenant_id == tenant_id,
                    CheckRun.connection_id == connection.id,
                    CheckRun.evidence_id.is_not(None),
                    CheckRun.id != run.id,
                )
                .order_by(CheckRun.finished_at.desc())
                .limit(1)
            )
        ).first()
        if (
            previous is not None
            and previous.results_digest == run.results_digest
            and previous.finished_at is not None
            and previous.finished_at > now - EVIDENCE_REFRESH
        ):
            return None

        check_ids = {row.check_id for row in rows if row.outcome in ("pass", "fail")}
        template_ids = set(
            (
                await session.execute(
                    select(ControlTemplateCheck.template_id).where(
                        ControlTemplateCheck.check_id.in_(check_ids)
                    )
                )
            ).scalars()
        )
        control_ids = await control_service.control_ids_for_templates(
            session, tenant_id=tenant_id, template_ids=template_ids
        )
        name = _PROVIDER_NAMES.get(connection.provider, connection.provider)
        keys = {row.id: row.key for row in (await session.execute(select(Check))).scalars()}
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
                "results": [
                    {
                        "check": keys.get(row.check_id),
                        "resource": row.resource_name,
                        "outcome": row.outcome,
                        "summary": row.detail.get("summary"),
                    }
                    for row in rows
                ],
            },
            "snapshot": snapshot,
        }
        data = json.dumps(document, indent=2, default=str).encode()
        view = await evidence_service.add_file(
            session,
            tenant_id=tenant_id,
            actor=actor,
            title=f"{name} {connection.account_login}: automated test results",
            filename=f"{connection.provider}-{connection.account_login}-{now:%Y%m%dT%H%MZ}.json",
            data=data,
            evidence_type="configuration_export",
            collected_at=now.date(),
            description=(
                f"{run.passed} passed, {run.failed} failed and {run.errored} could not be "
                f"checked across {run.resources} resources. Collected read only by the "
                f"{name} connector."
            ),
            source_label=f"{name} connector",
            owner_membership_id=connection.created_by_membership_id,
            renewal_date=now.date() + timedelta(days=EVIDENCE_VALIDITY_DAYS),
            control_ids=control_ids,
        )
        return view.id

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

    async def control_automation(  # noqa: PLR0912 — one read that assembles the page
        self, session: AsyncSession, *, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> AutomationView:
        control = await control_service.get_control(
            session, tenant_id=tenant_id, control_id=control_id
        )
        mode = {"Automated": "automated", "Hybrid": "hybrid"}.get(
            control.control_sub_type or "", "manual"
        )
        mapped: list[tuple[Check, str]] = []
        if control.template_id is not None:
            mapped = [
                (check, coverage)
                for check, coverage in (
                    await session.execute(
                        select(Check, ControlTemplateCheck.coverage)
                        .join(ControlTemplateCheck, ControlTemplateCheck.check_id == Check.id)
                        .where(ControlTemplateCheck.template_id == control.template_id)
                        .order_by(Check.name)
                    )
                ).tuples()
            ]
        needed = {key for check, _ in mapped for key in check.capabilities}
        capabilities = {
            row.key: row
            for row in (
                await session.execute(
                    select(IntegrationCapability).where(IntegrationCapability.key.in_(needed))
                )
            ).scalars()
        }
        connections = list(
            (
                await session.execute(
                    select(Connection).where(
                        Connection.tenant_id == tenant_id, Connection.status == "active"
                    )
                )
            ).scalars()
        )
        connected = {connection.provider for connection in connections}
        # Only connections that can run one of this control's checks speak for it:
        # a GitHub run says nothing about when laptops were last checked.
        by_id = {
            connection.id: connection
            for connection in connections
            if any(connection.provider in check.implementations for check, _ in mapped)
        }
        now = datetime.now(UTC)
        latest = await self._latest_runs(session, tenant_id, list(by_id))
        running = any(
            run.status == "running" and run.started_at > now - STALE_RUN for run in latest.values()
        )
        finished = await self._latest_finished(session, tenant_id, list(by_id))

        results_by_check: dict[uuid.UUID, list[CheckResult]] = defaultdict(list)
        check_ids = [check.id for check, _ in mapped]
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

        tests: list[TestView] = []
        for check, coverage in mapped:
            runners = [c for c in connections if c.provider in check.implementations]
            rows = results_by_check.get(check.id, [])
            if not check.implementations:
                status = "not_available"
            elif not runners:
                status = "not_connected"
            elif not rows:
                status = "pending"
            else:
                status = _worst([row.outcome for row in rows])
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
                            for check, _ in mapped
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
        if not tests:
            overall = "manual"
        elif "fail" in states:
            overall = "failing"
        elif "error" in states:
            overall = "error"
        elif "pass" in states or ran:
            overall = "passing"
        elif "pending" in states:
            overall = "pending"
        else:
            overall = "not_connected"

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
        )

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
