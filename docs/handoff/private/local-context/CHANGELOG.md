# Changelog (newest first)

The running record that replaces chat history. Add an entry at the top at the end of every session: date, tool, what
changed, what was verified, commits if any. Keep entries short. Entries before 2026-10-11 were reconstructed from git
history and the owner's notes; commit hashes are real, dates are the days the work landed.

## 2026-11-23, handoff branch (Claude Code)
- Owner moving machines: new GitHub branch `handoff/verity-dev` from the clean local c80ae7d with
  everything on disk: SSO (85bfb5e), guided onboarding and objectives (49caea2), website sources and
  specs (5ba06dc), AGENTS/README and other tools' product notes (a44b181), then the handoff guide
  `docs/handoff/README.md` and a scrubbed notes copy in `docs/handoff/private/` (local-context without
  session tokens, TOTP seed or browser profile; entry shims; the assistant's project memory;
  push-gitlab.bat). Pushed to GitHub only (the tip hash is in the session report; verify clones
  against it). GitLab untouched. Zip of the private notes copied to OneDrive.
- `tools/commit_paths.py` gained `snapshot` and `refresh-notes` for the handoff branch, handles
  deletions, and keeps `docs/handoff/` off `feat/phase1-completion`.
- Owner's standing rule: keep specs current and push each piece of work to `handoff/verity-dev`.

## 2026-11-23, late night (Claude Code)
- Provider guide `docs/runbooks/sso-providers.md` (contract scope per spec 3.2: Entra ID and Google
  Workspace sign in; Okta and SAML extra), phase E broken into E.0 to E.8 in tasks.md. Found: the
  owner's Keycloak build's SCIM server has no organizations, so SCIM users and groups land in the realm
  (E.3 plans the sync change). Production guide `docs/runbooks/keycloak-production.md` (what
  Infowise configures, Verity settings, smoke test, customer onboarding, mode A or B) and an OIDC
  block in `.env.production.example` (off by default). Nothing built, nothing committed.

## 2026-11-23, night (Claude Code)
- Keycloak SSO phase D, lifecycle (uncommitted): migration 5d2f8a1c7b63 (`users.sessions_revoked_at`,
  `role_assignments.source`, `tenant_sso.synced_at`, `sso_group_roles` with RLS). Accounts on first SSO
  sign in with a required, never Admin, default role; Keycloak organization groups give roles; directory
  sync (`modules/iam/sso_sync.py`, hourly worker job, Sync now) disables leavers, keeps the last Admin,
  fails closed; back-channel logout ends a person's sessions.
- Verified: unit suite 1248 passed; SSO integration, isolation and RLS coverage 17 passed plus 3 new
  lifecycle tests, on verity_test; ruff, mypy, import contracts (22 kept), tsc, eslint clean. Browser and
  worker on the demo stack with the local Keycloak, end to end (tasks.md, phase D notes). The demo
  database now holds a disabled `alice@northwind.example` in Northwind.
- The onboarding session's migration 6a1f9d3c8e25 now follows mine.

## 2026-11-23, guided onboarding (Claude Code)
- Owner answered every open decision by click (DECISIONS.md). Applied: D-5 Openlane rewrites shipped as drafts, D-10
  13 mapping fixes (migration 6a1f9d3c8e25 with audit rows and a library update notice), D-8 law entries shown with a
  disclaimer, profile fields in five templates, objectives for all 133 controls, reviewed-only evidence, interviewees.
- Assessment objectives wave 1 end to end (both frameworks): sealed pack of 163 objectives and 119 artifacts on the
  35 first month controls (own words, draft_unreviewed), outcome engine beside today's readiness under both
  automation rules, comparison report (no switch), Objectives tab, Frameworks > Objectives page, Type 1 and Stage 1
  views, Get Started step, not applicable with a reason, evidence tagged to records.
- Every buildable guided onboarding gap closed (tasks.md items dated 2026-11-23).
- The Keycloak session works in the same checkout and tests on `verity_test`; I tested on a private copy,
  `verity_test_ob` (GOTCHAS). Its migration `4b8e1d6a9c27` builds on mine; my `3f6a8c2d7e91` follows it.
  Nothing committed.

