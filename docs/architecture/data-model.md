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

**Tenancy.** Two planes. `platform_admins` and `tenants` carry no `tenant_id`; `tenant_branding`
(PK = `tenant_id`) and `tenant_provisioning` reference their tenant, and all of them are
RLS-protected — `tenants` on its own primary key (week1-review-decisions.md, items 6 and 9).
Platform-admin credentials live **on `platform_admins`** (`password_hash`,
`mfa_secret_encrypted` AAD-bound to the row, `recovery_codes_encrypted` as argon2id hashes,
`last_totp_counter` for replay protection) — approved deviation from the ER, item 5; the ER
document correction is pending (the .docx is the signed original). `tenants.created_by` is
nullable (self-signup has no admin, item 7); `tenant_provisioning` has no `failed` status — a
failing step stays `pending` and is retried (item 8). A **user is a global identity**
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
Two **approved derived columns** have no source in the ER prose and are design, not drift
(week1-review-decisions.md, item 11): `credentials.last_totp_counter` (TOTP replay protection —
a code at or before the stored counter is refused) and `user_identities.provider_type` (OIDC vs
SAML, required by ADR-0006). `permissions` is global content like frameworks: the Week 1
`module:action` keys are seeded by the migration that creates the table (item 14), and the
built-in Admin role's grant is "every key that exists", resolved at check time (item 13). The ER
document's identity diagrams still show the pre-ADR-0011 shape (`USERS.tenant_id`, no
`tenant_memberships`); regenerating them is **pending** — the .docx is the signed original and is
corrected under its own change control.

**Audit.** `audit_log` is append-only and serves both planes. `tenant_id` is **the stream the event
belongs to, not the actor's tenant** — a platform admin provisioning tenant X writes into X's stream
so the event appears in X's history; NULL means provider plane. The actor is the polymorphic pair
`actor_type` (`membership | platform_admin | system`) + `actor_id` (NULL exactly when `system`),
because one foreign key cannot point at `tenant_memberships`, `platform_admins`, and nothing at
once. Neither `tenant_id` nor `actor_id` carries an FK, deliberately: every FK action (`CASCADE`,
`SET NULL`, `RESTRICT`) is an `UPDATE` or `DELETE` the append-only trigger refuses, and the record
of a tenant teardown is precisely the record that must outlive the tenant. The table carries
`occurred_at` alone — the append-only exception to `created_at`/`updated_at`. All four ER deviations
approved in `openspec/changes/week1-review-decisions.md`, item 1. A **fifth** landed with the vendor
portal: `actor_type` gains `vendor_contact`, because that is the platform's first path on which a
state change is made by somebody who is neither a member nor the system — they hold a link, not a
session, and a `tenant_memberships` row for an outsider would break rule 3. The polymorphic pair was
built for exactly this, so it cost one CHECK; recording their answers as `system` would have made
"who answered this question" unanswerable. The ER correction is pending.

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

**Risk.** A risk with no linked control is found by querying `risk_control_map` against the active
controls, never by a stored flag, so the warning cannot go stale. **The matrix belongs to the
register, not the tenant**: `risk_registers` carries its own levels, labels, severity bands, category
taxonomy (`risk_categories`, two levels) and review cadence, so a workspace can run several registers
side by side. Scores are generated columns (likelihood × impact). `accepted` is only ever set by an
approved `risk_acceptances` row whose approver is not the requester (a CHECK); expiry or revocation
reopens the risk. `origin` + `origin_ref` + `template_id` record where a risk came from (library,
import, vendor finding) so Phase 3 ERM extends these tables instead of replacing them. Column lists
and every departure from the ER: `openspec/changes/week7-risk-register/design.md` §1.

**Vendors.** Vendor is the organisation; **an engagement is one use of it, and the engagement is the
unit of risk**. Stages, tiering runs, assessments and contracts all hang off an engagement, and
every vendor gets one implicit default engagement at creation so nothing has to special-case a null
one. `vendors.tier`, `current_residual_score`, `current_grade` and `annual_contract_value` are
**caches of the worst engagement**, kept so a portfolio of hundreds sorts without a join — derived,
never authoritative, and never the value an action is taken on. A vendor serving two departments
with different data is two risks, not one averaged one. Inherent and residual risk stay separate
fields with different jobs: inherent is scored before the review and decides how much review is
proportionate; residual is the output of the completed one. **The lifecycle is rows, not a status
column** — twelve stages in `vendor_stages` (intake, tiering, diligence, questionnaire, scoring,
findings, contracting, approval, onboarding, monitoring, reassessment, offboarding), unique on
`(tenant_id, engagement_id, cycle, stage)`, where `cycle` is a plain integer a reassessment
increments and the previous cycle's rows stay readable. **`approval` is the only gate.** `tiering`
is required and never skippable but is *not* a gate, because a gate is defined by needing an
approval record to exit — a distinction the tier's skip matrix depends on. A database `CHECK`
forbids `is_gate` and `status = 'skipped'` together, and a gate exits only on an approval with
`decided_at >= stage.entered_at`, so a send-back invalidates a stale approval without mutating the
append-only row. Exit criteria are **computed on read, never stored**: a stored blocker list goes
stale the moment the record that clears it changes. `next_reassessment_on` is computed from the
cadence schedule, not from completion dates, so reviews cannot drift later each cycle.
`vendor_transitions` and `vendor_approvals` are append-only and their actor FKs are `ON DELETE NO
ACTION`, because `SET NULL` issues an `UPDATE` that the append-only trigger refuses and the delete
then fails. Four tables — `vendor_scorecards`, `vendor_signals`, `vendor_discovered_apps`, and Slack
delivery on `vendor_alert_rules` — carry the rule-9 columns but have **no data source in any planned
phase**, so their screens say "no data source connected" rather than rendering an empty table: on a
monitoring surface, "watching and found nothing" and "not watching" look identical and mean opposite
things. `vendor_findings.promoted_risk_id` ships nullable with **no FK and no promotion action**
until `modules/risk/` exists. The tiering policy row is an **override, not a seed**: the shipped
defaults live in `vendors/scoring.py` and `vendors/lifecycle.py` and a tenant row merges over them
field by field, so a new tenant needs no provisioning step. What keeps a later retune from rewriting
history is `vendor_tiering_assessments.policy_snapshot`, which freezes the weights and thresholds
each run used. A stage's exit checks are **three-valued** — satisfied, blocking, or pending because
the module that answers them is not built yet; a pending check never blocks and never renders as a
tick, the same distinction rule 7 draws between `error` and `fail`.

