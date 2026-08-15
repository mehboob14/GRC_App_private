# Week 2 decisions — proposed, not yet approved

Week 2 is the compliance core: the framework engine, the SOC 2 control library, and engagement
setup. Ten questions have to be settled before the schema is written, because every one of them
is cheap now and a migration plus a data repair later.

**Nothing in this file has been confirmed by the client.** Every item below is marked
**PROPOSED — awaiting client confirmation** and is the reading I took, not an agreement I have.
Where a decision is genuinely the client's to make — the object storage target, the Type/Sub-type
vocabulary — the proposal is a seam that keeps building possible without pre-empting the answer.
This is the opposite of `week1-review-decisions.md`, which records answers already given; this
file records the questions and what I intend to do if no answer arrives before Stage 2 starts.

Drafted 2026-08-15. Confirming or overriding any item is a reply naming the item number. When an
item is confirmed, its status line changes to APPROVED and the date is recorded, in place.

---

## D1 — Type and Sub-type vocabulary for controls

**Status: PROPOSED — awaiting client confirmation.**

**Question.** The signed requirements say every control carries a Type and a Sub-type column, "for
example HR, Cloud, Development, CI/CD, Endpoint Devices, Security Tooling and XDR". What are the
permitted values of each, and where do they come from for the 114 prebuilt controls?

**The fact that forces the question.** The 114-control library we are seeding from
(`grc-s/backend/app/control_library.json`) carries `key`, `name`, `category`, `importance`,
`description`, and `mappings`. It carries **neither a type nor a sub-type field on any of the 114
rows**. There is no client-supplied taxonomy for either column anywhere in the requirements
document, the ER design, or the framework-engine deep-dive. The seven examples in the requirements
sentence are illustrative and are not a list; they also mix what look like two different axes (HR
and Development are organisational domains; Endpoint Devices and Security Tooling and XDR are
technology domains).

**Decision proposed.** Derive **Type** from the 11 categories the library already carries, which
are populated on all 114 rows and are internally consistent:

| Type (from category) | Templates |
|---|---:|
| Governance, Risk & Compliance | 22 |
| Data Management & Privacy | 17 |
| Identity & Access Management | 12 |
| Secure Development & Code Management | 12 |
| Infrastructure & Network Security | 11 |
| Logging, Monitoring & Incident Management | 11 |
| Human Resources & Personnel Security | 8 |
| Business Continuity & Third-Party Management | 8 |
| Endpoint Security | 6 |
| Communications & Collaboration Security | 5 |
| Physical & Environmental Security | 2 |

Leave **Sub-type** nullable and **blank on all 114 rows** until the client supplies a vocabulary.
The column exists, the filter exists, the API accepts and returns it, and a custom control can set
it. It is simply empty on shipped content rather than guessed at.

Both columns are **plain `text` with a `CHECK` constraint listing the permitted values**, not
Postgres enums and not a lookup table. A client-supplied vocabulary is then a one-line `ALTER
TABLE ... DROP CONSTRAINT / ADD CONSTRAINT` plus an `UPDATE` of the 114 seeded rows — not a schema
redesign, not a data migration across foreign keys.

**Rationale.** Three of the client's seven examples map cleanly onto categories we already have
(HR → Human Resources & Personnel Security, Endpoint Devices → Endpoint Security,
Development/CI-CD → Secure Development & Code Management), which is evidence the category axis is
the Type axis and the remaining examples are the Sub-type axis. But it is evidence, not
confirmation, and inventing 114 sub-type values to fill a screen would put fabricated compliance
metadata in front of an auditor. A blank column that filters correctly is honest; a guessed one is
a defect that looks like a feature. Deriving Type from a field that is already populated and
already curated means the library ships filterable on day one with zero invented data.

**What the client needs to tell us.** Either (a) confirm Type = the 11 categories and supply the
Sub-type list, or (b) supply both lists, in which case the 114 rows are re-tagged by `UPDATE`.

---

## D2 — The readiness formula

**Status: PROPOSED — awaiting client confirmation.**

