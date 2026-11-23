---
name: verity-risk-register
description: "Week-7 risk register built full stack (openspec week7-risk-register, migration b6d2e8f41a37); decisions, gotchas hit, pre-existing failing IAM/provider tests, headless verification workaround"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-14T07:15:18.854Z
---

Risk register (Deliverable 1.2) built 2026-09-14 in C:\Development\Verity_GRC_Platform, left UNCOMMITTED (user had not asked to commit).
Plan: `openspec/changes/week7-risk-register/` (proposal, design §1 tables, risk-decisions R1..R16, tasks) + `docs/product/risk-management-requirements.md` (Phase 2/3 ERM + Vanta/Drata parity backlog; the signed .docx stays untouched).

Key readings taken: matrix/bands/taxonomy live on each register (ER keys matrix by tenant); `accepted` only via an approved acceptance, requester can never approve (DB CHECK + service), risk owner may; expiry job `sweep_risk_register` reopens; treatment actions are tasks linked `remediates`; business unit = IAM group; AI assist falls back to closest starter-library risk (no AI key in local .env); later-phase ERM shown as "Soon" (TabStrip got a `soon` flag).

Gotchas hit:
- `get_risk` must `session.flush()` before the populate_existing load, or unflushed changes vanish (autoflush off).
- `AuditService.snapshot(row)` after flush on a row with server `onupdate` column raises MissingGreenlet; pass explicit `fields=`.
- `op.drop_constraint` needs `conv(name)` or the naming convention double-prefixes it.
- Chaining alembic commands through `| tail` hides failures; a failed upgrade let `downgrade -1` run on verity_test. Use `set -o pipefail`.
- The vendor jobs' notification kinds (`vendor_reassessment_due`, `vendor_document_expiring`) were refused by `ck_notifications__kind_valid` until this migration widened it.

Pre-existing, NOT caused by this work: 40 integration failures in test_iam_auth / test_iam_management / test_provider_auth / test_provider_tenants (tests expect old built-in roles like Auditor/Compliance Manager; provider audit stream empty). Confirmed identical on commit 1e27f93 via a throwaway worktree.

Verification: the Claude Browser MCP tools were unavailable ("reserved name"); ran API/Vite via background Bash + scratchpad `shot.py` CDP screenshots. On Windows, TaskStop leaves the node child alive; find it with Get-NetTCPConnection on the port and stop it. Dev workspace dana+2a956e now has 15 seeded risks and an ISO 27001 register. See [[verity-vendors-module]], [[verity-tests-wipe-database]].
