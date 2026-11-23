# Tasks: guided onboarding

Ordered so each phase ships on its own and nothing existing breaks. Requirement ids refer to
`docs/product/guided-onboarding/`. Sizes are for one developer: S is up to two days, M up to a
week, L more. Nothing starts before decision D-1.

A phase is done when its acceptance tests in part 2 pass, its isolation tests exist, `make check`
is clean, and the documents that describe it are updated in the same change.

## 0. Before any code

- [x] 0.1 Owner agrees scope and terms (D-1), ISO without SOC 2 (D-2), roles (D-12).
      2026-11-21: the owner said proceed with D-1, D-2 and D-3 as recommended. Work outside the
      signed phases is logged in `docs/product/guided-onboarding/phase_out_1.md` to be priced or
      shared separately. D-12 is still open; phase 1 avoids it (the status read needs only
      `tenant:read`, which every built in role holds).
- [x] 0.2 This change is reviewed and marked approved (owner go, 2026-11-21).
- [x] 0.3 Model names checked as each phase was built; where the build differs from section 2,
      `design.md` section 12 says so (2026-11-23).
- [x] 1.1 Fix the four defects of GS-14: security only completes the categories step (now "Choose
      your report type and categories", done once the engagement exists), the "later phase"
      footer is gone, control steps count every control ("4 of 133"), the page loads for every
      built in role (status needs `tenant:read` only; sections the role cannot read say so).
- [x] 1.2 Summaries through services: `engagement_service.program_figures` (every active
      framework in one read), `risk_service.assessment_counts`, `connector_service.connected_count`,
      plus the existing tenancy profile, iam members and security settings reads. Documents,
      tasks and vendors summaries come with the phases whose steps need them.
- [x] 1.3 `GET /onboarding/status`. Steps built now: profile, report type and categories (SOC 2),
      scope statement and applicability (ISO 27001), own two factor, admin two factor, invite,
      owners, risks, connect, evidence, failing checks (shown only once a check has a result).
      Not yet: a query count test (NF-8); the status read is one summary per module and one scope
      read per framework by construction, which the test should pin.
- [x] 1.4 Step catalogue. Deviation: a Python module (`modules/onboarding/steps.py`) instead of a
      sealed JSON file. Every step's done rule is code, so a file naming keys of code functions
      added indirection without review value; the module is reviewed like content. GS-3 updated.
      No "observation period" step: a Type 2 cannot be saved without both dates, so the step
      could never be open. Phase 3 adds "Start your observation period" (date reached).
- [x] 1.5 Rebuilt page `features/onboarding/components/get-started-page.tsx`: framework chips with
      type and dates, a Next card, shared steps grouped by phase with framework chips, a lane per
      framework, counts with a meter, "Where you stand" with four separate figures per framework,
      skip with a reason in a dialog, reopen. Loading, error and not permitted states. The old
      `compliance/components/quick-start-page.tsx` is removed.
- [x] 1.6 Address hooks: `?invite=1` (People), `?import=1` (Required documents), `?campaign=new`
      (document), `?tab=objectives|evidence` (control). Starting from a template is a button on
      Required documents, so the template picker needs no hook (2026-11-23).
- [x] 1.7 Skip and reopen with a reason. Migration `20261121_1000_onboarding_step_skips`
      (b9935aa647b2), forced RLS, no DELETE grant, audit rows on both. (GS-5)

Verified 2026-11-21: `tests/integration/test_onboarding_status.py` (5),
`tests/isolation/test_onboarding_isolation.py` (4), `tests/isolation/test_rls_coverage.py`,
`tests/unit/test_deps.py`, import contracts (20 kept), ruff and mypy on the changed files,
`tsc -p tsconfig.app.json` and eslint on the changed frontend files, migration up, down and up on
`verity_test`, and the page on the demo workspace (SOC 2 Type 2 plus ISO 27001) in headless
Chrome. The full backend suite was not run.

## 2. Company profile and country picker (M): core built 2026-11-21

- [x] 2.1 Migration `20261121_1100_company_profile_answers` (3b03e4d1a72c): `company_profile`
      gains `registered_address`, `answers` (JSONB object, CHECK), `answers_schema`, `status`
      (draft, confirmed), `version`, `confirmed_by_membership_id`, `confirmed_at`;
      `company_profile_versions` with forced RLS and append only. Up, down and up on `verity_test`.
- [x] 2.2 Answer model. Deviation: `modules/tenancy/profile_questions.py` instead of
      `profile.json`; it validates answers and the form renders from it, so the two cannot
      drift. 33 questions in six sections, 16 core plus the UAE zone. Unit test
      `tests/unit/test_profile_questions.py` (14): every question has a consumer line, counts,
      "not sure" counts as answered, bad answers refused in plain words. (PR-1, PR-4, PR-5, PR-6)
- [x] 2.3 Save (answers as a patch), confirm, versions, audit rows (`approve` on confirm).
      Routes `GET /tenant/profile/questions`, `POST /tenant/profile/confirm`,
      `GET /tenant/profile/versions`. Get Started's profile step now reads done only when
      confirmed, with a count of key questions before that. (PR-2, PR-3, PR-10)
- [x] 2.4 Country picker: `frontend/src/lib/countries.ts` (249 codes, aliases, regions, ranked
      search with spelling tolerance), `components/ui/country-select.tsx` (`CountrySelect`,
      `CountryMultiSelect`), `SearchableSelect` gains `filter`, `renderNoMatch`, `keepOpen`.
      Check: `node scripts/check-countries.ts` (27 cases, plain Node; the frontend has no test
      runner installed). Seen working in the demo UI: "Pakstan" finds Pakistan.
- [x] 2.5 Profile page as typed sections (`features/tenancy/profile-questions.tsx`): one line per
      question on what reads it, follow ups appear with their parent, draft and confirmed state,
      Save answers then Confirm profile, version history. Industry, size, headquarters and
      "frameworks in scope" moved off the legal details form. (PR-12)
- [x] 2.6 Prefill (2026-11-23): `GET /onboarding/profile-prefill` offers people (from active
      members), identity provider, hosting and code hosting (from active connections) for
      questions not answered; "Fill N from your workspace" puts them in the unsaved form,
      each marked with its source, and the person saves and confirms. (PR-7)
- [x] 2.7 Document variables (2026-11-23): starting from a template fills legal name, trading
      name, address, security lead and executive sponsor; a missing one shows "[Add your ...]"
      and the draft cannot go for approval while a marker remains. The fields are placed in five
      entity level templates (policy statement, ISMS scope, roles, oversight charter, SOC 2
      description). (PR-8)
- [x] 2.8 "Ask someone" on each profile section raises one task for that person. (2026-11-23)
- [x] 2.9 Earlier free text values (industry, company size, headquarters) show as hints under
      the matching question until it is answered. The old columns stay, read only.

Verified 2026-11-21: `tests/integration/test_company_profile_answers.py` (6),
`tests/isolation/test_profile_versions_isolation.py` (2), `tests/integration/test_onboarding_status.py`
(5, rerun), the unit test above, import contracts (20 kept), ruff and mypy, `tsc -p tsconfig.app.json`
and eslint on the changed frontend files, and the page on the demo workspace.

## 3. Frameworks, engagements and scope (M to L): built 2026-11-21 except 3.8, 3.10 (3.2 and 3.3 built with phase 5)

- [x] 3.1 Engagement fields and history. Migration 6b8df681a7aa: `as_of_date` (Type 1 only,
      CHECK), `target_date`, `driver`, `live_date`, `assessor_state` (unknown, undecided,
      chosen), accreditation body, contact, letter date; `certification_body` names the outside
      party for every framework; a save that does not send a field keeps it. Migration
      438b8c525629: `is_current` with one current engagement per framework version (partial
      unique index) and `engagement_milestones`. (EN-1 to EN-4)
- [x] 3.2 Framework chooser with "Help me choose". The overlap preview exists. Moved to phase 5
      with the setup flow, which is where the choice is made. (FS-1, FS-2, FS-4)
- [x] 3.3 Sign up behind `GUIDED_SETUP`. Moved to phase 5: without the setup flow a new workspace
      would have no way to choose a framework. (FS-3, CN-4, D-2)
- [x] 3.4 Turn a framework off with a reason (`POST /tenant-frameworks/{id}/deactivate`): keeps
      every record, refuses to turn off the last one, lists the controls only it needed and
      changes none of them. "Turn off" on the framework cards. (FS-6)
- [x] 3.5 Audit details card on every scope page, and an "Audit plan" card: the standard
      milestones for the audit type (dates that live on the engagement shown, not copied),
      planned and done dates, "Start next cycle" (closes the current cycle, carries scope
      decisions and vendors, keeps the history). (EN-2 to EN-4, EN-1)
- [x] 3.6 Scope: `scope_items` shared, `scope_decisions` per engagement (migration af53b58da5b3);
      `commitments` and `engagement_vendors` (migration 438b8c525629); suggestions from live
      assets and critical or high vendors, accepted by a person; "What is in scope", "What you
      promise customers" and "Subservice organisations" or "Suppliers the scope depends on" on
      the scope pages. (SC-0, SC-2, SC-3, SC-8, SC-9)
- [x] 3.7 SOC 2 can hold a scope statement and an audit firm (the emptying rule is gone). (SC-1)
- [x] 3.8 "In scope for" chips on asset and vendor pages, an "In scope for" filter on the
      asset register (`GET /engagement/in-scope-for`, assets take an id list so assets does not
      reach into compliance). Group pages not built. (SC-4, 2026-11-23)
- [x] 3.9 Changes in the period (`GET /engagement/changes`): scope changes recorded inside a SOC 2
      Type 2 period, listed on the SOC 2 scope page for the description's disclosure. (EN-5)
- [x] 3.10 Periodic controls against the period (`GET /engagement/periodic`): annual, quarterly
      and monthly controls with occurrences needed and evidence dated inside the Type 2 period
      or the year before the audit, on the Audits tab. Not on Get Started yet. (EN-8,
      2026-11-23)
- [x] 3.11 Timeline on Get Started from every framework's plan, with a table view. (GS-11)
- [x] 3.12 Done rules: "Name your auditor" per framework. Next picks the first open step of the
      framework whose next planned date comes first. (GS-8)

Verified 2026-11-21: `tests/integration/test_programme.py` (6), `test_scope_items.py` (4),
`tests/isolation/test_scope_isolation.py` (2), `test_onboarding_status.py`, RLS coverage, import
contracts (20 kept), ruff, mypy, tsc, eslint, migrations up, down and up on `verity_test`.

## 4. Ownership and required documents (M to L): built 2026-11-21 except 4.5, 4.9, 4.12

- [x] 4.1 Owner functions. Deviation: a rule by control family with named exceptions in
      `modules/onboarding/owner_functions.py` (part 5 table B2) instead of a field on 133
      templates; `tests/unit/test_owner_functions.py` checks every shipped control resolves.
      GOV-13 (internal audit) goes to the executive sponsor, not the security lead. (CL-8)
- [x] 4.2 `owner_functions` table (migration 9bc3f6a9db0c), "Who owns what" in Settings,
      Organization (replacing the "Key personnel" Soon tab), invite link, the internal audit
      warning, "Name who owns what" on Get Started. (OW-1, OW-4, OW-5)
- [x] 4.3 Apply owners through the compliance service, one audited change per control, keeping
      owners a person set unless the user unticks it. (OW-2)
- [x] 4.4 Role grants so every built in role loads Get Started (phase 1: status needs only
      `tenant:read`), and D-12: built in role Compliance Manager in `iam/service.py`
      `BUILT_IN_ROLE_KEYS`; existing workspaces get it with `python -m scripts.backfill_builtin_roles
      --apply`. Tests: `tests/unit/test_iam_module.py` (never holds administration or approvals),
      `tests/integration/test_onboarding_status.py` (acts on programme steps, refused on profile
      and invite). (OW-6)
- [x] 4.5 A member no longer active: Who owns what lists the functions they held and the
      controls and documents they owned; functions count and give defaults only through active
      members. Nothing is reassigned automatically. (OW-7, 2026-11-23)
- [x] 4.6 Required documents as reviewed data: `modules/documents/required_documents.py`,
      generated from Appendix A (54 rows: 44 templates, 5 kept in Verity modules, guidance and
      parts). Deviation: rows carry the frameworks, controls and profile condition, instead of
      fields on each template; the hand written `satisfies` stays for the template picker.
      (CL-4, CL-5)
- [x] 4.7 Starting a draft from a template links it to its controls (codes the workspace does
      not run are skipped). Owner and approver defaults from the functions are not set yet;
      the starter stays the owner as before. (RD-3)
- [x] 4.8 Required documents page (`/documents/required`, served by
      `GET /onboarding/required-documents` so the documents module reads only its own tables):
      states computed from the workspace's documents, one next step per row, rows hidden by
      the profile listed with the answer behind them. "Approve your policies and documents" on
      Get Started. (RD-1, RD-2, RD-5, RD-6, RD-7)
- [x] 4.9 An approved all staff document shows "Send to all staff for acknowledgement", which
      opens the campaign dialog on the document. (RD-8, 2026-11-23)
- [x] 4.10 A document lists the controls it supports (existing); controls list their documents
      (existing links). (RD-9, NV-4)
- [x] 4.11 Evidence guidance: what, where, what a good one shows and what to file when nothing
      happened on all 277 items; 19 "Sample of" items renamed to the full list the auditor
      samples from, 6 "Evidence" items renamed; 14 new items (13 manual operating items, the
      LM-07 incident register). Shown as "How to get this" on the control's checks tab. (CL-9)
- [x] 4.12 "Your part" on Get Started: documents waiting for your approval, documents to read
      and sign, tasks assigned to you. (GS-12, 2026-11-23)

Content: the 14 missing templates (CL-6) are drafted and shipped in the policies pack as
`review_status: draft_unreviewed` (sealed); the reviews of part 5, section 10 are still owed.
The seven Openlane rewrites (CL-1) are drafted in the owner's staging folder only, pending D-5.

Verified 2026-11-21: `tests/integration/test_ownership_and_required.py` (2),
`tests/unit/test_owner_functions.py` (3), content tests (176), seal check, import contracts
(20 kept), ruff, mypy, tsc, eslint, migration up, down and up.

## 5. Suggestions, baseline and work plan (L): built 2026-11-21

- [x] 5.1 Rule evaluator `modules/onboarding/rules.py`, pure, with unit tests
      (`tests/unit/test_onboarding_rules.py`): unknown or "not sure" never fires. (design 3.1)
- [x] 5.2 Deviation: the rules of part 5 section 4 are Python data reviewed with the code, not
      `applies_when` on the templates, as with the step catalogue; `bulk_ok` follows the "Safe
      to automate" column. The unit test checks every rule names a real question, option,
      control and ISO requirement. Rules built: no server sites, no offices, no software, no
      outside developers, employees only, office only, no subprocessors, no public app. The
      guidance switches of that table (card data, health, device model, oversight body) and
      "not needed for your SOC 2 scope" hiding are not built. (CL-7)
- [x] 5.3 Deviation: suggestions are computed on every read; only decisions are stored, in
      `onboarding_proposal_decisions` (migration 5d1e7c3b9a24). A rule that stops firing hides
      an open suggestion (replaced); an accepted one whose answer changed reads "review needed".
      A suggestion whose change is already in place, or that a person already decided on the
      record (a reviewed SoA row, a control moved off not started), is not shown. (PL-1, PL-4)
- [x] 5.4 Accept through the owning service (control status, SoA decision with
      `reviewed=True`, SOC 2 category), the decision audited in the same transaction; reject
      needs a reason; batch accept refused (409) where `bulk_ok` is false. (PL-2, PL-3, PL-5)
- [x] 5.5 Review page `/quick-start/suggestions`: grouped by the answer behind them, "Accept
      all" where allowed, a popup with the reason to edit, "Not for us" with a reason, decided
      ones collapsed, "Look again" rows link to their record. Get Started step "Review
      suggestions from your profile".
- [x] 5.6 `applicability_versions` (append only): approve freezes the statement as the next
      number, refused while a decision is unreviewed; list and download each version. On the
      statement page: "Approve version" and the version list; the ISO scope page names the
      approved version (2026-11-23). (SC-6, EN-11)
- [x] 5.7 A commitment that points at a SOC 2 category not in scope suggests adding it. (SC-5)
- [x] 5.8 `baselines`, `baseline_answers`, `readiness_snapshots` (append only). Baseline page
      `/quick-start/baseline`, one family per screen; answers never move a control's status;
      finishing takes a "Baseline" snapshot; reaching a milestone takes one too (2026-11-23),
      listed on the plan page. (PL-6, PL-9)
- [x] 5.9 Deviation: no `onboarding_plans` table. The plan is computed from the baseline and
      approval raises tasks through `task_service.raise_planned`, keyed on
      `(onboarding, item key)`, so approving twice raises nothing new; owners from the control,
      then its function; due date from the nearest planned milestone. Page `/quick-start/plan`.
      (PL-7, PL-11, PL-12)
- [x] 5.10 Evidence requests: a control in place without current evidence gets a task linked to
      the control. (PL-8)
- [x] 5.11 Connection suggestions from the identity provider, hosting and software answers,
      matched to the catalogue (`GET /onboarding/connections`), on the plan page. (PL-10)
- [x] 5.12 `onboarding_state` and the setup flow `/setup`: start point, frameworks with "Help me
      choose" (3.2), profile, audit, owners, suggestions; saved on every move; "Guided setup" on
      Get Started. Sign up skips SOC 2 adoption when `GUIDED_SETUP` is on (off by default;
      provider registration unchanged) (3.3).

Verified 2026-11-21 on verity_test: `test_proposals.py` (3), `test_baseline_and_plan.py` (3),
`tests/isolation/test_phase5_isolation.py` (6), `test_onboarding_status.py` and onboarding
isolation (12), unit rules (3), RLS coverage, import contracts (20 kept), ruff, mypy, tsc,
eslint, migration up, down and up. Fixed in passing: the Required documents list compared SOC 2
categories in the wrong case, so Privacy and Processing Integrity rows never showed.

## 6. Country reference panel (M, plus review time): built 2026-11-21 except 6.7

- [x] 6.1 Pack `seed/content/regulations/` (nine files, 83 entries, sealed, drafted with AI from
      the listed sources), read into memory by `modules/regulations/pack.py` after the seal
      check (`verity.seed.seal`, split from the loader so the module imports no other module's
      models). Unit test: sealed, unique keys, every trigger fact a real profile question,
      every "helps" code a real control or family, no dashes. (JC-1, J1)
- [x] 6.2 Matching on the shared grammar (`verity.shared.conditions`, now also used by the
      onboarding rules, with `any_in` and region expansion): the strongest trigger wins; an
      unanswered or "not sure" fact reads "Check whether it applies" for a first tier entry and
      hides the rest. (JC-2, JC-3, J3)
- [x] 6.3 Page `/regulations`: disclaimer, country chips, matrix by topic, a card per law, a
      drawer with duties (breach clocks first), dates, ISO 27001 and SOC 2 relation, controls
      you run that help, what they do not cover, sources, review state and overdue flag. Linked
      from the company profile and from the setup flow's profile screen (2026-11-23). (JC-5, JC-8,
      JC-9, J4)
