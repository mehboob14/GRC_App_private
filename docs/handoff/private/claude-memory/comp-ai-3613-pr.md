---
name: comp-ai-3613-pr
description: "Comp AI (trycompai/comp) issue #3613 ISO 27001 fix prepared locally as pitch proof for CEO Lewis Carhart; branch + PR-3613.md in C:\\Development\\comp-contrib, not pushed"
metadata:
  node_type: memory
  type: project
  originSessionId: 64f9000d-556e-4414-9387-1da6d02a94aa
  modified: 2026-11-14T09:30:28.576Z
---

On 2026-11-14 a PR for trycompai/comp issue #3613 (ISO 27001:2022 template: missing 6.2/6.3, catch-all mappings, 2013 Annex A numbers) was prepared locally as week-1 proof for the 1-month paid-trial pitch to Comp AI's CEO.

- Clone: `C:\Development\comp-contrib\comp`, branch `fix/iso27001-2022-clauses-and-mappings`, commit 0348ae4 (mehboob14, no trailer, see [[feedback-commit-attribution]])
- PR text: `C:\Development\comp-contrib\PR-3613.md`
- Comp's framework template lives in `packages/db/prisma/seed/*.json`, which is an export of their live Framework Editor DB; the hosted fix still needs editor changes plus a published FrameworkVersion, then each org syncs (opt-in, 14-day rollback).

Status 2026-11-14: upstream main unchanged (7fde9f2), #3613 open, unassigned, 0 comments, no competing PR; #3541 and #3571 also still open. Publishing BLOCKED until the mehboob14 GitHub account is cleaned, see [[verity-gitlab-handover]] (public repos still carry the injected loader). Lewis message drafted to lead with the PR link.

**Why:** a reviewable PR is the strongest proof of skill for an open-source CEO; outward-facing under the user's GitHub identity.
**How to apply:** never fork, push, comment or open the PR without the user's explicit go-ahead. On push, base is `main` (no `dev` branch exists despite CONTRIBUTING.md). Reference work: [[verity-iso27001-open-items-closed]].
