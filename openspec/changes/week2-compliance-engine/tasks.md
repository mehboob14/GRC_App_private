# Tasks — compliance engine

Each task is at most two hours. Every migration that adds a tenant-owned table enables RLS and adds
its policy in the same migration. The isolation tests ship in this change.

`week2-decisions.md` D1-D10 are **proposed, not confirmed**. Section 0 is the gate: if the client
overrides a decision, the affected design section changes before the migration is written.

## 0. Decision gate

- [ ] 0.1 Send `week2-decisions.md` for confirmation. Record each answer in place (status line to
      `APPROVED`, with the date) or amend the decision and the affected `design.md` section.
- [ ] 0.2 If D1 is answered with a client vocabulary, replace the derived Type values and the
      `CHECK` constraint lists before task 1.2. If unanswered, proceed with the 11 categories as
      Type and Sub-type null, and note the assumption in the migration docstring.

## 1. Global content — models, migration, seed

- [ ] 1.0 **Vendor the content pack into this repository, before anything reads it.** Both source
      files live in a different repo (`proposal.md`, "Provenance"). Copy
      `C:/Users/HP/OneDrive/Desktop/Platform/grc-s/backend/app/control_library.json` and
      `.../backend/data/soc2_controls.json` into `backend/src/verity/modules/compliance/content/`,
      record each file's `sha256` in a `content/SOURCES.md` alongside its origin path and the date
      copied, and assert the hashes in the seed test so a silent edit to a shipped compliance
      artefact fails the build. Hashes at time of writing:
      `control_library.json` = `e7b8135f2eb62f7218311aa7e17f6c1265af05d6068caaa1cd09279238127957`,
      `soc2_controls.json` = `82b1653ccf418e0acd40dc271ac56e4228e5321081e211b378f60d2d5c2be984`.
      Re-verify on copy; if either differs, stop and reconcile rather than recording the new one.
- [ ] 1.1 `modules/compliance/models.py` — Layer A and B tables from `design.md`: `frameworks`,
      `framework_versions`, `requirements`, `framework_version_requirements`, `control_templates`,
      `template_requirement_map`, with every `CHECK` and unique constraint.
- [ ] 1.2 Migration part one: create the six global tables and their indexes. **`GRANT SELECT`
      only** to the app role — do not call `grant_crud()`, and do not enable RLS. Assert in the
      migration that the app role has no `INSERT` privilege on them.
- [ ] 1.3 Content loader for the SOC 2 pack, run by the migration as the owner role: 1 framework,
      1 framework version (`2017-rev-2022`, `is_current`), 61 requirements from
      `soc2_controls.json` with `requirement_key = 'SOC2:' || code` and `is_always_in_scope` true
      for the 33 common-criteria rows, and their `framework_version_requirements` rows. Every
      insert `ON CONFLICT DO NOTHING`.
- [ ] 1.4 Content loader part two: 114 `control_templates` from `control_library.json` —
      `code` = the slug, `canonical_key` = the slug, `control_type` = the category (D1),
      `control_sub_type` null, `importance` lower-cased to `mandatory` / `preferred`.

      **The description transform, in full.** Every source `description` has the shape
      `"## Why? <why text>\n\n## How? <how text>"` — *both* headings are literal text in the
      string, not just the second one. Splitting only at `## How?` leaves all 114 descriptions
      beginning `"## Why? "`, which renders to the client. The transform is: split at `## How?`,
      strip the leading `## Why?` heading from the first part, strip the `## How?` heading from
      the second, trim whitespace from both, and assign them to `description` and
      `implementation_guidance`. A part that is empty after trimming is stored as NULL, not as an
      empty string.

      Then the 150 `template_requirement_map` rows, all `coverage='full'`, `weight=1.000`.
- [ ] 1.5 Seed assertions as a test, not as trust: exactly 61 requirements, 114 templates, 150
      mappings, 11 distinct template categories, 13 distinct requirement categories, and **zero
      requirements with no mapping**. A content pack that leaves a criterion uncoverable is a
      compliance defect no other test catches.

      Plus one assertion for the 1.4 transform: **no seeded `name`, `description`, or
      `implementation_guidance` on any of the 114 templates begins with `#`.** A leaked markdown
      heading is invisible to every other test here and visible to every auditor.
