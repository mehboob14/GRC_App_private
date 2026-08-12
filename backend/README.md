# Verity backend

FastAPI modular monolith. Python 3.12, SQLAlchemy 2.0 async, PostgreSQL 16 with row-level
security, Celery on Redis.

Conventions are binding and live in [CLAUDE.md](CLAUDE.md) and [../docs/](../docs/). Setup lives
in [../docs/runbooks/local-setup.md](../docs/runbooks/local-setup.md).

## Layout

```
src/verity/
  shared/       pure helpers with no dependencies of their own — uuid7 lives here
  core/         config, logging, errors, middleware, crypto, engine and session, deps, health
  db/           declarative base and mixins, migration-time RLS DDL, alembic
  modules/      one package per bounded context
  workers/      the Celery app and its tasks
  main.py       the application factory
tests/
  unit/         no database, no network
  integration/  a real Postgres and Redis, as the application role
  isolation/    tenant separation; a failure here is a merge blocker
```

The import graph is enforced, not suggested: `modules → db → core → shared`, and within a module
`router → service → repository → models`. No module may import another module's repository or
models. `make imports` fails the build otherwise; the contracts are in `pyproject.toml`.

`core/rls.py` holds the runtime tenant primitive and `db/rls.py` the migration-time DDL that
writes the policies. They are separate because `core` owns the session that binds the context and
`db` owns the schema that reads it.

## Commands

Run from the repository root; each is a `make` target, listed here as the command it wraps.

```bash
uv sync --frozen --extra dev                   # make setup
uv run alembic upgrade head                    # make migrate
uv run uvicorn verity.main:app --reload        # make run
uv run celery -A verity.workers.celery_app:celery_app worker   # make worker
uv run ruff format . && uv run ruff check .    # part of make check
uv run mypy                                    # strict
uv run lint-imports                            # module boundaries
VERITY_REQUIRE_DB=1 uv run pytest              # make test
```

`VERITY_REQUIRE_DB=1` turns an unreachable database from a skipped suite into a failure. CI sets
it. Without it the database suites skip with a message.

## What is here

Configuration read once and validated; structured logging with key-name redaction; one exception
handler producing a stable envelope with a correlation id; the tenant-context primitive and the
policy DDL that reads it; UUIDv7 keys and the table mixins; envelope encryption for secrets;
liveness and readiness probes; Alembic on the async engine with the migration role; a Celery app
with one no-op task; and a LangSmith-traced chat model client.

## What is deliberately not here

No domain models, no tables, no migrations, no feature endpoints. `core/deps.py` fixes the shapes
of `Principal`, `TenantContext`, and `require(permission)`, but the bodies raise
`NotImplementedError`: authentication, permissions, and the tenancy tables are Week 1. The module
packages under `modules/` are empty on purpose — they exist so the boundary contracts are real
from the first module rather than added after the first violation.
