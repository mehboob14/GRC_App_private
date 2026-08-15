# Compliance engine: frameworks, the control library, and engagements

## Why

Week 1 built somewhere for people to live. This change is the first thing they do there.

It is the compliance core: the framework engine that makes "collect evidence once, satisfy many
frameworks" true, the SOC 2 content pack, the tenant's own instantiated control library, and the
engagement that says which audit we are preparing for. Every module after it — evidence, readiness,
tasks, risk, vendors, the whole linkage fabric — attaches to a `controls` row. Controls are the hub;
this change builds the hub.

It is also the change that makes the client's own framework-engine deep-dive real (that document
lives in a different repository — see "Provenance" below). That document
was commissioned to be read *before* the schema was cut, and its conclusion is a short list of
day-one modelling decisions that separate adding a second framework by content-pack `INSERT` from
adding one and silently corrupting readiness. Three of those are adopted here — canonical control
identity, versioned content with stable requirement keys, and a weighted, reviewed crosswalk — and
`openspec/changes/week2-decisions.md` D7 records why. Adopting them after a tenant is instantiated
is a per-tenant data repair; adopting them now is three columns and an index.

Week 1 left an explicit hook for this change. `tenant_provisioning`'s `seed_content` step
"completes as an honest no-op (0 templates instantiated — the global content library does not exist
yet). Does real work when the library lands" (`week1-review-decisions.md`, item 10). This is when
it starts doing real work.

This change belongs to **Phase 1, deliverable 1.1 — Foundation**, and is Week 2 of the signed
eight-week build plan. `docs/product/delivery-plan.md` puts the "SOC 2 control library with Type
and Sub-type" in 1.1 alongside multi-tenancy, RBAC, and the audit trail; 1.2 is documents and
policies, the risk register, and vendor risk, none of which are in this change. It depends on
`add-backend-foundation`, `add-audit-trail`, `add-provider-plane`, and `add-identity-and-access`,
all of which cite 1.1 the same way.

## What changes

- **Migration — global content (no `tenant_id`, no RLS, `GRANT SELECT` only):** `frameworks`,
  `framework_versions`, `requirements`, `framework_version_requirements`, `control_templates`,
  `template_requirement_map`.
- **Migration — tenant plane (RLS enabled and forced, policy in the same migration):** `controls`,
  `control_requirement_map`, `engagements`, `engagement_frameworks`,
  `engagement_scope_categories`. Every parent/child reference between two of these is a
  **composite** foreign key on `(tenant_id, <parent>_id)`, because Postgres FK checks bypass row
  security. Plus the deferred foreign key from `role_assignments (tenant_id, engagement_id)` to
  `engagements (tenant_id, id)`, which Week 1 could not add because `engagements` did not exist.
- **SOC 2 content pack**, loaded by the migration as the owner role: 1 framework, 1 framework
  version, **61 requirements** across 13 categories (33 of them common criteria, always in scope),
  **114 control templates** across 11 categories, and **150 template→requirement crosswalk rows**.
  Every requirement is covered by at least one template; the seed asserts it.
- `backend/src/verity/modules/compliance/` — the vertical slice (router, schemas, models, service,
  repository, exceptions), following `modules/iam/` as the reference shape.
- **Library instantiation**: an idempotent upsert on `(tenant_id, canonical_key)` that materialises
  the template library into tenant controls and projects the shipped crosswalk into the tenant's
  own. Wired into `tenant_provisioning`'s `seed_content` step for new tenants and exposed as an
  explicit "enable framework" service call for existing ones.
- **Controls**: Type and Sub-type (D1), owner as a membership FK (D8), status, implementation
  guidance, and mapped criteria. Add a custom control, edit any control, edit its crosswalk, and
  disable one with a recorded justification. No delete route exists.
- **Engagements**: audit type (Type I / Type II), observation window, pinned framework version, and
  Trust Services categories in scope — with Security's common criteria always in scope and not
  deselectable.
- **Coverage view**: every in-scope requirement with no accepted mapped control (see Non-goals for
  the half of this that Week 3 completes).
- **Permission keys** `frameworks:read`, `controls:read`, `controls:manage`, `engagements:read`,
  `engagements:manage`, seeded by this migration (D9). Built-in Compliance Manager and Control
  Owner roles receive their Week 2 keys here.
- **One object scope**: `ControlOwnerScope`, filtering on `controls.owner_membership_id` — the
  concrete scope `add-identity-and-access/design.md` said would land with this module. Week 1
  finding #17 (`EngagementScope.allows` signature) is reconciled in the same task.
- **Frontend** `frontend/src/features/compliance/`: control library list with Type and Sub-type
  filters, control detail, engagement setup, coverage view.
- **Isolation tests** covering two tenants across every new tenant-owned table, plus the two
  global-content hazards the deep-dive names.

## Non-goals

- **No evidence.** No `evidence` table, no uploads, no object storage, no `evidence_control_map`.
  That is Week 3, and D3 settles the storage seam before it starts.
- **No readiness.** No `readiness_snapshots`, no snapshot writer, no percentage anywhere in the UI,
  no PDF export. Week 3. The readiness formula is *decided* in `week2-decisions.md` D2 and the
  columns it reads are created here, but nothing computes it in this change.
