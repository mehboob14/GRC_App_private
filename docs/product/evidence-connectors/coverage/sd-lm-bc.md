# Evidence coverage: SD, LM and BC families

Change and development (SD), logging, monitoring, incidents and vulnerabilities (LM), and continuity, capacity and suppliers (BC): 34 controls today, plus 7 proposed. Written to `AUTHORING.md` sections 5 and 6. The machine readable files are [sd-lm-bc.json](sd-lm-bc.json) (one entry per artifact per control, in the proposed structure) and [sd-lm-bc.controls.json](sd-lm-bc.controls.json) (one entry per control decision).

Everything here is a proposal for qualified review (FW-5, onboarding part 5 section 10). Nothing in content or code changes because of it.

An artifact's phase is the earliest phase in which a source other than a person can fill it, fully or in part. Later sources that deepen it carry their own phase in the tables below.

| Phase | Meaning |
|---|---|
| P1 | Verity modules, document templates and the GitHub connector now. GitHub reads that are not built yet count as P1 because they extend the connector that exists; each says so and may need a new read permission (unverified). |
| P2 | The signed Phase 2 connectors: GitLab and Bitbucket, CI and CD on GitHub, GitLab and Bitbucket, AWS, Okta, Google Workspace, Entra ID, 1Password, Jira, PagerDuty, Slack, Datadog, Sentry, Cloudflare, Tailscale. |
| P3 | Later connectors: vulnerability scanners (Tenable, Rapid7, Qualys), Azure, Google Cloud and the other hosts, Linear and the other ticket tools. |
| people-only | No system in the catalogue can fill it. |

The person source stays on every artifact (01-evidence-model.md, rule 1.3.1). In the JSON, `today` lists only sources that run now: a catalogued check with no implementation is under `planned`. Entries on a proposed control carry `"control_status": "proposed"`, entries on a proposed artifact type carry `"artifact_status": "proposed"`, and `objective_changes` names reworded, added or moved objectives.

## Proposed control changes

| Decision | Count | Controls |
|---|---|---|
| keep | 21 | SD-04, SD-06, SD-07, SD-08, SD-09, SD-11, SD-12, SD-13, SD-14, LM-01, LM-03, LM-04, LM-06, LM-08, LM-09, LM-10, LM-12, BC-02, BC-04, BC-05, BC-06 |
| revise objectives | 9 | SD-01, SD-02, SD-05, SD-10, LM-02, LM-05, LM-07, BC-01, BC-07 |
| split | 4 | SD-03, LM-11, BC-03, BC-08 |
| add | 3 | SD-15, SD-16, SD-17 |
| merge | 0 | none |

The splits create four proposed successors: SD-18 (from SD-03), LM-13 (from LM-11), BC-09 (from BC-03) and BC-10 (from BC-08). SD-15, SD-16 and SD-17 are the codes onboarding part 5 (sections 7 and 9) proposed. Each new code is the next free number in its family. Existing codes keep their meaning.

| Control | Decision | Why | Tenant impact |
|---|---|---|---|
| SD-01 Change authorization and approval | revise objectives | SOC2:CC8.1 (full) and ISO27001:A.8.19, A.8.32 rely on SD-01 for every kind of production change, including server software, infrastructure, configuration and database changes. SD-01.B tested a population of merges only, so it is reworded to cover the whole change population. | none |
| SD-02 Automated testing in CI | revise objectives | ISO27001:A.8.28 and A.8.29 rely on static analysis in the pipeline, which no objective tested. SD-02.F is added. SD-02.E applies only when Processing Integrity (SOC2:PI1.3) is in scope and reads not applicable otherwise. | none |
| SD-03 Dependency and image scanning | split | SD-03 bundles vulnerability scanning (SOC2:CC6.8, CC7.1, ISO27001:A.8.8, A.8.28, A.8.29) with a component list and licence review (ISO27001:A.5.32). The licence review has a different owner (legal with engineering), a different remediation (replace the component or approve the licence) and different applicability (a SOC 2 only workspace can leave it out), and no operating objective tested it. Successor: **SD-18 Software component list and licence review**. | adoption proposal: offer SD-18 to ISO workspaces; SD-03 wording change offered, not applied (CF-6) |
| SD-05 Input validation controls | revise objectives | SD-05.D (rejects and duplicates held in a monitored queue, rejection rate alerts) is processing integrity error handling under SOC2:PI1.2, not secure input validation. It moves to the proposed SD-15. What stays answers SOC2:PI1.2 and ISO27001:A.8.26, A.8.28, so SD-05 must be adoptable without Processing Integrity (onboarding lists it as on demand for PI only). | data migration: objective SD-05.D results and evidence stay on SD-05 history; SD-15 starts empty |
| SD-10 Secure SDLC policy | revise objectives | ISO27001:A.8.25 and A.8.27 (both full) and A.8.26, A.8.29 rest on SD-10. Objective B bundled approval of security requirements before build and the check before release that A.8.29 relies on. B is reworded and F added. A split into a separate design review control was weighed and not proposed: one owner, one population, and the objectives already separate the evidence. | none |
| SD-15 Processing error handling and correction | add | SOC2:PI1.2 and PI1.3 rest on SD-05 and SD-08 alone, each partial (LD-14). Error handling and correction is the missing activity (onboarding section 7). Receives SD-05.D. | adoption proposal: offer when Processing Integrity is elected |
| SD-16 Output delivery and review | add | SOC2:PI1.4 rests on SD-08 alone, and the SD-08 rationale says delivery to the right recipient needs its own check (onboarding section 7). | adoption proposal: offer when Processing Integrity is elected |
| SD-17 Direct changes to production data | add | SOC2:CC8.1 names changes to data. Direct changes to production data outside the application are tested by every SOC 1 and SOC 2 auditor and no SD control covers them (onboarding section 9). | adoption proposal: offer to every workspace with production data |
| LM-02 Centralized logging and retention | revise objectives | ISO27001:A.8.15 (full) needs collection, retention, protection, gap detection and review. LM-02.B and LM-02.C each bundled two of these with different evidence. Reworded B and C, added F (gap alerts) and G (protection from administrators). | none |
| LM-05 Incident postmortems with actions | revise objectives | ISO27001:10.2 asks that corrective action is checked for effect. LM-05.E added. A.5.27 (full) is otherwise covered. | none |
| LM-07 Incident response plan | revise objectives | ISO27001:A.5.28 is mapped on the evidence procedure, but only the written plan was examined; LM-07.F tests that evidence was handled as the plan sets. LM-07.C bundled sharing the plan and reviewing it; C is reworded and G added. | none |
| LM-11 Vulnerability management program | split | SOC2:CC7.1 and ISO27001:A.8.8 are both full on LM-11, which bundles discovery coverage (scanners, targets reconciled with the asset inventory, authenticated scans) with triage, remediation and risk acceptance. They have different owners (whoever runs the scanners versus each asset owner), cadences (scan interval versus per finding SLA) and failure conclusions (a coverage gap is not a late fix). Continuous compliance plan section 4 names this split. Scanner checks then map to LM-13, register checks to LM-11. Successor: **LM-13 Vulnerability scanning coverage**. | adoption proposal: LM-13 offered to every workspace running LM-11; LM-11 mapping coverage changes from full to partial with an audit row; no LM-11 result or acceptance is copied to LM-13 |
| BC-01 Automated, monitored backups | revise objectives | ISO27001:A.8.13 covers copies of software and systems, not only data stores; BC-01.F added. BC-01.D bundled storage protection with restore rights; D reworded and E added. BC-01 and BC-02 stay separate (continuous compliance plan section 4). | none |
| BC-03 Business continuity / disaster recovery plan | split | ISO27001:A.8.14 (full) is a separate Annex A control, chosen on its own in the Statement of Applicability, about technical redundancy. BC-03 bundled it with continuity planning (SOC2:CC9.1, ISO27001:A.5.29, A.5.30). The two have different owners (the business continuity owner versus engineering), different evidence (a plan and an exercise versus cloud configuration and a failover test) and different remediation (rewrite and exercise the plan versus change the architecture). A cloud check on zones and standbys needs a control to map to that is not the plan. Successor: **BC-09 Redundancy and failover of critical services**. | adoption proposal: offer BC-09 to workspaces running BC-03; A.8.14 moves with an audit row; BC-03.D history stays on BC-03 |
| BC-07 Vendor inventory | revise objectives | ISO27001:A.5.22 relies on suppliers no longer used being removed with access revoked. BC-07.D bundled the yearly review with offboarding, an event per vendor with its own record; D reworded and E added. | none |
| BC-08 Vendor security due diligence | split | BC-08 maps to ten requirements. ISO27001:A.8.30 (outsourced development) applies only where a supplier builds software for the company and needs its own evidence (code ownership, acceptance testing of deliveries, escrow); bundled in BC-08 it cannot be marked not applicable on its own in the Statement of Applicability. It moves to BC-10. BC-08 objectives are also revised: B repeated BC-07.C and becomes tiering, E bundled contract terms (A.5.20) with findings (now F), and G is added for ongoing delivery review (A.5.22, A.8.21). Successor: **BC-10 Oversight of outsourced development**. | adoption proposal: offer BC-10 when the profile says development is outsourced; A.8.30 rationale on BC-08 narrowed with an audit row |

Kept as they are:

| Control | Reason |
|---|---|
| SD-04 Emergency change procedure | One activity, the emergency path, with its own procedure, records and retrospective review. Objectives cover SOC2:CC8.1 and ISO27001:A.8.32 as mapped. |
| SD-06 Peer code review (branch protection) | One coherent activity, independent review before merge, with configuration and operating objectives. ISO27001:A.8.4 is partial by its own rationale (it does not show who can read code). |
| SD-07 Pipeline storage integrity | One activity (integrity of intermediate stores) for one criterion, SOC2:PI1.5. SD-07.E overlaps DM-08 retention but tests the pipeline's own stores. |
| SD-08 Processing reconciliation and monitoring | Job monitoring and reconciliation serve SOC2:PI1.3 and PI1.4 together. Delivery of outputs to the right recipient, which the PI1.4 rationale leaves open, goes to the proposed SD-16. The SOC 1 gap on general job scheduling (onboarding section 9) is not added, since SOC 1 is guidance only. |
| SD-09 Processing specifications | Specifications for SOC2:PI1.1; objectives cover definition, currency, test tracing and review after change. Communicating specifications to users is left to CS-02 (onboarding section 7). |
| SD-11 Secret scanning | One activity, detecting and handling leaked secrets, for SOC2:CC6.1, CC7.1 and ISO27001:A.5.17, A.8.28. Pre commit hooks remain guidance. |
| SD-12 Separate dev/staging/production | Environment separation, ISO27001:A.8.31 (full) and SOC2:CC8.1. SD-12.E overlaps DM-13 (masked test data); keep both, they test different populations (environments versus data sets). |
| SD-13 Controlled production deployments | Release step of change, SOC2:CC8.1 and ISO27001:A.8.19, A.8.32. Objectives cover source, approval, deployers and history. |
| SD-14 Change traceability | Traceability across the change records, SOC2:CC8.1 and ISO27001:A.8.32. |
| LM-01 Asset and system inventory | Asset inventory for SOC2:CC2.1, CC6.1 and ISO27001:A.5.9. Licence and end of support details in the guidance stay advisory. |
| LM-03 Configuration-change detection | Drift detection against a baseline, SOC2:CC7.1 and ISO27001:A.8.9, A.8.20. |
| LM-04 Security event evaluation | Event triage is the whole of SOC2:CC7.3 and ISO27001:A.5.25; objectives cover procedure, evaluation, escalation and consistency. |
| LM-06 Incident recovery procedures | Recovery from incidents, SOC2:CC7.5 (full) and ISO27001:A.5.26. |
| LM-08 On-call rotation | One activity, on call cover with escalation, for SOC2:CC7.2 and CC7.4. It has no ISO mapping, so an ISO only workspace would not see it; ISO27001:A.5.24 partial is proposed. |
| LM-09 Security anomaly alerting | Alerting on a limited set of conditions, SOC2:CC7.2 (full) and ISO27001:A.8.16. |
| LM-10 Incident tabletop exercise | Yearly exercise for SOC2:CC7.4 and ISO27001:A.5.24. |
| LM-12 Threat source monitoring | Threat source monitoring, ISO27001:A.5.7 (full). SOC2:CC7.1 partial is proposed so SOC 2 workspaces use it once it moves out of the ISO pack (CL-10). |
| BC-02 Backup restore testing | Restore testing, SOC2:A1.3 (full) and ISO27001:A.5.30, A.8.13. |
| BC-04 Capacity management | Capacity management, SOC2:A1.1 and ISO27001:A.8.6 (both full). |
| BC-05 Shadow-IT detection | Detecting applications adopted outside procurement, SOC2:CC9.2 and ISO27001:A.5.23. |
| BC-06 Subprocessor management | Subprocessor list and notice, SOC2:CC9.2, P6.1, P6.4 and ISO27001:A.5.21, A.5.22. Applies only when customer data is shared with subprocessors (profile fact). |

Considered and not proposed: a separate design review control out of SD-10 (one owner and one population; the objectives already separate the evidence); a general job scheduling control from the SOC 1 list (SOC 1 is guidance only); merging SD-12.E with DM-13, or LM-02.D with LM-09 (they overlap but test different populations).

### New and successor controls

**SD-15 Processing error handling and correction** (proposed, added)

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:PI1.2 | partial | Rejected and duplicate inputs are held in a monitored queue and corrected, so input errors are not lost. Validation at the boundary comes from SD-05. |
| SOC2:PI1.3 | partial | Processing errors are logged, corrected with approval and reprocessed against the reconciliation. Detecting the error comes from SD-08. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| SD-15.A | design | The error handling procedure is approved. It says where rejected inputs and processing errors are held, who reviews them, how a correction is approved and reprocessed, and the time allowed for each. | `doc-processing-integrity-procedure` |
| SD-15.B | operating | Each processing error in the period was logged with the date, the records affected, the cause and the correction, and was closed within the time the procedure allows. | `processing-error-log` |
| SD-15.C | operating | Corrections and reprocessing were approved by someone other than the person who made them, and the reprocessed run reconciled before its output was released. | `processing-error-log`, `reconciliation-results-and-how-exceptions-were` |
| SD-15.D (moved from SD-05.D) | operating | Duplicate and invalid records were caught at ingestion and sent to a monitored queue rather than dropped, and rejection rates above the expected level raised an alert that was followed up. | `evidence-validation-was-tested`; interview |

**SD-16 Output delivery and review** (proposed, added)

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:PI1.4 | partial | Outputs are checked before release and reach only their intended recipients on time, with wrong or late outputs corrected. SD-08 shows the outputs were produced. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| SD-16.A | design | Each key output has an approved specification of its recipients, format and timing, the checks made before release, and how a wrong or late output is withdrawn and corrected. | `processing-specifications-covering-inputs-outputs-and`, `doc-processing-integrity-procedure` |
| SD-16.B | operating | Each scheduled output in the period was produced on time and passed its completeness and accuracy checks before release. | `output-delivery-log` |
| SD-16.C | operating | Outputs reached only their intended recipients, and each misdirected, late or wrong output was recorded, corrected and, where a customer was affected, reported to them. | `output-delivery-log`, `security-incident-register` |

**SD-17 Direct changes to production data** (proposed, added)

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:CC8.1 | partial | Changes made straight to production data, outside the application and its release path, are requested, approved by someone other than the person who runs them, logged and reconciled with the database activity. The other change controls cover code and infrastructure. |
| ISO27001:A.8.32 | partial | Brings data fixes run by hand inside change control: approval before the change, a limited group who may run it, and a check of the database activity against approved changes. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| SD-17.A | design | The procedure for changing production data outside the application is approved. It says when a direct change is allowed, who may request, approve and run one, that it runs as a reviewed script where possible, and what is logged. | `doc-change-management-procedure` |
| SD-17.B | operating | Every direct change to production data in the period was requested and approved before it ran, by someone other than the person who ran it. | `production-data-change-log` |
| SD-17.C | operating | Only the listed people could change production data directly, and the database activity for the period matched the approved changes. | `list-of-privileged-accounts-with-approval`, `database-activity-log-review` |

**SD-18 Software component list and licence review** (proposed, split from SD-03)

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.5.32 | partial | Moved from SD-03. The component list records each open source component's licence, and licences that conflict with how the product is used or sold are reviewed before release. Commercial licences sit with GOV-05 and rights in staff work with HR-02. |
| ISO27001:A.5.21 | partial | A component list per release shows which third party software each release contains, which is the software part of supply chain visibility. Vulnerability scanning of those components stays with SD-03. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| SD-18.A | design | The component and licence standard is approved. It says which builds produce a component list, which licences are allowed, restricted or not allowed for how the product is used or sold, and who may approve an exception. | `doc-engineering-security-standard` |
| SD-18.B | operating | Each release in the period had a component list, produced by the build, naming each component, its version and its licence. | `software-component-list-with-licences` |
| SD-18.C | operating | Components with a restricted or not allowed licence were found before release and removed, replaced or approved as an exception with a reason. | `licence-exceptions-record`, `software-component-list-with-licences` |