**Question.** What exactly is a readiness percentage? The requirements promise "a readiness
percentage, overall and per criterion, tracked over time" and never define it. Every stakeholder
who reads a number assumes a definition, and an auditor-facing number that cannot be defended is
worse than no number.

**Decision proposed.** Per requirement, the score is:

- **1.0** when at least one mapped control is implemented **and** has current (non-stale) evidence
- **0.5** when exactly one of those two holds — implemented but unevidenced, or evidenced but not
  yet implemented
- **0.0** otherwise

Three boundary rules, each of which is the part people get wrong:

1. **A requirement with no mapped control scores 0.0 and stays in the denominator.** Excluding it
   would flatter the score by ignoring exactly the gaps the product exists to find. This matches
   the framework-engine deep-dive, which says unaddressed requirements count as zero rather than
   being excluded.
2. **A disabled control is excluded from the numerator, but the requirement it covered stays in
   the denominator** and drops to whatever its remaining controls justify. The coverage view says
   *why* — "was covered by disabled control X" — because the mapping row persists after the
   control is disabled.
3. Framework readiness is the **mean of the per-requirement scores over the requirements in scope
   for the engagement**, never a mean over controls. Averaging over controls over-weights a
   widely-mapped control; averaging over requirements is what the auditor is actually asking.

**It lives in exactly one pure function** — `verity.modules.compliance.readiness.score()` — taking
plain data and returning plain numbers, with no session, no HTTP, and no I/O. Every caller (the
live coverage view, the snapshot writer, the PDF export, the dashboard) goes through it. The
definition cannot drift between the dashboard and the report, because there is only one of it, and
it is unit-testable without a database.

**Interaction with D7.** D7 adopts `coverage` and `weight` on the crosswalk. The general form is
`min(1, Σ weight × control_score)` per requirement, where `control_score` is the 1.0 / 0.5 / 0.0
above. Because every seeded mapping ships as `coverage='full', weight=1.000`, this reduces
**exactly** to the rule stated above for every tenant on day one. The weighted form only starts to
differ when someone records a partial mapping, which is the behaviour we want and the reason the
columns land in Week 2 even though the formula runs in Week 3.

**Rationale.** Three states rather than a continuous score because a compliance number people
argue about is a number people stop trusting; 1.0 / 0.5 / 0.0 is defensible in a sentence.
Note that this decision is **implemented in Week 3, not Week 2** — evidence does not exist yet.
It is settled now because the Week 2 schema has to carry the columns the formula reads, and
retrofitting `weight` onto a crosswalk that already has rows in production is the expensive
version of this conversation.

---

## D3 — Evidence object storage

**Status: PROPOSED — awaiting client confirmation. Genuinely open; carried from Week 1.**

**Question.** Where do evidence files live? `docs/architecture/data-model.md` lists this under
"Open items from the ER document" as "object storage target for evidence files, and any data
residency constraints" and it is still open. S3, Azure Blob, or self-hosted MinIO? And is there a
jurisdiction the bytes may not leave?

**Decision proposed for now.** Build behind a **driver seam** — one small interface with
`put`, `get`, `signed_url`, `delete` — and ship a **local filesystem driver** as the only
implementation. The production target becomes a config change plus one driver file, and no
application code, no schema, and no API contract moves. The database already stores only
`file_ref` and a content hash, per `docs/conventions/database.md`, so the seam is naturally thin.

This is deliberately **not** a plugin framework, a registry, or an abstraction over three vendor
SDKs written before we know which one is used. It is one interface with one implementation because
we know a second one is coming and do not yet know which.

**Also to confirm, and defaulted if no answer arrives:**

| Parameter | Proposed default | Why |
|---|---|---|
| Maximum upload size | **25 MB** | Covers policy PDFs, screenshots, exported CSVs. Larger belongs in a document store, not an evidence record. |
| Signed URL TTL | **15 minutes** | Long enough for a slow download, short enough that a leaked URL is dead before it is useful. |
| Allowed types | **pdf, png, jpg, gif, csv, xlsx, docx, txt, json** | Allow-list, not deny-list. Validated on the sniffed content type, not the filename extension. |
| Antivirus scanning | **None in Phase 1** | Named as absent rather than assumed present. Adding ClamAV or a hosted scanner is a Phase 2 line item and a real dependency. |