## 2026-11-23, evening (Claude Code)
- Keycloak SSO phase C (uncommitted): migration 9c3e5a7b2d14 (after 3f6a8c2d7e91), `modules/iam/
  {keycloak_admin,idp_templates,sso_setup}.py`, DNS TXT domain proof (DNS over HTTPS, no new
  dependency), Connect popup for Entra ID, Okta, Google Workspace, OIDC, SAML, Keycloak kept in step
  with the switches, containment of workspace providers via the `identity_provider` claim, relink of a
  re-created provider account. Phase B fix: routing and cross-workspace uniqueness use proven domains.
- Verified in the browser: Verity created `northwind-oidc` in Keycloak from the page, and the next sign
  in went through it. This Keycloak build needs the `kc-admin-api` default scope on `verity-admin`
  (setup_local.py adds it).

## 2026-11-23, afternoon (Claude Code)
- Keycloak SSO phase B (uncommitted): `tenant_sso` (migration 4b8e1d6a9c27, after the objectives
  migration 7e2b4d9c1f53; another session has since chained 3f6a8c2d7e91 after it, so keep the id),
  forced RLS plus a provider-plane SELECT policy. Domain routing to `organization:<alias>`, the
  organization claim picks the workspace, SSO workspace choice held in Redis, first sign in through the
  organization stamps `verified_at`, enforcement with Admin plus TOTP break glass. Settings, Security,
  SSO page (tab no longer "Soon").
- Verified in the browser on the demo stack: set Northwind's SSO, sign in through Keycloak stamped the
  proof, Require SSO switched on. `verity_guide` migrated to head (this also applied the objectives
  migration, which fixes the Get Started error seen this morning).

## 2026-11-23 (Claude Code)
- Keycloak SSO, phase A (uncommitted): OpenSpec `add-keycloak-sso` (phases A to F), ADR-0015 (Keycloak
  organization per tenant, Verity keeps its own session, IdP does MFA, lifecycle read from Keycloak).
- Local Keycloak = the owner's source build unpacked to `C:\Development\keycloak-local`, port 8180
  (management 9180), started by `infra/keycloak/run-local.sh`, finished by `infra/keycloak/setup_local.py`.
  Realm `verity` (client verity-web, service account verity-admin, org northwind) and realm
  `northwind-corp` (stand-in customer IdP). Runbook `docs/runbooks/keycloak-local.md`.
- Backend: `OIDC_*` settings (off by default), `modules/iam/sso.py`, `IamAuthService.sso_sign_in`,
  routes `/auth/sso/{status,start,callback,complete,end-session}`, `sso_selection` token type,
  `IdentityRepository` (first use of `user_identities`). Frontend: live SSO button, `/sso/complete`,
  sign out through Keycloak.