**LM-13 Vulnerability scanning coverage** (proposed, split from LM-11)

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:CC7.1 | partial | Scans of infrastructure, containers, dependencies and the external surface at the set frequency, with targets reconciled to the asset inventory, are the discovery half of vulnerability detection. Handling what is found stays with LM-11. |
| ISO27001:A.8.8 | partial | Finding technical weaknesses across the whole estate, with authenticated scans and coverage gaps followed up. Evaluating and fixing them stays with LM-11. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| LM-13.A | design | The vulnerability management policy sets the scan scope for infrastructure, containers, dependencies and the external surface, the minimum scan frequency, when authenticated scans are required and what counts as a significant change that triggers an extra scan. | `vulnerability-management-policy-with-timeframes`, `doc-operations-security-policy` |
| LM-13.B (moved from LM-11.B) | operating | Infrastructure, containers, dependencies and the external surface were scanned at least quarterly and after significant change, with authenticated scans on internal systems, and the targets matched the asset inventory. | `scan-reports`, `asset-inventory` |
| LM-13.C | operating | Failed, partial and unauthenticated scans, and targets the scanner could not reach, were found and followed up, so a gap in coverage was not read as a clean result. | `scan-reports`, `log-of-control-deficiencies-with-owner` |

**BC-09 Redundancy and failover of critical services** (proposed, split from BC-03)

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.8.14 | full | Moved from BC-03. The redundancy each critical service relies on is recorded against its recovery targets, kept in place and failed over in a yearly test, which shows it is enough for the availability promised. |
| SOC2:A1.2 | partial | Redundant components and a tested failover are part of the recovery infrastructure. Backups come from BC-01 and environmental protection from PE-01 and PE-03. |
| ISO27001:A.5.30 | partial | A tested failover shows technology can meet the recovery targets the continuity plan sets. Data restores come from BC-02. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| BC-09.A | design | For each critical service the redundancy it relies on to meet its recovery targets is recorded, such as several availability zones, a standby database or a secondary region, and approved by the engineering lead. | `business-continuity-and-disaster-recovery-plan`, `doc-business-continuity-and-disaster-recovery-plan` |
| BC-09.B | operating | The recorded redundancy was in place throughout the period for each critical service. | `redundancy-configuration-export` |
| BC-09.C | operating | Failover of the redundant parts was tested in the last 12 months, and the time to fail over was compared with the recovery targets. | `exercise-or-test-report`, `measured-recovery-time-against-the-target` |
| BC-09.D (moved from BC-03.D) | operating | Where a secondary site or region exists, the test switched to it and confirmed that access control, logging and segmentation worked there. | `exercise-or-test-report`; interview |

**BC-10 Oversight of outsourced development** (proposed, split from BC-08)

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.8.30 | partial | Contracts with suppliers that build software set security requirements, code ownership, audit rights and escrow where needed, and each delivery is reviewed and tested before it goes live. Choosing the supplier stays with BC-08 and code review with SD-06. |
| SOC2:CC9.2 | partial | Manages the risk of a business partner that writes software the company runs. General vendor due diligence comes from BC-08. |

| Objective | Assurance | Statement | Artifacts |
|---|---|---|---|
| BC-10.A | design | Contracts with suppliers that build software for the company set the security requirements, who owns the code, audit rights and, where a critical system depends on the supplier's code, an escrow arrangement. | `doc-third-party-management-policy`, `security-terms-agreed-in-each-vendor` |
| BC-10.B | operating | Each delivery from a development supplier was reviewed by a member of staff and tested against its security requirements before it went live. | `acceptance-test-of-supplier-deliveries`, `sample-of-reviewed-changes` |
| BC-10.C | operating | Where escrow is required, the deposit was checked as complete and current at each review. | `escrow-verification-record` |

### Objective changes on existing controls

| Objective | Change | Statement | Artifacts | Why |
|---|---|---|---|---|
| SD-01.B | reword | Every production change released in the period appeared on the change list: application releases checked against the deployments, and infrastructure, configuration, database and server software changes checked against the cloud change history and administrator activity. | `change-requests-with-approval-for-a`, `sample-of-reviewed-changes`, `deployment-history-for-a-sample-of`, `infrastructure-and-configuration-change-history` | ISO27001:A.8.19 and A.8.32 rely on SD-01 for software installed on servers and for infrastructure, configuration and database changes, but the population was merges only. |
| SD-03.A | reword | The dependency triage standard is approved. It names the scanner for code dependencies and container images, sets triage and fix timeframes by severity, says which new critical findings fail a build and how exceptions are approved. | `dependency-vulnerability-triage-standard-with-timeframes`, `doc-engineering-security-standard` | The component list with licences moves to the proposed SD-18.A. |
| SD-10.B | reword | Each new application, major feature and acquired system in the period had its security requirements recorded and approved at design review before it was built or bought. | `approved-security-requirements-for-a-sample`, `security-assessment-for-each-critical-vendor` | The original bundled approval before build and verification before release, two moments with different evidence. Verification moves to SD-10.F. |
| LM-02.B | reword | Sign in, access change, administrator and application audit events from every in scope system reached the central log store. | `evidence-logs-are-reviewed`, `asset-inventory` | Gap alerting moves to its own objective, LM-02.F, because it is shown by different evidence (monitor and alert history, not source coverage). |
| LM-02.C | reword | Logs were kept for at least 12 months with the latest 3 months searchable at once. | `logging-and-retention-standard`, `log-store-retention-and-access-settings` | Retention and protection against administrators were one objective. ISO27001:A.8.15 claims both; protection moves to LM-02.G, and retention gains a settings test instead of an interview alone. |
| LM-07.C | reword | The current plan was given to everyone who holds a role in it, and each of them acknowledged the current version. | `incident-plan-acknowledgement-by-role-holders`, `doc-incident-response-plan` | Sharing the plan and reviewing it were one objective with different evidence and cadence. Review moves to LM-07.G. |
| BC-01.D | reword | Backups were encrypted at rest, and at least one copy sat in a separate region, account or site on immutable or offline storage. | `backup-policy-covering-scope-frequency-and`, `backup-storage-settings-export` | Storage protection and restore rights were one objective. Restore rights move to BC-01.E, and storage protection gains a settings test. |
| BC-03.A | reword | The continuity and recovery plan is approved. It sets recovery time and data loss targets for each critical service, activation criteria, roles, and how customers and staff are told. | `business-continuity-and-disaster-recovery-plan`, `doc-business-continuity-and-disaster-recovery-plan`, `doc-business-impact-analysis` | The redundancy each service relies on moves to the proposed BC-09.A. |
| BC-03.C | reword | The plan was exercised in the last 12 months against a realistic scenario, recording who took part and the results compared with each recovery target. | `exercise-or-test-report` | Failover of the redundant parts moves to the proposed BC-09.C. |
| BC-07.D | reword | The register was reviewed in the last 12 months, with contract dates and renewal points checked for each vendor. | `vendor-inventory-with-owner-data-and` | Offboarding with access revoked moves to BC-07.E: it is an event per vendor, not part of the yearly review. |
| BC-08.B | reword | Each supplier with access to systems or data had a current tier from a tiering assessment, and that tier set the depth of its assessment. | `vendor-inventory-with-owner-data-and`, `asset-inventory` | As written it repeated BC-07.C (register complete). BC-08 relies on BC-07 for the population and tests its own step, tiering. |
| BC-08.E | reword | Contracts carried the security terms the procedure sets for the vendor's tier, such as incident notice, audit rights, limits on subcontracting and data return at exit. | `security-terms-agreed-in-each-vendor` | Contract terms (ISO27001:A.5.20) and tracking of findings were one objective. Findings move to BC-08.F. |
| SD-02.F | add, operating | The security tests the engineering standard names, such as static analysis, ran on every change merged in the period, and each finding they raised was fixed, dismissed with a reason or carried as an approved exception before release. | `static-analysis-results-for-merged-changes`, `testing-standard-stating-what-must-pass` | ISO27001:A.8.28 and A.8.29 rely on static analysis in the pipeline (rationales on SD-02 and SD-10). No objective tested that it ran. |
| SD-10.F | add, operating | Before release, each of those systems was checked against its approved security requirements, and any requirement not met was fixed or accepted by the approver. | `approved-security-requirements-for-a-sample` | ISO27001:A.8.29 relies on SD-10 for acceptance against security requirements before release. |
| LM-02.F | add, operating | A source that stopped sending logs raised an alert, and each such alert was followed up until the source was sending again. | `log-source-gap-alerts` | Split out of LM-02.B; ISO27001:A.8.15 and SOC2:CC2.1 rely on complete logs. |
| LM-02.G | add, operating | The administrators of a system could not change or delete its logs, and the few people who can change retention or delete logs in the central store were named and approved. | `log-store-retention-and-access-settings` | Split out of LM-02.C; ISO27001:A.8.15 (full) and A.5.28 rely on protected logs. |
| LM-05.E | add, operating | Each closed corrective action was checked for effect, by confirming the cause did not recur or by a verification recorded by someone other than its owner. | `corrective-actions-tracked-to-closure`, `postmortem-for-each-significant-incident` | ISO27001:10.2 asks that the effect of corrective action is reviewed; LM-05 maps to it and no objective tested it. |
| LM-07.F | add, operating | Where an incident needed evidence, it was collected and kept as the plan sets, with a record of who collected and handled each item and when. | `evidence-handling-record-for-incidents`, `incident-response-plan` | ISO27001:A.5.28 is mapped to LM-07 on the evidence procedure, but only the written procedure was examined. |
| LM-07.G | add, operating | The plan was reviewed in the last 12 months and after each significant incident, and each review was recorded. | `review-and-re-approval-record-for`, `security-incident-register` | Split out of LM-07.C (shared and reviewed). |
| BC-01.E | add, operating | Rights to restore or delete backups were held by a small group that was reviewed in the period. | `list-of-privileged-accounts-with-approval` | Split out of BC-01.D. |
| BC-01.F | add, operating | The configuration, infrastructure code and images needed to rebuild each service were kept in versioned storage covered by the backup policy. | `rebuild-materials-inventory` | ISO27001:A.8.13 covers copies of software and systems as well as data. BC-01.A names them; nothing tested them. |
| BC-07.E | add, operating | Vendors no longer used were offboarded: their access was revoked, their copy of company data returned or deleted, and the offboarding recorded. | `vendor-offboarding-records` | Split out of BC-07.D; ISO27001:A.5.22 rationale relies on removal with access revoked. |
| BC-08.F | add, operating | Findings and accepted risks from assessments were tracked to closure, or to an acceptance with an owner and an expiry. | `security-assessment-for-each-critical-vendor`, `risk-register-with-owners-ratings-and` | Split out of BC-08.E. |
| BC-08.G | add, operating | At each reassessment of a critical vendor, its delivery against the agreed security and service levels was reviewed, and a material change, such as a breach, new ownership or a new subservice provider, led to an early review. | `vendor-service-level-review` | ISO27001:A.5.22 and A.8.21 rationales rely on checking delivered service levels; no objective tested it. |
| SD-05.D | move to SD-15.D | unchanged | unchanged | Tests the activity that moves to SD-15. |
| LM-11.B | move to LM-13.B | unchanged | unchanged | Tests the activity that moves to LM-13. |
| BC-03.D | move to BC-09.D | unchanged | unchanged | Tests the activity that moves to BC-09. |

Artifacts that leave a control with a moved objective: LM-11 `asset-inventory`. They appear under the successor in the JSON.

### Mapping changes

| Requirement | Control | Change | Coverage | Rationale |
|---|---|---|---|---|
| ISO27001:A.5.32 | SD-03 | remove |  | Moves to SD-18 with the component list and licence review. |
| SOC2:CC7.1 | LM-11 | coverage | partial | LM-11 keeps the register, triage, remediation times and risk acceptance. Discovery coverage moves to LM-13, so LM-11 alone no longer covers the whole criterion. |
| ISO27001:A.8.8 | LM-11 | coverage | partial | Same split: evaluating and treating weaknesses stays, finding them across the estate moves to LM-13. |
| ISO27001:A.5.24 | LM-08 | add | partial | An on call rotation with escalation makes the response roles the plan names reachable at any hour. The plan itself comes from LM-07 and the exercise from LM-10. |
| SOC2:CC7.1 | LM-12 | add | partial | Following advisories and the known exploited list surfaces newly disclosed weaknesses in software in use, which feeds detection. Scanning and remediation come from LM-11 and LM-13. Needs LM-12 adoptable by SOC 2 workspaces (CL-10). |
| ISO27001:A.8.14 | BC-03 | remove |  | Moves to BC-09 with the redundancy record and the failover test. |
| ISO27001:A.8.30 | BC-08 | rationale | partial | Narrowed: BC-08 chooses and reassesses the development supplier. Contract terms for code, testing of deliveries and escrow move to BC-10. |
| SOC2:PI1.2 | SD-15 | add | partial | See SD-15 above. |
| SOC2:PI1.3 | SD-15 | add | partial | See SD-15 above. |
| SOC2:PI1.4 | SD-16 | add | partial | See SD-16 above. |
| SOC2:CC8.1 | SD-17 | add | partial | See SD-17 above. |
| ISO27001:A.8.32 | SD-17 | add | partial | See SD-17 above. |
| ISO27001:A.5.32 | SD-18 | add | partial | See SD-18 above. |
| ISO27001:A.5.21 | SD-18 | add | partial | See SD-18 above. |
| SOC2:CC7.1 | LM-13 | add | partial | See LM-13 above. |
| ISO27001:A.8.8 | LM-13 | add | partial | See LM-13 above. |
| ISO27001:A.8.14 | BC-09 | add | full | See BC-09 above. |
| SOC2:A1.2 | BC-09 | add | partial | See BC-09 above. |
| ISO27001:A.5.30 | BC-09 | add | partial | See BC-09 above. |
| ISO27001:A.8.30 | BC-10 | add | partial | See BC-10 above. |
| SOC2:CC9.2 | BC-10 | add | partial | See BC-10 above. |

What existing workspaces need. Every change is offered, never applied (CF-6). A split keeps the original control with its evidence, owner, exceptions and history; the successor starts not implemented and empty, and accepting the adoption proposal writes an audit row. No green result, waiver or risk acceptance is copied to a successor, and moved objectives keep their past results on the original control. The coverage changes (LM-11 from full to partial, A.8.14 moving to BC-09) change framework readiness, so they need the owner's go and the reviewer's sign off. With these splits, the version control, CI, cloud and monitoring checks map as follows: scanner and scan coverage checks to LM-13; component list reads to SD-18; zone and standby reads to BC-09; supplier change reviews to BC-10.

### Proposed artifact types

New keys used by the new and revised objectives, on the CL-9 pattern (a thing, where a small company finds it, populations rather than samples).

| Key | Category | Valid days | Name | Where |
|---|---|---|---|---|
| `infrastructure-and-configuration-change-history` | configuration | 92 | List of infrastructure, configuration, database and server software changes made in production in the period, with actor, time and the approved change each matches | Cloud change history (for example the cloud audit trail) and merges to the infrastructure code repository, joined with change tickets. |
| `static-analysis-results-for-merged-changes` | configuration | 92 | List of all changes merged in the period with the static analysis run, its result and how each finding was handled | Code scanning results in the version control system or the CI tool. |
| `software-component-list-with-licences` | configuration | 92 | Component list for each release, with component, version and licence | Produced by the build or exported from the dependency graph of the version control system. |
| `licence-exceptions-record` | record | 365 | Components with a restricted or not allowed licence, with the decision, reason and approver | Tasks module, one approved task per exception, or the dependency review log. |
| `processing-error-log` | record | 31 | List of all processing errors in the period, with records affected, cause, correction, approver and closing date | The error queue or job dashboard, with an issue in the Tasks module for each error. |
| `output-delivery-log` | record | 31 | List of scheduled outputs in the period, with time produced, checks passed, recipients and any correction | Job logs or the delivery system (exports, reports, files sent to customers). |
| `production-data-change-log` | record | 92 | List of all direct changes to production data in the period, with requester, approver, who ran it and when | Tasks module or tickets, one approved request per change, with the script attached. |
| `database-activity-log-review` | record | 92 | Review of production database activity against approved data changes | Database audit log or query log for production, reviewed by someone who did not run the changes. |
| `log-source-gap-alerts` | record | 92 | Alerts raised when a log source stopped sending, with follow up | The observability tool's monitor history, with a ticket or issue for each gap. |
| `log-store-retention-and-access-settings` | configuration | 92 | Retention, immutability and delete permission settings of the central log store | Settings of the log store in the cloud console or observability tool, with the list of roles that can delete logs or change retention. |
| `evidence-handling-record-for-incidents` | record | 365 | Evidence collected for each incident that needed it, with who collected and handled each item and when | The incident issue in the Tasks module, with each item attached. |
| `incident-plan-acknowledgement-by-role-holders` | record | 365 | Acknowledgement of the current incident response plan by everyone who holds a role in it | Documents module, an acknowledgement campaign on the plan targeted at the incident roles. |
| `backup-storage-settings-export` | configuration | 92 | Encryption, cross region or cross account copy and immutability settings of each backup store | Backup vault or snapshot settings from the cloud console. |
| `rebuild-materials-inventory` | record | 365 | List of the configuration, infrastructure code and images needed to rebuild each service, with where each is kept | Infrastructure code repositories and image registries, listed in the continuity plan. |
| `redundancy-configuration-export` | configuration | 92 | Zone, standby and region settings of each critical service's databases, load balancers and compute | Cloud console or infrastructure code. |
| `vendor-offboarding-records` | record | 365 | Offboarding record for each vendor that stopped being used, with access revoked and data returned or deleted | Vendors module, offboarding step. |
| `vendor-service-level-review` | record | 365 | Review of each critical vendor's delivery against agreed security and service levels, and of material changes | Vendors module, contract service levels and monitoring signals, reviewed at reassessment. |
| `acceptance-test-of-supplier-deliveries` | record | 365 | List of deliveries from development suppliers in the period, with the internal reviewer and the acceptance test result | Pull requests from supplier accounts and the acceptance test record. |
| `escrow-verification-record` | record | 365 | Check that each source code escrow deposit is complete and current | Report from the escrow agent, or the verification note kept with the contract. |

