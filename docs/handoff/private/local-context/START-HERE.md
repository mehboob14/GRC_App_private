# Verity: start here

**Local only. Never commit, push, paste or upload this folder.** It exists so that any new chat, Cursor,
Codex or Claude session can start with the full picture instead of the previous chat's memory.
Keep it current (see "Before you stop"). Full rewrite: 2026-10-11.

## What you are working on

Verity is a multi-tenant SOC 2 / GRC compliance platform (ISO 27001 support was added on 2026-10-10 and is
still uncommitted) at `C:\Development\Verity_GRC_Platform`: FastAPI, async SQLAlchemy, PostgreSQL with
row-level security and Celery on the backend; React, TypeScript and Tailwind on the front. Many customer
companies run isolated on one deployment. One developer owns the work, and every commit is authored as
`mehboob14`.

Three codebases exist. Only the first is the product.

| Path | What it is | Rule |
|---|---|---|
| `C:\Development\Verity_GRC_Platform` | Verity, built from scratch since 2026-08-12 | all work happens here |
| `C:\Users\HP\OneDrive\Desktop\Platform\grc-s` | the older prototype, different layout, its own CLAUDE.md | reference only; its conventions do not apply |
| `C:\Users\HP\OneDrive\Documents\GRC-Tenant` | another prototype, source of ideas for the documents module | reference only |

Other projects share this machine (an audio to text app on port 8000, another API on 8001, a VerifyWise
Docker stack). Never stop, change or reuse their processes, ports or databases.

## Read in this order

1. This file.
2. [STATE.md](STATE.md): what is true right now. Run its "verify before trusting" commands first.
3. Before writing code, the repo's own contracts: `CLAUDE.md` (the non-negotiable rules), then
   `backend/CLAUDE.md` or `frontend/CLAUDE.md`, then `docs/conventions/*` and the ADRs in `docs/adr/`.
4. As needed: [ARCHITECTURE.md](ARCHITECTURE.md), [WORKFLOW.md](WORKFLOW.md), [GOTCHAS.md](GOTCHAS.md),
   [DECISIONS.md](DECISIONS.md), and [CHANGELOG.md](CHANGELOG.md) for how we got here.

