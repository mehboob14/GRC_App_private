# Current state

**Last updated: 2026-11-23** by Claude Code (guided onboarding phases 1 to 8, its gaps and assessment objectives wave 1 built, uncommitted; Keycloak SSO by another session, item 8; ISO 27001 was
committed on 2026-11-06 as local c80ae7d and GitLab 33df5e3, so the "uncommitted" notes on ISO below are history).
Alembic head on disk is now `3f6a8c2d7e91`: guided onboarding migrations run to `7e2b4d9c1f53` (objectives), the SSO migration `4b8e1d6a9c27` follows it, then `3f6a8c2d7e91` (scope statement approval), the SSO session's `9c3e5a7b2d14` and `5d2f8a1c7b63`, then `6a1f9d3c8e25` (SOC 2 mapping fixes, D-10). Head `6a1f9d3c8e25`. `REGULATIONS_SHOW_DRAFTS` now defaults on (D-8). Content changed too: 14 new
document templates, evidence guidance in the soc2 and iso27001 packs, and a new sealed `regulations` pack (83 AI drafted
entries, hidden unless `REGULATIONS_SHOW_DRAFTS=true`), so a deploy needs `seed-content` after migrate. Two new settings,
both off by default: `GUIDED_SETUP` (sign up adopts no framework) and `REGULATIONS_SHOW_DRAFTS`.
Guided onboarding progress lives in `openspec/changes/guided-onboarding/tasks.md` (phases 1 to 8 built with listed gaps). `verity_test` and `verity_guide` are at it; the
dev database `verity` is NOT migrated yet: run `alembic upgrade head` on it before starting the dev API. Existing
workspaces get the new Compliance Manager role only after `python -m scripts.backfill_builtin_roles --apply`.
**Verified against:** `feat/phase1-completion` 371f8a7, `origin/main` 4befd08, `gitlab/phase_01` 99cbdd7,
Alembic head `f6c2b8e4a915` (on disk, uncommitted), targeted tests listed under Verification status.

