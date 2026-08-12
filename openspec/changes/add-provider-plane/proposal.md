# Provider plane: the tenants register, branding, and provisioning

## Why

A tenant is the root object every other row in the system hangs off. Nothing tenant-owned can be
created until a tenant can be, and the tenant profile is not administrative trivia — the legal name
and registered address captured once at registration are what generated policies carry later, so
getting the field set right now is what stops every document being retyped.

This is also where the two planes become real rather than a diagram. Up to now "provider plane" has
been a rule in `CLAUDE.md`. This change gives it tables, a login, and a policy boundary that a test
can push against.

This change belongs to **Phase 1, deliverable 1.1 — Foundation**. It depends on `add-audit-trail`,
because every route in it changes state.

## What changes

- **Migration**: `platform_admins`, `tenants`, `tenant_branding`, `tenant_provisioning`, each with
  row-level security and its policies in the same migration.
- `backend/src/verity/core/security.py` — the shared authentication primitives both planes use:
  argon2id password hashing, TOTP verification, and signed session tokens. Placed in `core` because
  `add-identity-and-access` needs the same three for tenant users, and duplicating a password hasher
  is how two hashers with different parameters end up in one codebase.
- `backend/src/verity/modules/tenancy/` — the vertical slice: models, repository, service, schemas,
  router.
- **Platform-admin authentication** with **mandatory TOTP**. There is no configuration flag that
  turns it off, and no provider route is reachable without it.
- **Provider-plane API**: register a tenant, list and read tenants, update the profile, set branding,
  run and inspect provisioning.
- **Tenant-plane API**: a tenant reads its own profile and its own branding. Two routes, so the
  boundary is exercised from both sides.
- Every state-changing route calls `AuditService` in its own transaction.
- `backend/tests/isolation/test_tenancy_isolation.py`.

## Non-goals

- **No admin-panel UI.** Explicitly out of Week 1, and no frontend is touched.
- **No self-service trial signup.** Signup creates a tenant *and* its first user *and* their
  membership; the last two do not exist until `add-identity-and-access`. Signup ships there, on top
  of the registration service written here.
- **No `tenant_signups` table.** It appears in no version of the data model. Registration writes the
  `tenants` row directly with `status = 'provisioning'` and its provisioning steps, which the ER
  design already supports. If email verification and anti-abuse later need unverified signups held
  out of the tenants register, that is a deliberate ER change at that point and not a guess now.
- **No content seeding.** The `seed_content` provisioning step is recorded and left `pending`; the
  control library belongs to the compliance module, which is not Week 1.
- **No invitation email.** The `invite_admin` step records the invitation; delivery belongs to the
  notifications module. The tenant's first admin is created directly in
  `add-identity-and-access`.
- **No impersonation.** A platform admin never acquires a tenant session in Week 1. Provider routes
  address tenants as resources; they never bind tenant context.
- **No tenant teardown.** Hard delete for teardown is permitted by the conventions and needs its own
  design, because the audit trail deliberately survives it.

## Modules touched

`tenancy` (new), `core` (gains `security.py`), `audit` (consumed through `AuditService` only).

No module boundary is crossed. `tenancy` calls `audit`'s service and never its repository or its
table.

## Closest-review flags

**This change touches tenant isolation, authentication, and the audit trail. All three.**

- It creates the first tables a tenant session can reach, so it is the first real test of the RLS
  mechanism built in the foundation change.
- It introduces authentication, including the argon2id parameters and the TOTP window that
  `add-identity-and-access` will inherit unchanged for every tenant user.
- It stores a secret — the tenant's SMTP credentials — which must pass through `core/crypto.py`
  before it reaches the database and must never appear in a log line, an error, or an audit snapshot.

## Deviations and conflicts needing a decision at review

**1. `platform_admins` has nowhere to keep a credential.** The ER diagram gives it `id`, `email`,
`full_name`, `role`, `mfa_enabled`, and `status` — no password hash and no MFA secret. Platform
admins have their own login (ADR-0007: two populations, two logins) and cannot borrow the
`credentials` table, which keys on `users.id`. **Proposed:** add `password_hash`,
`mfa_secret_encrypted`, and `recovery_codes_encrypted` to `platform_admins`, which already carries
`mfa_enabled` and so already carries the credential concern. **Alternative:** a
`platform_admin_credentials` table mirroring `credentials`, which follows the ER's stated reasoning
for keeping secrets out of the person table. Either way this is a table or column not in the data
model and needs your explicit approval.

**2. `CLAUDE.md` rule 2 and the ER diagram disagree about branding and provisioning.** Rule 2 lists
branding and provisioning as provider plane with no `tenant_id`; the ER diagram gives
`tenant_branding` a `tenant_id` primary key and `tenant_provisioning` a `tenant_id` foreign key.
**Proposed:** the ER wins on the column — they must reference their tenant — and they get RLS
policies, which resolves the contradiction rather than choosing a side. Rule 2 then reads as being
about `platform_admins` and `tenants`, which genuinely have no `tenant_id`.

**3. `tenants.created_by` must be nullable.** The ER marks it "platform admin who registered it".
Self-service signup has no platform admin. Nullable, with the audit trail carrying who or what
created the row.

**4. `tenant_provisioning.status` has no failure value.** The ER allows `pending` and `done` only. A
step that fails stays `pending` and is retried. If you want `failed`, it is a `CHECK` change and a
line in the ER document.
