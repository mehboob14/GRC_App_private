# ADR-0014: One Verity control framework, mapped to frameworks and automated through capabilities

**Status:** Proposed
**Date:** 2026-09-18

## Context

Verity ships SOC 2 today: 114 control templates mapped to the criteria by 150 rows, adopted per
workspace. Phase 3 signs ISO 27001, HIPAA and GDPR "on the same control engine", Phase 2 signs
connectors and continuous checks, and customers ask three things the model does not answer yet:
which systems can automate a control, whether Verity's own modules can serve as evidence, and how a
second framework reuses the work done for the first.

Facts that constrain the answer:

- Auditors test requirements of the framework they attest to. A crosswalk between frameworks is
  never exact: CISO Assistant's SOC 2 to ISO 27001 set marks every one of its 2,810 rows as
  "intersects". Deriving one framework's status from another's overstates compliance.
- NIST IR 8477 and OSCAL 1.2 (control mapping model, December 2025) standardise how a mapping is
  described: a set theory relationship, a rationale type, a strength and provenance.
- Framework text is licensed unevenly. NIST and HIPAA are public; EU law is reusable with
  attribution; AICPA, ISO and PCI text is not ours to ship; the SCF licence forbids derivatives
  without a commercial licence.
- Drata, Vanta and Secureframe converge on one pattern: a vendor owned control set, frameworks
  mapped to it, tests bound to controls, and "connect any one" provider per category.
- The content loader prunes globally, so loading a second pack deletes the first pack's rows.

## Decision

1. **Verity controls are the unit of work.** One framework neutral library with stable codes.
   Frameworks are requirement sets mapped to those controls. A requirement is met only when every
   published control mapped to it is implemented and passing. Compliance is never inferred between
   frameworks; reuse is through the shared control and its evidence.
2. **Mappings carry the IR 8477 fields**: relationship, rationale type, strength, coverage, written
   rationale, source, author and reviewer, published only after a second qualified reviewer signs.
   Exportable as CSV now and as an OSCAL 1.2 mapping collection later.
3. **Frameworks arrive as content packs** with a licence tier and a text policy, a maturity level
   (requirements only, mapped, automated), and new controls for anything the library does not meet.
   The loader prunes per pack.
4. **Tests bind to capabilities, not vendors.** A capability (version control) lists the providers
   that offer it (GitHub, GitLab, Bitbucket); one connected provider is enough. Unsupported systems
   are requested, and the control keeps its manual path. Not configured is derived and never counts
   as pass or fail.
5. **Verity is a provider.** Its modules publish capabilities, run platform tests with the same
   states as connector tests, and generate evidence reports (XLSX with fixed columns and a PDF cover
   with parameters, row count and hash). Screenshots are not generated.

Detail: `openspec/changes/common-control-framework/design.md`; requirements
`docs/product/control-framework-requirements.md`.

## Alternatives considered

- **Controls per framework** (a separate control set for SOC 2, ISO, HIPAA). Rejected: the same
  MFA control would be implemented, evidenced and reviewed three times, and customers would see
  three statuses for one fact.
- **Adopt the Secure Controls Framework as the library.** Rejected for shipped content: CC BY-ND
  forbids the edits a product library needs, and the commercial licence is a recurring cost
  without a product need yet. SCF stays an internal coverage checklist.
- **Infer status across frameworks from a crosswalk** (CISO Assistant's inferred results).
  Rejected as a source of truth; kept only as a draft suggestion a person confirms, because an
  inferred pass on an "intersects" mapping is not audit evidence.
- **Bind tests to individual integrations** (the prototype catalogue). Rejected: every new provider
  would need new tests and new control mappings instead of one implementation of existing tests.
- **Screenshots of module pages as evidence.** Rejected: an auditor cannot reperform a picture; an
  export with its filters, row count and hash is information produced by the entity they can test.

## Consequences

- A second framework costs a content pack and a review, not a schema change; overlap is visible
  before activation.
- The 150 SOC 2 mappings must be reviewed and given rationales, and the SOC 2 text must move to
  identifiers and summaries or be licensed. Both are release blockers for commercial sale.
- The automation catalogue can ship before any connector, so the control page shows automation
  options honestly from Phase 1 onward.
- The engine takes on mapping governance: two person review, content CI and pack provenance.
- Revisit if a customer needs a tenant defined control set that cannot map to the library, or if
  auditors start accepting OSCAL mapping collections as evidence of crosswalk quality.

## Update 2026-10-04: composition is part of the decision

The decision stood and was built further. A control page now answers the question an auditor asks
of it, "what proves this, and where does that come from", from content: every test says which
capability it needs, which systems supply it, what it collects and why it belongs to the control;
every control lists the evidence people and Verity modules provide; and every criterion can be read
top down as the chain of its controls, tests and evidence. The same content serves a second
framework unchanged, because tests and evidence attach to controls and never to a requirement.
Details: design section 4.5, requirements section 3A.

What the review of the shipped content found and this fixed: every mapping loaded as full cover
with no rationale, test to control links that claimed to verify whole controls from one setting,
manifests whose hashes no longer matched their files, and a loader that would have deleted SOC 2
when a second framework was loaded. What it did not fix and remains open: mapping review by a
qualified second person (task A5), the AICPA text decision (A4), and platform tests running
(C2).