## Summary

| Measure | Count |
|---|---|
| Artifact entries (artifact per control, proposed structure) | 218 |
| Phase P1 | 195 |
| Phase P2 | 20 |
| Phase P3 | 0 |
| Phase people-only | 3 |
| First check (connector or verity, not a report or document alone) in P1 | 187 |
| First check (connector or verity, not a report or document alone) in P2 | 24 |
| First check (connector or verity, not a report or document alone) in P3 | 1 |
| First check (connector or verity, not a report or document alone) in none | 6 |
| Entries on proposed controls | 30 |
| Entries using a proposed artifact type | 19 |
| New verity checks | 18 |
| NEED predicates (distinct) | 75 |

| Capability | Distinct NEED predicates |
|---|---|
| alerting | 6 |
| ci_cd | 10 |
| cloud_infrastructure | 19 |
| identity_provider | 2 |
| observability | 12 |
| ticketing | 10 |
| version_control | 15 |
| vulnerability_scanner | 1 |

## New verity checks

Each reads its module through the module's service, inside row level security (ME-6), and files its report with the ME-3 cover. States follow AU-5: error is never fail, and a population Verity cannot see in full is insufficient information, never pass.

### `verity.incidents.registered`

Security incidents are registered with the facts the plan needs. Capability `verity_tasks`, resource `incident`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Issues in the Tasks module created from the proposed shipped Security incident task template, detected in the last 92 days, plus every one still open. |
| Predicate | Each has a severity, an owner who is an active member, the date found, a recorded notice decision (notify or not, who decided, when) and, once closed, a closing date and note. |
| Outcomes | pass when every incident has the facts; fail naming each incident that lacks one; not configured until the incident template exists; empty window gives insufficient information unless a person filed a dated nil return on LM-07 for the window, then pass with the nil return listed. |
| Evidence kept | Security incident register report (XLSX with PDF cover, ME-3): ID, title, severity, owner, found, notice decision and date, closed, linked controls. |
| Controls | **LM-07** (partial): Shows the register is kept with the facts the plan requires. It cannot show that every incident was entered. **LM-04** (partial): Shows events judged to be incidents reached the register with a severity. **SD-11** (partial): Shows a secret exposure linked to SD-11 was handled as an incident. |
| Module gap | Tasks has no incident marker and no notice decision field. Needs a shipped task template (and a structured notice field) or the Phase 3.1 Incidents module. |

### `verity.incidents.postmortem_recorded`

Significant incidents have a postmortem and actions. Capability `verity_tasks`, resource `incident`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Incidents (as above) of severity critical or high, or the tenant's own threshold for significant, closed in the last 92 days. |
| Predicate | Each links a postmortem (a document linked to the incident, or an attachment marked as the postmortem) and has at least one corrective or preventive action, or a recorded reason that none is needed. |
| Outcomes | pass, fail per incident; not applicable when no significant incident closed in the window (listed, so the LM-05.B nil return can be matched); error if the Tasks service is unavailable. |
| Evidence kept | Incident list with postmortem link, author, date and action count. |
| Controls | **LM-05** (partial): Shows each significant incident has a postmortem and actions. The quality of the root cause analysis is a person's judgement. |
| Module gap | No postmortem template ships; the content of the postmortem (timeline, impact, root cause, detection gap) is not read. |

### `verity.tasks.capa_on_time`

Corrective and preventive actions close on time. Capability `verity_tasks`, resource `task`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Corrective and preventive actions (issue actions) under issues linked to the control or under incident issues, open at any point in the last 92 days. |
| Predicate | Each has an owner who is an active member and a due date. A completed action was completed by its due date; an action under a critical or high issue was verified by someone other than its owner. No open action is past its due date. An action completed late stays a failure for that window. |
| Outcomes | pass, fail per action; not applicable when there were no actions; error if the Tasks service is unavailable. |
| Evidence kept | Remediation tasks report extended with actions: action, type, issue, owner, due, completed, verified by, on time. |
| Controls | **LM-05** (partial): Shows postmortem actions were owned and closed on time, not that they fixed the cause. **LM-10** (partial): Shows exercise actions were owned and closed. **BC-02** (partial): Shows issues from restore tests were tracked to closure. **BC-03** (partial): Shows issues from continuity exercises were tracked to closure. **SD-15** (partial): Shows corrections of processing errors were owned and closed. |
| Module gap | verity.tasks.remediation_in_sla covers tasks, not issue actions until they are promoted to tasks. |

### `verity.tasks.recurring_review_on_time`

Recurring reviews happen on schedule. Capability `verity_tasks`, resource `task`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Recurring task series linked to the control whose occurrences fell due in the look back window of the objective's frequency (weekly, monthly, quarterly or annual). |
| Predicate | Every occurrence that fell due was closed by an active member by its due date plus a grace (2 days weekly, 7 days monthly or quarterly, 30 days annual), with a closing note or an attachment. |
| Outcomes | pass; fail naming each missed or late occurrence; not configured when no recurring series is linked to the control (the page offers to set one up); not applicable before the first occurrence falls due. |
| Evidence kept | Occurrence list: series, due, closed, closed by, note, attachment names. |
| Controls | **LM-02** (partial): Shows the monthly log review was done on schedule, not what it found. **LM-09** (partial): Shows the quarterly tuning review was done. **LM-12** (partial): Shows the weekly threat source review ran. **BC-04** (partial): Shows the quarterly capacity review was done. **BC-05** (partial): Shows the review of discovered applications ran at its interval. **BC-07** (partial): Shows the yearly register review was done. **SD-14** (partial): Shows the quarterly trace sample was done. **BC-02** (partial): Shows the yearly restore test was scheduled and closed. **BC-03** (partial): Shows the yearly continuity exercise was held. **LM-10** (partial): Shows the yearly tabletop was held. **SD-17** (partial): Shows the database activity review was done. |
| Module gap | None in the data model; recurrence rules and closing notes exist. Needs a link from the series to the control (links table). |

### `verity.tasks.change_approved_independently`

Change requests are approved by someone other than the doer. Capability `verity_tasks`, resource `task`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Tasks created from a task template bound to the control (for example Production data change, Emergency change, Licence exception) in the last 92 days. |
| Predicate | Approval is required and was given by an active member who is neither the owner nor an assignee. Where the control requires approval before work (SD-17, SD-18), it was given before the task started. Where it allows approval afterwards (SD-04), it was given within the window the procedure sets after the task was resolved (default next business day). |
| Outcomes | pass, fail per task; not applicable when no such task exists in the window (listed for a nil return); not configured when no template is bound. |
| Evidence kept | Task list: code, template, owner, assignees, approver, approved at, started, resolved. |
| Controls | **SD-17** (partial): Shows each recorded data change was approved independently before it ran; changes made without a task are found only by SD-17.C. **SD-04** (partial): Shows each recorded emergency change had its retrospective approval in time. **SD-18** (partial): Shows each licence exception was approved by someone other than the requester. |
| Module gap | Needs task templates bound to controls (template_id exists; the binding does not). |

### `verity.vulns.triaged_in_time`

New findings are triaged within the timeframe. Capability `verity_vulnerabilities`, resource `finding`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Findings first detected in the last 92 days, from any source (import, scanner, manual), at the severities the policy names. |
| Predicate | The finding left the new state (to active, in progress, accepted or false positive) and had an owner within the triage time set for its severity. |
| Outcomes | pass, fail per finding; not configured until triage times are a setting; empty window gives insufficient information unless a scan or import ran in the window (then pass with zero). |
| Evidence kept | Vulnerability SLA report with first detected, triaged at, triaged by, triage due. |
| Controls | **SD-03** (partial): Shows dependency and image findings were triaged on time once they reached the register. **LM-11** (partial): Shows every finding in the register was triaged on time. |
| Module gap | Vulnerability settings hold remediation days per severity only; a triage time per severity is needed. |

### `verity.vulns.closed_within_sla`

Findings were fixed within their timeframe over the period. Capability `verity_vulnerabilities`, resource `finding`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Findings fixed, accepted or marked false positive in the last 92 days, and open findings past their due date. |
| Predicate | Fixed on or before its due date, or accepted by an approved exception before its due date. A critical or high fix is verified (retest or a later scan). A fix after the due date fails for that finding although it is closed. A resurfaced finding counts from its first detection. The report also gives the share fixed in time per severity. |
| Outcomes | pass; fail listing late, unverified and overdue findings; not applicable with a statement when nothing closed and nothing is overdue. |
| Evidence kept | Vulnerability SLA report for the window with on time flag and per severity rates. |
| Controls | **LM-11** (partial): Measures remediation against the timeframes over the period; current exposure stays with verity.vulns.within_sla. **SD-03** (partial): Same for dependency and image findings. **SD-05** (partial): Same for input validation findings from tests. |
| Module gap | None; fixed_at, sla_due_at, fixed_verified and transitions exist. |

### `verity.vulns.acceptances_approved`

Risk acceptances on findings are approved and in date. Capability `verity_vulnerabilities`, resource `finding`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Open findings in the accepted state, and exceptions approved in the last 92 days. |
| Predicate | Each has an approved exception, approved by an active member other than the requester, with a reason, compensating measures or an explicit none, and an expiry that has not passed and is no further out than the maximum the policy allows (default 12 months). |
| Outcomes | pass, fail per finding; not applicable when nothing is accepted. |
| Evidence kept | Exception list: finding, requester, approver, approved at, reason, compensating measures, expiry. |
| Controls | **LM-11** (partial): Shows every unfixed finding carries a valid, independently approved acceptance. **SD-03** (partial): Same for dependency and image findings. |
| Module gap | A maximum acceptance length is not a setting today. |

### `verity.vulns.kev_triaged_same_day`

Known exploited findings are assessed the day they appear. Capability `verity_vulnerabilities`, resource `finding`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Findings on vulnerabilities listed in the known exploited catalogue, where the finding was first detected, or the vulnerability was listed, in the last 92 days. |
| Predicate | The finding left the new state within one calendar day of the later of first detection and listing. The report records the days from listing to fix for each fixed finding. |
| Outcomes | pass, fail per finding; error when the catalogue could not be read; not applicable when no such finding exists. |
| Evidence kept | Known exploited findings: CVE, listed at, detected at, triaged at, fixed at, days to fix. |
| Controls | **LM-12** (partial): Shows known exploited flaws in software with a finding were assessed the same day. A flaw in software in use with no finding is invisible. **LM-11** (partial): Supports prioritising exploited weaknesses. |
| Module gap | None; KEV fields and transitions exist. |

### `verity.vulns.assets_scanned`

Every asset in scope was scanned within the interval. Capability `verity_vulnerabilities`, resource `asset`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Assets in service (active or in maintenance) of type infrastructure, cloud or application that are internet facing or in compliance scope. |
| Predicate | Each was a target of an imported vulnerability scan report or a scanner connector run dated within the scan interval the policy sets (default 92 days). |
| Outcomes | pass; fail naming each asset with a dated scan record older than the interval; insufficient information for an asset with no record at all until scan imports carry their target list; error if the module is unavailable. |
| Evidence kept | Asset list with last scan, scan tool, report, authenticated flag. |
| Controls | **LM-13** (partial): Reconciles scan targets with the asset inventory; whether the inventory is complete comes from LM-01. **LM-11** (partial): Same, until LM-13 is adopted. **SD-03** (partial): Registries and images recorded as assets. |
| Module gap | Imported scan reports record findings, not targets, so a clean scan of an asset leaves no trace. Needs a target list on vuln_reports. |

### `verity.vendors.discovered_apps_triaged`

Discovered applications have a decision. Capability `verity_vendors`, resource `discovered_app`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Discovered applications first seen more than 30 days ago, or longer than the review interval the tenant sets. |
| Predicate | The disposition is not pending. An application added as, or linked to, a vendor points to a vendor with an owner and a tier. An ignored application has a reason. |
| Outcomes | pass, fail per application; insufficient information when no discovery source ran and no person recorded a review in the interval. |
| Evidence kept | Discovered applications: name, first seen, users, scopes, disposition, vendor, decided by, decided at. |
| Controls | **BC-05** (partial): Shows each found application was decided. Finding them needs an identity provider connector or a person's review. |
| Module gap | Discovered apps have no connector source yet (Phase 2 identity providers); a reason for ignored apps needs confirming in the schema. |

### `verity.vendors.subprocessor_list_current`

The published subprocessor list matches the vendor register. Capability `verity_vendors`, resource `vendor`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Approved, active vendors that process customer personal data, and the published subprocessor list document linked to BC-06. |
| Predicate | Each such vendor has services, data types and data location recorded, and the list document's latest published version is newer than the latest change to that set of vendors (an approval, a termination or a change of location). |
| Outcomes | pass; fail naming the vendors changed after the last publication; not configured when no list document is linked; not applicable when the profile says no customer data goes to subprocessors. |
| Evidence kept | Subprocessor report: vendor, service, data types, location, approved, last change; list document version and publication date. |
| Controls | **BC-06** (partial): Shows the register and the published list agree in time. Whether customers were told before use stays with people. |
| Module gap | Vendors have no flag for customer data as opposed to staff data; Verity does not publish the list or record customer notices. |

### `verity.vendors.offboarding_complete`

Vendors that left were offboarded. Capability `verity_vendors`, resource `vendor`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Vendors and engagements terminated in the last 12 months. |
| Predicate | Each has an offboarding record with access revoked (date and who), data return or deletion attested or a recorded reason no data was held, contract provisions reviewed, and a completion date. |
| Outcomes | pass, fail per vendor; not applicable when none were terminated. |
| Evidence kept | Offboarding report: vendor, reason, access revoked at, by, data return attested, completed. |
| Controls | **BC-07** (partial): Shows recorded offboarding was complete; whether the access was really removed in each system needs the system itself. |
| Module gap | None; vendor_offboardings exists. |

### `verity.vendors.security_terms_on_file`

Critical and high vendors have the required security terms. Capability `verity_vendors`, resource `vendor`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Approved vendors of tier critical or high with a live engagement. |
| Predicate | An active contract that has not ended records the terms the tier requires: a breach notice time, right to audit, subcontracting terms and data return at exit, with a copy attached. |
| Outcomes | pass, fail per vendor naming the missing terms; not applicable when no such vendor exists. |
| Evidence kept | Contract terms report: vendor, tier, contract, end date, notice hours, audit right, subcontracting, exit clause, file. |
| Controls | **BC-08** (partial): Shows the recorded terms. Whether the text of the contract says so is a person's reading. **BC-10** (partial): Same for development suppliers; code ownership and escrow are not fields today. |
| Module gap | The terms required per tier are not a tiering policy setting; code ownership and escrow are not contract fields. |

### `verity.vendors.assurance_report_reviewed`

Critical vendors' assurance reports are current and read. Capability `verity_vendors`, resource `vendor`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Approved vendors of tier critical with a live engagement. |
| Predicate | A SOC report review whose audit period ended within the last 12 months (or a bridge letter covering the gap), or an ISO certificate in date, reviewed by an active member, with customer controls marked reviewed and subservice organisations recorded or stated as none. A qualified or adverse opinion, or material findings, link to a vendor finding or a risk. |
| Outcomes | pass, fail per vendor; not applicable when there is no critical vendor. |
| Evidence kept | Assurance report review list: vendor, report kind and type, period, opinion, bridge letter, customer controls reviewed, subservice organisations, reviewer, date. |
| Controls | **BC-08** (partial): Shows a current report was recorded as read with the right fields. Whether it was read well is a judgement. |
| Module gap | ISO certificates are documents without structured period fields. |

