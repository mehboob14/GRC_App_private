# Database conventions

Postgres 16. SQLAlchemy 2.0 async. Alembic for migrations. These conventions come from the ER
design and are binding.

## Every table

- `id` — **UUIDv7** primary key (time-ordered). Not integers: identifiers must survive CSV import,
  cross-system sync, and merges without collision. See [ADR-0002](../adr/0002-uuidv7-primary-keys.md).
- `created_at`, `updated_at` — `timestamptz`, always. Store UTC, never naive datetimes.
- `tenant_id` — on every tenant-owned table, and the **leading column of every composite index**.
  Exceptions: provider plane and global content tables (see
  [multi-tenancy.md](../architecture/multi-tenancy.md)).

## Naming

- Tables: plural `snake_case` — `vuln_instances`, `vendor_engagements`.
- Columns: `snake_case`. Foreign keys: `<singular>_id`.
- Booleans read as assertions: `is_internet_facing`, `has_mfa`.
- Timestamps end in `_at`; dates end in `_on` — `next_reassessment_on`, `synced_at`.
- Indexes: `ix_<table>__<cols>`. Uniques: `uq_<table>__<cols>`. Checks: `ck_<table>__<rule>`.

## Status fields

Text with a `CHECK` constraint, **not** a Postgres enum. Adding a state must be a constraint
change, not a type migration. Enums are painful to alter under load and this product will grow
states.

## Integration fields

Every table that could ever receive a row from an outside system carries `source`, `external_id`,
and `synced_at` from day one, with a unique constraint on `(tenant_id, source, external_id)`.

This is what makes every future connector an idempotent upsert against tables that already exist.
No migration is ever "the integration migration." Apply it even when the table is manual-only
today — assets, vulnerabilities, tasks, users, vendors, discovered apps.

## Append-only tables

`audit_log`, `task_transitions`, `vuln_transitions`, `check_results`, `readiness_snapshots`,
`kri_measurements`, `document_versions`.

Insert only. No `UPDATE`, no `DELETE`, ever — enforced by a revoked grant, not by convention alone.
Immutability is a feature this product sells, and appending is the cheapest thing a database does.

## Partitioning

`check_results` is partitioned **by month from the first migration**. Daily checks × connectors ×
resources × tenants compounds fast, and repartitioning a live table is painful.

Nothing else is partitioned. Partitioning anything else now is speculative complexity.

## Deletion

Compliance objects — controls, risks, documents, vendors — are **disabled or closed with a
recorded reason and an explicit status**. Never hard-deleted. An auditor's first question about a
missing control is who removed it and why; the disable record is the answer.

Hard deletion exists only for drafts and tenant teardown.

## Files

The database stores a `file_ref` and a content hash. The file lives in object storage, served
through signed URLs. Never store file bytes in Postgres — it wrecks backup and restore times,
which is a property this platform has to demonstrate.

Retention defaults to audit period + 1 year. `legal_hold` exempts an item from retention deletion
and is the enforcement point for the data-handling rule.

## Linkage model

Hybrid, deliberately — see [ADR-0003](../adr/0003-hybrid-linkage-model.md):

- **Explicit join tables** for hot, dashboard-driving pairs: control↔requirement,
  evidence↔control, risk↔control, check↔control_template, remediation_ticket↔instances.
- **One polymorphic `links` table** for the long tail: task→anything, document→anything,
  asset→risk, vulnerability→evidence, incident→risk. Indexed in **both** directions so the trace
  view walks either way.
- **Direct foreign keys** for one-way promotions: vendor_finding→risk, check_result→evidence,
  vuln_instance→asset, asset→replaced_by_asset.

Do not add a polymorphic link where a hot join belongs, and do not add a twelfth join table for
something browsed rather than computed.

## Migrations

- One logical change per migration. Reversible unless genuinely impossible — say so in the
  docstring if not.
- Every migration that adds a tenant-owned table **must** enable RLS and add the policy in the
  same migration. A table without a policy is a silent isolation hole.
- Never edit a migration that has run anywhere but your machine.
- Backfills that touch large tables go in batches, in their own migration, separate from DDL.
