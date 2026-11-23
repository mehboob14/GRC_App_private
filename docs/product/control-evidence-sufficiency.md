# Control evidence sufficiency: research and gap register

Last reviewed: 2026-10-08. Status: proposed product requirements and research; no implementation authorised by this document.

Purpose: record what each control needs to demonstrate, what Verity can already collect, what remains unknown, and what a customer can provide until automation exists. Maintain this register as controls are investigated; do not describe planned checks as running.

This review used the current working tree, including substantial pre-existing uncommitted work, official vendor documentation, and a user-supplied GitHub evidence export. Source-code presence does not confirm deployment or successful execution. No live database or authenticated production session was inspected. Customer repository names and the raw export are intentionally omitted here.

Related intent: [control framework requirements](control-framework-requirements.md), especially EC-1 to EC-10 and ME-1 to ME-8; [common control design](../../openspec/changes/common-control-framework/design.md); [ADR-0014](../adr/0014-common-control-framework.md). This document investigates the remaining sufficiency layer; it does not replace those artifacts or approve schema/API changes.

The [continuous compliance plan](continuous-compliance-plan.md) extends this research across connectors and internal modules. It defines control granularity, seven worked operating loops, production gates and the ISO expansion path. Keep concrete proof gaps and interim customer guidance in this register.

## 1. Recommended next capability

Give each control a reviewed, versioned definition of the evidence it requires. Evaluate those requirements against actual source records, scope, dates, results and approvals. A connection, enabled setting, attached file, or available module can support one requirement without satisfying the whole control.

Extend the existing expected-evidence content and compliance services. Start with SD-06, SD-03 and LM-11. There is no present need for a new policy engine, OSCAL runtime, dependency or service. Existing `evidence[].key`, `assurance`, `cadence`, `source`, `module` and `automated_by` are useful starting points, but do not yet bind particular evidence versions to evaluated requirements.

Keep these concepts distinguishable:

| Concept | What it establishes |
|---|---|
| Collection | The source was read, with a known population and any gaps recorded. |
| Check result | A specific predicate passed, failed, could not be evaluated, or had no applicable population. |
| Evidence coverage | Every required part of this control has suitable, attributable proof for the selected scope and period. |
| Control implementation | The owner's declaration about how the organisation operates the control. |
| Internal review | The relevant person approved the evidence or control assessment under the review policy. |
| Framework requirement coverage | Applicable controls support the particular requirement to the extent stated by reviewed mappings. |
| Auditor conclusion | An external assessment; never implied by a platform status. |

Automation should perform deterministic evaluations and collect operating proof. Humans approve the rule definitions, policies, exceptions and evidence needing judgment. Do not require a person to approve every unchanged daily machine result; define when changes invalidate a prior review. AI suggestions remain drafts.

## 2. What exists, verified against code

| Area | Current implementation | Remaining issue |
|---|---|---|
| GitHub scope | Resource inventory, per-repository choices, exclusion reasons and audit entries. Active non-forks are included by default; archived repositories and forks are excluded by default. | Visibility to a token is not an approved business/audit boundary. A business may rely on a fork or need historical evidence from an archived repository. |
| Results and evidence | Append-only check results; individual evidence files per check, subject to daily/change deduplication; scope and raw source data retained. | Summary counts omit some outcome categories; population completeness is not always reflected in verdicts. |
| Expected evidence | Control content distinguishes design and operating evidence, cadences, sources and proposed checks. All seven implemented GitHub checks have partial control mappings. | No binding/evaluation proves that every required evidence item has been fulfilled. Composition primarily describes where evidence can come from. |
| Readiness | `control_ready` requires manual `implemented`, any current evidence, and no automation state of failing/error/stale. | Any one non-rejected current item qualifies; pending evidence and items with no renewal date can count. Required evidence completeness and review are not enforced. |
| Automation rollup | Can show passing when at least one mapped check passes and none fail/error/stale. | Other required checks may be unconnected or planned. A partial check's pass does not establish the full control. |
| Framework rollup | Every applicable mapped control must be ready; no applicable controls is not ready. | Inherits the control predicate's limitations and does not establish completeness of the published mapping. |
| Vulnerabilities | Definitions, asset-specific instances, CSV scan imports, owners, severity, deadlines, transitions, retest/fix workflow, and exceptions already exist. | No GitHub alert ingestion or running module checks linking these records to control evidence requirements. |
| Tasks | Generic links to vulnerabilities, status history, due dates, and evidence attachments exist. | Task closure is not independently verified remediation. `vuln_overdue` automation is unavailable; task-side add-link UI/API needs verification. |