### `verity.vendors.findings_in_sla`

Vendor findings are handled within their timeframe. Capability `verity_vendors`, resource `vendor_finding`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Open vendor findings, and vendor findings closed in the last 92 days. |
| Predicate | Each has an owner and a treatment. None is past the timeframe the tiering policy sets for its severity without an accepted treatment with a reason. A finding closed late fails for that window. |
| Outcomes | pass, fail per finding; not applicable when there are none. |
| Evidence kept | Vendor findings: vendor, severity, source, treatment, owner, due, closed. |
| Controls | **BC-08** (partial): Shows assessment findings are tracked to closure or accepted. |
| Module gap | None; finding_sla_days_by_severity exists in the tiering policy. |

### `verity.vendors.service_levels_measured`

Critical vendors' service levels are measured. Capability `verity_vendors`, resource `vendor`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Service levels recorded on active contracts of critical vendors. |
| Predicate | Each has a measurement dated within the last 12 months or at the last reassessment. A breached service level links to an acknowledged signal, a finding or a reassessment. |
| Outcomes | pass, fail per service level; not applicable when no service levels are recorded (listed, because an empty list proves nothing). |
| Evidence kept | Service level report: vendor, contract, level, target, last measured, status, follow up. |
| Controls | **BC-08** (partial): Shows delivery against agreed levels was looked at; the measurement itself is entered by people. |
| Module gap | None in the model; measurements are entered by hand. |

### `verity.assets.third_party_in_vendor_register`

Third party assets are linked to a vendor. Capability `verity_assets`, resource `asset`, runs daily.

| Part | Definition |
|---|---|
| Population and period | Assets in service of type third party. |
| Predicate | Each is linked (links table) to a vendor in the register that is not terminated or archived. |
| Outcomes | pass, fail per asset; not applicable when there are none. |
| Evidence kept | Asset list with linked vendor and its status. |
| Controls | **BC-07** (partial): Shows third party systems recorded as assets all appear in the vendor register. **BC-08** (partial): Same population check before tiering. **LM-01** (partial): Reconciles the inventory with the vendor register. |
| Module gap | None; asset to vendor links exist in the linkage module. |

## NEED entries by capability

For the reconciliation step to match with connector check keys. Where an existing key fits, the tables use it instead.

**alerting**

- Alerts per service with acknowledgement and resolution are listed, so alerts nobody acted on show up. (LM-09)
- Each high severity incident in the on call tool links a postmortem. (LM-05)
- Each in scope service has an escalation policy naming the first responder, the escalation timeout and the next level, exported with the period it was in force. (LM-08)
- Every day of the period is covered by a primary and a backup in each in scope schedule, with no gaps. (LM-08)
- Every security alert in the period has a recorded resolution, or a note marking it benign, with time and responder. (LM-04)
- Responders in each in scope on call schedule have at least one working contact method recorded. (LM-07, LM-10)

**ci_cd**

- Builds that introduced a new critical dependency or image finding failed, and any release made despite one has a linked approved exception. (SD-03)
- Container image scan results exist for every image pushed to the production registries in the period. (SD-03)
- Each production deployment is linked to a change approved before the deployment started; deployments without one are listed. (SD-01)
- Each production deployment was preceded by a successful deployment of the same commit to staging. (SD-12)
- Each release build produced a component list stored with the release. (SD-18)
- Merges where a required check failed, was skipped or was bypassed by an administrator are listed. (SD-02)
- People and pipeline identities allowed to run or approve production deployments (environment reviewers, deployment branch rules) are listed. (SD-13)
- Production deployment credentials are stored as pipeline or environment secrets scoped to production, and no long lived key is held by a person. (SD-13)
- Static analysis ran on every merged change and the merge waited for its result. (SD-02)
- Static or dynamic application tests with input validation rules ran on merged changes, with results kept. (SD-05)

**cloud_infrastructure**

- A restore from backup into a non production account or isolated network ran in the last 12 months. (BC-02)
- Backup jobs for every production data store succeeded within the expected window across the period; failed or missed jobs are listed with times. (BC-01)
- Configuration changes in production accounts in the period are listed with actor and time, and each is matched to an approved change or flagged. (SD-01)
- Database audit logging is on for every production database. (SD-17)
- Each backup store has a copy in another region or account and an immutability or lock setting. (BC-01)
- Each database, load balancer and compute group tagged as critical runs across more than one zone or has a standby. (BC-09)
- Each high risk configuration finding in the period has a recorded disposition (fixed, accepted, false alarm) within the time its type allows. (LM-03)
- Each secret in the secrets manager has a last rotated date; values are never read. (SD-11)
- Every container registry in production accounts is listed so its scanning can be checked. (SD-03)
- Every production data store found in connected accounts matches a data asset in the register. (BC-01)
- Lifecycle rules on pipeline intermediate stores expire objects at or before the retention the schedule sets. (SD-07)
- No production snapshot or backup was shared with, or restored into, a non production account in the period. (SD-12)
- Principals with access to production accounts or projects are listed with their roles and how they were granted. (SD-12)
- Principals with restore or delete rights on backup vaults and snapshots are listed with their roles. (BC-01)
- Principals with write access to production databases are listed with their roles. (SD-17)
- Restore and failover events during a test window are recorded with start and end times. (BC-02, BC-09)
- Scaling, instance size and quota changes in the period are listed with time and actor from the cloud change history. (BC-04)
- The central log store has a retention lock or object lock, and system administrators cannot delete it. (LM-02)
- The cloud provider's own vulnerability scanning covers every running instance and image in production accounts. (LM-13)

**identity_provider**

- Applications connected to the identity provider each match an application asset or a vendor. (LM-01)
- Members of the groups that grant production access are listed. (SD-12)

**observability**

- A monitor alerts on a failed or late backup job. (BC-01)
- A monitor alerts when any listed log source sends nothing for longer than the set gap, and each alert was followed up. (LM-02)
- A monitor on the rejected records queue alerts when depth or rejection rate passes the expected level, and each alert was acknowledged. (SD-15)
- Alert volume and alerts closed without action are counted per monitor for the quarter. (LM-09)
- Each integrity check between stages reports a pass or fail per run, and runs are present for every scheduled time. (SD-07)
- Each reconciliation job run records counts, control totals and a pass or break result, and a break raises an alert. (SD-08, SD-15)
- Each scheduled output job ran on time and passed its pre release checks. (SD-16)
- Every in scope system in the asset register has a matching log source that sent events in the last 24 hours. (LM-02)
- No monitored resource reached its limit in the period without a threshold alert firing first. (BC-04)
- Processing errors are counted per job and run, with records affected. (SD-15)
- Production database activity events are retained and searchable for the review period. (SD-17)
- Roles that can delete logs or change retention in the observability tool are listed. (LM-02)

**ticketing**

- Capacity actions are tickets linked to the review that raised them. (BC-04)
- Each direct data change has a ticket approved, before it ran, by someone other than the person who ran it. (SD-17)
- Each drift alert opened a ticket that closed with a cause and an action. (LM-03)
- Each failed backup has a ticket with cause, fix and the date of the next good backup. (BC-01)
- Each new system epic links a design review or threat model item. (SD-10)
- Each project or epic for a new system has a linked security requirements item, approved before work started and checked before release. (SD-10)
- Emergency change tickets record who authorised, the reason and a retrospective approval within the window. (SD-04)
- Incident tickets record severity, owner, date found and date closed. (SD-11, SD-16, LM-04, LM-05, LM-06, LM-07)
- Security event tickets record the triage decision, date and evaluator. (LM-04)
- Tickets of released changes are kept, not deleted, for at least 12 months. (SD-14)

**version_control**

- A component list with licences can be exported for each in scope repository from the provider's dependency graph. (SD-18)
- Changes authored by outside collaborators or supplier accounts were approved by an organisation member before merge. (BC-10)
- Code scanning alerts in the period were fixed, dismissed with a reason, or carried as an exception within the timeframe. (SD-02)
- Dependency changes that add a component with a restricted licence are flagged at review. (SD-18)
- Each merge without a qualifying approval has an after the fact approving review, or a linked ticket, from someone other than the author within the window. (SD-04)
- Every dependency alert in the period has a triage decision (dismissed with a reason, or linked to a fix) within the timeframe for its severity, read with created, dismissed and fixed times. (SD-03)
- Every pull request merged to the default branch references a ticket key in its title, branch or description. (SD-14)
- Every repository with a commit in the period is in scope of the connection or excluded with a recorded reason, and each in scope repository is linked to an application asset. (SD-03, SD-06, SD-11)
- Every secret scanning alert in the period was resolved as revoked within the time the procedure sets, read with created and resolved times. (SD-11)
- Merges to the infrastructure code repository in the period are listed with their reviews. (SD-01)
- Organisation members and outside collaborators with write access to in scope repositories are listed. (SD-10)
- Push protection blocks new secrets on in scope repositories. (SD-11)
- Pushes that bypassed branch protection on in scope repositories are listed from the provider's audit records. (SD-04, SD-06)
- Repository administrators and everyone allowed to bypass branch protection or rulesets on in scope repositories are listed, and bypass is limited to named roles. (SD-06, SD-13)
- The required checks configured on each default branch include every check the testing standard names. (SD-02)

**vulnerability_scanner**

- Findings on known exploited vulnerabilities are reported with first seen time for every scanned asset. (LM-12)

## Existing checks used on controls they do not map to

An artifact can name any check as a source, but a check's evidence attaches only to the controls in its own `controls` list (AU-11). These partial mappings are proposed so the evidence reaches the control. Document checks (`verity.policies.*`, `verity.documents.controlled`) are left out: they judge each document and reach a control through the document's link.

| Check | Proposed partial mapping to |
|---|---|
| `alerts.acknowledged_in_time` | LM-08 |
| `alerts.incidents_resolved` | SD-11, SD-16, LM-04, LM-05, LM-07 |
| `alerts.security_routed` | LM-08 |
| `ci.deployment_history_recorded` | SD-01, SD-12 |
| `ci.production_deploys_controlled` | SD-01 |
| `ci.required_checks_passed` | SD-09 |
| `cloud.config_changes_recorded` | SD-01 |
| `cloud.encryption_at_rest` | BC-01 |
| `cloud.hardening_baseline` | LM-03 |
| `cloud.least_privilege` | SD-12, SD-13, SD-17, BC-01 |
| `cloud.machine_credentials_rotated` | SD-13 |
| `cloud.secrets_managed` | SD-11 |
| `cloud.storage_lifecycle` | SD-07 |
| `cloud.storage_versioned` | BC-01 |
| `idp.access_list_exported` | SD-10 |
| `idp.admins_limited` | SD-12 |
| `idp.connected_apps_known` | BC-07 |
| `observability.anomaly_monitors` | LM-02 |
| `observability.processing_monitored` | SD-07, SD-15 |
| `scanner.scans_current` | LM-13 |
| `tickets.changes_linked` | SD-09 |
| `vcs.code_scanning_enabled` | SD-02 |
| `vcs.default_branch_protected` | SD-02, SD-13, BC-01 |
| `vcs.merged_changes_reviewed` | SD-09, SD-14, LM-03, BC-10 |
| `verity.assets.classified` | BC-06 |
| `verity.management_review.in_12_months` | SD-04, LM-12 |
| `verity.risks.treated` | LM-12, BC-08 |
| `verity.vendors.assessed_in_cadence` | SD-10 |
| `verity.vendors.owner_and_tier` | BC-05, BC-08 |
| `verity.vulns.kev_owned` | LM-12 |
| `verity.vulns.within_sla` | SD-03, SD-05, LM-12 |

`verity.tasks.remediation_in_sla` and `tickets.remediation_tracked` are named on the deficiency log of many controls. Rather than fifteen static mappings, they should attach each result to the control its task or ticket is linked to, the way document checks do. The same mappings are in `check_mapping_changes` of [sd-lm-bc.controls.json](sd-lm-bc.controls.json).

## Control by control

### SD-01 Change authorization and approval

Decision: revise objectives. SOC 2: CC8.1 (full); CC5.2 (partial). ISO 27001:2022: A.8.19 Approved software only on live systems (partial); A.8.32 Approval and control of changes (partial).

GitHub already reads every merged pull request with its reviews, so the change list is partly collected today. That proves code review, not authorisation of the change: the approval with impact and rollback sits on a ticket (Jira, P2) or on a Verity task that requires approval. The reworded SD-01.B adds infrastructure, configuration, database and server software changes to the population; only a cloud connector (P2) lists those, and software installed by hand on a host stays visible only to a host agent, which is not in the catalogue. Standard changes (SD-01.E) stay with people: no system knows which changes were approved in advance as standard.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `change-management-policy` | SD-01.A, SD-01.E | person | template `change-management-procedure` (the procedure covers what counts as a change, approval, testing, rollback, standard and emergency changes); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-change-management-procedure` | SD-01.A | document:change-management-procedure | template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `change-requests-with-approval-for-a` | SD-01.B, SD-01.C, SD-01.D, SD-01.E | check:vcs.merged_changes_reviewed, person | `vcs.merged_changes_reviewed` (partial, P1); `tickets.changes_linked` (partial, P2); NEED ci_cd: Each production deployment is linked to a change approved before the deployment started; deployments without one are listed. (partial, P2); Tasks module: Change requests as tasks that require approval, `verity.tasks.change_approved_independently` NEW; person | P1 |
| `sample-of-reviewed-changes` | SD-01.B, SD-01.D | check:vcs.merged_changes_reviewed, person | `vcs.merged_changes_reviewed` (partial, P1); person | P1 |
| `deployment-history-for-a-sample-of` | SD-01.B | person | `ci.deployment_history_recorded` (partial, P2); `ci.production_deploys_controlled` (partial, P2); person | P2 |
| `infrastructure-and-configuration-change-history` (proposed) | SD-01.B | none (proposed) | `cloud.config_changes_recorded` (partial, P2); NEED cloud_infrastructure: Configuration changes in production accounts in the period are listed with actor and time, and each is matched to an approved change or flagged. (partial, P2); NEED version_control: Merges to the infrastructure code repository in the period are listed with their reviews. (partial, P1); person | P1 |
| `log-of-control-deficiencies-with-owner` | SD-01.D | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |

### SD-02 Automated testing in CI

Decision: revise objectives. SOC 2: CC8.1 (partial); PI1.3 (partial). ISO 27001:2022: A.8.25 Security rules for building software (partial); A.8.29 Testing for weaknesses before release (partial); A.8.32 Approval and control of changes (partial).

GitHub shows whether required checks are configured (vcs.status_checks_required, running). Whether each merge actually passed them needs CI run results (ci.required_checks_passed), which arrive with the CI and CD capability in P2 for GitHub Actions, GitLab CI and Bitbucket Pipelines. The new SD-02.F asks that static analysis ran; GitHub code scanning settings and alerts are a P1 extension. SD-02.E applies only when Processing Integrity is in scope, and an engineer must show which tests check accuracy and completeness: no system can tell what a test proves.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `testing-standard-stating-what-must-pass` | SD-02.A, SD-02.B, SD-02.F | person | template `engineering-security-standard` (section 3, Automated Tests); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-engineering-security-standard` | SD-02.A | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `branch-protection-settings` | SD-02.B | check:vcs.default_branch_protected, check:vcs.review_required | `vcs.status_checks_required` (full, P1); `vcs.default_branch_protected` (partial, P1); NEED version_control: The required checks configured on each default branch include every check the testing standard names. (partial, P1); person | P1 |
| `test-run-results-for-a-sample` | SD-02.C, SD-02.D, SD-02.E | person | `ci.required_checks_passed` (full, P2); NEED ci_cd: Merges where a required check failed, was skipped or was bypassed by an administrator are listed. (partial, P2); `vcs.status_checks_required` (partial, P1); person | P1 |
| `log-of-control-deficiencies-with-owner` | SD-02.D | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |
| `doc-processing-integrity-procedure` | SD-02.E | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `static-analysis-results-for-merged-changes` (proposed) | SD-02.F | none (proposed) | `vcs.code_scanning_enabled` (partial, P1); NEED ci_cd: Static analysis ran on every merged change and the merge waited for its result. (partial, P2); NEED version_control: Code scanning alerts in the period were fixed, dismissed with a reason, or carried as an exception within the timeframe. (partial, P1); Vulnerabilities module: Findings from code review reports, `verity.vulns.triaged_in_time` NEW; person | P1 |

Interviews no system replaces: SD-02.E.

### SD-03 Dependency and image scanning

Decision: split. SOC 2: CC6.8 (partial); CC7.1 (partial). ISO 27001:2022: A.5.21 Technology supply chain risk (partial); A.5.32 Software licenses and IP ownership (partial, moves out); A.8.8 Finding and fixing technical weaknesses (partial); A.8.28 Writing code that resists attack (partial); A.8.29 Testing for weaknesses before release (partial).

