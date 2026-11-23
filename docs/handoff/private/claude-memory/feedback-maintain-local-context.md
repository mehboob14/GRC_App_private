---
name: feedback-maintain-local-context
description: "Verity has a local, git-excluded context pack (START-HERE, STATE, ARCHITECTURE, WORKFLOW, DECISIONS, GOTCHAS, CHANGELOG, tools) that must be read at the start and kept current at the end of every Verity session"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-11T08:01:34.604Z
---

On 2026-10-11 the user asked for md files (agents.md style) holding everything about Verity (how it is built, context, current state) so a new chat, Cursor or Codex starts properly without being told again, kept out of the repo, and updated as work moves on instead of relying on chat history.

Built at `C:\Development\Verity_GRC_Platform\local-context\` (START-HERE.md, STATE.md, ARCHITECTURE.md, WORKFLOW.md, DECISIONS.md, GOTCHAS.md, CHANGELOG.md, tools/). Excluded through `.git/info/exclude`, never committed. Entry shims that point at it: `CLAUDE.local.md` and `AGENTS.override.md` in the repo root, `.cursor/rules/00-verity-local-context.mdc`, and `CLAUDE.local.md` in the grc-s folder (sessions here start in grc-s, whose own CLAUDE.md is the old prototype's).

**Why:** chat context is temporary; the user does not want to re-explain the project to each tool.
**How to apply:** at the start of Verity work read START-HERE.md then STATE.md (run its verify commands). Before finishing any session that changed anything, update STATE.md (state, verified, uncommitted, pending, decisions needed, "Last updated"/"Verified against"), add a CHANGELOG.md entry, and touch DECISIONS.md or GOTCHAS.md if a rule or pitfall changed. Never put secrets in it. Do not commit or push it, and keep it out of GitLab snapshots. Related: [[verity-iso27001-built]], [[deploy-and-client-comms-style]], [[feedback-commit-attribution]], [[feedback-no-long-test-runs]].
