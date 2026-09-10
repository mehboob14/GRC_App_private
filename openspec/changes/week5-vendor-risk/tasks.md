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

- [x] 3.1 Global `questionnaire_templates` + `questionnaire_questions` (no `tenant_id`, no RLS,
      `GRANT SELECT` only — **not** `grant_crud`, which the newest global table got wrong), seeded
      with the Verity-authored bank: **59 questions across V8's ten domains**, generated by
      `scripts/build_vendor_questionnaire.py` into a content pack and loaded by the existing seed
      command. Idempotent — the second run reports no changes. **V13 honoured: no SIG, CAIQ or
      HECVAT text**; `framework_refs` names SOC 2 and ISO 27001 controls by identifier only.
      Questions are never pruned on re-seed, unlike every other pack: a response points at the
      question it answered, and the FK is `ON DELETE RESTRICT`. Unasked and deleted differ.
- [x] 3.2 `vendor_assessments` + `vendor_assessment_responses`, migration. **The token moved to
      its own table** — `vendor_portal_tokens`, on the global plane with no policy, because a
      portal request must resolve a tenant before RLS can bind it and a tenant-owned table cannot
      answer that. It stores a sha256 and the pair it resolves to, nothing else. Rotation writes a
      row and revokes the old one, so who was sent a link and when survives (V11).
- [x] 3.3 Issue a questionnaire: the **tier picks the question set** (15 for low, 59 for critical),
      snapshotted onto the assessment because the bank is versioned content that can change
      mid-answer. Mints the token, returns it exactly once, emails the contact through the mailer
      directly — `notification_service` targets memberships and a vendor contact is not one.
- [x] 3.4 Portal endpoints — unauthenticated, token-resolved tenant, rate limited, upload through
      the shared allowlist. **Rate limiting did not exist in this codebase**: `core/ratelimit.py`
      is new, Redis-backed (the dependency was already pinned *for this*), fails closed, and uses
      two buckets so a successful resolve never consumes the brute-force budget. **Security review
      run before merge** — see the completion note.
- [x] 3.5 Residual scoring (V7) in `scoring.py` with 12 unit tests: the 70% control ceiling, `na`
      leaving both sides of the average, a domain answered entirely `na` dropping out, the clamp,
      and the critical-control floor. The clamp and the floor are reported as their own steps
      **including when they did not fire**, and the floor's step says in words that it applies
      after the clamp and may therefore exceed inherent.
- [x] 3.6 `vendor_findings`, migration, one finding per `no` with severity from what the question
      is. Idempotent per question: re-scoring a corrected answer closes the finding rather than
      raising a second. Acceptance requires a future expiry **and** a rationale, enforced in the
      service and again by a CHECK. `promoted_risk_id` ships nullable with **no FK and no
      promotion action**.
- [x] 3.7 Remediation creates a real task via `task_service`, not a vendor-local table, and
      refuses to create a second one for the same finding.
- [x] 3.8 `audit_log.actor_type` gains `vendor_contact`. **An approved ER deviation** — the fifth
      on that table — recorded in `docs/architecture/data-model.md` and asserted by
      `test_audit_models.py`, which caught it rather than letting it through. Not in the original list, and needed:
      The portal is the first path where a state change is made by somebody who is neither a
      member nor the system, and recording answers as `system` would make "who answered this
      question" unanswerable.
- [x] 3.9 **Security review of the portal, before merge.** Six adversarial lenses, each finding
      independently verified against the code. 25 confirmed, 10 refuted. Two were serious and both
      are fixed: the live token was written to the access log in plaintext on every request (it is
      a path segment and the access log logs paths — the router's own docstring justified the
      choice on the opposite claim), and every portal caller shared one rate-limit bucket in
      production because the API runs behind a proxy without `--proxy-headers`, so ~300 junk
      requests would have locked the portal out for every tenant. Also fixed: `evidence_required`
      was enforced only against `yes`, so downgrading every answer to `partial` bought a scored
      review with no documents; four audit rows were missing or misattributed; and two
      before-snapshots were hardcoded literals. `core/middleware.safe_path` redacts the credential
      segment in the access log and all four exception handlers, with seven tests pinning it.
      The remaining findings — an unaudited orphan on re-upload, the upload cap running after the
      body is buffered, the missing `--proxy-headers` deployment flag, and `tenant_display_name`
      never resolving — are recorded in the completion note.

## 4. Decision, contract and exit

- [x] 4.1 `vendor_approvals` (append-only, `decided_at` alone, both actor FKs `ON DELETE NO
      ACTION`), migration, four-valued decision (V3). **`vendor_assessments.decision` is dropped**
      in the same migration: the ER draws two decision enums that disagree, and two tables holding
      overlapping decision state is the trap V3 names.
