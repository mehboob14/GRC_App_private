"""Migration-time DDL for row-level security and append-only enforcement.

Called from Alembic migrations, never from the request path — the runtime half of the
mechanism is ``verity.core.rls``.

docs/conventions/database.md: a migration that adds a tenant-owned table **must**
enable RLS and add the policy in the same migration. A table without a policy is a
silent isolation hole that passes every other test. So enabling it is one call, and a
review can see whether that call is there.
"""

from __future__ import annotations

import re
from typing import Final

from alembic import op
from sqlalchemy import text as sql_text

from verity.core.config import get_settings
from verity.core.rls import TENANT_ID_SETTING

DEFAULT_POLICY_NAME: Final = "tenant_isolation"
_IDENTIFIER: Final = re.compile(r"^[a-z_][a-z0-9_]*$")


def _identifier(value: str, *, what: str) -> str:
    """Validate an identifier that is about to be interpolated into DDL.

    Postgres will not accept a bind parameter for a table, column, policy, or role
    name, so these are formatted into the statement. Every one is therefore checked
    against this pattern first.
    """
    if not _IDENTIFIER.match(value):
        raise ValueError(f"{what} {value!r} is not a valid snake_case identifier")
    return value


def tenant_policy_predicate(tenant_column: str = "tenant_id") -> str:
    """The predicate every tenant policy uses.

    Two details differ from the shorter form and both matter::

        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid

    ``current_setting(name, true)`` returns NULL rather than raising when the setting
    was never set on this session. Without the second argument, the first query on a
    tenant table from a connection that has not bound a tenant raises
    ``unrecognized configuration parameter`` and surfaces as a 500.

    ``NULLIF(..., '')`` handles bound-but-empty, which is how ``core.rls`` represents
    "no tenant" — ``set_config`` has no NULL. Casting ``''`` to uuid raises; NULLIF
    turns it into NULL first, and ``tenant_id = NULL`` is NULL, which is not true, so
    no row matches. Unbound means no rows: the policy fails closed.
    """
    _identifier(tenant_column, what="tenant column")
    return f"{tenant_column} = NULLIF(current_setting('{TENANT_ID_SETTING}', true), '')::uuid"


def enable_rls(
    table_name: str,
    *,
    tenant_column: str = "tenant_id",
    policy_name: str = DEFAULT_POLICY_NAME,
) -> None:
    """Enable, force, and police row-level security on a tenant-owned table.

    ``FORCE`` matters as well as ``ENABLE``: ``ENABLE`` alone does not apply to the
    table's owner, and migrations run as the owner. The application does not connect as
    the owner, so ``FORCE`` is a second line rather than the only one — which is the
    whole design.

    ``WITH CHECK`` carries the same predicate as ``USING``, so a write cannot place a
    row in a tenant other than the bound one. Without it, reads are isolated and writes
    are not.
    """
    _identifier(table_name, what="table name")
    _identifier(policy_name, what="policy name")
    predicate = tenant_policy_predicate(tenant_column)

    op.execute(sql_text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sql_text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sql_text(
            f"CREATE POLICY {policy_name} ON {table_name} "
            f"FOR ALL USING ({predicate}) WITH CHECK ({predicate})"
        )
    )


def disable_rls(table_name: str, *, policy_name: str = DEFAULT_POLICY_NAME) -> None:
    """Reverse :func:`enable_rls`. For a migration's ``downgrade`` only."""
    _identifier(table_name, what="table name")
    _identifier(policy_name, what="policy name")
    op.execute(sql_text(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"))
    op.execute(sql_text(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"))
    op.execute(sql_text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))


def grant_crud(table_name: str, *, role: str | None = None) -> None:
    """Grant the application role the DML it needs on a table.

    Explicit rather than relying on the cluster's default privileges, so a table's
    grants are visible in the migration that created it.
    """
    role = role or get_settings().database.app_role
    _identifier(table_name, what="table name")
    _identifier(role, what="role name")
    op.execute(sql_text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table_name} TO {role}"))


def make_append_only(table_name: str, *, role: str | None = None) -> None:
    """Revoke ``UPDATE``, ``DELETE``, and ``TRUNCATE`` from the application role.

    Rule 3: ``audit_log``, ``task_transitions``, ``vuln_transitions``,
    ``check_results``, ``readiness_snapshots``, ``kri_measurements``, and
    ``document_versions`` are insert-only, and docs/conventions/database.md requires
    that to be enforced by a revoked grant rather than by convention alone.

    Immutability is a property this product sells to auditors. A convention is not
    evidence; a refused ``UPDATE`` is.
    """
    role = role or get_settings().database.app_role
    _identifier(table_name, what="table name")
    _identifier(role, what="role name")
    op.execute(sql_text(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table_name} FROM {role}"))
