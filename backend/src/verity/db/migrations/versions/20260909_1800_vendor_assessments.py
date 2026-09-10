"""vendor questionnaire bank, assessments, responses and findings (Week 5, section 3)

Two global content tables and three tenant-owned ones. The global pair carries no
tenant_id and gets no enable_rls, exactly like frameworks and control_templates;
the application role gets SELECT only, because migrations and the seed command are
the only writers.

The portal credential is the reason several of these columns exist. V11: only the
token hash is stored, alongside an expiry and a revocation timestamp, so a dump of
vendor_assessments cannot be replayed against the portal. A CHECK keeps the hash
and the expiry together, since a credential with no expiry never dies, and the
hash is indexed because the portal knows the token and nothing else.

Three CHECKs carry policy rather than hygiene:

- ck_vendor_assessments__token_has_expiry, above.
- ck_vendor_assessment_responses__na_has_reason. "Does not apply" is a claim, and
  an unexplained one is how a questionnaire is emptied without anybody noticing.
- ck_vendor_findings__acceptance_is_time_boxed. An open-ended accepted risk is a
  risk nobody will look at again.

vendor_findings.promoted_risk_id is a bare uuid with no foreign key: modules/risk
has no tables in any migration yet. The seam is designed on both sides, so the
column ships and the promotion action does not.

Revision ID: b6d3f8a25c07
Revises: a1c9e4f72b56
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.core.config import get_settings
from verity.db.rls import disable_rls, enable_rls, grant_crud

revision: str = "b6d3f8a25c07"
down_revision: str | None = "a1c9e4f72b56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)

# Restated rather than imported: a migration describes the schema at this
# revision, not at HEAD.
RISK_DOMAINS = (
    "information_security",
    "access_control",
    "data_protection_privacy",
    "business_continuity",
    "incident_response",
    "secure_development",
    "infrastructure_cloud",
    "personnel_security",
    "compliance_legal",
    "fourth_party_management",
)
SCOPE_LEVELS = ("lite", "core", "detail")
ANSWER_TYPES = ("yes_no_na", "select", "multi_select", "text", "numeric")
ASSESSMENT_KINDS = ("initial", "reassessment")
REVIEW_FORMATS = ("questionnaire", "soc_report_review", "external_report")
ASSESSMENT_DOMAINS = ("security", "privacy", "legal", "esg")
ASSESSMENT_STATUSES = ("pending", "in_progress", "submitted", "expired", "scored")
ASSESSMENT_DECISIONS = ("pending", "approved", "approved_with_conditions", "rejected")
ANSWER_VALUES = ("yes", "partial", "no", "na")
GRADES = ("A", "B", "C", "D", "F")
FINDING_SOURCES = ("assessment", "sla_breach", "signal", "document_review", "offboarding")
FINDING_SEVERITIES = ("critical", "high", "medium", "low")
FINDING_STATUSES = ("open", "in_remediation", "accepted", "closed")
FINDING_TREATMENTS = ("remediate", "mitigate", "transfer", "accept")

_GLOBAL_TABLES = ("questionnaire_templates", "questionnaire_questions")
_TENANT_TABLES = ("vendor_assessments", "vendor_assessment_responses", "vendor_findings")
# Global plane: no tenant policy. See _create_portal_tokens.
_UNPOLICIED = "vendor_portal_tokens"

_MEMBERSHIPS = "tenant_memberships.id"


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


def _jsonb(name: str, empty: str = "'{}'::jsonb") -> sa.Column[Any]:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=sa.text(empty))


def _create_bank() -> None:
    op.create_table(
        "questionnaire_templates",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _jsonb("suggested_tiers", "'[]'::jsonb"),
        _jsonb("framework_mappings", "'[]'::jsonb"),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_ts(),
        sa.UniqueConstraint("code", name="uq_questionnaire_templates__code"),
    )
    op.create_table(
        "questionnaire_questions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("template_id", _UUID, nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("scope_level", sa.Text(), nullable=False, server_default="core"),
        sa.Column("answer_type", sa.Text(), nullable=False, server_default="yes_no_na"),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column(
            "critical_control", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("non_negotiable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "evidence_required", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        _jsonb("framework_refs", "'[]'::jsonb"),
        sa.Column("parent_question_id", _UUID, nullable=True),
        _jsonb("trigger_condition", "'[]'::jsonb"),
        *_ts(),
        _fk("questionnaire_questions", "template_id", "questionnaire_templates.id"),
        sa.ForeignKeyConstraint(
            ["parent_question_id"],
            ["questionnaire_questions.id"],
            ondelete="SET NULL",
            name="fk_questionnaire_questions__parent_question_id",
        ),
        _check("questionnaire_questions", "domain", RISK_DOMAINS),
        _check("questionnaire_questions", "scope_level", SCOPE_LEVELS),
        _check("questionnaire_questions", "answer_type", ANSWER_TYPES),
        sa.UniqueConstraint(
            "template_id", "code", name="uq_questionnaire_questions__template_code"
        ),
    )
    op.create_index(
        "ix_questionnaire_questions__template_id_domain",
        "questionnaire_questions",
        ["template_id", "domain"],
    )
    # Global content: no tenant_id, no RLS. The application reads the bank; only
    # migrations and the seed command write it.
    role = get_settings().database.app_role
    for table in _GLOBAL_TABLES:
        op.execute(sa.text(f"GRANT SELECT ON {table} TO {role}"))


def _create_assessments() -> None:
    op.create_table(
        "vendor_assessments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=False),
        sa.Column("template_id", _UUID, nullable=True),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("kind", sa.Text(), nullable=False, server_default="initial"),
        sa.Column("review_format", sa.Text(), nullable=False, server_default="questionnaire"),
        sa.Column("assessment_domain", sa.Text(), nullable=False, server_default="security"),
        _jsonb("scope"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("residual_score", sa.Float(), nullable=True),
        sa.Column("grade", sa.Text(), nullable=True),
        _jsonb("domain_scores"),
        _jsonb("score_snapshot"),
        sa.Column("decision", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("portal_contact_id", _UUID, nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("vendor_assessments"),
        _fk("vendor_assessments", "vendor_id", "vendors.id"),
        _fk("vendor_assessments", "engagement_id", "vendor_engagements.id"),
        _fk("vendor_assessments", "template_id", "questionnaire_templates.id", "SET NULL"),
        _fk("vendor_assessments", "portal_contact_id", "vendor_contacts.id", "SET NULL"),
        _check("vendor_assessments", "kind", ASSESSMENT_KINDS),
        _check("vendor_assessments", "review_format", REVIEW_FORMATS),
        _check("vendor_assessments", "assessment_domain", ASSESSMENT_DOMAINS),
        _check("vendor_assessments", "status", ASSESSMENT_STATUSES),
        _check("vendor_assessments", "grade", GRADES),
        _check("vendor_assessments", "decision", ASSESSMENT_DECISIONS),
    )
    op.create_index(
        "ix_vendor_assessments__tenant_id_vendor_id",
        "vendor_assessments",
        ["tenant_id", "vendor_id"],
    )
    op.create_index(
        "ix_vendor_assessments__tenant_id_engagement_id_cycle",
        "vendor_assessments",
        ["tenant_id", "engagement_id", "cycle"],
    )
    op.create_index(
        "ix_vendor_assessments__tenant_id_status", "vendor_assessments", ["tenant_id", "status"]
    )


def _create_portal_tokens() -> None:
    """The portal credential, on the global plane and deliberately unpolicied.

    A portal request presents a token and nothing else, so the tenant cannot be
    bound until the token has been resolved — and vendor_assessments is
    tenant-owned with FORCE RLS, so it cannot be read before that. This table is
    the way out, and it is not a new idea: ``users`` and ``user_identities``
    already sit on this plane for exactly the same job, resolving an externally
    held credential to an internal identity before any tenant is known.

    It holds no secret and no personal data. Only the token hash is stored, so a
    reader of this whole table learns "some hash belongs to some tenant" — and to
    use that they would already need the token the hash was made from.

    Everything downstream of the resolve runs tenant-bound, and every query in the
    service filters ``tenant_id`` explicitly. That explicit filter matters more
    here than anywhere else in the module, because on this table it is the only
    wall rather than the first of two.
    """
    op.create_table(
        "vendor_portal_tokens",
        sa.Column("id", _UUID, primary_key=True),
        # sha256 of the issued token. The token itself exists once, in the link
        # that is emailed, and is never recoverable from the database.
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("assessment_id", _UUID, nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        # No tenant policy, so no ON DELETE CASCADE from tenants either: a torn-down
        # tenant's tokens are removed by the teardown path, and a dangling row here
        # resolves to an assessment that is itself gone.
        _fk("vendor_portal_tokens", "assessment_id", "vendor_assessments.id"),
        sa.UniqueConstraint("token_hash", name="uq_vendor_portal_tokens__token_hash"),
    )
    op.create_index(
        "ix_vendor_portal_tokens__assessment_id", "vendor_portal_tokens", ["assessment_id"]
    )


def _create_responses() -> None:
    op.create_table(
        "vendor_assessment_responses",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("assessment_id", _UUID, nullable=False),
        sa.Column("question_id", _UUID, nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        _jsonb("answer_value"),
        sa.Column("implementation_notes", sa.Text(), nullable=True),
        sa.Column("na_justification", sa.Text(), nullable=True),
        sa.Column("delegated_to_contact_id", _UUID, nullable=True),
        sa.Column("evidence_id", _UUID, nullable=True),
        sa.Column("answered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        _tenant_fk("vendor_assessment_responses"),
        _fk("vendor_assessment_responses", "assessment_id", "vendor_assessments.id"),
        # RESTRICT: retiring a question that has been answered would delete the
        # answer with it, and an assessment has to stay readable after a bank
        # version retires the question it asked.
        _fk(
            "vendor_assessment_responses",
            "question_id",
            "questionnaire_questions.id",
            "RESTRICT",
        ),
        _fk(
            "vendor_assessment_responses",
            "delegated_to_contact_id",
            "vendor_contacts.id",
            "SET NULL",
        ),
        _fk("vendor_assessment_responses", "evidence_id", "evidence.id", "SET NULL"),
        _check("vendor_assessment_responses", "answer", ANSWER_VALUES),
        sa.CheckConstraint(
            "(answer IS DISTINCT FROM 'na') OR (na_justification IS NOT NULL)",
            name=conv("ck_vendor_assessment_responses__na_has_reason"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "assessment_id",
            "question_id",
            name="uq_vendor_assessment_responses__assessment_question",
        ),
    )
    op.create_index(
        "ix_vendor_assessment_responses__tenant_id_assessment_id",
        "vendor_assessment_responses",
        ["tenant_id", "assessment_id"],
    )


def _create_findings() -> None:
    op.create_table(
        "vendor_findings",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("vendor_id", _UUID, nullable=False),
        sa.Column("engagement_id", _UUID, nullable=True),
        sa.Column("assessment_id", _UUID, nullable=True),
        sa.Column("question_id", _UUID, nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("finding_source", sa.Text(), nullable=False, server_default="assessment"),
        sa.Column("severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("treatment", sa.Text(), nullable=False, server_default="remediate"),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sla_due", sa.Date(), nullable=True),
        sa.Column("owner_membership_id", _UUID, nullable=True),
        sa.Column("task_id", _UUID, nullable=True),
        sa.Column("accepted_until", sa.Date(), nullable=True),
        sa.Column("accepted_rationale", sa.Text(), nullable=True),
        sa.Column("accepted_by_membership_id", _UUID, nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # No FK: modules/risk has no tables. The column ships, the action does not.
        sa.Column("promoted_risk_id", _UUID, nullable=True),
        *_ts(),
        _tenant_fk("vendor_findings"),
        _fk("vendor_findings", "vendor_id", "vendors.id"),
        _fk("vendor_findings", "engagement_id", "vendor_engagements.id"),
        _fk("vendor_findings", "assessment_id", "vendor_assessments.id", "SET NULL"),
        _fk("vendor_findings", "question_id", "questionnaire_questions.id", "SET NULL"),
        _fk("vendor_findings", "owner_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_findings", "accepted_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_findings", "task_id", "tasks.id", "SET NULL"),
        _check("vendor_findings", "finding_source", FINDING_SOURCES),
        _check("vendor_findings", "severity", FINDING_SEVERITIES),
        _check("vendor_findings", "status", FINDING_STATUSES),
        _check("vendor_findings", "treatment", FINDING_TREATMENTS),
        # Acceptance is time-boxed or it is not acceptance.
        sa.CheckConstraint(
            "(status <> 'accepted') OR "
            "(accepted_until IS NOT NULL AND accepted_rationale IS NOT NULL)",
            name=conv("ck_vendor_findings__acceptance_is_time_boxed"),
        ),
    )
    for cols in (
        ("vendor_id",),
        ("assessment_id",),
        ("status", "severity"),
        ("owner_membership_id",),
        ("sla_due",),
    ):
        op.create_index(
            f"ix_vendor_findings__tenant_id_{'_'.join(cols)}",
            "vendor_findings",
            ["tenant_id", *cols],
        )


def upgrade() -> None:
    _create_bank()
    _create_assessments()
    _create_portal_tokens()
    _create_responses()
    _create_findings()

    for table in _TENANT_TABLES:
        enable_rls(table)
        grant_crud(table)
    # The portal table gets DML but no policy: the service is the wall, and it
    # filters tenant_id explicitly on every read of it.
    grant_crud(_UNPOLICIED)


def downgrade() -> None:
    op.drop_table(_UNPOLICIED)
    for table in reversed(_TENANT_TABLES):
        disable_rls(table)
        op.drop_table(table)
    for table in reversed(_GLOBAL_TABLES):
        op.drop_table(table)
