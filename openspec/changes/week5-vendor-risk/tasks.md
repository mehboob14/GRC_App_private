# Tasks — third-party vendor risk

Each task is at most two hours. Every migration that adds a tenant-owned table enables RLS and
adds its policy in the same migration; the isolation tests ship in this change.

`vendor-decisions.md` V1–V14 are **proposed, not confirmed**. Section 0 is the gate: if a
decision is overridden, the affected design section changes before any migration is written.

## 0. Decision gate — nothing below starts until this closes

- [ ] 0.1 Send `vendor-decisions.md` for confirmation. Record each answer in place (status line
      to `APPROVED`, with the date) or amend the decision and the affected `design.md` section.
- [ ] 0.2 **V1 first.** Eleven stages or twelve decides the `CHECK` constraint, the skip matrix
      and every stage row ever written. Nothing in section 2 starts before it is answered.
- [ ] 0.3 **V13 needs a legal answer, not an engineering one.** If SIG/CAIQ/HECVAT text cannot
      ship, task 3.1 seeds the Verity-authored bank only and the mapping-by-name stays.
- [ ] 0.4 Confirm V14's scope line. If the ER-only tables are pulled in, this change grows by
      roughly ten tables and needs re-planning rather than extending.
- [ ] 0.5 Write the agreed vendor model into `docs/architecture/data-model.md` as a module note.
      CLAUDE.md forbids inventing schema; that file is the working summary and currently has a
      Vendors paragraph of principles but no column list.

## 1. Foundation

- [ ] 1.1 `modules/vendors/models.py` — vocabularies as `Final` tuples, then `vendors`,
      `vendor_engagements`, `vendor_contacts`.
- [ ] 1.2 Migration part 1: those three tables, `enable_rls` + `grant_crud` each, tenant-first
      indexes, and the four `INSERT INTO permissions` rows (`vendors:read`, `:manage`,
      `:assess`, `:approve`).
- [ ] 1.3 `service.py` — Views, `create_vendor` with the implicit default engagement (V10),
      duplicate detection on save warning rather than blocking, `AuditService` on every write.
- [ ] 1.4 `schemas.py` + `router.py` — register list, create, get, update. `_Ctx`/`_Db` aliases,
      `require(...)` on every route, static paths before `/{id}`.
- [ ] 1.5 Mount in `main.py`; add the `vendors reaches no other module's data` contract and the
      four `ignore_imports` entries to `pyproject.toml`; confirm `lint-imports` still passes.
- [ ] 1.6 Isolation test: a vendor in tenant A is invisible to tenant B through the service and
      through raw SQL with the other tenant bound.

## 2. Tiering and the lifecycle

- [ ] 2.1 `scoring.py` — pure inherent tiering (V6) returning the full breakdown, plus its unit
      tests. No session, no I/O.
- [ ] 2.2 `vendor_tiering_policies` + `vendor_tiering_assessments`, migration, seeded defaults.
- [ ] 2.3 `vendor_stages` + `vendor_transitions` (append-only, `ON DELETE NO ACTION` on the actor
      FK), migration including the `CHECK` that a gate is never skipped.
- [ ] 2.4 Stage materialisation: running tiering inserts the stage rows for the cycle and marks
      the tier's skipped stages with their reason (V9).
- [ ] 2.5 `evaluate_exit(stage)` — blockers as structured objects naming the clearing record.
      Unit tests per stage.
- [ ] 2.6 The three transitions — advance / send back / skip — each writing both a
      `vendor_transitions` row and an `audit_log` row in one transaction. Tests for the
      send-back reset and for skip refusing a gate.
- [ ] 2.7 `allowed_transitions` and the blocker list on the detail view, so the client never
      hardcodes the machine.

## 3. Assessment and the portal

- [ ] 3.1 Global `questionnaire_banks` + `questionnaire_questions` (no `tenant_id`, no RLS),
      seeded with the Verity-authored bank across the ten domains (V8, subject to V13).
- [ ] 3.2 `vendor_assessments` + `vendor_responses`, migration. Token stored hashed with expiry
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
      gate-freshness rule (`decided_at >= stage.started_at`). Tests for both.
- [ ] 4.3 Conditions on an approval become tasks.
- [ ] 4.4 `vendor_documents` + `vendor_contracts`, migration, coverage window and expiry,
      `evidence_id` link.
- [ ] 4.5 `vendor_signals`, migration, with `source`/`external_id`/`synced_at` from day one.
- [ ] 4.6 `vendor_offboardings`, migration; archive-not-delete; attestation recorded as an
      assessment; certificate stored as evidence.
- [ ] 4.7 Reassessment: new cycle, carry intake and tiering forward, `next_reassessment_on`
      computed from cadence not completion. Test that a late review does not move the next one.
- [ ] 4.8 Two celery-beat jobs — reassessment queue and document expiry — each iterating tenants
      one transaction at a time.

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
- [ ] 5.11 Routes in `routes.tsx`; remove `comingSoon` from the nav entry; add the four permission
      keys to `PERMISSION_KEYS` **and** to `PERMISSION_GROUPS` — the compile guard will catch the
      second if it is forgotten.

## 6. Close

- [ ] 6.1 `make check` clean: ruff, mypy, import-linter, eslint, tsc.
- [ ] 6.2 `tests/isolation/` passes, including RLS coverage for every new tenant-owned table.
- [ ] 6.3 Walk the Week-5 review script end to end: add a vendor, tier it, issue a questionnaire,
      log a finding — plus the approval gate, which the week list omits but ¶85 requires.
- [ ] 6.4 Update `docs/architecture/data-model.md` with anything learned that is "easy to get
      wrong", and record the finding→risk shortfall in the change's completion note.
