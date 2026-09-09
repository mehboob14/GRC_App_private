# Tasks — third-party vendor risk

Each task is at most two hours. Every migration that adds a tenant-owned table enables RLS and
adds its policy in the same migration; the isolation tests ship in this change.

**V1, V10, V13 and V14 are confirmed (2026-09-09).** The other ten decisions stand as
*recommendation taken* and are built as written in `vendor-decisions.md`.

## 0. Before the first migration

- [x] 0.1 Decisions sent and answered. V1 twelve stages · V10 engagement is the unit of risk ·
      V13 Verity-authored bank only · V14 full ER, 26 tables.
- [x] 0.2 Vendor model written into `docs/architecture/data-model.md` as a module note — engagement
      as the unit of risk, the cached-not-authoritative columns, twelve stages as rows with
      `approval` the only gate, the `entered_at` gate-freshness rule, computed-not-stored exit
      criteria, append-only actor FKs, the four unfed tables, and the count (27 = 25 tenant-owned
      + 2 global). Points at `design.md` §1 for columns.
- [x] 0.3 All 26 ER tables transcribed verbatim into `design.md` §1, plus `vendor_transitions`.
      **§1 is now the single build reference — every migration is written from it.** Section 0
      settled thirteen things the diagrams left open, all in §1's deviation register:
      seven renames (`questionnaire_questions`, `vendor_tiering_policies`,
      `vendor_assessment_responses`, `vendor_assessment_comments`, `vendor_soc_report_reviews`,
      `vendor_discovered_apps`, `vendor_offboardings`); `questionnaire_templates` **keeps** its ER
      name against the earlier `questionnaire_banks`; **`vendor_reviewers` is cut** — policy
      `required_reviewer_roles_by_tier` ∩ `vendor_team_roster` covers spec ¶82 with no new table;
      `vendor_stages.exit_blockers` is cut (computed, never stored); `started_at` → the ER's
      `entered_at`; `portal_token` → hash + expiry + revocation (V11); `vendor_assessment_responses`
      gains a PK the diagram omits; `questionnaire_questions` gains `body`.

**Column lists live in `design.md` §1, not here.** A task naming a table means the block in §1.

## 1. Foundation

- [x] 1.1 `modules/vendors/models.py` — vocabularies as `Final` tuples, then `vendors`,
      `vendor_engagements`, `vendor_contacts`. `vendors` composes `Integratable`
      (`docs/conventions/database.md` names the table). One `LIFECYCLE_STATUSES` tuple serves both
      the vendor and the engagement: same states, independent values.
- [x] 1.2 Migration `f4b7d2a90e18` — those three tables, `enable_rls` + `grant_crud` each,
      tenant-first indexes, and the four `INSERT INTO permissions` rows (`vendors:read`,
      `:manage`, `:assess`, `:approve`). Downgrade proven by running it and re-upgrading.
      Also registered `vendors`, `documents`, `evidence` and `vulnerabilities` in
      `migrations/env.py`, which imported only eight of twelve model modules — autogenerate would
      have proposed dropping every table it could not see.
- [x] 1.3 `service.py` — Views, `create_vendor` with the implicit default engagement (V10),
      duplicate detection that warns rather than blocks, `AuditService` on every write. `_recache`
      is the only writer of the cached worst-engagement columns. No `repository.py`: the six most
      recent modules have none, and `backend/CLAUDE.md` was corrected to say so.
- [x] 1.4 `schemas.py` + `router.py` — register list, create, get, update, plus engagement and
      contact writes, `/facets` and `/duplicate-check`. `_Ctx`/`_Db` aliases, `require(...)` on
      every route, static paths before `/{vendor_id}`. `vendors:assess` and `vendors:approve` are
      seeded but attached to no route yet — sections 3 and 4 earn them.
- [x] 1.5 Mounted in `main.py`; the `vendors reaches no other module's data` contract already
      existed, so this added its `ignore_imports` for the sanctioned audit and iam legs.
      `lint-imports`: 17 contracts kept, 0 broken.
- [x] 1.6 Isolation test — six properties, all passing: the default engagement is written in the
      same transaction; an unfiltered read returns only tenant A's rows on all three tables; the
      register **and the duplicate check** stay inside the tenant (both tenants hold a vendor
      named "Acme Cloud"); a B row is absent by id and `NotFound` through the service; an unbound
      session sees nothing; and three forged writes carrying B's `tenant_id` are refused by
      `WITH CHECK`. `test_rls_coverage` now covers the three new tables automatically.

