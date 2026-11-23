---
name: verity-connectors-github
description: "GitHub connector and control Automation panel (built 2026-09-19, committed 8301042 on 2026-09-24 together with the linkage module); how runs, results, evidence and the automation pack work, plus the local port clash with VerifyWise"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-19T10:22:06.409Z
---

Built 2026-09-19, committed 2026-09-24 in 8301042, per build plan week 7 ("connect GitHub and watch controls pass or fail").

Backend `modules/connectors`:
- `models.py`: global `integration_capabilities`, `checks`, `control_template_checks`; tenant `connections`, `check_runs`, `check_results`, `integration_requests`.
  - `check_results` is partitioned by month to 2028-12 plus a default partition, append only.
- `http.py`: shared retry with backoff and jitter, paging, error classes.
- `github.py`: pure `collect`/`evaluate`, 7 checks.
- `service.py`: run = start (row lock), collect outside the transaction, finish (results, evidence at most once a day unless the results change, health).
- Content pack `seed/content/automation/` (13 capabilities, 59 checks, 53 of 57 automated or hybrid controls). The loader orders packs that contain checks last.
- Migration `63ac7a1e3c8f`.
- Routes: `/connections`, `/connections/{id}/runs` (BackgroundTasks), `/controls/{id}/automation` (`frameworks:read`), `/integration-requests`.

Frontend `features/connectors`:
- `AutomationPanel`, `AutomationSummary` and `AutomationHeaderButton` on the control page. The Tests tab is now "Automation".
- Connections page shows real connections. `ConnectGitHubDialog` connects, then starts the first run with a second call.

**Why:** the connect request can commit after background tasks start, so the first run is a separate POST.

**How to apply:**
- Control read permission is `frameworks:read`, not `controls:read`.
- Integration tests use `connector_service.transport = httpx.MockTransport(...)`.
- Local UI checks use scratchpad `fake_github.py` (port 8765) with `CONNECTORS_GITHUB_API_URL`.
- The user's VerifyWise Docker stack holds ports 5433, 6379 and 5173. When it runs, start Verity's WSL Postgres on 5434 (`pg_ctlcluster --skip-systemctl-redirect -o '-p 5434' 16 main start`), Redis on 6380, and Vite on 5175. Never stop VerifyWise.

Related: [[verity-common-control-framework]], [[verity-tests-wipe-database]].

**Accuracy pass 2026-10-03 (uncommitted; the user asked to inspect why automation "looked inaccurate").**
Found by pushing a fake personal account and a fake organisation through the real API:
- A personal-account run judged every owned repo (92 "failing"); forks, empty and coursework repos included, no way to choose. Now `connection_resources` (inventory + scope, migration `e7b2a41c9d35`): archived and forks out by default (system, re-derived each run), person decisions sticky, an exclusion needs a reason (CHECK + service), audited, printed on the evidence under `verity.scope`. UI: **Choose repositories** dialog on the connection card.
- A control whose only result was `not_applicable` read "Passing" (IAM-03 on a personal account). `_control_status` in service.py now: failing > error > passing (needs at least one pass) > not_applicable > pending > not_connected.
- "Protected" passed a branch that only blocked force pushes. Now needs a PR requirement, push restriction or lock. Free-plan limits fail with "upgrade the plan, or exclude with a reason" (admin on the repo + setting absent = plan; no admin = error). Empty repos = not_applicable.
- Readiness ignored the tests entirely (`checks_available=False` hard-coded, the dashboard card was static zeros). `compliance/readiness.py` is the single definition used by the dashboard and the report: ready = implemented + evidence that still counts (not rejected, not past renewal; `control_ids_with_current_evidence`) + automation not failing/error; criterion met only when EVERY applicable control is ready (CF-4). This lowers existing dashboard numbers: say so.
- 14 SOC 2 control mappings corrected (migration `f1c8d62b0e47`, only controls still equal to the old shipped set; a customised control is left alone; verified up and down). SD-11 secret scanning was under CC6.8 (malicious software); now CC6.1 + CC7.1.
- GitHub can only ever automate a slice of CC8.1, CC7.1, CC6.1, CC6.8, PI1.3, and only partially (table in connectors/README.md).
Still open per the spec: findings/waivers (AU-8, AU-10), per-control scoping (`control_checks`), observation-window coverage in readiness (AU-7), a `stale` state for automation that stopped running (connector evidence is valid 7 days, so readiness degrades anyway), and more GitHub checks (member/admin list for access reviews, Dependabot open alerts against SLA, code scanning, enforce_admins).

**Local test environment gotchas learnt doing it.** The scratchpad is cleaned between sessions, so recreate `env_wsltest.sh` (WSL pg 5433, db `verity_test`, redis 6379/1). Docker Desktop may be down: the WSL cluster still works once a long `wsl -d Ubuntu -e bash -lc 'sleep 7200'` holds the bridge open. Never run two pytest processes against one test DB (conftest TRUNCATEs). A running pytest imports code once, so edits made mid-run are not covered by it. Heredocs with longer quoted blocks break in this shell: write the file with the Write tool and apply it with a small python script. The full integration suite is 242 tests and ~35 minutes. To see a flow on screen, serve the test fixture as a real HTTP server (`http.server` wrapping the `httpx.MockTransport` handler) and point `CONNECTORS_GITHUB_API_URL` at it.

**Update 2026-10-04:** the Automation tab is now "Checks" (`checks-panel.tsx`); the GitHub evaluator keeps every review with time and commit and counts only each reviewer's last decision before the merge, treats an unreadable ruleset as error, states a cut short population, and a result older than 48h is `stale` (blocks readiness). `stale` and the review/ruleset items above are no longer open. See [[verity-evidence-composition]].