- [x] 6.4 `regulation_decisions` (migration 8a4f2c6e1b37): relevant or not, a note required for
      not relevant, audited; a relevant law joins "Your obligations" on the laws page with the
      date it joined (2026-11-23). (JC-6, J5)
- [x] 6.5 Countries outside the pack are named on the page and logged by code only. (JC-7)
- [x] 6.6 "Controls you run that help", wildcards expanded to the workspace's own controls.
- [~] 6.7 Review by named reviewers. Shown in production now with the disclaimer and a not
      reviewed mark (D-8, 2026-11-23; `REGULATIONS_SHOW_DRAFTS` defaults on). Earlier: every entry is `ai_drafted` and the panel hid
      it unless `REGULATIONS_SHOW_DRAFTS` is on (off by default), saying how many wait. (J2, D-8)

Verified 2026-11-21: `tests/unit/test_regulations_pack.py` (3), `test_regulations.py` (1),
isolation for `regulation_decisions` (with phase 5, 8 passed), RLS coverage, seal check,
import contracts (21 kept, new `regulations` contract), ruff, mypy, tsc, eslint, migration up,
down and up.

## 7. Audit records, description, existing programmes, SOC 1 (L): built 2026-11-22 except parts of 7.5

- [x] 7.1 `assurance_records`, `assurance_findings` (migration 2c7d9e4f6a18, no DELETE grant):
      internal audit and management review with performer (member, or a named outside person
      and firm), independence confirmed by a member, report or minutes as a document, the
      clause 9.3 inputs listed for the review. A finding raises its corrective action task
      through `task_service.raise_planned` keyed on `(assurance, finding id)`. Page: Frameworks,
      Audits tab. (EN-9, CN-5)
