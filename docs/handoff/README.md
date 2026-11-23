# Verity: picking the work up on a new machine

This branch, `handoff/verity-dev` on GitHub, holds everything the old machine had: the code, every spec,
the agent files (`.claude`, `.cursor`, `.agents`, `CLAUDE.md`, `AGENTS.md`), the docs, the public website
sources, and a scrubbed copy of the private working notes in `docs/handoff/private/`. It is updated as
work continues. The client's GitLab gets its own snapshots and never this branch.

## 1. Get the code safely

On 2026-10-19 the GitHub account pushed obfuscated malware into `postcss.config` files on every branch
that existed then (`main`, `feat/phase1-completion`, `feat/website-deploy`, `codex/public-website`). A
frontend build or dev server runs that file. This branch was made from the clean local history. So:

Clone into a short local folder outside OneDrive or Dropbox (for example `C:\dev`), from an ordinary
terminal where Git can ask you to sign in to GitHub, not through a tool that times out:

```bash
git clone --branch handoff/verity-dev --single-branch https://github.com/mehboob14/GRC_App_private.git C:/dev/Verity_GRC_Platform
cd C:/dev/Verity_GRC_Platform
git rev-parse HEAD                                    # must equal the hash the last session reported
git cat-file -s HEAD:frontend/postcss.config.js       # 81 (the stored size; thousands means infected)
git cat-file -s HEAD:website/postcss.config.mjs       # 105
git grep -l "global.o=" -- "*.js" "*.mjs" "*.cjs"     # must print nothing
```

Read the sizes with `git cat-file -s`, not from the files on disk: on Windows Git turns line endings into
CRLF on checkout, so the same clean files show 87 and 113 bytes there.

If a clone stops part way (no `HEAD`, no files, a locked `tmp_pack` file): close the terminal, end any
`git.exe` still running in Task Manager, delete the folder, and clone again. A shallow clone is smaller:
`git clone --depth 1 --branch handoff/verity-dev --single-branch <url> C:/dev/Verity_GRC_Platform`, and
`git fetch --unshallow` later brings the history.

Only then run `npm install`. Never check out, pull or build the other GitHub branches until the account is
secured (password and every token rotated, 2FA on, sessions signed out) and those branches are restored.

## 2. Restore the private notes

`docs/handoff/private/` holds the working notes the sessions keep (`local-context/`: START-HERE, STATE,
DECISIONS, GOTCHAS, ARCHITECTURE, WORKFLOW, CHANGELOG, tools), their entry shims, the assistant's project
memory, and the GitLab push script. Session tokens, TOTP seeds and the demo browser profile were left out.
The same files are also in a zip in OneDrive.

```bash
cp -r docs/handoff/private/local-context ./local-context
cp docs/handoff/private/shims/CLAUDE.local.md docs/handoff/private/shims/AGENTS.override.md .
mkdir -p .cursor/rules && cp docs/handoff/private/shims/.cursor/rules/00-verity-local-context.mdc .cursor/rules/
cat >> .git/info/exclude <<'EOF'
/local-context/
/CLAUDE.local.md
/AGENTS.override.md
/.cursor/rules/00-verity-local-context.mdc
EOF
cp docs/handoff/private/push-gitlab.bat ..            # the client snapshot script lives beside the repo
```

The assistant's memory goes to `~/.claude/projects/<key>/memory/`, where `<key>` is the folder Claude Code
is opened in with every character other than a letter or digit turned into `-` (for
`C:\Development\Verity_GRC_Platform` that is `C--Development-Verity-GRC-Platform`). Copy
`docs/handoff/private/claude-memory/*.md` there.

Then read `local-context/START-HERE.md` and `local-context/STATE.md`: they are the current picture.

## 3. Set the machine up

The full recipe is `docs/runbooks/local-setup.md` and `running-the-app.md`; the short version:

| Need | Notes |
|---|---|
| Git and Git Bash | Windows 11 was the old machine; `make` was not installed, so the raw commands are used |
| Python 3.12, `uv` | `cd backend && uv sync` makes `backend/.venv` |
| Node 24 and npm | `cd frontend && npm install` (after the checks in section 1) |
| PostgreSQL 16 and Redis | ran natively in WSL2 Ubuntu: Postgres cluster on port 5433, Redis 6379. `infra/docker/docker-compose.yml` is the Docker alternative |
| Java 21 | only for the local Keycloak (`docs/runbooks/keycloak-local.md`) |

Databases on the one Postgres: `verity` (development), `verity_test` (the only one tests may use: the
integration and isolation suites truncate users and tenants), `verity_guide` (demo data for screenshots).
Roles: `verity_owner` (migrations, seeds) and `verity_app` (the app, no BYPASSRLS). For each database:
`alembic upgrade head`, then `python -m verity.manage seed-content`.

Secrets are not in git. Recreate by hand: the repository root `.env` (from `.env.example`: the secret and
encryption keys, database URLs and roles, Redis, SMTP, the AI provider settings), `infra/docker/.env.production` on the server (from its example),
and the Keycloak client secrets when SSO is on (`docs/runbooks/keycloak-production.md`).

The local Keycloak is built from the owner's Keycloak source clone (`C:\Development\Key_cloak`, a fork of
keycloak/keycloak built to `quarkus/dist/target/keycloak-999.0.0-SNAPSHOT.zip`). A released Keycloak 26
also works for most of it; the runbook lists what differed.

## 4. Where everything is

| Read | For |
|---|---|
| `CLAUDE.md` (and `backend/CLAUDE.md`, `frontend/CLAUDE.md`) | the contract: architecture rules every change follows |
| `AGENTS.md` | the same for Codex and other agents |
| `docs/architecture/` | architecture, data model, integrations, check catalogue |
| `docs/adr/` | why things are the way they are (0001 to 0015) |
| `openspec/changes/` | one folder per feature: proposal, design, tasks, what is verified |
| `docs/product/` | the signed requirements specification, product plans, guided onboarding |
| `docs/runbooks/` | run, deploy, back up, Keycloak locally and in production, SSO providers |
| `docs/user-guide/` | the customer facing guide with screenshots |
| `local-context/` (restored in section 2) | state, decisions, gotchas, workflow, changelog |

## 5. How the work is kept

- Commits are authored `mehboob14 <mehboobarshad300@gmail.com>`, with no AI attribution trailer.
- This branch is updated as work goes on: specs, notes and code together.
  `python local-context/tools/commit_paths.py snapshot --message-file msg.txt` refreshes the notes copy and
  commits everything that differs; `python local-context/tools/commit_paths.py push --branch
  handoff/verity-dev` pushes it. Never force.
- The client's GitLab (`gitlab.com/grc3253640/verity`, branch `phase_01`) is the client's record. Only the
  owner decides what goes there, through `push-gitlab.bat` from the local `feat/phase1-completion`. The
  handoff folder and the private notes never go to GitLab.
- Before stopping, each session updates `local-context/STATE.md` and `CHANGELOG.md`.

## 6. Where things stand

The full status by module is in `local-context/STATE.md`. Highlights at the time of this handoff
(2026-11-23):

- Phase 1 platform (controls, evidence, tasks, documents, risks, vendors, assets, vulnerabilities, audit)
  and ISO 27001 beside SOC 2 are built.
- Guided onboarding (eight phases), assessment objectives wave 1 and the SOC 2 mapping fixes are built
  on this branch, not yet in any client snapshot.
- Single sign on through Keycloak, phases A to D (sign in, workspace organizations, customer providers
  set up from Verity, lifecycle sync and back-channel logout), built and tested against a local
  Keycloak. Next: real Entra ID, Google Workspace and Okta tenants (phase E,
  `docs/runbooks/sso-providers.md`), then the client's Keycloak (phase F,
  `docs/runbooks/keycloak-production.md`).
- Connectors: GitHub plus Verity's built-in checks; the other fourteen Phase 2 connectors are not built.
