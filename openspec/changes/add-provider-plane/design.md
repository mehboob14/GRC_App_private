# Design — provider plane

## Tables

Columns come from the ER Design document §3.1, provider-plane diagram. That diagram is unaffected by
the identity update and is byte-identical in both versions of the document, so it is usable as-is.
`created_at` and `updated_at` are added to each per `docs/conventions/database.md` and are not
repeated below.

```
platform_admins
  id                        uuid  PK, UUIDv7
  email                     text  NOT NULL UNIQUE
  full_name                 text  NOT NULL
  role                      text  NOT NULL   CHECK IN ('super_admin','onboarding','support')
  mfa_enabled               bool  NOT NULL DEFAULT false
  status                    text  NOT NULL   CHECK IN ('active','disabled')
  password_hash             text  NOT NULL   -- NOT IN THE ER DOCUMENT. See proposal, deviation 1.
  mfa_secret_encrypted      text  NULL       -- NOT IN THE ER DOCUMENT.
  recovery_codes_encrypted  jsonb NULL       -- NOT IN THE ER DOCUMENT.
```

```
tenants
  id                     uuid PK, UUIDv7
  legal_name             text NOT NULL      -- used in generated documents
  trading_name           text NULL
  slug                   text NOT NULL UNIQUE   -- subdomain
  industry               text NULL
  registration_number    text NULL
  address_line1          text NULL
  address_line2          text NULL
  city                   text NULL
  state_region           text NULL
  postal_code            text NULL
  country                text NULL
  primary_contact_name   text NULL
  primary_contact_email  text NULL
  primary_contact_phone  text NULL
  plan                   text NOT NULL
  status                 text NOT NULL  CHECK IN ('provisioning','active','suspended','terminated')
  created_by             uuid NULL  FK -> platform_admins.id   -- NULL for self-service signup
  onboarded_at           date NULL
  notes                  text NULL
```

`legal_name`, `slug`, `plan`, and `status` are the only required fields. Everything else is captured
at registration where known and completed later, because a trial signup will not have a registration
number to hand and refusing the signup over it would be the wrong trade.

```
tenant_branding
  tenant_id          uuid PK, FK -> tenants.id ON DELETE CASCADE
  logo_ref           text NULL
  primary_color      text NULL
  secondary_color    text NULL
  custom_domain      text NULL UNIQUE
  email_from_name    text NULL
  email_from_address text NULL
  smtp_config_ref    text NULL    -- application-layer ciphertext, never plaintext
  document_footer    text NULL
```

```
tenant_provisioning
  id           uuid PK, UUIDv7
  tenant_id    uuid NOT NULL FK -> tenants.id ON DELETE CASCADE
  step         text NOT NULL  CHECK IN ('create_tenant','seed_content','invite_admin','verify')
  status       text NOT NULL  CHECK IN ('pending','done')
  completed_at timestamptz NULL
  UNIQUE (tenant_id, step)
```

`UNIQUE (tenant_id, step)` is what makes provisioning idempotent — see below. `CHECK ((status =
'done') = (completed_at IS NOT NULL))` keeps the two columns from disagreeing.

## Row-level security, and the contradiction it resolves

`CLAUDE.md` rule 2 lists branding and provisioning as provider-plane tables with no `tenant_id`. The
ER diagram gives `tenant_branding` a `tenant_id` primary key and `tenant_provisioning` a `tenant_id`
foreign key. They cannot be both.

The ER is right about the column — a branding row is meaningless without knowing whose it is — so the
resolution is to keep the column *and* add the policy, which satisfies rule 1 as well. Rule 2 then
means what it can mean: `platform_admins` and `tenants` carry no `tenant_id`.

All four tables get RLS. The pattern is the one established in `add-audit-trail`: a tenant policy
keyed on `app.tenant_id`, and a provider policy keyed on `app.provider_plane`, combined by Postgres
with `OR`.

| Table | Tenant plane | Provider plane |
|---|---|---|
| `platform_admins` | no policy — invisible | full |
| `tenants` | `SELECT` where `id` = bound tenant | full |
| `tenant_branding` | `SELECT` where `tenant_id` = bound tenant | full |
| `tenant_provisioning` | `SELECT` where `tenant_id` = bound tenant | full |

Two notes on this table.

**`tenants` gets a policy keyed on its primary key.** ADR-0007 says `tenants` carries no `tenant_id`,
and it still does not — the policy reads `id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`.
This is a strengthening rather than a deviation: without it, a missing `WHERE` clause in any
tenant-plane query against the register lists every customer company by legal name, which is a
confidentiality incident that costs nothing to make impossible.

**The tenant plane gets `SELECT` only, everywhere.** Lifecycle, plan, branding, and provisioning are
written from the provider plane. A tenant changing its own plan is a business-logic hole that the
policy closes at the database.

This also settles a question raised in `add-audit-trail`'s design: the provider plane is defended by
the GUC-keyed policy consistently, not on `audit_log` alone. If that is later judged too weak, the
upgrade — a dedicated `verity_provider` role with `TO verity_provider USING (true)` and its own
connection pool — replaces the provider policies on all five tables at once, and nothing above the
policy layer changes.

## Indexes

`tenant_id` leads every composite index.

