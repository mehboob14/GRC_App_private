"""tenant-built vendor questionnaires, for tiering and for due diligence

V5 shipped the questionnaire bank as global content and named a tenant-authored
bank as Phase 2, "its own table with tenant_id and RLS rather than a nullable
column retrofitted onto global content". These are those tables.

Two purposes share one builder. A tiering questionnaire is internal: our own
people answer it about how we use a vendor, and it sets the tier. A due diligence
questionnaire goes to the vendor through the portal, and it sets the residual
score. Both are sections of typed questions (single and multiple choice, text,
number, date, file) with options, scores and rules.

Nothing already written changes meaning:

- vendor_tiering_assessments keeps its five factor columns for the runs made
  before this revision, and they go nullable because a questionnaire run fills
  answers and questionnaire_snapshot instead.
- vendor_assessment_responses gains question_key and question_snapshot. A row now
  answers either a bank question (question_id, as before) or a question copied
  from a tenant questionnaire at dispatch. A CHECK keeps it to exactly one, and
  the yes/partial/no/na vocabulary now binds bank rows only.
- The bank tables gain purpose, section, help_text, options and required so the
  library can ship typed questions. Existing bank rows keep their types.

Revision ID: f3b8d2c6a915
Revises: e5a9c3d17b42
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import enable_rls, grant_crud

revision: str = "f3b8d2c6a915"
down_revision: str | None = "e5a9c3d17b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)

# Restated rather than imported: a migration describes the schema at this revision.
PURPOSES = ("tiering", "due_diligence")
STATUSES = ("active", "archived")
QUESTION_TYPES = ("single_choice", "multi_choice", "text", "paragraph", "number", "date", "file")
EVIDENCE_RULES = ("none", "optional", "required")
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
OLD_BANK_TYPES = ("yes_no_na", "select", "multi_select", "text", "numeric")
BANK_TYPES = (
    *OLD_BANK_TYPES,
    "single_choice",
    "multi_choice",
    "paragraph",
    "number",
    "date",
    "file",
)
FACTORS = (
    "data_sensitivity",
    "business_criticality",
    "system_access",
    "regulatory_scope",
    "fourth_party_reliance",
)

_TENANT_TABLES = ("vendor_questionnaires", "vendor_questionnaire_questions")
_MEMBERSHIPS = "tenant_memberships.id"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _check(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    return sa.CheckConstraint(_in(column, values), name=conv(f"ck_{table}__{column}_valid"))


def _ts() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _jsonb(name: str, empty: str = "'{}'::jsonb") -> sa.Column[Any]:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=sa.text(empty))


def _fk(table: str, column: str, target: str, ondelete: str = "CASCADE") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [target], ondelete=ondelete, name=f"fk_{table}__{column}"
    )


def _library_upgrade() -> None:
    op.add_column(
        "questionnaire_templates",
        sa.Column("purpose", sa.Text(), nullable=False, server_default="due_diligence"),
    )
    op.create_check_constraint(
        conv("ck_questionnaire_templates__purpose_valid"),
        "questionnaire_templates",
        _in("purpose", PURPOSES),
    )
    # A tiering library question measures exposure and has no control domain.
    op.alter_column("questionnaire_questions", "domain", nullable=True)
    op.add_column("questionnaire_questions", sa.Column("section", sa.Text(), nullable=True))
    op.add_column("questionnaire_questions", sa.Column("help_text", sa.Text(), nullable=True))
    op.add_column("questionnaire_questions", _jsonb("options", "'[]'::jsonb"))
    op.add_column(
        "questionnaire_questions",
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_constraint(
        conv("ck_questionnaire_questions__answer_type_valid"), "questionnaire_questions"
    )
    op.create_check_constraint(
        conv("ck_questionnaire_questions__answer_type_valid"),
        "questionnaire_questions",
        _in("answer_type", BANK_TYPES),
    )


def _create_questionnaires() -> None:
    op.create_table(
        "vendor_questionnaires",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _jsonb("default_tiers", "'[]'::jsonb"),
        _jsonb("tier_thresholds"),
        sa.Column("library_code", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", _UUID, nullable=True),
        sa.Column("updated_by_membership_id", _UUID, nullable=True),
        *_ts(),
        _fk("vendor_questionnaires", "tenant_id", "tenants.id"),
        _fk("vendor_questionnaires", "created_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _fk("vendor_questionnaires", "updated_by_membership_id", _MEMBERSHIPS, "SET NULL"),
        _check("vendor_questionnaires", "purpose", PURPOSES),
        _check("vendor_questionnaires", "status", STATUSES),
    )
    op.create_index(
        "ix_vendor_questionnaires__tenant_id_purpose_status",
        "vendor_questionnaires",
        ["tenant_id", "purpose", "status"],
    )
    # One tiering default per tenant, or the tiering dialog would have to guess.
    op.create_index(
        "uq_vendor_questionnaires__tenant_id_default_tiering",
        "vendor_questionnaires",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("purpose = 'tiering' AND is_default"),
    )

    op.create_table(
        "vendor_questionnaire_questions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("questionnaire_id", _UUID, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("section", sa.Text(), nullable=False, server_default="General"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("answer_type", sa.Text(), nullable=False, server_default="single_choice"),
        _jsonb("options", "'[]'::jsonb"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="none"),
        _jsonb("evidence_on", "'[]'::jsonb"),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("critical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _jsonb("condition"),
        _jsonb("framework_refs", "'[]'::jsonb"),
        sa.Column("library_code", sa.Text(), nullable=True),
        *_ts(),
        _fk("vendor_questionnaire_questions", "tenant_id", "tenants.id"),
        _fk("vendor_questionnaire_questions", "questionnaire_id", "vendor_questionnaires.id"),
        _check("vendor_questionnaire_questions", "answer_type", QUESTION_TYPES),
        _check("vendor_questionnaire_questions", "evidence", EVIDENCE_RULES),
        _check("vendor_questionnaire_questions", "domain", RISK_DOMAINS),
    )
    op.create_index(
        "ix_vendor_questionnaire_questions__tenant_id_questionnaire_id",
        "vendor_questionnaire_questions",
        ["tenant_id", "questionnaire_id", "position"],
    )

    for table in _TENANT_TABLES:
        enable_rls(table)
        grant_crud(table)


def _tiering_upgrade() -> None:
    for factor in FACTORS:
        op.alter_column("vendor_tiering_assessments", factor, nullable=True, server_default=None)
    op.add_column("vendor_tiering_assessments", sa.Column("questionnaire_id", _UUID, nullable=True))
    op.create_foreign_key(
        "fk_vendor_tiering_assessments__questionnaire_id",
        "vendor_tiering_assessments",
        "vendor_questionnaires",
        ["questionnaire_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("vendor_tiering_assessments", _jsonb("answers"))
    op.add_column("vendor_tiering_assessments", _jsonb("questionnaire_snapshot"))


def _review_upgrade() -> None:
    op.add_column("vendor_assessments", sa.Column("questionnaire_id", _UUID, nullable=True))
    op.create_foreign_key(
        "fk_vendor_assessments__questionnaire_id",
        "vendor_assessments",
        "vendor_questionnaires",
        ["questionnaire_id"],
        ["id"],
        ondelete="SET NULL",
    )

    table = "vendor_assessment_responses"
    op.alter_column(table, "question_id", nullable=True)
    op.add_column(table, sa.Column("question_key", sa.Text(), nullable=True))
    op.add_column(table, _jsonb("question_snapshot"))
    op.drop_constraint(conv(f"ck_{table}__answer_valid"), table)
    # The four-value vocabulary binds bank rows. A snapshot row's answer is one of
    # its own question's option keys, which only the service can check.
    op.create_check_constraint(
        conv(f"ck_{table}__answer_valid"),
        table,
        "(question_id IS NULL) OR (answer IS NULL) OR (answer IN ('yes', 'partial', 'no', 'na'))",
    )
    op.create_check_constraint(
        conv(f"ck_{table}__one_question_source"),
        table,
        "(question_id IS NULL) <> (question_key IS NULL)",
    )
    op.create_index(
        f"uq_{table}__assessment_question_key",
        table,
        ["tenant_id", "assessment_id", "question_key"],
        unique=True,
        postgresql_where=sa.text("question_key IS NOT NULL"),
    )

    op.add_column("vendor_findings", sa.Column("question_key", sa.Text(), nullable=True))


def upgrade() -> None:
    _library_upgrade()
    _create_questionnaires()
    _tiering_upgrade()
    _review_upgrade()


def _without_force(table: str, statement: str) -> None:
    """Run one data statement on a FORCE RLS table as the owner.

    Under FORCE the owner is filtered like anyone else, and with no tenant bound
    that means it sees no rows: the statement would match nothing, and the NOT
    NULL that follows would then fail on rows it never saw.
    """
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_column("vendor_findings", "question_key")

    table = "vendor_assessment_responses"
    # Answers to questions copied from a tenant questionnaire cannot exist in the
    # older schema, which has nowhere to say what question they answered.
    # Identifiers here are module constants, never input.
    _without_force(table, f"DELETE FROM {table} WHERE question_id IS NULL")  # noqa: S608
    op.drop_index(f"uq_{table}__assessment_question_key", table_name=table)
    op.drop_constraint(conv(f"ck_{table}__one_question_source"), table)
    op.drop_constraint(conv(f"ck_{table}__answer_valid"), table)
    op.create_check_constraint(
        conv(f"ck_{table}__answer_valid"), table, _in("answer", ("yes", "partial", "no", "na"))
    )
    op.drop_column(table, "question_snapshot")
    op.drop_column(table, "question_key")
    op.alter_column(table, "question_id", nullable=False)

    op.drop_constraint("fk_vendor_assessments__questionnaire_id", "vendor_assessments")
    op.drop_column("vendor_assessments", "questionnaire_id")

    tiering = "vendor_tiering_assessments"
    # A questionnaire run has no factor answers. Zero keeps its stored score and
    # tier standing, which is what the engagement's stages were laid out from.
    _without_force(
        tiering,
        f"UPDATE {tiering} SET "  # noqa: S608 -- constants only
        + ", ".join(f"{factor} = COALESCE({factor}, 0)" for factor in FACTORS),
    )
    op.drop_column(tiering, "questionnaire_snapshot")
    op.drop_column(tiering, "answers")
    op.drop_constraint("fk_vendor_tiering_assessments__questionnaire_id", tiering)
    op.drop_column(tiering, "questionnaire_id")
    for factor in FACTORS:
        op.alter_column(tiering, factor, nullable=False, server_default=sa.text("0"))

    op.drop_table("vendor_questionnaire_questions")
    op.drop_table("vendor_questionnaires")

    # Library content the older schema cannot hold: tiering templates, and any
    # question of a type it does not know. A bank question somebody answered is
    # protected by its RESTRICT foreign key, and the downgrade stops there.
    op.execute("DELETE FROM questionnaire_templates WHERE purpose = 'tiering'")
    op.execute(
        f"DELETE FROM questionnaire_questions WHERE NOT ({_in('answer_type', OLD_BANK_TYPES)})"  # noqa: S608
    )
    op.execute("DELETE FROM questionnaire_questions WHERE domain IS NULL")
    op.drop_constraint(
        conv("ck_questionnaire_questions__answer_type_valid"), "questionnaire_questions"
    )
    op.create_check_constraint(
        conv("ck_questionnaire_questions__answer_type_valid"),
        "questionnaire_questions",
        _in("answer_type", OLD_BANK_TYPES),
    )
    op.drop_column("questionnaire_questions", "required")
    op.drop_column("questionnaire_questions", "options")
    op.drop_column("questionnaire_questions", "help_text")
    op.drop_column("questionnaire_questions", "section")
    op.alter_column("questionnaire_questions", "domain", nullable=False)
    op.drop_constraint(conv("ck_questionnaire_templates__purpose_valid"), "questionnaire_templates")
    op.drop_column("questionnaire_templates", "purpose")
