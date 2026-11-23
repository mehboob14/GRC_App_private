# Continuous compliance: control design and delivery plan

Reviewed: 2026-10-08. Status: research and proposed design; implementation is not authorised. No code, content packs, mappings, configuration or migrations were changed for this plan.

Goal: deliver an auditable SOC 2 preparation and continuous control monitoring product, with reusable controls and evidence for ISO/IEC 27001 and subsequent frameworks. Each release must complete useful control workflows, including their manual and review paths. A larger connector catalogue alone is not the release outcome.

This builds on the [evidence sufficiency and gap register](control-evidence-sufficiency.md). Keep that file as the maintained list of proof gaps and customer workarounds. Refer to [control framework requirements](control-framework-requirements.md), the [common-control proposal](../../openspec/changes/common-control-framework/design.md), [mapping review](mapping-review-2026-10.md), and the generated [check catalogue](../architecture/check-catalogue.md) rather than duplicating all control/check mappings here.

## 1. Research findings and their application

| Verified public pattern | Proposed application in Verity |
|---|---|
| Drata decomposes broad framework requirements into reusable operational controls. Its DCF catalogue is customisable, versioned over time, and not exhaustive for every organisation. [DCF relationships](https://help.drata.com/en/articles/11095971-the-drata-control-framework-requirement-relationship). | Keep Verity controls as the unit of operation. Assess granularity against the customer's actual activities, scope and risks. |
| Vanta's common controls are currently documented as a Public Preview internal reporting layer grouping framework controls by shared objective. [Common controls](https://help.vanta.com/en/articles/16894224-managing-common-controls). | Do not equate this reporting hierarchy with audit-facing control evaluations. An additional grouping layer is optional; the existing Verity architecture already supports shared controls. |
| Vanta supports custom tests joining two resource types, including different integrations. [Custom tests](https://help.vanta.com/en/articles/11345522-creating-custom-tests). | A check may need HR and IdP facts, or inventory and device facts. Specify authoritative sources and joins, including unmatched and ambiguous records. Do not assume this proves arbitrary cross-system checks already exist in Verity. |
| Drata's SOC 2 evidence examples distinguish repository configuration, production deployment access, change operation and emergency handling; backup configuration, failure response and restoration are also distinct. Change proof can combine tickets, PR reviews and CI/CD activity. [Evidence examples](https://help.drata.com/en/articles/9421165-example-evidence-for-not-monitored-controls-soc-2). | Split by meaningful operating objective, owner, population and cadence. Several connectors can support one control, and one observation can support several controls. |
| Vanta separates resource access scope, framework scope and test applicability. [Scope concepts](https://help.vanta.com/en/articles/15878326-determining-resource-access-for-your-integrations). | Record business/engagement scope, source visibility, per-control population and justified applicability separately. |
| Drata gates controls with optional required approval; mapped evidence changes can require reapproval. [Required approvals](https://help.drata.com/en/articles/13380564-manage-required-approval-and-control-readiness). | Pin review to a defined evidence/control revision. Require independent review where the adopted control or risk policy needs it; do not assume either vendor universally mandates segregation. |
| Vanta documents finding deadlines and test rollout dates. [SLAs](https://help.vanta.com/en/articles/11346006-managing-slas), [upcoming tests](https://help.vanta.com/en/articles/11345481-what-is-an-upcoming-test). | Preserve applicable policy/test versions and deadlines. Preview changed evaluators, and retain the result under the old rule. |

Both vendors expose useful patterns, not public proof that every mapped control is audit-sufficient. Vanta expressly separates control status from auditor assessment; Drata warns that a policy-only ready control can still lack operating evidence. Those limitations are documented in the [sufficiency register](control-evidence-sufficiency.md#4-how-vanta-and-drata-inform-this-plan).

Two patterns should be handled more explicitly in Verity. Missing a required source must remain a missing/unknown obligation, even if no technical test can run; a disconnected integration must not improve readiness. Complete operational history must remain available even when an auditor export is scoped or summarised. [Vanta test-count behaviour](https://help.vanta.com/en/articles/11346086-why-does-my-test-count-change), [auditor visibility](https://help.vanta.com/en/articles/11345526-auditor-visibility-into-test-data).

## 2. Standards and product boundaries

SOC 2 criteria describe expectations against which organisational controls are evaluated; points of focus assist interpretation and are not a mandatory one-test-per-point checklist. Type II involves operation over a period; current configuration cannot establish historical effectiveness. Verity must preserve system scope, commitments, selected Trust Services Categories, relevant service providers and the engagement's date/period. Management's assertions and the auditor's conclusions remain distinct from machine evaluation. [AICPA TSC resource](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022), [public TSC introduction and engagement discussion](https://assets.ctfassets.net/rb9cdnjh59cm/72xv4p67HVXKp6CjWmjkPk/1cdbfa19f6307e2720396b66a6194dc9/trust-services-criteria-updated-copyright.pdf).

For SOC 2, start with the relevant common criteria and explicitly selected additional categories. Do not count all 61 seeded requirements as mandatory for every engagement. Additional Availability, Confidentiality, Processing Integrity or Privacy needs must be reviewed against the agreed scope. Existing `criteria_in_scope` and framework-version models are useful foundations.

ISO/IEC 27001 requires an information security management system as well as suitable controls. Target the 2022 edition and applicable amendments, including Amendment 1:2024. Adding Annex A labels to SOC 2 controls will not implement the management system. [ISO standard and amendments](https://www.iso.org/standard/27001).

Control mappings are reviewed relationships, not automatic compliance equivalence. Retain rationale, source/version, conditions and residual coverage gaps. Two partial links cannot simply be added as percentages to prove a requirement complete. NIST's mapping approach is a useful reference for describing such relationships. [NIST IR 8477](https://csrc.nist.gov/pubs/ir/8477/final).

No public vendor control catalogue or copyrighted framework text should be copied into a new Verity pack merely because it is accessible. Write Verity-owned control descriptions and obtain the required source access/content permission for the qualified review. Existing attribution and framework-content questions remain release gates.

## 3. Current baseline and design gaps

Parsed from the working-tree seed files on the review date: **116 controls, 61 SOC 2 requirements, 167 requirement mappings and 81 checks**. Seven checks have implementations, all GitHub. Eighteen `verity.*` module checks are planned metadata. Runtime providers contain GitHub only. Counts describe library/implementation coverage, not compliant controls or deployed tenant results.

| Library domain | Controls | Controls with any catalogued check | Controls with an implemented check |
|---|---:|---:|---:|
| Business continuity and third-party management | 8 | 5 | 0 |
| Communications and collaboration | 5 | 1 | 0 |
| Data management and privacy | 17 | 4 | 0 |
| Endpoint security | 6 | 6 | 0 |
| Governance, risk and compliance | 22 | 10 | 0 |
| HR and personnel | 8 | 2 | 0 |
| Identity and access | 12 | 12 | 1 |
| Infrastructure and network | 11 | 11 | 0 |
| Logging, monitoring and incidents | 11 | 7 | 1 |
| Physical and environmental | 2 | 0 | 0 |
| Secure development and code | 14 | 13 | 5 |

Source: [controls](../../backend/src/verity/seed/content/soc2/control_templates.json), [checks](../../backend/src/verity/seed/content/automation/checks.json), [capabilities](../../backend/src/verity/seed/content/automation/capabilities.json), [mappings](../../backend/src/verity/seed/content/soc2/template_requirements.json), [runtime providers](../../backend/src/verity/modules/connectors/models.py). The working tree has pre-existing uncommitted changes; live deployment was not verified.

Reconcile these issues before converting the proposed evaluations into readiness:

1. **Mapping meaning:** earlier common-control design text defines `full` as meeting a requirement alone; later design text and `TemplateRequirementMap` describe a primary route to its central obligation. These meanings are different. Agree the actual coverage claim and separately identify primary/supporting roles; do not reinterpret existing rows silently.
2. **Readiness:** currently one current non-rejected item plus implementation and no blocking automation can qualify a control. The required-evidence definition must become evaluated rather than merely displayed.
3. **Multi-source checks:** catalogued examples such as `people.leavers_deprovisioned` and `tickets.changes_linked` name two capabilities but have no implementations or full correlation workflow.
4. **Module execution:** planned platform tests need service-based evaluation and result provenance. `check_runs.connection_id` is required today; decide how module-origin runs fit through a reviewed model change, without fabricating external connections.
5. **Simultaneous engagements:** the current engagement has `UNIQUE(tenant_id)`. SOC 2 and ISO assessments with separate scope, versions and periods require an approved evolution; a second pack alone is insufficient.
6. **Historical detail:** current review sampling, source detection times, exception expiry and evidence-version binding have gaps recorded as CE-01 to CE-14. Resolve them before period effectiveness claims.

## 4. How to retain, refine, split or add controls

Write each operational control as: responsible actor; action; protected population; trigger/frequency; approved deadline where relevant; required retained records; authority reviewing the outcome. These choices are customer/context dependent. A daily collection interval or a 30-day SLA is not automatically a universal SOC 2/ISO requirement.

An evidence obligation sits below the control and states what must be proven. Tests evaluate particular predicates; connectors supply facts. A policy approval, configuration observation, activity history and reviewer decision can be different obligations for one control.

| Decision | Use when | Verity examples |
|---|---|---|
| Retain; add evaluated obligations | One coherent objective, with several complementary forms of proof. | IAM-03 MFA across relevant identity populations; SD-06 peer review configuration and actual reviews. |
| Refine wording or conditional applicability | Guidance promises more than the control statement/evidence model, or some systems are not relevant. | SD-03 dependency versus container scope, SBOM/build-gating promises; reconcile IAM-03 “no standing exclusions” with approved-exception evidence. |
| Split after review | Different activities need independent ownership, cadence, applicability or remediation conclusions. | LM-11 discovery coverage versus triage/remediation may justify focused controls if obligations within LM-11 cannot support the actual operating responsibilities. |
| Add a new control | A necessary risk/requirement obligation has no suitable existing control after gap review. | ISO-specific ISMS scope or SoA governance where existing GOV controls cannot meet the needed objective. |
| Deprecate or consolidate with migration | Two controls actually duplicate the same activity and intent. | Review HR-05/IAM-12 overlap while preserving broader HR offboarding and distinct access revocation; do not merge from names alone. |

The change-management library already separates SD-01 authorisation, SD-06 review, SD-02 testing, SD-13 deployment, SD-14 traceability, SD-04 emergency handling and SD-12 environment separation. Preserve this useful structure. Likewise BC-01 backup operation and BC-02 restoration testing answer different questions.

Do not mechanically turn every sentence of implementation guidance into a mandatory obligation. Review the adopted control statement, system commitments, risk treatment and selected requirement first. If guidance is advisory, label it accordingly; if the control promises it, define its evidence and evaluation.

No new control codes are assigned by this plan. A split needs a reviewed mapping diff, stable successor identities, an effective date and a tenant adoption proposal. Preserve the original records, evidence, ownership, exceptions, histories and old engagement conclusions. Do not copy an original green result or risk acceptance to every successor. Let users review changes to their adopted wording and mappings.

## 5. Reusable full control loop

| Stage | Required output and gate |
|---|---|
| 1. Define | Versioned objective, owner, scope, evidence obligations, policy parameters, mapping rationale and reviewer. Unreviewed content is a draft. |
| 2. Establish population | Reconcile expected business systems/resources against source visibility. Record inclusions, exclusions, unmatched records and uncertainty. |
| 3. Collect | Read-only, attributable snapshots/events with source time, collection time, stable identity, permission/pagination/completeness information and retained proof. |
| 4. Correlate | Join records across sources using tenant-bound durable identifiers and explicit authoritative-source rules. Ambiguous/unmatched joins remain visible. |
| 5. Evaluate | Apply pinned predicates to the correct population and period. Distinguish unmet requirement, missing evidence, no events, late/stale data, and collection error. |
| 6. Act | Open/deduplicate an issue for a failing predicate or a coverage problem, assign owner and deadline, and link tasks. Preserve original findings and policy deadlines. |
| 7. Decide exceptions | Authorised, bounded decisions state remaining risk, compensating measures, expiry and affected objective. An acceptance does not mean repaired or retrospectively timely. |
| 8. Verify | Source-confirmed change, accepted retest or explicit human attestation with appropriate evidence. Task completion alone is insufficient. Reopen on recurrence. |
| 9. Review | Reuse valid approvals under the defined review policy; route new or material changes to the appropriate reviewer. Keep evidence authenticity distinct from favourable outcome. |
| 10. Report and repeat | Explain present posture and period performance separately; export the evidence chain and limitations. Reconcile on schedule, source events, scope changes and policy changes. |

Treat provider alternatives precisely: Okta can implement an IdP capability instead of Entra where it covers that population. If the tenant actually uses both, both populations need coverage. A connected GitHub account cannot substitute for in-scope GitLab repositories. No integration should claim coverage for systems it cannot observe.

Continuous operation requires trigger and frequency choices by obligation. Use events where reliable and reconciliation schedules to detect missed events, drift and visibility changes. Snapshots prove observed states at their times; they do not prove there were no violations between polls. Report observed coverage and unknown intervals; do not label a percentage of polling days as an auditor opinion.

Keep technical exposure separate from the control predicate. An open vulnerability still within its approved remediation SLA need not mean the timely-remediation control failed. A late fix can resolve exposure while preserving a historical control deviation. Do not let task due dates, an after-the-fact exception or a changed SLA rewrite that history.

## 6. Worked profiles for the first complete loops

These are draft operating plans, not approved audit programmes. Current criterion codes are from Verity's seed; exact wording, parameters, ownership and applicability need content and customer review. Proposed collectors below are unavailable unless explicitly stated otherwise.

### A. SD-06 peer code review, with the existing change controls

**Objective:** relevant code changes receive the adopted independent approval before merge. Current mapping: CC8.1. **Population:** business repositories and protected/release branches, not automatically each default branch; period changes, direct pushes and permitted emergency paths must be addressed by the applicable controls.

**Design and sources:** approved development procedure plus GitHub configuration/review records (partially implemented). Jira/request records, actual CI runs, deployment/environment events and cloud change records are proposed inputs to SD-01, SD-02, SD-13 and SD-14. Use commit SHA, PR ID, deployment ID and explicit change references; title similarity is not a reliable join.

**Evaluation:** establish complete relevant PR/review coverage; require the appropriate non-author approval at merge under the adopted policy; handle changes requested/dismissals, later commits, required reviewers, bypass identities and missing history. SD-01 separately evaluates authorisation before deployment. A PR approval does not prove all production changes used the PR path. A clean sample remains a sample with its selection and limitations.

**Loop:** collect events or scheduled records, reconcile changes/deployments, create one issue per control predicate and offending change, assign an owner, record corrective action, then verify future enforcement/source state. Retrospective emergency review can satisfy the declared emergency procedure; it cannot create an earlier approval timestamp. Preserve the original deviation.

**Evidence/review:** procedure revision, population and completeness report, review timestamps/identities/commit relation, related request/test/deployment records and reviewed exceptions. Evaluate current enforcement separately from the selected period. **Completion demonstration:** one approved change, a late approval, bypass, unknown review history, an unlinked deployment and an emergency case all produce the expected explanations.

### B. LM-11 vulnerability management, with SD-03 and EP-04

**Objective:** detect and handle relevant vulnerabilities within the adopted risk policy. Current mapping: CC7.1; SD-03 and EP-04 also support CC6.8/CC7.1. **Population:** required repositories, registries, hosts, endpoints and external services, reconciled to assets and scan coverage.

**Design and sources:** approved scanning/triage/remediation policy; actual Dependabot/scanner/registry findings (future collectors); source scan runs including clean runs; Verity assets, vulnerability instances, transitions, tasks and exceptions (existing foundations). GitHub's implemented enabled-setting check contributes configuration proof only.

**Evaluation:** separate discovery completeness, scan timeliness, assignment/triage, severity-policy deadlines, independently supported closure and exception validity. Preserve source detection time, import time, applicable policy, fixed-late findings, reopenings and unmatched assets. A current scan does not establish timely patching, and an empty imported register does not establish no vulnerabilities.

**Loop:** ingest idempotently; correlate asset/package/locator; assign and prioritise; create/link remediation work; retest; close/reopen with source proof; expire/review accepted risks. Collection outages produce coverage work, not a claim the assets are clean. Apply the approved severity deadlines, not a universal vendor default.

**Evidence/review:** full population and source reports, policy revision, register with source detection/triage/due/fix/retest times, reviewed false positives/acceptances, compensation evidence and period SLA results. **Completion demonstration:** overdue open, fixed late, reopened, valid/expired acceptance, missing scan, duplicate import and a completed-but-unverified task. Preserve substantial existing vulnerability workflow; do not rebuild exceptions from scratch.

### C. IAM-12 access removal, supported by HR-05 offboarding

**Objective:** revoke access within the organisation's approved time after termination or a qualifying role change. Current mappings for both: CC6.2/CC6.3, partial. HR-05 additionally covers duties such as equipment, shared credentials and ownership transfer.

**Population and sources:** authoritative staff/contractor leaver/mover events; IdP identities; GitHub, cloud and other local/non-SSO accounts, sessions and tokens as required; approved offboarding tasks. Entra/Okta/Google Workspace connectors are planned. HR connectors are outside the current signed catalogue; a controlled workforce import is also a proposed capability. Verity login memberships are not a substitute employee register.

**Correlation/evaluation:** match immutable provider identities to the authorised personnel record, handling renamed/reused email addresses, multiple accounts and contractors. Compare the effective termination/change time with actual revocation evidence for each required system. IdP disabled alone cannot prove local accounts, tokens and sessions were removed. Missing timestamps or unmatched accounts block completeness.

**Loop:** trigger at effective personnel change, reconcile daily or at the approved cadence, assign unresolved system removals, escalate at the policy deadline, and verify source state/events. These collectors remain read-only; customer administrators execute revocations through existing tools. A later verified removal resolves current exposure without erasing lateness.

**Evidence/review:** complete event roster, match decisions, source access baseline, dated revocations, HR checklist and any approved residual access decisions. **Completion demonstration:** normal leaver, future termination, contractor, renamed account, mover, local account and missing-source cases. Define which inherited SSO assertions are defensible rather than assuming every SSO app is covered.

### D. IAM-02 periodic access review

**Objective:** authorised reviewers periodically evaluate relevant access and implement corrections. Current mapping: CC6.2 partial and CC6.3 labelled full; the latter must be interpreted under the mapping review in section 3.

**Population and sources:** IdP, cloud IAM, repository permissions and other relevant system entitlements, with human/nonhuman owners and employment status. Freeze a campaign baseline and record subsequent changes. Provider collectors and the customer access-review workflow are planned; the existing Verity RBAC module governs Verity access and does not supply this customer workflow.

**Evaluation:** complete source coverage; explicit reviewer disposition for every required entitlement; reviewer authority and segregation where required; deadlines; confirmed removal/change of rejected access. A downloaded list or completed task alone does not prove review and correction. Set cadence by approved policy and risk, not a universal quarterly rule.

**Loop:** launch on schedule/material change, assign reviewers, track decisions, open removal tasks, obtain fresh source confirmation, close the campaign and retain residual risks. Overdue and partial campaigns remain visible. Access retained through an exception requires its own justified approval and expiry.

**Evidence/review:** signed campaign population, source counts, reviewer identities and dated decisions, removal confirmations, exceptions and change reconciliation. **Completion demonstration:** self-review restriction, inaccessible source, missing manager, an unacted removal, privilege added during review, and a complete campaign. Manual signed review packs remain the path until the campaign feature ships.

### E. LM-01 asset and system inventory

**Objective:** maintain a reconciled, owned and classified inventory of the relevant estate. Current mapping: CC2.1/CC6.1, partial. **Sources:** cloud accounts/subscriptions, business SaaS discovery, approved procurement/manual lists, devices and repositories, reconciled to Verity assets.

AWS/Azure/GCP discovery is planned. MDM integrations require separate scope approval; current device-management providers are marked `not_planned`. VantageMDM is a separate proposed source and is absent from the current provider catalogue: its API, tenancy, device identity and attestations need a contract. Device encryption or EDR assertions need their own EP control predicates; enrolment alone cannot establish them.

**Evaluation:** expected source accounts have current complete inventories; resources match assets by provider/account/immutable ID; ownership, environment, classification and review requirements hold; unknown or duplicate items remain visible. All existing assets having owners is insufficient if assets are missing. Loss of visibility must not automatically decommission an asset.

**Loop:** discover/reconcile, create work for unknown/unowned assets, obtain owner/scope decisions, verify disposal or changes, periodically review, and retain source visibility history. **Evidence/review:** source and asset population reconciliation, decision/ownership history, lifecycle evidence and unresolved gaps. **Completion demonstration:** unknown cloud resource, missing account, ID collision, permission loss and real deletion are distinct.

### F. BC-08 vendor due diligence, supported by BC-07 inventory

**Objective:** assess relevant third-party service use and act on its risks before the applicable approval/access milestone and on reassessment. Current BC-08 mappings: CC9.2 labelled full/P6.4 partial; BC-07 supports CC9.2. Evaluate **engagements**, because a vendor can supply different services with different risk and data access.

**Population and sources:** approved procurement/finance/manual universe plus IdP app/access signals, linked to Verity vendor engagements, risk tier, assessments, assurance-report reviews, contracts where applicable and decisions. Current vendor workflows are reusable; external discovery and `verity.vendors.*` evaluators are planned.

**Evaluation:** relevant service is inventoried; tiering is current; required diligence and authorised decision precede the defined milestone; reassessment is current; conditions are fulfilled. A SOC 2 report upload alone does not establish its period, service/system coverage, exceptions or customer-responsibility review. Record subservice dependencies and applicable complementary user entity controls (CUECs) in the customer's own programme.

**Loop:** intake, collect/review records, resolve findings or approve bounded risk, approve use, monitor due dates/material change, reassess and offboard. Verify task/condition closure. A risk decision must not re-label an unperformed assessment as completed.

**Evidence/review:** reconciled engagement population, tiering/assessment versions, reviewer decisions, report limitations/CUECs, contracts/conditions and dated follow-up. **Completion demonstration:** two engagements for one vendor, an expired report, overdue assessment, material service change and unresolved pre-use condition.

### G. GOV-18 risk assessment with GOV-20, GOV-13 and GOV-15

**Objective:** identify and assess relevant risks, decide and follow treatment, independently evaluate the programme where required, and obtain management decisions. These are separate existing controls with distinct outcomes; their exact framework mappings remain subject to review.

**Sources:** system commitments/scope, assets, vendors, incidents/changes, risk registers and assessments, approved methodology, treatment tasks, internal assessment records and management minutes. Connector results inform likelihood/exposure and review triggers; they do not make management's risk acceptance or oversight decisions.

**Evaluation:** relevant population and methodology were used; required assessments/reviews occurred at their approved intervals and triggers; decisions have authorised owners; actions are completed or explicitly accepted; effectiveness is reviewed. A filled register or uploaded meeting agenda cannot establish the process was performed.

**Loop:** schedule or trigger assessment, gather inputs, evaluate risks, approve treatment/residual risk, monitor actions, perform review and follow-up. **Evidence/review:** dated assessment, treatment plan, internal review/audit findings, management decisions and verified corrective actions. **Completion demonstration:** overdue treatment, unapproved residual risk, missing review record and an ineffective corrective action stay visible. These workflows support future ISO work without automatically satisfying its clauses.

## 7. Connector plan driven by control outcomes

| Capability / source | First useful control outcome | Boundary and sequencing |
|---|---|---|
| Existing GitHub + Verity module services | Review evidence and vulnerability workflow pilots | Finish CE population/evidence gaps and module evaluations first. Extend GitHub only with necessary reviewed read permissions. |
| Jira (or approved existing request records) | Request-to-approval-to-release traceability | Complete the change loop with CI/deployment observations. A Jira issue mentioning a PR is not automatically authorisation. |
| One priority IdP: Entra, Okta or Google Workspace | Identity population, MFA and access removal/review | Choose the provider used by the pilot customer; cover other in-scope providers subsequently. Workforce truth/import and local accounts remain dependencies. |
| AWS first in the current plan; Azure/GCP later | Inventory, cloud safeguards, IAM, logging and backups | Enumerate all declared accounts/regions/services and specify supported resource types. AWS connector presence does not mean every cloud control is automated. |
| Vulnerability scanners/registries | Discovery coverage and verified remediation | Tenable/Rapid7/Qualys are Phase 3 in current plans. Earlier delivery needs explicit reprioritisation; use supported raw reports meanwhile. |
| GitLab and Bitbucket | Equivalent code/review populations where used | Reuse check intent, but prove provider-specific semantics. Do not infer equivalence from similarly named settings. |
| 1Password | Vault use/access obligations | Complement relevant credential controls; cannot by itself prove all secrets are governed. |
| Datadog/Sentry; PagerDuty | Alert delivery, response and operating history | Correlate source alert to receipt/acknowledgment/action. A configured destination alone does not establish response. |
| Cloudflare/Tailscale | Defined edge/network/access predicates | State resource and policy coverage; join relevant identity and change data where the control needs it. |
| Slack | Notification and evidence-request delivery | Successful message delivery supports workflow, not proof that a security control operated. |
| HR/MDM/VantageMDM | Personnel lifecycle and device populations | HR/MDM are outside the currently catalogued delivery scope or not integrated. Define authoritative sources and approved scope before promises. |

Connector acceptance contract: exact supported obligations and limitations; minimal credentials; resource discovery; event/source timestamps; stable IDs; pagination/rate-limit behaviour; token scope drift; deletion/disappearance semantics; raw evidence retention; schema/version validation; reconnect/backfill; per-tenant isolation; idempotent retries; recorded-fixture tests; visible customer setup and coverage errors.

Use existing connector HTTP, storage, transaction and module-service boundaries. Add only the data concepts required by the reviewed pilots. Cross-source evaluation should consume owning-service outputs; do not bypass module boundaries with broad joins or introduce a general policy engine before a demonstrated need. Write operations in customer systems remain a separately reviewed feature.

## 8. ISO and subsequent framework expansion

ISO/IEC 27001:2022 Annex A aligns with 93 controls in four themes; it is a reference set within a risk-driven ISMS. [UKAS transition guidance](https://www.ukas.com/resources/technical-bulletins/transition-arrangements-for-iso-iec-270012022/). Necessary controls are selected through risk treatment and compared with Annex A; the SoA records inclusion decisions, implementation and reasons for Annex A exclusions, including necessary custom controls. The cited ISO committee note is practice guidance, not the normative standard. [SoA practice note](https://committee.iso.org/files/live/sites/jtc1sc27/files/resources/ISO-IECJTC1-SC27-WG1_N3298_Auditing%20Practices%20Note%20-%20SoA.pdf).

Plan four linked deliverables:

1. **Framework content:** versioned identifiers and approved descriptions for clauses 4–10 and Annex A, amendments, reviewed mappings, provenance and permitted text. Compare existing GOV controls before creating new ones.
2. **ISMS workflows:** organisational context, interested parties and scope; leadership, objectives and responsibilities; risk assessment/treatment; competence/communication and document control; operation; monitoring, internal audit, management review, nonconformity/corrective action and improvement. Reuse suitable existing modules and retain human decisions. [BSI evidence requirements overview](https://www.bsigroup.com/globalassets/localfiles/en-th/webinars/webinar-iso27001-2022-transition-november-2022-r4.pdf).
3. **SoA and applicability:** necessary controls, inclusion rationale, implementation, approved exclusions and change history. A missing connector or NA technical result is not an Annex A exclusion. Clauses 4–10 must not inherit Annex A-style exclusion toggles.
4. **Separate assessments, shared proof:** independent SOC 2 and ISO scopes/versions/periods and review conclusions, using the same control/evidence versions where appropriate. A source fact can be reused; an ISO qualifier can require additional proof. Preserve existing SOC 2 records when adopting or upgrading ISO.

Adding further frameworks follows the same gap review and versioning process. Do not assume a content pack is sufficient when a framework requires a new decision/workflow. Licensing and qualified review are required before representing content as supported. ISO clauses and SoA cannot be validated solely from the public summaries researched here.

## 9. What production ready must mean

| Gate | Observable completion |
|---|---|
| Content correctness | Every applicable requirement has reviewed coverage reasoning; every adopted control has a reviewed operational profile, required evidence, failure/unknown cases and customer parameters. No unresolved contradictory mapping meanings. |
| Scope and correlation | Expected-versus-visible populations reconcile; missing sources, collisions, scope changes and exclusions are explainable. Tests cannot improve by losing access. |
| Continuous operation | Scheduling and event reconciliation survive duplicate/late data, provider outages, worker crashes, rate limits and reconnects; no unbounded retries; collection lag and unknown coverage are visible. |
| History and traceability | Evaluations pin control/rule/scope/policy/evidence versions and period; old conclusions remain reproducible. File hashes support integrity but do not alone prove completeness or authenticity of the source process. |
| Remediation and decisions | Owned issues, task links, source-backed closure, recurrence and expired exceptions are demonstrated; accepted risk remains distinct from remediation. |
| Isolation and permissions | Tenant filters plus transaction-bound RLS, backend permission/object scope, audited mutations, protected credentials and role-scoped evidence export; adversarial isolation tests use the app role. |
| Human workflow | Useful loading/error/empty states, explicit missing-proof tasks, alternative/manual routes, accessible review decisions, source limitations and understandable current/period distinctions. |
| Audit delivery | Versioned system description and scope, request tracking, selected populations/samples, supporting artifacts, decisions and limitations export; auditor access is scoped/time-bounded and retains required history. No invented auditor opinion. |
| Deployment and recovery | Migrations preserve existing tenants and adopted content; background work is bounded; evidence retention/backup/restore is demonstrated; rollback/disable preserves history and cannot silently turn monitoring green. |
| Validation | Unit predicates, provider fixture contracts, orchestration/DB/RLS integration, workflow UI, historical-window and migration tests; then a controlled pilot with reconciled source totals and human review. |

These gates apply to each supported source/control workflow, not only to the final feature release. Content can be wrong even when code tests pass, so the control definitions need separate qualified review.

## 10. Delivery sequence and review responsibilities

1. **Content and scope workshop:** select the first customer system, category scope, observation period and operating policies. Resolve mapping semantics and required-evidence definitions for SD-06, SD-03, LM-11. Product/compliance author prepares them; a second qualified reviewer challenges coverage; management owns adopted policy choices.
2. **Evidence evaluation foundation:** specify binding/versioning, population completeness, period handling, review rules and shared evaluated outputs. Resolve CE-01 to CE-05/10/11/13 first. Run proposed evaluations alongside existing readiness and inspect differences before enabling new claims.
3. **First complete control workflow:** SD-06 end to end on GitHub, with honest manual routes for uncovered history. Then SD-03/LM-11 with real source findings, current module workflows, historical SLAs and verified exceptions. Do not begin by building fifteen shallow connectors.
4. **Change and identity workflows:** add Jira/CI/deployment inputs, then one pilot IdP plus authoritative personnel input; complete the profiles above. Access-review campaigns require their own planned workflow, not just another API import.
5. **Cloud, asset, vendor and operational domains:** deliver the next evidence outcomes with AWS and module evaluations; add other providers when they cover an actual customer population. Complete backup/restore, logging/response, people, policy, physical and governance controls through automation or documented human workflows as appropriate.
6. **SOC 2 release gate:** evaluate all controls and requirements applicable to the chosen system and categories, resolve residual gaps, demonstrate operational history, audit packaging and production gates. The six technical/vendor profiles and governance example here are a starting set; they do not complete all 116 control reviews.
7. **ISO workstream:** after stable control/evidence contracts, deliver the licensed/reviewed pack, ISMS gaps, SoA and separate engagements. Reuse evidence while testing framework-specific coverage and migration. Other frameworks repeat this reviewed process.

The product owner selects delivery priority and commercial scope. A compliance lead authors test procedures and mappings; a qualified SOC 2 practitioner/audit partner or ISO specialist reviews relevant content. Customer control owners confirm actual operation and exceptions. Engineering owns collection/evaluation correctness and reliability. Auditors retain their independent testing and conclusions. This research supplies a concrete draft, not those reviewers' approval.

Do not schedule every connector or proposed workflow simply because it appears in a catalogue. Signed Phase 2/3 boundaries, platform-report extensions and HR/MDM/VantageMDM additions must be reconciled with the intended release scope. No code changes are authorised by this plan.

## 11. Remaining decisions and verification limits

- Which first customer stack/population to support; which IdP/cloud/request source is authoritative; applicable category/period and approved control wording.
- Exact frequency, SLA, sampling, exception and review rules. Default examples are drafts until reviewed.
- Whether LM-11 needs separate control records or evaluated obligations within its current record. Defer new IDs until the first profiles demonstrate the need.
- Approved interpretation of existing `full` mappings and the migration of any stronger claims already shown.
- Adequate historical APIs/events and retention for each source, especially approval/revocation and rescans. Unsupported history remains unknown/manual rather than fabricated.
- Review of the full licensed framework material, pack redistribution rights and content attribution. Public vendor/standard guidance was researched; complete normative ISO text and production workflows were not validated.

Update the shared [gap register](control-evidence-sufficiency.md#8-maintained-gap-and-lookup-register) as each decision is answered, with source evidence, reviewer and acceptance result. Use the existing spec/review workflow for the eventual schema, API, connector and tenant-boundary changes.
