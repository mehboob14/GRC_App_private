# Pitfalls that already cost time

Written 2026-10-11. Each one happened here. Add new ones as you find them: what you saw, why, what to do.

## Database and tests
- **Tests truncate the database they point at.** `clean_iam` and `clean_tenancy` run `TRUNCATE users, tenants CASCADE` as the
  owner. A dev shell pointed at `verity` wiped real local workspaces on 2026-09-14. Always `source tools/env_test.sh`.
- **WSL idles out.** Postgres and Redis vanish with it ("connection refused", `WinError 1225`). Check `pg_lsclusters` first.
  Killing the keep alive process (`wsl ... sleep 86400`) takes the databases down with it.
- **Never two pytest runs on `verity_test`**; a long run imports code once; foreground tool calls die at about 10 minutes; piped
  alembic hides failures (use `set -o pipefail`).
- **`autoflush=False`.** `audit.record` and `repository.add` do not flush. After mutating a row, flush before any query that
  should see it (counts, `refresh`, `populate_existing`). Real examples: acknowledging a campaign returned a stale pending
  count; `link_framework` read "existing links" before the adoption just before it was flushed and inserted the same
  `(control, requirement)` pair twice (`uq_control_requirements`).
- **`AuditService.snapshot(row)` after a flush on a row with a server `onupdate` column raises `MissingGreenlet`.** Pass `fields=`.
  A freshly mutated ORM row with server defaults needs `flush()` then `refresh()` before sync access to `created_at` or `updated_at`.
- **FORCE ROW LEVEL SECURITY filters SELECT, not only writes, and it applies to the owner.** A data migration that lifts FORCE only
  around its UPDATE silently reads zero rows. Lift it around reads too. Test the downgrade and reset rows to the pre state: the
  upgrade looked fine only because the rows had been fixed by hand.
- `op.drop_constraint` needs `conv(name)` or `op.f(name)`, or the naming convention double prefixes it.
- Older notes say the RLS setting is `app.current_tenant`; the code says `app.tenant_id` (`db/rls.py`). The code wins.
- `verity_owner` created as a superuser (some throwaway containers) makes `test_append_only` fail for an environment reason.
- Control vocabularies: `controls.category`, `control_type` and `control_sub_type` are CHECK constrained. Free text from a form is a
  masked 500. Source values from the vocabulary endpoint.
- Notification kinds are CHECK constrained (`ck_notifications__kind_valid`): a new kind needs a migration that widens it.

## Backend habits
- **`dict(result)` on a SQLAlchemy Result raises** ("ChunkedIteratorResult not subscriptable": it has `keys()`).
  Build the dict with a comprehension and `# noqa: C416`.
- **New assets start `planned`.** Checks judge assets in service only; a test must transition them to active.
- **Run now right after creating a connection can 404**: the create commits after its response (the known
  `get_tenant_session` race). Retry, or wait for the list to show it.
- **`f6c2b8e4a915` refuses to downgrade while any `verity` connection exists.** On verity_test truncate tenants first.
- **A pack control added after a workspace added its framework is not adopted** (adding adopts once). SOC 2 has
  `backfill_adopt_soc2`; ISO has none yet. The demo workspace in verity_guide has no PE-03 for this reason.
- Routes built in a loop under `from __future__ import annotations` must pass `Depends(require(...))` as a default value, not in
  `Annotated[...]`, or FastAPI reads the principal as a query parameter (422).
- Declare static routes (`/custom-fields`, `/campaigns/pending`) before `/{id}` or FastAPI matches the word as an id.
- The audit action vocabulary is fixed (`create`, `update`, `delete`, `transition`, `approve`).
- Adding a service to service call can open a transitive import contract break: add the specific `ignore_imports` line to the
  affected import-linter contracts in `pyproject.toml` instead of weakening a contract.
- `PATCH /assets/{id}` is a full replace: send every field. `AssetWrite` forbids extra fields (owner fields are `*_membership_id`).
- Frameworks sort by `(position, code)`. Code that takes `frameworks[0]` as SOC 2 breaks once ISO exists.
- Every `/engagement*` call without `?framework=` means SOC 2, by design.
- The test `test_risk_register` fails between 00:00 and 05:00 local (UTC date compare). Not a regression.
- Cross-module reads that look cheap can loop a service per row (N+1). Existing code accepts it for a handful of rows; do not copy it
  for lists.

## Frontend
- **`npx tsc --noEmit` at the frontend root checks nothing** (a solution file with `"files": []`). Use `-p tsconfig.app.json`, or
  `npm run typecheck` / `npm run build`. `vite build` alone does not type check.
- Invalid `Badge` variants render with no colour and no error: type check, then look at the screen.
- Dev browser imports of `/src/x.ts` and `@/x` resolve to different module ids, so `instanceof` fails across them.
- The in-app preview browser usually does not draw or fire scroll events and refuses some local URLs. Use the headless Chrome
  scripts in `tools/`. `form_input` does not update React Hook Form state; real keystrokes or direct session injection do.
  Use DOM `.click()` for Radix dialogs.