- Verified end to end in the browser on the demo stack and by tests (see the change's tasks.md).
  Nothing committed. Seen in passing: Get Started on `verity_guide` fails because new objectives code
  reads `evidence_artifacts`, which that database does not have (not from this change).

## 2026-11-22, early (Claude Code)
- Guided onboarding phases 3 to 8 finished (uncommitted): suggestions from the profile with accept, reject and review
  (decisions only stored), baseline, readiness snapshot, work plan raised as tasks once, evidence requests, connection
  suggestions, SoA versions, guided setup flow with Help me choose, sign up behind `GUIDED_SETUP`; country panel
  (`modules/regulations`, 83 drafted entries, hidden until reviewed); audits, findings as tasks, description inputs,
  documents approved outside Verity, SOC 1 guide, check and audit steps; AI drafts with offline templates.
- Migrations 5d1e7c3b9a24, 8a4f2c6e1b37, 2c7d9e4f6a18 (up, down, up on verity_test). `verity_guide` migrated and
  seeded; its demo profile now has answers (AE, SA, no offices, Okta, AWS).
- Fixed in passing: Required documents compared SOC 2 categories in the wrong case (Privacy and Processing Integrity
  rows never showed). Seal check split into `verity.seed.seal`.
- Verified: targeted integration, isolation and unit tests per phase (see tasks.md), RLS coverage, import contracts 21
  kept, ruff, mypy, tsc, eslint; screenshots of suggestions, setup, audits, laws and Get Started on the demo. Full
  suite not run. Nothing committed.

## 2026-11-21, night (Claude Code)
- Phase 3.6 core: migration af53b58da5b3 (`scope_items` shared, `scope_decisions` per engagement, forced RLS, no
  DELETE), `compliance/scope_service.py`, `/engagement/scope-items` routes, "What is in scope" on both scope pages,
  notices for a change inside a SOC 2 period or to a certified ISO scope. 4 integration and 2 isolation tests pass.
- Country catalogue fixed: eight corrections applied, OM-01 rewritten for RD 68/2026, SA-05, PK-07, AE-02 and US-15
  checked against official texts (notes in `grc-s/research_notes/Guided onboarding plan/`).
- Seen on the demo workspace (two sample scope items added there). Nothing committed.

## 2026-11-21, late (Claude Code)
- Owner said yes to D-6 (shared scope, if both frameworks allow it) and D-12 (a role to run the programme), and to fix
  the items that were not solid.
- D-6 checked against AICPA and ISO/accreditation sources: allowed with conditions. In or out is decided per item per
  framework; each framework keeps its own statement; a change to a shared item asks per framework. Rules in SC-0 and
  design 2.3 (`scope_items` shared, `scope_decisions` per engagement). Notes: `shared_scope_check.md`.
- D-12 built: built in role Compliance Manager (programme keys only; no invites, roles, groups, security, profile or
  management approvals, since an invite can hand out Admin and `tenant:manage` also sets the mail server). Unit and
  integration tests. Existing workspaces need `scripts.backfill_builtin_roles --apply`.
- Phase 3 started: migration 6b8df681a7aa (Type 1 as of date, target date, driver, go live date, auditor state,
  accreditation body, contact, letter date). Saves keep fields they do not send, so SOC 2 can now hold a scope
  statement and an audit firm. Audit details card on both scope pages; Get Started gains "Name your auditor".
- ISO points confirmed from accreditation body sources and part 1 updated (SoA version on the certificate, 27006-1
  8.2.2; audit time Annex C and D; internal audit and management review before certification, 27006-1 9.5.2).
- Verified: tests listed in tasks.md, migrations up/down/up, tsc, eslint, the card on the demo workspace. Not run:
  the full suite. Nothing committed.

## 2026-11-21, evening (Claude Code)
- Owner said proceed with D-1 (log out of scope work in `docs/product/guided-onboarding/phase_out_1.md` to price or
  share separately), D-2 (ISO without SOC 2) and D-3 (SOC 1 guidance only), and to keep the OpenSpec change current.
- Phase 1 built: `GET /onboarding/status` (needs only `tenant:read`; steps the role cannot read come back
  not_permitted), step catalogue `modules/onboarding/steps.py`, skip and reopen with a reason (table
  `onboarding_step_skips`, migration b9935aa647b2), `engagement_service.program_figures`, new Get Started page with
  framework chips, Next card, phases, a lane per framework and four separate figures per framework. The four old
  defects are fixed. No observation period step: a Type 2 cannot be saved without dates.
- Phase 2 core built: typed company profile (33 questions, 16 key, one catalogue that validates and drives the form),
  confirm and frozen versions (migration 3b03e4d1a72c, `company_profile_versions` append only), country picker with
  249 countries, regions, aliases and spelling tolerance. Not built: prefill, document variables, assign a section.
- Research: ISO facts checked against sources and part 1 corrected (IAF replaced by Global Accreditation
  Cooperation from 2026-01-01; PNAC and GAC not recognised for ISO 27001; no maximum Stage 1 to Stage 2 gap in the
  standard). 26 first tier country entries source checked: 17 confirmed, 8 corrected, 1 not confirmed, 4 must not
  ship yet. Notes in `grc-s/research_notes/Guided onboarding plan/`.
- Verified: 5 status, 6 profile, 2 + 4 isolation, 14 unit tests, RLS coverage, route permission unit test, import
  contracts (20 kept), ruff, mypy, tsc, eslint, migrations up/down/up on verity_test, both pages on the demo
  workspace in headless Chrome. Not run: the full backend suite. `verity_guide` migrated to 3b03e4d1a72c; dev `verity`
  not migrated. Nothing committed or pushed.

## 2026-11-21 (Claude Code)
- Planning only, no product code: guided onboarding for SOC 2 and ISO 27001. Wrote `docs/product/guided-onboarding/`
  (README with decisions D-1 to D-16; 01 official journey and who does what; 02 requirements with acceptance, profile
  questions and the 25 step Get Started catalogue; 03 screens, country picker, navigation map; 04 country reference
  panel; 05 control library and objectives; Appendix A, 54 required documents) and
  `openspec/changes/guided-onboarding/` (proposal, design, tasks in 8 phases). Proposed, not approved, uncommitted.
- Inputs: code read of today's onboarding (Get Started is SOC 2 only with four defects), SOC research with primary
  sources, competitor help centres, an 89 entry country catalogue draft (mostly search summaries, not shippable), and
  the compliance persona's review (new findings LD-01 to LD-23: seven Openlane templates follow ISO 27001:2013 wording;
  nine criteria read met on one partial control). The ISO 27001 process research failed on a network error, so part 1's
  ISO section is from knowledge and needs a lead auditor's read. Notes: `grc-s/research_notes/Guided onboarding plan/`.
