# ADR-0001: Shared schema multi-tenancy with row-level security

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

Several customer companies run isolated on one deployment. Isolation must be provable, and the
team operating this is small.

## Decision

One schema. `tenant_id` on every operational row. Postgres row-level security as a second wall
keyed on `tenant_id`. An automated isolation test runs on every change. The provider plane
(platform admins, tenants register, branding, provisioning) is a small set of global tables above
the tenant boundary.

## Alternatives considered

**Schema or database per tenant.** Rejected: multiplies migration, backup, and operational work
by the number of tenants, a heavy burden for a small team.

**Application filter only, no RLS.** Rejected: one forgotten WHERE clause is a breach.

## Consequences

Strong isolation at single-schema cost. Every query path must set tenant context, including
workers and unauthenticated token routes. `tenant_id` must lead every composite index.

**Revisit when:** an enterprise customer contractually requires physical separation.
