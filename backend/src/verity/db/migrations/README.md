# Migrations

Empty on purpose. The backend foundation change ships no domain tables, so
`alembic upgrade head` creates the `alembic_version` table and nothing else — which is
what proves the wiring without asserting a schema that has not been specified yet.

## Commands

Run from `backend/`:

```bash
uv run alembic upgrade head              # apply
uv run alembic downgrade -1              # reverse the last one
uv run alembic revision -m "add controls" --autogenerate
uv run alembic upgrade head --sql        # emit SQL for review instead of running it
```

Migrations connect as `DATABASE_MIGRATION_URL` — the role that owns the schema. The
application connects as `DATABASE_URL`, a role that owns nothing and holds no
`BYPASSRLS`. If those are the same role, RLS is not being tested by anything.

## The rule that has no exception

A migration that creates a tenant-owned table enables row-level security and adds its
policy **in that same migration**, using `verity.db.rls.enable_rls`. Never as a
follow-up. A table without a policy passes every test except the one nobody wrote.

`script.py.mako` puts the full checklist at the top of every generated revision.