- Not verified: nothing was run. Sizes in tasks.md are estimates made before reading every model.

## 2026-11-07 (Claude Code)
- Controls library, frontend only, uncommitted: "Criteria" renamed "Requirements" (register column, column picker, side
  panel, CSV, report export), requirement chips capped at 3 with "+N more" opening the control's Requirements tab.
  tsc (`-p tsconfig.app.json`) and eslint clean; no tests run. Also wrote `grc-s/call-prep/run-on-windows.md`.

## 2026-11-06, later (Claude Code)
- Committed the ISO 27001 and built-in checks work locally as c80ae7d on feat/phase1-completion (108 files, mehboob14,
  "Added ISO 27001 framework and built-in checks"); not pushed. The GitHub push was rejected and revealed the force
  pushed malware on every GitHub branch (see STATE.md). Owner informed, then chose GitLab as the main version control:
  pushed to GitLab phase_01 as 33df5e3 from the clean local branch (payload scan clean, nothing removed). GitHub untouched.

## 2026-11-06 (Claude Code)
- Call prep for 2026-11-07 (no product code changed). Demo workspace "Northwind Software Ltd" on verity_guide, login
  demo-call@northwind.example (session `tools/demo_session.call.json`, TOTP secret `tools/demo_call_totp.json`, local demo
  only): SOC 2 Type II plus ISO 27001, scope, 7 SoA decisions, LM-01 / BC-07 / IAM-07 / DM-06 worked; "Legacy reporting
  server" left unowned so LM-01 fails and A.5.9 flips partly to met when fixed live (rehearsed, then restored). Pack in
  `grc-s/call-prep/`: demo-script.md, demo-code.py, demo-reset.py, deployment-options.md, screens/. Deck (private):
  https://claude.ai/artifact/HQHgc3zNhcYZRNWK42fHst
- Deployment brief findings: only Docker Compose is supported; S3 storage driver is a stub (evidence on local disk);
  LEADS_NOTIFY_EMAIL and .env.production.example default to the owner's mailbox and current server; runbook nginx block
  lacks client_max_body_size (uploads over 1 MB fail); deploy.sh assumes the shared host's edge container and always
  builds; backup.sh skips the env file (APP_ENCRYPTION_KEY); pg_dump as owner fails on managed Postgres (FORCE RLS).

## 2026-10-30 (Claude Code)
- Research only, no code: framework-independent assessment model (objectives per control, methods examine/interview/
  observe/test, artifact catalogue, many sources per artifact) ahead of the Go connectors Faheem asked for. Report:
  `C:/Users/HP/OneDrive/Desktop/Platform/grc-s/reports/Framework independent assessment model.md`, notes beside it in
  `research_notes/`. Key facts: no competitor ships structured objectives (Vanta's common-control layer is only in
  preview); NIST 800-53A/171A text is public domain; SCF may ship only verbatim (no rewording, even by AI); AICPA, ISO and
  PCI text may not ship. Owner decisions listed in the report (automation Option A or B, pending evidence, AICPA text,
  objective reviewer, first Go provider).

## 2026-10-19 (Claude Code)
- Closed the ISO 27001 open items (uncommitted, nothing pushed, not deployed). Reviewer persona added:
  `local-context/agents/compliance-auditor.md` (ISO 27001 lead auditor, PCI DSS QSA, SOC 2, banking, on premises).
- Crosswalk: the persona reviewed all mappings in six chunks, a critic merged them; 300 confirmed fixes applied (288 by
  script, 12 by hand). Pack now 300 mappings (47 full, 253 partial), 17 new controls (PE-03 added: environment and
  equipment protection at own sites, payment device inspection in step 3), 10 evidence lists widened. A.5.34 keeps 7
  controls as a reviewed exception in `test_iso27001_pack.py`.
- Library wording: data migration `e3a91c5d7b20` rewrites 60 shipped controls (neutral wording plus the review's
  corrections); a workspace's edited copy is kept. Proven up, down, up on verity_test, with a round trip (edited GOV-02 kept).