- **No tasks, no documents, no risk, no vendors, no assets, no vulnerabilities, no connectors,
  no checks, no AI.** Weeks 4-7 and Phase 2.
- **The "control with no evidence" half of the coverage view is deferred to Week 3.** The signed
  Week 2 scope names both halves of the coverage view; the second half is an anti-join against a
  table that does not exist until Week 3. This change ships the requirement-side gap
  ("in-scope criterion with no mapped control") in full, and the control-side gap becomes one
  additional anti-join in the Week 3 change. This is flagged, not quietly dropped.
- **No second framework.** ISO 27001, GDPR, and HIPAA content packs are Phase 3. The point of this
  change is that adding them is an `INSERT` — and the isolation tests prove the reuse path works by
  instantiating a synthetic second framework in a fixture, not by shipping real ISO content.
- **No template refresh.** `instantiated_content_hash` is written and never read in this change
  (D7d). Propagating improved template guidance to pristine tenant copies is a later feature; the
  provenance it needs is recorded now because it cannot be reconstructed later.
- **No frontend test framework.** See `week2-decisions.md` D6 — the frontend has none today, and
  every rule in this change lives in the backend so the untested layer is presentation only.

## Modules touched

`compliance` (new). Consumes `iam` (`require(permission)`, membership lookups for owner
validation), `tenancy` (the provisioning service, for the `seed_content` step), and `audit`
(`AuditService`) — all through their service interfaces only, never their repositories.

It **modifies one table owned by another module**: `role_assignments.engagement_id` gains its
foreign key. This is a deliberate cross-module migration, flagged here because it is exactly the
kind of thing that should not happen quietly. The column, its nullability, and its purpose were all
defined in `add-identity-and-access`; only the constraint that could not exist yet is added.

## Closest-review flags

**This change touches tenant isolation and authorization. It does not touch authentication, and it
creates no append-only table.**

- It is the first change where a **tenant-scoped query joins to unscoped global content**. That
  join is the mechanism the whole multi-framework design rests on, and it is also the one shape
  where a mistake reads as "everyone's compliance is empty" or "one tenant's mapping is visible to
  another". Both directions get an isolation test.
- It creates the first table whose RLS policy protects a **join table with no direct business
  meaning** (`control_requirement_map`). It carries its own `tenant_id` for the reason recorded in
  D10, not by copy-paste.
- It is the first change to use **object-scoped authorization in anger** (`ControlOwnerScope`).
  Week 1 exercised the hook only in unit tests. Scope denial must be 404, not 403.
- It adds a **foreign key to another module's table**.
- It ships **content**: 114 templates and 150 mappings that end up in front of an auditor. A wrong
  crosswalk row is a compliance defect that no test catches, so the seed is asserted for
  completeness (every requirement covered) and checked against the source library by count.

## Schema status — derived from the ER prose and the deep-dive, for approval

The ER document's Section 3.2 describes this module in prose and gives the relationships, but the
Week 2 column lists are **derived**, from three sources in priority order: the ER prose, the
framework-engine deep-dive's hardening section, and `docs/conventions/database.md`. Every derived
column is marked in `design.md`.

Two deviations are recorded explicitly rather than absorbed:

1. **Person references follow `CLAUDE.md` rule 9, not the ER diagram.** The diagrams show
   `owner_id` against `users`; `controls.owner_membership_id` is a foreign key to
   `tenant_memberships.id`. Full reasoning and citation in `week2-decisions.md` D8.
2. **Engagement scope is a join table, not `jsonb`.** The ER models `categories_in_scope` as free
   `jsonb`; the deep-dive identifies that as a referential-integrity gap where a renamed or
   mistyped category silently changes the readiness denominator. A three-column join table is less
   code than validating the `jsonb` would be.

`week2-decisions.md` D1 through D10 are **proposed and not yet confirmed by the client**. This
change is written against those proposals. If any is overridden, the affected section of
`design.md` changes before implementation starts, not after.

## Provenance — the sources these documents cite live in a different repository

Three of the sources this change rests on are **not in this repository** and do not resolve for a
reader of it. They live in the earlier prototype repo at
`C:/Users/HP/OneDrive/Desktop/Platform/grc-s`:

| Cited as | Actual location | Used for |
|---|---|---|
| `control_library.json` | `grc-s/backend/app/control_library.json` | the 114 control templates and the 150 crosswalk rows |
| `soc2_controls.json` | `grc-s/backend/data/soc2_controls.json` | the 61 requirements across 13 categories |
| `SOC2-Platform-Framework-Engine-DeepDive` | `grc-s/docs/SOC2-Platform-Framework-Engine-DeepDive.docx` | the hardening D7 adopts, and the risks it names |

The deep-dive is a client document under its own change control and stays where it is; it is cited
here by its external path so a reader can find it rather than assume it is missing. The two JSON
files are **build inputs** and must not stay external: a seed that reads from a path outside the
repository is not reproducible, and the content is what an auditor eventually reads. Task 1.0
vendors them in with a recorded `sha256` before any loader is written.