- [x] 7.2 Outside audit stages on the same records with graded findings (major, minor,
      exception, observation); a graded finding closes only with closure evidence; a major is
      marked verified by the body with the date. (EN-10)
- [x] 7.3 Description inputs `GET /engagement/description-inputs`: nine areas, each with what
      the records already say (profile, commitments, in scope items, subservice vendors,
      categories not in scope, changes in the period) and what is left to write; the
      description itself starts from `soc2-system-description`. Page: Frameworks, Description
      tab. (EN-6)
- [x] 7.4 Done rules: go live (20), system description approved (18), internal audit with a
      report (21), management review with minutes (22), no finding past due (23), audit recorded
      with findings closed and majors verified (24). Phases "check" and "audit" added.
- [x] 7.5 Built: past reports and certificates as records (EX-2 facts and file); prior findings
      as tasks tagged with their record (EX-4); "We already have this" on Required documents
      confirms an uploaded draft as approved outside Verity with its date, by a member who may
      approve, kept on the document (`approved_elsewhere_on`, `_by`) and audited (RD-4, D-11,
      EX-3 one row at a time); the baseline already turns "in place" into evidence requests
      (EX-5). Added 2026-11-23: a certificate plans the next surveillance or recertification
      date; bulk import with a suggested match per file; "We already have a programme" puts an
      import screen (reports, documents, baseline) before the profile in setup (EX-1).