GitHub shows Dependabot alerts are on (running). Reading the alerts themselves, with created, dismissed and fixed times, is a P1 extension that needs read access to the alerts; once findings reach the Vulnerabilities module, the new triage and SLA checks evaluate them. Image scanning needs a registry or CI source (P2). Build failure on a new critical finding (SD-03.C) needs CI results (P2). The component list and licence review moves to SD-18.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `dependency-vulnerability-triage-standard-with-timeframes` | SD-03.A | person | template `engineering-security-standard` (section 4, Dependencies, Images and Licences); template `operations-security-policy` (Finding and fixing vulnerabilities); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-engineering-security-standard` | SD-03.A | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `open-alerts-triaged-within-the-timeframe` | SD-03.B, SD-03.D, SD-03.E | person | `vcs.dependency_alerts_enabled` (partial, P1); NEED version_control: Every dependency alert in the period has a triage decision (dismissed with a reason, or linked to a fix) within the timeframe for its severity, read with created, dismissed and fixed times. (partial, P1); NEED ci_cd: Container image scan results exist for every image pushed to the production registries in the period. (partial, P2); Vulnerabilities module: Vulnerability SLA report filtered to dependency and image findings, `verity.vulns.triaged_in_time` NEW; `verity.vulns.within_sla` (partial, P1); person | P1 |
| `asset-inventory` | SD-03.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to applications and registries; NEED version_control: Every repository with a commit in the period is in scope of the connection or excluded with a recorded reason, and each in scope repository is linked to an application asset. (partial, P1); NEED cloud_infrastructure: Every container registry in production accounts is listed so its scanning can be checked. (partial, P2); `verity.vulns.assets_scanned` (partial, P1, NEW); person | P1 |
| `test-run-results-for-a-sample` | SD-03.C | person | NEED ci_cd: Builds that introduced a new critical dependency or image finding failed, and any release made despite one has a linked approved exception. (partial, P2); person | P2 |
| `vulnerability-register-with-remediation-and-accepted` | SD-03.C, SD-03.E | check:verity.vulns.within_sla | `verity.vulns.within_sla` (partial, P1); `verity.vulns.closed_within_sla` (partial, P1, NEW); `verity.vulns.acceptances_approved` (partial, P1, NEW); Vulnerabilities module: Vulnerability SLA report; person | P1 |
| `log-of-control-deficiencies-with-owner` | SD-03.E | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |

Interviews no system replaces: SD-03.B.

### SD-04 Emergency change procedure

Decision: keep. SOC 2: CC8.1 (partial). ISO 27001:2022: A.8.32 Approval and control of changes (partial).

Merges without a qualifying approval are already in the data vcs.merged_changes_reviewed reads, so vcs.unreviewed_merges_recorded is a P1 GitHub extension. Who authorised the emergency and why are recorded by people, in a ticket or in a Verity task; the new verity.tasks.change_approved_independently checks the later approval came from someone else within the window. The management review of the emergency rate (SD-04.E) is a person's judgement in the minutes.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `emergency-change-procedure` | SD-04.A | person | template `change-management-procedure` (section 4, Emergency changes); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-change-management-procedure` | SD-04.A | document:change-management-procedure | template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `emergency-changes-with-their-after-the` | SD-04.B, SD-04.C, SD-04.D | person | `vcs.unreviewed_merges_recorded` (partial, P1); NEED version_control: Each merge without a qualifying approval has an after the fact approving review, or a linked ticket, from someone other than the author within the window. (partial, P1); NEED ticketing: Emergency change tickets record who authorised, the reason and a retrospective approval within the window. (partial, P2); Tasks module: Emergency change tasks, `verity.tasks.change_approved_independently` NEW; person | P1 |
| `unreviewed-merge-log` | SD-04.B | person | `vcs.unreviewed_merges_recorded` (partial, P1); NEED version_control: Pushes that bypassed branch protection on in scope repositories are listed from the provider's audit records. (partial, P1); person | P1 |
| `management-review-agenda-and-minutes` | SD-04.E | check:verity.management_review.in_12_months, person | `verity.management_review.in_12_months` (partial, P1); person | P1 |

Interviews no system replaces: SD-04.E.

### SD-05 Input validation controls

Decision: revise objectives. SOC 2: PI1.2 (partial). ISO 27001:2022: A.8.26 Stating security needs before building or buying (partial); A.8.28 Writing code that resists attack (partial).

Static analysis settings (vcs.code_scanning_enabled, a P1 GitHub extension) and imported code review and penetration test findings show validation was tested; the Vulnerabilities module tracks fixes and retests. Whether the tests were adequate is the tester's judgement. SD-05.D moves to SD-15. SD-05 maps to ISO27001:A.8.26 and A.8.28, so it should be adoptable without Processing Integrity.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `input-validation-standard` | SD-05.A | person | template `engineering-security-standard` (section 6, Coding Rules and Input Handling); template `processing-integrity-procedure` (section 3, Checks on Input); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-engineering-security-standard` | SD-05.A | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-processing-integrity-procedure` | SD-05.A | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `evidence-validation-was-tested` | SD-05.B, SD-05.C | person | `vcs.code_scanning_enabled` (partial, P1); NEED ci_cd: Static or dynamic application tests with input validation rules ran on merged changes, with results kept. (partial, P2); Vulnerabilities module: Findings from code review and penetration test reports with input handling weakness types, `verity.vulns.closed_within_sla` NEW; person | P1 |
| `penetration-test-report-from-an-independent` | SD-05.B | person | Vulnerabilities module: Reports of type penetration test, uploaded and parsed, with their findings; person | P1 |
| `remediation-of-findings-with-retest-evidence` | SD-05.C | person | Vulnerabilities module: Findings with verified fixes and remediation plans, `verity.vulns.closed_within_sla` NEW; person | P1 |
| `vulnerability-register-with-remediation-and-accepted` | SD-05.C | check:verity.vulns.within_sla | `verity.vulns.within_sla` (partial, P1); `verity.vulns.closed_within_sla` (partial, P1, NEW); `verity.vulns.acceptances_approved` (partial, P1, NEW); Vulnerabilities module: Vulnerability SLA report; person | P1 |

### SD-06 Peer code review (branch protection)

Decision: keep. SOC 2: CC8.1 (partial). ISO 27001:2022: A.5.3 Separating conflicting duties (partial); A.8.4 Who can read and change code (partial); A.8.25 Security rules for building software (partial); A.8.28 Writing code that resists attack (partial); A.8.30 Oversight of contracted developers (partial); A.8.32 Approval and control of changes (partial).

The strongest automated control in these families. GitHub collects branch protection and every merged change with its reviews (running), and the merged change list fills SD-06.D in full when the daily runs cover the period without truncation. Repository scope (SD-06.B) is partly the connection's scope list; a person confirms nothing holding production code is missing, and the asset link is proposed. Ruleset bypass lists are not read yet, so SD-06.C stays partial. GitLab and Bitbucket implement the same checks in P2.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `peer-review-standard-in-the-development` | SD-06.A | person | template `engineering-security-standard` (section 2, Peer Review and Branch Protection); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-change-management-procedure` | SD-06.A | document:change-management-procedure | template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-engineering-security-standard` | SD-06.A, SD-06.C | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `sample-of-reviewed-changes` | SD-06.B, SD-06.D | check:vcs.merged_changes_reviewed, person | `vcs.merged_changes_reviewed` (full, P1); NEED version_control: Every repository with a commit in the period is in scope of the connection or excluded with a recorded reason, and each in scope repository is linked to an application asset. (partial, P1); person | P1 |
| `asset-inventory` | SD-06.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to applications; NEED version_control: Every repository with a commit in the period is in scope of the connection or excluded with a recorded reason, and each in scope repository is linked to an application asset. (partial, P1); person | P1 |
| `branch-protection-settings` | SD-06.C | check:vcs.default_branch_protected, check:vcs.review_required | `vcs.default_branch_protected` (full, P1); `vcs.review_required` (full, P1); NEED version_control: Repository administrators and everyone allowed to bypass branch protection or rulesets on in scope repositories are listed, and bypass is limited to named roles. (partial, P1); person | P1 |
| `unreviewed-merge-log` | SD-06.E | person | `vcs.unreviewed_merges_recorded` (partial, P1); NEED version_control: Pushes that bypassed branch protection on in scope repositories are listed from the provider's audit records. (partial, P1); person | P1 |

Interviews no system replaces: SD-06.B.

### SD-07 Pipeline storage integrity

Decision: keep. SOC 2: PI1.5 (partial). ISO 27001:2022: none.

Integrity checks between stages run in the customer's own jobs. Observability monitors (P2) can show job health and missing runs, not the checksums themselves. Versioned storage is a cloud setting (cloud.storage_versioned, P2). Idempotence under retry (SD-07.D) is an engineering claim people demonstrate. Applies only with Processing Integrity.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `pipeline-storage-design-showing-stages-and` | SD-07.A, SD-07.D | person | template `processing-integrity-procedure` (section 6, Stored Data Between Stages); Documents module: Policy register, `verity.policies.reviewed`; `cloud.storage_versioned` (partial, P2); person | P1 |
| `doc-processing-integrity-procedure` | SD-07.A | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `integrity-check-results` | SD-07.B, SD-07.C, SD-07.D | person | NEED observability: Each integrity check between stages reports a pass or fail per run, and runs are present for every scheduled time. (partial, P2); `observability.processing_monitored` (partial, P2); `cloud.storage_versioned` (partial, P2); Tasks module: Issues raised for failed integrity checks, `verity.tasks.remediation_in_sla`; person | P1 |
| `log-of-control-deficiencies-with-owner` | SD-07.C | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |
| `data-retention-schedule` | SD-07.E | person | template `data-management-policy` (Appendix B, Data Retention Matrix); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `evidence-data-was-deleted-when-retention` | SD-07.E | person | `cloud.storage_lifecycle` (partial, P2); NEED cloud_infrastructure: Lifecycle rules on pipeline intermediate stores expire objects at or before the retention the schedule sets. (partial, P2); person | P2 |

Interviews no system replaces: SD-07.D.

### SD-08 Processing reconciliation and monitoring

Decision: keep. SOC 2: PI1.3 (partial); PI1.4 (partial). ISO 27001:2022: none.

Job monitors (observability.processing_monitored, P2) cover runs that failed or did not start. Reconciliation results come from the customer's jobs; breaks can be held as Verity issues with their SLA. Applies only with Processing Integrity.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `reconciliation-procedure` | SD-08.A | person | template `processing-integrity-procedure` (sections 4 and 5, checks during processing and on output); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-processing-integrity-procedure` | SD-08.A | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `reconciliation-results-and-how-exceptions-were` | SD-08.B, SD-08.C, SD-08.D | person | `observability.processing_monitored` (partial, P2); NEED observability: Each reconciliation job run records counts, control totals and a pass or break result, and a break raises an alert. (partial, P2); Tasks module: Issues for reconciliation breaks, `verity.tasks.remediation_in_sla`; person | P1 |
| `log-of-control-deficiencies-with-owner` | SD-08.D | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |

Interviews no system replaces: SD-08.B.

### SD-09 Processing specifications

Decision: keep. SOC 2: PI1.1 (partial). ISO 27001:2022: none.

Specifications are documents: the processing integrity template holds them, and the Documents module keeps versions, owners and approvals (verity.documents.controlled). Whether the version matches production (SD-09.B) and whether tests trace to the specification (SD-09.C) are engineering judgements no system makes.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `processing-specifications-covering-inputs-outputs-and` | SD-09.A, SD-09.B, SD-09.C | person | template `processing-integrity-procedure` (section 2, Specifications); Documents module: Policy register, `verity.policies.reviewed`; `verity.documents.controlled` (partial, P1); person | P1 |
| `doc-processing-integrity-procedure` | SD-09.A | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `review-of-specifications-after-change` | SD-09.B, SD-09.D | person | Documents module: Specification document versions with approver and date, `verity.documents.controlled`; person | P1 |
| `test-run-results-for-a-sample` | SD-09.C | person | `ci.required_checks_passed` (partial, P2); person | P2 |
| `change-requests-with-approval-for-a` | SD-09.D | check:vcs.merged_changes_reviewed, person | `tickets.changes_linked` (partial, P2); `vcs.merged_changes_reviewed` (partial, P1); person | P1 |

Interviews no system replaces: SD-09.B.

### SD-10 Secure SDLC policy

Decision: revise objectives. SOC 2: CC8.1 (partial). ISO 27001:2022: A.5.8 Security steps in every project (partial); A.5.37 Procedures for running systems (partial); A.8.25 Security rules for building software (full); A.8.26 Stating security needs before building or buying (partial); A.8.27 Building security into system design (full); A.8.28 Writing code that resists attack (partial); A.8.29 Testing for weaknesses before release (partial).

Policy and policy review are Documents work (running). Acquired systems are assessed in Vendors (running). Security requirements per new system and design reviews are people's records; a ticketing connector (P2) helps find the population, and the Assets and Vendors modules list systems that are new in the period. Secure coding training has no source in the catalogue and stays people only; GitHub can list who writes code (P1 extension).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `secure-development-lifecycle-policy` | SD-10.A | person | template `secure-development-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-secure-development-policy` | SD-10.A, SD-10.E | document:secure-development-policy | template `secure-development-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `approved-security-requirements-for-a-sample` | SD-10.B, SD-10.F | person | NEED ticketing: Each project or epic for a new system has a linked security requirements item, approved before work started and checked before release. (partial, P2); Assets module: Asset inventory: applications first seen in the period; Vendors module: Vendors approved in the period; person | P1 |
| `security-assessment-for-each-critical-vendor` | SD-10.B | check:verity.vendors.assessed_in_cadence | `verity.vendors.assessed_in_cadence` (partial, P1); Vendors module: Vendor assessments for systems bought in the period; person | P1 |
| `evidence-security-was-considered-in-the` | SD-10.C | person | Documents module: Design review documents linked to SD-10, with approver and date, `verity.documents.controlled`; NEED ticketing: Each new system epic links a design review or threat model item. (partial, P2); person | P1 |
| `secure-coding-training-completion-for-developers` | SD-10.D | person | person | people-only |
| `group-and-role-membership-export` | SD-10.D | person | NEED version_control: Organisation members and outside collaborators with write access to in scope repositories are listed. (partial, P1); `idp.access_list_exported` (partial, P2); person | P1 |
| `review-and-re-approval-record-for` | SD-10.E | check:verity.policies.reviewed | `verity.policies.reviewed` (partial, P1); person | P1 |

Interviews no system replaces: SD-10.E.

### SD-11 Secret scanning

Decision: keep. SOC 2: CC6.1 (partial); CC7.1 (partial). ISO 27001:2022: A.5.17 Passwords and credential handling (partial); A.8.28 Writing code that resists attack (partial).

GitHub shows secret scanning is on (running). Reading the alerts with their resolution and times, and push protection, are P1 extensions. Rotation proof needs the secrets manager (P2). Misuse before rotation (SD-11.D) needs a person to read the access logs and conclude: no system can prove a leaked credential was not used.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `procedure-for-rotating-exposed-secrets` | SD-11.A | person | template `engineering-security-standard` (section 5, Secrets in Code); template `infrastructure-security-standard` (section 4, Secrets); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-engineering-security-standard` | SD-11.A | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `records-of-exposed-secrets-that-were` | SD-11.B, SD-11.C, SD-11.D, SD-11.E | person | `vcs.secret_scanning_enabled` (partial, P1); NEED version_control: Every secret scanning alert in the period was resolved as revoked within the time the procedure sets, read with created and resolved times. (partial, P1); NEED version_control: Push protection blocks new secrets on in scope repositories. (partial, P1); Tasks module: Exposure raised as a security incident issue linked to SD-11, `verity.incidents.registered` NEW; person | P1 |
| `asset-inventory` | SD-11.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to applications; NEED version_control: Every repository with a commit in the period is in scope of the connection or excluded with a recorded reason, and each in scope repository is linked to an application asset. (partial, P1); person | P1 |
| `secret-store-rotation-list` | SD-11.C | person | `cloud.secrets_managed` (partial, P2); NEED cloud_infrastructure: Each secret in the secrets manager has a last rotated date; values are never read. (partial, P2); person | P2 |
| `security-incident-register` | SD-11.E | person | Tasks module: Security incident register report, `verity.incidents.registered` NEW; `alerts.incidents_resolved` (partial, P2); NEED ticketing: Incident tickets record severity, owner, date found and date closed. (partial, P2); person | P1 |

Interviews no system replaces: SD-11.B.

### SD-12 Separate dev/staging/production

Decision: keep. SOC 2: CC8.1 (partial). ISO 27001:2022: A.8.31 Keeping test and live systems apart (full).

Environment separation is the cloud account structure check (cloud.environments_separated, full for SD-12.B, P2). Who can reach production needs cloud and identity provider lists (P2). Promotion order needs deployment history (P2). Masked or synthetic test data (SD-12.E) stays with people, helped by a cloud read that no production snapshot was copied into a lower account.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `environment-architecture-showing-separation` | SD-12.A | person | template `secure-development-policy` (Separate places to build, test and run); Documents module: Policy register, `verity.policies.reviewed`; `cloud.environments_separated` (partial, P2); person | P1 |
| `doc-secure-development-policy` | SD-12.A | document:secure-development-policy | template `secure-development-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `cloud-accounts-and-production-access` | SD-12.B, SD-12.C, SD-12.E | person | `cloud.environments_separated` (full, P2); `cloud.least_privilege` (partial, P2); NEED cloud_infrastructure: Principals with access to production accounts or projects are listed with their roles and how they were granted. (partial, P2); NEED identity_provider: Members of the groups that grant production access are listed. (partial, P2); person | P2 |
| `list-of-privileged-accounts-with-approval` | SD-12.C | person | `cloud.least_privilege` (partial, P2); `idp.admins_limited` (partial, P2); person | P2 |
| `deployment-history-for-a-sample-of` | SD-12.D | person | `ci.deployment_history_recorded` (partial, P2); NEED ci_cd: Each production deployment was preceded by a successful deployment of the same commit to staging. (partial, P2); person | P2 |
| `evidence-test-data-is-masked-or` | SD-12.E | person | NEED cloud_infrastructure: No production snapshot or backup was shared with, or restored into, a non production account in the period. (partial, P2); person | P2 |