- Templates: 15 written by Verity (30 total), including the Operating Procedure Template; reviewed by the persona.
- Built-in checks: provider `verity` in the connectors machinery, 30 checks over the workspace's own records, always on,
  hourly scheduler creates the connection, one evidence file per check (only the records it judged). Migration
  `f6c2b8e4a915` (connection CHECKs). Readiness never counts Verity's own reports as evidence.
- Code review (engineer plus persona): 20 confirmed findings fixed, among them: acknowledgement of the code of conduct and
  AUP judged over all staff minus guest auditors; republishing no longer makes old recipients late; acknowledgements and
  disposal records audited; documents.controlled uses the 12 month approval rule; DPA needs the signed copy; undated
  evidence counts 12 months for the check; a severity raised on re-import shortens open findings' SLA (never lengthens,
  audited); not applicable controls do not mitigate risks; a blocked task's plain due date still runs out; evidence
  files bounded and too-large files skipped; one tenant's failure no longer stops the hourly job; control pages cap
  results at 200 with "first N of M"; built-in evidence opens as a report.
- Docs: user guide chapters 03, 05, 11, 13 and README, 7 new screenshots (taken on a second demo workspace in
  verity_guide, session in `tools/demo_session.shots.json`), one page HTML rebuilt. Website pages in the
  `C:/Development/verity-website-work` worktree (feat/website-deploy), uncommitted; npm test 22 passed.
- Second review pass (engineer, frontend engineer, compliance persona, each with an adversarial verifier): 22 confirmed,
  19 fixed: a resurfaced finding's clock runs from its return; guest auditors are found by an engagement scoped or
  time boxed role; the controls report ignores Verity's reports; one failing connection no longer stops the others;
  capped results keep every plan limited row; list keys; "Verity" as the evidence origin; the audit and review
  checks ignore policy or procedure documents; DPA check judges vendors in use (and says "a copy", not "signed");
  GOV-13 renamed Internal audit; GOV-20 asks for the owner's approval as an upload; IAM-07 and PE-03 record what they
  ask for; operating procedure template routes A.5.37 through GOV-28; check, guide and site wording made literal.
  Three left for the owner (DECISIONS.md, Open).
- Verified: ruff, mypy, import-linter 19 kept, tsc, ESLint; unit 210 (content and checks) plus 344 related; website
  npm test 22; migrations up, down, up twice on verity_test; integration: see STATE.md, Verification status.

## 2026-10-18 (Claude Code)
- Website plan extended: the owner wants an original design. The previous change followed Harness element by element
  (header, menu, hero, isometric cubes, number strip, sections, motion, docs) and the website's cube logo was drawn to match;
  design.md section 6 now lists each borrowed element and its replacement. Published a direction board (phase 0 draft):
  https://claude.ai/artifact/B1JiEhCzntkdEe5jXWHdMf (three mark concepts, the guardian, five tones, type, homepage order).
- Found: the app's brand mark (`frontend/src/components/ui/brand-mark.tsx`, since c7a93c9 on 2026-08-18) is a placeholder
  that its own comment says is the Vimeo logo; it shows on the sign in page, sidebar, provider screens and vendor portal of
  the deployed app. Flagged to the owner; not changed.

## 2026-10-16 (Claude Code)
- Website: ran the latest site (`feat/website-deploy`, 33df557) locally from a separate worktree,
  `C:\Development\Verity_site` (own `npm ci`; the main checkout's `website/` is Codex's older copy and was not touched).
  Start it with preview `verity-site` (port 3001, entry in `grc-s/.claude/launch.json`).
- Planned the security plus compliance website revamp Faheem asked for (Oneleet as reference): OpenSpec change
  `openspec/changes/security-compliance-website/` in that worktree (proposal, design, tasks, spec delta). Owner decisions:
  Managed service planned not staffed (show Coming soon), partner products inside the offer, pricing model without numbers,
  mascot = cube guardian. Site audit findings recorded in design.md. Uncommitted, nothing pushed, no code changed.

## 2026-10-11 (Claude Code)
- Finished ISO 27001 verification. Found and fixed a bug the tests caught: adding ISO to a workspace that already had controls
  inserted duplicate control to requirement links (`link_framework` read before adoption was flushed; it now flushes first).
  Statement of Applicability "partly" now counts started work (in progress or implemented) so implemented controls without
  evidence no longer read "Not started". Control detail shows framework logos instead of "ISO2". 11 ISO tests, unit (1140),
  ruff, mypy, import-linter, tsc, eslint all green. Screens checked in headless Chrome.
