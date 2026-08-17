"""re-code SOC 2 controls to category-based codes (IAM-01, GRC-01, …)

Revision ID: d1f4c8a9b370
Revises: c9e3a7b52f41
Create Date: 2026-08-17 10:00:00.000000

The shipped templates were re-coded from descriptive slugs ("access-approval")
to short category codes ("IAM-01") in the seed pack; the loader upserts those on
``code``, so the global plane follows on the next seed run. Tenants that already
adopted the library hold their own copy of the old code on ``controls.code``,
and that copy is what every screen shows — so it is renamed here.

The new code is read from ``control_templates`` via ``controls.template_id``
rather than a literal 114-row map: the seed pack is the single source of the
mapping, and deriving it keeps this migration correct if the pack is reloaded
before it runs. Custom (internal) controls have a NULL ``template_id`` and are
untouched — their codes are the tenant's own.

``controls`` carries ``FORCE ROW LEVEL SECURITY``, which applies to the table
owner too — and a migration runs as the owner with no tenant bound, so the
UPDATE would match zero rows and silently do nothing. This is a deliberate
cross-tenant backfill, so ``FORCE`` is lifted for the statement and restored
immediately, inside the same transaction: if this migration fails, the rollback
puts ``FORCE`` back with it.

Ordering note: the ``UPDATE`` runs inside one transaction, so the unique
``(tenant_id, code)`` index is only checked at statement end; old and new code
spaces do not overlap ("IAM-01" vs "access-approval"), so no collision is
possible in either direction.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d1f4c8a9b370"
down_revision: str | None = "c9e3a7b52f41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _recode(target: str) -> None:
    """Re-point every adopted control's code at the template's ``target`` column.

    ``FORCE`` is lifted only for the UPDATE and restored in the same
    transaction — see the module docstring.
    """
    op.execute("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        UPDATE controls AS c
           SET code = t.{target}
          FROM control_templates AS t
         WHERE c.template_id = t.id
           AND c.code <> t.{target}
        """  # noqa: S608 — `target` is a literal from this module, never input
    )
    op.execute("ALTER TABLE controls FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    # Adopted controls carry the template's code; re-point them at the new one.
    _recode("code")


def downgrade() -> None:
    # The old code survives on the template's canonical_key, which the re-code
    # deliberately left untouched — so the rename is reversible without a map.
    _recode("canonical_key")