### SD-13 Controlled production deployments

Decision: keep. SOC 2: CC8.1 (partial). ISO 27001:2022: A.8.19 Approved software only on live systems (partial); A.8.32 Approval and control of changes (partial).

Deployment history and environment protection are CI and CD reads (P2). The history fills SD-13.E in full once every production pipeline is connected. Repository administrators and bypass rights are a P1 GitHub extension. That deployment credentials are not on laptops is partly shown by cloud key ages (P2) and otherwise only by interview.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `deployment-procedure-stating-who-may-release` | SD-13.A | person | template `engineering-security-standard` (section 8, Releases to Production); template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-change-management-procedure` | SD-13.A | document:change-management-procedure | template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-engineering-security-standard` | SD-13.A | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `deployment-history-for-a-sample-of` | SD-13.B, SD-13.C, SD-13.E | person | `ci.deployment_history_recorded` (full, P2); `ci.production_deploys_controlled` (partial, P2); person | P2 |
| `branch-protection-settings` | SD-13.B | check:vcs.default_branch_protected, check:vcs.review_required | `vcs.default_branch_protected` (partial, P1); person | P1 |
| `list-of-privileged-accounts-with-approval` | SD-13.D | person | NEED ci_cd: People and pipeline identities allowed to run or approve production deployments (environment reviewers, deployment branch rules) are listed. (partial, P2); NEED version_control: Repository administrators and everyone allowed to bypass branch protection or rulesets on in scope repositories are listed, and bypass is limited to named roles. (partial, P1); `cloud.least_privilege` (partial, P2); person | P1 |
| `inventory-of-service-accounts-and-keys` | SD-13.D | person | `cloud.machine_credentials_rotated` (partial, P2); NEED ci_cd: Production deployment credentials are stored as pipeline or environment secrets scoped to production, and no long lived key is held by a person. (partial, P2); person | P2 |

Interviews no system replaces: SD-13.D.

### SD-14 Change traceability

Decision: keep. SOC 2: CC8.1 (partial). ISO 27001:2022: A.8.32 Approval and control of changes (partial).

Traceability joins tickets, pull requests and deployments. A ticket key in each merged pull request is a GitHub only check (P1). The full join (tickets.changes_linked with ci.deployment_history_recorded) needs Jira and CI (P2). The quarterly trace sample is people's work; a recurring Verity task shows it was done on schedule.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-change-management-procedure` | SD-14.A | document:change-management-procedure | template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `change-records-linking-request-review-and` | SD-14.B, SD-14.C, SD-14.D, SD-14.E | person | `tickets.changes_linked` (partial, P2); `ci.deployment_history_recorded` (partial, P2); `vcs.merged_changes_reviewed` (partial, P1); NEED version_control: Every pull request merged to the default branch references a ticket key in its title, branch or description. (partial, P1); NEED ticketing: Tickets of released changes are kept, not deleted, for at least 12 months. (partial, P2); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |
| `sample-of-reviewed-changes` | SD-14.C | check:vcs.merged_changes_reviewed, person | `vcs.merged_changes_reviewed` (partial, P1); person | P1 |
| `data-retention-schedule` | SD-14.D | person | template `data-management-policy` (Appendix B, Data Retention Matrix); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `log-of-control-deficiencies-with-owner` | SD-14.E | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |

### SD-15 Processing error handling and correction

Decision: add. SOC 2: PI1.2 (partial, proposed); PI1.3 (partial, proposed). ISO 27001:2022: none.

Proposed. Rejected records and processing errors are logged and corrected in the customer's systems; Verity holds each error as an issue with corrective actions and checks they close on time. Monitors on queues and rejection rates come with observability (P2). Applies only with Processing Integrity.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-processing-integrity-procedure` | SD-15.A | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `processing-error-log` (proposed) | SD-15.B, SD-15.C | none (proposed) | NEED observability: Processing errors are counted per job and run, with records affected. (partial, P2); Tasks module: Issues for processing errors with correction actions, `verity.tasks.capa_on_time` NEW; person | P1 |
| `reconciliation-results-and-how-exceptions-were` | SD-15.C | person | `observability.processing_monitored` (partial, P2); NEED observability: Each reconciliation job run records counts, control totals and a pass or break result, and a break raises an alert. (partial, P2); Tasks module: Issues for reconciliation breaks, `verity.tasks.remediation_in_sla`; person | P1 |
| `evidence-validation-was-tested` | SD-15.D | person | `observability.processing_monitored` (partial, P2); NEED observability: A monitor on the rejected records queue alerts when depth or rejection rate passes the expected level, and each alert was acknowledged. (partial, P2); Tasks module: Issues raised for rejection spikes, `verity.tasks.remediation_in_sla`; person | P1 |

Interviews no system replaces: SD-15.D.

### SD-16 Output delivery and review

Decision: add. SOC 2: PI1.4 (partial, proposed). ISO 27001:2022: none.

Proposed. Output production and its checks come from job monitoring (P2). Whether an output reached only its intended recipient is in the delivery system's own records and is read by people. Applies only with Processing Integrity.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `processing-specifications-covering-inputs-outputs-and` | SD-16.A | person | template `processing-integrity-procedure` (section 2, Specifications); Documents module: Policy register, `verity.policies.reviewed`; `verity.documents.controlled` (partial, P1); person | P1 |
| `doc-processing-integrity-procedure` | SD-16.A | document:processing-integrity-procedure | template `processing-integrity-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `output-delivery-log` (proposed) | SD-16.B, SD-16.C | none (proposed) | NEED observability: Each scheduled output job ran on time and passed its pre release checks. (partial, P2); person | P2 |
| `security-incident-register` | SD-16.C | person | Tasks module: Security incident register report, `verity.incidents.registered` NEW; `alerts.incidents_resolved` (partial, P2); NEED ticketing: Incident tickets record severity, owner, date found and date closed. (partial, P2); person | P1 |

### SD-17 Direct changes to production data

Decision: add. SOC 2: CC8.1 (partial, proposed). ISO 27001:2022: A.8.32 Approval and control of changes (partial, proposed).

Proposed. Direct data changes are recorded as approved requests, in Verity tasks (P1, with the new independence check) or tickets (P2). Who can change production data and the database activity come from the cloud (P2). Comparing activity with approved changes is a person's review.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-change-management-procedure` | SD-17.A | document:change-management-procedure | template `change-management-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `production-data-change-log` (proposed) | SD-17.B | none (proposed) | Tasks module: Production data change tasks, `verity.tasks.change_approved_independently` NEW; NEED ticketing: Each direct data change has a ticket approved, before it ran, by someone other than the person who ran it. (partial, P2); person | P1 |
| `list-of-privileged-accounts-with-approval` | SD-17.C | person | NEED cloud_infrastructure: Principals with write access to production databases are listed with their roles. (partial, P2); `cloud.least_privilege` (partial, P2); person | P2 |
| `database-activity-log-review` (proposed) | SD-17.C | none (proposed) | NEED cloud_infrastructure: Database audit logging is on for every production database. (partial, P2); NEED observability: Production database activity events are retained and searchable for the review period. (partial, P2); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |

### SD-18 Software component list and licence review

Decision: proposed successor of SD-03. SOC 2: none. ISO 27001:2022: A.5.32 Software licenses and IP ownership (partial, proposed); A.5.21 Technology supply chain risk (partial, proposed).

Proposed. A component list with licences can come from the version control dependency graph (P1 extension, permission unverified) or from the build (P2). Licence exceptions are approved tasks. Whether a licence fits how the product is sold is a legal judgement.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-engineering-security-standard` | SD-18.A | document:engineering-security-standard | template `engineering-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `software-component-list-with-licences` (proposed) | SD-18.B, SD-18.C | none (proposed) | NEED version_control: A component list with licences can be exported for each in scope repository from the provider's dependency graph. (partial, P1); NEED ci_cd: Each release build produced a component list stored with the release. (partial, P2); person | P1 |
| `licence-exceptions-record` (proposed) | SD-18.C | none (proposed) | NEED version_control: Dependency changes that add a component with a restricted licence are flagged at review. (partial, P1); Tasks module: Licence exception tasks, `verity.tasks.change_approved_independently` NEW; person | P1 |

### LM-01 Asset and system inventory

Decision: keep. SOC 2: CC2.1 (partial); CC6.1 (partial). ISO 27001:2022: A.5.9 Asset register (partial).

The Assets module holds the inventory and three checks run today (owner, classification, review). Completeness needs discovery: assets.resources_registered for cloud (AWS first, P2) and identity provider applications (P2), plus the new link between third party assets and vendors. Devices have no source in the catalogue, because device management is not planned.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-asset-management-policy` | LM-01.A | document:asset-management-policy | template `asset-management-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `asset-inventory` | LM-01.B, LM-01.C | check:verity.assets.owner_assigned | Assets module: Asset inventory report, `verity.assets.owner_assigned`; `verity.assets.classified` (partial, P1); `assets.resources_registered` (partial, P2); NEED identity_provider: Applications connected to the identity provider each match an application asset or a vendor. (partial, P2); person | P1 |
| `vendor-inventory-with-owner-data-and` | LM-01.C | check:verity.vendors.owner_and_tier | `verity.assets.third_party_in_vendor_register` (partial, P1, NEW); Vendors module: Vendor register report; person | P1 |
| `review-that-the-inventory-is-complete` | LM-01.D | check:verity.assets.reviewed | `verity.assets.reviewed` (partial, P1); `assets.resources_registered` (partial, P2); person | P1 |

### LM-02 Centralized logging and retention

Decision: revise objectives. SOC 2: CC7.2 (partial); CC2.1 (partial). ISO 27001:2022: A.5.28 Preserving forensic evidence (partial); A.8.15 Recording and protecting activity logs (full).

Cloud audit logging and observability retention checks (P2) show logs are collected and kept. Coverage of every in scope system compares the asset register with log sources (P2). Protection from administrators and retention locks are settings reads (P2). The monthly review record is a person's; a recurring Verity task shows it was done on time.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `logging-and-retention-standard` | LM-02.A, LM-02.C | person | template `infrastructure-security-standard` (section 5, Logs, Detection and Alerts); template `operations-security-policy` (Activity logs, Keeping logs safe); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-infrastructure-security-standard` | LM-02.A | document:infrastructure-security-standard | template `infrastructure-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-operations-security-policy` | LM-02.A | document:operations-security-policy | template `operations-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `evidence-logs-are-reviewed` | LM-02.B, LM-02.D | person | `cloud.audit_logging` (partial, P2); `observability.logs_retained` (partial, P2); NEED observability: Every in scope system in the asset register has a matching log source that sent events in the last 24 hours. (partial, P2); `observability.anomaly_monitors` (partial, P2); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |
| `asset-inventory` | LM-02.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to in scope systems that must send logs; NEED observability: Every in scope system in the asset register has a matching log source that sent events in the last 24 hours. (partial, P2); `cloud.audit_logging` (partial, P2); person | P1 |
| `log-store-retention-and-access-settings` (proposed) | LM-02.C, LM-02.G | none (proposed) | `observability.logs_retained` (partial, P2); `cloud.audit_logging` (partial, P2); NEED cloud_infrastructure: The central log store has a retention lock or object lock, and system administrators cannot delete it. (partial, P2); NEED observability: Roles that can delete logs or change retention in the observability tool are listed. (partial, P2); person | P2 |
| `log-source-gap-alerts` (proposed) | LM-02.F | none (proposed) | NEED observability: A monitor alerts when any listed log source sends nothing for longer than the set gap, and each alert was followed up. (partial, P2); `cloud.audit_logging` (partial, P2); Tasks module: Issues raised for log gaps, `verity.tasks.remediation_in_sla`; person | P1 |

Interviews no system replaces: LM-02.C.

### LM-03 Configuration-change detection

Decision: keep. SOC 2: CC7.1 (partial). ISO 27001:2022: A.8.9 Baseline settings for systems (partial); A.8.20 Protection of the network and its devices (partial).

Drift detection is the cloud configuration family (cloud.config_changes_recorded, mapped full to LM-03, P2). When Verity's own cloud checks fail, the control_failed automation opens issues, which gives an investigation trail in Tasks with an SLA. Fixing the cause of recurring drift (LM-03.D) is a judgement.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `approved-configuration-baseline` | LM-03.A, LM-03.B, LM-03.D | person | template `infrastructure-security-standard` (section 1, Configuration Baselines); template `operations-security-policy` (Appendix A, Hardening standards); Documents module: Policy register, `verity.policies.reviewed`; `cloud.hardening_baseline` (partial, P2); `vcs.merged_changes_reviewed` (partial, P1); person | P1 |
| `doc-infrastructure-security-standard` | LM-03.A, LM-03.C | document:infrastructure-security-standard | template `infrastructure-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `alerts-on-drift-that-were-investigated` | LM-03.B, LM-03.C, LM-03.D | person | `cloud.config_changes_recorded` (partial, P2); NEED cloud_infrastructure: Each high risk configuration finding in the period has a recorded disposition (fixed, accepted, false alarm) within the time its type allows. (partial, P2); NEED ticketing: Each drift alert opened a ticket that closed with a cause and an action. (partial, P2); Tasks module: Issues raised by failing cloud checks (control_failed automation), `verity.tasks.remediation_in_sla`; person | P1 |

Interviews no system replaces: LM-03.D.

### LM-04 Security event evaluation

Decision: keep. SOC 2: CC7.3 (full). ISO 27001:2022: A.5.25 Triage of security events (full); A.8.16 Watching systems for unusual behavior (partial).

Acknowledgement and resolution of alerts come from the on call tool (P2). Recording a decision on every event, including benign ones, is people's work, held in Tasks or a ticket queue. Consistency review (LM-04.D) is a judgement.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `event-triage-procedure` | LM-04.A, LM-04.C | person | template `incident-response-plan` (Severity, Escalation and Internal Reporting); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-incident-response-plan` | LM-04.A | document:incident-response-plan | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `sample-of-evaluated-events-with-the` | LM-04.B, LM-04.C, LM-04.D | person | `alerts.acknowledged_in_time` (partial, P2); NEED alerting: Every security alert in the period has a recorded resolution, or a note marking it benign, with time and responder. (partial, P2); NEED ticketing: Security event tickets record the triage decision, date and evaluator. (partial, P2); Tasks module: Events triaged as issues in Tasks; person | P1 |
| `security-incident-register` | LM-04.C | person | Tasks module: Security incident register report, `verity.incidents.registered` NEW; `alerts.incidents_resolved` (partial, P2); NEED ticketing: Incident tickets record severity, owner, date found and date closed. (partial, P2); person | P1 |

Interviews no system replaces: LM-04.D.

### LM-05 Incident postmortems with actions

Decision: revise objectives. SOC 2: CC7.4 (partial); CC7.5 (partial). ISO 27001:2022: 10.2 Fixing failures and their causes (partial); A.5.26 Handling security incidents (partial); A.5.27 Lessons from incidents (full).

