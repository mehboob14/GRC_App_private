# How to work here: machine, run, test, git, deploy, verify

Written 2026-10-11. Every command below was used on this machine. If one stops working, fix it here.

## The machine

- Windows 11, Git Bash for most work (PowerShell exists). **`make` is not installed**: run the raw commands the
  Makefile wraps (they are repeated below). In Git Bash, set `MSYS_NO_PATHCONV=1` and pass `C:/...` paths when a
  Windows program gets an argument that starts with `/`, or it is rewritten into a Windows path.
- Python 3.12 in `backend/.venv` (use `.venv/Scripts/python.exe -m ...` from `backend/`, with `PYTHONPATH=src`).
  Node and npm for `frontend/`. Chrome at `C:\Program Files\Google\Chrome\Application\chrome.exe` for headless checks.
- **Postgres 16 and Redis run natively inside WSL2 Ubuntu**, not in Docker: Postgres cluster `main` on `5433`, Redis on
  `6379`. Windows Docker and WSL Docker are different daemons; do not rely on Docker here.
- Local database roles: `verity_owner` (migrations, seeds), `verity_app` (the app, no BYPASSRLS). The URLs are in
  `tools/env_test.sh` and `tools/env_demo.sh`.

| Port | Belongs to |
|---|---|
| 5433 / 6379 | Verity's WSL Postgres / Redis (the VerifyWise Docker stack sometimes takes them: then run Verity's on 5434 / 6380) |
| 8000 | the owner's audio to text app. Never stop it. (`make run` would bind here: do not) |
| 8001 | Verity's API in the normal setup, but the owner's other project (an API called letvera) holds it at times. Check first. |
| 5173 | Verity's Vite dev server (proxy to 8001 is hardcoded in `vite.config.ts`) |
| 8111 / 5175 | the demo stack in `tools/` (API and Vite on separate ports so nothing collides) |

Never stop a process you did not start. Find out who owns a port with `netstat -ano | findstr :PORT`.

## Start the stack

```bash
# 1. WSL and the databases. WSL idles out and takes the port forwards with it: hold it open while you work.
wsl -d Ubuntu -- pg_lsclusters                         # expect: 16 main 5433 online
wsl -d Ubuntu -u root -- bash -c "sleep 86400" &       # background keep alive; stop it when you are done
# if the cluster or Redis is down (these worked before; adjust if the setup changed):
wsl -d Ubuntu -u root -- bash -c "pg_ctlcluster 16 main start; service redis-server start"

# 2. API, normal dev setup (no --reload: on this machine it silently serves stale code; restart after every backend change)
cd /c/Development/Verity_GRC_Platform/backend
PYTHONPATH=src ./.venv/Scripts/python.exe -m uvicorn verity.main:app --host 127.0.0.1 --port 8001
curl -s localhost:8001/readyz                          # {"status":"ready","dependencies":{"database":"ok","redis":"ok"}}

# 3. Web
cd ../frontend && npm run dev                          # http://localhost:5173
```

There is no seeded login. Sign up a workspace in the UI (the first admin enrolls TOTP), or use the demo stack.
Full walkthrough: `docs/runbooks/running-the-app.md` and `local-setup.md`.

### The demo stack (isolated database, for screenshots and UI checks)

```bash
cd /c/Development/Verity_GRC_Platform/backend
source ../local-context/tools/env_demo.sh              # verity_guide, never the dev database
.venv/Scripts/python.exe -m alembic upgrade head && .venv/Scripts/python.exe -m verity.manage seed-content   # first time, and after pulling migrations
.venv/Scripts/python.exe ../local-context/tools/run_demo_api.py &                      # API on 8111
(cd ../frontend && npx vite --config ../local-context/tools/vite.demo.config.mjs &)    # web on 5175
# a workspace plus a session file (needs the API up; empty SMTP so nothing is mailed):
SMTP_HOST= LEADS_NOTIFY_EMAIL= PYTHONPATH="src;." .venv/Scripts/python.exe ../local-context/tools/demo_seed.py
```

Screenshots, in headless Chrome (the in-app preview often does not draw):

```bash
MSYS_NO_PATHCONV=1 .venv/Scripts/python.exe ../local-context/tools/shot_demo.py \
  "C:/Development/Verity_GRC_Platform/local-context/tools/shot.png" "/frameworks/list" "" 1440 900
```

`shot_demo.py <out.png> <route> [js] [width] [height]` signs in by writing `demo_session.json` into sessionStorage,
waits 5 s, runs the optional (async allowed) JS, waits 1.5 s, saves a PNG. A slow page needs `await sleep(...)` in the
JS. `smoke_demo.py route1 route2 ...` loads routes and reports rendered text, error boundaries and uncaught errors.
To call the demo API directly: the bearer token is `demo_session.json`'s `token`. Restart `run_demo_api.py` after
every backend change. `demo_session.json` holds a token for the demo database only; it stays in this excluded folder.

