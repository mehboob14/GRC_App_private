---
name: verity-documents-approval-tiers
description: "Document approval tiers rebuilt as multi-assignee (users/roles/groups), auto-notify, auto-publish, dedicated decision page; campaign dialog UI redesign"
metadata: 
  node_type: memory
  type: project
  originSessionId: f15d1444-2a71-44b8-bd6d-15988000f78a
  modified: 2026-09-03T14:44:47.928Z
---

**VERITY DOCUMENT APPROVAL TIERS REBUILD (2026-09-03).** User's ask: Owner card gets an
"Assign" button; Tier 1/Tier 2 cards get inline multi-assignment (users/roles/groups) with
their own "Assign" button; delete "Send for review" — assigning tier 1 IS what starts the
review and auto-notifies; decisions happen on a dedicated page reached from a notification
(view content + metadata, comment, type a word to confirm — same shape as the acknowledgement
campaign flow); once the last tier clears, auto-publish, no manual step; approval/review vs
acknowledgement campaigns are explicitly different features, never merged. Plus: redesign the
"Start an acknowledgement campaign" dialog UI. See [[verity-documents-ack-campaigns]],
[[verity-documents-module]].

## Backend (documents module)

**Model change**: `DocumentApproval.approver_membership_id` (one approver per tier) dropped.
Two new RLS-forced tables: `DocumentApprovalTarget` (what the owner picked — user/role/group id
+ a snapshot name) and `DocumentApprovalAssignee` (who that resolves to today, their own
`decision` pending/approved/rejected, and `source_target_ids: JSONB` — every target id they
satisfy, since one person can be named directly AND pulled in by a role in the same tier).
Migration `20260903_1000_document_approval_multi_assignee.py` rev `afedee6a313a` ←
`e2a5c7d93f42`, applied.

