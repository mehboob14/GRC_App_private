"""Connectors: shipped check content, and each workspace's connections, runs and results.

Checks are global content like requirements (ER 3.10). A check names the
capabilities it needs (version control, identity provider) rather than one
vendor, and one connected provider per capability is enough. The capability
lists which providers can supply it and when each arrives, which is what the
control page shows. ``control_template_checks`` maps checks to the stable
control template, so a check arrives already mapped in every workspace.

``check_results`` is the one high volume table: append only (rule 3) and range
partitioned by month on ``observed_at`` from its first migration (ER 5.9). Its
primary key carries ``observed_at`` because Postgres requires the partition key
in every unique constraint on a partitioned table.

A connection's credential is envelope encrypted before it reaches this table
(rule 6). The ciphertext is bound to its row through the AAD, and disconnecting
destroys it; the row itself stays, because its runs and results are history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Final, NoReturn

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, event, func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import (
    Base,
    TenantScoped,
    Timestamped,
    UUIDPrimaryKey,
    status_check,
    tenant_index,
)
from verity.shared.ids import uuid7

PROVIDERS: Final[tuple[str, ...]] = ("github",)
"""Providers a workspace can connect today. The catalogue lists many more; each
joins this tuple when its collector ships."""

ACCOUNT_TYPES: Final[tuple[str, ...]] = ("organization", "user")
CONNECTION_STATUSES: Final[tuple[str, ...]] = ("active", "disconnected")
RUN_TRIGGERS: Final[tuple[str, ...]] = ("manual", "schedule")
RUN_STATUSES: Final[tuple[str, ...]] = ("running", "completed", "failed")
OUTCOMES: Final[tuple[str, ...]] = ("pass", "fail", "error", "not_applicable")
"""Rule 7: ``error`` means Verity could not tell, never that the control failed."""
COVERAGE: Final[tuple[str, ...]] = ("full", "partial")
FREQUENCIES: Final[tuple[str, ...]] = ("daily", "weekly")
REQUEST_STATUSES: Final[tuple[str, ...]] = ("open", "planned", "available", "declined")
SCOPE_STATES: Final[tuple[str, ...]] = ("in_scope", "excluded")
SCOPE_DECIDERS: Final[tuple[str, ...]] = ("system", "person")
"""Who put a resource in or out of scope. A system decision (an archived repository,
a fork) is re-derived on every run; a person's decision is sticky until a person
changes it, which is what makes an exclusion something an auditor can rely on."""

_MEMBERSHIP_FK: Final = "tenant_memberships.id"


# -- global content (no tenant_id, SELECT only for the app role) -----------------


class IntegrationCapability(UUIDPrimaryKey, Timestamped, Base):
    """A kind of system a check reads, and the providers that offer it.

    ``providers`` is a list of ``{key, name, status, phase}``: ``status`` is
    ``available`` (a collector ships), ``planned`` (on the delivery plan, with its
    phase) or ``not_planned`` (outside the signed catalogue; a workspace can
    request it).
    """

    __tablename__ = "integration_capabilities"

    key: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    description: Mapped[str]
    providers: Mapped[list[dict[str, Any]]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )


class Check(UUIDPrimaryKey, Timestamped, Base):
    """One automatable assertion, written once for every provider that can run it.

    ``capabilities`` are all required; any one provider per capability satisfies
    it. ``implementations`` names the providers whose collector evaluates this
    check today, so a capability can be connectable while one of its checks is
    still to come.
    """

    __tablename__ = "checks"

    key: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    description: Mapped[str]
    capabilities: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    implementations: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    resource_type: Mapped[str]
    frequency: Mapped[str] = mapped_column(default="daily", server_default=text("'daily'"))
    remediation: Mapped[str]
    # The artifacts this check collects (a branch protection setting, a pull
    # request, a CI run), by name. What an auditor is shown, not what it is called.
    evidence_kinds: Mapped[list[str]] = mapped_column(
        postgresql.JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (status_check("checks", "frequency", FREQUENCIES),)


class ControlTemplateCheck(UUIDPrimaryKey, Timestamped, Base):
    """Which checks evidence which control template, and how much of it.

    ``coverage`` is ``full`` only when passing this check alone verifies the whole
    control, and ``partial`` when it verifies part of it. ``rationale`` says which
    part, and what the check does not prove.
    """

    __tablename__ = "control_template_checks"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("control_templates.id", ondelete="CASCADE")
    )
    check_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checks.id", ondelete="CASCADE"))
    coverage: Mapped[str] = mapped_column(default="partial")
    rationale: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint("template_id", "check_id", name="uq_control_template_checks__pair"),
        status_check("control_template_checks", "coverage", COVERAGE),
    )


# -- tenant plane (forced RLS) ---------------------------------------------------


class Connection(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A workspace's read only link to one provider account."""

    __tablename__ = "connections"

    provider: Mapped[str]
    account_login: Mapped[str]
    account_type: Mapped[str]
    display_name: Mapped[str]
    status: Mapped[str] = mapped_column(default="active", server_default=text("'active'"))
    credential_ciphertext: Mapped[str | None] = mapped_column(default=None)
    credential_hint: Mapped[str | None] = mapped_column(default=None)
    credential_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    last_run_at: Mapped[datetime | None] = mapped_column(default=None)
    last_success_at: Mapped[datetime | None] = mapped_column(default=None)
    last_error: Mapped[str | None] = mapped_column(default=None)
    error_streak: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    created_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(default=None)
    disconnected_reason: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("connections", "provider", PROVIDERS),
        status_check("connections", "account_type", ACCOUNT_TYPES),
        status_check("connections", "status", CONNECTION_STATUSES),
        # An active connection must hold its credential; a disconnected one never does.
        CheckConstraint(
            "(status = 'active') = (credential_ciphertext IS NOT NULL)",
            name=conv("ck_connections__credential_only_while_active"),
        ),
        Index(
            "uq_connections__tenant_id_provider_account_login",
            "tenant_id",
            "provider",
            "account_login",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    def __repr__(self) -> str:
        # Never the ciphertext: it is not secret on its own, but it has no business
        # in a log line either.
        return f"Connection(id={self.id!r}, provider={self.provider!r}, status={self.status!r})"


class ConnectionResource(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Something a connection can see, and whether its checks look at it (AU-9).

    The inventory a run discovers, and the scope decision beside each item. A
    SOC 2 engagement covers named systems, not everything a token can reach: a
    personal account holds forks, coursework and empty repositories that no
    auditor will ask about, and judging them fills the control page with noise
    nobody can act on.

    ``source``, ``external_id`` and ``synced_at`` are here from the start because
    this is exactly what a discovery connector fills (rule 9), and it is the
    natural feed for the asset inventory later.
    """

    __tablename__ = "connection_resources"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE")
    )
    resource_type: Mapped[str] = mapped_column(
        default="repository", server_default=text("'repository'")
    )
    source: Mapped[str]
    external_id: Mapped[str]
    name: Mapped[str]
    url: Mapped[str | None] = mapped_column(default=None)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    scope: Mapped[str] = mapped_column(default="in_scope", server_default=text("'in_scope'"))
    scope_reason: Mapped[str | None] = mapped_column(default=None)
    decided_by: Mapped[str] = mapped_column(default="system", server_default=text("'system'"))
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    synced_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        status_check("connection_resources", "scope", SCOPE_STATES),
        status_check("connection_resources", "decided_by", SCOPE_DECIDERS),
        # An exclusion with no stated reason is a repository quietly dropped from
        # the audit, which is the thing this table exists to prevent.
        CheckConstraint(
            "(scope <> 'excluded') OR (scope_reason IS NOT NULL)",
            name=conv("ck_connection_resources__exclusion_has_reason"),
        ),
        UniqueConstraint(
            "tenant_id", "connection_id", "external_id", name="uq_connection_resources__external_id"
        ),
        tenant_index("connection_resources", "connection_id", "scope"),
    )


class CheckRun(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One collection from one connection: when, why, and what it found."""

    __tablename__ = "check_runs"

    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connections.id"))
    trigger: Mapped[str]
    triggered_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )
    status: Mapped[str] = mapped_column(default="running", server_default=text("'running'"))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    resources: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    passed: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    failed: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    errored: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(default=None)
    results_digest: Mapped[str | None] = mapped_column(default=None)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("check_runs", "trigger", RUN_TRIGGERS),
        status_check("check_runs", "status", RUN_STATUSES),
        tenant_index("check_runs", "connection_id", "started_at"),
    )


