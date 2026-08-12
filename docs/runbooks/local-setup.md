# Local setup

Every command here has been run end to end against this repository. If one of them stops being
true, fix it in the same change that broke it — a runbook nobody has followed is a guess.

## Prerequisites

Docker Desktop, Python 3.12, and [`uv`](https://docs.astral.sh/uv/). Node 20+ and `pnpm` join
when the frontend does.

On Windows, `make` is not present by default. Either work inside WSL or run the command each
target wraps; every target below names it.

## 1. Install

```bash
make setup      # copies .env.example to .env, then: uv --directory backend sync --frozen --extra dev
```

`.env` is created once and never overwritten. It is git-ignored. The development defaults in it
are safe on a laptop and are refused outright in a deployed environment: `Settings` will not
construct with `ENV=production` while `SECRET_KEY` or `APP_ENCRYPTION_KEY` still hold theirs.

## 2. Bring up the stack

```bash
make up         # docker compose -f infra/docker/docker-compose.yml up -d --wait postgres redis minio
```

PostgreSQL 16, Redis 7, and MinIO. Keycloak is not part of Phase 1 — native auth — and joins for
the external-IdP phase ([ADR-0006](../adr/0006-keycloak-as-identity-provider.md)).

The Postgres container runs [`infra/docker/postgres/init/01-roles.sh`](../../infra/docker/postgres/init/01-roles.sh)
on an empty data directory, which creates three roles:

| Role | Used by | Properties |
|---|---|---|
| `verity_owner` | migrations | owns the schema |
| `verity_app` | the API and the workers | owns nothing, `NOSUPERUSER`, `NOBYPASSRLS` |
| `verity_readonly` | ad-hoc reads | `SELECT` only; row-level security still applies |

The split is not decoration. A table's owner is exempt from `ENABLE ROW LEVEL SECURITY` unless
the table also carries `FORCE`, so an application connecting as the owner would be protected only
by every migration having remembered `FORCE` — and one forgotten `FORCE` opens everything. See
[multi-tenancy](../architecture/multi-tenancy.md).

`make up` also runs a one-shot `minio-init` service that creates the evidence bucket and enables
versioning on it.

## 3. Migrate

```bash
make migrate    # uv --directory backend run alembic upgrade head
```

Alembic connects as `DATABASE_MIGRATION_URL` (the owner), never as the application role. There
are no domain migrations yet, so on a fresh database this creates `alembic_version` and stops.

## 4. Run

```bash
make run        # uvicorn verity.main:app --reload --host 127.0.0.1 --port 8000
make worker     # celery -A verity.workers.celery_app:celery_app worker --loglevel=info
make beat       # celery -A verity.workers.celery_app:celery_app beat --loglevel=info
```

Two probes, and they are different on purpose:

```bash
curl -s localhost:8000/healthz   # {"status":"ok","service":"verity-api","version":"0.1.0"}
curl -s localhost:8000/readyz    # {"status":"ready","dependencies":{"database":"ok","redis":"ok"}}
```

`/healthz` contacts nothing, so a database outage does not get every replica killed and restarted
into the same outage. `/readyz` reports each dependency and answers 503 when one is down, so an
unready replica leaves the load balancer and keeps running. Neither reports a host, a DSN, or a
driver message.

API docs are served at `/docs` in local and test environments only.

## 5. Check and test

```bash
make check      # ruff format --check, ruff check, mypy --strict, lint-imports
make test       # VERITY_REQUIRE_DB=1 pytest  (unit + integration + isolation)
```

`make test` sets `VERITY_REQUIRE_DB=1`, which turns an unreachable database from a skip into a
failure. Without it — running `pytest` directly — the database suites skip with a message, which
is convenient locally and unacceptable in CI: a silently skipped isolation suite is a green build
that proves nothing.

## Verify the setup is actually correct

```bash
make test-isolation    # VERITY_REQUIRE_DB=1 pytest tests/isolation -v
```

If this fails, the roles are wrong before anything else is. The suite refuses to run at all if the
connection can bypass row-level security, and `test_application_role_cannot_bypass_row_level_security`
asserts it as a visible result rather than only a refusal. A suite that runs as a superuser or a
`BYPASSRLS` role proves nothing while appearing to prove everything.

## Configuration

Every setting is read from the environment exactly once, into `verity.core.config.Settings`.
Nothing else in the codebase reads `os.environ` for configuration. `.env.example` is the complete
list with its development defaults; the ones that must change before a deployed environment are
marked there.

Both `<repo>/.env` and `backend/.env` are read, the backend one taking precedence.

## Without Docker

Postgres 16, Redis, and MinIO installed natively — or in WSL — work exactly as well; nothing in
the application knows the difference. Two things to get right:

- Run [`infra/docker/postgres/init/01-roles.sh`](../../infra/docker/postgres/init/01-roles.sh)
  by hand against the database. It is guarded throughout and safe to re-run. It expects
  `POSTGRES_USER` and `POSTGRES_DB` in the environment and, outside the container, a
  `verity_owner` that holds `CREATEROLE`.
- Point `DATABASE_URL` and `DATABASE_MIGRATION_URL` at whatever port it ended up on. A native
  Postgres already occupying 5432 is the usual reason the suite connects to the wrong cluster and
  reports that a role does not exist.

## Seed the first platform admin

The provider plane is unreachable until one operator exists, and operators are otherwise created
through the provider panel — which needs an operator. The bootstrap:

```bash
cd backend
uv run python -m verity.manage seed-platform-admin \
    --email ops@example.com --name "Ops Admin" --role super_admin
```

- Refuses to run once **any** platform admin exists; further admins are managed through the
  provider API by a `super_admin` (`platform_admins:manage`).
- Prints a generated one-time password exactly once (or takes it from
  `VERITY_SEED_ADMIN_PASSWORD` if set). It is printed, never logged — the logging pipeline
  redacts anything password-shaped by design.
- The admin is created **unenrolled**. TOTP is mandatory on the provider plane, so the first
  login forces enrollment:
  1. `POST /api/v1/provider/login` with the email and password → `next_step: "mfa_enroll"` and a
     five-minute challenge token. No session is issued.
  2. `POST /api/v1/provider/mfa/enroll` with the challenge → the TOTP secret and an
     `otpauth://` URI to scan into an authenticator app.
  3. `POST /api/v1/provider/mfa/confirm` with the challenge and a current code → the first
     session token plus eight single-use recovery codes, shown once. Store them.
  Subsequent logins are `login` → `mfa/verify` with a code (or one recovery code, which is
  consumed by use).

## Seed global content

Frameworks, requirements, control templates, checks, risk and document templates — plus a demo
tenant. Not built yet; it arrives with the first domain modules. Seeding will be idempotent and
safe to re-run.

## Still to document

Backup and restore (a Phase 1 exit criterion — write it while it is fresh, not at the demo), and
the frontend once it exists.