> **SECURITY INCIDENT, found 2026-11-06.** Every GitHub branch (origin main, feat/phase1-completion,
> codex/public-website, feat/website-deploy) had its tip commit rewritten and force pushed with obfuscated JavaScript
> hidden in `frontend/postcss.config.js` and `website/postcss.config.mjs` (runs on any frontend build or dev server).
> Same message and date, timezone +0100. Do NOT pull, build or deploy from origin until it is restored. Clean tips:
> main 4befd08, feat/phase1-completion 371f8a7 (local c80ae7d = ISO commit on top), codex/public-website 7b184ca,
> feat/website-deploy 33df557. Infected commits tagged locally `incident-2026-11-06/*`. GitLab phase_01 (99cbdd7) is
> clean; never run push-gitlab.bat with the default source (origin) until GitHub is clean.
> 2026-11-06: the owner made **GitLab the main version control**. GitLab phase_01 = 33df5e3 ("Added ISO 27001 framework
> and built-in checks"), snapshotted from the clean local c80ae7d. GitHub was left as is (not restored, not pushed).

This file goes stale. Before trusting a line, run the checks in "Verify before trusting". If reality
disagrees, fix this file first and say so in CHANGELOG.md.

## Verify before trusting

```bash
cd /c/Development/Verity_GRC_Platform
git rev-parse --short feat/phase1-completion origin/feat/phase1-completion origin/main gitlab/phase_01
git branch --show-current                       # expect codex/public-website (see WORKFLOW.md, the odd checkout)
python local-context/tools/commit_paths.py candidates     # read only: what is uncommitted and ours
ls backend/src/verity/db/migrations/versions | tail -3    # newest migration; one head only
ls backend/src/verity/seed/content                         # content packs on disk
wsl -d Ubuntu -- pg_lsclusters                  # expect: 16 main 5433 online
```

Whether the server runs a given commit is not knowable from here: ask the owner.

## Where the product stands

| Area | Status |
|---|---|
| Phase 1, core platform on manual data | Built. The owner told the client team it is done (2026-10-06). The 2026-10-03 audit found about 30 open spec clauses; round 2 closed several (list below), the rest are "still open". |
| Phase 2, connectors and automation | 1 of 15 connectors (GitHub: 7 runnable checks of 81 catalogued). Evidence mapping suggestions and a maturity check exist (rule based when no LLM key). No Jira, Slack, alerts, findings workflow, AI document drafting. |
| Phase 3, ERM and more frameworks | ERM tabs are "Soon" screens. **ISO 27001 is built end to end, reviewed by the compliance persona, with templates, built-in checks, guide and site pages (2026-10-19), uncommitted, not deployed.** No SSO, access reviews, CIS, live scanners. |
| Public website, docs portal, user guide | Separate `website/` Next.js app, live at a temporary address, built outside the signed plan (never present it as billable). 2026-10-16: Faheem asked for a security plus compliance revamp, so that new work can be scoped and priced; plan in the `Verity_site` worktree, `openspec/changes/security-compliance-website/` (uncommitted). |

Scope is defined by the signed spec and build plan (`docs/product/*.docx`, never edit them) and
`docs/product/delivery-plan.md`. Phases 2 and 3 are priced separately; anything not in a phase is agreed
before any work starts.

## Branches and remotes (verified 2026-10-11)

| Ref | Tip | Meaning |
|---|---|---|
| `feat/phase1-completion` (local and `origin`) | 371f8a7 | The working line: 24 commits over old main. The server deploys this branch. Not merged to main. |
| `origin/main` | 4befd08 | Moved when the website PR merged. Local `main` (dcf1472) is behind. |
| `codex/public-website` | 7b184ca | **The checked out HEAD of this directory** (website revamp by another tool session). Not where our work goes. |
| `feat/website-deploy` | 33df557 | Website container deploy and demo request page. Checked out (detached) in the worktree `C:\Development\Verity_site` since 2026-10-16; website work happens there. |
| `gitlab/phase_01` | 99cbdd7 | The client's repository. Separate history: snapshots committed by `push-gitlab.bat`. Last: "repo updated". |
| `handoff/verity-dev` (local and `origin`) | see CHANGELOG | Since 2026-11-23: everything on disk (code, specs, agent files, website, notes copy) on top of local `feat/phase1-completion` c80ae7d. GitHub only. Kept current with `commit_paths.py snapshot`. |
| `fe/week1-wiring` | 93c95d3 | Old, ignore. |

Remotes: `origin` is a private GitHub repo, `gitlab` is the client's. Recipes in WORKFLOW.md.

## Uncommitted work in the working tree

1. **ISO 27001 end to end** (built 2026-10-10 and 2026-10-11; verified; the owner has not yet asked to commit):
   - migration `20261010_1000_framework_scope_and_applicability.py` (head `c5d8a2f7e91b`, down `7c3e91d2a8f4`);
   - backend: `compliance/{framework_service,soa_export,tenant_framework_router}.py` (new), changes in
     `control_service`, `engagement_service`, `engagement_router`, `models`, `schemas`, `repository`, `service`,
     `report_service`, plus `seed/loader.py`, `scripts/seal_content.py`, `modules/ai/mapping.py`,
     `modules/iam/service.py`, `core/email.py`, `main.py`, `__init__.py`;
   - content: `seed/content/iso27001/*` (sealed) and ISO ids on the policy templates;
   - tests: `test_iso27001_pack.py`, `test_soa_export.py`, `test_iso27001.py`, `test_frameworks_isolation.py`,
     edits to `test_control_sub_type.py` and `test_leads.py`;
   - frontend: `features/compliance/` (new `frameworks-api.ts`, `use-frameworks.ts`, `add-framework-dialog`,
     `management-system-scope`, `statement-page`; edits to the frameworks, scope, coverage, dashboard, detail and
     control pages), `app/routes.tsx`, `lib/api/{endpoints,types}.ts`;
   - docs: `THIRD_PARTY_NOTICES.md`, `docs/product/iso27001-plan.md` (section 10 = what was built),
     `docs/product/iso27001-draft-crosswalk.csv`, `docs/runbooks/deployment.md`, the tasks file of the
     `common-control-framework` change.
   Added 2026-10-16 to 10-19 (same uncommitted set, see CHANGELOG): migrations `20261016_1100_neutral_control_wording.py`
   (`e3a91c5d7b20`) and `20261016_1200_builtin_verity_checks.py` (`f6c2b8e4a915`, head); `connectors/verity.py` (new) and
   fact methods in assets, vulnerabilities, vendors, risk, documents, tasks, evidence, iam and compliance; the worker job;
   content (soc2 wording and evidence, iso27001 crosswalk and PE-03, automation checks, 15 Verity templates); tests
   `test_verity_checks.py` (unit and integration); frontend connectors, evidence report and template picker; user guide
   chapters 03, 05, 11, 13, README, 7 images and the HTML. Website pages are in the separate worktree
   `C:/Development/verity-website-work` (feat/website-deploy), also uncommitted.
2. **Risk settings popups** (3 frontend files: `risks-settings-page.tsx`, `risk-settings-cards.tsx`,
   `custom-fields-card.tsx`): already on GitLab (commit 33364fb) but not on GitHub's `feat/phase1-completion`.
   Include them in the next GitHub commit so the two histories agree.
3. **Not ours, leave alone:** everything under `website/`, `website-v0-source-2026-10-01.zip`, `AGENTS.md` and
   `README.md` (the Codex guide and edits by another tool), `docs/product/continuous-compliance-plan.md`,
   `docs/product/control-evidence-sufficiency.md`, the `add-public-website` and `revamp-public-website` OpenSpec
   changes. `docs/runbooks/week1-demo.md` exists on the branch but is missing on disk: do not commit the deletion.

4. **Controls library wording** (2026-11-07, 4 frontend files, tsc and eslint clean, not on GitLab): "Criteria" became
   "Requirements" on the controls register, side panel, CSV and report export; requirement chips are capped at 3 with a
   "+N more" button that opens the control on its Requirements tab (`controls-page.tsx`, `control-detail-page.tsx`,
   `controls-bulk-bar.tsx`, `control-report-export.ts`).
5. **Guided onboarding plan** (2026-11-21, documents only, no code): `docs/product/guided-onboarding/` (README, parts 1
   to 5, Appendix A) and `openspec/changes/guided-onboarding/` (proposal, design, tasks). Proposed, not approved. It is
   outside the signed phases; decisions D-1 to D-16 are in its README. Research notes are in
   `grc-s/research_notes/Guided onboarding plan/`.

6. **Guided onboarding phases 1 and 2** (2026-11-21, code, uncommitted, owner said proceed with D-1 to D-3):
   backend `modules/onboarding/` (new: status route, step catalogue, skips), `shared/countries.py`,
   `modules/tenancy/profile_questions.py`, changes in `tenancy` (profile answers, confirm, versions), `compliance/
   engagement_service.py` (`program_figures`), `risk/service.py`, `connectors/service.py`, `main.py`,
   `db/migrations/env.py`, `pyproject.toml` (onboarding import contract), migrations
   `20261121_1000_onboarding_step_skips.py` and `20261121_1100_company_profile_answers.py`; tests
   `tests/integration/test_onboarding_status.py`, `test_company_profile_answers.py`, `tests/isolation/
   test_onboarding_isolation.py`, `test_profile_versions_isolation.py`, `tests/unit/test_profile_questions.py`.
   Frontend `features/onboarding/` (new Get Started), `features/tenancy/profile-questions.tsx` and the profile page,
   `components/ui/country-select.tsx`, `searchable-select.tsx`, `lib/countries.ts`, `lib/api/{types,endpoints}.ts`,
   `app/routes.tsx`, `features/iam/components/team-page.tsx` (`?invite=1`), `scripts/check-countries.ts`; removed
   `features/compliance/components/quick-start-page.tsx`. Docs: `docs/architecture/data-model.md`, the plan folder
   (incl. `phase_out_1.md`, the log of work outside the signed phases) and the OpenSpec change.

7. **Guided onboarding phases 3 to 8** (2026-11-21 and 22, code, uncommitted). New backend: `modules/onboarding/{rules,
   proposals_service,plan_service,assist}.py`, `modules/regulations/` (whole module), `modules/compliance/{assurance_service,
   assurance_router,description_service,scope_service,programme_service,programme_router}.py`, `modules/documents/
   {required_documents,required_service}.py`, `shared/{conditions,countries}.py`, `seed/seal.py`,
   `seed/content/regulations/`, migrations `20261121_1300` to `20261121_1800`. Changed: config (two settings), iam
   sign up, tasks service (`raise_planned`, `existing_keys`, `task_ids_for_keys`), connectors (`connected_keys`),
   documents (approved elsewhere), framework service (SoA versions), seal script, pyproject (regulations contract and
   legs). Tests: `tests/integration/test_{scope_items,programme,ownership_and_required,proposals,baseline_and_plan,
   regulations,assurance,onboarding_assist}.py`, `tests/isolation/test_{scope,phase5}_isolation.py`, `tests/unit/
   test_{owner_functions,onboarding_rules,regulations_pack}.py`. Frontend: `features/onboarding/components/{suggestions,
   baseline,plan,setup,draft-button,...}`, `features/regulations/`, `features/compliance/components/{assurance-page,
   description-page,soc1-guide-page,statement-versions,...}.tsx`, routes, frameworks tabs, required documents.

8. **Keycloak SSO phase A** (2026-11-23, uncommitted): `openspec/changes/add-keycloak-sso/`, `docs/adr/
   0015-keycloak-organizations-for-sso.md`, `docs/runbooks/keycloak-local.md`, `infra/keycloak/`
   (realms, run-local.sh, setup_local.py), backend `core/config.py` (OidcSettings), `core/security.py`
   (sso_selection), `modules/iam/{sso.py,service.py,repository.py,router.py,schemas.py}`, tests
   `tests/unit/test_sso.py`, `tests/integration/test_sso_sign_in.py`, `tests/unit/test_security.py`,
   `tests/unit/test_iam_module.py`; frontend `features/iam/components/{sign-in-page,sso-complete-page}.tsx`,
   `features/iam/auth-kit/auth-bits.tsx`, `lib/auth/auth-provider.tsx`, `lib/api/endpoints.ts`,
   `app/routes.tsx`. Phase B adds migration `20261123_1200_tenant_sso.py`, `tests/integration/
   test_tenant_sso.py`, `tests/isolation/test_sso_isolation.py`, `features/iam/components/
   sso-settings-page.tsx`, `settings-nav.ts`. Phase C adds migration `20261123_1500_tenant_sso_provider.py`,
   `modules/iam/{keycloak_admin,idp_templates,sso_setup}.py`, `tests/unit/test_sso_setup.py`,
   `tests/integration/test_sso_setup_flow.py`, pyproject legs for `iam.sso_setup`. Phase D (lifecycle)
   adds migration `20261123_1800_sso_lifecycle.py` (5d2f8a1c7b63), `modules/iam/sso_sync.py`, changes in
   `core/deps.py` (session epoch), `modules/iam/{models,repository,service,sso,keycloak_admin,sso_setup,
   router,schemas}.py`, `workers/{tasks,celery_app}.py` (hourly `sync_sso_directories`), realm file
   back-channel URL, `tests/integration/test_sso_lifecycle.py`, the SSO page (automatic accounts, groups,
   Sync now). Phases A to D are built; E needs the owner's Entra, Okta and Google test tenants, F needs
   Infowise. Local Keycloak lives outside the repo in `C:\Development\keycloak-local`.

9. **Assessment objectives and onboarding gaps** (2026-11-23, uncommitted): `modules/objectives/` (whole module),
   `seed/content/objectives/` (sealed, draft_unreviewed), migrations `20261123_0900_objective_decisions.py` and
   `20261123_1300_scope_statement_approval.py`; changes in onboarding, compliance (assurance, engagement, scope,
   programme), documents (profile markers, match template, owned counts), evidence, connectors, assets (id filter),
   regulations; frontend `features/objectives/`, control and document pages, controls and assets registers, setup,
   profile, Get Started. Tests: `tests/unit/test_objectives.py`, `test_profile_markers.py`,
   `tests/integration/test_objectives.py`, `test_onboarding_gaps.py`. Later the same day: objectives for all 133
   controls (591), migration `20261123_1900_soc2_mapping_fixes.py`, Openlane rewrites and profile fields in the
   policies pack, `notifications` kind `library_update` (model and frontend type).

10. **Evidence connectors research and plan** (2026-11-23, documents only, no code; on the GitHub handoff branch):
   `docs/product/evidence-connectors/` (README, AUTHORING, 01 evidence model and Go collector architecture, 02
   integration model, 03 market research, 04 phases and work packages, 05 check registry and `checks-proposed.json`,
   06 control changes, 07 control matrix, 08 owner decisions curated and raw, mdm-and-endpoint-strategy, 33 connector
   documents, coverage per family, verification logs, `tools/` generators) and `openspec/changes/evidence-connectors-program/`.
   Findings: 11 control splits and 4 additions proposed (148 controls), 127 new checks, 24 coverage downgrades, only 3%
   of artifact rows fully filled by a check by end of Phase 2 (93% partly), 768 provider facts checked (545 confirmed,
   83 corrected, 136 still unverified with reasons). Defects to fix first: the shared device artifact, the 16 full check
   mappings, GitHub not seeing direct pushes, the vulnerability module before scanners. Next: the 20 gating decisions
   in `08-owner-decisions.md`, then P1 packages. Rule B was already decided (DECISIONS.md); G1 is only its refinement.
   2026-11-24: F4 and F5 planned in detail with build and deployment: `openspec/changes/connector-runtime/`
   (proposal, design, tasks) and `docs/adr/0016-go-collectors-beside-the-python-core.md` (Proposed); decisions R1 to R6.

`commit_paths.py candidates` printed items 1 to 3 when last run; items 4 to 10 are newer.

## Deployed state

Unknown to this file. Last known: the owner was handed deploy sheets for 02c5047 (2026-10-07, result never
reported) and later work (AI evidence suggestions 812cf19, maturity check 54ad3bd, risk settings 371f8a7) was
pushed on 2026-10-08 with no confirmation of a deploy. ISO 27001 is not deployed. The production box is a
shared host that the owner borrowed: never touch it, hand over commands (WORKFLOW.md, "Deploy").

## Local environment (volatile: check, do not assume)

- On 2026-10-11 the owner stopped the WSL keep alive, so Postgres (5433) and Redis (6379) were down. The demo API
  (8111) and demo Vite (5175) were stopped on purpose. Restore steps are in WORKFLOW.md.
- Databases on the WSL cluster: `verity` (dev, real local accounts, never test against it), `verity_test`
  (disposable, tests only), `verity_guide` (demo workspace "Northwind Software Ltd" with SOC 2 and ISO 27001
  added). `verity_test` and `verity_guide` were migrated to `c5d8a2f7e91b` and loaded with the ISO pack. `verity`
  was not touched in the latest session; check it with `alembic current` before using it.
- Port 8001 (the Verity API's usual port) belongs to the owner's other project right now. `vite.config.ts`
  hardcodes the proxy to 8001, so the demo stack runs on 8111 and 5175 with `tools/`.

## Content packs on disk (verified 2026-10-11)

| Pack | Contents |
|---|---|
| `soc2` | 116 control templates, 61 criteria, 167 mappings, each with coverage and a rationale; neutral wording (2026-10-19) |
| `iso27001` | 123 requirements (30 clauses, 93 Annex A), 17 new controls, 300 mappings (47 full, 253 partial) |
| `automation` | 22 capabilities, 93 checks (7 runnable on GitHub, 30 by Verity's built-in checks) |
| `policies` | 30 templates: 15 Openlane Policy Hub (Apache-2.0, attribution kept), 15 written by Verity |
| `risk_library` | 60 risk templates |
| `vendor_profile`, `vendor_questionnaire`, `vendor_tiering` | vendor banks |

Every tenant adopts the full SOC 2 library at signup. Adding ISO 27001 adopts only what it needs and links the
controls already run: a workspace with all 116 SOC 2 controls ends with 133, 111 of 123 ISO requirements answered
by existing controls (104 of them gain ISO links), 12 needing a new one.

## Status by area

| Area | State and gaps |
|---|---|
| tenancy (provider plane) | Built. Provider console and tenant branding built but never checked in a browser. |
| iam | Native auth, TOTP, roles and groups, invitations (including a time boxed guest auditor), verify first signup, rate limits. Admin MFA is off by default (a per tenant switch). The spec's built in roles (Compliance manager, Control owner, Employee, Auditor) and scoping are not built. SSO and the external identity provider are deferred (ADR-0006). |
| audit | Append only log, export to CSV and Excel (Excel capped at 50,000 events). |
| compliance | Frameworks, requirements, controls, engagements per framework, readiness (one definition in `readiness.py`), coverage, dashboards, Statement of Applicability, reports. |
| evidence | Real. Validity and staleness, per check connector evidence, suggestions mapping evidence to controls (a person approves), maturity check, renewal tasks. |
| tasks | Real. SLAs, severity, repeating tasks, attachments, approval for recurring tasks, immutable history. |
| documents | Real. Versions (append only), approval tiers with several assignees, acknowledgement campaigns, review dates and reminders, rich text editor, templates. |
| risk | Real. Registers with their own matrix and taxonomy, library, acceptance with expiry, settings (custom fields, scoring formula, appetite). ERM tabs are "Soon". |
| vendors | Real, the largest module: lifecycle, tiering, questionnaires, vendor portal, findings, promotion to the risk register. |
| assets | Real: CRUD, import, relationships, custom fields. Gaps: owning team picker, watchers. |
| vulnerabilities | Real: definition and instance model, import (XML is refused today), EPSS and KEV enrichment job, SLA, exceptions, remediation plans. |
| connectors | GitHub, plus Verity's built-in checks (provider `verity`, 30 checks over the workspace's own records, always on). Scope selection per connection, one evidence file per check. |
| ai | A client plus mapping suggestions and the maturity check. No LLM key locally, so the rule based path runs. |
| notifications, linkage, links, customfields | Built. `links` and `customfields` are primitives (no router). |
| leads | Public demo request endpoint for the website (provider plane table). |
| approvals | Placeholder package: each module keeps its own approvals. |
| frontend dashboards | `/dashboard` (admin and My Day) show workspace data since 2026-10-04. Get Started is live. |

Phase 1 items closed in round 2 (2026-10-04 to 10-07): audit export, review dates and reminders, acknowledgement
reminders and completion export, trace view (up to four hops), deploy and backup scripts, rate limits, task
severity, repeats and attachments, renewal tasks for stale evidence, live dashboards, provider console and branding.

Phase 1 items still open (from the 2026-10-07 list; re-verify): tenant admin MFA default, the spec's roles and
scoping, retention and legal hold, readiness over time, branded PDF, criteria colouring view and renewal queue,
Change Management and Acceptable Use templates, SIG, CAIQ, ISO and DPA questionnaires, scan ingest (XML refused,
no PDF, no AI parsing), asset form gaps, a backup and restore drill (the script exists), `/metrics`, tests for
evidence and controls, the provider console never opened in a browser.

## Known problems, not fixed

- The app's brand mark is a placeholder that its code comment says is the Vimeo logo (`frontend/src/components/ui/brand-mark.tsx`).
  It shows on the deployed sign in page and vendor portal. Replace with the Verity mark once chosen (website plan, D1), or use
  the comment's one step fallback to the check icon. Owner decides.

- `get_tenant_session` commits after the response is sent: a failed commit can follow a 2xx, and read after
  write can race. Likely fix: `scope="function"` on that dependency. App wide.
- `test_risk_register` compares `date.today()` with UTC and fails between 00:00 and 05:00 local time.
- An unknown `evidence_type` on `POST /evidence/link` escapes as a 500 (a CHECK violation) instead of a typed error.
- Sharing the session between browser tabs (`lib/auth/tab-share.ts`) widens token exposure. The real fix is
  httpOnly cookies (ADR-0006). The trade-off was explained to the owner.
- The 43 control Sub-type values are Verity's own proposal, not confirmed by the client.
- SOC 2 criteria text is verbatim AICPA text (licensing risk to flag).
- ISO 27001 crosswalk: reviewed by Verity's internal compliance persona (2026-10-19), not by an independent qualified
  person (FW-5 still open). Names sit close to official titles (legal review, plan section 9).
- A control shipped into a pack after a workspace added that framework is not adopted (no ISO backfill script).
- The SOC 2 counts on the website worktree stay at 114 and 150 until its backend copy carries the 116 pack
  (`tests/catalog.test.ts` reads that copy); the policy count there says 15 for the same reason.
- The repo's `AGENTS.md` (Codex guide) is stale in two places: it says the two dashboards are hard coded
  (live since bbdbde5, 2026-10-04) and that SOC 2 is the only shipped framework (ISO 27001 now exists locally).

## Verification status

- Last full backend run: 1566 passed (54 minutes) on 2026-10-06, before the AI evidence, risk settings and ISO work.
  Not rerun since. The owner should run it before the next deploy (WORKFLOW.md, "Tests").
- 2026-10-10 and 11: 11 ISO integration and isolation tests passed; an earlier SOC 2 regression group (151 tests)
  passed; 1140 unit tests passed (2026-10-11); ruff, mypy, import-linter (19 contracts kept), `tsc` and ESLint clean.
- ISO screens were checked in headless Chrome against a real database: add dialog, scope, Statement of
  Applicability and its decision dialog, both dashboards, controls list, control detail.
- 2026-10-19: ruff, mypy, import-linter (19 kept), tsc and ESLint clean; 344 related unit tests, then 210 content and
  check unit tests passed; migrations up, down, up on verity_test with a tenant round trip; built-in run on the demo database
  (118 records, 26 passed, 134 failed); integration: test_verity_checks, test_iso27001, test_control_sub_type and
  test_connectors_routes 27 passed after the second review, and earlier the same session test_document_campaigns and
  test_assets_vulns_routes passed; website npm test 22 passed. The full suite was not run (about an hour): the owner
  should run it before the next deploy.

## Suggested next steps (the owner decides; each needs a go)

1. Commit the ISO work and the risk popups to `feat/phase1-completion` with `commit_paths.py`, push to GitHub, then to
   GitLab with `C:\Development\push-gitlab.bat "message"` (it snapshots `origin/feat/phase1-completion`, so push
   GitHub first).
2. Hand over the server deploy sheet: in tmux on the server, `git fetch origin && git checkout feat/phase1-completion
   && git pull && bash infra/scripts/deploy.sh`. It backs up, builds, migrates, swaps, loads content. ISO needs
   no backfill. Ask the owner to run the full suite first, in the background.
3. Answer the Open items in DECISIONS.md (acknowledgement population, SLA anchor, ISO on which plans, FW-5 reviewer).
4. Commit the website worktree pages on `feat/website-deploy` and redeploy the site after the platform.
5. Then: an ISO backfill for controls shipped after a workspace added it.
7. Guided onboarding: phases 1 to 8 built (2026-11-22), gaps listed per task in `tasks.md`. Owner answers still owed:
   D-4 (AICPA text), D-5 (Openlane rewrites, staged), D-8 (legal review of the country pack; until then it is hidden in
   production), D-9, D-10, D-13 (website prefill, not built). Run the full backend suite once in the background before
   committing (only targeted tests were run). History of this item below.
   Earlier: phases 1 and 2 built, phase 3 started (audit details and auditor step), D-12 built (Compliance
   Manager role). D-6 decided and checked: shared scope items, in or out decided per framework (SC-0, design 2.3).
   Phase 3.6 core built (shared scope items, decisions per framework). Next: suggestions from records (3.3),
   commitments and vendors that count, milestones and engagement history. Leftovers of
   phase 2: prefill (2.6), document variables (2.7, do with phase 4), assign a section (2.8). Country content: first
   tier rechecked against official texts; three small points and a full human review remain before anything ships (D-8).
   The demo workspace on `verity_guide` now holds two sample scope items (Staging environment, Northwind platform).
6. Before any Go connector: the assessment model (objectives, artifacts, shadow readiness), phases 0 to 3 of the
   2026-10-30 report in `grc-s/reports/Framework independent assessment model.md`; then the first IdP collector in Go.
