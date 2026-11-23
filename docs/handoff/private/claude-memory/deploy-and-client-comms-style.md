---
name: deploy-and-client-comms-style
description: "On shared/client servers, hand over commands instead of running them; client-facing messages must be short, casual, non-technical"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-18T07:16:49.754Z
---

Two standing preferences, both given while deploying to a shared Contabo box
(37.60.228.227) borrowed from a colleague:

1. **Do not execute commands against client/shared servers.** Write the commands
   out and let the user run them. This applies to SSH, key generation, and
   anything touching the remote host — the user stopped a local `ssh-keygen`
   mid-call and said "don't run any command by yourself".
2. **Client-facing messages: short, casual, human, no fluff.** Plain language,
   not technical detail. The user rewrote drafts twice to cut them down.

**Why:** the server hosts other people's live services (VantageCast relay +
a 7-month-old Keycloak stack). The user is accountable to the person who lent
it, so they want to see and approve every remote action, and the person they
report to is not an engineer.

**How to apply:** for remote/shared infra, produce a command sheet with a
read-only survey first, and state clearly what each step touches. For messages
to a colleague or client, keep it to a few plain sentences — name what was
looked at, what's needed, and what the risk is, and skip the reasoning.

Related: [[verity-grc-platform]]