| Index | Columns |
|---|---|
| `uq_tenants__slug` | `(slug)` |
| `ix_tenants__status` | `(status)` — the provider register's default filter; no `tenant_id` exists on this table |
| `uq_tenant_provisioning__tenant_id_step` | `(tenant_id, step)` |
| `ix_tenant_provisioning__tenant_id_status` | `(tenant_id, status)` |
| `uq_tenant_branding__custom_domain` | `(custom_domain)` — partial, `WHERE custom_domain IS NOT NULL` |

## Shared authentication primitives

`core/security.py` holds three things, and `add-identity-and-access` reuses all three unchanged.
`backend/CLAUDE.md` assigns `security` to `core`, and the alternative — a hasher in `tenancy` and
another in `iam` — is how two argon2 configurations with different parameters end up in one codebase.

**Password hashing: argon2id.** Parameters are pinned in code, not configuration, and recorded here
so a later change cannot quietly weaken them: `time_cost=3`, `memory_cost=65536` (64 MiB),
`parallelism=4`, `hash_len=32`, `salt_len=16`. These are the argon2-cffi defaults at the OWASP
second recommended option. `verify()` reports when a stored hash used older parameters so it can be
rehashed on the next successful login.

**TOTP.** 30-second step, 6 digits, SHA-1 (what every authenticator app implements), and a window of
one step either side for clock skew. The last accepted counter is stored so a code cannot be
replayed inside its own window — `pyotp` does not do this and a naive implementation leaves a
30-second replay open.

**Session tokens.** Signed with `SECRET_KEY`, carrying subject, plane, issued-at and expiry, and
nothing authorization-bearing: no roles, no permissions, no tenant. Roles change and a token does
not, so authorization is resolved per request from the database. The token names *who*, never *what
they may do*.

The MFA challenge issued between the password step and the code step is a separate short-lived token
with a distinct type claim, valid for five minutes, accepted by the TOTP route and by nothing else. A
challenge that a session-consuming route would accept is a bypass of the second factor.

## The MFA secret

Stored through `core/crypto.py`'s envelope encryption, with the additional authenticated data bound
to the row that owns it (`platform_admin:<id>`). Binding matters: without it, ciphertext copied from
one admin's row to another's decrypts cleanly, and an attacker with write access to the table can
move a known secret onto a target account.

Recovery codes are stored as argon2id hashes of single-use codes, not as recoverable ciphertext,
because nothing needs to read them back — only to check one.

## Authorization on the provider plane

The `permissions`, `roles`, and `role_permissions` tables are tenant-scoped, so they cannot hold a
provider-plane grant. Provider routes still declare a two-part key, and the key set for each
`platform_admins.role` is a mapping held in code:

| Role | Keys |
|---|---|
| `super_admin` | all of the below, plus `platform_admins:manage` |
| `onboarding` | `tenants:create`, `tenants:read`, `tenants:update`, `tenants:brand`, `tenants:provision` |
| `support` | `tenants:read` |

"Every route declares its permission" therefore holds on both planes; only the resolution differs,
and the dependency that enforces it is the same one.

## Tenant identifiers in provider-plane paths

`docs/conventions/api.md` forbids the tenant as a path or query parameter. Provider routes are
`/api/v1/provider/tenants/{tenant_id}`, which looks like a violation and is not: the rule is about
the *acting* tenant, and these routes address a tenant **as a resource**, in the way
`/api/v1/vendors/{vendor_id}` addresses a vendor.

The line that must not be crossed: no provider route binds `app.tenant_id` from a path parameter.
Provider sessions bind `app.provider_plane` and nothing else. Acting *as* a tenant is impersonation,
which is not in this change, and when it arrives it is an explicit audit-logged flow per `api.md`.

## Idempotency — what happens if this runs twice?

**Registration** accepts an `Idempotency-Key`. The key, the platform admin, and a hash of the request
body are recorded with the resulting tenant id; a repeat with the same key returns the original
tenant rather than creating a second one. A repeat with the same key and a *different* body is a
409 — silently returning the first result would hide a client bug. The slug's unique constraint is
the backstop when no key is supplied, and it surfaces as a 409, not a 500.

**Provisioning** is idempotent by construction. Steps are rows with `UNIQUE (tenant_id, step)`;
running provisioning selects the pending ones and completes them, so a second run finds nothing to do
and writes nothing — including no duplicate audit records, because no state changed. Completing the
last step and flipping the tenant to active are in one transaction, so a crash between them cannot
leave a tenant with every step done and a status of provisioning.

**Branding** is a full replace of one row keyed by `tenant_id`, which is idempotent by definition.

## Dependencies, timeouts, and failure

The only dependency in this change is Postgres, covered by the statement timeout already configured
on the engine. There is no external call: no mail is sent, no content is seeded, no object storage is
touched.

Two future steps have external dependencies and are deliberately inert here. `invite_admin` records
the invitation and does not deliver it; `seed_content` stays pending. When each is implemented it
gets its own timeout and its own retry, and neither may hold the registration transaction open —
registration commits, and delivery happens after, or the tenant's existence depends on an SMTP
server being reachable.

Argon2 verification at the pinned parameters costs roughly 50 ms of CPU per attempt by design. Login
routes are rate-limited per `api.md`, more tightly than the rest, because a hash that is expensive
for an attacker is equally expensive for the server.

## Reversibility

The migration is reversible. The downgrade drops the four tables, which destroys every tenant on the
deployment; the docstring says so plainly.