class CheckResult(TenantScoped, Base):
    """One check on one resource in one run. Insert only, partitioned by month."""

    __tablename__ = "check_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    observed_at: Mapped[datetime] = mapped_column(primary_key=True, server_default=func.now())
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("check_runs.id"))
    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connections.id"))
    check_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checks.id"))
    resource_type: Mapped[str]
    resource_id: Mapped[str]
    resource_name: Mapped[str]
    outcome: Mapped[str]
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        status_check("check_results", "outcome", OUTCOMES),
        tenant_index("check_results", "check_id", "observed_at"),
        tenant_index("check_results", "run_id"),
        {"postgresql_partition_by": "RANGE (observed_at)"},
    )


class CheckResultAppendOnlyError(RuntimeError):
    """An ORM update or delete of a check result. The database refuses it too."""


@event.listens_for(CheckResult, "before_update")
def _refuse_update(_mapper: object, _connection: object, _target: object) -> NoReturn:
    raise CheckResultAppendOnlyError("check_results is append-only: UPDATE is not permitted")


@event.listens_for(CheckResult, "before_delete")
def _refuse_delete(_mapper: object, _connection: object, _target: object) -> NoReturn:
    raise CheckResultAppendOnlyError("check_results is append-only: DELETE is not permitted")


class IntegrationRequest(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A workspace asking for a system Verity cannot connect to yet."""

    __tablename__ = "integration_requests"

    provider_name: Mapped[str]
    capability_key: Mapped[str | None] = mapped_column(default=None)
    control_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("controls.id", ondelete="SET NULL"), default=None
    )
    note: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="open", server_default=text("'open'"))
    requested_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(_MEMBERSHIP_FK, ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        status_check("integration_requests", "status", REQUEST_STATUSES),
        tenant_index("integration_requests", "created_at"),
    )