- Wrote `docs/product/iso27001-plan.md` section 10 (what was built, numbers, what is open).
- Created this local context pack (`local-context/`, excluded from git) and the entry files that point to it.
- The owner stopped the WSL keep alive: local Postgres and Redis are down until restarted. Demo servers stopped.
- Uncommitted: the whole ISO build and three risk settings popup files. Nothing pushed.

## 2026-10-10 (Claude Code)
- Planned ISO 27001 (`docs/product/iso27001-plan.md`, draft crosswalk CSV), following Probo for identifiers only; then built it
  end to end on the one control library at the owner's request: migration `c5d8a2f7e91b` (`scope_model`, `position`,
  `tenant_frameworks`, `requirement_applicability`, engagement per framework), sealed `iso27001` pack (123 requirements, 16 new
  controls, 242 mappings), framework service and Statement of Applicability with XLSX export, overlap preview, per framework
  dashboards and coverage, Frameworks UI (list with Add dialog, switcher, Scope, Applicability, decision dialog). Three
  subagents authored the content in parallel; scripts validated it.

## 2026-10-08 (Claude Code)
- Evidence AI: suggested controls with requirements and maturity, a check on upload (812cf19, 54ad3bd). Risk settings live: custom
  fields, scoring formula, appetite (371f8a7, migration `7c3e91d2a8f4`); settings page later redesigned as popups (on GitLab as
  33364fb, not on GitHub). Client GitLab handover: remote `gitlab`, branch `phase_01`, `push-gitlab.bat`, AI tooling folders removed.

## 2026-10-07 (Claude Code)
- Evidence per check (one file per check, linked only to its controls) and navigation that remembers where you were (02c5047);
  connector results readable on the control, plan limits said once (b9716ea). Full backend suite: 1566 passed in 54 minutes.

## 2026-10-06 (Claude Code)
- Round 2: audit export (CSV, Excel), review dates and reminders, acknowledgement reminders, trace view, `deploy.sh` and `backup.sh`,
  demo requests endpoint for the website, dashboard coverage bars, deploy proxy reload fix. The owner told the client team Phase 1 is
  done; the website went live at a temporary address (`feat/website-deploy`).

## 2026-10-04 (Claude Code)
- Evidence composition (evidence kinds, Checks tab, criterion chain), provider console and tenant branding, rate limits, task
  severity, repeats, attachments and renewal tasks, live dashboards, the Phase 1 completion plan. Worker evidence volume and
  proxy address fixes found while writing the deploy sheet.

## 2026-10-03 (Claude Code)
- Spec gap audit against the signed spec (Phase 1 not sign off clean, about 30 open clauses). GitHub accuracy pass: scoped
  repositories, honest statuses, readiness defined once, 14 SOC 2 mappings corrected.

## 2026-10-02 (another tool session)
- Website revamp on `codex/public-website` (design system, homepage, docs portal); three of its commits are authored "Claude", against
  the `mehboob14` rule, so they never go to the client's repo. The checkout's HEAD has stayed on that branch since.

## 2026-09-24 to 09-29
- GitHub connector (8301042), cross module linked records, custom fields (77ee629), user guide with 43 screenshots (61929d1),
  commit attribution rule, GitLab handover preparation.

## 2026-09-14 to 09-19
- Risk register built (2026-09-14); the owner's local workspaces were wiped by an integration test run against the dev database
  (hence `verity_test`); module header pattern; common control framework spec and ADR-0014 (09-18); GitHub connector built (09-19).

## 2026-09-02 to 09-13
- Error handling pass (reader copy for 180 backend errors, `describeError`, error boundary), UI consistency primitives, assets and
  documents wired to the real backend, document approval tiers rebuilt (multi assignee), vulnerabilities module, vendors module
  (the largest) through 09-13.

## 2026-08-17 to 08-31
- Full SOC 2 library adopted by every workspace; control codes by domain; control content rewritten; runbooks; first production
  deploy (2026-08-24); evidence mapping suggestions and acknowledgement campaigns (08-31); documents module.

## 2026-08-12 to 08-16
- Foundation and Week 1: backend core, RLS, audit, tenancy (provider plane), iam (native auth, TOTP, RBAC, memberships), Verity
  design system, verify first signup. First commit in this repo: 2026-08-12 (`f0cc207`).

## Before 2026-08-12
- The older prototype in `grc-s` (June to August 2026) and a reskin to the client's design (2026-08-08) led to the decision to
  rebuild as Verity from scratch with a stricter architecture.
