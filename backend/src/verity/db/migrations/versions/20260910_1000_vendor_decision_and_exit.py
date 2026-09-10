"""vendor approvals, contracts, documents, monitoring and the exit (Week 5, section 4)

Fifteen tenant-owned tables, completing the ER's vendor set. RLS and grants land
with each of them (rule 12); vendor_approvals is additionally append-only.

It also DROPS vendor_assessments.decision. V3: the ER draws two decision enums
that disagree with each other — four-valued verbs on vendor_approvals and
three-valued participles on the assessment — and two tables holding overlapping
decision state is a data-integrity trap. The approval row is the record of who
decided what, when and why; the assessment is the work product and keeps its
status. Section 3 shipped the column by transcribing the ER before this was
settled, and no row has ever carried a value other than the default.

Constraints in here that carry policy rather than hygiene:

- ck_vendor_approvals__rationale_present. A decision with no reasoning is a
  signature with no basis, and it is the first thing an auditor asks to see.
- ck_vendor_intake_requests__rejection_has_reason. A refusal with no stated reason
  is the same request arriving next quarter with nobody able to say why it was
  turned down.
- ck_vendor_approval_conditions__waiver_has_reason.
- ck_vendor_subprocessors__not_self_referential.
- Three ordered-date checks, on document coverage, contract term and audit period.

Revision ID: d2f7b0a1e94c
Revises: c8e1a4b62f39
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, drop_append_only, enable_rls, grant_crud, make_append_only

revision: str = "d2f7b0a1e94c"
down_revision: str | None = "c8e1a4b62f39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_MEMBERSHIPS = "tenant_memberships.id"

# Restated rather than imported: a migration describes the schema at this revision.
ROSTER_ROLES = (
    "tprm_lead",
    "analyst",
    "security",
    "privacy",
    "legal",
    "procurement",
    "exec_approver",
    "it",
)
URGENCIES = ("low", "normal", "high")
INTAKE_SCREENING = ("pending", "passed", "flagged")
INTAKE_DECISIONS = ("pending", "approved", "auto_approved", "rejected")
APPROVAL_DECISIONS = ("approve", "approve_with_conditions", "defer", "reject")
CONDITION_STATUSES = ("open", "met", "overdue", "waived")
DOC_TYPES = (
    "soc_report",
    "iso_cert",
    "bridge_letter",
    "dpa",
    "pentest",
    "insurance",
    "financials",
    "bcdr",
    "policy",
)
DOC_COLLECTION_STATUSES = ("requested", "received", "reviewed")
SOC_REPORT_KINDS = ("soc1", "soc2", "soc3")
SOC_REPORT_TYPES = ("type_i", "type_ii")
SOC_OPINIONS = ("unqualified", "qualified", "adverse", "disclaimer")
CONTRACT_TYPES = ("master", "dpa", "sla", "security_addendum", "nda")
CONTRACT_STATUSES = ("draft", "active", "expired", "terminated")
SLA_STATUSES = ("on_track", "at_risk", "breached")
SUBPROCESSOR_PROVENANCE = ("vendor_declared", "auto_detected", "intelligence")
SUBPROCESSOR_STATUSES = ("active", "removed")
SCORECARD_PROVIDERS = ("securityscorecard", "bitsight", "upguard", "manual")
SIGNAL_TYPES = (
    "rating_change",
    "breach",
    "adverse_media",
    "financial",
    "sla_breach",
    "cert_expiry",
)
SIGNAL_SOURCE_CLASSES = (
    "rating_platform",
    "breach_intel",
    "media",
    "financial_provider",
    "internal",
)
SIGNAL_STATUSES = ("new", "acknowledged", "dismissed")
ALERT_ACTIONS = ("notify", "create_task", "trigger_reassessment")
ALERT_CHANNELS = ("in_app", "email", "slack")
DISCOVERED_DISPOSITIONS = ("pending", "added_as_vendor", "linked_to_vendor", "ignored")
COMMENT_AUTHOR_TYPES = ("internal_user", "vendor_contact")
COMMENT_VISIBILITY = ("internal_only", "vendor_shared")
SEVERITIES = ("critical", "high", "medium", "low")

# Creation order respects the foreign keys; downgrade drops the reverse.
_TABLES = (
    "vendor_approvals",
    "vendor_approval_conditions",
    "vendor_documents",
    "vendor_soc_report_reviews",
    "vendor_contracts",
    "vendor_slas",
    "vendor_subprocessors",
    "vendor_intake_requests",
    "vendor_team_roster",
    "vendor_offboardings",
    "vendor_scorecards",
    "vendor_signals",
    "vendor_alert_rules",
    "vendor_discovered_apps",
    "vendor_assessment_comments",
)
_APPEND_ONLY = "vendor_approvals"


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    joined = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({joined})", name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{table}__tenant_id"
    )


def _fk(table: str, column: str, target: str, ondelete: str = "CASCADE") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [target], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _jsonb(name: str, empty: str = "'[]'::jsonb") -> sa.Column[Any]:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=sa.text(empty))


def _integratable() -> tuple[sa.Column[Any], ...]:
    return (
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def _integration_unique(table: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(
        "tenant_id", "source", "external_id", name=f"uq_{table}__tenant_id_source_external_id"
    )


def _index(table: str, *cols: str) -> None:
    op.create_index(f"ix_{table}__tenant_id_{'_'.join(cols)}", table, ["tenant_id", *cols])


def _create_decision() -> None:
    op.create_table(
        "vendor_approvals",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("stage_id", _UUID, nullable=True),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        _jsonb("excluded_membership_ids"),
        sa.Column("decided_by_membership_id", _UUID, nullable=True),
        # Append-only: decided_at alone, no created_at/updated_at.
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=False),
        _tenant_fk("vendor_approvals"),
        _fk("vendor_approvals", "vendor_id", "vendors.id"),
        _fk("vendor_approvals", "engagement_id", "vendor_engagements.id"),
        # NO ACTION on both: SET NULL is an UPDATE, which the append-only trigger
        # refuses, which would fail the delete that triggered it.
        _fk("vendor_approvals", "stage_id", "vendor_stages.id", "NO ACTION"),
        _fk("vendor_approvals", "decided_by_membership_id", _MEMBERSHIPS, "NO ACTION"),
        _check("vendor_approvals", "decision", APPROVAL_DECISIONS),
        sa.CheckConstraint(
            "length(btrim(rationale)) > 0", name=conv("ck_vendor_approvals__rationale_present")
        ),
    )
    _index("vendor_approvals", "vendor_id")
    _index("vendor_approvals", "engagement_id", "cycle")
    _index("vendor_approvals", "stage_id")

    op.create_table(
        "vendor_approval_conditions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("approval_id", _UUID, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("task_id", _UUID, nullable=True),
        sa.Column("waived_reason", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("vendor_approval_conditions"),
        _fk("vendor_approval_conditions", "approval_id", "vendor_approvals.id"),
        _fk("vendor_approval_conditions", "owner_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_approval_conditions", "task_id", "tasks.id", "SET NULL"),
        _check("vendor_approval_conditions", "status", CONDITION_STATUSES),
        sa.CheckConstraint(
            "(status <> 'waived') OR (waived_reason IS NOT NULL)",
            name=conv("ck_vendor_approval_conditions__waiver_has_reason"),
        ),
    )
    _index("vendor_approval_conditions", "approval_id")
    _index("vendor_approval_conditions", "status")


def _create_paperwork() -> None:
    op.create_table(
        "vendor_documents",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("file_ref", sa.Text(), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("collection_status", sa.Text(), nullable=False, server_default="requested"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_membership_id", _UUID, nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("evidence_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("vendor_documents"),
        _fk("vendor_documents", "vendor_id", "vendors.id"),
        _fk("vendor_documents", "reviewed_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_documents", "evidence_id", "evidence.id", "SET NULL"),
        _check("vendor_documents", "doc_type", DOC_TYPES),
        _check("vendor_documents", "collection_status", DOC_COLLECTION_STATUSES),
        sa.CheckConstraint(
            "(issue_date IS NULL) OR (valid_until IS NULL) OR (valid_until >= issue_date)",
            name=conv("ck_vendor_documents__coverage_window_ordered"),
        ),
    )
    _index("vendor_documents", "vendor_id")
    _index("vendor_documents", "doc_type")
    _index("vendor_documents", "valid_until")

    op.create_table(
        "vendor_soc_report_reviews",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("document_id", _UUID, nullable=True),
        sa.Column("assessment_id", _UUID, nullable=True),
        sa.Column("report_kind", sa.Text(), nullable=False, server_default="soc2"),
        sa.Column("report_type", sa.Text(), nullable=False, server_default="type_ii"),
        sa.Column("audit_period_start", sa.Date(), nullable=True),
        sa.Column("audit_period_end", sa.Date(), nullable=True),
        _jsonb("tsc_included"),
        sa.Column("opinion", sa.Text(), nullable=False, server_default="unqualified"),
        sa.Column(
            "bridge_letter_received", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "findings_material", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("cuec_reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cuec_notes", sa.Text(), nullable=True),
        sa.Column("subservice_orgs", sa.Text(), nullable=True),
        sa.Column("cpa_firm", sa.Text(), nullable=True),
        sa.Column("reviewed_by_membership_id", _UUID, nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("vendor_soc_report_reviews"),
        _fk("vendor_soc_report_reviews", "vendor_id", "vendors.id"),
        _fk("vendor_soc_report_reviews", "document_id", "vendor_documents.id", "SET NULL"),
        _fk("vendor_soc_report_reviews", "assessment_id", "vendor_assessments.id", "SET NULL"),
        _fk("vendor_soc_report_reviews", "reviewed_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _check("vendor_soc_report_reviews", "report_kind", SOC_REPORT_KINDS),
        _check("vendor_soc_report_reviews", "report_type", SOC_REPORT_TYPES),
        _check("vendor_soc_report_reviews", "opinion", SOC_OPINIONS),
        sa.CheckConstraint(
            "(audit_period_start IS NULL) OR (audit_period_end IS NULL) OR "
            "(audit_period_end >= audit_period_start)",
            name=conv("ck_vendor_soc_report_reviews__period_ordered"),
        ),
    )
    _index("vendor_soc_report_reviews", "vendor_id")
    _index("vendor_soc_report_reviews", "audit_period_end")

    op.create_table(
        "vendor_contracts",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=True),
        sa.Column("contract_type", sa.Text(), nullable=False, server_default="master"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("breach_notification_hours", sa.Integer(), nullable=True),
        sa.Column("right_to_audit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "subprocessor_terms", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "exit_data_return_clause", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("file_ref", sa.Text(), nullable=True),
        sa.Column("evidence_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("vendor_contracts"),
        _fk("vendor_contracts", "vendor_id", "vendors.id"),
        _fk("vendor_contracts", "engagement_id", "vendor_engagements.id"),
        _fk("vendor_contracts", "evidence_id", "evidence.id", "SET NULL"),
        _check("vendor_contracts", "contract_type", CONTRACT_TYPES),
        _check("vendor_contracts", "status", CONTRACT_STATUSES),
        sa.CheckConstraint(
            "(start_date IS NULL) OR (end_date IS NULL) OR (end_date >= start_date)",
            name=conv("ck_vendor_contracts__term_ordered"),
        ),
    )
    _index("vendor_contracts", "vendor_id")
    _index("vendor_contracts", "status")
    _index("vendor_contracts", "renewal_date")

    op.create_table(
        "vendor_slas",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("contract_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("measurement", sa.Text(), nullable=True),
        sa.Column("measured_at", sa.Date(), nullable=True),
        sa.Column("cure_period_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="on_track"),
        *_ts(),
        _tenant_fk("vendor_slas"),
        _fk("vendor_slas", "contract_id", "vendor_contracts.id"),
        _fk("vendor_slas", "vendor_id", "vendors.id"),
        _check("vendor_slas", "status", SLA_STATUSES),
    )
    _index("vendor_slas", "contract_id")
    _index("vendor_slas", "vendor_id", "status")

    op.create_table(
        "vendor_subprocessors",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("service", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("data_location", sa.Text(), nullable=True),
        sa.Column("provenance", sa.Text(), nullable=False, server_default="vendor_declared"),
        sa.Column("linked_vendor_id", _UUID, nullable=True),
        sa.Column("notification_obligation", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        *_ts(),
        _tenant_fk("vendor_subprocessors"),
        _fk("vendor_subprocessors", "vendor_id", "vendors.id"),
        _fk("vendor_subprocessors", "linked_vendor_id", "vendors.id", "SET NULL"),
        _check("vendor_subprocessors", "provenance", SUBPROCESSOR_PROVENANCE),
        _check("vendor_subprocessors", "status", SUBPROCESSOR_STATUSES),
        sa.CheckConstraint(
            "linked_vendor_id IS NULL OR linked_vendor_id <> vendor_id",
            name=conv("ck_vendor_subprocessors__not_self_referential"),
        ),
    )
    _index("vendor_subprocessors", "vendor_id")
    _index("vendor_subprocessors", "linked_vendor_id")


def _create_intake_and_exit() -> None:
    op.create_table(
        "vendor_intake_requests",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("requested_by_membership_id", _UUID, nullable=True),
        sa.Column("vendor_name", sa.Text(), nullable=False),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("proposed_service", sa.Text(), nullable=False, server_default=sa.text("''")),
        _jsonb("data_types_shared"),
        sa.Column("urgency", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("screening_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("decision", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_membership_id", _UUID, nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_vendor_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("vendor_intake_requests"),
        _fk("vendor_intake_requests", "requested_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_intake_requests", "decided_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_intake_requests", "created_vendor_id", "vendors.id", "SET NULL"),
        _check("vendor_intake_requests", "urgency", URGENCIES),
        _check("vendor_intake_requests", "screening_status", INTAKE_SCREENING),
        _check("vendor_intake_requests", "decision", INTAKE_DECISIONS),
        sa.CheckConstraint(
            "(decision <> 'rejected') OR (decision_reason IS NOT NULL)",
            name=conv("ck_vendor_intake_requests__rejection_has_reason"),
        ),
    )
    _index("vendor_intake_requests", "decision")
    _index("vendor_intake_requests", "requested_by_membership_id")

    op.create_table(
        "vendor_team_roster",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("membership_id", _UUID, nullable=False),
        *_ts(),
        _tenant_fk("vendor_team_roster"),
        _fk("vendor_team_roster", "membership_id", _MEMBERSHIPS),
        _check("vendor_team_roster", "role", ROSTER_ROLES),
        sa.UniqueConstraint(
            "tenant_id", "role", "membership_id", name="uq_vendor_team_roster__role_member"
        ),
    )
    _index("vendor_team_roster", "role")

    op.create_table(
        "vendor_offboardings",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("access_revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_by_membership_id", _UUID, nullable=True),
        sa.Column("data_return_attested_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("attestation_assessment_id", _UUID, nullable=True),
        sa.Column(
            "contract_provisions_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "final_payments_settled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("certificate_evidence_id", _UUID, nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_ts(),
        _tenant_fk("vendor_offboardings"),
        _fk("vendor_offboardings", "vendor_id", "vendors.id"),
        _fk("vendor_offboardings", "engagement_id", "vendor_engagements.id"),
        _fk("vendor_offboardings", "revoked_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk(
            "vendor_offboardings", "attestation_assessment_id", "vendor_assessments.id", "SET NULL"
        ),
        _fk("vendor_offboardings", "certificate_evidence_id", "evidence.id", "SET NULL"),
    )
    _index("vendor_offboardings", "vendor_id")
    _index("vendor_offboardings", "engagement_id")


def _create_monitoring() -> None:
    op.create_table(
        "vendor_scorecards",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("overall_grade", sa.Text(), nullable=True),
        _jsonb("factor_scores", "'{}'::jsonb"),
        sa.Column("as_of", sa.TIMESTAMP(timezone=True), nullable=False),
        *_integratable(),
        *_ts(),
        _tenant_fk("vendor_scorecards"),
        _fk("vendor_scorecards", "vendor_id", "vendors.id"),
        _check("vendor_scorecards", "provider", SCORECARD_PROVIDERS),
        _integration_unique("vendor_scorecards"),
    )
    _index("vendor_scorecards", "vendor_id", "as_of")

    op.create_table(
        "vendor_signals",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("source_class", sa.Text(), nullable=False, server_default="internal"),
        sa.Column("severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("dedup_key", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="new"),
        sa.Column("acknowledged_by_membership_id", _UUID, nullable=True),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("triggered_assessment_id", _UUID, nullable=True),
        sa.Column("observed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *_integratable(),
        *_ts(),
        _tenant_fk("vendor_signals"),
        _fk("vendor_signals", "vendor_id", "vendors.id"),
        _fk("vendor_signals", "acknowledged_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_signals", "triggered_assessment_id", "vendor_assessments.id", "SET NULL"),
        _check("vendor_signals", "signal_type", SIGNAL_TYPES),
        _check("vendor_signals", "source_class", SIGNAL_SOURCE_CLASSES),
        _check("vendor_signals", "severity", SEVERITIES),
        _check("vendor_signals", "status", SIGNAL_STATUSES),
        _integration_unique("vendor_signals"),
        sa.UniqueConstraint("tenant_id", "dedup_key", name="uq_vendor_signals__dedup_key"),
    )
    _index("vendor_signals", "vendor_id", "status")
    _index("vendor_signals", "observed_at")

    op.create_table(
        "vendor_alert_rules",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        _jsonb("tier_scope"),
        _jsonb("signal_types"),
        sa.Column("min_severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("action", sa.Text(), nullable=False, server_default="notify"),
        sa.Column("channel", sa.Text(), nullable=False, server_default="in_app"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_ts(),
        _tenant_fk("vendor_alert_rules"),
        _check("vendor_alert_rules", "min_severity", SEVERITIES),
        _check("vendor_alert_rules", "action", ALERT_ACTIONS),
        _check("vendor_alert_rules", "channel", ALERT_CHANNELS),
    )
    _index("vendor_alert_rules", "is_enabled")

    op.create_table(
        "vendor_discovered_apps",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        # No FK: connector_connections does not exist yet.
        sa.Column("source_connection_id", _UUID, nullable=True),
        sa.Column("app_name", sa.Text(), nullable=False),
        _jsonb("oauth_scopes"),
        sa.Column("authorizing_users", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disposition", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("vendor_id", _UUID, nullable=True),
        *_integratable(),
        *_ts(),
        _tenant_fk("vendor_discovered_apps"),
        _fk("vendor_discovered_apps", "vendor_id", "vendors.id", "SET NULL"),
        _check("vendor_discovered_apps", "disposition", DISCOVERED_DISPOSITIONS),
        _integration_unique("vendor_discovered_apps"),
    )
    _index("vendor_discovered_apps", "disposition")

    op.create_table(
        "vendor_assessment_comments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("assessment_id", _UUID, nullable=False),
        sa.Column("question_id", _UUID, nullable=True),
        sa.Column("author_type", sa.Text(), nullable=False, server_default="internal_user"),
        # Polymorphic, like audit_log's actor: no FK, because one key cannot point
        # at a membership and a vendor contact at once.
        sa.Column("author_id", _UUID, nullable=True),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="internal_only"),
        sa.Column("body", sa.Text(), nullable=False),
        *_ts(),
        _tenant_fk("vendor_assessment_comments"),
        _fk("vendor_assessment_comments", "assessment_id", "vendor_assessments.id"),
        _check("vendor_assessment_comments", "author_type", COMMENT_AUTHOR_TYPES),
        _check("vendor_assessment_comments", "visibility", COMMENT_VISIBILITY),
    )
    # Not (assessment_id, visibility): that name is 65 characters and Postgres
    # truncates at 63, which would silently diverge from the model's.
    _index("vendor_assessment_comments", "assessment_id")


def upgrade() -> None:
    _create_decision()
    _create_paperwork()
    _create_intake_and_exit()
    _create_monitoring()

    for table in _TABLES:
        enable_rls(table)
        grant_crud(table)
    # After grant_crud: it revokes on top of the grant.
    make_append_only(_APPEND_ONLY)

    # V3. Two tables holding overlapping decision state is a data-integrity trap,
    # and vendor_approvals is the authoritative one.
    op.execute(
        sa.text(
            "ALTER TABLE vendor_assessments DROP CONSTRAINT IF EXISTS "
            "ck_vendor_assessments__decision_valid"
        )
    )
    op.drop_column("vendor_assessments", "decision")


def downgrade() -> None:
    op.add_column(
        "vendor_assessments",
        sa.Column("decision", sa.Text(), nullable=False, server_default="pending"),
    )
    op.execute(
        sa.text(
            "ALTER TABLE vendor_assessments ADD CONSTRAINT ck_vendor_assessments__decision_valid "
            "CHECK (decision IN ('pending', 'approved', 'approved_with_conditions', 'rejected'))"
        )
    )
    drop_append_only(_APPEND_ONLY)
    for table in reversed(_TABLES):
        disable_rls(table)
        op.drop_table(table)
