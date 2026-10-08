"""Risk register settings: scoring formula, appetite, custom fields.

``risk_registers.scoring_formula`` is ``{method: product|additive|weighted, ...}``
and ``appetite`` maps a top-level category id to ``{appetite, tolerance}`` scores.
The score columns stop being ``likelihood * impact`` generated columns (Postgres
cannot read another table there) and become ordinary columns a trigger fills from
the register's formula, so every SQL filter and sort keeps working. Existing rows
keep their values because the default formula is the product.

Revision ID: 7c3e91d2a8f4
Revises: 61e2554a5209
Create Date: 2026-10-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

revision: str = "7c3e91d2a8f4"
down_revision: str | None = "61e2554a5209"
branch_labels: str | None = None
depends_on: str | None = None

_CK = "ck_custom_field_definitions__object_type_valid"


def _object_check(values: tuple[str, ...]) -> None:
    op.drop_constraint(conv(_CK), "custom_field_definitions", type_="check")
    op.create_check_constraint(
        conv(_CK),
        "custom_field_definitions",
        "object_type IN (" + ", ".join(repr(v) for v in values) + ")",
    )


def upgrade() -> None:
    op.add_column(
        "risk_registers",
        sa.Column(
            "scoring_formula",
            postgresql.JSONB(),
            server_default=sa.text("""'{"method": "product"}'::jsonb"""),
            nullable=False,
        ),
    )
    op.add_column(
        "risk_registers",
        sa.Column(
            "appetite", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
    )
    op.add_column(
        "risks",
        sa.Column(
            "custom_fields",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    _object_check(("asset", "vulnerability", "risk"))

    op.execute("ALTER TABLE risks ALTER COLUMN inherent_score DROP EXPRESSION")
    op.execute("ALTER TABLE risks ALTER COLUMN residual_score DROP EXPRESSION")
    op.execute(
        """
        CREATE FUNCTION risk_score(f jsonb, l int, i int) RETURNS int
        LANGUAGE sql IMMUTABLE AS $$
          SELECT CASE
            WHEN l IS NULL OR i IS NULL THEN NULL
            WHEN f->>'method' = 'additive' THEN l + i
            WHEN f->>'method' = 'weighted'
              THEN l * COALESCE((f->>'likelihood_weight')::int, 1)
                 + i * COALESCE((f->>'impact_weight')::int, 1)
            ELSE l * i
          END
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION risks_set_scores() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE f jsonb;
        BEGIN
          SELECT scoring_formula INTO f FROM risk_registers WHERE id = NEW.register_id;
          f := COALESCE(f, '{}'::jsonb);
          NEW.inherent_score := risk_score(f, NEW.inherent_likelihood, NEW.inherent_impact);
          NEW.residual_score := risk_score(f, NEW.residual_likelihood, NEW.residual_impact);
          RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_risks_scores BEFORE INSERT OR UPDATE ON risks "
        "FOR EACH ROW EXECUTE FUNCTION risks_set_scores()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_risks_scores ON risks")
    op.execute("DROP FUNCTION risks_set_scores()")
    op.execute("DROP FUNCTION risk_score(jsonb, int, int)")
    op.drop_index("ix_risks__tenant_id_residual_score", table_name="risks")
    op.drop_column("risks", "inherent_score")
    op.drop_column("risks", "residual_score")
    op.add_column(
        "risks",
        sa.Column(
            "inherent_score",
            sa.Integer(),
            sa.Computed("inherent_likelihood * inherent_impact", persisted=True),
            nullable=True,
        ),
    )
    op.add_column(
        "risks",
        sa.Column(
            "residual_score",
            sa.Integer(),
            sa.Computed("residual_likelihood * residual_impact", persisted=True),
            nullable=True,
        ),
    )
    op.create_index("ix_risks__tenant_id_residual_score", "risks", ["tenant_id", "residual_score"])
    op.execute("DELETE FROM custom_field_definitions WHERE object_type = 'risk'")
    _object_check(("asset", "vulnerability"))
    op.drop_column("risks", "custom_fields")
    op.drop_column("risk_registers", "appetite")
    op.drop_column("risk_registers", "scoring_formula")