## 2. Tiering and the lifecycle

- [x] 2.1 `scoring.py` — pure inherent tiering (V6) returning the full breakdown, plus its unit
      tests. No session, no I/O. Reports the distance to the band above **and** below, which is
      spec ¶82's "what would change this" without re-running the form. `_tier_for` falls back per
      band to the shipped default so a partial override from tenant-editable JSON retunes one band
      instead of raising from inside a compliance calculation.
- [x] 2.2 `vendor_tiering_policies` + `vendor_tiering_assessments`, migration. **No seeded rows**:
      the defaults live in `scoring.py` / `lifecycle.py` and a row here is the override, merged
      field by field. That frees a new tenant of a provisioning step and keeps the migration from
      inserting a tenant-owned row it cannot see through that row's own policy. Adds
      `stage_skip_matrix_by_tier` and `required_reviewer_roles_by_tier`, the two things spec ¶82
      promises and the ER gives nowhere to live.
- [x] 2.3 `vendor_stages` + `vendor_transitions` (append-only, `ON DELETE NO ACTION` on both actor
      FKs, `occurred_at` alone), migration including `ck_vendor_stages__gate_never_skipped`.
      Verified directly: a skipped gate is refused by the database even when the service is
      bypassed.
- [x] 2.4 Stage materialisation: tiering inserts the twelve rows for the cycle and marks the
      tier's skipped stages with the policy that skipped them (V9). Idempotent — a retier re-plans
      what is still ahead and never touches a stage already complete or under way.
- [x] 2.5 `evaluate_exit(stage, facts)` — a checklist of `ExitCheck`, each naming the record that
      clears it. **Three-valued**: `None` means the module answering it is not built yet, so it
      never blocks and never renders as a tick. All twelve stages covered by unit tests against
      synthetic facts.
- [x] 2.6 The three transitions — advance / send back / skip — each writing a `vendor_transitions`
      row **and** an `audit_log` row in one transaction. Tests for the send-back reset (stages
      before the target untouched, skipped rows stay skipped), for skip refusing a gate and a
      required stage, and for the append-only trigger refusing a rewrite.
- [x] 2.7 `allowed_transitions` and the blocker/pending lists on every stage of the detail view,
      plus the stage vocabulary, skip matrix and tiering factors on `/facets` — so the client never
      hardcodes the machine.

## 3. Assessment and the portal

- [ ] 3.1 Global `questionnaire_templates` + `questionnaire_questions` (no `tenant_id`, no RLS),
      seeded with the Verity-authored bank across the ten domains (V8, subject to V13).
- [ ] 3.2 `vendor_assessments` + `vendor_assessment_responses`, migration. Token stored hashed with expiry
      and revocation columns (V11).
- [ ] 3.3 Issue a questionnaire: create the assessment, mint the token, notify the contact.
- [ ] 3.4 Portal endpoints — unauthenticated, token-resolved tenant, rate limited, upload
      allowlist. **Security review before merge**: this is the platform's only external write
      path.
- [ ] 3.5 Residual scoring (V7) in `scoring.py` with its tests, including the clamp and the
      critical-control floor as reported steps.
- [ ] 3.6 `vendor_findings`, migration, auto-suspend on an open critical, acceptance with a
      required future expiry. `promoted_risk_id` nullable, **no promotion action**.
- [ ] 3.7 Remediation creates a real task via `task_service`, not a vendor-local table.

## 4. Decision, contract and exit

- [ ] 4.1 `vendor_approvals` (append-only), migration, four-valued decision (V3).
- [ ] 4.2 Approve/defer/reject with segregation of duties enforced server-side (V4) and the
      gate-freshness rule (`decided_at >= stage.entered_at`). Tests for both.
- [ ] 4.3 Conditions on an approval become tasks.
- [ ] 4.4 `vendor_documents` + `vendor_contracts`, migration, coverage window and expiry,
      `evidence_id` link.
- [ ] 4.5 `vendor_signals`, migration, with `source`/`external_id`/`synced_at` from day one.
- [ ] 4.6 `vendor_soc_report_reviews`, migration. Structured fields: report kind, audit period,
      criteria, opinion, bridge letter, findings-material, CUEC reviewed, subservice orgs.
      **This is the CC9.2 artefact** (ER ¶110) — it earns its own review screen, not a form.
