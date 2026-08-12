# Multi-tenancy and isolation

The single most important property of this platform. A user in one workspace must never read or
write another workspace's data, and this is proven by an automated test that runs on every change.

## Two planes

**Provider plane** — the internal panel where the team registers and manages customer companies.
Tables here have **no `tenant_id`**: `platform_admins`, `tenants`, `tenant_branding`,
`tenant_provisioning`. This is the deliberate exception to the rule below.

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
