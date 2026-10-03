# Tasks: common control framework, automation, platform evidence, new frameworks

Ordered so each step ships on its own and nothing existing breaks. Phase labels follow the signed
specification; items marked **extension** go beyond it and are agreed before they are scheduled.
Requirement IDs refer to `docs/product/control-framework-requirements.md`.

## A. Content foundation (small, before Phase 2)

- [ ] A1 Migration: additive columns on `control_templates`, `requirements`,
      `template_requirement_map` (relationship, rationale type, strength, source, status, author,
      reviewer), `frameworks.maturity`; `requirement_transitions`, `framework_packs`. Downgrade
      tested. (CF-2, CF-3, CF-10, FW-2)
      Built (a7d3f19e2c58): `control_templates.pack` and `evidence`, `checks.evidence_kinds`,
      `control_template_checks.rationale`; the crosswalk's `coverage` and `rationale` are now
      filled. Open: relationship, rationale type, strength, source, author and reviewer;
      `frameworks.maturity`; `requirement_transitions`; `framework_packs`; the test procedure.
- [x] A2 Loader: prune per pack instead of globally; write `framework_packs`; print a diff; refuse a
      pack that breaks its `text_policy`. (CF-8, FW-1)
      Built: templates are pruned per pack, mappings per framework, a mapping onto another pack's
      template resolves by code, a mapping without coverage and rationale is refused, and a pack
      whose files do not match its sealed manifest is refused (`scripts/seal_content.py`).
      Proved with a probe framework in `tests/integration/test_content_loader.py`. Open:
      `framework_packs` rows, the printed diff and `text_policy`.
- [ ] A3 Content CI: every requirement mapped or marked with a reason; rationale and reviewer on
      every published mapping; no dangling keys; manifest hash matches. (FW-3)
      Built (`tests/unit/test_content_integrity.py`): coverage and rationale on every mapping, evidence
      kinds on every check, every automated evidence route names a test the control has, a
      full test link only where the control has one test, no dashes in shipped copy, manifests
      match. Open: reviewer on every mapping, requirements marked with a reason.
- [ ] A4 SOC 2 pack: replace verbatim TSC wording with identifiers and Verity summaries, or record
      AICPA permission; backfill mappings as published but unreviewed. (CF-8, open question 3)
- [ ] A5 Mapping review: a qualified second reviewer signs relationship, rationale type, strength,
      coverage and rationale for the SOC 2 mappings, including the LM-01 to CC6.1 note. (CF-3,
      open question 4)
      The 167 mappings now carry coverage and a rationale written by Verity from the criterion
      text and the control's own statement. They are unreviewed by a second person, and 25
      criteria have no primary route (all their controls only support them), which is a list to
      review rather than a defect: A1.2, CC1.1, CC1.3, CC1.4, CC1.5, CC2.1, CC2.2, CC5.1,
      CC5.2, CC6.1, CC6.4, CC6.5, CC6.7, CC9.1, P3.2, P6.1, P6.4, P6.5, P6.7, P7.1, PI1.1 to
      PI1.5.
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

- [~] C1 Register Verity as an always connected provider with module capabilities. (ME-1)
      Catalogued: provider `verity` (planned) on seven capabilities `verity_*`. Becomes
      available, and always connected, when the runner ships.
- [~] C2 Platform tests from appendix C. (ME-2)
      Catalogued: the 18 tests exist as checks mapped to 20 controls, each with its evidence kinds
      and rationale. Open: the runner (module services only, rule 4) and a home for results
      that is not a connection (`check_runs.connection_id` is required today).
- [ ] C3 Evidence reports: XLSX with the appendix C columns and a PDF cover sheet; scheduled by
      control frequency and on demand. (ME-3, ME-4, ME-5)
- [x] C4 Control page "Evidence sources": manual types, platform reports, connector tests. (ME-7)
      Built as the Checks tab, with the register column and the criterion view (section F).

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
      readiness. (AU-6, AU-7) Built: status and 30 day history on the control; automated status
      rolled into readiness through `compliance/readiness.py` (a failing, unreadable or out of
      date control is not ready, a requirement is met only when every applicable control is,
      CF-4); the dashboard automation card reads real counts; a result older than two days reads
      "Out of date" instead of pass or fail (AU-5). Open: observation window coverage in
      readiness (AU-7).
- [x] D7 Scoping and exclusions with reasons printed on evidence. (AU-9, AU-11) Built for GitHub
      repositories: `connection_resources` inventory, archived and forked repositories out by
      default, a person's decision sticky, an exclusion needs a reason (database CHECK as well as
      the service), audited, and printed on the evidence. Open: per control scoping
      (`control_checks`) and waivers (AU-10).

## F. Evidence composition (2026-10-04, requirements section 3A)

- [x] F1 Model and content: coverage and rationale on 167 requirement links and 101 test links,
      evidence kinds on 81 tests, expected evidence on 116 controls, 18 platform tests and 4
      change and pipeline tests catalogued, two controls added for CC8.1 (SD-13 controlled
      production deployments, SD-14 change traceability), BC-08 mapped to P6.4. (EC-1 to EC-4,
      EC-10)
- [x] F2 API: composition and evidence on `GET /controls/{id}/automation`,
      `GET /control-composition`, `GET /requirements/{id}/chain`. (EC-1, EC-5 to EC-8)
- [x] F3 UI: the Checks tab, the Requirements tab's rationale, the register's "Evidenced by"
      column, and the criterion view opened from Frameworks. (EC-1, EC-7, EC-8)
- [x] F4 GitHub accuracy from the content review: the last decision each reviewer made before the
      merge counts, a policy that could not be read is an error, a population cut short is
      stated, administrators who can bypass are said, every result names its rules, out of
      date results. (AU-5)
- [ ] F5 Evidence slots: bind an uploaded or collected file to the expected item it satisfies, and
      let readiness require the required items. Changes readiness, so it is its own decision.
- [ ] F6 Collectors that make SD-13 and SD-14 real: GitHub deployments and environments, CI run
      results per merged change, a ticket system (Jira) for request to release.
- [ ] F7 Platform test runner (C2) for the 18 module tests, then evidence reports (C3).
- [ ] F8 Align the declared `control_sub_type` of the 49 templates that disagree with the derived
      mode, as a tenant safe data migration (CF-6).
- [ ] F9 Per control evidence projections instead of one connection wide snapshot attached to
      every control, and versioned check definitions pinned on each run.

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
