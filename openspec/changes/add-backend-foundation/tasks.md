# Tasks — backend foundation

## 1. Project and tooling

- [x] 1.1 `backend/pyproject.toml`: uv project, `src/` layout, Python 3.12, exact-pinned runtime and
      dev dependencies, each justified in `design.md`.
- [x] 1.2 `ruff` configuration: line length, lint rule selection, formatter settings.
- [x] 1.3 `mypy` strict configuration, including per-package overrides only where a dependency ships
      no stubs.
- [x] 1.4 `pytest` configuration: `asyncio_mode`, marker registration, test paths.
- [x] 1.5 `import-linter` contracts: the four-layer package graph, the per-module
      `router → service → repository → models` layering, and one cross-module data-access contract per
      module.
- [x] 1.6 `uv.lock` committed.

## 2. Primitives below the database

- [x] 2.1 `shared/ids.py`: `uuid7()` per RFC 9562, monotonic within a millisecond.
- [x] 2.2 Unit tests: version and variant fields, ordering, monotonicity under a frozen clock.

## 3. Configuration and observability

- [x] 3.1 `core/config.py`: grouped settings — database, redis, celery, s3, ai, langsmith — plus
      `ENV`, `SECRET_KEY`, `APP_ENCRYPTION_KEY`. Cached accessor. Production guards against
      development defaults. Rejection of a synchronous database driver.
- [x] 3.2 `core/logging.py`: structlog pipeline, recursive key-name redaction, stdlib bridge so
      uvicorn and SQLAlchemy logs render through the same pipeline, JSON in deployed environments and
      console locally.
- [x] 3.3 `core/middleware.py`: correlation id (pure ASGI, so the contextvar survives to the
      exception handler) and the security headers `docs/security/baseline.md` mandates.
- [x] 3.4 Unit tests: redaction at depth, settings validation, correlation id propagation.

## 4. Errors

- [x] 4.1 `core/errors.py`: `VerityError` base with `code`, `http_status`, and a message that is safe
      to return; the subclass set; an internal-only `detail` that is logged and never serialised.
- [x] 4.2 The one exception handler set: domain errors, request validation, `HTTPException`, and the
      catch-all that returns a generic body and logs the real exception against the correlation id.
- [x] 4.3 Unit tests: envelope shape, no internals in the 500 body, correlation id echoed.

## 5. Tenant context — the load-bearing part

- [x] 5.1 `core/rls.py`: the setting name constant, `bind_tenant_context` using
      `set_config(:name, :value, true)` with bound parameters, a read-back helper, a guard that refuses
      to bind with no transaction open, and a guard repositories can assert on.
- [x] 5.2 `db/rls.py`: `enable_rls`, `add_tenant_policy`, `make_append_only`, and the policy predicate
      built once so no migration writes it by hand.
- [x] 5.3 Isolation tests: transaction-local lifetime, empty after commit and after rollback, no
      carry-over on a pooled connection, refusal outside a transaction, and the application role holds
      neither `SUPERUSER` nor `BYPASSRLS`.

## 6. Database access

- [x] 6.1 `core/db.py`: async engine with `pool_pre_ping`, sized pool, statement timeout; the session
      factory; `session_scope(tenant_id)` owning the transaction boundary; `get_session` and
      `get_tenant_session` dependencies; engine disposal on shutdown.
- [x] 6.2 `db/base.py`: `Base` with the naming convention and type annotation map; `UUIDPrimaryKey`,
      `Timestamped`, `TenantScoped`, `Integratable` mixins; `tenant_index` refusing a non-leading
      `tenant_id`; `status_check` producing a `CHECK` rather than an enum.
- [x] 6.3 Unit tests: index and constraint naming, `tenant_index` leading column, `status_check`
      rendering.

## 7. Cryptography

- [x] 7.1 `core/crypto.py`: keyring parsed from settings with an active key id and retained previous
      keys; AES-256-GCM data key per value wrapped by the master key; versioned dotted ciphertext
      carrying the key id; AAD binding; a `__repr__` that reveals nothing.
- [x] 7.2 Unit tests: round-trip, tamper detection, AAD mismatch, decryption under a rotated key,
      `repr` containing no key material.

## 8. Application

- [x] 8.1 `core/deps.py`: `Principal`, `TenantContext`, `get_current_principal`, `get_tenant_context`,
      `require(permission)` — signatures and docstrings fixed, bodies raising `NotImplementedError`
      naming Week 1.
- [x] 8.2 `core/health.py`: `/healthz` touching nothing; `/readyz` checking Postgres and Redis under
      timeout and reporting per-dependency status with no connection detail.
- [x] 8.3 `main.py`: `create_app()`, lifespan disposing the engine, explicit middleware order, the
      exception handlers, OpenAPI metadata, docs disabled outside development.
- [x] 8.4 Integration test: `/healthz` returns 200; `/readyz` returns 503 with the database down.

## 9. Migrations

- [x] 9.1 `db/migrations/env.py` on the async engine, migration role URL, `Base.metadata` as target,
      `compare_type` and `compare_server_default` on.
- [x] 9.2 `script.py.mako` carrying the RLS reminder into every generated migration.
- [x] 9.3 `alembic.ini` pointing at the package, empty `versions/`.
- [x] 9.4 `alembic upgrade head` runs clean against the local cluster.

## 10. Workers

- [x] 10.1 `workers/celery_app.py`: broker and backend from settings, JSON-only serialisation, UTC,
      late acknowledgement, prefetch of 1, beat schedule with one entry.
- [x] 10.2 `workers/tasks.py`: the no-op heartbeat, and the tenant-context-per-unit-of-work pattern
      written out where the next person to add a job will read it.
- [x] 10.3 A worker starts against the local Redis and registers the task.

## 11. AI client

- [x] 11.1 `modules/ai/llm.py`: LangSmith tracing configured from settings, provider-agnostic chat
      model construction with timeout and retry, and the rule-8 guardrail note.
- [x] 11.2 The client constructs with tracing enabled from environment configuration.

## 12. Infrastructure

- [x] 12.1 `infra/docker/docker-compose.yml`: postgres 16, redis 7, minio, minio bucket
      initialisation, health checks, named volumes. No Keycloak.
- [x] 12.2 `infra/docker/postgres/init/`: application and read-only roles, neither superuser nor
      `BYPASSRLS`; default privileges so tables the owner creates are usable by the application;
      `CREATE` revoked from `PUBLIC`.
- [x] 12.3 `.env.example` covering every setting, with development defaults that fail in production.
- [x] 12.4 `Makefile`: `setup`, `up`, `down`, `migrate`, `test`, `check`, and the per-tool targets the
      composites call.

## 13. Continuous integration

- [x] 13.1 `.github/workflows/backend-ci.yml`: Postgres and Redis services, roles created to match
      the compose init, `uv sync --frozen`, ruff, mypy, import-linter, `alembic upgrade head`, and
      pytest with `VERITY_REQUIRE_DB=1` so the isolation suite cannot skip.

## 14. Documentation

- [x] 14.1 `docs/architecture/multi-tenancy.md`: replace the unimplementable `SET LOCAL` snippet with
      the `set_config` form and the `NULLIF` policy predicate, and say why.
- [x] 14.2 `backend/CLAUDE.md`: state precisely where the transaction boundary is and why the tenant
      setting's lifetime decides it.
- [x] 14.3 `docs/runbooks/local-setup.md`: real commands, role setup, MinIO bucket, and the
      verification step.
- [x] 14.4 `backend/README.md`: layout, commands, and what is deliberately not here yet.
- [x] 14.5 `README.md`: correct the stale "Keycloak for identity" line and the `infra/` description.