- [ ] 1.6 Verify `alembic upgrade head` / `downgrade -1` / `upgrade head` on the global half.

## 2. Tenant plane — models, migration, RLS

- [ ] 2.1 `models.py` — Layer C tables: `controls`, `control_requirement_map`, `engagements`,
      `engagement_frameworks`, `engagement_scope_categories`. Every person reference is a FK to
      `tenant_memberships.id` (D8). Every `CHECK` from `design.md`, including the two that make a
      disabled control impossible without a justification and a timestamp.
- [ ] 2.2 Migration part two: create the five tenant tables, every index from the `design.md`
      table with `tenant_id` leading, `enable_rls()` + `grant_crud()` on each, and the two partial
      unique indexes that carry real semantics — `(tenant_id, canonical_key)` and the one-active-
      engagement index. Every `CHECK` and `UNIQUE` is **named** per
      `docs/conventions/database.md` (`ck_<table>__<rule>`, `uq_<table>__<cols>`) — an unnamed
      constraint cannot be dropped by a later migration without looking up what Postgres called it.
      `control_sub_type` gets **no** `CHECK` on either table (D1: no vocabulary exists yet).
- [ ] 2.3 Composite foreign keys, per `design.md`, "Composite foreign keys": `UNIQUE (tenant_id,
      id)` on `controls`, `engagements`, and `engagement_frameworks`, and every child key on the
      pair — `control_requirement_map (tenant_id, control_id)`, `engagement_frameworks
      (tenant_id, engagement_id)`, `engagement_scope_categories (tenant_id,
      engagement_framework_id)`, and the deferred `role_assignments (tenant_id, engagement_id) ->
      engagements (tenant_id, id) ON DELETE RESTRICT`, with a downgrade that removes it. Postgres
      FK checks bypass RLS, so a bare `id` reference is a cross-tenant hole. `role_assignments` is
      an `iam` table; say so in the migration docstring and cite
      `add-identity-and-access/design.md`.
- [ ] 2.4 Seed the five Week 2 permission keys (`INSERT ... ON CONFLICT (key) DO NOTHING`) and
      grant them to the built-in Compliance Manager, Control Owner, and Auditor roles per
      `design.md`. Admin needs no change.
- [ ] 2.5 Verify `upgrade` / `downgrade` / `upgrade` end to end, and that the downgrade docstring
      states it destroys every tenant control, crosswalk edit, and engagement.

## 3. Instantiation

- [ ] 3.1 Implement `instantiate(tenant_id, framework_version_id)` exactly as specified in
      `design.md`: upsert on `(tenant_id, canonical_key)` **with the index predicate in the
      conflict target** — `ON CONFLICT (tenant_id, canonical_key) WHERE canonical_key IS NOT NULL`
      — because the arbiter is a partial index and Postgres raises 42P10 without it. Then project
      the shipped crosswalk with `ON CONFLICT DO NOTHING`. Returns
      `InstantiationResult(created, reused, mappings_created)`. Add a test that runs the real
      statement against Postgres; a mocked upsert cannot catch 42P10.
- [ ] 3.2 `next_free_code()` — resolve a `(tenant_id, code)` collision by numeric suffix. It is a
      read-then-write, so `(tenant_id, code)` is a **second arbiter** that `ON CONFLICT` cannot
      cover: catch `unique_violation` on `uq_controls__tenant_id_code` inside a `SAVEPOINT` and
      retry with the next free code, bounded, then raise a typed error. Unit-test that a custom
      control already holding the slug does not block instantiation, and test the retry with a
      forced collision.
- [ ] 3.3 Wire it into `tenancy`'s provisioning `seed_content` step through the tenancy service
      interface, replacing the Week 1 honest no-op. The step now reports the real count.
- [ ] 3.4 Audit rows: one `create` per control and per mapping, same transaction. Integration-test
      that a rolled-back instantiation leaves no audit rows.
- [ ] 3.5 Idempotency test: run it twice, assert the second run creates nothing and returns
      `(0, 114, 0)`.
