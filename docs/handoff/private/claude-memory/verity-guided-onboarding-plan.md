---
name: verity-guided-onboarding-plan
description: "Guided onboarding (SOC 2 + ISO 27001) in Verity: 8 phases, all buildable gaps and assessment objectives wave 1 built uncommitted by 2026-11-23 (head 3f6a8c2d7e91); owed owner answers"
metadata:
  node_type: memory
  type: project
  originSessionId: 82e8670c-b448-4307-8bce-6caa63c036c9
  modified: 2026-11-21T19:15:22.952Z
---

Plan (2026-11-21): `C:\Development\Verity_GRC_Platform\docs\product\guided-onboarding\` (README with D-1 to D-16,
parts 01 to 05, appendix A) and `openspec/changes/guided-onboarding/` (proposal, design with a section 12 of build
deviations, tasks in 8 phases with [x], [~], [ ] per task). Research notes in `grc-s\research_notes\Guided onboarding plan\`.

Owner decisions: proceed (D-1), log all out-of-scope work in `phase_out_1.md` (no prices; rows 1 to 34 so far), ISO
without SOC 2 (D-2), SOC 1 guidance only (D-3), shared scope items decided per framework (D-6), Compliance Manager
role (D-12). Owner said "finish the entire plan" on 2026-11-21.

Built by 2026-11-22, all uncommitted, Alembic head 2c7d9e4f6a18 (dev DB `verity` not migrated; verity_test and
verity_guide are). Phases: 1 Get Started, 2 profile, 3 engagements and scope, 4 owners and required documents, 5
suggestions (computed, only decisions stored), baseline, plan raised as tasks, SoA versions, setup flow, `GUIDED_SETUP`
flag; 6 country panel in `modules/regulations` (83 AI drafted entries, hidden unless `REGULATIONS_SHOW_DRAFTS`); 7
assurance records and findings, description inputs, approved-outside-Verity documents, SOC 1 guide; 8 AI drafts with
offline templates and injection tests.

2026-11-23: every buildable gap closed and assessment objectives wave 1 built (modules/objectives, sealed pack of
163 objectives on 35 controls, draft_unreviewed, shadow outcomes with a comparison report, no readiness switch until
the owner picks automation rule A or B). A Keycloak SSO session shares the checkout and verity_test; test on a private
clone verity_test_ob; its migrations sit between mine (head 6a1f9d3c8e25 at end of day).
Owner answered all open decisions by click on 2026-11-23 (recorded in local-context/DECISIONS.md): D-4 keep AICPA
text for now, D-5 ship Openlane rewrites as drafts, D-8 show law entries with disclaimer, D-9 ISO auditor + SOC 2 CPA,
D-10 apply mapping fixes with notice, D-13 no website prefill; objectives rule B, reviewed evidence only, switch after
review, write all controls (591 objectives on 133 controls done).

**Why:** the owner wants the spec to stay the record and every out-of-scope piece priced separately.

**How to apply:** before committing, ask the owner to run the full backend suite (only targeted tests ran). Owed: the independent review (D-9) and the owner's sign off
on the objectives comparison report. What is still open is in tasks.md: 6.7 legal review, 8.3, content L1/L3/L6, objectives for the
other 98 controls and their review (O2). Test env has an expired AI key: force `api_key=None` in tests.
Related: [[verity-iso27001-built]], [[verity-common-control-framework]], [[feedback-no-long-test-runs]].
