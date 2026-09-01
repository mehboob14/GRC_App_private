# Asset management — build plan

Week 6 / Deliverable 1.3. This plan covers the **assets** module; **vulnerabilities** follows
immediately after as its own module (Deliverable 1.3 bundles the two, and the vuln coupling needs
both). Reference implementation to copy: the **tasks** module (freshest full vertical slice), with
**documents** as the frontend reference and **controls** as the backend reference.

## Decisions (locked with the client)

- **Scope:** build assets fully now; design the schema so **vulnerabilities** drops in next.
  Risk follows later — the `links` table already lets a vuln point at a risk before the risk module
  is rich, so the 4-hop trace (vuln → asset → risk → control → policy) completes once vulns + a
  minimal risk register exist.
- **Phase-1 depth:** core first (register, criticality, lifecycle, hygiene, CSV import, 360
  linkage). Dependency graph, asset groups, and inventory-review attestation land as a follow-on
  stage (A8 / B6), not the first slice.

## Sources

- **Requirements, Deliverable 1.3** — the manual asset field set, criticality, lifecycle, hygiene,
  and the 360-degree linkage.
- **ER §3.8** — the product-grade target (unified deduplicated record, dependency graph, software
  inventory, saved-query policy engine, inventory attestation). Most is connector-driven = Phase 2/3.
- **delivery-plan.md** — *"Build the phase you are in. Design the schema for all three."* The
  `assets` table must carry what connectors need later; the connector-only tables are added in P2.

## What already exists to build on

- `links` primitive — polymorphic over `asset`/`risk`/`vulnerability`/`control`/`evidence`/
  `document`/`vendor`. The 360 linkage rides this; **no per-target columns, no new join tables.**
- `notifications` — stale-asset / hygiene / decommission alerts (`notify` + outbox).
- `audit`, RLS (rule 1/2), `Integratable` (rule 9), deny-by-default permissions (rule 7), the
  metadata-driven RLS-coverage test (auto-covers new tenant tables).
- **Not yet built (stubs):** `risk`, `vendors`, `vulnerabilities`. Assets links to
  controls/documents/evidence today; risk/vuln targets arrive with their modules.

---

## Phase-1 data model (build now)

All tenant-owned (rule 1: `tenant_id` first in every composite index, RLS + FORCE + policy in the
same migration). Person references are FK `tenant_memberships` (rule 3); the owning team is a group.
`assets` is `Integratable` and carries correlation keys so Phase-2 connectors do not force a change.

- **`assets`**
  - identity: `name`, `description`, `asset_type` (application | infrastructure | data | cloud |
    third_party | business_service), `hostname`, `ip_address`, `location`, `vendor_ref`
    (nullable text/link until the vendors module exists)
  - correlation keys (carried now, populated by connectors in P2 — their presence is what lets the
    P2 dedup resolver merge without a schema change): `fqdn`, `primary_mac`, `serial_number`,
    `cloud_resource_id`, `os_normalized` (e.g. `windows-11-23H2` — also the P3 CIS-benchmark key),
    `environment` (prod | staging | dev | test | dr)
  - classification: `data_classification`, `regulated_data_type`, `compliance_scope`
  - exposure: `internet_facing`, `customer_facing`, `network_segment`, `business_function`
  - business context: `valuation`, `business_impact_notes`, `operational_dependency_rating`
  - ownership chain (FK memberships): `primary_owner`, `secondary_owner`, `business_owner`,
    `custodian`, `escalation_contact`; `owning_team_group_id` (FK group)
  - criticality: `confidentiality`, `integrity`, `availability` (1–5, **nullable, no default**),
    computed+stored `criticality_score` (nullable), derived `tier`, separate `tier_override`
    (+ reason)
  - lifecycle: `status` (planned | active | in_maintenance | decommissioned | retired),
    per-transition timestamps, `replaced_by_asset_id` (self-FK)
  - freshness: `first_seen_at`, `last_seen_at`, `last_reviewed_at`
  - integration: `source`, `external_id`, `synced_at`, unique `(tenant_id, source, external_id)`
  - CHECKs: valid enums; `tier_override` requires a reason; decommission requires a replacement
- **`decommission_records`** — `disposal_method`, `media_sanitised`, disposal evidence ref, actor,
  timestamp (auditors test retirement followed policy).
