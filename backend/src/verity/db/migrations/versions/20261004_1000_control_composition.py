"""What evidences a control: evidence kinds on checks, expected evidence on templates.

A control is evidenced by checks that connected systems and Verity modules run,
and by things people provide. The library carried the first half only as a bare
link from a check to a control. This adds what the control page needs to say, for
each control, which systems and which people evidence it:

* ``checks.evidence_kinds``: the artifacts a check collects (a branch protection
  setting, a pull request, a CI run), as a list of names.
* ``control_template_checks.rationale``: why this check is evidence for this
  control, and what it does not prove.
* ``control_templates.evidence``: what a person or a Verity module provides for
  the control beyond what its checks collect (the policy, the sample, the
  review), each marked design or operating and with how often it is renewed.
* ``control_templates.pack``: which content pack ships the template, so loading a
  second framework prunes only what its own pack owns (F17).

The crosswalk rationale and coverage need no column: ``template_requirement_map``
has carried both since it was created, and the loader now fills them.

A mapping added for BC-08 (vendor assessment also supports P6.4) is carried to
workspaces that adopted it, under the library update rule (CF-6): a control is
corrected only while its mapping is still exactly what was shipped. The same
FORCE row level security handling as the earlier content migrations applies.

Revision ID: a7d3f19e2c58
Revises: f1c8d62b0e47
Create Date: 2026-10-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7d3f19e2c58"
down_revision: str | None = "f1c8d62b0e47"
branch_labels: str | None = None
depends_on: str | None = None

# code -> (criteria as shipped before, criteria as shipped now)
CHANGES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "BC-08": (("CC9.2",), ("CC9.2", "P6.4")),
}

_TEXT_ARRAY = postgresql.ARRAY(sa.Text())

_UNEDITED = sa.text(
    "SELECT c.id, c.tenant_id FROM controls c "
    "JOIN control_templates t ON t.id = c.template_id "
    "WHERE t.code = :code AND c.origin = 'template' "
    "AND COALESCE(("
    "  SELECT array_agg(r.requirement_key ORDER BY r.requirement_key) "
    "  FROM control_requirements cr JOIN requirements r ON r.id = cr.requirement_id "
    "  WHERE cr.control_id = c.id), ARRAY[]::text[]) = :keys"
).bindparams(sa.bindparam("keys", type_=_TEXT_ARRAY))

_REMOVE = sa.text(
    "DELETE FROM control_requirements cr USING requirements r "
    "WHERE cr.requirement_id = r.id AND cr.control_id = :control_id "
    "AND r.requirement_key <> ALL(:target)"
).bindparams(sa.bindparam("target", type_=_TEXT_ARRAY))

_ADD = sa.text(
    "INSERT INTO control_requirements (id, tenant_id, control_id, requirement_id) "
    "SELECT gen_random_uuid(), :tenant_id, :control_id, r.id FROM requirements r "
    "WHERE r.requirement_key = ANY(:target) "
    "AND NOT EXISTS (SELECT 1 FROM control_requirements x "
    "  WHERE x.control_id = :control_id AND x.requirement_id = r.id)"
).bindparams(sa.bindparam("target", type_=_TEXT_ARRAY))


def _keys(criteria: tuple[str, ...]) -> list[str]:
    return sorted(f"SOC2:{criterion}" for criterion in criteria)


def _apply(from_index: int, to_index: int) -> None:
    bind = op.get_bind()
    for table in ("controls", "control_requirements"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    try:
        for code, sets in CHANGES.items():
            source, target = _keys(sets[from_index]), _keys(sets[to_index])
            for control_id, tenant_id in bind.execute(
                _UNEDITED, {"code": code, "keys": source}
            ).all():
                bind.execute(_REMOVE, {"control_id": control_id, "target": target})
                bind.execute(
                    _ADD, {"control_id": control_id, "tenant_id": tenant_id, "target": target}
                )
    finally:
        for table in ("control_requirements", "controls"):
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.add_column(
        "checks",
        sa.Column(
            "evidence_kinds",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("control_template_checks", sa.Column("rationale", sa.Text(), nullable=True))
    op.add_column(
        "control_templates",
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "control_templates",
        sa.Column("pack", sa.Text(), nullable=False, server_default=sa.text("'soc2'")),
    )
    _apply(0, 1)


def downgrade() -> None:
    _apply(1, 0)
    op.drop_column("control_templates", "pack")
    op.drop_column("control_templates", "evidence")
    op.drop_column("control_template_checks", "rationale")
    op.drop_column("checks", "evidence_kinds")