- [ ] 3.6 **The reuse test — the reason the hardening exists.** Seed a synthetic second framework
      whose templates share canonical keys with the SOC 2 pack. Instantiate it into a tenant that
      already has SOC 2. Assert: zero new controls for the shared concepts, new crosswalk edges
      only, and that a control's owner and status are unchanged. Assert the same for a custom
      control that has opted into a canonical key.

## 4. Controls — service and routes

- [ ] 4.1 Repository and service: list with filters (Type, Sub-type, status, owner, requirement,
      free text, include/exclude disabled), read by id, and the control's mapped criteria.
- [ ] 4.2 `GET /controls`, `GET /controls/{id}` — `controls:read`. Cross-tenant id is 404.
- [ ] 4.3 `POST /controls` (custom: no `template_id`, optional `canonical_key`) and
      `PATCH /controls/{id}` — `controls:manage`. Owner must be an active membership **in this
      tenant**; a `users.id` is rejected at validation with a typed error.
- [ ] 4.4 `POST /controls/{id}/disable` — justification is required by the schema and by the
      database. `POST /controls/{id}/enable` clears the disable columns. Disabling an already
      disabled control is a no-op with no second audit row.
- [ ] 4.5 `PUT /controls/{id}/requirements` — edit the tenant crosswalk: add, remove, set
      `coverage` / `weight` / `rationale`. Adding by hand sets `review_status='accepted'` with the
      acting membership as reviewer.
- [ ] 4.6 Every state-changing path writes `audit_log` with before/after snapshots in the same
      transaction. Integration-test one rollback per verb.

## 5. Engagements and the coverage view

- [ ] 5.1 Engagement CRUD: create (draft), read, list, patch, `DELETE` for drafts only (409
      otherwise). `engagements:read` / `engagements:manage`.
- [ ] 5.2 `POST /engagements/{id}/frameworks` — pin a `framework_version_id`, and auto-insert the
      always-in-scope categories. `PUT .../categories` sets the optional ones; removing an
      always-in-scope category is a typed 422, never a silent ignore.
- [ ] 5.3 `POST /engagements/{id}/activate` — draft to active. The partial unique index is what
      refuses a second active engagement; the service translates the integrity error to a typed
      domain exception, it does not pre-check and race.
- [ ] 5.4 `GET /engagements/{id}/coverage` — every in-scope requirement of the pinned version with
      no accepted, enabled, mapped control, plus per-category counts. The query joins through
      `controls`, never against `control_requirement_map` unqualified.
- [ ] 5.5 Unit-test the Type I / Type II window rules: Type II needs a real window, Type I stores
      the as-of date in both columns, start after end is refused.

> **`readiness.score()` is not in this change.** An earlier draft carried it here as task 5.6. It
> contradicts `proposal.md`'s Non-goals ("No readiness … nothing computes it in this change") and
> D2 itself, which says the formula is *decided* in Week 2 and **implemented in Week 3**. Week 2
> creates the columns the formula reads and writes the definition down in `design.md`; the pure
> function and its unit tests belong to the Week 3 evidence-and-readiness change.

## 6. Authorization

- [ ] 6.1 Implement `ControlOwnerScope` against `controls.owner_membership_id`, satisfying the
      `ObjectScope` protocol. `filter` for lists, `allows` for by-id — denial is **404**.
- [ ] 6.2 Reconcile Week 1 finding #17: `EngagementScope.allows(...)` currently treats its argument
      as an engagement id, not the object-under-access id the protocol defines. Fix the signature
      and its callers now that a module uses the protocol for real.
- [ ] 6.3 Test the matrix: Compliance Manager sees every control in the tenant; a Control Owner
      sees only owned controls and gets 404 for another owner's control by id; a member with no
      compliance key gets 403 regardless of ownership.

## 7. Isolation tests — ship in this change

- [ ] 7.1 `tests/isolation/test_compliance_isolation.py`: tenants A and B each with controls,
      crosswalk rows, engagements, and scope categories. Every list, read, update, and disable from
      an A session touches nothing of B; cross-tenant ids are 404.
- [ ] 7.2 A write carrying tenant B's `tenant_id` from an A-bound session is refused by
      `WITH CHECK`, on all five tenant tables.