- **`asset_transitions`** — append-only lifecycle history (like `task_transitions`), separate from
  and additional to `audit_log`.

### Follow-on Phase-1 stage (A8 / B6)

- **`asset_relationships`** — typed dependency graph (depends_on | runs_on | contains |
  connects_to | processes_data_for) with provenance; powers impact tracing + criticality
  inheritance for infrastructure under a business_service.
- **`asset_groups`** (+ membership: static or a saved rule) — segments the estate; scopes
  dashboards and ownership defaults.
- **`inventory_reviews`** — periodic attestation; owner signs off, export stored as evidence
  (ISO 27001 A.5.9 / SOC 2).

### Designed now, built in Phase 2/3 (they reference `assets`, so adding them later changes nothing here)

`source_asset_records`, `asset_merge_log`, `field_precedence_policies`, `asset_lifecycle_settings`
(freshness/staleness), `software_products` / `software_installations`, the general `asset_policies`
saved-query engine + `policy_violations`. **Phase 3:** CIS hardening benchmarks ride the checks
engine (results reference an asset), live scanner ingest, CMDB.

---

## Design decisions

- **No phantom defaults (adopted from the reference — a hard rule).** `criticality`,
  `criticality_score`, CIA ratings, and lifecycle carry **no default**. NULL means "not assessed"
  all the way through; the UI renders "— / assess", never a laundered "medium"/"active". The
  reference documented how a placeholder value silently propagates into risk scores, board-pack
  dollar figures, and CIA derivations for assets nobody rated. This shapes the schema (nullable, no
  server_default) and the UI.
