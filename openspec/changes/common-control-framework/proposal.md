# Common control framework: one library, reviewed mappings, capability automation, module evidence

## Why

Verity runs on SOC 2 today, and the signed plan adds connectors and monitoring (Phase 2) and ISO
27001, HIPAA and GDPR on the same control engine (Phase 3). Four questions decide whether that
works for real audits:

1. Is Verity's control library a framework of its own, with the real requirements mapped behind
   it, the way Drata's DCF and Vanta's controls work?
2. Can a control page say which systems automate it (version control needs one of GitHub, GitLab
   or Bitbucket) and keep monitoring it over time?
3. Can Verity's own modules (assets, vulnerabilities, risks, vendors, policies) be the evidence?
4. How does a new framework join the library: reuse overlapping controls, add new ones, stay
   defensible to an auditor, and respect the publisher's licence?

## What changes

- **The control library becomes the Verity control framework.** Controls gain objective, test
  procedure, evidence guidance, frequency, applicability and deprecation. Mappings gain the NIST
  IR 8477 fields (relationship, rationale type, strength, rationale, source, reviewer) and a draft,
  reviewed, published state. Requirement status comes only from mapped controls; nothing is
  inferred between frameworks.
- **An automation catalogue as content.** Capabilities, providers, tests and their capability
  rules load from a pack, so the control page shows an Automation panel ("connect one of"), and a
  Request an integration path, before any connector exists. Phase 2 connectors then run the tests,
  keep results append only, raise findings and show observation coverage.
- **Verity as a built in provider (extension).** Platform tests on module data and XLSX evidence
  reports with a PDF cover sheet, attached to the mapped controls and renewed on schedule.
- **Framework packs.** A licence tier and text policy per framework, per pack loading, content CI,
  two person review, an overlap preview on activation, the ISO Statement of Applicability, HIPAA
  required and addressable, and version transitions.

## Scope by phase

| Group | Phase | Signed |
|---|---|---|
| A Content foundation, SOC 2 text and mapping review | Before Phase 2 | Supports 1.1 |
| B Automation catalogue and Automation panel | Before Phase 2 | Supports 2.1 |
| C Verity module evidence | Phase 2 | Extension |
| D Connector framework and monitoring | Phase 2 | Signed (2.1, 2.2) |
| E ISO 27001, HIPAA, GDPR | Phase 3 | Signed (3.1) |
| E Other frameworks, custom frameworks, OSCAL | Later | Extension |

## Impact

- Additive migrations only: new nullable columns and new tables with defaults. Existing
  adoption, readiness, evidence and linkage keep working unchanged.
- New global content tables (no `tenant_id`, read only) and new tenant tables with forced RLS,
  audit rows and working downgrades (rules 1, 2, 5, 12).
- The content loader moves from a global prune to a per pack prune (fixes a known week 2 gap).
- The hardcoded connector catalogue in the frontend is replaced by content that follows the signed
  section 8 catalogue.

## Not in this change

Automated answering of security questionnaires, an endpoint agent, SOC 1 and SOC 3, and any
framework text a licence does not allow. HR and device management connectors are not in the signed
catalogue and wait for agreement (requirements, question 1).

## Risks

- The SOC 2 pack carries verbatim AICPA text today: fix before commercial sale.
- Mapping quality depends on a qualified second reviewer; without one, packs stay drafts.
- Platform evidence is new scope; it is proposed, not assumed.