Postmortems and corrective actions can live in Tasks: an incident issue, a linked postmortem and corrective actions with owners and dates. Two new checks evaluate them. The quality of the root cause analysis, the themes review and whether an action worked are judgements.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-incident-response-plan` | LM-05.A, LM-05.D | document:incident-response-plan | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-corrective-action-procedure` | LM-05.A | document:corrective-action-procedure | template `corrective-action-procedure`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `postmortem-for-each-significant-incident` | LM-05.B, LM-05.C, LM-05.D, LM-05.E | person | Tasks module: Incident issues with postmortem link, `verity.incidents.postmortem_recorded` NEW; NEED alerting: Each high severity incident in the on call tool links a postmortem. (partial, P2); person | P1 |
| `security-incident-register` | LM-05.B | person | Tasks module: Security incident register report, `verity.incidents.registered` NEW; `alerts.incidents_resolved` (partial, P2); NEED ticketing: Incident tickets record severity, owner, date found and date closed. (partial, P2); person | P1 |
| `corrective-actions-tracked-to-closure` | LM-05.C, LM-05.E | person | Tasks module: Actions under incident issues, `verity.tasks.capa_on_time` NEW; `verity.tasks.remediation_in_sla` (partial, P1); `tickets.remediation_tracked` (partial, P2); person | P1 |

Interviews no system replaces: LM-05.D.

### LM-06 Incident recovery procedures

Decision: keep. SOC 2: CC7.5 (full). ISO 27001:2022: A.5.26 Handling security incidents (partial).

Incident timelines come from the on call tool (alerts.incidents_resolved, P2) or the incident issue in Tasks. Checking that a system was clean before restoring it (LM-06.C) and declaring recovery complete are people's judgements, recorded in the incident.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `recovery-procedures` | LM-06.A, LM-06.D | person | template `incident-response-plan` (Mitigation and Remediation); template `operating-procedure-template` (one runbook per key system); template `business-continuity-and-disaster-recovery-plan` (Appendix A, procedures by scenario); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-incident-response-plan` | LM-06.A | document:incident-response-plan | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-operating-procedure-template` | LM-06.A | document:operating-procedure-template | template `operating-procedure-template`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `recovery-records-for-incidents` | LM-06.B, LM-06.C, LM-06.D | person | `alerts.incidents_resolved` (partial, P2); Tasks module: Incident issues with recovery steps and resolved time, `verity.incidents.registered` NEW; person | P1 |
| `security-incident-register` | LM-06.B | person | Tasks module: Security incident register report, `verity.incidents.registered` NEW; `alerts.incidents_resolved` (partial, P2); NEED ticketing: Incident tickets record severity, owner, date found and date closed. (partial, P2); person | P1 |

Interviews no system replaces: LM-06.C.

### LM-07 Incident response plan

Decision: revise objectives. SOC 2: CC7.4 (full); P6.5 (partial). ISO 27001:2022: A.5.24 Incident response preparation (partial); A.5.26 Handling security incidents (partial); A.5.28 Preserving forensic evidence (partial).

The plan, the contact list and acknowledgements by role holders are Documents work (P1). The register is Tasks with a proposed incident template and the new verity.incidents.registered. That every incident was recorded, and handled as the plan says, stays with people: a register shows only what was entered.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `incident-response-plan` | LM-07.A, LM-07.E, LM-07.F | person | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-incident-response-plan` | LM-07.A, LM-07.C | document:incident-response-plan | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; `verity.policies.acknowledged` (partial, P1); person | P1 |
| `roles-and-contact-list` | LM-07.B | person | template `incident-response-plan` (Appendix A, Contact Information); Documents module: Policy register, `verity.policies.reviewed`; Vendors module: Vendor contacts of type security for critical vendors (support routes); NEED alerting: Responders in each in scope on call schedule have at least one working contact method recorded. (partial, P2); person | P1 |
| `incident-plan-acknowledgement-by-role-holders` (proposed) | LM-07.C | none (proposed) | Documents module: Acknowledgement campaign on the incident response plan targeted at the incident roles, `verity.policies.acknowledged`; person | P1 |
| `security-incident-register` | LM-07.D, LM-07.E, LM-07.G | person | Tasks module: Security incident register report, `verity.incidents.registered` NEW; `alerts.incidents_resolved` (partial, P2); NEED ticketing: Incident tickets record severity, owner, date found and date closed. (partial, P2); person | P1 |
| `evidence-handling-record-for-incidents` (proposed) | LM-07.F | none (proposed) | Tasks module: Attachments on incident issues with uploader and time; person | P1 |
| `review-and-re-approval-record-for` | LM-07.G | check:verity.policies.reviewed | `verity.policies.reviewed` (partial, P1); person | P1 |

Interviews no system replaces: LM-07.C, LM-07.E.

### LM-08 On-call rotation

Decision: keep. SOC 2: CC7.2 (partial); CC7.4 (partial). ISO 27001:2022: A.5.24 Incident response preparation (partial, proposed).

Cover for every day, escalation and missed pages are on call reads (PagerDuty, P2). Without an on call tool the schedule export stays with people. Reviewing missed pages (LM-08.D) is people's work.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `escalation-policy` | LM-08.A, LM-08.C | person | template `incident-response-plan` (Escalation and Internal Reporting); Documents module: Policy register, `verity.policies.reviewed`; NEED alerting: Each in scope service has an escalation policy naming the first responder, the escalation timeout and the next level, exported with the period it was in force. (partial, P2); person | P1 |
| `doc-incident-response-plan` | LM-08.A | document:incident-response-plan | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `on-call-schedule` | LM-08.B, LM-08.C, LM-08.D | person | NEED alerting: Every day of the period is covered by a primary and a backup in each in scope schedule, with no gaps. (partial, P2); `alerts.security_routed` (partial, P2); `alerts.acknowledged_in_time` (partial, P2); person | P2 |

Interviews no system replaces: LM-08.D.

### LM-09 Security anomaly alerting

Decision: keep. SOC 2: CC7.2 (full). ISO 27001:2022: A.8.16 Watching systems for unusual behavior (partial).

Monitors for the priority conditions (observability.anomaly_monitors) and routing (alerts.security_routed) arrive in P2. The quarterly tuning review is people's work; a recurring Verity task shows it was done.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `alerting-standard` | LM-09.A, LM-09.B, LM-09.C | person | template `infrastructure-security-standard` (section 5, Logs, Detection and Alerts); Documents module: Policy register, `verity.policies.reviewed`; `observability.anomaly_monitors` (partial, P2); person | P1 |
| `doc-infrastructure-security-standard` | LM-09.A | document:infrastructure-security-standard | template `infrastructure-security-standard`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `review-of-alert-tuning` | LM-09.B, LM-09.C, LM-09.D | person | `observability.anomaly_monitors` (partial, P2); NEED observability: Alert volume and alerts closed without action are counted per monitor for the quarter. (partial, P2); NEED alerting: Alerts per service with acknowledgement and resolution are listed, so alerts nobody acted on show up. (partial, P2); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |

### LM-10 Incident tabletop exercise

Decision: keep. SOC 2: CC7.4 (partial). ISO 27001:2022: A.5.24 Incident response preparation (partial).

The exercise is people's work. Tasks holds the actions and shows they closed on time; a recurring task shows the exercise was held each year.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-incident-response-plan` | LM-10.A | document:incident-response-plan | template `incident-response-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `tabletop-exercise-plan-and-report` | LM-10.B, LM-10.C, LM-10.D | person | `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |
| `roles-and-contact-list` | LM-10.C | person | template `incident-response-plan` (Appendix A, Contact Information); Documents module: Policy register, `verity.policies.reviewed`; Vendors module: Vendor contacts of type security for critical vendors (support routes); NEED alerting: Responders in each in scope on call schedule have at least one working contact method recorded. (partial, P2); person | P1 |
| `actions-from-the-exercise` | LM-10.D | person | Tasks module: Remediation tasks linked to LM-10, `verity.tasks.capa_on_time` NEW; `verity.tasks.remediation_in_sla` (partial, P1); `tickets.remediation_tracked` (partial, P2); person | P1 |

Interviews no system replaces: LM-10.C.

### LM-11 Vulnerability management program

Decision: split. SOC 2: CC7.1 (full to partial, proposed). ISO 27001:2022: A.8.8 Finding and fixing technical weaknesses (full to partial, proposed).

The Vulnerabilities module already evaluates current SLA state (verity.vulns.within_sla). New module checks add triage time, period SLA performance and acceptance validity. Scanners (Tenable, Rapid7, Qualys) are P3, so findings arrive by import until then. Scan coverage moves to LM-13.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `vulnerability-management-policy-with-timeframes` | LM-11.A, LM-11.E | person | template `operations-security-policy` (Finding and fixing vulnerabilities); Documents module: Policy register, `verity.policies.reviewed`; Vulnerabilities module: SLA settings per severity (vuln_sla_policies); person | P1 |
| `doc-operations-security-policy` | LM-11.A | document:operations-security-policy | template `operations-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `vulnerability-register-with-remediation-and-accepted` | LM-11.C, LM-11.D, LM-11.E | check:verity.vulns.within_sla | `verity.vulns.within_sla` (partial, P1); `verity.vulns.closed_within_sla` (partial, P1, NEW); `verity.vulns.acceptances_approved` (partial, P1, NEW); Vulnerabilities module: Vulnerability SLA report; person | P1 |
| `scan-reports` | LM-11.C | person | Vulnerabilities module: Imported scan reports and the findings they created; `scanner.scans_current` (partial, P3); person | P1 |
| `penetration-test-report-from-an-independent` | LM-11.C | person | Vulnerabilities module: Reports of type penetration test, uploaded and parsed, with their findings; person | P1 |

### LM-12 Threat source monitoring

Decision: keep. SOC 2: CC7.1 (partial, proposed). ISO 27001:2022: A.5.7 Tracking emerging threats (full).

Verity already reads the known exploited catalogue and EPSS for findings, which is one threat source, and the new check shows exploited findings were assessed the same day. Reading other sources and judging relevance is people's work; a recurring Verity task shows the weekly routine ran.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `threat-sources-and-the-routine-for` | LM-12.A, LM-12.B, LM-12.E | person | template `operations-security-policy` (Tracking new threats); Documents module: Policy register, `verity.policies.reviewed`; Vulnerabilities module: Known exploited catalogue and EPSS enrichment status (last successful refresh); person | P1 |
| `doc-operations-security-policy` | LM-12.A | document:operations-security-policy | template `operations-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `log-of-threats-reviewed-and-actions` | LM-12.B, LM-12.D | person | `verity.tasks.recurring_review_on_time` (partial, P1, NEW); Vulnerabilities module: Known exploited and EPSS enrichment applied to findings in the period; person | P1 |
| `actively-exploited-vulnerabilities-and-time-taken` | LM-12.C | person | Vulnerabilities module: Vulnerability SLA report filtered to known exploited, `verity.vulns.kev_triaged_same_day` NEW; `verity.vulns.kev_owned` (partial, P1); NEED vulnerability_scanner: Findings on known exploited vulnerabilities are reported with first seen time for every scanned asset. (partial, P3); person | P1 |
| `vulnerability-register-with-remediation-and-accepted` | LM-12.C | check:verity.vulns.within_sla | `verity.vulns.within_sla` (partial, P1); `verity.vulns.closed_within_sla` (partial, P1, NEW); `verity.vulns.acceptances_approved` (partial, P1, NEW); Vulnerabilities module: Vulnerability SLA report; person | P1 |
| `risk-register-with-owners-ratings-and` | LM-12.D | check:verity.risks.treated | `verity.risks.treated` (partial, P1); Risks module: Risk register report; person | P1 |
| `management-review-agenda-and-minutes` | LM-12.D | check:verity.management_review.in_12_months, person | `verity.management_review.in_12_months` (partial, P1); person | P1 |

Interviews no system replaces: LM-12.D.

### LM-13 Vulnerability scanning coverage

Decision: proposed successor of LM-11. SOC 2: CC7.1 (partial, proposed). ISO 27001:2022: A.8.8 Finding and fixing technical weaknesses (partial, proposed).

Proposed. Scan coverage compares scan targets with the asset inventory. Today imported reports record findings but not the targets scanned, so a clean asset leaves no trace; scanner connectors (P3) and a target list on imports close that.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `vulnerability-management-policy-with-timeframes` | LM-13.A | person | template `operations-security-policy` (Finding and fixing vulnerabilities); Documents module: Policy register, `verity.policies.reviewed`; Vulnerabilities module: SLA settings per severity (vuln_sla_policies); person | P1 |
| `doc-operations-security-policy` | LM-13.A | document:operations-security-policy | template `operations-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `scan-reports` | LM-13.B, LM-13.C | person | `scanner.scans_current` (partial, P3); Vulnerabilities module: Imported scan reports with tool and scan date, `verity.vulns.assets_scanned` NEW; NEED cloud_infrastructure: The cloud provider's own vulnerability scanning covers every running instance and image in production accounts. (partial, P2); person | P1 |
| `asset-inventory` | LM-13.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, in service infrastructure, cloud and internet facing assets; `verity.vulns.assets_scanned` (partial, P1, NEW); `scanner.scans_current` (partial, P3); person | P1 |
| `log-of-control-deficiencies-with-owner` | LM-13.C | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |

### BC-01 Automated, monitored backups

Decision: revise objectives. SOC 2: A1.2 (partial); CC9.1 (partial); PI1.5 (partial). ISO 27001:2022: A.5.29 Keeping safeguards running through outages and crises (partial); A.5.30 Technology recovery readiness (partial); A.5.33 Keeping records safe (partial); A.8.13 Backups that can be restored (partial).

Backup settings and job history are cloud reads (P2). Restore rights come from cloud IAM (P2). Rebuild materials are partly in version control (running branch protection on infrastructure code repositories).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `backup-policy-covering-scope-frequency-and` | BC-01.A, BC-01.D | person | template `operations-security-policy` (Backups and restore tests); template `business-continuity-and-disaster-recovery-plan` (Appendix B, RTOs and RPOs); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-operations-security-policy` | BC-01.A | document:operations-security-policy | template `operations-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-business-continuity-and-disaster-recovery-plan` | BC-01.A | document:business-continuity-and-disaster-recovery-plan | template `business-continuity-and-disaster-recovery-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `asset-inventory` | BC-01.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to production data assets; `cloud.backups_enabled` (partial, P2); NEED cloud_infrastructure: Every production data store found in connected accounts matches a data asset in the register. (partial, P2); person | P1 |
| `backup-failure-alerts-and-follow-up` | BC-01.B, BC-01.C | person | `cloud.backups_enabled` (partial, P2); NEED cloud_infrastructure: Backup jobs for every production data store succeeded within the expected window across the period; failed or missed jobs are listed with times. (partial, P2); NEED observability: A monitor alerts on a failed or late backup job. (partial, P2); NEED ticketing: Each failed backup has a ticket with cause, fix and the date of the next good backup. (partial, P2); Tasks module: Issues for backup failures, `verity.tasks.remediation_in_sla`; person | P1 |
| `backup-storage-settings-export` (proposed) | BC-01.D | none (proposed) | `cloud.encryption_at_rest` (partial, P2); NEED cloud_infrastructure: Each backup store has a copy in another region or account and an immutability or lock setting. (partial, P2); person | P2 |
| `list-of-privileged-accounts-with-approval` | BC-01.E | person | NEED cloud_infrastructure: Principals with restore or delete rights on backup vaults and snapshots are listed with their roles. (partial, P2); `cloud.least_privilege` (partial, P2); person | P2 |
| `rebuild-materials-inventory` (proposed) | BC-01.F | none (proposed) | `vcs.default_branch_protected` (partial, P1); `cloud.storage_versioned` (partial, P2); person | P1 |

Interviews no system replaces: BC-01.D.

### BC-02 Backup restore testing

Decision: keep. SOC 2: A1.3 (full). ISO 27001:2022: A.5.30 Technology recovery readiness (partial); A.8.13 Backups that can be restored (partial).

A restore test is people's work. The cloud can show that a restore ran and how long it took (P2); a recurring Verity task shows the yearly test happened, and corrective actions are tracked. Whether the restored data was complete and intact is a person's check.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-business-continuity-and-disaster-recovery-plan` | BC-02.A, BC-02.D | document:business-continuity-and-disaster-recovery-plan | template `business-continuity-and-disaster-recovery-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `backup-policy-covering-scope-frequency-and` | BC-02.A | person | template `operations-security-policy` (Backups and restore tests); template `business-continuity-and-disaster-recovery-plan` (Appendix B, RTOs and RPOs); Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `restore-test-plan-and-results` | BC-02.B, BC-02.C, BC-02.E | person | `verity.tasks.recurring_review_on_time` (partial, P1, NEW); NEED cloud_infrastructure: A restore from backup into a non production account or isolated network ran in the last 12 months. (partial, P2); `verity.tasks.capa_on_time` (partial, P1, NEW); person | P1 |
| `measured-recovery-time-against-the-target` | BC-02.D | person | NEED cloud_infrastructure: Restore and failover events during a test window are recorded with start and end times. (partial, P2); person | P2 |
| `log-of-control-deficiencies-with-owner` | BC-02.E | check:verity.tasks.remediation_in_sla | `verity.tasks.remediation_in_sla` (partial, P1); Tasks module: Remediation tasks report filtered to the control; `tickets.remediation_tracked` (partial, P2); person | P1 |

Interviews no system replaces: BC-02.C.

### BC-03 Business continuity / disaster recovery plan

Decision: split. SOC 2: CC9.1 (partial); A1.2 (partial). ISO 27001:2022: A.5.29 Keeping safeguards running through outages and crises (partial); A.5.30 Technology recovery readiness (partial); A.5.37 Procedures for running systems (partial); A.8.14 Failover for critical systems (full, moves out).

The plan is a document (P1). The exercise and its comparison with targets are people's work, scheduled and tracked in Tasks. Redundancy and failover move to BC-09.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `business-continuity-and-disaster-recovery-plan` | BC-03.A, BC-03.B, BC-03.E | person | template `business-continuity-and-disaster-recovery-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-business-continuity-and-disaster-recovery-plan` | BC-03.A, BC-03.B | document:business-continuity-and-disaster-recovery-plan | template `business-continuity-and-disaster-recovery-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-business-impact-analysis` | BC-03.A | document:business-impact-analysis | template `business-impact-analysis`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `exercise-or-test-report` | BC-03.C, BC-03.E | person | `verity.tasks.recurring_review_on_time` (partial, P1, NEW); `verity.tasks.capa_on_time` (partial, P1, NEW); person | P1 |

### BC-04 Capacity management

Decision: keep. SOC 2: A1.1 (full). ISO 27001:2022: A.8.6 Keeping resources ahead of demand (full).

Capacity alarms and trends are observability and cloud reads (P2). The quarterly review and the growth forecast are people's work; a recurring task shows the review was done.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-operations-security-policy` | BC-04.A | document:operations-security-policy | template `operations-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `alerting-standard` | BC-04.A, BC-04.C | person | template `infrastructure-security-standard` (section 5, Logs, Detection and Alerts); template `operations-security-policy` (Keeping enough capacity); Documents module: Policy register, `verity.policies.reviewed`; `cloud.capacity_alarms` (partial, P2); person | P1 |
| `capacity-review` | BC-04.B, BC-04.C, BC-04.D | person | `observability.capacity_trends` (partial, P2); `cloud.capacity_alarms` (partial, P2); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); NEED observability: No monitored resource reached its limit in the period without a threshold alert firing first. (partial, P2); person | P1 |
| `capacity-actions-that-were-taken` | BC-04.D | person | NEED cloud_infrastructure: Scaling, instance size and quota changes in the period are listed with time and actor from the cloud change history. (partial, P2); NEED ticketing: Capacity actions are tickets linked to the review that raised them. (partial, P2); Tasks module: Tasks raised from the capacity review, `verity.tasks.remediation_in_sla`; person | P1 |

Interviews no system replaces: BC-04.C.

### BC-05 Shadow-IT detection

Decision: keep. SOC 2: CC9.2 (partial). ISO 27001:2022: A.5.23 Cloud service security rules (partial).

Discovered applications have a home in the Vendors module today, entered by hand, and gain a source with an identity provider connector (idp.connected_apps_known, P2). Expense and card review has no source in the catalogue.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-cloud-services-security-policy` | BC-05.A | document:cloud-services-security-policy | template `cloud-services-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-acceptable-use-policy` | BC-05.A | document:acceptable-use-policy | template `acceptable-use-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `review-of-newly-discovered-applications` | BC-05.B, BC-05.C, BC-05.D | person | `idp.connected_apps_known` (partial, P2); Vendors module: Discovered applications with first seen and disposition, `verity.vendors.discovered_apps_triaged` NEW; `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |
| `decision-to-approve-or-remove-each` | BC-05.C, BC-05.D | person | Vendors module: Discovered applications with disposition, `verity.vendors.discovered_apps_triaged` NEW; `idp.connected_apps_known` (partial, P2); person | P1 |
| `vendor-inventory-with-owner-data-and` | BC-05.D | check:verity.vendors.owner_and_tier | `verity.vendors.owner_and_tier` (partial, P1); `verity.vendors.discovered_apps_triaged` (partial, P1, NEW); person | P1 |