**Completion rule** (locked by user's answers): a named user must decide themselves; a role or
group is satisfied by ANY ONE of its resolved members. `_tier_satisfied()` checks stored target
ids against stored assignee decisions — NOT re-resolved live, so a role/group membership change
after assignment doesn't retroactively lock/unlock a tier. Any single rejection kills the tier
immediately (no "wait for everyone" on reject). **Real bug caught by the smoke test**: the first
draft of `_tier_satisfied` selected `DocumentApprovalTarget.id` (the row's own PK) instead of
`.target_id` (the actual person/role/group id) — silently made every tier require re-approval
forever. Caught because the smoke test asserted the exact sequence, not just "no exception".

**State machine** (`assign_approval_tier` + `decide_approval_tier`, replacing the old
`submit_for_approval`/`decide_approval`): assigning tier 1 on a draft/expired doc IS the start —
flips lifecycle to `needs_approval`, notifies immediately, no separate submit step. Tier 2 can be
staged any time (targets saved, `status="not_started"`) but only ACTIVATES (notifies) once tier 1
is `approved`; tier 2 assignment before tier 1 has ever been assigned is refused ("Assign tier 1
first"). Deciding the LAST tier's final requirement auto-publishes in the same transaction
(`approved` -> `published`, two separate audit rows, no manual publish click). Rejecting resets
lifecycle to `draft`; reassigning tier 1 on a draft/expired doc wipes all tier rows and starts
fresh (old decisions gone). `publish()` endpoint kept as an unused manual fallback.

**Audit action vocabulary is fixed** (`Literal["create","update","delete","transition","approve"]`
in `audit/models.py`) — custom strings like "assign"/"decide" fail mypy. Used `update` for
assignment, `approve` for a person's decision (regardless of approve/reject outcome).

**New endpoints**: `POST /{id}/approvals/{tier}/assign` (require_manage, replaces `/submit`),
`POST /{id}/approvals/{tier}/decide` (require_approve at the router gate PLUS a service-layer
check that the actor is actually an assignee of that tier — rule 7's object-level scope on top of
the flat permission), `GET /approvals/pending` + `/approvals/pending/count` (mirrors the existing
`/campaigns/pending` pattern exactly, for the bell).

**Verified live**: a direct-service smoke harness (rolled back) proved named-all + group-any-one
completion, sequential tier activation, auto-publish on the final decision, an outsider refused,
double-decide refused, tier-2-before-tier-1 refused, and reject-then-resubmit clearing stale
state — against real tenant data. ruff/mypy/import-linter all clean (89 files, 17/17 contracts).

## Frontend (documents module)

- `types.ts`: `ApprovalTier.approver` (single name) replaced by `targets: ApprovalTarget[]`,
  `assignees: ApprovalAssignee[]`, `my_decision`. New `PendingApproval` type.
- `recipient-picker.tsx` + `use-recipient-options.ts` (split: component vs hook+constants, same
  react-refresh-lint reason as earlier splits this session) — the People/Roles/Groups picker was
  DUPLICATED verbatim inside `create-campaign-dialog.tsx`; promoted to one shared pair used by
  both the campaign dialog and the new tier-assign dialog.
- `tier-approval-card.tsx` + `assign-tier-dialog.tsx`: the Tier 1/Tier 2 cards on
  `document-detail-page.tsx`'s Overview tab (replacing the old compact "Approval" status list +
  the separate "Owner" panel's position). A card the backend hasn't created a row for yet
  (a fresh draft) is synthesized client-side via `tierCards()` so there's always an Assign
  affordance — the backend only creates tier rows once first assigned.
- Owner card gets its own "Assign" dialog wrapping the EXISTING `iam/components/owner-select.tsx`
  (`OwnerSelect`) — did not rebuild a person picker, that component already existed and fit.
- **`document-approval-page.tsx`** (new, route `/documents/:documentId/approvals/:tier`): mirrors
  `campaign-page.tsx`'s shape (DetailHeader, DocumentContentViewer, a Document facts card, a
  roster card) but for one tier's decision. ONE confirm text input serves both intents: typing
  "approve" enables the Approve button, typing "reject" enables Send-back — reuses the exact
  "type a word to confirm" idiom the campaign flow already had, rather than inventing a second
  mechanism.
- **Correction to my own earlier belief**: I had thought the "type ACKNOWLEDGE to confirm" input
  (the user's very first ask in this document-approvals thread) was never built. Re-reading
  `campaign-page.tsx` found it already fully implemented (`ACK_WORD`, `ackConfirm` state, the
  input + help text) — done in an earlier, now-compacted part of this session. Did not redo it;
  used it as the template for the new approval page instead.
- `acknowledgements-bell.tsx`: merged pending campaigns AND pending approvals into one dropdown
  (`PENDING_APPROVALS_KEY` alongside the existing `PENDING_CAMPAIGNS_KEY`), each item opening its
  own page in a new tab (`noopener,noreferrer`) — the existing campaign convention, kept for both.
- `create-campaign-dialog.tsx` UI redesign (the literal screenshot complaint): added a one-line
  explainer under the title, a "Recipients" section header with a live "N reviewers, M approvers
  selected" summary, small icons (users/shield/layers) on the People/Roles/Groups sub-labels
  (added to the now-shared `RecipientPicker`, so the tier-assign dialog got them for free too), a
  clock icon on the due-date label, `space-y-4` -> `space-y-5` for more breathing room.
- Removed: "Send for review" button + its dialog, the top-header Approve/Reject/Publish buttons
  (decisions now happen only on the dedicated page; lifecycle basically never rests at "approved"
  long enough to show a Publish button anyway, since the last decide auto-publishes in the same
  request).

**Verified**: `npm run typecheck` (`tsc -b`, the project's REAL command) clean, full `eslint`
clean, production `build` clean. Backend restarted to pick up the new router paths (openapi
confirmed all 4 new endpoints); a stale backend from an EARLIER unrelated fix in this session was
still running and had none of them — always re-check `/openapi.json` after a router change, don't
assume a prior restart covers a later edit.