- [x] 7.6 SOC 1 guide `/guides/soc1`: what it is, objectives agreed with the audit firm, the
      general IT controls you run with their state, the three gaps. Guidance only. (S1-1 to S1-3)
- [x] 7.7 "Plan your next period" appears once the cycle's report or certificate decision is
      recorded and leaves when the next cycle starts. (GS-13)

Verified 2026-11-22: `test_assurance.py` (2), status tests updated for the seven phases (10 with
assurance), RLS coverage, import contracts (21 kept), ruff, mypy, tsc, eslint, migration up,
down and up.

## 8. AI assists (S to M): built 2026-11-22 and 23 except 8.3

- [x] 8.1 `POST /onboarding/assist` (`modules/onboarding/assist.py`): scope statement,
      description section, control explanation, suggestion reason. Each draft's origin (source,
      model, prompt version, time) is an audit row; with no key, or on failure, a template
      draft that says so. "Draft with AI" on the scope statement, the description areas, the
      suggestion popup and the control page ("Explain for us"); "Tailor with AI" on a draft
      document (preview, then "Use this version" saves a normal new version); a scope statement
      from a draft keeps "Draft, written with AI" until a member approves it, and the scope step
      needs that approval (EN-11) (2026-11-23). (AI-1, AI-2, AI-6)