Four things about the lifecycle rows read wrong from the schema alone. **Tiering writes all twelve
rows at once, every one of them `not_started`** — nothing enters `in_progress` until a stage is
advanced, so a freshly tiered engagement has no current stage by that column and "where the work
is" means *the first row that is neither complete nor skipped*. Keying off `in_progress` alone
hides the controls at the one moment somebody needs them. **A transition is addressed by
`stage_id`, never by engagement**: a reassessment increments `cycle` and writes a fresh twelve, so
an engagement holds several sets and only the row identifies which. **The gate's own exit check is
self-clearing** — `approval.decided` blocks the approval stage and is satisfied only by recording
the decision, so anything that treats the raw blocker list as a reason to withhold the decision
control deadlocks the gate permanently. And **exit checks are computed per stage on read**, which
means the same check code can be blocking on one engagement and pending on another in the same
response.

Twenty-eight tables: twenty-five tenant-owned, plus `questionnaire_templates`,
`questionnaire_questions` and **`vendor_portal_tokens`** on the global content plane with no
`tenant_id` and no RLS. The portal-token table is the surprising one, and it is deliberate: a
vendor contact arrives holding nothing but an opaque token, so the tenant has to be resolved
*before* any RLS binding can exist. Making the table global is the same shape `users` already uses
and keeps the resolution to one row lookup; the alternatives were rejected because widening the
provider plane would expose `audit_log` across tenants, and putting the tenant in the token
contradicts a stated design comment in `core/security.py`. It stores only a hash — the URL handed
out at issue time is the only copy of the token that will ever exist.

**Verbatim column lists for all of them, with every deviation
from the ER named, live in §1 of
[the vendor-risk change's design](../../openspec/changes/week5-vendor-risk/design.md)** — the
single build reference, from which migrations are written rather than from the ER diagram images.

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
connection + resource, so a check failing on three buckets raises three findings. Checks bind to
capabilities (version control, identity provider), never to one vendor; mappings from controls to
requirements carry a reviewed relationship and rationale. Tables and columns:
`openspec/changes/common-control-framework/design.md` (ADR-0014). Built: global
`integration_capabilities`, `checks`, `control_template_checks`; tenant `connections`,
`check_runs`, `check_results` (partitioned by month, pre-created to December 2028 plus a
default partition), `integration_requests`, `connection_resources`.

Each check lists the artifacts it collects (`checks.evidence_kinds`), each link from a check to
a control says how much of the control it verifies and why (`control_template_checks.coverage`,
`rationale`), and each control template lists the evidence a person or a Verity module provides
beyond its checks (`control_templates.evidence`: name, design or operating, cadence, upload or
platform module, and which checks collect the same thing). `control_templates.pack` names the
content pack that ships a template, so a second framework prunes only what it owns. The crosswalk
(`template_requirement_map`) carries `coverage` and a written `rationale` on every row.

`connection_resources` is the inventory a run discovers (repositories today) with the scope
decision beside each item: `scope` (`in_scope`, `excluded`), `decided_by` (`system`, re-derived on
every run, or `person`, sticky), and a mandatory `scope_reason` for an exclusion, by CHECK
constraint as well as in the service. It carries `source`, `external_id` and `synced_at` (rule 9),
so it is also the natural feed for the asset inventory. Only in-scope resources are read, and
every exclusion is printed on the evidence (AU-9).

## Conventions

`id` is UUIDv7. `created_at` / `updated_at` on every table — append-only tables are the
documented exception and carry their event timestamp (`occurred_at`) alone. Status fields are
text with CHECK constraints, never enums. `tenant_id` leads every composite index. Full detail in
[../conventions/database.md](../conventions/database.md).

## Scheduled jobs the model depends on

Evidence staleness refresh; readiness snapshot writer; acceptance and waiver expiry (risk
acceptances reopen their risk, `sweep_risk_register`, which also notifies overdue risk reviews); vulnerability
SLA sweep; vendor reassessment queue; vendor document expiry; vendor SLA breach sweep; scheduled
checks and connector syncs; acknowledgement reminders; vendor monitoring; asset hygiene;
vulnerability enrichment (daily EPSS/KEV refresh, score recomputation, resurfacing check).

Each is idempotent and safe to re-run.

## Open items from the ER document

- Object storage target for evidence files, and any data residency constraints.
- Retention period (model defaults to audit period + 1 year, with legal hold).
- Tenant registration field set.
- **The credentials table stays** (Phase 1 uses native auth); the customer's external Keycloak-based
  IdP federates in later — see [ADR-0006](../adr/0006-keycloak-as-identity-provider.md). Resolved.
