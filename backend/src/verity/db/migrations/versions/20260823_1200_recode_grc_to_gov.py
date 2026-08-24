"""Re-code the Governance category from GRC-NN to GOV-NN.

The Governance, Risk & Compliance category shipped as ``GRC-01…GRC-22``. "GRC"
reads as the whole product, not one category, so it is re-coded to ``GOV-`` (the
seed pack was updated to match). Custom controls now use the ``IC-`` (Internal
Control) namespace; this migration only touches shipped/adopted controls.

Both planes move together: ``control_templates`` (global, no RLS) and every
tenant's adopted copy on ``controls``. Only adopted rows (``template_id IS NOT
NULL``) are re-coded — a tenant's own custom controls keep their codes.

``controls`` carries ``FORCE ROW LEVEL SECURITY``, which applies to the owner a
migration runs as, so a cross-tenant UPDATE would match zero rows. FORCE is
lifted for the statement and restored in the same transaction (same pattern as
the earlier category re-code). Old and new code spaces do not overlap
(``GRC-04`` vs ``GOV-04`` differ), so the unique ``(tenant_id, code)`` index —
checked at statement end — cannot collide.
"""

from __future__ import annotations

from alembic import op

revision = "e1a7c93d820b"
down_revision = "d8f2b4c091a7"
branch_labels = None
depends_on = None


def _swap(old: str, new: str) -> None:
    # Global content plane: no RLS. `old`/`new` are literals from this module,
    # never input, so the interpolation is safe.
    op.execute(
        f"UPDATE control_templates SET code = '{new}-' || substring(code from 5) "  # noqa: S608
        f"WHERE code LIKE '{old}-%'"
    )
    # Tenant plane: lift FORCE for this cross-tenant backfill, restore in-txn.
    op.execute("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"UPDATE controls SET code = '{new}-' || substring(code from 5) "  # noqa: S608
        f"WHERE code LIKE '{old}-%' AND template_id IS NOT NULL"
    )
    op.execute("ALTER TABLE controls FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _swap("GRC", "GOV")


def downgrade() -> None:
    _swap("GOV", "GRC")
