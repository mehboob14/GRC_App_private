---
name: verity-vendors-module
description: Week-5 third-party risk (TPRM) module in Verity — backend sections 0-4 and the section-5 interface, with the local quirks needed to run and verify it
metadata:
  type: project
---

Verity's vendors module (`backend/src/verity/modules/vendors/`, `frontend/src/features/vendors/`)
is the third-party risk product, driven by `openspec/changes/week5-vendor-risk/`.
Sections 0-5 are built and committed; section 6 (close) is open as of 2026-09-10.

**Why:** it is the largest module in the platform — 28 models, 35 routes, ~20
frontend components — and its design decisions are not derivable from the code
alone.

**How to apply:**

- `design.md` §1 is the single build reference: all 26 ER tables transcribed
  verbatim plus a deviation register. Every rename or structural departure is
  recorded there, not in commit messages.
- `ExitCheck.satisfied` is three-valued. `null` means the module answering it is
  not built yet — never a tick, never a blocker. Rendering `!satisfied` as a
  cross shows phantom blockers on every vendor.
- The lifecycle plans twelve `not_started` stage rows at tiering time. Nothing
  is ever `in_progress` until an advance happens, so "the current stage" is the
  first row that is neither complete nor skipped, not the one marked in progress.
- `approval.decided` is a blocker on the approval gate that only the decision
  itself clears. Anything keying "can I decide" off the raw blocker list
  deadlocks the gate.
- Stage transitions are keyed on `stage_id`, not `engagement_id`.
- `portal_url` is returned exactly once; the row stores a hash.
- Promotion to the risk register is built (`POST /risks/from-vendor-finding`).

**Running it locally on this machine** (see also [[verity-grc-platform]]):
Postgres is in WSL on **5433**, credentials `verity_app:verity_app` (app) and
`verity_owner:verity_owner` (migrations); Redis must be started or the rate
limiter fails closed. WSL2 localhost forwarding goes cold — hold it open with a
long-lived `wsl -e bash -lc 'sleep 3600'` in the background before connecting.
Backend on 8001, vite on 5173 (`.claude/launch.json` name is `verity-main`).
Tables have FORCE RLS, so even the owner role sees nothing without
`app.tenant_id` set — write through `core.db.session_scope(tenant_id)`.
Running integration pytest truncates users and tenants on whatever DB it points at; on 2026-09-14 that wiped the user's own workspace. Always `source /tmp/venv_test.sh` (verity_test) first, see [[verity-tests-wipe-database]].

**Before assuming you broke something:** as of 2026-09-10 the full backend suite is
40 failed / 637 passed, and all 40 are pre-existing in `test_provider_auth.py`,
`test_provider_tenants.py`, `test_iam_management.py` and one stale password-policy
unit test. They reproduce standalone and touch nothing in vendors. `make check`
and `tests/isolation/` (55 tests) are both green — those are the two gates worth
trusting. The local venv holds exactly what `uv.lock` pins, so a local `make check`
failure is a real CI failure, not a tooling difference.

**UI decisions from the user's 2026-09-13 review** (commits 6d79a6e, 663e159):
- The user rejects visible dashes of any kind as "AI-looking": no em/en dashes in
  copy, no lone dash placeholders (use None / Not set / No date), no dashed or
  fence-rule borders, no strikethrough. Applies platform-wide.
- They want less text, one-screen views and popups over inline forms. Tiering is a
  stepped Dialog; the Lifecycle tab is a full-width workspace with a left stage
  sub-nav (Assess / Decide / Operate), tier summary inside the Tiering stage and
  the approval decision inside the gate.
- Tier colour is one solid severity ramp (`components/tier-tone.ts`, `TierBadge`),
  low is slate. The old status-family mapping gave Medium a violet they disliked.
- `awaiting_gate` is labelled "In review": it means tiered and not yet approved.

**Seeing the UI at desktop size:** the in-app Browser pane is ~380px wide and
emulating 1440px scales the screenshot to illegible. Drive headless Chrome over
CDP instead with `memory/cdp_shot.py` (backend venv has `websockets` and `httpx`):
a JSON step list of login / goto / eval / wait / shot, then Read the PNG.
The demo tenant is wiped whenever integration tests run; re-run
`backend/scripts/week5_vendor_demo.py` for fresh credentials.


**Questionnaires (2026-09-14, commit 9327d4e + frontend follow-up):** tiering and due
diligence are both tenant-built (`vendor_questionnaires`, `vendor_questionnaire_questions`,
`questionnaires.py`, ADR-0013). Tiering = our team answers about the vendor, sets the
tier; due diligence = vendor answers in the portal, sets residual + findings. Library on
the global plane (`vendor_tiering`, `vendor_profile`, `vendor_questionnaire` packs);
defaults provisioned once per purpose on first list/create. Runs and dispatches store
snapshots, so edits never rewrite history; `answers_with_questions` returns
`AskedQuestion` for bank and snapshot rows alike. Five-factor tiering bodies still
accepted by the API. UI: Vendors > Questionnaires tab, builder at
`/vendors/questionnaires/:id` (drawer editor, library picker, preview, settings).

**Hardening before the 2026-09-24 client review (2026-09-22, committed 5613e5b on 2026-09-24):** stage moves only on
the current stage (`lifecycle.current_stage`, `_require_current`); latest gate decision wins;
approve refused over open critical-or-blocking findings (engagement + vendor-wide) or open earlier
stages; retier before the gate rewinds to re-opened work; reassessment date shifts by cadence
difference, new cycle only after the gate; offboarding once, revokes portal tokens, checklist UI;
`_rolled_up_status` reads vendor-level exit records (reading its own cached status made one
engagement's exit stick). Integration tests for these live in the vendor suites; the walkthrough
script is scratchpad `vendor_walk.py`. Prep guide for the review is the "Vendor Risk Playbook"
artifact. Known gaps: manual signals, policy settings UI, manual findings, document files, SLA entry.

**Phase-1 gaps closed (2026-09-23, committed 5613e5b on 2026-09-24):** migration `8a1f4c26d05b` adds `manual` to
`vendor_findings.finding_source`. New: `record_signal`/`set_signal_status` (+ SignalsPanel on the
Monitoring tab), `create_finding` by hand, `update_document`/`attach_document_file` (evidence store,
`vendor_report`), `save_sla` + SlasPanel on Paperwork, and `policy_view`/`update_policy` with a
Vendors > Policy screen (bands, cadences, finding windows, skip matrix, reviewer roles; the gate is
refused in the skip matrix). Finding due dates read `finding_sla_days_by_severity` from the policy,
falling back to the module constants.

**Everything else closed (2026-09-23, committed 5613e5b on 2026-09-24):** migrations `5c93b7e2a481`
(`vendor_assessment_reviewers`, RLS) and `9f2d1a7c6b40` (built-in roles get `vendors:read`).
Review collaboration = assign a domain (or the whole review) to a person, each with its own
assigned/in_review/done; comments internal or `vendor_shared`, portal reads shared-only and the
contact replies as `vendor_contact` (never internal, by construction). Alert rules fire inside
`record_signal` (notify / create_task / trigger_reassessment moves `next_reassessment_on` to
today; Slack inert). Discovered apps: record + triage, `added_as_vendor` raises an intake request.
Register now orders/pages in SQL via `_register_order`; attention filter and grade/owner sorts
still scan. Smoke scripts: scratchpad `smoke_rest.py` and `smoke_last.py`.
