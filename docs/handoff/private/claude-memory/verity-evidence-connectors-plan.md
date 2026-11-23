---
name: verity-evidence-connectors-plan
description: "2026-11-23 R&D plan for every connector and control in docs/product/evidence-connectors (148 controls proposed, 127 new checks, 20 gating decisions); documents only, on the GitHub handoff branch"
metadata:
  node_type: memory
  type: project
  originSessionId: b2af17ce-bbe2-448f-8020-79779048c41f
  modified: 2026-11-23T12:34:27.590Z
---

Owner asked (2026-11-23) for a plan, not code: every connector (Entra, Okta, Google Workspace first, MDM, then
Jira, GitLab and the rest of Phase 2 and 3) mapped through assessment objectives to Verity's controls and both
frameworks, with credentials, connect UI, in product guides, Go collectors in mind, competitor research, and a
further breakdown of the 133 controls by framework nature.

Plan lives in `docs/product/evidence-connectors/` (README is the index; 04 is the build plan; 08 holds the 20
decisions that gate it) plus `openspec/changes/evidence-connectors-program/tasks.md`. Generators in its `tools/`
(merge.py, gen_docs.py, validate.py) regenerate 05 to 08 after coverage or check edits.

Key results: 11 splits and 4 additions proposed (148 controls, need qualified review); 127 new checks; all 16 full
check mappings should be partial; only 3% of artifact rows get a fully filling check by end of Phase 2 (93% partly),
so automation rule A or B matters; identity providers use two credentials behind one setup (Keycloak never holds a
directory read credential); devices, endpoint and HR need the client's scope extension; no endpoint agent yet.

**Why:** the owner wants agents to implement it package by package later.
**How to apply:** before building any connector or control change, read the package in 04 and its decisions in 08;
keep facts verified (official docs) and push changes to the handoff branch ([[feedback-github-handoff-branch]]).
Related: [[verity-keycloak-sso]], [[verity-common-control-framework]], [[verity-guided-onboarding-plan]].
