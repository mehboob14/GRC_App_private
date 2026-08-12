# Platform-wide audit trail

## Why

Rule 5 says every state-changing action writes `audit_log` with actor, timestamp, and before/after
snapshots. Two changes land immediately after this one — the provider plane and identity — and both
are nothing but state-changing actions. If the audit trail is not there first, every service written
in those changes has to be reopened to add it, and the ones that get missed are missed silently.

Immutability is a property this product sells to an auditor. "We do not update that table" is a code
review; a refused `UPDATE` is evidence. So the enforcement is a revoked grant plus a database
trigger, not a convention.

This change belongs to **Phase 1, deliverable 1.1 — Foundation**. It is the first change with a
table in it.

## What changes

- **Migration**: creates `audit_log` with row-level security, the tenant policy, the provider-plane
  policy, the revoked `UPDATE`/`DELETE` grant, and the trigger that refuses both — all in the same
  migration.
- `backend/src/verity/modules/audit/` — the `audit` module as a vertical slice: `models.py`,
  `repository.py`, `service.py` (`AuditService`), `schemas.py`, `router.py`.
- `AuditService.record(...)` writes on the **caller's session, inside the caller's transaction**, so
  a rolled-back change cannot leave an audit row claiming it happened.
- `AuditService.snapshot(...)` builds the before/after payloads with a deny-list that keeps
  secret-bearing columns out of the trail.
- `verity.db.rls.make_append_only` gains the trigger half; today it only revokes.
- One read route, `GET /api/v1/audit-log`, cursor-paginated, permission key `audit:read`.
- `backend/tests/isolation/test_audit_isolation.py` — two tenants, plus the provider-plane rows that
  must be invisible to both.

## Non-goals

- **No audit wiring for real actions.** Nothing in the system changes state yet. The services written
  in `add-provider-plane` and `add-identity-and-access` call `AuditService` as they are written; this
  change delivers the mechanism and proves it against records created by its own tests.
- **No provider-plane read endpoint.** Platform admins reading across tenants belongs with the admin
  panel, which is explicitly out of Week 1. The *write* path and the policy that will serve the read
  are both in place.
- **No retention or archival job.** Retention defaults to audit period + 1 year
  (`docs/conventions/database.md`); the job that enforces it is not Week 1, and deleting audit rows
  needs its own design because the table refuses deletes by construction.
- **No partitioning.** `check_results` is the one partitioned table (ER §5.9). Partitioning
  `audit_log` now would be speculative.
- **No frontend.**

## Modules touched

`audit` (new). `core` gains nothing; `db/rls.py` gains the trigger half of `make_append_only`.

No module boundary is crossed. Every other module will reach the audit trail through
`AuditService`, never through its repository or its table — this change establishes that as the only
available path by giving the module no other public surface.

## Closest-review flags

**This change touches the audit trail and tenant isolation. Both.**

- It creates the first append-only table. Review the trigger and the grant together: either alone is
  incomplete, because the grant does not bind the owner role and the trigger does not stop a
  privileged session that disables triggers.
- It introduces a **second GUC**, `app.provider_plane`, and a policy that reads it. That is a
  deliberate widening of what a session can see, and it is the single most security-sensitive thing
  in this change. `design.md` states the threat model and the stronger alternative that was not
  taken.
- `audit_log.tenant_id` is **not** a foreign key, deliberately, against the ER diagram. Reasoning in
  `design.md` — in short, a cascading delete on tenant teardown would be a `DELETE` against an
  append-only table, and the record of a teardown is exactly the record you cannot afford to lose.

## Deviations from the ER document, for approval

| ER Design says | This change does | Why |
|---|---|---|
| `tenant_id uuid FK` | `tenant_id uuid NULL`, no FK | Provider-plane events have no tenant; teardown must not cascade into the trail |
| `actor_id uuid FK` | `actor_type` + `actor_id`, no FK | One actor column cannot name a platform admin, a membership, and the scheduler |
| `action` in `create update transition approve delete` | unchanged | Authentication is recorded as `create`/`delete` on `object_type = 'session'` rather than inventing a value |
| `created_at`/`updated_at` on every table | `occurred_at` only | An `updated_at` on a table that refuses `UPDATE` is a column that can only ever lie |
