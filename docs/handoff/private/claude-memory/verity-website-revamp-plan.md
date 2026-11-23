---
name: verity-website-revamp-plan
description: 2026-10-16/18 plan for the security plus compliance website revamp (Oneleet reference, leave the Harness copy), owner decisions, direction board URL, Vimeo placeholder logo in the app
metadata:
  type: project
---

Faheem asked for a revamp: compliance plus security sold as one offer ("as a service"), more colour, premium, animated, a mascot, a landing page framework. The owner also wants to drop the Harness look: the previous `revamp-public-website` change copied Harness element by element, and the website's cube logo was drawn to match that art.

Plan: OpenSpec change `openspec/changes/security-compliance-website/` in the worktree `C:\Development\Verity_site` (branch feat/website-deploy, uncommitted). Direction board (phase 0 draft, private): https://claude.ai/artifact/B1JiEhCzntkdEe5jXWHdMf.

Owner decisions (2026-10-16): Managed service planned, not staffed, so Coming soon with register interest; partner products (MDM, Keycloak identity, a third product) inside the offer as Coming soon; pricing shows the model, no numbers; mascot = a block shaped guardian, now drawn flat and derived from a new Verity mark (concepts A Tick V, B Seal, C Guardian face; board recommends C).

Design direction: Sora + Inter (the product design system), five tones Paper, Mist, Sky, Deep, Ink from the DS ramps, optional seal gold, StoryBrand homepage of 13 sections, motion only for state changes. Faheem's open answers are D1 to D8 on the board.

**Why:** the user is accountable to Faheem; this work was requested, so it can be scoped and priced (unlike the first site).

**How to apply:** build in the Verity_site worktree after Faheem signs off the board; never claim Managed or partner products as live; keep Coming soon in proportion. The app's brand mark (`frontend/src/components/ui/brand-mark.tsx`) is a placeholder whose comment says it is the Vimeo logo, shown on the deployed sign in page and vendor portal: flagged, not changed. Related: [[verity-website-deploy]], [[verity-commercial-thread-2026-10]], [[verity-design-reskin]].