**Rationale.** The residency answer can change the hosting decision, not the code, so blocking
Weeks 3-4 on it costs weeks and buys nothing. The four parameters are defaulted rather than left
open because a limit nobody set is a limit nobody can enforce, and "no AV scanning" stated in
writing is materially different from "we forgot".

---

## D4 — Engagement cardinality

**Status: PROPOSED — awaiting client confirmation.**

**Question.** May a tenant have more than one engagement at a time? The requirements describe "the
audit engagement" in the singular but never say whether a second one is legal.

**Decision proposed.** **Exactly one active engagement per tenant**, enforced by a partial unique
index:

```sql
CREATE UNIQUE INDEX uq_engagements__tenant_active
  ON engagements (tenant_id) WHERE status = 'active';
```

Drafts and closed engagements are unconstrained, so a tenant can prepare next year's engagement
while this year's is running, and can keep the full history.

**Rationale.** Direction of travel matters more than the answer. Relaxing this later is
`DROP INDEX` and a UI change. Adding it later — once readiness snapshots exist and every snapshot
row has to be attributed to one of several concurrent engagements, with a defensible rule for
which one the dashboard number came from — is a data repair on an append-only table, which is the
one repair this architecture makes deliberately hard. Take the constraint now; it is free to
remove and expensive to introduce.

**Two consequences to note.** `role_assignments.engagement_id` was created in Week 1 as a bare
nullable uuid with **no foreign key**, precisely because `engagements` did not exist yet
(`add-identity-and-access/design.md`). Week 2 is when that FK is added. And Week 1 review finding
#17 — `EngagementScope.allows(...)` treats its argument as an engagement id rather than the
object-under-access id the `ObjectScope` protocol defines — was deferred with the note "reconcile
the signature when the compliance module first uses it". This is that moment; it is a task in the
Week 2 change.

---

## D5 — The branded PDF export

**Status: PROPOSED — awaiting client confirmation.**

**Question.** The requirements promise "a readiness and gap-assessment report exported as a
branded PDF" in Week 3. How is it produced?

**Decision proposed.** A **print-stylesheet route plus `window.print()`**. A dedicated
`/reports/readiness/print` route renders the report with an `@media print` stylesheet, and the
browser's own print-to-PDF produces the file.

**Rationale.** Zero new dependencies. The output is genuinely branded, because the Verity design
tokens, the tenant's logo, and the colour palette are already live on the frontend — a server-side
renderer would have to have all of that shipped to it a second time, and would drift from the
screens the moment either changed. The alternative — WeasyPrint, or headless Chromium under
Playwright — adds a heavyweight runtime dependency, a font-provisioning problem in the container,
and a second place where branding lives.

**The condition that would change this.** A server-side renderer becomes justified the moment the
report must be **emailed, or generated on a schedule** — because then no browser is present to do
the printing. If the client wants a monthly readiness report in their inbox, this decision flips
and the dependency is worth it. That is a scope question, not a technical one, and it is the
question I need answered rather than the renderer choice.

---

## D6 — Frontend test framework

**Status: PROPOSED — awaiting client confirmation. Stated as a fact first, because it is one.**

**The fact.** **The frontend has no test framework.** Not a thin one — none.
`frontend/package.json` has no `vitest`, no `@testing-library/*`, no `jsdom`, and no `test`
script; `frontend/src` contains **zero** `*.test.*` or `*.spec.*` files. `make test` runs the
backend suite and nothing else. Every Week 1 quality claim rests on backend tests, type checking
(`tsc -b`), and lint. This is not a criticism of the Week 1 build — it is a fact that has to be
written down before Week 2 doubles the size of the frontend.

**Decision proposed.** Do not stand up vitest for Week 2. Instead, **keep every rule in the
backend**, so the untested layer is presentation only:

- state machines (control status, engagement status, disable/enable) — backend service + tests
- the readiness formula (D2) — one pure backend function + unit tests
- content hashing and integrity — backend
- evidence staleness boundaries — backend
- permission and object-scope resolution — backend, already tested
- the instantiation upsert (D7) — backend + isolation tests

The frontend then holds no logic whose failure is silent. A broken filter is visible in one click;
a wrong readiness formula is not visible at all, which is exactly why it lives where the tests are.

**Rationale, and the honest limit.** This is a containment strategy, not a substitute. It does not
cover a component that renders the right number in the wrong place, a form that silently drops a
field, or a route guard that stops guarding. **Revisit before the frontend surface grows further** —
concretely, before Week 5, when risk and vendor screens land and the frontend stops being mostly
tables. Standing up vitest plus testing-library is roughly half a day; the reason not to do it in
Week 2 is sequencing, not value.

---

## D7 — Framework-engine day-one hardening

**Status: PROPOSED — awaiting client confirmation. The highest-consequence item in this file.**

**Question.** The client commissioned a framework-engine design deep-dive
(`SOC2-Platform-Framework-Engine-DeepDive`) whose entire second half is a list of modelling
decisions to adopt **before implementation begins**. Do we adopt them in Week 2, or defer?

**The deep-dive's own verdict**, on the hardening below: it is "the difference between a second
framework that is an insert" and one that silently corrupts readiness. It also says that without
canonical control identity the platform "silently duplicates controls and readiness is wrong".
These are the client's own words about the client's own architecture, and they were written to be
read before the schema was cut. Week 2 is the last cheap moment.

**Decision proposed — adopt three, in the Week 2 migration:**

**(a) Canonical control identity.** `canonical_key` on both `controls` and `control_templates`,
with a partial `UNIQUE (tenant_id, canonical_key) WHERE canonical_key IS NOT NULL` on `controls`.
Instantiation becomes an **upsert on canonical key**, so enabling a second framework reuses the
tenant's existing control and adds requirement edges, instead of minting a near-identical twin
with its own owner, status, and split evidence. Custom controls may opt into a canonical key, which
is what stops a hand-built MFA control from being duplicated by the first ISO pack. On the 114
seeded templates `canonical_key` is simply the existing slug, so it costs nothing today and is
load-bearing the day a second content pack ships.

**(b) Framework versions and stable requirement keys.** `framework_versions (id, framework_id,
version, published_at)`, and a requirement identity that is **never re-minted**: one `requirements`
row per `(framework_id, code)`, carrying a natural key of the form `SOC2:CC6.1`, with which
versions contain it recorded in a join table. Engagements pin a `framework_version_id`, and
readiness always computes against the pinned version. A content update is then additive — a v1.1
that adds a requirement cannot grow the denominator of a tenant mid-audit on v1, and a typo fix
mutates the same row rather than orphaning every mapping that pointed at it. Without this, one bad
content deploy corrupts every tenant at once, because the join crosses into global content.

**(c) Coverage semantics on the crosswalk.** `coverage` (`full` | `partial`), `weight`,
`rationale`, and a review lifecycle (`review_status` of `suggested` | `accepted` | `rejected`,
with `reviewed_by_membership_id` and `reviewed_at`) on `control_requirement_map`. Without these, a
bare join means one weak mapping turns a requirement green, and an unreviewed auto-suggestion is
indistinguishable from an auditor-blessed one.

**(d) A fourth item, smaller, included for one reason.** `instantiated_content_hash` on `controls`
— a hash of the template fields at the moment of copying. Nothing in Week 2 reads it. It is
included because the deep-dive's own note is that provenance drift "that already happened is
unfixable retroactively": without it we can never afterwards distinguish a control a tenant
customised (leave alone) from a pristine copy (safe to refresh when template guidance improves).
One nullable column, written once by the instantiator. If the client would rather not carry it,
dropping it is free — but only before the first tenant is instantiated.

**A semantic choice inside (c) that needs the client's eye.** Mappings seeded from the shipped
crosswalk are proposed to be created as `review_status='accepted'` with `reviewed_by` **null** —
meaning "accepted as shipped platform content, not reviewed by a person here". The alternative
reading is that they seed as `suggested`, which would mean a brand-new tenant's readiness reads
0% until someone manually accepts 150 mappings. I took the first reading. It is exactly the kind of
compliance semantic that a guess should not silently decide, so it is called out rather than
buried.