- **Criticality (adopting the reference's ISO 27005 scorer).** CIA rated **1–5** each. `base =
  MAX(C, I, A)` mapped `{1:2, 2:4, 3:6, 4:8, 5:10}` — highest harm wins, not a sum; no CIA → base
  5.0. Boosts: `+2.5` internet_facing, `+1.5` restricted / `+1.0` confidential data_classification,
  `+1.5` high-impact business_function; clamp `[0, 10]` → `criticality_score`. Buckets: `≥8.5`
  Critical · `≥6.5` High · `≥4.0` Medium · else Low. `recompute` always writes the score but only
  writes the text `tier` when `tier_override` is unset, so the record always shows "system computed
  X, person published Y". A live preview endpoint returns `{score, bucket}` without persisting (for
  the A4 form). business_service assets carry criticality directly; infrastructure inherits via
  dependency edges (A8/B6). `business_function` becomes a structured catalogue (id/label/group/
  high_impact), not free text.
- **Lifecycle.** Enforced transitions (a state machine served to the client, like tasks).
  Decommission is a guarded action: requires a replacement + a `decommission_record`, and — once
  vulns exist — cascades to close the asset's open vuln instances.
- **Hygiene (Phase 1).** Computed directly: owner set, type set, criticality set, classification
  set, CIA rated; stale detection from `last_reviewed_at` / `last_seen_at`. The general saved-query
  policy engine (coverage gaps from multi-source data) waits for Phase 2.
- **Linkage.** Reuse `links`. *Divergence from the reference:* it used a separate explicit join
  table per pair (`AssetControlLink`, `AssetEvidenceLink`, `VulnerabilityAssetLink`, `RiskAssetLink`
  …); Verity's polymorphic `links` primitive replaces all of them — assets ↔ controls/documents/
  evidence now, risk/vulns as they land, one table, indexed both ways.

---

## Stages

### Phase A — frontend on mocks (UI/UX first)

- **A1** types + in-memory mock store + tokens (asset shapes, enums, criticality, lifecycle).
- **A2** asset register (reference UI to mirror): a KPI strip (Total · Critical · Need-CIA ·
  regulated/CDE · Stale>30d), faceted filters with counts (Type · Criticality · Status · Exposure ·
  Environment) via a `/facets`-style endpoint, search, saved views, and a `DataTable` whose columns
  are Asset (tile + inline vuln count) · Type · Owner (warn colour if unassigned) · Criticality
  pill · CIA meter (or "— assess") · Lifecycle dots · Last-seen (rose if stale) · Value ($ only if
  real) · Status. Bulk actions: set-criticality, delete. Unassessed fields render "—", never a
  fake value.
- **A3** asset detail: tabs — Overview · Criticality/CIA · Ownership · Lifecycle · Relationships ·
  Linked (risks/controls/docs/evidence/vulns) · Activity.
- **A4** new/edit form with a **live criticality preview** as CIA/exposure are set.
- **A5** CSV/Excel import: downloadable template → upload → validate/preview → commit. Template
  columns (from the reference, required = `name` + `asset_type`): `name, description, asset_type,
  host_name, ip_address, vendor, location, operating_system, confidentiality_rating,
  integrity_rating, availability_rating, data_classification, internet_facing, business_function,
  network_segment, compliance_scope` (comma-split), `owner_name, owning_team, valuation, status,
  criticality` (blank = auto-calc; a value = audited override), `criticality_override_reason`.
  Import recomputes criticality per row.
- **A6** lifecycle actions + decommission wizard (replacement + disposal record).
- **A7** asset dashboard: by tier/type, hygiene score, stale assets, lifecycle mix.
- **A8** *(follow-on)* dependency graph + asset groups + inventory-review attestation.

### Phase B — backend (one vertical slice at a time)

- **B1** models + migration: P1 tables, RLS+FORCE+policies, `Integratable`, append-only
  `asset_transitions`; seed permissions `assets:read` / `assets:manage` / `assets:import` /
  `assets:decommission`.
- **B2** service + repository: CRUD, criticality compute, hygiene compute, filters/pagination.
- **B3** router + schemas: deny-by-default routes, audit row on every state change.
- **B4** lifecycle + decommission logic: enforced transitions, decommission cascade hook (closes
  vulns once that module exists).
- **B5** CSV import backend: template, parse, validate, bulk upsert on `(source, external_id)`.
- **B6** *(follow-on)* relationships + groups + inventory reviews.
- **B7** 360-linkage wiring via `links` (asset ↔ controls/docs/evidence).

### Phase C — integrate + harden

Wire the frontend to the real API, delete mocks, verify against the live DB (RLS-coverage test
auto-covers the new tables), exercise import + decommission end to end.

---

## Vulnerabilities (next module) — outline

Three-level model from ER §3.9: **`vuln_definitions`** (CVE/finding, CVSS score+vector, CWE,
enrichment set [manual in P1, auto EPSS/KEV in P2], recommendation) → **`vuln_instances`** (one def
on one asset at one locator; unique (asset, def, locator); state machine new/active/in_progress/
pending_retest/fixed/resurfaced/accepted/false_positive; `risk_score` blends severity + exploit +
asset criticality + exposure; owner inherited from asset) → **`vuln_transitions`** (append-only).
Plus manual entry + report upload (Excel/CSV/PDF/XML, AI-assisted parse), per-severity SLA, and a
governed exception/risk-acceptance workflow with mandatory expiry. This is where asset criticality
pays off (prioritisation) and where decommission-closes-vulns lands.

**Composite priority (from the reference, for `vuln_instances`).** Seven weighted signals summing to
10: `CVSS 0.20 + EPSS 0.20 + exploit_maturity 0.15 + KEV 0.15 + attack_vector 0.10 +
internet_exposure 0.10 + asset_criticality 0.10`, with a **KEV floor of 8.0** (anything CISA
known-exploited never ranks below High) and `None` when every signal is missing (keeps the column
honest). Buckets: `≥9` Critical · `≥7` High · `≥4` Medium. Per-severity SLA defaults (days):
`{critical:7, high:30, medium:90, low:180, info:365}`. Enrichment fields (EPSS, KEV, public-exploit,
vendor-patch) are manual in P1 and auto-refreshed in P2.

## Resolved / open questions

- **Criticality formula — resolved:** adopt the reference's max-based ISO 27005 scorer (above).
- **CSV template — resolved:** adopt the reference's column set (stage A5).
- **No phantom defaults — resolved:** hard rule, NULL = not assessed end to end.
- **Open — two status columns?** The reference keeps `status` (operational: active/inactive/
  decommissioned) *and* `lifecycle_state` (human judgement) in parallel. Recommendation: Verity uses
  **one** `status` (the five-state lifecycle) to stay lean, unless a separate operational flag earns
  its keep. Confirm before B1.
- **Open — vendor link** while `vendors` is a stub: nullable free-text now, upgraded to a real link
  when vendors lands.