- [x] 4.2 Approve/defer/reject with segregation of duties enforced server-side (V4 — **two**
      exclusions, the business owner *and* the stage submitter, taking the ER's prose over its
      diagram) and the gate-freshness rule. The submitter is read from the append-only transition
      history, so it cannot be edited after the fact. Who was barred is **frozen onto the approval
      row**: the business owner can change, and "was segregation of duties applied here" has to
      stay answerable. `approvers()` returns the disqualified with their reason so the picker greys
      a name *and explains*, rather than refusing after a rationale has been written.
- [x] 4.3 Conditions on an approval become tasks, and an `approve_with_conditions` with no
      conditions is refused — it is an unconditional approval written more elaborately.
- [x] 4.4 `vendor_documents` + `vendor_contracts`, migration, coverage window and expiry,
      `evidence_id` link. Expiry and the auto-renew **notice deadline** are derived on read, never
      stored: the date somebody actually needs is never the one printed on the contract.
- [x] 4.5 `vendor_signals`, migration, with `source`/`external_id`/`synced_at` and a `dedup_key`
      unique per tenant from day one.
- [x] 4.6 `vendor_soc_report_reviews`, migration. **The CC9.2 artefact** (ER ¶110), structured so
      "which critical vendors hold an unqualified SOC 2 Type II covering the period" is a query. A
      qualified opinion or material findings raises a finding rather than being filed — recording
      the review and leaving the reader to notice is how a bad report gets forgotten.
- [x] 4.7 `vendor_subprocessors`, migration. `linked_vendor_id` makes concentration visible: the
      register reports how many other vendors declare the same fourth party.
- [x] 4.8 `vendor_slas`, migration. The stored status feeds the sweep; the breach flag the
      interface shows is derived on read.
- [x] 4.9 `vendor_approval_conditions`, migration; each condition creates a task, and a waiver
      states why.
- [x] 4.10 `vendor_assessment_comments`, migration. `visibility` is load-bearing — an
      `internal_only` comment reaching the portal is a disclosure incident.
- [x] 4.11 `vendor_intake_requests`, migration; the front door. Screening name-matches against the
      register so a duplicate is flagged before anyone reviews it. Accepting creates the vendor and
      its first engagement in one transaction; declining creates nothing and keeps its reason.
- [x] 4.12 `vendor_team_roster`, migration; roles as rows. With the tiering policy's
      `required_reviewer_roles_by_tier` this completes spec ¶82's "required reviewers" — and it
      needed no table of its own, which is why `vendor_reviewers` was cut in section 0.
- [x] 4.13 `vendor_alert_rules`, migration. In-app and email work; `slack` is accepted and inert
      until the Phase-2 connector, because a customer configuring Slack and never learning it does
      nothing is worse than one told it is unavailable.
- [x] 4.14 `vendor_scorecards` and `vendor_discovered_apps`, migrations, with rule-9 columns.
      **Manual entry only** — no connector feeds either in any phase yet.
- [x] 4.15 `vendor_offboardings`, migration; archive-not-delete, and completion is **refused while
      a step is outstanding**. An exit marked complete with access still live is the record an
      auditor uses to show the process is theatre.
- [x] 4.16 Reassessment: new cycle, stages laid out from the *current* tier, `next_reassessment_on`
      moved on the cadence from where it already was. Tested that a late review does not move the
      next one, and that an archived vendor drops out of the queue.
- [x] 4.17 Three celery-beat jobs — reassessment queue, document expiry, SLA breach sweep — each
      iterating tenants one transaction at a time, because the tenant setting is transaction-local
      and a job looping inside one transaction would read every tenant after the first with the
      wrong tenant bound. The first two only notify; only the SLA sweep writes, because a breached
      SLA is a fact the vendor caused rather than a judgement the platform is making.
- [x] 4.18 **The gate could be decided before it was reached.** Found by the send-back test: a
      reviewer could approve at intake, before a single stage of the review had happened, which
      would make the lifecycle decorative. `decide()` now requires the stage to have been entered,
      and `lifecycle` treats a never-entered stage as *not* satisfying the freshness rule — a
      send-back clears `entered_at`, so the old reading let a pre-send-back approval satisfy the
      gate again.

## 5. Interface

- [x] 5.1 New `components/ui` primitives: stage rail, checklist row, threshold ruler, `date`
      variant on `TextField`, sparkline. **Reuse the documents module's diff renderer** rather
      than building a second. Check every `status-*` family and icon name exists first.
- [x] 5.2 `features/vendors/` — `types.ts`, `tokens.ts`, `api.ts`, layout with the four
      module-root tabs.
