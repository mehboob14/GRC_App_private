# Backend foundation

## Why

Nothing exists in `backend/` yet. Fifteen modules are going to be built on top of a small set of
cross-cutting primitives, and three of those primitives are the compliance properties this product
sells: the tenant-context primitive that RLS keys on, the single error handler that must never leak
internals, and the application-layer encryption that secrets pass through before they reach the
database.

Getting those wrong is not a refactor. A tenant-context helper that leaks across a pooled connection
is a data breach. An error envelope that changes shape after five modules have shipped is a frontend
rewrite. A ciphertext format without a key id in it means re-encrypting every secret row to rotate a
key. These are decided once, now, before there is anything to migrate.

This change belongs to **Phase 1, deliverable 1.1 — Foundation**. It is the part of 1.1 that comes
before controls, evidence, dashboards, and tasks.

## What changes

- `backend/pyproject.toml` — uv-managed project, pinned dependencies, `ruff`, `mypy --strict`,
  `pytest`, and the `import-linter` contracts that enforce the module boundaries in
  `backend/CLAUDE.md`.
- `backend/src/verity/shared/ids.py` — UUIDv7 generation (ADR-0002).
- `backend/src/verity/core/` — `config.py` (Settings, loaded once), `db.py` (async engine, session
  factory, session scope), `rls.py` (**the tenant-context primitive**), `errors.py` (domain
  exception base plus the one exception handler), `logging.py` (structlog with key-name redaction),
  `crypto.py` (envelope encryption), `deps.py` (principal, tenant context, `require(permission)`),
  `middleware.py` (correlation id, security headers), `health.py`.
- `backend/src/verity/db/` — `base.py` (declarative `Base`, UUIDv7 PK, timestamp / tenant /
  integration mixins, index and status-check helpers), `rls.py` (migration-time DDL helpers:
  `enable_rls`, `add_tenant_policy`, `make_append_only`), and Alembic wired to the async engine with
  an empty `versions/`.
- `backend/src/verity/main.py` — app factory, `/healthz`, `/readyz`, no mounted domain routers.
- `backend/src/verity/workers/` — Celery app, beat schedule, one no-op task, and the documented
  set-tenant-context-per-unit-of-work pattern.
- `backend/src/verity/modules/` — the fifteen documented module packages, empty except `ai`, which
  gets a LangSmith-traced LangChain client and the rule-8 guardrail note.
- `backend/tests/` — pytest config and `conftest.py` with async fixtures against a real Postgres with
  RLS on, connecting as the non-`BYPASSRLS` application role; `unit/`, `integration/`, `isolation/`.
- `infra/docker/docker-compose.yml` — postgres 16, redis, minio. No Keycloak (Phase 3).
- `infra/docker/postgres/init/` — creates the application role and the read-only role, neither with
  `BYPASSRLS`, and sets default privileges.
- `Makefile`, `.env.example`, `.github/workflows/backend-ci.yml`.

## Non-goals

- **No domain models, tables, or migrations.** `versions/` ships empty. `alembic upgrade head` is a
  no-op that proves the wiring, nothing more.
- **No feature endpoints.** The app mounts `/healthz` and `/readyz` and nothing else.
- **No authentication or authorization logic.** `core/deps.py` fixes the *shapes* — `Principal`,
  `TenantContext`, `require(permission)` — and raises `NotImplementedError`. Week 1 implements them.
  `argon2-cffi`, `pyjwt`, and `pyotp` are declared now because the seam they serve is designed now;
  they are unused until Week 1.
- **No AI features.** Phase 2 owns AI drafting. `modules/ai/llm.py` is a constructible, traced
  client and nothing else.
- **No frontend.** Not touched.
- **No connector framework.** Phase 2.

## Modules touched

`ai` (client only), plus the fifteen module packages created empty. No module boundary is crossed
because no module has anything in it yet — the point of this change is that the contracts which
prevent crossing them are in place before that becomes possible.

## Closest-review flags

This change **touches tenant isolation**. `core/rls.py` and `db/rls.py` are the two halves of the
mechanism ADR-0001 depends on: the runtime GUC binding and the policy DDL. Review those two files
and `tests/isolation/` first.

It **adds dependencies** — twenty-one runtime, seven development. Each is justified in `design.md`.

It does **not** touch the audit trail or any append-only table, because neither exists yet.
`db/rls.py` ships the `make_append_only` helper those tables will use.