- [x] 8.2 `test_onboarding_assist.py`: profile text carrying an instruction stays inside the
      data block, and a model answer claiming approval changes no control, suggestion or
      document. (AI-3, AI-4)
- [x] 8.3 "Draft from our website": not built, by decision (D-13, 2026-11-23). (AI-5)

## Content track, in parallel (part 5)

- [x] L5 Evidence guidance, and owner functions (half of L4). Done with 4.1 and 4.11.
- [x] L2 Documents that bind. Done as `required_documents.py` (4.6).
- [x] L4 Applicability rules. Done as `rules.py` (5.2). The guidance switches are short notes
      on the control page ("For your company"), and controls no requirement in scope needs can
      be filtered on the controls register (2026-11-23). Shipped control text is unchanged.
- [~] L3 Missing templates: 14 drafted and shipped as `draft_unreviewed`; the reviews of part 5 section 10 are owed.
- [~] L1 Honest content: the seven Openlane templates replaced by the plain word rewrites, marked
      draft and unreviewed (D-5, 2026-11-23). SOC 2 criterion text kept as is for now (D-4).
- [~] L6 Mapping fixes (D-10, 2026-11-23): 13 SOC 2 links added and DM-14 on P8.1 made partial;
      migration 6a1f9d3c8e25 carries the links to controls nobody edited, writes an audit row per
      link and a "library update" notice to the security lead, the sponsor and the control owners.
      Not done: the guidance and evidence text edits of section 7 (need a wording migration), the
      new controls DM-20, SD-15, SD-16, SD-17, DM-19 and PE-03 for SOC 2 (need the shared pack
      decision), the A.5.34 conditional links.