- [x] 5.3 Register: columns, facets, `ColumnPicker`, `useTableSort`, the **Blocker / next
      action** column, and the healthy-state line.
- [x] 5.4 Detail page: `DetailHeader` + inline `TabStrip` + `lg:grid-cols-[1fr_20rem]` with
      `min-w-0` on the left column.
- [x] 5.5 The lifecycle workspace: vertical stage rail, gates fenced and diamond-marked, blockers
      as actions with their own buttons, skipped rows carrying the policy that skipped them.
- [x] 5.6 The gate-unblock handoff: blockers collapse to one success line, the advance control
      enables, and the next actor is named with a notify action.
- [x] 5.7 Tiering panel in the shape of the vulnerability risk panel: gauge, factor × weight ×
      points table, threshold ruler, live recompute.
- [x] 5.8 Approval form with disqualified approvers greyed and annotated (V4).
- [x] 5.9 Reassessment-as-diff: prior answers pre-filled, changed chips, "what changed since"
      panel with the score delta and its cause.
- [x] 5.10 Document rows with coverage window and countdown; renewal request action.
- [x] 5.11 SOC report review screen: the structured fields as a readable summary an auditor can
      accept, not a form dump. Opinion and material-findings lead.
- [x] 5.12 Subprocessor register and SLA tab.
- [x] 5.13 Intake request queue with approve/decline.
- [x] 5.14 Monitoring tab: signals and scorecards, each with an explicit **"no data source
      connected"** state rather than an empty table.
- [x] 5.15 Routes in `routes.tsx`; remove `comingSoon` from the nav entry; add the four permission
      keys to `PERMISSION_KEYS` **and** to `PERMISSION_GROUPS` — the compile guard will catch the
      second if it is forgotten.


**Deviations, recorded rather than silently taken:**

- **No sparkline.** 5.1 asked for one; the monitoring tab has no series to draw
  because signals, scorecards and app discovery all need a data source nobody
  has connected. A sparkline over no data is a decoration. Each of the three
  says so in its own words instead.
- **The documents diff renderer is not reused.** It renders server-tagged text
  blocks from `GET /documents/{id}/versions/{v}/diff`. A reassessment diff is
  answer-level, there is no equivalent endpoint, and features do not import each
  other. The "what changed since cycle N" panel compares the two cycles'
  responses client-side instead, with the score delta and the answers that moved.
- **No `date` variant on `TextField`.** It already spreads `type` onto the
  input, so `type="date"` works today and is used in six places.
- **The stage rail, checklist row and threshold ruler are feature-local**, not
  `components/ui`. They carry vendor domain knowledge, and the frontend contract
  says a domain component in the primitive directory is a mistake.
- **Two real `components/ui` additions**, both earned: `TextArea` (the same
  seven-line block was hand-rolled in eight files, none with an error slot), and
  `TableIconButton` made `forwardRef` (it could not be a Radix trigger, which is
  why every register hand-rolled the same button rather than using it).

**Backend fixes this section forced, each with the interface that exposed it:**

- `GET /vendors/findings`, `/intake` and `/roster` were declared after
  `GET /{vendor_id}` and answered 422 rather than data. Moved above it, with
  `tests/unit/test_route_shadowing.py` proving it for every router in the app.
- `FindingOut` gained `vendor_name`. The cross-vendor queue could otherwise only
  print an id, which is not a work queue.
- `VendorDetailOut` gained `assessments` (a summary, not the full payload).
  There is no list-assessments route, so the panel had nothing to list.
- `VendorFacetsOut` gained `reviewer_roles_by_tier`, so the gate handoff names
  the next actor from the policy instead of a second copy in TypeScript.
- `list_intake` returned an empty duplicates list, so a request could be flagged
  with no way to see what it matched.
- `tenant_display_name` read a `name` column that does not exist, so every
  portal page was addressed from "our organisation". Now trading, then legal.
- The SOC-review finding's body read `SOC2 type_ii ... opinion qualified`. It is
  the one finding that reaches the cross-vendor queue with no other context.

## 6. Close

- [ ] 6.1 `make check` clean: ruff, mypy, import-linter, eslint, tsc.
- [ ] 6.2 `tests/isolation/` passes, including RLS coverage for every new tenant-owned table.
- [ ] 6.3 Walk the Week-5 review script end to end: add a vendor, tier it, issue a questionnaire,
      log a finding — plus the approval gate, which the week list omits but ¶85 requires.
- [ ] 6.4 Update `docs/architecture/data-model.md` with anything learned that is "easy to get
      wrong", and record the finding→risk shortfall in the change's completion note.