Repo docs describe intent. Check claims against the code, migrations and tests before relying on them (the
repo's own `AGENTS.md` says the same, and a few of its statements are already stale: see STATE.md).

## The five things that break people here

1. **The git checkout is unusual.** HEAD is `codex/public-website`, but the files on disk are
   `feat/phase1-completion` plus uncommitted work plus another tool's website files. Plain `git status`,
   `git add -A`, `git commit`, `git checkout`, `git pull`, `git stash` and `git diff <branch>` are wrong
   here. Read-only `git log` and `git show` are fine. To commit, use `local-context/tools/commit_paths.py`,
   and only when the owner asks. Details in WORKFLOW.md.
2. **Tests wipe the database they point at.** `tests/integration` and `tests/isolation` run
   `TRUNCATE users, tenants CASCADE`. Run `source local-context/tools/env_test.sh` first so they hit
   `verity_test`. Never point them at `verity` (dev, real local accounts) or `verity_guide` (demo).
3. **Postgres and Redis live inside WSL and die when WSL idles.** If the database refuses connections, check
   `wsl -d Ubuntu -- pg_lsclusters` (expect `16 main 5433 online`) before suspecting code.
4. **Autoflush is off.** After you change a row, `flush()` before you read it back, and flush before reading
   rows an earlier step added in the same transaction.
5. **Shipped content is sealed.** After any edit under `backend/src/verity/seed/content/`, run
   `scripts/seal_content.py`. Tenants hold copies of control text made at adoption, so changing shipped
   control text needs a data migration, not only a seed edit.

## Hard rules

Repo rules (breaking one is a bug even if the tests pass):

- Every tenant owned row has `tenant_id`. The row level security policy ships in the same migration as the
  table and is forced. The tenant comes from the authenticated membership, never from client input.
  Filter by tenant in code and rely on RLS: both walls, never one.
- Layering is router, service, optional repository, model. No ORM in routers, no HTTP types in services,
  no commits inside services, cross-module calls go service to service. The 19 import-linter contracts stay
  green.
- Every state change writes an audit row in the same transaction. `audit_log` and the other history tables are
  append only. Compliance objects are disabled or closed with a recorded reason, never hard deleted.
- Every route declares a permission. Object scope is applied in the service. An object from another tenant or
  outside the caller's scope looks absent.
- Secrets are encrypted in the application and never logged. Errors are typed domain errors with reader copy
  in `message`. A connector `error` is never shown as a control `fail`. AI output is only ever a draft that a
  person approves. Every in-tenant reference to a person points at `tenant_memberships`, never `users`.
- Schema changes are hand reviewed Alembic migrations with a working downgrade. A new tenant table adds its
  RLS in that migration. Never edit a migration that has run anywhere but your machine.
- Spec first (OpenSpec) for anything that adds a table or column, changes a module boundary, touches auth or
  tenancy, adds a dependency or a connector, or changes an API contract. Update docs in the same change. Do
  not build Phase 2 or Phase 3 features unless the owner says so.

The owner's standing preferences:

- Short answers, no filler. Verify with the cheapest check that proves the point. Spend fewer tokens.
- **No long checks.** Never run the whole backend suite (1566+ tests, about an hour). Run targeted files, and
  ask the owner to run anything longer. Say plainly what was and was not run.
- **Never run commands against shared or client servers.** Hand over a command sheet and let the owner run it.
  Never push, deploy, delete data, kill a process you did not start, or message anyone unless asked.
- Commits are authored `mehboob14`. Never add `Co-Authored-By` or any AI attribution to a commit message or
  PR text, even when your tooling suggests it.
- UI copy has no visible dashes: no em or en dashes, no lone dash placeholders (write None, Not set, No date).
  Less text. Popups for focused decisions instead of long scrolling. No subtitles under register titles. Trust
  copy names things Verity really enforces, never generic claims.
- When asked to draft a client message: short, casual, plain words, no technical detail, no prices.

## When something is unclear: ask, do not assume

This overrides any global "make the most reasonable assumption" preference for this project. Ask before:

- anything about what a compliance mapping, requirement or control legally means, or the text of a standard;
- schema, auth, tenancy, dependencies, connectors, module boundaries, API contracts;
- commits, pushes, deploys, server commands, deleting or resetting data, killing processes, long runs;
- anything in the "Open" list of [DECISIONS.md](DECISIONS.md), and anything the signed scope does not list.

For plain implementation choices (names, layout, local style), follow the surrounding code and state the
reading you took in one line.

## Before you stop (every session, every tool)

1. Update [STATE.md](STATE.md): what changed, what is verified (and what was not run), what is uncommitted,
   what is pending, what needs a decision. Bump its "Last updated" and "Verified against" lines.
2. Add an entry at the top of [CHANGELOG.md](CHANGELOG.md): date, tool, what, commit hashes if any.
3. If a rule, decision or pitfall changed, update [DECISIONS.md](DECISIONS.md) or [GOTCHAS.md](GOTCHAS.md).
4. Never write secrets here: no passwords, tokens, SMTP credentials, personal data. Say where they live.
5. Keep files short. Link to repo docs instead of copying them. If you find a statement here that is wrong,
   fix it now and note it in the changelog.

## What is in this folder

| File | Holds | Changes |
|---|---|---|
| START-HERE.md | this entry point and the rules | rarely |
| STATE.md | the current state: branches, uncommitted work, what is deployed, status by module, backlog | every session |
| ARCHITECTURE.md | how the product is built | when the design changes |
| WORKFLOW.md | machine setup, run, test, git, deploy and verification recipes | when a recipe changes |
| DECISIONS.md | decisions and why, plus the open questions | when decided |
| GOTCHAS.md | pitfalls that already cost time | when found |
| CHANGELOG.md | dated log, newest first | every session |
| tools/ | helper scripts: safe commit, test and demo environments, screenshots, demo seed | when scripts change |

## Keeping it local

This folder, and the entry files that point to it, are excluded through `.git/info/exclude`, which belongs to
this machine's clone and is never pushed:

```
/local-context/   /CLAUDE.local.md   /AGENTS.override.md   /.cursor/rules/00-verity-local-context.mdc
```

Check with `git check-ignore -v local-context/START-HERE.md`. Never `git add -f` these, never run
`git clean -x` here, and keep them out of any snapshot pushed to the client's GitLab.

**Backup and handoff (owner's decision, 2026-11-23).** A scrubbed copy of this folder (without session
tokens, the TOTP seed or the browser profile), its entry shims and the assistant's project memory travel
on the GitHub branch `handoff/verity-dev` in `docs/handoff/private/`, refreshed by
`tools/commit_paths.py snapshot`. That branch is GitHub only, never GitLab. `docs/handoff/README.md` there
is the new machine guide. A zip of the same also went to OneDrive.