Exact change points for a future reviewed specification:

- [readiness.py](../../backend/src/verity/modules/compliance/readiness.py): `control_ready`, `requirement_ready`.
- [evidence/service.py](../../backend/src/verity/modules/evidence/service.py): `control_ids_with_current_evidence` currently excludes rejected/expired items, rather than requiring approval or all expected items.
- [connectors/composition.py](../../backend/src/verity/modules/connectors/composition.py): source availability and expected-evidence composition; these are not sufficiency verdicts.
- [connectors/service.py](../../backend/src/verity/modules/connectors/service.py): automation aggregation, `_sync_inventory`, `_scope_summaries`, `_evidence`, and control views.
- [connectors/github.py](../../backend/src/verity/modules/connectors/github.py): `collect`, `_reviews`, `_merged_changes`, `_effective_approvers`, `_merged_reviewed`, `_dependency_alerts`.
- [control content](../../backend/src/verity/seed/content/soc2/control_templates.json), [check content](../../backend/src/verity/seed/content/automation/checks.json), and [framework mappings](../../backend/src/verity/seed/content/soc2/template_requirements.json).
- [vulnerability models](../../backend/src/verity/modules/vulnerabilities/models.py), [vulnerability service](../../backend/src/verity/modules/vulnerabilities/service.py), [task service](../../backend/src/verity/modules/tasks/service.py), [linkage service](../../backend/src/verity/modules/linkage/service.py).

## 3. Findings from the supplied 7 October report

The attached raw JSON was for `vcs.default_branch_protected`, collected at 17:46 UTC. Parsing its data gives:

| Measure | Count |
|---|---:|
| Repositories listed | 95 |
| Excluded, all with system fork reasons | 13 |
| In-scope repositories with results | 82 |
| Ordinary failures | 54 |
| Failures classified with `reason=plan` | 20 |
| Not applicable | 8 |
| Passes / collection errors | 0 / 0 |

Thus `95 = 13 + 82`, and `82 = 54 + 20 + 8`. The header's 74 failures includes the 20 plan failures. The rendered report separates those 20 but its main tiles omit the eight not-applicable outcomes. This is a presentation/meaning gap, not evidence of 20 missing results. The separate pasted review-required report has the same 74 versus 54+20 split, but its raw JSON was not supplied and independently parsed.

The merged-review paste shows three failed repository-level results and many repositories with no merges or no commits. It does not mean only three pull requests were checked, nor that every other repository passed. Exact event totals and completeness require that check's full raw report; they cannot be recovered from the pasted summary alone.

Required reporting contract, proposed:

- Show the unit next to counts: repositories, pull requests, alerts, or check/resource results. Never divide check-row failures by a distinct-repository count without explaining the units.
- Every listed resource must have an explicit disposition. Keep exclusion, no events, feature unavailable, missing permission, truncated/unread, pass and fail distinguishable. Feature unavailable may remain a blocking failed predicate with a reason; do not silently turn it into a pass or exclusion.
- Distinguish visible resources from business inventory, approved scope, and actually evaluated resources. A token can hide repositories that a collector cannot enumerate.
- Preserve failed evidence. A valid, authentic report of failure is useful evidence and must be reviewable; approving the report does not approve the control result.
- Remediation advice must not suggest making private business code public or excluding a required repository merely to obtain a pass. Offer suitable enforcement, an approved alternative process, or a genuine scope correction with justification.

## 4. How Vanta and Drata inform this plan

These are documented behaviours, not claims about either company's private implementation:

