---
name: verity-module-header-pattern
description: "Every Verity module root puts icon, live count subtitle and its buttons in the shell top bar; registers keep only search and filters"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-14T15:40:53.957Z
---

As of 2026-09-15 (uncommitted) Risks, Vendors, Assets, Vulnerabilities, Controls, Evidence, Documents and Tasks all follow one shape: `PageHeader` with `icon`, a live `subtitle` ("N open · N critical", zero parts dropped) and `actions` (secondary buttons, primary Add last), then `TabStrip variant="bar"` with counts. PageHeader portals actions into the app shell top bar. Dialogs opened from the top live in the module layout and reach pages through a typed outlet context (`risks-outlet.ts`, `vendors-outlet.ts`, `assets-outlet.ts`, `vulnerabilities-outlet.ts`, `tasks-outlet.ts`). Vulnerabilities gained a real layout with nested routes; import and detail stay outside as drill downs. Detail pages put actions in `DetailHeader actions`.

When a header Export needs register state, lift it without render loops: a ref (assets) or a memoized rows array set in an effect (vulnerabilities).

**Why:** user asked for every module to match the risk register and vendor UX. **How to apply:** new modules copy `risks-layout.tsx`. Related: [[verity-ui-consistency-primitives]], [[verity-risk-register]].
