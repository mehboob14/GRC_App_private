---
name: verity-common-control-framework
description: "Spec (2026-09-18, uncommitted) for Verity's own control framework, capability-bound automation, modules as evidence and adding frameworks; files, decisions and the open questions the client must answer"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-18T18:13:51.276Z
---

Written 2026-09-18, not committed:
- `docs/product/control-framework-requirements.md` (requirement IDs CF, AU, ME, FW; ME rather than PE because PE-01/02 are physical controls)
- `docs/adr/0014-common-control-framework.md` (Proposed)
- `openspec/changes/common-control-framework/{proposal,design,tasks}.md`
- Pointers added in delivery-plan.md, data-model.md and the ADR index.

Decisions:
- Requirement status comes only from mapped controls; nothing is inferred between frameworks.
- Mappings carry the NIST IR 8477 fields and need a second reviewer.
- Tests bind to capabilities ("connect one of"). not_configured is derived.
- Verity is a built-in provider: platform tests plus XLSX reports with a PDF cover, no screenshots.
- Framework order: ISO 27001, HIPAA, GDPR, then CSF 2.0, NIS2/DORA, PCI once licensed, ISO 42001.

**Why:** the user wants production-ready planning for real audits, from SOC 2 toward ISO.

**How to apply:**
- Build from `tasks.md` groups A to E.
- Group C (module evidence) and the post-GDPR frameworks are extensions that need client agreement.
- Open questions to resolve first:
  - The signed section 8 catalogue has no HR or MDM/EDR connectors, so HR-05 and EP-* cannot be automated.
  - The frontend `connector-catalogue.ts` (40 providers) does not match section 8.
  - AICPA text licence.
  - Who is the second reviewer.

Related: [[verity-control-library-provenance]], [[verity-multiframework-design]], [[verity-linkage]].

**Status 2026-10-03:** D7 (scoping and exclusions with reasons on the evidence) is built for GitHub repositories, and D6 now rolls automated status into readiness with CF-4 enforced (`compliance/readiness.py`); AU-7 window coverage in readiness is still open. See [[verity-connectors-github]].

**Status 2026-10-04:** composition built (EC-1..10 in spec section 3A, tasks section F): coverage and rationale on every mapping, evidence kinds, expected evidence, Checks tab, criterion view, per pack loading, stale state. A1 partial (relationship, strength, reviewer open), A2 done, A3 partial, C4 done, C1/C2 catalogue only. See [[verity-evidence-composition]].
