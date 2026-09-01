"""Every tenant-owned table must actually carry the RLS wall — not just the
helper that would write it (that is ``test_rls_policy``), but the wall itself,
present on every real table the data model defines.

This is the systemic guard behind rule 1 / rule 12: a new module that adds a
``TenantScoped`` table but forgets ``enable_rls`` in its migration is a silent
cross-tenant leak that no per-module test would catch. Here the *model metadata*
is the checklist — the mixin is the marker of "tenant-owned" — and the live
schema is checked against it. Add a tenant table, and this test demands its
policy in the same breath.

The three properties checked are the three that make isolation real:
- ROW LEVEL SECURITY enabled,
- FORCE set (or the owner, who created the table, bypasses it),
- at least one policy present.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from verity.db.base import Base, TenantScoped

pytestmark = [pytest.mark.isolation, pytest.mark.integration]


def _tenant_owned_tables() -> set[str]:
    """Table names of every mapped class that mixes in ``TenantScoped``.

    Auto-discovers every ``verity.modules.*.models`` so the mapper is fully
    populated regardless of what the test session happened to import (a module
    with no router — ``links`` — is otherwise never pulled in). Add a module,
    and its tenant tables enter this checklist with no edit here.
    """
    import contextlib  # noqa: PLC0415
    import importlib  # noqa: PLC0415
    import pkgutil  # noqa: PLC0415

    import verity.modules  # noqa: PLC0415

    for module in pkgutil.iter_modules(verity.modules.__path__):
        # Not every module defines a models.py (e.g. connectors).
        with contextlib.suppress(ModuleNotFoundError):
            importlib.import_module(f"verity.modules.{module.name}.models")

    return {
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, TenantScoped)
    }


async def test_every_tenant_owned_table_has_forced_rls_and_a_policy(
    app_engine: AsyncEngine,
) -> None:
    tables = _tenant_owned_tables()
    assert tables, "no tenant-owned tables found — the enumeration is broken, not the schema"

    async with app_engine.connect() as connection:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT c.relname,
                           c.relrowsecurity,
                           c.relforcerowsecurity,
                           (SELECT count(*) FROM pg_policies p
                              WHERE p.schemaname = 'public' AND p.tablename = c.relname) AS policies
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relname = ANY(:names)
                    """
                ),
                {"names": list(tables)},
            )
        ).all()
    by_name = {row[0]: row for row in rows}

    problems: list[str] = []
    for table in sorted(tables):
        row = by_name.get(table)
        if row is None:
            problems.append(f"{table}: no such table in the database")
        elif not row[1]:
            problems.append(f"{table}: ROW LEVEL SECURITY is not enabled")
        elif not row[2]:
            problems.append(
                f"{table}: FORCE ROW LEVEL SECURITY is not set (the owner bypasses RLS)"
            )
        elif row[3] == 0:
            problems.append(f"{table}: no RLS policy is defined")

    assert not problems, "tenant-owned tables missing their RLS wall:\n  " + "\n  ".join(problems)
