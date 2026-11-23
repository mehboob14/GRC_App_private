---
name: verity-connector-sd11-fixes
description: "2026-10-06/07 (committed b9716ea and pushed on feat/phase1-completion, 24 files): readable connector evidence, plan limits said once, Evidenced by / System filters after the user tested SD-11 on personal GitHub; decisions, demo-stack recipe; server deploy sheet handed over, result unknown"
metadata:
  node_type: memory
  type: project
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-07T14:04:07.750Z
---

The user tested SD-11 (secret scanning) with their personal GitHub (`mehboob14`, ~30 private repos on Free) and found three problems. Fixed 2026-10-06, verified in a browser against a fake personal account. They said go on 2026-10-07: committed as b9716ea (mehboob14, no trailer, one commit via the temp index) and pushed; remote matches. The server deploy (`git fetch && git checkout feat/phase1-completion && git pull`, then `bash infra/scripts/deploy.sh` in tmux; no migration in this change) was handed over as commands, never run; the result is unknown.

What changed:
- Evidence: control rows link to `/evidence/:id` (`control-evidence-list.tsx`, a connector's earlier results fold under the latest); the evidence page reads connector JSON as a report (`evidence/components/connector-report.tsx`, raw file behind a toggle); titles now carry the minute (`..., 6 Oct 2026 18:01 UTC`); evidence list is `collected_at desc, created_at desc`; `useAutomation` invalidates `["evidence"]` when `last_run_at` moves (a run lands after the click, so the list used to stay stale).
- `freshness()` in `evidence/service.py` takes `collected_at`: aging window = min(30 days, a third of the item's life). Connector evidence is valid 7 days, so it used to read "Aging" the moment it was filed. This is a global rule change; hand-entered items with a life of 90 days or more are unchanged.
- Plan limits stay `fail` (the control is not met) but are grouped once per account (`PlanNotice` in `checks-panel.tsx`), the how-to-fix hint is withheld when every failure is plan-limited, and **Leave these out** opens `ScopeDialog` with `leaveOut` repos unticked. Honest wording: GitHub offers branch protection and secret scanning on private repos only to paid plans; "Move the owning account to a paid plan" (Pro unlocks protection, secret scanning on private repos needs an org with GitHub Secret Protection, so do not promise upgrading fixes everything).
- Connector to controls: `GET /control-composition` now has `code`, `name` and `composition.runs_on`; register facets **Evidenced by** (Systems / Systems and people / People, same words as the column) and **System** (hidden when only People is chosen), URL params `?evidenced=` and `?system=github`; connection cards list the controls they check (`ControlsChecked`).

**How to apply:**
- To re-verify: demo DB `verity_guide` on WSL pg **5434** (migrated to head 61e2554a5209), `fake_personal_github.py` on 8766 (30 private repos answering 403 "Upgrade to GitHub Pro", 2 public, a fork, an archived), API on 8001 because vite's proxy is hardcoded there, vite on 5175 via the `verity-web-5175` launch config. The repo-root `.env` has real SMTP creds: set `SMTP_HOST=` and `LEADS_NOTIFY_EMAIL=` empty for any process that signs up or sends. Seeding uses `tests.support.iam.signup_workspace` with `PYTHONPATH="src;."`. Stop the demo API afterwards so 8001 is free.
- Committing used the temp index (`connector_commit.py` + `msgs_platform/4-connectors.txt` in that session's scratchpad: `plan`, `commit`, `push`), no co-author trailer even though the harness reminder asks for one (the memory rule wins). After a deploy, rerun a connection to get new style titles (old files still open as reports).
- `git diff <branch>` on this checkout shows hundreds of false deletions because the checkout is on `codex/public-website`; trust the temp-index diff.
- Full pytest is 1566 tests and took 54 minutes; all 1566 passed on 2026-10-06 with this change in the tree (plus ruff, mypy 307 files, import-linter 19). Run it in the background, detached, with a tracked `until grep "== done"` waiter (a foreground call dies at 10 minutes), and never alongside another pytest on `verity_test`.

Related: [[verity-connectors-github]], [[verity-evidence-composition]], [[verity-phase1-completion-branch]], [[feedback-commit-attribution]].