- [x] O1 Assessment objectives wave 1 (2026-11-23): sealed pack `seed/content/objectives/`
      (119 artifacts, 163 objectives on the 35 controls of part 5 section 8, both frameworks,
      `draft_unreviewed`); loader refuses unknown artifacts, interview alone, a control with no
      design objective (AO-1, AO-2); outcomes derived, never stored, beside today's readiness
      under both automation rules with a comparison report and no switch (AO-3); next step per
      unmet objective, Objectives tab on controls, Frameworks > Objectives page, Get Started step
      (AO-4); `objective_decisions` (not applicable with a reason) and `evidence_artifacts`
      (which upload is which record), migration 7e2b4d9c1f53.
- [x] O2 Objectives for every control (2026-11-23, owner: "write all remaining now"): 591 objectives on
      all 133 controls, 338 artifact types, `draft_unreviewed`. Interviews name who is interviewed
      (an owner function). Person evidence counts only once reviewed; rule B is the rule. AO-5
      built; AO-6 enforced by a content test. Still owed: the independent review (D-9: ISO lead
      auditor and SOC 2 CPA), then the owner's sign off on the comparison report before readiness
      switches. Writers' notes on thin evidence (for the reviewer and for new connector
      artifacts): SD-03, SD-11, EP-01, EP-02, EP-03 lack coverage reports; GOV-16, NS-10, IAM-04,
      IAM-10, BC-02, BC-04, BC-05, NS-03, NS-08, LM-05, LM-10 have no design evidence item; DM-06,
      DM-07, DM-13 rest partly on other controls' records.

## Rough size

| Phase | Size |
|---|---|
| 1 Honest Get Started | 3 to 5 days |
| 2 Profile and country picker | 5 to 7 days |
| 3 Frameworks, engagements, scope | 7 to 10 days |
| 4 Ownership and required documents | 7 to 10 days |
| 5 Suggestions, baseline, plan, setup | 10 to 14 days |
| 6 Country panel (build) | 5 to 7 days, review time separate |
| 7 Records, description, existing programmes, SOC 1 | 8 to 12 days |
| 8 AI assists | 3 to 5 days |

About ten to fourteen working weeks of build for one developer, not counting content writing and
outside review. These are estimates made before reading every model in detail. Step 0.3 will move
them.
