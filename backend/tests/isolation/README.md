# Isolation suite

A merge blocker (docs/conventions/testing.md). Never skipped, never red, never merged
with either.

## What is here now

There are no tenant-owned tables yet, so this suite asserts the **mechanism** rather
than the matrix:

- The role the application connects as is not a superuser and does not hold
  `BYPASSRLS`. If it did, every other assertion in this directory would be vacuously
  true and a green suite would be actively misleading.
- Tenant context is transaction-local: it is readable inside its transaction and empty
  in the next one, after both commit and rollback.
- A connection returned to the pool and handed out again carries no context from its
  previous user. This is the failure that pooling introduces and no query review would
  catch.
- Binding tenant context outside a transaction is refused rather than silently
  discarded.

## What Week 1 adds

Once `tenancy` and `iam` create tables, this suite gains the matrix
docs/architecture/multi-tenancy.md requires: two tenants seeded, and for every list,
read, update, and delete path, tenant B touches nothing of tenant A's — a cross-tenant
read by id returning 404 and never 403, and a cross-tenant write refused by the
`WITH CHECK` half of the policy.

Every new module adds its isolation test in the same change that adds the module.

## Rules for anything added here

Never disable row-level security in a fixture. Never connect as a role that can bypass
it. If a test needs two tenants, create two tenants.
