---
name: verity-multiframework-design
description: "How Verity's data model supports multiple frameworks (ISO 27001, GDPR) and the gaps before it works"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-23T15:06:43.610Z
---

Verity is built framework-generic; SOC 2 is just the one shipped pack. How a second framework (ISO 27001, GDPR) attaches, and what's missing.

**Mechanism**: `Framework`/`FrameworkVersion`/`Requirement` are generic; `requirement_key` is globally unique and namespaced (`SOC2:CC6.1`, so `ISO27001:A.5.1` fits). The cross-framework identity is `control_templates.canonical_key` — deliberately NOT unique, so two packs shipping the same concept (same canonical_key) collapse into ONE tenant control (design ref D7a). That one control then carries `ControlRequirement` rows to criteria in BOTH frameworks = "one control satisfies both", provable via the crosswalk. `seed/loader.py:load_all` iterates every dir under `content/`, so a framework = drop a `content/iso27001/` pack (framework.json + requirements.json + control_templates.json + template_requirements.json).

**Gaps before it actually works**:
1. Loader is single-pack today: `_load_templates` and `_load_crosswalk` prune GLOBALLY (anything not in the pack being loaded is deleted), so a 2nd pack clobbers the 1st except shared canonical_keys. Prune must be scoped per-pack first.
2. No per-mapping rationale/coverage captured (all full/1.0/NULL) — needed for a defensible cross-framework crosswalk.
3. Current getprobo/probo dropped explicit criteria mappings (see [[verity-control-library-provenance]]), so ISO/GDPR mappings need another source or expert authoring.
4. `instantiate_library` dedupes tenant controls by template_id (fine, because loader already collapses templates to one per canonical_key).

Control code prefixes (2026-08-23): custom (tenant-authored) controls auto-code as `IC-NN` (Internal Control) via `control_service._next_custom_code`. Seeded SOC 2 controls are category-prefixed: BC, CS, DM, EP, GOV (Governance — renamed from GRC), HR, IAM, LM, NS, PE, SD. "GRC" is no longer used as a control prefix anywhere (migration e1a7c93d820b recoded GRC-→GOV- on control_templates + adopted controls; seed pack + _recode_map updated).

Update 2026-10-10: gap 1 (global prune) is fixed (per pack prune, sealed manifests). The blockers that remain for ISO are in [[verity-iso27001-plan]].