- Vanta rolls control status up from mapped tests and documents and explicitly separates it from an auditor's assessment. Adopt the visible traceability and that distinction. [Vanta controls](https://help.vanta.com/en/articles/11345373-controls-page).
- Vanta exposes test criteria, resource results, source data and exclusions. Its guidance says aggregation varies by test, so Verity needs a declared population and predicate for each evidence requirement. [Vanta automated test evidence](https://help.vanta.com/en/articles/11345529-automated-test-evidence).
- Drata uses valid mapped evidence, passing tests, published policies and current evidence dates in readiness. Its own guidance warns that some controls can appear ready from a policy while still needing operating evidence. Copying a mapped-item rollup alone would retain the gap we are investigating. [Drata control readiness](https://help.drata.com/en/articles/10723594-are-your-controls-ready-understanding-the-relationship-between-policies-evidence-and-controls).
- Drata can require a designated approval in addition to readiness, and evidence/policy changes can trigger another review. Its framework view rolls up applicable mapped controls. [Drata approvals](https://help.drata.com/en/articles/13380564-manage-required-approval-and-control-readiness), [framework readiness](https://help.drata.com/en/articles/13765790-framework-readiness).
- Vanta's vulnerability guidance discusses scan results and remediation samples against company SLAs, and distinguishes dependency scanning from host scanning. This supports combining GitHub data with Verity's vulnerability workflow. [Scanning guidance](https://help.vanta.com/en/articles/11346112-frequently-asked-question-what-should-i-use-for-vulnerability-scanning), [SLA calculations](https://help.vanta.com/en/articles/11951321-how-vanta-calculates-vulnerability-slas).

Recommendation inferred from these sources and Verity's gaps: define required evidence explicitly before calculating completeness, retain the reasons for every result, and expose internal review separately from auditor acceptance.

## 5. Required shape of a control's evidence definition

Use the existing stable control and evidence keys. The following are semantic requirements to specify, not an approved database schema:

| Definition | Decision needed |
|---|---|
| Objective and boundaries | Which assertion is being tested? Which systems, assets, people, repositories and environment belong to it? |
| Evidence obligations | Required design proof and required operating proof. Identify supplemental items that do not affect completion. |
| Accepted sources | Exact test/source/module report/document version; permitted manual equivalents and who approves equivalence. |
| Combination rule | Which items are all required, and which are approved alternatives? One arbitrary attachment cannot fulfil all obligations. |
| Predicate and denominator | What must be true of which population? Define severity thresholds, sampling rules and zero-event handling. |
| Period and timeliness | Observation start/end, scan cadence, freshness, SLA policy version and historical gaps. Collection date and expiry date alone are insufficient. |
| Completeness | Pagination/truncation, permission gaps, unmatched assets, missing systems, excluded records and known unknowns. |
| Review policy | When deterministic proof is enough, when human review is required, and which changes invalidate it. |
| Exceptions | Applicable resource, risk, requester, approver, dates, compensating measures and their proof. Acceptance does not mean fixed. |
| Result explanation | Met, missing, failed, incomplete/unknown, stale or needs review, with the source records and next action. |
| Provenance | Rule/mapping version, scope version, input references/hashes, observation time and evaluator version; preserve prior conclusions. |

Proposed eligibility rule: every required obligation has an accepted source for the relevant scope and period, the required predicates hold with adequate population coverage, and required review is complete. Missing definitions, planned tests, unconnected sources and incomplete collection do not satisfy an obligation. An approved manual alternative may do so if it meets the same declared need.

Keep status dimensions separate in the UI: implementation; automated findings/coverage; evidence completion; review; exception disposition. A useful explanation is “Scan configuration verified; alert remediation history missing; policy awaiting review.” Avoid one green badge hiding these conditions.

An empty population requires evidence that the population really was empty during the selected period and a documented rule for that case. No PR merges does not establish that there were no direct pushes; no imported vulnerabilities does not establish that scanning found none. A late fix resolves the current issue but leaves the historical SLA breach visible.

For framework requirements, evaluate the published mapping's coverage and any requirement-specific qualifiers. Reuse shared control evidence across frameworks, but do not infer that satisfying a SOC 2 mapping satisfies an ISO requirement. Partial mappings and unmapped obligations remain visible. This extends the current rollup and needs specification review.

## 6. First control profiles to complete

The criterion identifiers below are the current seed mappings, not new or independently certified mappings. Evidence needs are draft product acceptance conditions to review against each customer's control wording.

| Control and mapped criteria | Current GitHub contribution | Additional proof / automation to define | Customer action until available |
|---|---|---|---|
| **SD-06 Peer code review** — CC8.1 | Protection, required review setting, recent merged-PR review sample. | Approved review procedure; complete relevant change population; valid independent approval before merge; handling of later commits, bypasses and emergency changes. | Confirm business repositories/branches and provide change/review records for gaps. |
| **SD-03 Dependency and image scanning** — CC6.8, CC7.1 | Dependency alert setting only. | Covered repositories and registries; actual scans/alerts; triage timestamps; build gating and SBOM where required by the adopted control; remediation or valid acceptance. | Supply dependency/container scan exports and alert handling records; adopt an approved triage policy. |
| **LM-11 Vulnerability management program** — CC7.1 | One finding source is enabled. | Approved scope/cadence/SLAs; full relevant scan coverage; finding ownership/triage; fixes and retests; on-time and late remediation history; reviewed exceptions. | Import scan reports, reconcile assets, assign findings, retain fix/retest evidence, and review accepted risks. |
| **SD-01 Change management** — CC8.1 | Selected protection and PR-review facts. | Change request, business/security approval, test results, deployment linkage and emergency-change review across in-scope changes. | Link representative request/approval/deployment records with dated evidence. |
| **SD-02 Automated testing in CI** — CC8.1, PI1.3 | Required status checks configured. | Actual check executions for relevant changes, success before merge/deploy, bypass/skip behaviour, and test relevance to the adopted objective. | Provide CI run records and approved test scope; configuration alone is partial. |
| **SD-11 Secret scanning** — CC6.1, CC7.1 | Scanner enabled. | Source coverage; actual detections; credential revocation/rotation and investigation; complete no-event records where applicable. | Provide scanner findings and rotation/incident records; do not include secret values. |
| **IAM-03 MFA** — CC6.1 | GitHub organisation enforcement where applicable. | Identities/systems in scope, actual enforcement/coverage, approved exceptions and other authentication sources. Personal-account NA cannot establish business MFA coverage. | Provide IdP/system reports and document identities outside enforcement. |

Future modules use the same contract: an asset register needs completeness/reconciliation and owner review; TPRM needs in-scope engagements, current assessments, decisions and follow-up proof. A module row or task link alone is not an evaluated evidence obligation. Business continuity remains a separate future capability and must retain a manual path until implemented.

## 7. Vulnerability automation: concrete path

1. **Establish the population.** Map business repositories, registries, hosts and relevant assets to the control scope. Compare expected scan coverage with the source populations. Preserve scan date, source, completeness and zero-finding runs.
2. **Ingest actual findings.** Add a reviewed read-only Dependabot alert collection plan. Preserve stable source identity, affected package/manifest/resource, source detection and update times, dismissal/fix/reopen history and raw provenance. Specify how repository/package findings map to the existing asset + definition + locator model; do not guess or silently discard unmatched rows.
3. **Manage work in Verity.** Use the existing owner, severity, SLA, transitions, task links and retest paths. Decide the relationship between task completion and vulnerability verification. A task marked closed must not automatically establish that the affected package or asset was fixed.
4. **Evaluate the period.** Apply the approved severity-based policy to source detection time and actual remediation/verification events. Include items fixed late, reopened items, exclusions, unknown timestamps and scan gaps. Do not report only today's open overdue count as historical effectiveness.
5. **Apply exception decisions transparently.** Use existing exception capabilities after verifying their lifecycle. Show accepted exposure separately; check authorisation, scope, expiry and compensating evidence. An exception is neither a technical fix nor an automatic override of a framework requirement.
6. **Produce attributable proof.** An immutable report/assessment references the source population, policy and rule versions, period, findings, task/exception decisions, and supporting evidence. A control evaluation binds this to the specific required evidence keys; the requirement view follows the reviewed control mapping.

Current module facts and limits:

- `VulnInstance` has first/last seen, owner, severity, SLA due, fixed/verification and acceptance fields; transitions and source reports exist. CSV import deduplicates by asset, definition and locator. These are reusable foundations. However, `_ingest` assigns `first_detected_at` from import time and starts the SLA then; it does not preserve an earlier source detection timestamp. Importing an old finding therefore cannot prove its true historical remediation timeliness.
- SLA deadlines use the then-current tenant severity policy at creation/resurfacing, but the instance does not retain that policy's version. Define how historical decisions preserve the applicable policy and how changes affect existing deadlines.
- `pending_retest -> fixed` has a manual verification path. The remediation-plan apply flow is explicitly simulated, and its verification is a person's attestation; neither is an independent scanner retest.
- `VulnException` request/decision APIs and a UI already exist, including requester/decider separation and time limits. A one-step `/accept` path also remains. The sweep reopens expired accepted instances, but no corresponding exception-record expiry update was found. Verify reconciliation and deployed UX before describing the lifecycle as complete.
- Scan reports have a `scan_date` field with no assignment found in the inspected import flow; unmatched counts are returned but not retained on the report; an instance's original `report_id` is not refreshed on later observations. Historical source coverage and per-run lineage need explicit design.
- `verity.vulns.within_sla`, `verity.vulns.kev_owned`, `verity.tasks.remediation_in_sla` and `scanner.scans_current` are seeded definitions with no implementations. Module presence does not make these evaluations run.
- Generic task-vulnerability links and task attachments exist. The task-side add-link API is stubbed and overdue-vulnerability task automation is unavailable. Verify the usable linkage path before promising an automatic remediation workflow.

## 8. Maintained gap and lookup register

Priorities: P1 = resolve before stronger readiness claims; P2 = next automation/operating-proof work. Status is research status, not implementation approval. All engineering ownership is unassigned until scope review.

| ID | Priority / status | Needed decision or work | Completion evidence / interim guidance |
|---|---|---|---|
| CE-01 | P1 / confirmed gap | Bind actual evidence versions/results to every required control evidence key, with completeness and review rules. | One config file cannot satisfy LM-11's policy, scans and remediation obligations; show each missing item. |
| CE-02 | P1 / partial capability | Confirm business scope and resource identity; distinguish token visibility, approved scope and evaluated population. Reconcile resources no longer visible. | Scope owner can explain included/excluded resources and changed visibility. Customers review defaults; a fork is not inherently outside the business. |
| CE-03 | P1 / confirmed gap | Reconcile header/report/check totals and include NA, plan limits and incomplete reads. | The supplied example explains 95 = 13 + 54 + 20 + 8 consistently; count units are explicit. |
| CE-04 | P1 / confirmed gap | Propagate completeness through repository, PR and review pagination and rate-limit handling. | Incomplete clean sample never becomes a full-population pass; incomplete zero sample never becomes verified no activity. |
| CE-05 | P1 / lookup plus gaps | Define valid review at merge: independent reviewer, timestamps, changes requested/dismissals, required approvers, relevant commit and bypasses. | Fixtures cover late approvals, revoked approvals, later commits, bot identities and missing history. Source events are sufficient for the claimed time, or the result says unknown. |
| CE-06 | P2 / missing collector | Import actual Dependabot findings into an approved existing-module contract. Decide asset/package identity, provenance, duplication and reopen handling. | Reimport creates no duplicate finding; lost visibility or an absent alert is not automatically called fixed. Manual scan/alert import remains available. |
| CE-07 | P1 / partial capability | Preserve scan population, negative results, scan time, unmatched rows and observation lineage. | A zero-finding report can distinguish a complete clean scan from an unscanned/hidden system. |
| CE-08 | P2 / planned only | Implement approved module evaluations over historical vulnerability/task data, using policy versions and known timestamps. | Fixed-late findings remain SLA misses for the historical window; current posture and period performance differ correctly. |
| CE-09 | P1 / capability exists, verify | Reconcile exception record status, instance acceptance, expiry sweep and the two acceptance paths. Define effect on control assessment. | Expired acceptance is not displayed as active or counted as remediation; current valid exceptions stay visible with approver and evidence. |
| CE-10 | P1 / confirmed gap | Define required review and material-change invalidation, distinct from evidence authenticity and control outcome. | Pending manual proof does not satisfy an approval-required obligation; approved failure evidence remains a failure. |
| CE-11 | P1 / needs content review | Verify every control's required design/operating items and mapping coverage/qualifiers. Reconcile differences with existing AU/EC readiness prose. | Reviewed profiles for pilot controls; unmapped or partially supported framework needs do not disappear. |
| CE-12 | P2 / design needed | Persist reproducible period assessments and report versions while preserving append-only histories. | A prior assessment remains explainable after rule, evidence, scope, policy or control mapping changes. |
| CE-13 | P1 / confirmed wording risk | Replace upgrade/public/exclude advice with context-appropriate remedies in a future change. | Customers receive safe operational choices; exclusion requires a genuine scope basis, and public disclosure is not a compliance shortcut. |
| CE-14 | P2 / partial capability | Complete usable task-finding linkage and define evidence-backed closure/retest rules. | A completed task with an unresolved source finding cannot make remediation pass. |
| CE-15 | P1 / design needed | Distinguish alternative providers from all providers actually used by the scoped business. Reconcile each expected source population and visibility history. | Passing GitHub cannot cover in-scope GitLab repositories; disconnecting a required source leaves a missing/unknown obligation. Customers maintain an approved system/source list meanwhile. |
| CE-16 | P1 / planned only | Define authoritative workforce/resource sources and stable cross-source joins, with ambiguity and unmatched-record handling. | Offboarding covers IdP and relevant local accounts; reused emails do not silently match different people. Verity tenant memberships are not the customer's employee population. Use reviewed personnel/access exports until collection and correlation ship. |
| CE-17 | P1 / needs content review | Review control granularity and contradictions before splitting or adding controls. Prioritise SD-03 scope/guidance, IAM-03 exclusions, EP-04 patch proof and LM-11 operating obligations. | Existing change controls retain separate purposes; new controls have a distinct objective/owner/cadence where needed. A current scan alone never establishes on-time patching. See the continuous plan's control-decision rubric. |
| CE-18 | P1 / confirmed documentation conflict | Resolve whether `full` mapping means independently meeting a requirement or being its primary supporting control; current design passages conflict. | Reviewed mapping definitions and tenant-facing claims agree. Existing mappings are not silently promoted to full criterion satisfaction; residual obligations remain visible. |
| CE-19 | P2 / design needed | Plan ISO content, ISMS workflows, SoA, and simultaneous framework assessments with independent scopes/periods. The current engagement is unique per tenant. | SOC 2 history survives ISO adoption; shared evidence does not erase framework-specific obligations. Customers retain approved scope/SoA and management-system records until these workflows are supported. |
| CE-20 | P1 / design needed | Govern control/rule/mapping revisions and any split through review, versioning, effective dates and explicit tenant adoption. | Earlier conclusions remain reproducible; new or successor controls do not inherit a passing result or acceptance without review. Content changes show their evidence and scope impact before activation. |
| CE-21 | P1 / design needed | Demonstrate continuous collection and evaluation reliability across retries, late events, outages, revoked permissions and backfill. Define per-obligation freshness and retention. | Lost visibility cannot improve posture; collection lag and unknown intervals are explicit; replay produces no duplicate issue. Current snapshots and period effectiveness remain distinguishable. |

Details behind CE-04/05: GitHub currently collects at most 500 closed PRs and reads reviews for at most 100 merged PRs per repository, with up to 300 reviews per PR. `_merged_reviewed` can pass a clean incomplete sample and forces `complete=True` on zero merges. Repository enumeration is also capped; paging does not communicate whether a further page existed after the cap. These may not affect the supplied 95-repository run, but they affect the validity of universal claims.

`_effective_approvers` already checks pre-merge timing, excludes the author and uses the latest qualifying decision per reviewer. It allows approval of an earlier commit while recording it. Verify whether that is acceptable under the adopted control and whether REST review state reconstructs dismissal/history at merge time. The API supplies review state, `submitted_at` and `commit_id`; these fields alone should not be assumed to provide every historical event. [GitHub review API](https://docs.github.com/en/rest/pulls/reviews#list-reviews-for-a-pull-request).

## 9. Proposed delivery sequence and acceptance

1. Review three pilot control profiles with the product/compliance owner: SD-06, SD-03, LM-11. Set scope, observation period, required evidence, alternatives, SLA policy and review needs. Resolve CE-11 against the existing common-control proposal.
2. Specify the population/count/temporal correctness work and the evidence-to-obligation contract. Agree API, model, permissions and migration impact before implementation. Preserve existing evidence and keep old reports distinguishable from new evaluation versions.
3. Evaluate the pilots using current manual/module evidence with explicit missing/unknown reasons. Verify that partial GitHub passes cannot complete them. Use deterministic rules; do not introduce a general rule language unless these pilots demonstrate a concrete need.
4. Add actual vulnerability finding ingestion and the missing module evaluations; complete exception and task lifecycle gaps. Ship each source only when its coverage and provenance are demonstrable.
5. Roll out a shared evaluated view to controls, framework drill-down, dashboards and exports. Compare it with current readiness before enabling new claims. Expand the same reviewed pattern to remaining controls and later frameworks using the [continuous compliance delivery plan](continuous-compliance-plan.md#10-delivery-sequence-and-review-responsibilities); resolve CE-15 to CE-21 for the affected release.

Required scenarios for the eventual spec (not executed in this documentation task):

- Dependabot enabled, no imported findings or coverage report: configuration supported, remediation proof missing.
- All visible repositories pass, but business inventory or paging is incomplete: coverage unknown.
- A complete no-event period versus a missing/partial event history: distinct conclusions.
- Approval after merge; approval later withdrawn; approval on an earlier commit; missing review pages: explicit, policy-consistent outcomes.
- One current pending file versus approved evidence for every required item: different eligibility.
- Authentic approved evidence showing a failure: still blocks its predicate.
- A fixed-late vulnerability with a closed task: current issue resolved, historical SLA miss retained.
- A current exception, an expired exception and a false-positive decision: distinct treatment and review requirements.
- Required planned test with an approved manual equivalent: can meet its obligation; planned test alone cannot.
- Repeated source imports, changed policy, lost token access and cross-tenant record IDs: deterministic history, no duplicate findings, no silent passes, no information leakage.

Existing tenant/RLS boundaries, backend permissions, service boundaries, mutation audit entries and append-only tables remain mandatory. Any new schema/API requires the normal reviewed OpenSpec change; this register authorises none.

## 10. How to maintain this file

For each newly investigated control, record:

- Control code, exact adopted objective and current framework mappings.
- Business scope and assessment period; source populations and exclusions.
- Required design and operating evidence keys, accepted sources/alternatives and combination rule.
- Existing collected facts and their limitations; actual deployed behaviour if verified.
- Missing proof, lookup questions, client action now, and product work later.
- Rule author/reviewer, status, source references, acceptance scenarios and last verified date.

Use statuses `confirmed gap`, `partial capability`, `lookup`, `planned only`, `implemented in code`, and `verified in deployment` deliberately. Close a tracker item only with linked code/test evidence and, where relevant, a demonstrated workflow. Keep historical limitations and the decision that resolved them.

Open decisions: who approves the evidence definitions and framework mappings; the pilot customer's business scope and period; exact SLA and review policies; acceptable alternatives for unavailable GitHub features; and a qualified review of what each control supports. These affect the later specification, but do not prevent documenting the current gaps.