- [ ] 7.3 **Global-content hazard one:** an A-bound session reads `frameworks`, `requirements`, and
      `control_templates` in full. Assert the counts are 1 / 61 / 114 with a tenant bound — RLS
      naively applied to global content would make this zero and every tenant's compliance would
      silently read empty.
- [ ] 7.4 **Global-content hazard two:** the app role's `INSERT`, `UPDATE`, and `DELETE` on all six
      global tables are refused by privilege. A tenant cannot author a framework or a requirement.
- [ ] 7.5 The coverage-gap anti-join returns only tenant A's gaps when B has mapped the same
      requirement — the leak the deep-dive names for an unqualified `NOT EXISTS`.
- [ ] 7.6 Two tenants instantiating the same framework get independent control rows; editing A's
      control name, owner, or status changes nothing in B.
- [ ] 7.7 **Cross-tenant parent references are refused by the database.** From an A-bound session,
      insert a `control_requirement_map` row with `tenant_id = A` and B's `control_id`; an
      `engagement_frameworks` row with `tenant_id = A` and B's `engagement_id`; an
      `engagement_scope_categories` row with `tenant_id = A` and B's `engagement_framework_id`;
      and a `role_assignments` row with `tenant_id = A` and B's `engagement_id`. Each must raise
      **`foreign_key_violation`** — assert the specific SQLSTATE, not merely that something raised.
      Every row carries A's own `tenant_id`, so RLS `WITH CHECK` is satisfied and the composite
      foreign key is the only thing refusing it. With bare `id` references all four would succeed.

## 8. Frontend — `features/compliance/`

- [ ] 8.1 `api.ts` / `schemas.ts` / `hooks.ts` mirroring the routes, following
      `features/iam/` as the reference shape. No business rules on this side (D6).
- [ ] 8.2 Control library list: table with Type and Sub-type filters, status, owner, search, and a
      disabled toggle. Empty and loading states from the design system primitives.
- [ ] 8.3 Control detail: fields, mapped criteria with coverage and weight, implementation
      guidance, owner assignment, edit, and disable with a required justification in the dialog.
- [ ] 8.4 Add-custom-control form.
- [ ] 8.5 Engagement setup: audit type, observation window (Type I collapses to one date picker),
      framework version, categories in scope with the always-in-scope ones locked and labelled.
- [ ] 8.6 Coverage view: in-scope criteria with no control, grouped by category, linking to the
      control library filtered to that requirement.
- [ ] 8.7 Nav entry, route guards on the new permission keys, and MSW handlers matching the real
      response shapes.

## 9. Docs — in the same change

- [ ] 9.1 `docs/architecture/data-model.md`: expand the **Compliance** paragraph with the three
      layers, canonical control identity, framework versioning with stable requirement ids, and the
      crosswalk's coverage / weight / review columns. Record the two ER deviations with citations.
- [ ] 9.2 Update the ER Design document's Section 3.2 diagram to match: `framework_versions`,
      `framework_version_requirements`, `canonical_key` on controls and templates, the crosswalk's
      new columns, `owner_membership_id` instead of `owner_id`, and the engagement scope join table
      in place of `categories_in_scope` jsonb. The `.docx` is the signed original and is corrected
      under its own change control — flag it, do not edit it in place.
- [ ] 9.3 Write **ADR-0012, canonical control identity and framework versioning**. This is
      expensive to reverse and is the kind of decision `openspec/config.yaml` says belongs in an
      ADR rather than in an archived change.
- [ ] 9.4 `docs/architecture/multi-tenancy.md`: document that compliance derivation joins tenant
      tables to unscoped global content by design, why global content is `SELECT`-only to the app
      role, and the two hazards tests 7.3-7.5 cover.
- [ ] 9.5 Record the derived columns approved here — `canonical_key`, `framework_versions`,
      `framework_version_requirements`, `requirement_key`, `is_always_in_scope`, `coverage`,
      `weight`, `rationale`, `review_status`, `instantiated_content_hash` — so a future reader does
      not mistake them for drift.
- [ ] 9.6 Extend `docs/runbooks/week1-demo.md` into a Week 2 section: instantiate a tenant, filter
      the library by Type, edit a control, add a custom one, disable one with a justification, set
      up an engagement, and read the coverage view. It is also an integration test, so the demo
      cannot rot.
