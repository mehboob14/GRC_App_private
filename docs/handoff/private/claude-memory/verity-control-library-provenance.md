---
name: verity-control-library-provenance
description: "Where Verity's 114 SOC 2 controls come from, how they map to criteria, and the commercial/legal gaps"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-23T11:28:07.365Z
---

Verity's SOC 2 control library provenance and accuracy, as of 2026-08-23 (matters for commercialization + multi-framework).

**Source of truth**: seed content packs at `backend/src/verity/seed/content/soc2/` (control_templates.json=114, requirements.json=61 criteria, template_requirements.json=150 mappings, MANIFEST.json has SHA256 per file). Loaded by `seed/loader.py` into global `control_templates`/`requirements`; each tenant gets copies in `controls` via `control_service.instantiate_library`.

**Derivation**: the 114 controls derive from **getprobo/probo** (MIT license). The grc-s prototype's `backend/transform_frameworks.py` states it "convert[s] Probo framework catalogs". Prototype `backend/app/control_library.json` carries probo's schema (canonical `key`, `## Why?/## How?` markdown, importance MANDATORY/PREFERRED, `mappings:[{code,framework}]`). Our seed split Why→description, How→implementation_guidance. Criterion TEXT was replaced 2026-08-18 with **verbatim AICPA Trust Services Criteria** (2017/2022) — AICPA TSC is copyrighted; reproducing verbatim in a commercial product is a licensing risk to flag.

**Accuracy (structural, verified)**: all 61 criteria covered by ≥1 control, 0 controls mapped to nothing, 0 dangling refs. 27 criteria have only 1 control. BUT mapping *correctness* (does control X truly satisfy criterion Y) has **no documented validation methodology** — neither our seed nor probo's README states how mappings were reviewed. `TemplateRequirementMap.coverage/weight/rationale` exist but seed leaves them full/1.0/NULL, so no per-mapping justification is captured.

**Current probo diverged**: at the cited commit d76d8bf, probo restructured controls into thematic `.md` (core/operations/personnel/physical/transparency, codes like PER.ACC.006, tiers Mandatory/Optional/Advanced) with **no explicit criteria mappings** — so you cannot re-sync mappings from current probo; our 114 are an older snapshot.

**Commercial to-dos**: add probo MIT attribution notice to the repo; get legal read on AICPA TSC verbatim text; commission an expert review of the crosswalk and populate rationale/coverage. See [[verity-multiframework-design]] for how ISO/GDPR would attach.
