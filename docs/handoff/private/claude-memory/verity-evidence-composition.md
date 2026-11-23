---
name: verity-evidence-composition
description: "2026-10-04 (uncommitted): Vanta/Drata style chain requirement to control to check to evidence built on the SOC 2 library; Checks tab, register marks, criterion view, sealed content, GitHub accuracy; what is still open"
metadata:
  node_type: memory
  type: project
  originSessionId: 6ccef17a-c871-4bbb-87d0-d988eb0d9721
  modified: 2026-10-03T16:04:10.343Z
---

Built 2026-10-04 in `C:\Development\Verity_GRC_Platform`, all uncommitted, after the user asked for the control library to be Vanta/Drata style and accurate ("which requirements map to which evidence", "a control can need several connectors or manual work and should say so", a Checks tab per control, ISO 27001 later) and attached two identical Codex review reports (`GRC_Mapping_Verification*.html`, repo at 61929d1).

What exists now:
- Migration `a7d3f19e2c58` (head): `checks.evidence_kinds`, `control_template_checks.rationale`, `control_templates.evidence` (JSONB) and `.pack`; BC-08 gets P6.4 on unedited tenant controls. Round trip tested on `verity_test`.
- Content (`seed/content/soc2`, `automation`): coverage + rationale on all 167 requirement links, rationale on 101 check links (16 full: full only when the control has that one check), `evidence_kinds` on 81 checks, expected evidence on 116 controls (design/operating, cadence, upload or Verity module, `automated_by` check keys). 116 controls (new SD-13 deployments, SD-14 traceability for CC8.1), 81 checks (7 runnable on GitHub, 18 platform `verity.*` planned, 4 new CC8.1 chain checks), capabilities `ci_cd` and `verity_*`.
- `connectors/composition.py` (pure rules; mode automated/hybrid/manual is by design, today's state is separate counts), `chain_service.py` in compliance, endpoints `GET /controls/{id}/automation` (extended), `GET /control-composition`, `GET /requirements/{id}/chain`.
- UI: Checks tab (`checks-panel.tsx`, shared words in `composition-meta.ts`/`composition-ui.tsx`, `automation-meta.ts`), marks beside each code in the controls register, criterion dialog opened from Frameworks ("How it is met") and a control's Requirements tab.
- Loader: per pack pruning, mappings per framework, refuses mappings without coverage+rationale, refuses packs whose files differ from the sealed manifest (hash over LF-normalised bytes). `backend/scripts/seal_content.py` must be run after ANY content edit (`--check` to verify); a unit test enforces it. Probe framework test in `tests/integration/test_content_loader.py` proves ISO can load beside SOC 2.
- GitHub: effective approvals (last decision before merge, no after-merge/withdrawn/dismissed/author), unreadable ruleset is error not fail, up to 100 merged PRs / 500 closed PRs and "complete" flag, admin bypass said, `rule` stamp on results, digest includes detail, `stale` after 48h (blocks readiness; dashboard folds it into "could not check").
- Docs: spec section 3A (EC-1..10), design 4.5, tasks section F, ADR-0014 update, `docs/product/mapping-review-2026-10.md` (status of each Codex finding F01..F20), user guide chapters 2, 3, 11 + new images, connectors README.

Why: the old Automation tab showed only a declared sub type and a bare check list; 49 of 116 declared sub types disagree with what the checks and evidence imply, and every crosswalk row loaded as full with no reason.

How to apply:
- Deploy order on the live server: pull, build, migrate (`a7d3f19e2c58`), `seed-content`, THEN `python -m scripts.backfill_adopt_soc2` in the api container so existing workspaces adopt SD-13 and SD-14. Hand commands over, do not run them.
- Never add a column to the controls register: at 1440px Status already sits at the edge, so sources are drawn inline beside the control code.
- `DialogBody` has `-mx-6 px-6`; inside a `p-0` dialog use a plain padded div.
- Demo stack for screenshots: scratchpad `run_api_guide.py` (verity_guide DB, Redis 3, fake GitHub 8765 from the integration test's `RecordedGitHub`), `shot.py` with `SHOT_H`. History strip aggregates results across connections, so a switched account shows yesterday's passes; remove it by DOM before a "nothing to verify" shot.
- Open: evidence slots (readiness requiring items), platform runner (C2), collectors for SD-13/SD-14 (GitHub deployments, CI runs, Jira), second reviewer for mappings (A5), AICPA text (A4), align declared `control_sub_type`, per-control evidence projections, versioned check definitions.

Related: [[verity-common-control-framework]], [[verity-connectors-github]], [[verity-control-library-provenance]], [[verity-user-guide]].

Verified 2026-10-04: 699 unit tests, 312 integration + isolation tests (40 min), connector + loader modules re-run on the final code (15), ruff, mypy, import-linter (18 kept), seal check, tsc, eslint, vite build; migration chain from an empty database, round trips and a from scratch seed on a scratch DB; pages checked in a browser against the demo workspace. Not deployed, not committed. A `PERMISSION_KEYS` gap (connectors:*, risks:*) was spun off as a task chip.

