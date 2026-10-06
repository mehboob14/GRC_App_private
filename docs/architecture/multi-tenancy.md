# Multi-tenancy and isolation

The single most important property of this platform. A user in one workspace must never read or
write another workspace's data, and this is proven by an automated test that runs on every change.

## Two planes

**Provider plane** — the internal panel where the team registers and manages customer companies:
`platform_admins`, `tenants`, `tenant_branding`, `tenant_provisioning` (and the
`tenant_registration_keys` idempotency record). Only `platform_admins` and `tenants` carry no
`tenant_id` — branding and provisioning reference their tenant, per the ER, and **every one of
the five is RLS-protected** (see the policy table below). Provider-plane requests run under
`app.provider_plane`, bound by `core.db.provider_session_scope` for an authenticated platform
admin only, and never bind a tenant: provider routes address a tenant *as a resource*
(`/provider/tenants/{tenant_id}`), which is not the acting-tenant parameter `api.md` forbids.

**Tenant plane** — the application each customer company uses. Every operational table carries
`tenant_id`.

A **tenant is one customer company**. A **user is a global identity** (`users` carries no `tenant_id`;
email is unique globally); their place in a tenant is a `tenant_memberships` row carrying that tenant's
roles. Every in-tenant reference to a person FKs to the membership, never to the user. Phase 1 defaults
to one membership per user, so the single-company experience is unchanged; a global user (an auditor or
consultant across companies) is the same schema with more memberships — see
[ADR-0011](../adr/0011-tenant-membership-model.md).

Platform admins are a **separate population with separate tables and a separate login** from tenant
users. Do not model an operator as a tenant user with extra permissions.

## Global content tables

Framework content is shipped data, not tenant data. These carry no `tenant_id` and are read-only
to tenants: `frameworks`, `requirements`, `control_templates`, `checks`, questionnaire banks,
`document_templates`, `risk_templates`.

Tenant creation **instantiates** the library: each control template becomes a tenant control
carrying `template_id`, and the template's requirement mappings are copied into the tenant's map.
This is why adding ISO 27001, HIPAA, or GDPR later is inserting content, never changing schema.

## Enforcement — three layers, all required

**1. Session variable + RLS.** Every request opens its transaction by setting the tenant. The
statement is `set_config` rather than `SET LOCAL`, because `SET LOCAL` takes no bind parameter:
writing it means interpolating the tenant id into SQL, on the one statement in the system where
getting it wrong is a cross-tenant read.

```sql
SELECT set_config('app.tenant_id', :tenant_id, true);   -- true = transaction-local
```

Transaction-local is the point: the value dies with the transaction and cannot leak to the next
user of a pooled connection. `verity.core.rls.bind_tenant_context` is the only place that issues
it, and it refuses to run outside an open transaction rather than silently having no effect.

Every tenant-owned table has RLS enabled with a policy of this form, emitted by
`verity.db.rls.enable_rls`:

```sql
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
```

Both parts of that expression are load-bearing. `current_setting(..., true)` returns NULL instead
of raising when nothing is bound, and `NULLIF(..., '')` turns "bound to no tenant" — provider-plane
work, where `set_config` stores an empty string because it has no NULL — into NULL as well. A NULL
on either side matches no row, so an unbound query returns nothing and raises nothing. The shorter
`current_setting('app.tenant_id')::uuid` instead raises, which surfaces as a 500 and makes the
provider plane unusable.

The policy carries `WITH CHECK` as well as `USING`. Without it, reads are isolated and writes are
not, which is the more damaging half: a forged `tenant_id` would plant a row inside another
tenant's workspace.

**2. Application filter.** Repositories filter by `tenant_id` explicitly. RLS is the safety net,
not the mechanism. If RLS is the only thing stopping a cross-tenant read, one misconfigured
migration is a data breach.

**3. Automated isolation test.** `backend/tests/isolation/` seeds two tenants and asserts that
every list, read, update, and delete path returns or touches nothing belonging to the other. This
suite runs in CI on every change and is a merge blocker. It connects as the application role and
refuses to run at all if that role can bypass a policy — a suite running as a superuser proves
nothing while appearing to prove everything.

## Dual-plane tables and `app.provider_plane`

A few tables serve **both planes** — `audit_log`, whose `tenant_id` is the stream an
event belongs to and is NULL for provider-plane events, and the four identity-resolution
tables described below. One tenant policy cannot express "each
tenant sees its stream *and* an authenticated operator sees every stream", so a dual-plane table
carries **four policies**, keyed on two settings:

```sql
CREATE POLICY <t>_tenant_select   ON <t> FOR SELECT
  USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
CREATE POLICY <t>_tenant_insert   ON <t> FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
CREATE POLICY <t>_provider_select ON <t> FOR SELECT
  USING      (NULLIF(current_setting('app.provider_plane', true), '') = 'on');
CREATE POLICY <t>_provider_insert ON <t> FOR INSERT
  WITH CHECK (NULLIF(current_setting('app.provider_plane', true), '') = 'on');
```

