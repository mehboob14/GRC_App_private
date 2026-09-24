# Tasks: common control framework, automation, platform evidence, new frameworks

Ordered so each step ships on its own and nothing existing breaks. Phase labels follow the signed
specification; items marked **extension** go beyond it and are agreed before they are scheduled.
Requirement IDs refer to `docs/product/control-framework-requirements.md`.

## A. Content foundation (small, before Phase 2)

- [ ] A1 Migration: additive columns on `control_templates`, `requirements`,
      `template_requirement_map` (relationship, rationale type, strength, source, status, author,
      reviewer), `frameworks.maturity`; `requirement_transitions`, `framework_packs`. Downgrade
      tested. (CF-2, CF-3, CF-10, FW-2)
- [ ] A2 Loader: prune per pack instead of globally; write `framework_packs`; print a diff; refuse a
      pack that breaks its `text_policy`. (CF-8, FW-1)
- [ ] A3 Content CI: every requirement mapped or marked with a reason; rationale and reviewer on
      every published mapping; no dangling keys; manifest hash matches. (FW-3)
- [ ] A4 SOC 2 pack: replace verbatim TSC wording with identifiers and Verity summaries, or record
      AICPA permission; backfill mappings as published but unreviewed. (CF-8, open question 3)
- [ ] A5 Mapping review: a qualified second reviewer signs relationship, rationale type, strength,
      coverage and rationale for the 150 SOC 2 mappings, including the LM-01 to CC6.1 note. (CF-3,
      open question 4)
- [ ] A6 Probo MIT attribution notice in the repository. (CF-10)
- [ ] A7 Crosswalk CSV export per framework. (CF-9)

## B. Automation catalogue in the product (small, before Phase 2)

- [x] B1 Content pack `automation/`: capabilities, providers from the signed section 8 catalogue
      with delivery phase, tests, capability rules, implementations (all `planned`), template to
      test map for the 57 automated and hybrid controls. (AU-1, AU-2, AU-4)
      Built: 59 checks over 13 capabilities; 53 of the 57 controls mapped. DM-03, GOV-06,
      GOV-16 and PE-02 have no connector test yet and show the request path.
- [x] B2 `GET /controls/{id}/automation` and the control page Automation panel: tests, "connect one
      of" providers per capability with their status, and "Request an integration". (AU-1)
- [ ] B3 `integration_requests` table and dialog; provider plane list for triage. (AU-3)
      Built: table, dialog, list per control and workspace. Open: the provider plane list.
- [ ] B4 Connections page reads providers from content instead of the hardcoded list; providers
      outside section 8 marked extension. (open question 2)
      Built: status and phase per card come from content; the card list itself is still the
      frontend catalogue until question 2 is answered.

## C. Platform evidence (extension, proposed for Phase 2)

- [ ] C1 Register Verity as an always connected provider with module capabilities. (ME-1)
- [ ] C2 Platform tests from appendix C. (ME-2)
- [ ] C3 Evidence reports: XLSX with the appendix C columns and a PDF cover sheet; scheduled by
      control frequency and on demand. (ME-3, ME-4, ME-5)
- [ ] C4 Control page "Evidence sources": manual types, platform reports, connector tests. (ME-7)

## D. Connector framework and monitoring (Phase 2, signed)

- [x] D1 `connections` with envelope encrypted credentials, health, error streaks, expiry.
- [ ] D2 `control_checks`, `check_runs`, monthly partitioned `check_results`, `findings`,
      `waivers`. (AU-5, AU-8, AU-10)
      Built: `check_runs`, `check_results`. Open: `control_checks`, `findings`, `waivers`.
- [x] D3 Scheduler: runs by test frequency, only for controls in scope; error is never fail.
      (AU-5, AU-12) Daily per connection; per control scoping arrives with `control_checks`.
- [ ] D4 First fifteen connectors (spec 2.1), each implementing the tests its capabilities need.
      Built: GitHub (seven checks, build plan week 7).
- [ ] D5 Findings, alerts on state change, digest, auto resolve (spec 2.2). (AU-8)
- [ ] D6 Control automated status, run history and observation window coverage per control and in
      readiness. (AU-6, AU-7) Built: status and 30 day history on the control. Open: readiness.
- [ ] D7 Scoping and exclusions with reasons printed on evidence. (AU-9, AU-11)

## E. Frameworks (Phase 3, signed for ISO 27001, HIPAA, GDPR)

- [ ] E1 `tenant_frameworks`; one engagement per framework version. (FW-10)
- [ ] E2 Add framework flow with the overlap preview; adoption of new controls in one
      transaction. (FW-6)
- [ ] E3 ISO/IEC 27001:2022 pack: clauses 4 to 10 and Annex A, review of the appendix B draft
      mappings, new management system controls, Statement of Applicability with
      `requirement_applicability` and XLSX export. (FW-4, FW-5, FW-7)
- [ ] E4 HIPAA Security Rule pack (full text) with required and addressable specifications.
      (FW-8)
- [ ] E5 GDPR pack (articles relevant to controllers and processors) with the privacy controls.
- [ ] E6 Framework version upgrade through `requirement_transitions` (first use: the next SOC 2 or
      PCI DSS revision). (FW-9)
- [ ] E7 **Extension:** NIST CSF 2.0, NIS2, DORA, PCI DSS 4.0.1 (after licence), ISO/IEC 42001, in
      that order.
- [ ] E8 **Extension:** custom frameworks imported from a CSV template. (FW-11)
- [ ] E9 **Extension:** OSCAL 1.2 mapping collection export and catalog import. (CF-9)
