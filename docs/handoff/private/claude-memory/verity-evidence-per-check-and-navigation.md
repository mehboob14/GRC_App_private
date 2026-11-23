---
name: verity-evidence-per-check-and-navigation
description: "2026-10-07 round 2 after the user deployed SD-11 work (committed 02c5047 and pushed; server deploy commands handed over, result unknown): one evidence file per check, Back/state/scroll/new-tab-login fixes platform wide, evidence screens; env gotchas (port 8001 is another project's, headless screenshots)"
metadata:
  node_type: memory
  type: project
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-07T16:32:02.746Z
---

The user deployed [[verity-connector-sd11-fixes]] and came back with seven points. Built and verified locally 2026-10-07, committed as 02c5047 (53 files, mehboob14, no trailer) and pushed on the user's instruction ("commit, push, then give the server commands"). The server deploy sheet (fetch, checkout feat/phase1-completion, pull, deploy.sh; then Run now on the connection; then the retire script) was handed over, never run. The last full backend run was still going when it was pushed (the one before it, 1574 tests, passed); check the result when it lands.

What changed:
- **One evidence file per check** (`connectors/service.py::_evidence`): titled `<check name>: GitHub <account>, <d Mon yyyy HH:MM> UTC`, linked only to the controls that check supports, holding only that check's results and the slice of the snapshot it read (`github.evidence_snapshot`). Filed with `source`, `external_id = connection:check:digest16:run`, `synced_at` (rule 9); a repeat is found with `evidence_service.latest_synced` (prefix lookup), so no migration. `check_runs.evidence_id` is no longer set. Old one-file-per-run items stay linked to many controls until `python -m scripts.retire_legacy_connector_evidence --apply` is run once after a run on the new code (dry run by default, skips a workspace with no per-check evidence yet, audited, nothing deleted). Tested against real legacy rows in the demo DB.
- **Navigation, platform wide** (`frontend/src/lib/nav/`): `useEntryState` keeps filters/search/page/tab per history entry (location.key, sessionStorage, cleared on sign-out); the shared `useTableSort` uses it; `DetailHeader` Back goes to the previous page in this tab (history-log + back-labels, plain click = navigate(-1)); `useScrollRestoration` restores `<main>` scroll on Back and resets it on other navigations (it ignores the scroll event a page swap causes, via entryIndex). New tabs take the session from open tabs over a BroadcastChannel before first render (`lib/auth/tab-share.ts`, workspace and provider planes separately) and sign-out is announced with the token so only that session ends. Window `window.open` opener copy still works.
- Evidence screens: Type and Controls cells (`evidence-cells.tsx`), "Show N earlier automated results" toggle (historyKey), Controls tab shows control name and statement, Download JSON in the header, honest Origin, `files.ts` holds the shared download helpers; control page lost its Related controls card.

A fresh-eyes review agent found real problems in the first cut, all fixed before shipping (keep these in mind for similar work):
- Per-check files multiplied an old flaw: lapsed evidence raises one renewal task plus one email per item (`tasks.raise_evidence_renewals`), and every lapsed item counts as stale/aging on dashboards. Fix: that automation skips anything with a `source`, and `EvidenceView.superseded` (newest of a series, `series_of(source, external_id)` = id up to the last two `:` parts) keeps history out of the engagement counts and the library counts.
- Cross-tab session sharing widens token exposure (script in a fresh tab can ask other tabs). Mitigations in `tab-share.ts`: only tabs used in the last 30 minutes answer, the most recently used tab wins (right workspace), sign-in/invite/password/vendor-portal pages and the provider plane's own login never ask, 120 ms wait. Say this trade-off out loud to the user: httpOnly cookies (ADR-0006) are the real fix.
- `useEntryState`: the first entry of a document load has router key "default" and storage outlives the load, so it is scoped to the load; objects are merged over the starting value (a field added by a later build); a `replace` navigation forgets the old key; sign-in, workspace switch and provider sign-out clear it.
- `DetailHeader` Back must not step through a record's own route tabs (`recordOf`), `automatedBy` trusts `source` and only falls back to the old "label + title" pair, the retire script keeps a legacy file on controls with no per-check evidence yet.

Gotchas learnt:
- **Port 8001 now belongs to the user's other project** (letvera ai API, uvicorn). Never stop it. Run the Verity demo API on 8111 and vite on 5175 with a demo config in the scratchpad (`vite.demo.config.mjs`, absolute imports, proxy to 8111); `vite.config.ts` hardcodes 8001.
- The in-app preview window often will not draw (screenshots time out, scroll events do not fire). Use headless Chrome over CDP instead (`shot_demo.py`: signs in via sessionStorage, runs an async JS snippet, saves a PNG; `smoke_demo.py` loads many routes and reports exceptions). Run them with `MSYS_NO_PATHCONV=1` and Windows-style `C:/...` paths.
- `signup_workspace` helpers need `PYTHONPATH="src;."` from backend/; set `SMTP_HOST=` and `LEADS_NOTIFY_EMAIL=` empty (repo-root .env has real SMTP).
- Full backend suite takes about 55 minutes (1566 tests at the time); never run a second pytest against `verity_test`.

Related: [[verity-connectors-github]], [[verity-phase1-completion-branch]], [[feedback-commit-attribution]].
