# Data model

**Source of truth:** the *Data Model and ER Design* document. This file is the working summary that
agents and engineers read. If the two disagree, the ER document wins and this file gets fixed.

## Three principles

1. **Frameworks are content; controls belong to the organisation.** Framework requirements, the
   prebuilt control library, checks, and templates ship as read-only global data. The
   organisation's records map onto them.
2. **Every operational row is tenant scoped.** `tenant_id` on every tenant-owned table, enforced on
   every query. Isolation is structural, not an afterthought.
3. **Every ingestible record is born integration ready.** `source`, `external_id`, `synced_at` from
   day one on anything that could ever arrive from an outside system.

## Module notes that are easy to get wrong

**Tenancy.** Two planes. Provider plane tables carry no `tenant_id`. A **user is a global identity**
(`users`, `credentials`, `user_identities` carry no `tenant_id`; email is unique globally). Membership
in a tenant is **`tenant_memberships`** — the many-to-many join; roles reach the person through
`role_assignments`, which also carries the auditor time-box (`engagement_id`, `valid_from`,
`valid_until`). Every in-tenant reference to a person (owner, approver, assignee, group member) FKs to
the **membership**, never to `users`. Phase 1 defaults to one membership per user; global users (a person
across several tenants) is the same schema with more rows, no rewrite — see
[ADR-0011](../adr/0011-tenant-membership-model.md).

**Identity (IAM).** Phase 1 uses native auth (the `credentials` table: password hash + encrypted MFA
secret). `user_identities` is the federation seam and is **provider-agnostic**, keyed by provider
name, provider type (OIDC / SAML), and external subject. The customer's external Keycloak, a future
in-house Keycloak, or a direct Entra / Okta / Google connection are all just rows there. Users are
decoupled from how they authenticate, so any identity provider is added behind the `current_identity`
seam **additively, never a schema rewrite**. Authorization (roles, groups, permissions, object-scoped)
always lives in the platform, never in the IdP. See
[ADR-0006](../adr/0006-keycloak-as-identity-provider.md).

**Audit.** `audit_log` is append-only and serves both planes. `tenant_id` is **the stream the
event belongs to, not the actor's tenant** — a platform admin provisioning tenant X writes into
X's stream so the event appears in X's history; NULL means provider plane. The actor is the
polymorphic pair `actor_type` (`membership | platform_admin | system`) + `actor_id` (NULL exactly
when `system`), because one foreign key cannot point at `tenant_memberships`, `platform_admins`,
and nothing at once. Neither `tenant_id` nor `actor_id` carries an FK, deliberately: every FK
action (`CASCADE`, `SET NULL`, `RESTRICT`) is an `UPDATE` or `DELETE` the append-only trigger
refuses, and the record of a tenant teardown is precisely the record that must outlive the
tenant. The table carries `occurred_at` alone — the append-only exception to
`created_at`/`updated_at`. All four ER deviations approved in
`openspec/changes/week1-review-decisions.md`, item 1.

**Compliance.** `readiness_snapshots` is append-only and written on a schedule. Live readiness is
computed from the maps; history comes from snapshots, because mappings and evidence mutate in place
and past values could not otherwise be reconstructed.

**Evidence.** The database stores metadata plus an integrity hash; the file lives in object storage
under `file_ref`. `valid_until` is computed at capture from the evidence type; staleness is derived
and cached by a scheduled job. Connector-written evidence uses the same table with
`kind = connector_result` — automated and manual evidence are one concept, one renewal queue, one
approval path.

**Tasks.** `task_transitions` is append-only and is the immutable history. Jira loose coupling rides
`task_source` + `external_id`.

**Documents.** Published versions are immutable rows; editing creates the next version. Acknowledgement
campaigns target a **version**, not the document. Group membership is snapshot at campaign launch, so
later joiners fall into the next campaign rather than appearing retroactively overdue.

**Risk.** A risk with no linked control is found by querying the map, never by a stored flag, so the
warning cannot go stale. `risk_source` + `origin_id` exist now so Phase 3 ERM extends this table
instead of replacing it.

**Vendors.** Vendor is the organisation; engagement is one use of it. Inherent and residual risk are
separate fields with different jobs: inherent is scored before review and drives rigor; residual is
the output of the completed review. Gates (`is_gate`) require an approval record to exit and are
never skipped, regardless of tier. `next_reassessment_on` is computed from the cadence schedule, not
from completion dates, so reviews cannot drift later each cycle.

**Assets.** Non-destructive merge: `source_asset_records` preserves every source's raw view,
correlation matches on stable identifiers in strict order (cloud instance id, agent id, serial, MAC,
then hostname) and **deliberately distrusts IP addresses**. `asset_merge_log` makes merges
debuggable and splittable. Ownership on the asset is what vulnerability instances, policy
violations, and drift alerts inherit.

**Vulnerabilities.** Definition holds enrichment once; instances are the unit of work, unique on
asset + definition + locator. State is explicit and stored. `fixed` is scanner-verified or formally
approved, never asserted. A reappearing definition flips the old instance to `resurfaced`.

**Connectors and checks.** Checks are global content mapped to the stable control template identity.
`error` is a first-class state, never conflated with `fail`. `check_results` is the one high-volume
table: append-only, partitioned by month from day one. Findings are opened per failing check +
connection + resource, so a check failing on three buckets raises three findings.

## Conventions

`id` is UUIDv7. `created_at` / `updated_at` on every table — append-only tables are the
documented exception and carry their event timestamp (`occurred_at`) alone. Status fields are
text with CHECK constraints, never enums. `tenant_id` leads every composite index. Full detail in
[../conventions/database.md](../conventions/database.md).

## Scheduled jobs the model depends on

Evidence staleness refresh; readiness snapshot writer; acceptance and waiver expiry; vulnerability
SLA sweep; vendor reassessment queue; scheduled checks and connector syncs; acknowledgement
reminders; vendor monitoring; asset hygiene; vulnerability enrichment (daily EPSS/KEV refresh,
score recomputation, resurfacing check).

Each is idempotent and safe to re-run.

## Open items from the ER document

- Object storage target for evidence files, and any data residency constraints.
- Retention period (model defaults to audit period + 1 year, with legal hold).
- Tenant registration field set.
- **The credentials table stays** (Phase 1 uses native auth); the customer's external Keycloak-based
  IdP federates in later — see [ADR-0006](../adr/0006-keycloak-as-identity-provider.md). Resolved.
