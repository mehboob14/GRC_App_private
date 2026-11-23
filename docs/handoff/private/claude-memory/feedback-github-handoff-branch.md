---
name: feedback-github-handoff-branch
description: "Owner's standing rule since 2026-11-23: keep specs current and commit and push Verity work to the GitHub branch handoff/verity-dev as it lands; never touch GitLab for this"
metadata:
  node_type: memory
  type: feedback
  originSessionId: b2af17ce-bbe2-448f-8020-79779048c41f
  modified: 2026-11-23T10:17:58.395Z
---

Since 2026-11-23 (owner moving machines): every piece of Verity development or R&D also updates its specs
and docs, and gets committed and pushed to the GitHub branch `handoff/verity-dev` (code, specs, agent
files, website, and the scrubbed notes copy in `docs/handoff/private/`). GitLab is not touched by this;
only the owner decides GitLab snapshots.

**Why:** the owner moves to another machine and wants one branch that always holds the full current state.
The GitHub account was used for the 2026-10-19 malware push, so every push report gives the tip hash for
the new machine to verify against.

**How to apply:** at the end of each piece of work, `python local-context/tools/commit_paths.py snapshot
--message-file msg.txt` then `push --branch handoff/verity-dev` (never force, never tags); prefer logical
commits first. Commit authored mehboob14, no AI trailer ([[feedback-commit-attribution]]). New machine
guide: `docs/handoff/README.md`. Related: [[verity-gitlab-handover]], [[feedback-maintain-local-context]].
