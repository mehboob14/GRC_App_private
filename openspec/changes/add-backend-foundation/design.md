# Design — backend foundation

## Layout, and where it differs from the file list that prompted it

`CLAUDE.md` assigns `core/` "config, db session, security, deps, errors, logging" and `db/`
"declarative base, RLS helpers, alembic migrations". So the declarative base lives in `db/base.py`,
not `core/base.py`.

"RLS helpers" splits in two, because the two halves have different jobs and different callers:

| File | Job | Called by |
|---|---|---|
| `core/rls.py` | Bind the tenant for a transaction at runtime | Every request and every job |
| `db/rls.py` | Emit the policy and grant DDL | Migrations only |

They share one constant — the setting name — which `core/rls.py` owns because the request path is
where getting it wrong is a breach.

`uuid7()` goes in `shared/ids.py`, not `core/ids.py`. `db/base.py` needs it for the primary-key
default, and the import-linter layering below puts `db` above `core`, so anything `db` depends on has
to sit below `core`. `shared/` is where `CLAUDE.md` puts "cross-module value objects and pure
helpers", which is what an id generator is.

## Import layers

Top to bottom, each layer may import the ones below it and not the ones above:

```
verity.modules
verity.db
verity.core
verity.shared
```

`db` above `core` rather than below is deliberate. `db/rls.py` needs the setting name from
`core/rls.py`, and Alembic's `env.py` needs `core/config.py` for the migration URL. Nothing in
`core/` needs anything from `db/` — the engine does not need `Base`, and `core/db.py` deals in
sessions, not tables. Putting `db` below `core` would have forced an `ignore_imports` exemption for
`env.py` on day one, and an exemption in the first commit is an exemption forever.

Inside a module, `router → service → repository → models`, with every layer optional so the contract
holds for modules that have not been written yet.

Cross-module isolation is one `forbidden` contract per module rather than a wildcard, because
import-linter's wildcards cannot express "any module's repository except my own". Fifteen contracts is
verbose; it is also greppable, and it fails with the offending import named.

## The tenant-context primitive

`SET LOCAL app.tenant_id = :tid` cannot be written that way. Postgres `SET` takes a literal, not a
bind parameter, so a bind-parameter version of the statement in `docs/architecture/multi-tenancy.md`
does not exist. The two options are string interpolation — a SQL injection sink on the single most
security-sensitive statement in the codebase — or `set_config`:

```sql
SELECT set_config('app.tenant_id', :tenant_id, true)
```

`set_config(name, value, is_local)` with `is_local = true` is exactly `SET LOCAL`; the third argument
is what makes it transaction-local. All three arguments are ordinary function arguments, so the
tenant id is a bound parameter. This is the form the code uses.

`docs/architecture/multi-tenancy.md` is updated in this change to show it, because the snippet as
written cannot be implemented safely and the next agent will copy it.

### The policy predicate

The documented predicate is `USING (tenant_id = current_setting('app.tenant_id')::uuid)`. Two
changes:

```sql
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
```

`current_setting(name, true)` returns NULL instead of raising when the setting was never set in this
session. Without the second argument, any query on a tenant table from a connection that has not yet
bound a tenant raises `unrecognized configuration parameter`, which surfaces as a 500 rather than as
an empty result.

`NULLIF(..., '')` handles the bound-but-empty case. The primitive binds `''` rather than NULL when
there is no tenant, because `set_config` has no NULL. `''::uuid` raises `invalid input syntax for
type uuid`; `NULLIF` turns it into NULL first, and `tenant_id = NULL` is NULL, which is not true, so
the row is filtered. Unbound means no rows, which is the fail-closed behaviour the spec requires.

`WITH CHECK` carries the same predicate, so a write cannot insert a row into a tenant other than the
bound one.

`FORCE ROW LEVEL SECURITY` is applied alongside `ENABLE`. `ENABLE` alone does not apply to the
table's owner, and migrations run as the owner. The application does not connect as the owner, so
`FORCE` is a second line rather than the only one — which is the point.

