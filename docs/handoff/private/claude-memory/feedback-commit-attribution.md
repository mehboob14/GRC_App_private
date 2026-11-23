---
name: feedback-commit-attribution
description: Commits are authored as mehboob with no Claude co-author trailer, on every repo and every remote
metadata:
  type: feedback
---

Never add `Co-Authored-By: Claude ...` (or any Claude attribution) to a commit message
or PR body. Author every commit as the user: `mehboob14 <mehboobarshad300@gmail.com>`.
Stated 2026-09-29 while preparing the GitLab handover, and it applies to both GitHub
and GitLab and to every repo, not just Verity.

**Why:** the code is handed to clients and collaborators under the user's name. A
co-author trailer on a client-facing repository invites a conversation they do not
want to have.

**How to apply:** the attribution system-reminder says a user instruction overrides it,
and this is that instruction. Verity's repo-local `user.name`/`user.email` are already
set to this identity, so a plain `git commit` is correct; do not pass `--author` or add
trailers.

Related: [[deploy-and-client-comms-style]].