**What is deliberately NOT adopted now:** monthly partitioning of `readiness_snapshots` and
`check_results` (Week 3 and Phase 2 respectively, when the tables exist), keying checks to
`canonical_key` (Phase 2, when connectors land), and `CONTROL_TEMPLATE_ORIGIN` as a multi-origin
join (a single `template_id` provenance column is sufficient until a second content pack exists;
`canonical_key` is what makes it upgradeable). Each is listed so a future reader knows it was
considered, not missed.

**Rationale.** (a) and (b) are the two the deep-dive calls load-bearing. Both are structural, both
are unpleasant to retrofit — (a) becomes a per-tenant manual merge of duplicated controls once
duplicates exist, (b) becomes a rebuild of every mapping — and neither costs meaningful time now.
(c) is three columns and a CHECK. Skipping any of them buys a few hours in Week 2 and sells a
data-corruption class of bug in Week 7.

---

## D8 — Person references: the ER diagram contradicts the rules

**Status: PROPOSED — awaiting client confirmation. Recorded as an explicit deviation.**

**Question.** The ER design diagrams show `owner_id` and `user_id` columns pointing at `users`.
`CLAUDE.md` rule 9 and ADR-0011 say every in-tenant reference to a person is a foreign key to
`tenant_memberships`, never to `users`. Which wins for `controls.owner`?

**Decision proposed.** **Follow the rule, not the diagram.** `controls.owner_membership_id` is a
foreign key to `tenant_memberships.id`. So is `disabled_by_membership_id`, and so is
`control_requirement_map.reviewed_by_membership_id`. No compliance table in Week 2 carries a
foreign key to `users`.

**Rationale.** A `user_id` on a tenant-owned table lets you assign a control to somebody who is not
a member of that tenant — the schema cannot stop it, and RLS cannot see it, because `users` has no
`tenant_id` to check against. This is the precise failure ADR-0011 was accepted to prevent, and it
is why the ER identity diagrams are already known to be stale: the same diagrams still show
`USERS.tenant_id`, "unique per tenant" email, and no `TENANT_MEMBERSHIPS` box at all, and
`week1-review-decisions.md` item 11 already approved deriving the identity schema from the prose
and the ADRs rather than from those diagrams. This is the same deviation, one module later.

**Recorded with citation, not silently.** The deviation is written into
`week2-compliance-engine/design.md` under "Schema status", the ER document correction is a task in
that change, and this item is the citation a future reader will find when they notice the diagram
and the migration disagree. `.docx` files are the signed originals and are not edited here.

---

## D9 — The Week 2 permission keys, listed once

**Status: PROPOSED — awaiting client confirmation.**

**Question.** What are the permission keys for the modules landing in Weeks 2-4, and who seeds
them? Week 1 established that `permissions` is global content seeded by migration
(`week1-review-decisions.md`, item 14), that Admin's grant is "every key that exists" resolved at
check time (item 13), and that other built-in roles receive their keys in the module change that
introduces them.

**Decision proposed.** These ten keys, and no others, for Weeks 2-4:

| Key | Introduced by |
|---|---|
| `frameworks:read` | Week 2 — compliance |
| `controls:read` | Week 2 — compliance |
| `controls:manage` | Week 2 — compliance |
| `engagements:read` | Week 2 — compliance |
| `engagements:manage` | Week 2 — compliance |
| `evidence:read` | Week 3 — evidence |
| `evidence:manage` | Week 3 — evidence |
| `tasks:read` | Week 4 — tasks |
| `tasks:manage` | Week 4 — tasks |
| `readiness:read` | Week 3 — compliance (readiness) |

Each key is seeded by **the migration that creates its module's first table**, as
`INSERT ... ON CONFLICT (key) DO NOTHING`. Week 2's migration therefore seeds the first five and
touches none of the others.

