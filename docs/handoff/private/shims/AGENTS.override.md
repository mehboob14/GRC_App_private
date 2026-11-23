# Verity local override for Codex (local only: never commit this file)

This file replaces the tracked `AGENTS.md` for Codex on this machine, so read these, in order, before any work:

1. `AGENTS.md` (the repo's Codex guide) and `CLAUDE.md` (the non-negotiable rules), then `backend/CLAUDE.md` or `frontend/CLAUDE.md`.
2. `local-context/START-HERE.md`, then `local-context/STATE.md`. They hold the current state, the commands and the pitfalls that
   the tracked docs do not. If they are missing, stop and tell the owner.

Never forget (the full list is in START-HERE.md):

1. HEAD of this checkout is `codex/public-website`, but the files on disk are another branch plus uncommitted work. Do not run
   `git status`, `git add -A`, `git commit`, `git checkout`, `git pull`, `git stash` or `git diff <branch>`. Commit only when the
   owner asks, with `local-context/tools/commit_paths.py`.
2. Integration and isolation tests TRUNCATE the database they point at. `source local-context/tools/env_test.sh` first
   (verity_test). Never run the full backend suite: give the owner the command.
3. Postgres (5433) and Redis (6379) run in WSL and die when WSL idles. Ports 8000 and 8001 belong to the owner's other projects.
4. Never run commands against servers, push, deploy, delete data or message anyone unless asked. Commits are authored
   `mehboob14` with no AI attribution.
5. If a requirement, mapping or scope is ambiguous, or it touches schema, auth, tenancy, dependencies or connectors: ask. Do not
   assume. For this project this overrides the global "make the most reasonable assumption" preference in `~/.codex/AGENTS.md`.
6. UI copy has no visible dashes. Less text, popups for focused decisions.
7. Other tools work in this directory too: preserve unrelated and uncommitted work, do not tidy files you were not asked to change.
8. Before you stop: update `local-context/STATE.md` and add an entry to `local-context/CHANGELOG.md`.