Interviews no system replaces: BC-05.B.

### BC-06 Subprocessor management

Decision: keep. SOC 2: CC9.2 (partial); P6.1 (partial); P6.4 (partial). ISO 27001:2022: A.5.21 Technology supply chain risk (partial); A.5.22 Ongoing supplier oversight (partial).

The vendor register knows which vendors hold personal data, where and for what. The new check compares the published list document with vendor changes. Customer notices before a new subprocessor is used stay with people.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `subprocessor-list-shared-with-customers` | BC-06.A, BC-06.B, BC-06.C, BC-06.D | person | Vendors module: Vendor register filtered to vendors that process customer personal data: service, data types, location, `verity.vendors.subprocessor_list_current` NEW; person | P1 |
| `doc-third-party-management-policy` | BC-06.A | document:third-party-management-policy | template `third-party-management-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `data-inventory-and-data-map` | BC-06.B | person | Assets module: Asset inventory filtered to data assets with classification and regulated data, `verity.assets.classified`; Vendors module: Vendor register: data types, personal data and location; person | P1 |
| `vendor-inventory-with-owner-data-and` | BC-06.B | check:verity.vendors.owner_and_tier | `verity.vendors.subprocessor_list_current` (partial, P1, NEW); Vendors module: Vendor register report: personal data, data types, location; person | P1 |
| `notices-to-customers-of-subprocessor-changes` | BC-06.C, BC-06.D | person | person | people-only |

Interviews no system replaces: BC-06.C.

### BC-07 Vendor inventory

Decision: revise objectives. SOC 2: CC9.2 (partial). ISO 27001:2022: A.5.19 Managing supplier security risk (partial); A.5.22 Ongoing supplier oversight (partial).

The Vendors module holds the register and verity.vendors.owner_and_tier runs today. Completeness against payments has no source; identity provider apps (P2) and third party assets help. Offboarding records exist in the module.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-third-party-management-policy` | BC-07.A | document:third-party-management-policy | template `third-party-management-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `vendor-inventory-with-owner-data-and` | BC-07.B, BC-07.C, BC-07.D | check:verity.vendors.owner_and_tier | `verity.vendors.owner_and_tier` (partial, P1); Vendors module: Vendor register report with contract and renewal dates; `idp.connected_apps_known` (partial, P2); `verity.assets.third_party_in_vendor_register` (partial, P1, NEW); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |
| `asset-inventory` | BC-07.C | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to third party assets; `verity.assets.third_party_in_vendor_register` (partial, P1, NEW); person | P1 |
| `vendor-offboarding-records` (proposed) | BC-07.E | none (proposed) | Vendors module: Offboarding records, `verity.vendors.offboarding_complete` NEW; `idp.connected_apps_known` (partial, P2); person | P1 |

Interviews no system replaces: BC-07.C.

### BC-08 Vendor security due diligence

Decision: split. SOC 2: CC9.2 (full); P6.4 (partial). ISO 27001:2022: A.5.19 Managing supplier security risk (partial); A.5.20 Security terms in supplier contracts (partial); A.5.21 Technology supply chain risk (partial); A.5.22 Ongoing supplier oversight (partial); A.5.23 Cloud service security rules (partial); A.8.21 Checking what network providers deliver (partial); A.8.26 Stating security needs before building or buying (partial); A.8.30 Oversight of contracted developers (partial).

The Vendors module holds tiering, assessments, assurance report reviews, contracts, findings and service levels. New module checks evaluate each. Reading an assurance report well is a judgement no system makes.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-third-party-management-policy` | BC-08.A | document:third-party-management-policy | template `third-party-management-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-cloud-services-security-policy` | BC-08.A | document:cloud-services-security-policy | template `cloud-services-security-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `vendor-inventory-with-owner-data-and` | BC-08.B | check:verity.vendors.owner_and_tier | `verity.vendors.owner_and_tier` (partial, P1); Vendors module: Tiering assessments per engagement; person | P1 |
| `asset-inventory` | BC-08.B | check:verity.assets.owner_assigned | Assets module: Asset inventory report, filtered to third party assets; `verity.assets.third_party_in_vendor_register` (partial, P1, NEW); person | P1 |
| `security-assessment-for-each-critical-vendor` | BC-08.C, BC-08.F | check:verity.vendors.assessed_in_cadence | `verity.vendors.assessed_in_cadence` (partial, P1); `verity.vendors.findings_in_sla` (partial, P1, NEW); Vendors module: Vendor register report with assessments and findings; person | P1 |
| `vendor-assurance-reports-that-were-reviewed` | BC-08.D | person | Vendors module: SOC report reviews with period, opinion, customer controls and subservice organisations, `verity.vendors.assurance_report_reviewed` NEW; person | P1 |
| `security-terms-agreed-in-each-vendor` | BC-08.E | person | Vendors module: Contracts with security clauses, `verity.vendors.security_terms_on_file` NEW; person | P1 |
| `risk-register-with-owners-ratings-and` | BC-08.F | check:verity.risks.treated | `verity.risks.treated` (partial, P1); Risks module: Risk register report; person | P1 |
| `vendor-service-level-review` (proposed) | BC-08.G | none (proposed) | Vendors module: Contract service levels and monitoring signals, `verity.vendors.service_levels_measured` NEW; person | P1 |

Interviews no system replaces: BC-08.D.

### BC-09 Redundancy and failover of critical services

Decision: proposed successor of BC-03. SOC 2: A1.2 (partial, proposed). ISO 27001:2022: A.8.14 Failover for critical systems (full, proposed); A.5.30 Technology recovery readiness (partial, proposed).

Proposed. Zone, standby and region settings are cloud reads (P2). The failover test is people's work, with failover events visible in the cloud history.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `business-continuity-and-disaster-recovery-plan` | BC-09.A | person | template `business-continuity-and-disaster-recovery-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `doc-business-continuity-and-disaster-recovery-plan` | BC-09.A | document:business-continuity-and-disaster-recovery-plan | template `business-continuity-and-disaster-recovery-plan`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `redundancy-configuration-export` (proposed) | BC-09.B | none (proposed) | NEED cloud_infrastructure: Each database, load balancer and compute group tagged as critical runs across more than one zone or has a standby. (partial, P2); person | P2 |
| `exercise-or-test-report` | BC-09.C, BC-09.D | person | NEED cloud_infrastructure: Restore and failover events during a test window are recorded with start and end times. (partial, P2); `verity.tasks.recurring_review_on_time` (partial, P1, NEW); person | P1 |
| `measured-recovery-time-against-the-target` | BC-09.C | person | NEED cloud_infrastructure: Restore and failover events during a test window are recorded with start and end times. (partial, P2); person | P2 |

Interviews no system replaces: BC-09.D.

### BC-10 Oversight of outsourced development

Decision: proposed successor of BC-08. SOC 2: CC9.2 (partial, proposed). ISO 27001:2022: A.8.30 Oversight of contracted developers (partial, proposed).

Proposed. GitHub shows supplier changes were reviewed by staff (P1 extension of the review data). Acceptance testing and escrow stay with people.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-third-party-management-policy` | BC-10.A | document:third-party-management-policy | template `third-party-management-policy`; Documents module: Policy register, `verity.policies.reviewed`; person | P1 |
| `security-terms-agreed-in-each-vendor` | BC-10.A | person | Vendors module: Contracts with security clauses, `verity.vendors.security_terms_on_file` NEW; person | P1 |
| `acceptance-test-of-supplier-deliveries` (proposed) | BC-10.B | none (proposed) | NEED version_control: Changes authored by outside collaborators or supplier accounts were approved by an organisation member before merge. (partial, P1); person | P1 |
| `sample-of-reviewed-changes` | BC-10.B | check:vcs.merged_changes_reviewed, person | `vcs.merged_changes_reviewed` (partial, P1); person | P1 |
| `escrow-verification-record` (proposed) | BC-10.C | none (proposed) | person | people-only |

## What no system can prove

Besides every interview listed above, these objectives rest on a person's judgement, a signature or a record no catalogued system holds. Connectors and module checks can show that the record exists and is on time, not that it is right.

| Objectives | What stays with people |
|---|---|
| SD-01.E | Whether a change fitted a standard change approved in advance. |
| SD-02.E | Whether the suite holds tests that really check processing accuracy. |
| SD-04.C | Whether the person who authorised an emergency was allowed to. |
| SD-04.E | The management review of the emergency rate. |
| SD-07.D | That retried stages neither duplicate nor lose records. |
| SD-09.B, SD-09.C | That the specification matches production and tests trace to it. |
| SD-10.C | That security was considered well in a design review. |
| SD-10.D | Secure coding training completion (no training source in the catalogue). |
| SD-11.D | That a leaked credential was not used before rotation. |
| SD-12.E | That lower environments hold only masked or synthetic data. |
| SD-16.C | That an output reached only its intended recipient. |
| SD-18.C | Whether a licence fits how the product is used or sold. |
| LM-03.D | That the cause of recurring drift was fixed. |
| LM-04.D | Consistency of triage decisions. |
| LM-05.D, LM-05.E | Recurring themes and whether a corrective action worked. |
| LM-06.C, LM-06.D | That a system was clean before restore, and that recovery was complete. |
| LM-07.D, LM-07.E | That every incident was entered in the register and handled as the plan says. |
| LM-07.F | That evidence was captured without changing it. |
| LM-10.B, LM-10.C | That the scenario was realistic and the right people took part. |
| LM-12.B, LM-12.D, LM-12.E | Relevance of threat items, feeding them into risks, and the choice of sources. |
| BC-02.C | That restored data was complete and intact. |
| BC-03.B | That each workaround keeps access control, logging and encryption in place. |
| BC-04.B | The growth forecast. |
| BC-06.C | That customers were told before a new subprocessor was used. |
| BC-08.D | That an assurance report was read with care. |
| BC-10.C | That an escrow deposit is complete. |

People-only artifacts in this file: `escrow-verification-record`, `notices-to-customers-of-subprocessor-changes`, `secure-coding-training-completion-for-developers`.

## Content problems found

- Four person only document artifacts duplicate a doc- artifact on the same objective: change-management-policy (SD-01.A), secure-development-lifecycle-policy (SD-10.A), incident-response-plan (LM-07.A) and business-continuity-and-disaster-recovery-plan (BC-03.A, B). A workspace is asked for the same document twice, once by template and once by upload. Give each the template source or retire it.
- 26 document artifacts in these families are person only although a template or a template section exists (testing standard, peer review standard, input validation standard, triage standard, emergency change procedure, deployment procedure, logging standard, configuration baseline, recovery procedures and others). This file proposes the template source for each.
- No template exists for a vulnerability management policy, a backup policy, a subprocessor list or a postmortem. The dependency triage artifact says it lives in the vulnerability management policy, which does not exist as a template.
- Many artifacts name catalogued checks that have no implementation (tickets.changes_linked, ci.*, vcs.unreviewed_merges_recorded, vcs.code_scanning_enabled, alerts.*, scanner.scans_current, cloud.*, idp.*). In practice they are person only today; the control page must say provide it for now (EC-6).
- capabilities.json lists GitHub under CI and CD as planned for Phase 2 although the GitHub connector exists. Deployments, workflow runs and check results need new read permissions (unverified here), so ci.* checks are P2 even on GitHub.
- Tasks has no incident marker and no notice decision field, yet the security incident register (LM-07.D) is meant to live there. A shipped Security incident task template with a structured notice decision, or the Phase 3.1 Incidents module, is needed before verity.incidents.registered can run.
- Imported vulnerability scan reports record findings, not the targets scanned, so scan coverage (LM-11.B, now LM-13.B) cannot be shown from Verity: a clean asset leaves no trace.
- The Vulnerabilities module has remediation days per severity but no triage time, so SD-03.D and the new triage check have no parameter to test against.
- vendor_subprocessors is each vendor's own subprocessor list (fourth parties), not the company's published subprocessor list. Vendors have no flag for customer data as opposed to staff data, and Verity records no customer notices.
- vendor_discovered_apps has no connector source until an identity provider connector ships, so BC-05 is manual in P1.
- BC-08.B repeated BC-07.C (register complete). Reworded to tiering in this proposal.
- Onboarding lists SD-05 as on demand when Processing Integrity is elected, but SD-05 maps ISO27001:A.8.26 and A.8.28, which apply to any ISO workspace.
- LM-08 has no ISO 27001 mapping, so an ISO only workspace would not see on call cover; LM-12 sits in the ISO pack, so SOC 2 workspaces cannot adopt it (CL-10).
- vcs.code_scanning_enabled maps only to SD-05, but static analysis is what ISO27001:A.8.28 and A.8.29 rely on through SD-02 and SD-10, and no objective tested that it ran (SD-02.F added).
- docs/architecture/check-catalogue.md says 81 tests and Appendix C of control-framework-requirements.md says Verity tests are planned; checks.json has 93 checks and the 30 verity checks run. The generated catalogue needs regenerating.
- verity.tasks.remediation_in_sla is used as a source on LM-05, LM-10, BC-02 and BC-03 artifacts but maps only to GOV-08, so its evidence never attaches to those controls (see the check mapping table).
