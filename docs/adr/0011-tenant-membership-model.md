# ADR-0011: Users are global identities; membership is `tenant_memberships`

**Status: Accepted**
**Date:** 2026-08-10

## Context

The written requirements model a user as belonging to exactly one tenant. But the customer has raised
**global users** — an auditor, consultant, or partner who works across several organisations — as a
likely direction. Retrofitting cross-tenant users onto a one-tenant-per-user schema later would touch
the `users` table, every person-reference foreign key, RLS scoping, and the identity seam: exactly the
kind of rewrite this project avoids by designing later phases ahead. Designing the membership model
now, while it is still on paper, costs one join table and defaults to the same single-tenant behaviour.

## Decision

1. **A user is a global identity.** `users` (and `credentials`, `user_identities`) carry no
   `tenant_id`; email is unique globally. The row is the person, independent of any organisation.

2. **`tenant_memberships` is the tenant-scoped person.** A many-to-many join of user × tenant, carrying
   that tenant's role assignments and the auditor time-box columns (`engagement_id`, `valid_from`,
   `valid_until`). It carries `tenant_id` and sits under RLS like any tenant-owned row.

3. **Every in-tenant reference to a person is a FK to `tenant_memberships`, never to `users`.** Asset
   owner, control owner, approver, assignee, group member. This is what stops a person who is in two
   tenants from leaking across the boundary.

4. **Phase 1 defaults to one membership per user.** Signup creates one user + one membership; the invite
   flow adds a membership to the inviting tenant. The single-tenant experience is unchanged. A global
   user is the same schema with more than one membership — enabled later without a migration.

5. **Groups contain memberships, not users**, and are tenant scoped.

## Consequences

- `users`, `credentials`, `user_identities` join the global side of the model (no `tenant_id`),
  alongside the provider plane and global content — see [ADR-0007](0007-provider-plane-above-tenant-plane.md).
- The identity seam resolves the **active tenant** per request; authorization reads roles from the
  active membership, not from the user. A user with one membership behaves exactly as the old model did.
- Person-reference columns across the schema point at `tenant_memberships.id`. Getting this right on
  paper now is free; changing it after data exists is a migration on a live compliance platform.
- Uniqueness: email unique globally on `users`; `(tenant_id, user_id)` unique on `tenant_memberships`.

## Alternatives considered

**One tenant per user, as the requirements literally state.** Simpler today. Rejected as the default
because the customer flagged global users and the retrofit is a schema-and-code rewrite. The membership
model, defaulting to single, buys the option for the price of one join table.
