"""Correct fourteen SOC 2 control mappings that did not match the criteria.

The control library arrived from the prototype with its criterion mappings
unvalidated. Reading them against the AICPA points of focus found one wrong
mapping and thirteen missing ones:

* SD-11 Secret scanning was mapped to CC6.8, which is about unauthorized or
  malicious *software*. A committed credential is a failure to protect
  credentials (CC6.1) and a vulnerability a change introduced (CC7.1).
* LM-01 Asset inventory lacked CC6.1, whose first point of focus is "identifies
  and manages the inventory of information assets".
* HR-01 background checks lacked CC1.4 ("considers the background of
  individuals"); HR-07 lacked CC1.5; NS-05 lacked CC7.2; LM-08 lacked CC7.4;
  EP-02 lacked CC6.1 (encryption); BC-06 lacked P6.4 (vendor privacy
  commitments); CS-03 lacked CC2.3 (inbound communication); PE-01 lacked CC9.2
  (subservice organisation review); IAM-01, IAM-12 and HR-05 lacked CC6.3; IAM-02
  lacked CC6.2 ("reviews the appropriateness of access credentials").

The shipped crosswalk (``template_requirements.json``) is corrected by the
content pack and reaches ``template_requirement_map`` through ``seed-content``.
This migration carries the same correction to controls a workspace has already
adopted, under the library-update rule (CF-6): library updates never overwrite a
tenant's edits. A control is corrected only if its mapping is still exactly what
was shipped; one a workspace has changed is left alone.

``control_requirements`` and ``controls`` carry ``FORCE ROW LEVEL SECURITY``,
which applies to the owner a migration runs as and filters SELECT as well as
DML, so a cross-tenant backfill sees nothing unless FORCE is lifted. It is lifted
for the backfill and restored in the same transaction, as the earlier content
migrations do.

``downgrade`` applies the inverse on the same basis.

Revision ID: f1c8d62b0e47
Revises: e7b2a41c9d35
Create Date: 2026-10-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1c8d62b0e47"
down_revision: str | None = "e7b2a41c9d35"
branch_labels: str | None = None
depends_on: str | None = None

# code -> (criteria as shipped before, criteria as shipped now)
CHANGES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "SD-11": (("CC6.8",), ("CC6.1", "CC7.1")),
    "LM-01": (("CC2.1",), ("CC2.1", "CC6.1")),
    "NS-05": (("CC6.8",), ("CC6.8", "CC7.2")),
    "HR-01": (("CC1.1",), ("CC1.1", "CC1.4")),
    "HR-07": (("CC1.4",), ("CC1.4", "CC1.5")),
    "LM-08": (("CC7.2",), ("CC7.2", "CC7.4")),
    "EP-02": (("CC6.5", "CC6.7"), ("CC6.1", "CC6.5", "CC6.7")),
    "BC-06": (("CC9.2", "P6.1"), ("CC9.2", "P6.1", "P6.4")),
    "CS-03": (("CC2.2",), ("CC2.2", "CC2.3")),
    "PE-01": (("CC6.4",), ("CC6.4", "CC9.2")),
    "IAM-01": (("CC6.2",), ("CC6.2", "CC6.3")),
    "IAM-12": (("CC6.2",), ("CC6.2", "CC6.3")),
    "HR-05": (("CC6.2",), ("CC6.2", "CC6.3")),
    "IAM-02": (("CC6.3",), ("CC6.2", "CC6.3")),
}

_TEXT_ARRAY = postgresql.ARRAY(sa.Text())

# Controls adopted from this template whose mapping is exactly ``keys``: untouched.
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
    _apply(0, 1)


def downgrade() -> None:
    _apply(1, 0)