**Rationale.** Listing all ten now — a week before half of them are needed — is the point. Seeding
is spread across three migrations written in three different weeks, and the failure mode is that
Week 3 invents `evidence:upload` while Week 2's role seeder granted `evidence:manage`, leaving a
role that silently authorises nothing. One list, agreed once, and every later migration checks
against it. `ON CONFLICT DO NOTHING` makes re-running any migration safe and makes the order of
seeding irrelevant.

**Note on the split.** `read` / `manage` rather than
`read`/`create`/`edit`/`delete`. The finer split has no consumer — there is no role in the
requirements that may create a control but not edit one — and unused permission keys are a
liability, because every one is a check somebody eventually gets wrong. Object-level scoping
(control owner sees assigned controls) is service-layer filtering on top of the flat check, exactly
as `backend/CLAUDE.md` requires, and is **not** expressed as extra keys.

---

## D10 — Global content versus tenant-owned tables

**Status: PROPOSED — awaiting client confirmation.**

**Question.** Which Week 2 tables carry `tenant_id` and RLS, and which are global content? Getting
this wrong in either direction is severe: RLS naively applied to global tables makes every tenant's
compliance read empty, and a tenant-writable global table is a cross-tenant content leak.

**Decision proposed.**

**Global content — no `tenant_id`, no RLS, `GRANT SELECT` only to the application role:**
`frameworks`, `framework_versions`, `requirements`, `framework_version_requirements`,
`control_templates`, `template_requirement_map`.

These are written **only** by the content loader running as the **migration (owner) role** — the
same role that owns the schema and is already separate from `verity_app` by configuration
(`DATABASE_MIGRATION_URL` must differ from `DATABASE_URL`). The application role gets `SELECT` and
nothing else, so `grant_crud()` is deliberately **not** called on these tables. A tenant cannot
author a framework or a requirement even if a service tried to: the grant is not there.

**Tenant-owned — `tenant_id`, RLS enabled and forced, policy in the same migration, `tenant_id`
leading every composite index:** `controls`, `control_requirement_map`, `engagements`,
`engagement_frameworks`, `engagement_scope_categories`, and — when they arrive in Weeks 3-4 —
`evidence`, `evidence_control_map`, `readiness_snapshots`, `tasks`.

**Two specifics that are easy to get wrong and are therefore written down.**

`control_requirement_map` carries **its own `tenant_id`**, denormalised from `controls`. It is
reachable only through a control, so in principle the parent's policy would do — but the
deep-dive names the exact query that breaks without it: a coverage-gap `NOT EXISTS` written
against the map without joining through `controls` leaks the fact that "some tenant somewhere
mapped this requirement". A direct policy on the map closes that by construction rather than by
remembering to write the join. The same reasoning as `group_members` in Week 1.

Because Layer A has no `tenant_id`, **every readiness join crosses the RLS boundary** — a
tenant-scoped `controls` joined to an unscoped `requirements`. That is intended and it is the whole
reason multi-framework is cheap. The two hazards to test for are (i) a write path that treats a
global table as tenant-writable, and (ii) a rollup that returns another tenant's map rows. Both get
an explicit isolation test in the Week 2 change.

**Rationale.** This is a restatement of `CLAUDE.md` rule 2 and the ER's own Section 6, made
concrete for the eleven tables Week 2 creates, so that no one has to re-derive it per table at
2 a.m. under a migration deadline.

---

## What is still genuinely open, and blocks nothing

Listed so it is visible that these are unanswered rather than forgotten:

1. **D1** — the Sub-type vocabulary. Blocks nothing; the column ships empty and filterable.
2. **D3** — the object storage target and any data-residency constraint. Blocks nothing until
   deployment; the driver seam absorbs the answer.
3. **D5** — whether the readiness report must be emailed or scheduled. Blocks nothing in Week 2;
   changes the Week 3 renderer choice if the answer is yes.
4. **D7's review-status seeding semantics** — shipped mappings as `accepted` or as `suggested`.
   Blocks nothing; changes one literal in the instantiator, and changes what a brand-new tenant's
   first dashboard reads.

Everything else above is a decision I will build to unless told otherwise.