### Where the transaction boundary lives

`backend/CLAUDE.md` says services own transactions and repositories never commit. Taken literally as
"the service calls commit", it breaks the primitive: the tenant setting is transaction-local, so a
service that commits mid-request leaves every later statement in that request with no tenant bound
and reading zero rows. That failure is silent and looks like missing data.

So the transaction boundary is the unit of work, and the session dependency owns it:
`session_scope(tenant_id)` opens the transaction, binds the tenant inside it, yields, and commits on
clean exit or rolls back on exception. Services still never call `commit`; they use
`begin_nested()` when they need a savepoint. `backend/CLAUDE.md` is updated to say this precisely,
because the ambiguous version invites the bug.

## Envelope encryption

Per value: a random 256-bit data key encrypts the plaintext with AES-256-GCM; the master key encrypts
the data key with AES-256-GCM under its own nonce. The stored form is dotted, versioned base64:

```
v1.<key_id>.<b64 wrapped_dek>.<b64 dek_nonce>.<b64 nonce>.<b64 ciphertext>
```

`key_id` is in the ciphertext so a master key can be rotated by promoting a new key and keeping the
old one for decryption, rather than by re-encrypting every secret row in the database. Retrofitting a
key id into a format that is already in production means exactly that migration, which is why the
format is decided before there is a row to migrate.

The caller passes an `aad` context string, authenticated but not encrypted, so a ciphertext copied
from one row to another fails to decrypt. Callers pass something that identifies the row —
`connector_credential:<id>`, `credentials.mfa_secret:<membership_id>`.

Fernet was the obvious alternative and is rejected: AES-128-CBC with a single static key, no
per-value data key, no key id, and no AAD. It cannot express rotation and cannot bind a ciphertext to
its row.

## Failure behaviour of external dependencies

| Dependency | Timeout | On failure |
|---|---|---|
| Postgres | connect 10s, statement 30s (settings) | `/readyz` 503; request path returns the generic 500 envelope |
| Redis | 5s socket | `/readyz` 503; Celery `broker_connection_retry_on_startup` |
| S3 / MinIO | 10s connect, 30s read, 3 retries | Not exercised this change |
| LLM provider | 30s, 2 retries (settings) | Not exercised this change; Phase 2 adds the circuit breaker `docs/architecture/ai-features.md` requires |

`/healthz` contacts nothing, so a database outage does not get the process killed and restarted into
the same outage.

## What happens if this runs twice

- **`alembic upgrade head`** — idempotent; there are no revisions, so it is a no-op after the first
  run.
- **The Postgres role init script** — runs only on first container init, and is written
  `IF NOT EXISTS` so re-running it by hand against an existing cluster is safe.
- **The MinIO bucket creation** — `mc mb --ignore-existing`.
- **The no-op Celery task** — pure, no writes.
- **`uv sync`** — idempotent against the lockfile.

Nothing in this change writes a domain row, so there is no idempotency key to design yet. The
`Idempotency-Key` handling `docs/conventions/api.md` requires arrives with the first mutating
endpoint.

## Dependencies, and why each one

Runtime:

| Package | Why | Instead of |
|---|---|---|
| `fastapi` | The stack decision in `CLAUDE.md` | — |
| `uvicorn[standard]` | ASGI server; `[standard]` for `uvloop` and `httptools` | — |
| `sqlalchemy[asyncio]` | The stack decision; `[asyncio]` is the async extra | — |
| `asyncpg` | Async Postgres driver. A sync driver on the event loop blocks every request | `psycopg` sync, which the reference build used and which is the defect being avoided |
| `alembic` | The migration decision in `CLAUDE.md` | — |
| `pydantic` | Boundary validation, mandated by `docs/security/baseline.md` | — |
| `pydantic-settings` | Environment parsing and validation for one settings object | hand-rolled `os.environ` reads |
| `celery[redis]` | The queue decision in `CLAUDE.md`; the extra brings the Redis transport | — |
| `redis` | Direct client for the readiness probe and future rate limiting, separate from Celery's use | — |
| `httpx` | Async HTTP client for outbound calls and the ASGI test transport | `requests`, which is blocking and forbidden by `backend/CLAUDE.md` |
| `structlog` | Structured logging with a processor pipeline, which is what makes key-name redaction possible at all | stdlib `logging`, where redaction has no interception point |
| `cryptography` | AES-256-GCM for envelope encryption | `Fernet` alone — see above |
| `argon2-cffi` | Password hashing for Phase 1 native auth. Unused until Week 1 | `bcrypt`, which caps input at 72 bytes and is not the current recommendation |
| `pyotp` | TOTP for the MFA that `docs/security/baseline.md` requires of admin accounts. Unused until Week 1 | hand-rolled RFC 6238 |
| `pyjwt` | Session token signing. Unused until Week 1 | `python-jose`, which is effectively unmaintained and has a history of algorithm-confusion CVEs. This is a deliberate substitution for one of the two options offered |
| `boto3` | S3-compatible object storage client, which MinIO speaks | — |
| `tenacity` | Declarative retry with backoff for connector and LLM calls | retry loops written per caller |
| `langchain` | Provider-agnostic LLM interface | provider SDKs called directly, which couples every prompt to one vendor |
| `langchain-openai` | The provider binding for the default model. `init_chat_model` resolves providers lazily and needs the binding installed to construct anything. **Not in the original list; added because "the client constructs" is otherwise unverifiable** | — |
| `langsmith` | Prompt and output tracing, which `docs/architecture/ai-features.md` requires ("prompts and outputs are logged with the tenant, actor, model, and version") | a hand-rolled trace table |
| `orjson` | JSON serialisation for the structlog renderer | stdlib `json`, which cannot serialise `datetime` or `UUID` without a default hook |

Development: `ruff` (lint and format, replacing black + isort + flake8), `mypy` (strict typing),
`pytest`, `pytest-asyncio` (async test support), `pytest-cov` (coverage as the diagnostic
`docs/conventions/testing.md` calls it), `import-linter` (the boundary contracts), `types-redis` and
`types-passlib`-style stubs only where a package ships none.

Every runtime dependency is pinned to an exact version and the lockfile is committed, per
`docs/security/baseline.md`.

## Testing approach

`tests/unit/` needs no database: UUIDv7 properties, crypto round-trip and tamper and rotation,
redaction, error envelope shape, index naming, settings validation.

`tests/integration/` and `tests/isolation/` connect as the application role to a real Postgres with
RLS on. Locally, an unreachable database skips them with a message. In CI, `VERITY_REQUIRE_DB=1`
turns that skip into a failure, so the suite cannot quietly stop running — a skipped isolation suite
is the failure mode `docs/conventions/git.md` names as never acceptable.

`tests/isolation/` this change asserts the mechanism rather than the matrix, because there are no
tenant tables yet: the application role holds neither `SUPERUSER` nor `BYPASSRLS`; the tenant setting
is transaction-local; a pooled connection carries no context from its previous user; binding outside
a transaction is refused. Week 1 adds the two-tenant read/write/update/delete matrix on top, once
there are tables to put rows in.

## Rejected alternatives

**A `tenant_id` column with no FK.** `TenantMixin` declares the foreign key to `tenants.id` with
`ON DELETE CASCADE` even though `tenants` does not exist yet. It resolves when the `tenancy` module
defines the table, and nothing uses the mixin before then. The alternative — a bare UUID column with
a comment promising a constraint later — is the kind of promise that does not get kept.

**Field-level detail in the 422 envelope.** `docs/conventions/api.md` fixes the envelope at `code`,
`message`, `correlation_id`. Validation failures therefore return a code and no field detail, which
is poor for form UX. Extending the envelope is an API convention change and belongs in its own
change with the first real endpoint, not smuggled in here.

**A database-generated UUIDv7 default.** Postgres 16 has no `uuidv7()`; that arrives in 18.
Generating in the application also means an id exists before the insert, which the audit log needs.