- [ ] 4.7 `vendor_subprocessors`, migration. The fourth-party register with data location and
      notification obligations.
- [ ] 4.8 `vendor_slas`, migration. Committed level vs measured, with the breach flag derived on
      read rather than stored.
- [ ] 4.9 `vendor_approval_conditions`, migration; each condition also creates a task.
- [ ] 4.10 `vendor_assessment_comments`, migration; the reviewer thread on an assessment.
- [ ] 4.11 `vendor_intake_requests`, migration; the front door, with its own approve/decline that
      creates the vendor on acceptance.
- [ ] 4.12 `vendor_team_roster`, migration; roles as rows, not a JSON blob.
- [ ] 4.13 `vendor_alert_rules`, migration. In-app delivery works now; the Slack channel is
      wired but inert until the Phase 2 connector.
- [ ] 4.14 `vendor_scorecards` and `vendor_discovered_apps`, migrations, with rule-9 columns. **Manual
      entry only** — no connector feeds either in any phase yet.
- [ ] 4.15 `vendor_offboardings`, migration; archive-not-delete; attestation recorded as an
      assessment; certificate stored as evidence.
- [ ] 4.16 Reassessment: new cycle, carry intake and tiering forward, `next_reassessment_on`
      computed from cadence not completion. Test that a late review does not move the next one.
- [ ] 4.17 Three celery-beat jobs — reassessment queue, document expiry, SLA breach sweep — each
      iterating tenants one transaction at a time.

## 5. Interface

- [ ] 5.1 New `components/ui` primitives: stage rail, checklist row, threshold ruler, `date`
      variant on `TextField`, sparkline. **Reuse the documents module's diff renderer** rather
      than building a second. Check every `status-*` family and icon name exists first.
- [ ] 5.2 `features/vendors/` — `types.ts`, `tokens.ts`, `api.ts`, layout with the four
      module-root tabs.
- [ ] 5.3 Register: columns, facets, `ColumnPicker`, `useTableSort`, the **Blocker / next
      action** column, and the healthy-state line.
- [ ] 5.4 Detail page: `DetailHeader` + inline `TabStrip` + `lg:grid-cols-[1fr_20rem]` with
      `min-w-0` on the left column.
- [ ] 5.5 The lifecycle workspace: vertical stage rail, gates fenced and diamond-marked, blockers
      as actions with their own buttons, skipped rows carrying the policy that skipped them.
- [ ] 5.6 The gate-unblock handoff: blockers collapse to one success line, the advance control
      enables, and the next actor is named with a notify action.
- [ ] 5.7 Tiering panel in the shape of the vulnerability risk panel: gauge, factor × weight ×
      points table, threshold ruler, live recompute.
- [ ] 5.8 Approval form with disqualified approvers greyed and annotated (V4).
- [ ] 5.9 Reassessment-as-diff: prior answers pre-filled, changed chips, "what changed since"
      panel with the score delta and its cause.
- [ ] 5.10 Document rows with coverage window and countdown; renewal request action.
- [ ] 5.11 SOC report review screen: the structured fields as a readable summary an auditor can
      accept, not a form dump. Opinion and material-findings lead.
- [ ] 5.12 Subprocessor register and SLA tab.
- [ ] 5.13 Intake request queue with approve/decline.
- [ ] 5.14 Monitoring tab: signals and scorecards, each with an explicit **"no data source
      connected"** state rather than an empty table.
- [ ] 5.15 Routes in `routes.tsx`; remove `comingSoon` from the nav entry; add the four permission
      keys to `PERMISSION_KEYS` **and** to `PERMISSION_GROUPS` — the compile guard will catch the
      second if it is forgotten.

## 6. Close

- [ ] 6.1 `make check` clean: ruff, mypy, import-linter, eslint, tsc.
- [ ] 6.2 `tests/isolation/` passes, including RLS coverage for every new tenant-owned table.
- [ ] 6.3 Walk the Week-5 review script end to end: add a vendor, tier it, issue a questionnaire,
      log a finding — plus the approval gate, which the week list omits but ¶85 requires.
- [ ] 6.4 Update `docs/architecture/data-model.md` with anything learned that is "easy to get
      wrong", and record the finding→risk shortfall in the change's completion note.
