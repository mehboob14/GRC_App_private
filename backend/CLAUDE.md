# Backend — conventions for AI-assisted work

Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, Celery.
Read [../docs/conventions/database.md](../docs/conventions/database.md) before touching models, and
[../docs/conventions/code-quality.md](../docs/conventions/code-quality.md) for the cross-cutting quality
bar (SOLID, reuse, design) that applies to everything below.

## Module layout — vertical slices

Every module under `src/verity/modules/<name>/` owns its full stack:

```
<module>/
  __init__.py
  router.py        FastAPI routes. HTTP only: parse, authorise, call service, shape response.
  schemas.py       Pydantic request/response models. Never expose ORM objects directly.
  models.py        SQLAlchemy models for this module's tables only.
  service.py       Business logic. The only place rules live.
  repository.py    Data access. All queries filter tenant_id explicitly.
  exceptions.py    Module-specific errors, mapped to HTTP in the handler.
  tasks.py         Celery tasks owned by this module (optional).
```

**Do not** create global `models.py`, `services.py`, or `crud.py`. Layer-first structure is what
turns a codebase into mud at ~30 modules.

## Module boundaries

- A module may import another module's **service interface**. Never its `repository.py`, never its
  `models.py`, never its tables directly.
- Cross-module reads that get expensive become an explicit method on the owning service, not a
  join across boundaries.
- Shared pure helpers live in `shared/`. If you are about to put business logic in `shared/`, it
  belongs in a module.
- Circular imports between modules mean the boundary is wrong. Fix the boundary, don't add a
  local import inside a function.

## Layer rules

- **Routers** contain no business logic and no queries. If a router has an `if` about domain
  state, it belongs in the service.
- **Services** contain no SQL and no `Request`/`Response` objects. They take and return domain
  types, so they are testable without HTTP.
- **Repositories** contain no business rules. They return models or rows.
- A service method is one unit of work. Repositories never commit, and neither do services:
  `core.db.session_scope` opens the transaction, binds the tenant, and commits on a clean exit.
  This is not style. The tenant setting is transaction-local, so a service that commits half way
  through its work leaves every later statement with no tenant bound — under RLS those statements
  return zero rows and raise nothing, so data that exists appears to be missing, intermittently,
  depending on where the commit landed. A service needing a partial rollback uses
  `session.begin_nested()`; a savepoint does not disturb the setting.

## Async

Everything I/O is `async`. Never call a blocking library on the event loop — no `requests`, no
sync `psycopg`, no blocking file reads in a request path. CPU-bound or blocking work goes to a
Celery task.

## Errors

- Raise domain exceptions from services (`EvidenceNotFound`, `ApprovalRequired`).
- One exception handler maps them to HTTP.
- **Error responses never leak internals** — no stack traces, no SQL, no upstream provider
  messages. Log the detail with a correlation id; return the id to the client.

## Security — non-negotiable in this codebase

- Every route declares its required permission explicitly. No route is authenticated-only by
  default; there is no implicit allow.
- Permissions are flat `module:action` keys (`controls:edit`, `evidence:approve`). Roles are
  named bundles, assignable to a user or a group.
- **Object-scoped roles are application logic**, not permission keys. Control owner sees assigned
  controls; auditor sees one engagement inside its window. The flat permission check runs first,
  then the ownership/assignment filter. Never assume the flat model gives row-level scoping — it
  does not.
- Auditor access is time-boxed through `engagement_id`, `valid_from`, `valid_until` on the role
  assignment. Expired means invisible, checked at query time and not by a nightly job.
- Connector credentials and MFA secrets are encrypted at the application layer before they reach
  the database, and are excluded from every log and every `__repr__`.
- Every state-changing service method writes an `audit_log` entry with before/after snapshots.
  If it changes state and does not write the trail, it is incomplete.

## Testing

- **Unit** — services with repositories faked. Fast, no database.
- **Integration** — real Postgres with RLS on, connecting as the app role.
- **Isolation** — `tests/isolation/` proves cross-tenant access fails. Merge blocker.
- Never disable RLS in a fixture. Never use a `BYPASSRLS` role in tests.
- Every bug fix starts with a failing test that reproduces it.

## Scheduled jobs

Defined in `workers/`, each idempotent and safe to re-run: evidence staleness refresh, readiness
snapshot writer, acceptance and waiver expiry, vulnerability SLA sweep, vendor reassessment queue,
scheduled checks and connector syncs, acknowledgement reminders, vendor monitoring, asset hygiene,
vulnerability enrichment.

Each sets tenant context per unit of work. A job that partially fails must be resumable without
double-writing.

## Connectors

Every connector implements the shared framework interface. Least-privilege read-only credentials,
consistent auth, paging, rate limiting, and error handling.

A collection failure is recorded as **`error`, never `fail`**. A broken integration must never
look like a failed control — this is the difference between a trustworthy compliance product and
one that cries wolf.