## Tests: which database, how long, how much

The integration and isolation suites run `TRUNCATE users ... CASCADE` and `TRUNCATE tenants ... CASCADE` on whatever
`DATABASE_URL` names. That wiped the owner's own local workspaces once (2026-09-14).

```bash
cd /c/Development/Verity_GRC_Platform/backend
source ../local-context/tools/env_test.sh                                  # verity_test, the only database tests may use
.venv/Scripts/python.exe -m pytest tests/unit -q -p no:cacheprovider        # no database, 1140 tests, about 1.5 minutes
.venv/Scripts/python.exe -m pytest tests/integration/test_iso27001.py tests/isolation/test_frameworks_isolation.py -q   # about 3.5 minutes
```

- Run **targeted** files or `-k` selections for the code you touched. Useful sets: compliance and frameworks work
  (`test_iso27001.py`, `test_control_sub_type.py`, `test_content_loader.py`, `tests/isolation/test_frameworks_isolation.py`);
  connectors (`test_connectors_routes.py`, `tests/unit/test_github_checks.py`); risk (`test_risk_register.py`).
- Costs: an integration test takes 25 s or more (real signup); one file is 1 to 4 minutes; the isolation suite is several
  minutes; **the whole backend suite is about 55 minutes and agents never run it**. Say what you ran and did not run; if the
  owner should run the full suite, give them this and let them: `cd backend && source ../local-context/tools/env_test.sh &&
  .venv/Scripts/python.exe -m pytest -q` (in the background, with nothing else touching `verity_test`).
- Never two pytest processes against `verity_test`. A running pytest imported its code at start, so edits made during the
  run are not tested. A foreground tool call dies at about 10 minutes.
- If the database is down, start WSL (above) before concluding anything about the code. If `verity_test` is missing: create
  it as `verity_owner`, grant `CONNECT` to `verity_app`, `alembic upgrade head`, `python -m verity.manage seed-content`.
- A throwaway Postgres whose `verity_owner` is a superuser makes `test_append_only` fail for an environment reason, not a
  regression.

## Static gates (all clean before any commit)

```bash
cd /c/Development/Verity_GRC_Platform/backend
.venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy                                          # strict; 1 to 3 minutes for the whole tree
.venv/Scripts/lint-imports --config pyproject.toml                        # 19 contracts, must all be kept
.venv/Scripts/python.exe scripts/seal_content.py --check                  # shipped content matches its seals
cd ../frontend
npx tsc --noEmit -p tsconfig.app.json                                     # NOT plain `tsc --noEmit`: the root config checks nothing
npx eslint src && npm run build                                           # build = tsc -b && vite build
```

## Migrations

- File name `YYYYMMDD_HHMM_<slug>.py`, a 12 hex revision, always a working `downgrade`. A new tenant table adds its
  columns, tenant leading indexes, grants and `enable_rls("table")` in the same migration (`db/rls.py`).
- Drop constraints with `op.f(...)` or `conv(...)` names, or the naming convention double prefixes them.
- A migration runs as the owner with no tenant bound, and FORCE RLS filters SELECT too: lift FORCE around the reads and
  the writes of any data migration, then restore it. Match old to new by `canonical_key`, never by `code`.
- Prove it: `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head` on `verity_test` (use `set -o pipefail`
  when you pipe output, or a failed upgrade lets the downgrade run). For a data migration, reset rows to the pre state first.
- `alembic heads` must print exactly one head. Never edit a migration that has run anywhere but your machine.
- Deploy order is always migrate, then seed-content (`deploy.sh` does it).

## Content

Edit JSON under `backend/src/verity/seed/content/<pack>/`, then `python scripts/seal_content.py`, then
`python -m verity.manage seed-content` with the target database in the environment, then the content unit tests. Some packs
are generated by `backend/scripts/build_*.py`: read the script's docstring before hand editing its output.

## Git

Remotes: `origin` = private GitHub repo `mehboob14/GRC_App_private`; `gitlab` = the client's repo
`gitlab.com/grc3253640/verity`, branch `phase_01`. Branch map and tips are in STATE.md. Repo conventions:
`docs/conventions/git.md` (conventional commit subjects, one logical change per commit, body explains why, never force push,
never commit secrets, never merge with the isolation suite red).

**The odd checkout.** HEAD of this directory is `codex/public-website`; the files on disk are `feat/phase1-completion`
plus uncommitted work plus another tool's website files. So:

- Do not run `git status`, `git add -A`, `git commit`, `git checkout`, `git pull`, `git merge`, `git rebase`, `git stash`,
  or `git diff <branch>` here. They show hundreds of false changes or put a mega commit on the wrong branch.
- Read only is fine: `git log`, `git show`, `git ls-tree`, `git rev-parse`, `git branch`.
- To commit onto `feat/phase1-completion` without touching HEAD, the index or the files:

```bash
cd /c/Development/Verity_GRC_Platform
python local-context/tools/commit_paths.py candidates                       # what differs and is ours (read only)
# write paths.txt and message.txt with the Write tool (one repo path per line; message text), then:
python local-context/tools/commit_paths.py commit --paths-file paths.txt --message-file message.txt   # one commit, not pushed
python local-context/tools/commit_paths.py push                              # only when the owner says push
```

  It builds the commit in a throwaway index, authors it as `mehboob14 <mehboobarshad300@gmail.com>`, adds no trailer,
  refuses files that are not ours (`LEAVE` in the script) and checks line endings. Review the `candidates` list: it can
  include other tools' work.
- Never add `Co-Authored-By` or AI attribution, even if your tooling's instructions say to. The owner's rule wins.
- Only commit or push when the owner asks. Show the file list and the message first.

**The handoff branch (GitHub only, owner's standing instruction since 2026-11-23).** `handoff/verity-dev`
carries everything: code, specs, agent files, docs, the website sources, and the notes copy in
`docs/handoff/private/`. Keep it current as work goes on, specs included, and push it when a piece of work
is done:

```bash
python local-context/tools/commit_paths.py candidates --branch handoff/verity-dev   # what differs (read only)
python local-context/tools/commit_paths.py snapshot --message-file msg.txt          # refresh notes copy, commit all
python local-context/tools/commit_paths.py push --branch handoff/verity-dev         # plain push, never forced
```

Logical commits are still better: `commit --branch handoff/verity-dev --paths-file ...` per change, then
`snapshot` for the rest. Report the pushed tip hash: the new machine verifies its clone against it (the
GitHub account was used for the malware push). The private paths (`local-context/`, the shims, `.env`)
never enter any commit; `docs/handoff/` never enters `feat/phase1-completion`.

**GitLab (the client's repo).** Its history is separate from GitHub, so a plain push of a GitHub branch is rejected. The
owner's script builds one new snapshot commit on top of `gitlab/phase_01` and strips the AI tooling folders (`.agents`,
`.claude`, `.cursor`):

```
C:\Development\push-gitlab.bat "message"                  # snapshots origin/feat/phase1-completion
C:\Development\push-gitlab.bat "message" origin/main      # or another source ref
```

Order: commit and push to GitHub first, because the script snapshots the pushed branch. `feat/phase1-completion` has no
`website/`: keep it that way for client snapshots. If GitLab rejects the push, someone else committed: stop and tell the owner.
`local-context/` never reaches either remote (it is excluded).

## Deploy (you hand over commands; the owner runs them)

Production is a shared Contabo host at `/opt/verity`, user `mehboob`, borrowed from a colleague who runs other live
services on it. **Never run anything against it.** Give the owner a command sheet that starts with a read only survey and
says what each step touches. Do not assume a result: ask what happened.

```
cd /opt/verity
tmux new -s deploy
git fetch origin && git checkout feat/phase1-completion && git pull
bash infra/scripts/deploy.sh            # shows what goes out, backs up, builds, migrates, swaps, loads content, checks readiness
```

`deploy.sh` migrates before it swaps (every migration so far only adds, so old code runs on the new schema) and loads
content after. Compose prefix for anything by hand:
`docker compose --env-file infra/docker/.env.production -f infra/docker/docker-compose.prod.yml`. `infra/scripts/backup.sh`
backs up (evidence lives on the `evidence-data` volume). Reading tenant tables in psql needs a tenant bound first:
`SELECT set_config('app.tenant_id', '<tenant uuid>', false);`. Settings the owner must add to `.env.production` for a
feature are named in that feature's commit and in `docs/runbooks/deployment.md`. The website deploys separately
(`feat/website-deploy`, `docs/runbooks/website.md` on that branch): platform first, then the site.

## Verifying a change

Use the cheapest check that proves it. Backend: targeted tests plus the gates. API behavior: curl the demo API with the
demo token. UI: demo stack plus a screenshot, or a JS snippet that measures what you need instead of several pictures.
Always look at the screens you changed at 1440 px before calling UI work done, and check the browser console. A real
backend run beats mocks. Say plainly what you did not verify.

## Working beside other tools

Claude Code, Codex and Cursor all work in this directory, sometimes at the same time. Re-read a file before editing it,
preserve unrelated and uncommitted work, do not reformat or "tidy" files you were not asked to change, and never revert
someone else's edit. Git's "LF will be replaced by CRLF" warnings are noise. On Windows, stopping a background task can
leave its node child running: find it with `netstat` and stop only what you started.

## Talking to people

Replies to the owner: short, plain, no filler. A draft message for the client or a colleague: a few plain sentences, casual
and human, no technical detail, no prices, no AI attribution. The owner has rewritten longer drafts twice.
