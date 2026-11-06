"""Let a workspace turn on Verity's built-in checks as a connection.

The automated check machinery (connections, runs, results, evidence per check) was built for
GitHub, which reads an outside account with a stored credential. The built-in provider
``verity`` reads data the workspace already keeps in Verity (documents, risks, vendors, the
Statement of Applicability, evidence) and needs no credential at all. Two constraints on
``connections`` assumed every provider has one:

* ``ck_connections__provider_valid`` listed only ``github``.
* ``ck_connections__credential_only_while_active`` required an active connection to hold a
  credential. For ``verity`` the rule becomes "never holds one"; every other provider keeps the
  old rule exactly.

No table, column or row changes, so the upgrade is safe under load and existing GitHub
connections are untouched.

``downgrade`` restores both constraints. It refuses while any ``verity`` connection exists:
those rows (and their append-only check results, which reference them) cannot satisfy the old
constraints and must not be deleted, so the refusal names what to do instead of losing history.

Revision ID: f6c2b8e4a915
Revises: e3a91c5d7b20
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.naming import conv

revision: str = "f6c2b8e4a915"
down_revision: str | None = "e3a91c5d7b20"
branch_labels: str | None = None
depends_on: str | None = None

_PROVIDER = conv("ck_connections__provider_valid")
_CREDENTIAL = conv("ck_connections__credential_only_while_active")

_OLD_CREDENTIAL = "(status = 'active') = (credential_ciphertext IS NOT NULL)"
_NEW_CREDENTIAL = (
    "CASE WHEN provider = 'verity' THEN credential_ciphertext IS NULL "
    "ELSE (status = 'active') = (credential_ciphertext IS NOT NULL) END"
)


def upgrade() -> None:
    op.drop_constraint(_PROVIDER, "connections", type_="check")
    op.create_check_constraint(_PROVIDER, "connections", "provider IN ('github', 'verity')")
    op.drop_constraint(_CREDENTIAL, "connections", type_="check")
    op.create_check_constraint(_CREDENTIAL, "connections", _NEW_CREDENTIAL)


def downgrade() -> None:
    bind = op.get_bind()
    # connections has FORCE ROW LEVEL SECURITY, which applies to the owner this runs as and
    # filters SELECT: without lifting it the count below would always read zero.
    op.execute("ALTER TABLE connections NO FORCE ROW LEVEL SECURITY")
    try:
        built_in = bind.execute(
            sa.text("SELECT count(*) FROM connections WHERE provider = 'verity'")
        ).scalar_one()
    finally:
        op.execute("ALTER TABLE connections FORCE ROW LEVEL SECURITY")
    if built_in:
        raise RuntimeError(
            f"{built_in} workspace connection(s) use the built-in Verity checks. Their check "
            "results are append-only history and cannot be removed, so this downgrade cannot "
            "restore the GitHub-only constraints. Stay on this revision, or restore a backup "
            "taken before it."
        )
    op.drop_constraint(_CREDENTIAL, "connections", type_="check")
    op.create_check_constraint(_CREDENTIAL, "connections", _OLD_CREDENTIAL)
    op.drop_constraint(_PROVIDER, "connections", type_="check")
    op.create_check_constraint(_PROVIDER, "connections", "provider IN ('github')")