Postgres combines permissive policies with `OR`, which is what lets the provider plane read across
streams without weakening the tenant predicate. A row with `tenant_id IS NULL` never satisfies the
tenant predicate — `NULL = anything` is not true — so provider-plane rows are invisible to every
tenant session **by construction**, and an unbound session sees nothing at all. On an append-only
table there is deliberately no UPDATE or DELETE policy: with RLS enabled and no policy for a
command, the command matches nothing.

`app.provider_plane` is a second transaction-local setting, bound through the same
`set_config(..., true)` primitive as the tenant id, by **exactly one code path**:
`verity.core.db.provider_session_scope`, entered on behalf of an authenticated platform
admin, by the iam module's authentication flows for identity resolution (below), or by the
leads module's one public route, which writes only the provider-plane `demo_requests` table and
its audit row (`data-model.md`). It is never
derived from a request parameter, a header, or a token claim a tenant user can
influence. It is honestly a switch that widens visibility and is only as strong as the code that
sets it — the same property `app.tenant_id` already has. The GUC approach (over a dedicated
database role with its own pool) was approved in `openspec/changes/week1-review-decisions.md`,
item 4, to be revisited when the provider admin panel grows real tenant-data reads.

## Identity resolution runs before any tenant is bound

Authentication cannot start from a tenant: a login knows an email, a session or invite token
knows a membership id, and only the membership row knows which tenant it belongs to. Two
mechanisms make that resolution safe (`add-identity-and-access`):

- **The global identity tables carry no RLS at all.** `users`, `credentials`,
  `user_identities`, and the global `permissions` catalogue have no `tenant_id` and no tenant
  policy, so the login-by-email lookup succeeds regardless of which tenants the person belongs
  to — and regardless of any tenant a buggy pooled connection might still think is bound,
  because the lookup never consults `app.tenant_id`.
- **The four tenant-scoped tables that answer the rest of the resolution** —
  `tenant_memberships`, `group_members`, `roles`, `role_assignments` — carry an additional
  **SELECT-only** policy keyed on `app.provider_plane`. The iam auth flows and
  `core.deps.get_current_principal` run those reads inside `provider_session_scope`; there is
  deliberately no INSERT/UPDATE/DELETE policy on that plane, so every write still requires the
  bound tenant. Signup is the sanctioned exception that needs both: it writes the tenant
  register under the provider setting and then binds the new tenant *in the same transaction*
  to write the first membership — one transaction, no partials.

The route's own tenant-bound session is opened only after the membership has named its tenant
(`get_tenant_session`), and the tenant is taken from the membership row — never from a request
parameter, and never from the token beyond the membership id it names.

## The provider plane's own tables

The tenancy migration polices all five provider-plane tables with the same two settings
(`add-provider-plane/design.md`; each policy `FOR ALL ... WITH CHECK` on the provider side,
`FOR SELECT` only on the tenant side):

| Table | Tenant plane | Provider plane |
|---|---|---|
| `platform_admins` | no policy — invisible | full |
| `tenants` | `SELECT` where `id` = bound tenant | full |
| `tenant_branding` | `SELECT` where `tenant_id` = bound tenant | full |
| `tenant_provisioning` | `SELECT` where `tenant_id` = bound tenant | full |
| `tenant_registration_keys` | no policy — invisible | full |

Two properties are deliberate. **`tenants` is RLS-protected on its own primary key** — it carries
no `tenant_id`, so its policy reads `id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`.
A strengthening of ADR-0007: without it, one missing `WHERE` clause in any tenant-plane query
against the register lists every customer company by legal name. **The tenant plane gets `SELECT`
only, everywhere.** Lifecycle, plan, branding, and provisioning are written from the provider
plane; a tenant changing its own plan is a business-logic hole the database itself closes. With
no tenant-side INSERT/UPDATE/DELETE policy, writes match nothing or are refused outright —
`tests/isolation/test_tenancy_isolation.py` proves both directions.

## Rules

- The application connects as a role **without** `BYPASSRLS`. Migrations use a separate role.
- Never use `SECURITY DEFINER` to work around a policy.
- Never disable RLS in a test fixture. If a test needs two tenants, create two tenants.
- `tenant_id` is always the **leading column of every composite index**. A query plan that filters
  on tenant last is a performance bug waiting for your largest customer.
- Background jobs and Celery workers must set the tenant context explicitly per unit of work.
  A worker that iterates tenants sets it once per tenant, inside the transaction.
- Anything reached by an unauthenticated route (vendor questionnaire portal tokens, acknowledgement
  links) resolves its tenant **from the token**, never from user input.

## Why shared schema and not schema-per-tenant

Per-tenant schemas multiply migration, backup, and operational work by the number of tenants —
a heavy burden for a small team. Shared schema with RLS gives strong isolation at single-schema
cost. Revisit only if an enterprise customer contractually requires physical separation; the
`tenant_id` column and the provider plane make that migration possible later.

See [ADR-0001](../adr/0001-shared-schema-multi-tenancy-with-rls.md).