- The Vite proxy is hardcoded to 8001; the demo stack uses its own config. The first request after an API restart is slow.
- Tests of UI state keyed by history entry: the first entry of a document load has the router key `default`; `useEntryState`
  scopes to the load. `DetailHeader` Back must not step through a record's own route tabs.
- Controls register: never add a column; at 1440 px Status already sits at the edge. `DialogBody` has `-mx-6 px-6`: inside a
  `p-0` dialog use a plain padded div.
- Do not call state updaters with side effects inside setState (StrictMode runs them twice).
- Static analysis of copy: no visible dashes anywhere (see START-HERE.md).

## Content
- `scripts/seal_content.py` after every content edit, or the loader refuses the pack and a unit test fails.
- The seed loader keys control templates on `canonical_key`; a re-code turns into delete plus insert and the adopted-controls foreign
  key refuses it. Changed shipped control text never reaches tenants without a data migration.
- Content authored by several people mixes British and American spelling: the library uses American.

## Windows, shell and tools
- **Git Bash rewrites a leading `/path` argument** into a Windows path: run `shot_demo.py` with `MSYS_NO_PATHCONV=1`.
- **`shot_demo.py` on a cold Vite returns a blank page**: pass a JS wait of about 20 s. A hung headless Chrome keeps
  port 9352; kill that PID before the next shot.
- **shot_demo clicks by text: exclude `a`** or a tab named like a sidebar link (Evidence) opens the sidebar page.
  `/frameworks?framework=ISO27001` lands on the SOC 2 dashboard; click the switcher instead.
- **Prettier is not a frontend dependency**: `npx prettier` downloads it. Use the local `tsc` and `eslint` only.
- A `\\` typed in a Bash tool command reaches the shell as one `\`. Dockerfile line continuations and sed back references written
  through Python heredocs were silently damaged. Put such text in a file with the Write tool, then verify behavior.
- Heredocs with long quoted blocks break in this shell: write the file, then apply it.
- Git Bash rewrites arguments that start with `/`. Use `MSYS_NO_PATHCONV=1` and `C:/...` paths for Windows programs.
- Stopping a background task on Windows can leave its node or python child alive. Find it with `netstat -ano` and stop only yours.
- `make` is missing; `--reload` serves stale code; SQLAlchemy and uvicorn processes keep old modules until restarted.
- OneDrive syncs `grc-s` (the old prototype) but not `C:\Development`.

## Email, secrets, accidents
- The repo-root `.env` (and `backend/.env`) holds **real SMTP credentials**. Any process that signs up users or sends mail must
  run with `SMTP_HOST=` and `LEADS_NOTIFY_EMAIL=` set empty, or it really sends. Seeding scripts have done this by accident once.
  Run local mail tests from a folder with no `.env` above it.
- Never write secrets, tokens or personal data into this folder, commit messages, test fixtures or screenshots.

## Product traps
- The control and automation read permission is `frameworks:read`, not `controls:read`.
- GitHub free plan limits (branch protection, secret scanning on private repos) are reported as `fail` grouped once per account with
  honest wording; do not promise upgrading fixes everything.
- A control whose only result is `not_applicable` is not "Passing". Status order: failing, error, passing (at least one pass),
  not_applicable, pending, not_connected.
- Assets created in an old mock based UI never reached the database: when a dropdown is empty, check the data source before the filter.
- Cross-tab session sharing and `sessionStorage` bearer tokens widen token exposure; do not extend them without telling the owner.
- (2026-11-21) The frontend has no test runner installed (no vitest in package.json). `npx vitest` silently fetches
  one into the npx cache: do not. A pure helper gets a plain Node self check instead: `node scripts/check-countries.ts`
  (Node 24 runs TypeScript by stripping types; import with the `.ts` extension, no `@/` aliases).
- (2026-11-21) `tools/shot_demo.py`'s JS argument is evaluated as one expression: pass an async IIFE that defines its
  own `sleep`. Radix menus open on a keyboard Enter after `focus()`, not on `.click()`. `DEMO_SESSION=demo_session.call.json`
  picks the Northwind call workspace; its token lasts 12 hours (re-mint with `tests.support.iam.tenant_session_headers`).

## Two sessions, one test database (2026-11-23)
Integration tests TRUNCATE tables, so two sessions running them on `verity_test` at once deadlock and break each
other's sign up tokens. Give the second session its own copy: create `verity_test_ob` (owner `verity_owner`) and fill
it with `pg_dump -p 5433 -d verity_test | psql -p 5433 -d verity_test_ob` inside WSL (a fresh `alembic upgrade
head` on an empty database fails at a 2026-10 data migration), then point a copy of `env_test.sh` at it.
