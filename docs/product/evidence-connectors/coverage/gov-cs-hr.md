# GOV, CS and HR: where every artifact's evidence comes from

Control mapping research for the governance (GOV, 30 controls), communication (CS, 7) and people (HR, 9)
families, written to `AUTHORING.md` sections 5 and 6. It is a plan: nothing here is built, and no content
JSON is changed. Files: this page, `gov-cs-hr.json` (one entry per artifact per control, on the proposed
structure) and `gov-cs-hr.controls.json` (one decision per control). Read on 2026-11-23 from the shipped
content packs, the guided onboarding plan (part 5 and appendix A), `control-framework-requirements.md`
(appendices B and C) and the module code under `backend/src/verity/modules/`.

## Proposed control changes

Each control was read against every requirement it maps to in `soc2` and `iso27001`
`template_requirements.json`. A split is a proposal for qualified review (FW-5 second reviewer), never
applied by this plan. Existing codes keep their meaning; successors take the next free number.

| Decision | Count | Controls |
|---|---|---|
| keep | 31 | CS-01, CS-04, CS-05, CS-06, GOV-01, GOV-02, GOV-03, GOV-04, GOV-06, GOV-07, GOV-09, GOV-10, GOV-11, GOV-12, GOV-14, GOV-16, GOV-18, GOV-19, GOV-22, GOV-23, GOV-24, GOV-25, GOV-26, GOV-27, GOV-30, HR-01, HR-03, HR-04, HR-06, HR-07, HR-09 |
| revise_objectives | 12 | CS-02, CS-03, GOV-05, GOV-08, GOV-13, GOV-20, GOV-21, GOV-28, GOV-29, HR-02, HR-05, HR-08 |
| split | 3 | CS-07, GOV-15, GOV-17 |
| add | 0 | none |
| merge | 0 | none |

No requirement mapped to these families lacks a suitable control, so nothing is added. No pair is
merged: GOV-01 and GOV-28 overlap on document mechanics but test different things (whether a policy
still fits practice, against how every document is controlled); HR-05 and IAM-12, and HR-06 and IAM-01,
overlap on access but the HR controls are wider. They share evidence instead.

### Splits

**CS-07 Contacts with authorities and security communities: split out CS-08 Security community memberships and advisories (proposed).** ISO27001:A.5.5 (authorities) and A.5.6 (security groups) are both mapped full but are different activities: the first is an incident and legal duty owned with legal, the second is a threat input owned by security, with its own evidence and its own SoA row.

- Moves: CS-07.B becomes CS-08.B.
- New objectives on the successor: CS-08.A, CS-08.C.
- Tenant impact: adoption proposal: ISO 27001 workspaces are offered CS-08; CS-07 evidence tagged to memberships is listed for the owner to re-tag, nothing is copied and no green result carries over.

**GOV-15 Periodic management review of security: split out GOV-31 Yearly management review by top management (proposed).** Bundles a quarterly management review (SOC2:CC4.2, CC1.2, the forum for control health) with the yearly review by top management that ISO27001:9.3.1 to 9.3.3 require, with its own input list, attendees and outputs. Different cadence, different body, and the ISO part does not apply to a SOC 2 only workspace.

- Moves: GOV-15.C becomes GOV-31.C.
- New objectives on the successor: GOV-31.A, GOV-31.B, GOV-31.D.
- Tenant impact: adoption proposal and data migration: ISO 27001 workspaces are offered GOV-31; the 9.3 mappings move after the owner accepts; management review assurance records stay where they are and are linked to both controls; verity.management_review.in_12_months moves to GOV-31 and its history stays on GOV-15.

**GOV-17 Security policy suite: split out GOV-32 Top management security policy statement (proposed).** Bundles the top management policy statement (ISO27001:5.2, a clause duty with its own approver and content) with the topic policy set (SOC2:CC5.3 full, ISO27001:A.5.1 and topic Annex A links). Different approver, different evidence, and SOC 2 does not ask for the statement.

- Moves: GOV-17.A becomes GOV-32.A.
- New objectives on the successor: GOV-32.D.
- Tenant impact: adoption proposal: ISO 27001 workspaces are offered GOV-32; the policy statement document is linked to GOV-32 on acceptance; 5.2 readiness is recomputed, never copied.

Mapping changes the splits need (requirement, control, coverage before and after, rationale):

| Requirement | Control | From | To | Rationale |
|---|---|---|---|---|
| ISO27001:A.5.6 | CS-07 | full | removed | Moves to CS-08; CS-07 keeps authority contacts (A.5.5). |
| ISO27001:A.5.6 | CS-08 | none | full | The list of groups and feeds followed, each with an owner, kept current and producing items for the threat review, is the contact this requirement asks for. |
| ISO27001:9.3.1 | GOV-15 | full | removed | The yearly review by top management moves to GOV-31. |
| ISO27001:9.3.2 | GOV-15 | full | removed | As above. |
| ISO27001:9.3.3 | GOV-15 | full | removed | As above. |
| ISO27001:7.1 | GOV-15 | partial | removed | Resource commitments for the program are decided at the yearly review. |
| ISO27001:9.3.1 | GOV-31 | none | full | A yearly review by top management of whether the program fits, covers what it should and works, with attendees and decisions recorded. |
| ISO27001:9.3.2 | GOV-31 | none | full | The review takes each set input and the record shows it, input by input. |
| ISO27001:9.3.3 | GOV-31 | none | full | Decisions on improvements, changes and resources are recorded and tracked. |
| ISO27001:5.1 | GOV-31 | none | partial | Top management reviewing the program once a year is part of leadership. Policy and objectives are shown by GOV-32 and GOV-26. |
| ISO27001:7.1 | GOV-31 | none | partial | The yearly review records the resource commitments for the program as a whole. Needs per objective are in GOV-26. |
| ISO27001:5.2 | GOV-17 | partial | removed | The statement moves to GOV-32. CS-04 keeps its partial link for communication to staff. |
| ISO27001:5.1 | GOV-17 | partial | removed | Top management setting the policy moves with the statement. |
| ISO27001:5.2 | GOV-32 | none | full | A statement approved by top management that fits the company, frames the objectives, commits to the requirements and to improving, is communicated to staff and is available to interested parties. |
| ISO27001:5.1 | GOV-32 | none | partial | Top management setting the policy is part of leadership. Review and resourcing are shown by GOV-02, GOV-15 and GOV-31. |
| SOC2:CC5.3 | GOV-32 | none | partial | The statement is the top of the policy set that deploys control activities; the topic policies are GOV-17. |

Check mapping: `verity.management_review.in_12_months` moves from GOV-15 to GOV-31. It is a 12 month floor, which fits the yearly review. The quarterly review gets verity.assurance.management_review_held.

### Objective changes

| Objective | Change | Assurance | Statement (Verity's words) | Why |
|---|---|---|---|---|
| CS-02.F | add | design | Where Processing Integrity is in scope, the published terms or service description say what the service processes, which inputs it accepts and what customers can expect about the completeness, accuracy and timing of its outputs. | SOC2:PI1.1 is mapped partial to CS-02 on the published terms, and no objective tested what those terms say about processing. |
| CS-03.A | reword | design | A security reporting channel, such as a security address or form, is published for staff and customers. It names who reads it and the expected response time, says that reports made in good faith carry no blame, and the incident plan points to it. | The ISO27001:A.6.8 mapping is full and its rationale relies on no blame for good faith reports, which no objective tested. |
| CS-07.B to CS-08.B | move | operating | The company belonged to or subscribed to security groups and advisory feeds that fit its technology and sector, and a named person followed each one and passed on what mattered. | Moves with ISO27001:A.5.6 to the successor control. |
| GOV-05.E | add | operating | Software licences and other intellectual property terms the company relies on are in the register with their limits and an owner, and use was compared with those limits in the last 12 months. | ISO27001:A.5.32 is mapped partial on licence and IP terms in the register, and no objective tested them. |
| GOV-08.B | reword | operating | Every deficiency found in the period was logged with its source, date found, owner, severity, root cause, due date and the step taken at once to contain it and deal with its effects, including those raised by internal audit and by incidents. | ISO27001:10.2 is mapped full and its rationale names containment and consequences, which the objective left out. |
| GOV-08.E | reword | operating | Deficiencies past their due date were reported at management review with a new date or a decision. | The old objective bundled overdue reporting with the search for the same cause elsewhere; the second part moves to GOV-08.F. |
| GOV-08.F | add | operating | Where a root cause could apply elsewhere, other systems and teams were checked for the same problem, and the policy, procedure or control was changed where the cause showed a wider gap. | Tests the part of ISO27001:10.2 on similar problems elsewhere and changes to the program on its own. |
| GOV-13.E | add | operating | After each significant change to the organization, its services or the way security is run, a targeted independent review was held, or the change was recorded as covered by the next planned audit with a reason. | ISO27001:A.5.35 is mapped full and expects review on significant change as well as at planned intervals. |
| GOV-13.F | add | design | Where the Privacy category is in scope, the audit program covers the privacy commitments, including how privacy requests and complaints are handled. | SOC2:P8.1 is mapped partial to GOV-13 (guided onboarding part 5, section 7) with no objective behind it. |
| GOV-15.A | reword | design | An approved procedure sets a management review at least each quarter with the security lead and managers who can commit resources, and states how actions are recorded and escalated. | The input list of the yearly review moves to GOV-31.A. |
| GOV-15.C to GOV-31.C | move | operating | In the last 12 months top management judged whether the program still fits the business, covers what it should and works, using the set inputs, and recorded its decisions on improvements, changes and resources. | Moves with ISO27001:9.3.1 to 9.3.3 to the successor control. |
| GOV-17.A to GOV-32.A | move | design | The top level security policy is approved by top management, or by the board where a regulator requires it. It fits the purpose of the company, states the security objectives or how they are set, and commits to meeting the requirements that apply and to improving the program. | Moves with ISO27001:5.2 to the successor control. |
| GOV-17.D | reword | operating | The current version of each policy was available to all staff at a known location during the period. | The part on sharing the top level policy outside the company moves to GOV-32.D. |
| GOV-20.F | add | operating | Each risk treated by transfer names the contract or insurance policy that carries it, with its cover and expiry, and a recorded decision says whether insurance is needed against business disruption. | SOC2:CC9.1 is mapped partial to GOV-20 and the guided onboarding plan adds the insurance decision; no objective tested transfer. |
| GOV-21.E | add | operating | Each person holding a role with security duties was told of the role and its duties in writing, such as through a role description they acknowledged, and could describe it when asked. | ISO27001:5.3 expects roles to be communicated, and the mapping rationale says this control does not show it; no other control did. |
| GOV-28.B | reword | design | A list names every document and record the program needs, including those the standards, laws and contracts followed call for, each with an owner. | The operating procedures part moves to GOV-28.F, so ISO27001:7.5.1 and A.5.37 are tested apart. |
| GOV-28.F | add | operating | An operating procedure exists for each routine task on the systems in scope, with an owner, version and review date, and the people who run those systems can reach the current version. | ISO27001:A.5.37 is owned by engineering and was folded into the documents list objective. |
| GOV-29.D | reword | operating | Before each planned change to the management system or the services in scope, the reason, expected effect, owner, timing and resources were recorded and approved. | Planned and unplanned changes are two populations; unplanned ones move to GOV-29.F. |
| GOV-29.F | add | operating | Each unplanned change to the management system or the services in scope in the period was reviewed afterwards for harm, and any action needed was raised. | ISO27001:8.1 asks for unintended changes to be reviewed, tested on its own. |
| HR-02.B | reword | operating | The list of staff and contractors who started in the period was complete when compared with the joiner roster and the contractor register. | Outside parties are a different population with a different source; they move to HR-02.F. |
| HR-02.F | add | operating | Each outside party given confidential information in the period, such as a supplier, partner or prospective customer, had a non-disclosure agreement or contract confidentiality terms in force first. | ISO27001:A.6.6 is mapped full and covers outside parties, whose population is the vendor and partner list, not the joiner roster. |
| HR-05.C | reword | operating | Every leaver on the roster for the period had a closed offboarding record. | Role changes move to HR-05.F. |
| HR-05.F | add | operating | Each role change in the period had the access, asset and duty items of the checklist run by the date of the change, and access the new role does not need was removed. | ISO27001:A.6.5 covers change of role; movers and leavers are separate populations with separate failures. |
| HR-08.E | add | operating | The training checked that people understood it, such as through a quiz or a phishing exercise, and each person below the pass mark was trained again. | The SOC2:CC1.4 rationale says attendance alone does not show competence, and ISO27001:A.6.3 and 7.2 expect training to work. |
| CS-08.A | add | design | The security groups, advisory feeds and professional bodies the company follows are listed, each chosen for its technology or sector, with a named owner and a rule for what is passed on and to whom. | The successor needs a design objective of its own. |
| CS-08.C | add | operating | Items passed on from these sources in the period reached the threat review or the people named, and the list of sources was checked in the last 12 months. | ISO27001:A.5.6 is about keeping the contact useful, so what came of it is tested, not membership alone. |
| GOV-31.A | add | design | An approved procedure sets a review by top management at least once a year and lists what it must take in: actions from earlier reviews, changes in outside and inside factors and in what interested parties need, their feedback, nonconformities and corrective actions, measurement and audit results, how far objectives were met, risk results and treatment status, and improvement ideas. | ISO27001:9.3.2 needs the inputs set in advance. |
| GOV-31.B | add | operating | The record of the yearly review shows each listed input was considered, with the source record for each, or says why one did not apply. | ISO27001:9.3.2 is tested input by input, which the old GOV-15.C did in one line. |
| GOV-31.D | add | operating | Each decision from the yearly review on improvements, changes to the program or resources has an owner and a date and was tracked to closure or carried to the next review. | ISO27001:9.3.3 outputs are tested on their own. |
| GOV-32.D | add | operating | The current policy statement was communicated to staff and made available to customers and other interested parties who need it, and the version they could reach was the approved one. | ISO27001:5.2 expects the statement communicated inside and available outside; this was half of the old GOV-17.D. |

Kept controls, with the reason, are in `gov-cs-hr.controls.json`.

## How to read the tables

- **Today** is the source `artifacts.json` names now: `person`, `check:<key>` or `document:<template>`.
- **Planned** lists every source in order: Verity module reports and `verity.*` checks, document
  templates, connector checks (existing keys), `NEED <capability>` for connector predicates the
  reconciliation step will match to keys, and what a person still supplies.
- **Phase** is when the first non person source arrives: P1 Verity modules and documents now; P2 the
  signed Phase 2 connectors (GitHub already runs); P3 later connectors, unsigned systems (HR, learning,
  signing, screening) or modules signed for Phase 3 and not built (Incidents 3.1, Access reviews 3.2);
  people-only when no system will ever hold it. A phase never means the person part goes away: almost
  every source fills `partial`, and the notes say what remains.
- A `verity.*` check reads module data through module services inside the tenant's session (ME-6).
  Verity membership is not the staff roster: every check that judges "all staff" judges members, so
  the roster comparison stays open until an HR source exists (open question 1).

## Counts

299 artifact entries across 49 controls (46 adopted, 3 proposed successors), 155 distinct artifacts.

| Phase | Artifact entries |
|---|---|
| P1 | 266 |
| P2 | 11 |
| P3 | 15 |
| people-only | 7 |

New `verity.*` checks: 32. Existing checks reused: 38.

| Capability | NEED predicates |
|---|---|
| alerting | 1 |
| background_screening (new capability) | 1 |
| esignature (new capability) | 1 |
| hr_system | 10 |
| identity_provider | 5 |
| learning_platform (new capability) | 4 |
| public_web (new capability) | 2 |
| ticketing | 4 |

New capabilities proposed (none exists in `capabilities.json`; only `verity_members` is built in, the
others are outside the signed catalogue and land in P3):

- `verity_members`: Members, groups and owner functions kept in Verity (iam and onboarding modules).
- `learning_platform`: The training platform that assigns courses and records completion.
- `esignature`: The signing tool that holds signed agreements, such as DocuSign.
- `background_screening`: The screening provider that runs pre-hire checks, such as Checkr or Certn.
- `public_web`: Unauthenticated reads of the company's own public web pages (security.txt, trust page, terms).

## New Verity checks

Common outcomes: **pass** when every record in the population meets the predicate; **fail** lists each
record that does not; **error** (could not check) when a module read fails; **insufficient information**
where stated, when the population itself cannot be established. Settings named below are workspace
settings with the default shown. Every check keeps the records it judged as the evidence snapshot.

| Check | Capability | Population | Predicate | Empty population and other states | Frequency | Evidence kept | Controls (coverage: rationale) |
|---|---|---|---|---|---|---|---|
| `verity.assurance.internal_audit_held` | verity_controls | Internal audit assurance records on every current engagement. | At least one record is held or closed with an end date in the last 12 months, names who performed it (a member or an outside firm), has its independence confirmed by a member other than the performer, and, where the performer is a member, that member owns none of the live controls in scope. | No record: workspace fail. No current engagement: insufficient information, since records hang on an engagement. | daily | Record id, dates, performer, confirming member, count of controls the performer owns. | GOV-13 (partial): Shows an audit was held in time and by someone independent of the controls. Scope, criteria and what the report says stay with the uploaded report and the auditor's reading. |
| `verity.assurance.management_review_held` | verity_controls | Each calendar quarter of the SOC 2 Type 2 window, or of the last 12 months when there is no window. | Each quarter has a management review record, held or closed, dated inside the quarter, with at least one attendee or performer recorded. | No quarter covered: fail. The quarter in progress is judged only after it ends. | daily | Quarter, record id, date, attendees. | GOV-15 (partial): Shows the quarterly review took place. What it covered and decided stays in the minutes.; GOV-19 (partial): Places a review in each quarter; that the register was on its agenda stays in the minutes. |
| `verity.assurance.management_review_inputs_recorded` | verity_controls | Management review records held or closed in the last 12 months. | At least one record covers every input on the shipped management review list, each marked considered or not applicable with a note. | No record: fail. | daily | Record id and the input list with each state. | GOV-31 (partial): Shows the set inputs were taken into the yearly review. Whether top management judged the program sound is a person's conclusion.; GOV-15 (partial): Until GOV-31 is adopted, the yearly review sits on GOV-15. |
| `verity.assurance.findings_tracked` | verity_controls | Assurance findings (internal audit, management review, outside audit stage) open at any time in the last 12 months. | Every finding has an owner who is an active member, a due date and a linked task; a major or minor finding past its due date fails unless it is closed with closure evidence. | No findings: no result (nothing to verify). | daily | Finding id, grade, owner, due date, task id, closure evidence id. | GOV-13 (partial): Shows audit findings became owned, dated actions. Reporting to managers stays in the minutes.; GOV-08 (partial): Shows audit findings reached the deficiency log.; GOV-30 (partial): Shows improvement items from audits reached the log. |
| `verity.tasks.owned_and_dated` | verity_tasks | Open tasks and issues linked to a control, risk, assurance finding or vendor finding, or raised from a review, an improvement or a competence gap. | Each has an owner who is an active member and a due date or SLA date. | No such task: no result. | daily | Task code, kind, link, owner, due date. | GOV-08 (partial): Shows each logged deficiency has an owner and a due date. Root cause and containment stay in the task text.; GOV-15 (partial): Shows review actions are owned and dated.; GOV-30 (partial): Shows accepted improvements are owned and dated. The decision and reason stay with people.; GOV-14 (partial): Shows coverage gaps raised as tasks have an owner.; HR-09 (partial): Shows competence gap actions have an owner and date. |
| `verity.tasks.closure_evidenced` | verity_tasks | Tasks and issues linked to a control, risk or finding, closed in the last 92 days. | Each closed with a closure note and at least one attachment or linked evidence item; a critical or high issue also has each corrective action completed and verified by someone other than its owner. | Nothing closed: no result. | daily | Task code, closed date, closure note present, attachment count, action verification. | GOV-08 (partial): Shows closure rests on proof, not the owner's word. Whether the proof is adequate stays with the reviewer.; GOV-20 (partial): Shows each closed treatment action carries proof.; GOV-30 (partial): Shows improvements closed with evidence.; GOV-12 (partial): Shows fraud treatment actions closed with proof. |
| `verity.tasks.recurring_done_on_time` | verity_tasks | Recurring task series linked to a control, and their instances due in the last 12 months. | Each instance was closed by its due date plus the series grace (default 14 days) with a note or attachment. A cancelled instance counts as missed. | No series linked: no result, and the control falls back to the person's record. | daily | Series, instance due and closed dates, attachment count. | CS-07 (partial): Shows the yearly contact check ran. Whether each channel worked is the note on the task.; CS-08 (partial): Shows the threat feed review ran on its cadence.; GOV-02 (partial): Shows the oversight meeting happened on cadence. Challenge and decisions stay in the minutes.; GOV-10 (partial): Shows the quarterly briefing was given. Its content stays with people.; GOV-21 (partial): Shows the structure review ran.; GOV-24 (partial): Shows the factors review ran.; GOV-29 (partial): Shows planned activities were done on time. Whether each met its standard stays with people. |
| `verity.tasks.checklist_steps_done` | verity_tasks | Tasks started from a task template linked to HR-03, HR-05 or HR-06, created in the last 92 days. | The task is closed, every sub-task is closed, and each sub-task closed on or before its own due date; an open checklist older than the template's time limit fails. | No checklist task: no result. Who should have had one comes from the roster, not from this check. | daily | Task code, template, person named, sub-task states and dates. | HR-05 (partial): Shows each leaver checklist was finished on time. Return of devices is the sub-task's evidence.; HR-06 (partial): Shows each joiner checklist was finished on time.; HR-03 (partial): Shows contractor start and end checklists were finished. |
| `verity.checks.runs_continuous` | verity_controls | Every automated check enabled for a live in scope control, over the Type 2 window or the last 92 days. | No gap longer than two days between runs that produced a result for a daily check, or longer than one and a half times the frequency otherwise. A run that errored counts as a gap. | No check enabled: no result. | daily | Check, control, each gap with start, end and provider health. | GOV-06 (partial): Shows monitoring ran across the period and lists where it did not. What covered a gap stays a person's note. |
| `verity.controls.failed_checks_tracked` | verity_controls | Check results that moved from pass to fail on a live in scope control in the last 92 days. | Each failure has a linked remediation task created within two days (setting) with the control owner as owner, or the check passed again within that time. | No failures: no result. | daily | Check, control, failure time, task code and owner. | GOV-06 (partial): Shows failures reached the control owner as work. Fix time is tested by verity.tasks.remediation_in_sla. |
| `verity.members.leaver_ownership_moved` | verity_members | Memberships disabled in the last 92 days, from the audit trail. | Every live control, open risk, published document, active vendor and open task the member owned on the day they were disabled had a new owner who is an active member within five days (setting). | No leavers: no result. | daily | Member, disabled date, each owned record and the date it moved. | GOV-09 (partial): Shows ownership moved when someone left Verity. The leaving date in HR may differ, which the roster comparison covers.; HR-05 (partial): Shows the handover of owned compliance records for each leaver. |
| `verity.members.owner_functions_held` | verity_members | Owner functions mapped to at least one live control, plus the security lead and executive sponsor functions always. | Each is held by an active member today, and the security lead function had an active holder on every day of the last 92 days. | Functions never mapped: fail for the two required ones. | daily | Function, holder, holder history. | GOV-10 (partial): Shows the security lead role was held without a gap. The written appointment stays an upload.; GOV-21 (partial): Shows each role with security duties is held by a current member.; HR-09 (partial): Gives the list of people in security roles that competence records must cover. |
| `verity.risks.reviewed_after_change` | verity_risks | Change events Verity records in the last 92 days: vendors approved at tier critical or high or holding personal data, scope items added or decisions changed, assets put in service at high or critical criticality. | Each event has a risk in an active register created, rescored or reviewed and linked to that vendor, asset or scope item between 30 days before and 14 days after the event (settings). | No events: no result. The dated nil note stays a person's record. | daily | Event, date, linked risk, risk event date. | GOV-03 (partial): Sees only the changes Verity knows about. Architecture and hosting changes outside Verity stay with ticketing or people. |
| `verity.risks.acceptance_independent` | verity_risks | Risk acceptances decided in the last 12 months. | The approver is an active member other than the requester, a rationale is recorded, and the expiry is no more than 12 months (setting) after the decision. | No acceptances: no result. | daily | Acceptance id, risk, requester, approver, dates. | GOV-19 (partial): Shows accepted risks were approved by someone else with a reason and expiry. Whether the approver holds the right authority stays with people.; GOV-20 (partial): Shows remaining risk was accepted in writing by a second person.; GOV-07 (partial): Shows unmitigated risks carry an accepted decision. |
| `verity.risks.treatment_planned` | verity_risks | Open risks with treatment mitigate. | Each has a treatment plan text, a treatment due date, an owner who is an active member and a target residual likelihood and impact; a due date in the past while the risk is still in treatment fails as overdue. | No mitigated risks: no result. | daily | Risk code, plan present, due date, owner, residual target, overdue days. | GOV-20 (partial): Shows each mitigated risk has an owned, dated plan and flags overdue ones. Risk owner approval of the plan stays an approval on the task or an upload.; GOV-12 (partial): Applies to fraud risks too. |
| `verity.risks.scope_covered` | verity_risks | Scope items in scope for a current engagement of kind service, system or vendor; assets in service of high or critical criticality; vendors of tier critical. | Each is linked to at least one risk in an active register assessed in the last 12 months. | No scope items: insufficient information, since scope is not set. | daily | Item, kind, linked risk codes. | GOV-18 (partial): Shows the assessment reached the declared scope. A conclusion that an item carries no significant risk has no field and stays a person's note. |
| `verity.risks.fraud_assessed` | verity_risks | Active risk registers. | At least one open risk from a fraud or insider template of the risk library, or in a category marked fraud, is scored, was assessed in the last 12 months and links to a live control. | No such risk: workspace fail. | daily | Risk codes, template, score, assessed date, linked controls. | GOV-12 (partial): Shows fraud was considered and linked to controls. Incentive, opportunity and override reasoning stays in the assessment text. |
| `verity.soa.version_approved` | verity_frameworks | ISO 27001, when added. | The newest Statement of Applicability version was approved by an active member in the last 12 months, and no applicability decision changed after it was approved. | No approved version: fail. | daily | Version number, approver, date, decisions changed since. | GOV-27 (partial): Shows the version in use was approved and kept. One approver is recorded; sign off by each risk owner stays an upload. |
| `verity.soa.matches_risk_treatment` | verity_frameworks | Live controls linked to an open risk treated by mitigation, for ISO 27001. | Each such control maps to at least one Annex A requirement marked applicable, and no Annex A requirement marked not applicable maps only to such controls. | No mitigated risk with controls: no result. | daily | Control, risk codes, requirement keys and decisions. | GOV-27 (partial): Shows treatment and applicability agree. Whether each reason is specific stays a person's reading. |
| `verity.isms.scope_approved` | verity_frameworks | The current ISO 27001 engagement. | The scope statement was approved by a named active member in the last 12 months and has not changed since that approval. | No engagement: fail when ISO 27001 is active. | daily | Approver, approval date, last change date. | GOV-23 (partial): Shows the scope in use is the approved one. Approver seniority is not recorded. |
| `verity.scope.items_decided` | verity_frameworks | Scope suggestions (assets and vendors not yet scope items) and live scope items, for each current engagement. | No suggestion older than 30 days is undecided, and each live item has an in or out decision for each current engagement. | No engagement: insufficient information. | daily | Item or suggestion, age, decision per engagement. | GOV-14 (partial): Shows new assets and vendors are brought into the system list. Systems unknown to Verity stay with connectors and people.; GOV-23 (partial): Shows each new supplier or system got a scope decision.; GOV-22 (partial): Shows the description's scope keeps up with what Verity knows. |
| `verity.engagement.subservice_listed` | verity_frameworks | Approved, active vendors of tier critical or high, for the current SOC 2 engagement. | Each is an engagement vendor (a subservice organisation with its method, or a supplier), or was removed from the engagement with a reason. | No engagement: insufficient information. | daily | Vendor, tier, role, method. | GOV-22 (partial): Shows each critical supplier is accounted for in the description. Which controls each party operates stays in the description text. |
| `verity.commitments.owned_and_mapped` | verity_frameworks | Active commitments in the register. | The register holds at least one commitment from a contract and one from a published source; each has an owner who is an active member, a source reference, and points at a requirement or category. | No commitments: workspace fail. | daily | Commitment, source kind, reference, owner, points at. | CS-02 (partial): Shows the promises are registered and owned. That practice meets them stays the security lead's comparison.; GOV-22 (partial): Shows commitments are listed for the description.; GOV-05 (partial): Covers the contractual side of the obligations register.; CS-01 (partial): Holds the breach notice terms of contracts. |
| `verity.regulations.decided` | verity_frameworks | Reviewed country pack entries the reference panel shows as applying or likely to apply to the profile. | Each has a workspace decision; each one decided relevant was added to the obligations register; a decision made on an older profile version than the current one is listed as stale and fails. | No entries shown: no result. | daily | Regulation key, decision, register date, profile version. | GOV-05 (partial): Shows the laws the profile points to were decided. Laws outside the reviewed pack stay with legal. |
| `verity.policies.major_change_campaigned` | verity_policies | Major versions of published all staff or required documents published in the last 12 months. | Each was followed within 14 days (setting) by an acknowledgement campaign on that version targeting every active member, directly or through a role or group. | No major change: no result. | daily | Document, version, publish date, campaign, recipients. | CS-04 (partial): Shows material changes were announced to staff and re-acknowledged.; CS-06 (partial): Covers the policy change topic of the plan only. |
| `verity.policies.acknowledged_at_join` | verity_policies | Members who accepted their invitation in the last 12 months, guest auditors left out. | Each signed the current version of every all staff document within 14 days (setting) of accepting. | No joiners: no result. | daily | Member, accepted date, each document and signed date. | GOV-04 (partial): Shows joiners acknowledged the code soon after joining Verity. The employment start date may differ.; HR-06 (partial): Covers the policy step of the joiner checklist.; CS-04 (partial): Covers acknowledgement at hire.; HR-03 (partial): Covers contractors who are members. |
| `verity.documents.required_present` | verity_policies | Rows of the Required documents list for the frameworks the workspace runs and its profile (guided onboarding CL-5). | Each row's document exists, is published, was approved in the last 12 months (or approved elsewhere with a date), and has no placeholders left. One result per row. | No framework: no result. | daily | Row, template, document code, state, approval date. | GOV-17 (partial): Shows each required topic policy exists and is current.; GOV-28 (partial): Is the machine form of the list of documents the program needs.; GOV-32 (partial): Covers the policy statement row. |
| `verity.programme.periodic_on_track` | verity_frameworks | Live controls with an operating evidence item of monthly, quarterly or annual cadence, over the audit period (the programme periodic view). | Dated evidence found so far is at least the number of occurrences due by today. | No audit dates: insufficient information. | daily | Control, cadence, needed, found. | GOV-29 (partial): Shows recurring activities left records on schedule. Whether each met its standard stays with people. |
| `verity.vulns.pentest_in_12_months` | verity_vulnerabilities | Uploaded vulnerability reports of type penetration test. | At least one parsed report is dated in the last 12 months (setting). | No report: fail. | daily | Report id, date, finding count. | GOV-16 (partial): Shows a test was done in time. The tester's independence and the scope stay with the report. |
| `verity.vulns.pentest_fixes_verified` | verity_vulnerabilities | Critical and high findings from penetration test reports closed as fixed in the last 12 months. | Each has its fix verified, with a retest report or evidence attached. | No such findings: no result. | daily | Finding, severity, closed date, verified flag, attachment. | GOV-16 (partial): Shows fixed findings were retested. Open ones are judged by verity.vulns.within_sla. |
| `verity.training.acknowledged` | verity_policies | Active members, guest auditors left out; documents linked to HR-08 as training material. | Each member signed a campaign on the current training material in the last 12 months, and each member who joined in the period within 30 days (setting) of joining. | No training document linked: no result. | daily | Member, document, version, signed date. | HR-08 (partial): Records attendance or reading for training run in house. It does not show understanding, which HR-08.E asks for. |
| `verity.vendors.contractors_bounded` | verity_vendors | Active vendors of type contractor and their live engagements. | Each engagement has a sponsor who is an active member, a start date, an end date and systems in scope listed; none past its end date is still active. | No contractors: no result. | daily | Vendor, engagement, sponsor, dates, systems. | HR-03 (partial): Shows the register is complete in its fields and end dates are enforced on the record. Account removal on that date needs the identity provider. |

## Needs for connector research

| Capability | Phase | Predicate | Controls |
|---|---|---|---|
| alerting | P2 | messages posted in the named security announcement channel in the period, with date, author and channel (Slack) | CS-04, CS-06 |
| background_screening | P3 | every hire, move into a sensitive role and recheck in the period has a completed check with a clear result dated before the first access date, without the check details | HR-01 |
| esignature | P3 | every person who started in the period has a completed confidentiality agreement signed on or before the first access date | HR-02, HR-03 |
| hr_system | P3 | agreements signed in the HR system for each person, with agreement type and date signed | HR-02, HR-03 |
| hr_system | P3 | an annual review cycle is configured for every employee group | HR-07 |
| hr_system | P3 | certifications and training records for each person in a listed security role, dated | HR-09 |
| hr_system | P3 | contractors with company, sponsor, start date and end date | HR-02, HR-03 |
| hr_system | P3 | each person's title, department and manager, for the organization chart | GOV-21, HR-04, HR-07 |
| hr_system | P3 | every active person on the HR roster has a Verity membership, so acknowledgement and training cover the whole staff | CS-04, CS-05, CS-06, GOV-04, GOV-11, GOV-21, GOV-32, HR-03, HR-06, HR-07, HR-08 |
| hr_system | P3 | every active position has a job description, and the description has a security duties section | HR-04, HR-07, HR-09 |
| hr_system | P3 | every employee in post for the cycle has a completed performance review with reviewer and date | HR-07 |
| hr_system | P3 | every person who started, changed role or left in the period, with employment type, start date and end date | CS-04, GOV-04, GOV-09, GOV-21, HR-01, HR-02, HR-05, HR-06, HR-08 |
| hr_system | P3 | hires and moves into roles marked sensitive, with start dates, to compare with completed checks | HR-01 |
| identity_provider | P2 | accounts created and disabled in the period with their dates, to test the roster against | CS-04, GOV-04, GOV-09, GOV-21, HR-01, HR-02, HR-05, HR-06, HR-08 |
| identity_provider | P2 | each account is labelled employee, contractor or service, and each contractor account has an end date | HR-03 |
| identity_provider | P2 | each active user carries a title, department and manager, so the organization chart can be rebuilt from the directory | GOV-21, HR-04, HR-07 |
| identity_provider | P2 | each contractor account was disabled on or before the end date in the contractor register | HR-02, HR-03 |
| identity_provider | P2 | the published security reporting address is a group or shared mailbox with at least one active member | CS-03 |
| learning_platform | P3 | completions of the role modules by the people in each listed security role | HR-09 |
| learning_platform | P3 | every assigned person completed the yearly security course in the last 12 months, and each joiner within the set days of the start date | HR-03, HR-06, HR-07, HR-08 |
| learning_platform | P3 | overdue assignments with each reminder sent and the date of escalation | HR-03, HR-06, HR-07, HR-08 |
| learning_platform | P3 | the courses assigned in the period, with topics, audience and due rule | CS-03, HR-08 |
| public_web | P3 | security.txt is published at the company domain, has not expired and names a monitored contact | CS-03 |
| public_web | P3 | the security page, terms, service levels and privacy notice are reachable and dated, and each change in their text is recorded with the date seen | CS-02, GOV-22 |
| ticketing | P2 | changes marked significant (architecture, hosting, new data type, new supplier) link to a risk review dated before release | GOV-01, GOV-03, GOV-13 |
| ticketing | P2 | every joiner and leaver has an onboarding or offboarding ticket from the checklist template, closed with each step done and dated | GOV-09, HR-05, HR-06 |
| ticketing | P2 | every report to the security address opened a ticket with date, source, triage decision and closure date | CS-03 |
| ticketing | P2 | incident tickets in the period, with severity, detection date, closure date and the customer notice decision | CS-01, CS-03, CS-06, CS-07, GOV-08 |

## Control by control

### CS-01 Customer breach-notification commitment

SOC 2: CC2.3 (partial). ISO 27001:2022: none.

Decision: keep. Contract terms become structured commitments in the register, the plan is a document, and incidents need a register that Tasks can only approximate until the Incidents module exists.

Stays with people: The contract clauses themselves, the decision to notify, the notice sent. No system can prove: CS-01.A interview on who decides; CS-01.D that the right contacts got the notice in time.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `customer-contract-terms-on-breach-notification` | CS-01.A, CS-01.B, CS-01.D | person | compliance: Commitments register, contract source, breach notice [`verity.commitments.owned_and_mapped` NEW]; person: the standard agreement or DPA clause, and the list of contracts that differ | P1 |
| `incident-procedure-showing-the-notification-timeframes` | CS-01.A, CS-01.B | person | template `incident-response-plan`; documents: Policy register [`verity.policies.reviewed`]; person: comparison of the plan's timeframe with the shortest contractual one | P1 |
| `doc-incident-response-plan` | CS-01.A | document:incident-response-plan | template `incident-response-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `security-incident-register` | CS-01.C | person | tasks: Issues tagged as security incidents; `alerts.incidents_resolved` (alerting); NEED ticketing; incidents: Incident register (module signed for Phase 3.1, not built); person: dated nil return for a quarter with no incident | P1 |
| `notification-decisions-for-each-incident-including` | CS-01.C, CS-01.D | person | incidents: Incident register with notification decision (module signed for Phase 3.1, not built); NEED ticketing; person: decision recorded in each incident record or postmortem, including decisions not to notify | P2 |

### CS-02 External security commitments

SOC 2: CC2.3 (full), PI1.1 (partial). ISO 27001:2022: none.

Decision: revise_objectives. The Commitments register already holds each promise with its source and the requirements it bears on. A public web read can show the published pages and when they changed.

Stays with people: The comparison of each promise with practice, and approval before a change is published. No system can prove: CS-02.C and CS-02.D, a judgement that practice meets each promise.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `published-security-availability-and-privacy-commitments` | CS-02.A, CS-02.B, CS-02.D, CS-02.E, CS-02.F | person | compliance: Commitments register [`verity.commitments.owned_and_mapped` NEW]; template `privacy-notice-outline`; NEED public_web; person: copies of the published terms, service levels and security page, with their dates | P1 |
| `service-commitments-and-system-requirements-shared` | CS-02.B | person | compliance: Commitments register [`verity.commitments.owned_and_mapped` NEW]; compliance: System description facts per area; template `soc2-system-description` | P1 |
| `check-that-the-commitments-match-actual` | CS-02.C, CS-02.D, CS-02.E | person | compliance: Commitments register with the controls each points at [`verity.commitments.owned_and_mapped` NEW]; person: the security lead's dated comparison of each promise with practice, and the control or setting that meets it | P1 |
| `doc-processing-integrity-procedure` | CS-02.F | document:processing-integrity-procedure | template `processing-integrity-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |

### CS-03 Security incident reporting channel

SOC 2: CC2.2 (partial), CC2.3 (partial). ISO 27001:2022: A.5.24 (partial), A.6.8 (full).

Decision: revise_objectives. The channel is documented in templates; whether the address is monitored can be read from the identity provider, and security.txt from the public site. Reports need a ticket or Tasks convention.

Stays with people: Screenshots of the security page; the triage judgement; the interview. No system can prove: CS-03.D whether each report was routed correctly.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `published-reporting-channel-for-staff-and` | CS-03.A, CS-03.B | person | template `security-communication-plan`; template `incident-response-plan`; NEED public_web; NEED identity_provider; person: screenshot of the security page and staff handbook entry | P1 |
| `doc-incident-response-plan` | CS-03.A | document:incident-response-plan | template `incident-response-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-security-communication-plan` | CS-03.A | document:security-communication-plan | template `security-communication-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `training-content-and-schedule` | CS-03.B | person | template `competence-and-awareness-procedure`; NEED learning_platform; documents: Training material held as a document with review date [`verity.documents.controlled`] | P1 |
| `onboarding-checklist` | CS-03.B | person | template `joiner-mover-leaver-checklists`; tasks: Onboarding task template with one sub-task per step; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `sample-of-reports-received-and-how` | CS-03.C, CS-03.D | person | tasks: Issues raised from security reports; NEED ticketing; person: export of the shared inbox behind the security address | P1 |
| `security-incident-register` | CS-03.D | person | tasks: Issues tagged as security incidents; `alerts.incidents_resolved` (alerting); NEED ticketing; incidents: Incident register (module signed for Phase 3.1, not built); person: dated nil return for a quarter with no incident | P1 |

### CS-04 Internal policy portal

SOC 2: CC2.2 (partial). ISO 27001:2022: Cl. 5.2 (partial), Cl. 7.3 (partial), A.5.1 (partial), A.6.3 (partial).

Decision: keep. This is what Documents does: published versions, approval tiers and acknowledgement campaigns. The gap is staff who are not Verity members.

Stays with people: The roster comparison until an HR source exists; the interview on escalation. No system can prove: None of the core objectives; CS-04.E escalation needs an interview.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `policy-portal-showing-current-policies-available` | CS-04.A, CS-04.B | person | documents: Policy register, published versions [`verity.policies.reviewed`]; documents: Policy register [`verity.documents.controlled`]; person: screenshot or export where the record is kept outside Verity | P1 |
| `doc-information-security-policy` | CS-04.A | document:information-security-policy | template `information-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-information-security-policy-statement` | CS-04.A | document:information-security-policy-statement | template `information-security-policy-statement`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `published-security-policies-covering-each-required` | CS-04.B, CS-04.D | check:verity.policies.reviewed | documents: Policy register [`verity.policies.reviewed`]; documents: Required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.documents.controlled`] | P1 |
| `staff-acknowledgement-of-current-policies` | CS-04.C, CS-04.E | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; documents: Acknowledgement campaigns after major changes [`verity.policies.major_change_campaigned` NEW]; NEED hr_system | P1 |
| `roster-of-joiners-and-leavers-with` | CS-04.C | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `sample-of-messages-sent-under-the` | CS-04.D | person | documents: Acknowledgement campaigns after major policy changes [`verity.policies.major_change_campaigned` NEW]; NEED alerting; person: emails, newsletters and all hands slides | P1 |

### CS-05 Whistleblower / ethics reporting mechanism

SOC 2: CC1.1 (partial), CC2.2 (partial). ISO 27001:2022: none.

Decision: keep. Only the design is a document. The report log is kept out of Verity on purpose.

Stays with people: The anonymized log, the nil return, the independence of whoever handles each report. No system can prove: CS-05.C, CS-05.D and CS-05.E rest on a confidential log and interviews.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `description-of-the-confidential-reporting-mechanism` | CS-05.A, CS-05.B, CS-05.D | person | template `information-security-policy`; template `code-of-conduct`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-information-security-policy` | CS-05.A | document:information-security-policy | template `information-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `staff-acknowledgement-of-current-policies` | CS-05.B | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; documents: Acknowledgement campaigns after major changes [`verity.policies.major_change_campaigned` NEW]; NEED hr_system | P1 |
| `anonymized-log-of-reports-received-and` | CS-05.C, CS-05.D, CS-05.E | person | person: anonymized log kept by the person who receives reports, or the hotline export, with a dated nil return when empty | people-only |
| `minutes-showing-security-was-discussed-and` | CS-05.E | person | tasks: Recurring oversight meeting task with minutes attached [`verity.tasks.recurring_done_on_time` NEW]; template `oversight-body-charter`; person: the minutes, showing challenge and decisions | P1 |

### CS-06 Security communication plan

SOC 2: none. ISO 27001:2022: Cl. 7.4 (full), A.5.1 (partial).

Decision: keep. The plan is a document with a running check. Messages sent can come from Slack and from campaigns after major policy changes.

Stays with people: Emails, newsletters and slides; the check that messages were understood. No system can prove: CS-06.D whether messages were received and understood.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `security-communication-plan` | CS-06.A, CS-06.B, CS-06.D | check:verity.communication.plan_documented | template `security-communication-plan`; documents: Policy register [`verity.communication.plan_documented`] | P1 |
| `doc-security-communication-plan` | CS-06.A | document:security-communication-plan | template `security-communication-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `sample-of-messages-sent-under-the` | CS-06.B, CS-06.C | person | documents: Acknowledgement campaigns after major policy changes [`verity.policies.major_change_campaigned` NEW]; NEED alerting; person: emails, newsletters and all hands slides | P1 |
| `security-incident-register` | CS-06.C | person | tasks: Issues tagged as security incidents; `alerts.incidents_resolved` (alerting); NEED ticketing; incidents: Incident register (module signed for Phase 3.1, not built); person: dated nil return for a quarter with no incident | P1 |
| `staff-acknowledgement-of-current-policies` | CS-06.D | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; documents: Acknowledgement campaigns after major changes [`verity.policies.major_change_campaigned` NEW]; NEED hr_system | P1 |

### CS-07 Contacts with authorities and security communities

SOC 2: none. ISO 27001:2022: A.5.5 (full).

Decision: split. The contact list lives in the communication plan; the yearly contact check is a recurring task the template already names.

Stays with people: Each contact with an authority and the agreement given before it. No system can prove: CS-07.D that legal agreed before contact.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `contact-list-for-authorities-and-security` | CS-07.A, CS-07.C | person | template `security-communication-plan`; documents: Policy register [`verity.communication.plan_documented`] | P1 |
| `doc-security-communication-plan` | CS-07.A | document:security-communication-plan | template `security-communication-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `yearly-check-that-contact-details-still` | CS-07.C | person | tasks: Recurring yearly contact check task [`verity.tasks.recurring_done_on_time` NEW]; person: result of each check: date, who checked, what changed | P1 |
| `notification-decisions-for-each-incident-including` | CS-07.D | person | incidents: Incident register with notification decision (module signed for Phase 3.1, not built); NEED ticketing; person: decision recorded in each incident record or postmortem, including decisions not to notify | P2 |
| `security-incident-register` | CS-07.D | person | tasks: Issues tagged as security incidents; `alerts.incidents_resolved` (alerting); NEED ticketing; incidents: Incident register (module signed for Phase 3.1, not built); person: dated nil return for a quarter with no incident | P1 |

### CS-08 Security community memberships and advisories (proposed)

SOC 2: none. ISO 27001:2022: A.5.6 (full).

Decision: proposed successor of CS-07. Proposed successor. A recurring threat review task gives a cadence; the sources followed are a person's list.

Stays with people: The memberships and what was passed on. No system can prove: CS-08.B and CS-08.C, mostly people's records.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `memberships-or-subscriptions-to-security-communities` | CS-08.A, CS-08.B, CS-08.C | person | person: receipts, sign up emails or the list of feeds followed, with the owner of each | people-only |
| `doc-security-communication-plan` | CS-08.A | document:security-communication-plan | template `security-communication-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `log-of-threats-reviewed-and-actions` | CS-08.C | person | tasks: Recurring threat review task [`verity.tasks.recurring_done_on_time` NEW]; person: the log of items reviewed and actions taken | P1 |

### GOV-01 Annual policy review

SOC 2: CC5.3 (partial). ISO 27001:2022: Cl. 7.5.2 (partial), Cl. 7.5.3 (partial), A.5.1 (partial).

Decision: keep. Documents holds review dates, approvals and version history, and two checks already run on them.

Stays with people: How each review compared the policy with practice, and which business changes forced an early review. No system can prove: GOV-01.C, a comparison with practice.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-document-control-procedure` | GOV-01.A | document:document-control-procedure | template `document-control-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `review-and-re-approval-record-for` | GOV-01.B, GOV-01.C, GOV-01.E | check:verity.policies.reviewed | documents: Policy register [`verity.policies.reviewed`]; documents: Policy register with version history [`verity.documents.controlled`]; person: note on how each review compared the policy with practice | P1 |
| `published-security-policies-covering-each-required` | GOV-01.B | check:verity.policies.reviewed | documents: Policy register [`verity.policies.reviewed`]; documents: Required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.documents.controlled`] | P1 |
| `log-of-control-deficiencies-with-owner` | GOV-01.C | check:tickets.remediation_tracked, check:verity.tasks.remediation_in_sla | tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; tasks: Remediation tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Remediation tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing) | P1 |
| `version-history-and-approval-record-for` | GOV-01.D | check:verity.documents.controlled | documents: Policy register with version history [`verity.documents.controlled`] | P1 |
| `approval-record-for-each-policy` | GOV-01.D | person | documents: Policy register with approval tiers [`verity.documents.controlled`] | P1 |
| `risk-reviews-done-after-significant-changes` | GOV-01.E | person | risk: Risk events linked to vendors, assets and scope changes [`verity.risks.reviewed_after_change` NEW]; `tickets.changes_linked` (version_control+ticketing); NEED ticketing; person: dated nil note when no trigger occurred | P1 |

### GOV-02 Board / executive security oversight

SOC 2: CC1.2 (full). ISO 27001:2022: Cl. 5.1 (partial), Cl. 7.1 (partial).

Decision: keep. The charter is a template. Meetings can run as a recurring task with the minutes attached.

Stays with people: Minutes, membership and independence, challenge and decisions. No system can prove: GOV-02.B independence and GOV-02.D challenge.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `charter-of-the-board-or-executive` | GOV-02.A, GOV-02.C | person | template `oversight-body-charter`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-oversight-body-charter` | GOV-02.A, GOV-02.B | document:oversight-body-charter | template `oversight-body-charter`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `record-of-who-sits-on-the` | GOV-02.B | person | template `oversight-body-charter`; person: board register or member list with independence noted | P1 |
| `minutes-showing-security-was-discussed-and` | GOV-02.C, GOV-02.D, GOV-02.E | person | tasks: Recurring oversight meeting task with minutes attached [`verity.tasks.recurring_done_on_time` NEW]; template `oversight-body-charter`; person: the minutes, showing challenge and decisions | P1 |

### GOV-03 Change-triggered risk review

SOC 2: CC3.4 (full). ISO 27001:2022: Cl. 6.3 (partial), Cl. 8.2 (partial), A.5.8 (partial).

Decision: keep. Verity sees vendor, asset and scope changes and the risk events that follow; changes elsewhere need ticketing.

Stays with people: Which changes counted as significant; the nil note. No system can prove: GOV-03.E the yearly review of the trigger list (interview).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `procedure-listing-what-triggers-a-risk` | GOV-03.A, GOV-03.E | person | template `risk-assessment-methodology`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-risk-assessment-methodology` | GOV-03.A | document:risk-assessment-methodology | template `risk-assessment-methodology`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-change-management-procedure` | GOV-03.A | document:change-management-procedure | template `change-management-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `risk-reviews-done-after-significant-changes` | GOV-03.B, GOV-03.C, GOV-03.D | person | risk: Risk events linked to vendors, assets and scope changes [`verity.risks.reviewed_after_change` NEW]; `tickets.changes_linked` (version_control+ticketing); NEED ticketing; person: dated nil note when no trigger occurred | P1 |
| `change-requests-with-approval-for-a` | GOV-03.B, GOV-03.C | check:tickets.changes_linked, check:vcs.merged_changes_reviewed, person | `tickets.changes_linked` (version_control+ticketing); `vcs.merged_changes_reviewed` (version_control); NEED ticketing; person: which changes counted as significant, where no ticket field marks them | P2 |
| `vendor-inventory-with-owner-data-and` | GOV-03.B | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |
| `risk-register-with-owners-ratings-and` | GOV-03.D | check:verity.risks.treated | risk: Risk register [`verity.risks.treated`]; risk: Risk register [`verity.risks.reviewed`]; risk: Risk register [`verity.risks.controls_linked`]; risk: Risk register [`verity.risks.acceptance_current`] | P1 |

### GOV-04 Code of conduct and ethics policy

SOC 2: CC1.1 (partial). ISO 27001:2022: A.5.4 (partial), A.5.10 (partial), A.6.2 (partial), A.6.4 (partial).

Decision: keep. The code is a template and acknowledgement is a running check; joiners need the new at join check.

Stays with people: Breaches and their handling, approval by the chief executive. No system can prove: GOV-04.D breach handling.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `approved-code-of-conduct` | GOV-04.A | person | template `code-of-conduct`; documents: Policy register [`verity.policies.reviewed`]; person: confirmation that the approver is the chief executive or a founder, when the approval tier is a role | P1 |
| `doc-code-of-conduct` | GOV-04.A | document:code-of-conduct | template `code-of-conduct`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-acceptable-use-policy` | GOV-04.A | document:acceptable-use-policy | template `acceptable-use-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `acknowledgement-from-every-member-of-staff` | GOV-04.B, GOV-04.C | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; NEED hr_system; person: roster comparison for staff who are not Verity members | P1 |
| `roster-of-joiners-and-leavers-with` | GOV-04.B | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `doc-human-resource-security-policy` | GOV-04.C | document:human-resource-security-policy | template `human-resource-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `record-of-breaches-and-the-action` | GOV-04.D | person | person: private record kept by the chief executive or HR lead, with a dated nil return when empty | people-only |

### GOV-05 Compliance obligations register

SOC 2: CC2.3 (partial). ISO 27001:2022: Cl. 4.2 (partial), A.5.31 (full), A.5.32 (partial), A.5.34 (partial).

Decision: revise_objectives. Commitments, regulation decisions and active frameworks together are most of the register.

Stays with people: Licence terms, laws outside the reviewed pack, the yearly review. No system can prove: GOV-05.D the review interview.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `register-of-contractual-regulatory-and-certification` | GOV-05.A, GOV-05.B, GOV-05.C, GOV-05.E | person | compliance: Obligations: commitments, regulation decisions and active frameworks [`verity.commitments.owned_and_mapped` NEW]; regulations: Country reference panel with the workspace's decisions [`verity.regulations.decided` NEW]; template `context-and-interested-parties`; person: software licence and other contract terms not held in Verity | P1 |
| `doc-context-and-interested-parties` | GOV-05.A | document:context-and-interested-parties | template `context-and-interested-parties`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `service-commitments-and-system-requirements-shared` | GOV-05.C | person | compliance: Commitments register [`verity.commitments.owned_and_mapped` NEW]; compliance: System description facts per area; template `soc2-system-description` | P1 |
| `customer-contract-terms-on-breach-notification` | GOV-05.C | person | compliance: Commitments register, contract source, breach notice [`verity.commitments.owned_and_mapped` NEW]; person: the standard agreement or DPA clause, and the list of contracts that differ | P1 |
| `register-of-interested-parties-and-what` | GOV-05.C | check:verity.interested_parties.documented | template `context-and-interested-parties`; documents: Policy register [`verity.interested_parties.documented`]; compliance: Commitments register (customer requirements) [`verity.commitments.owned_and_mapped` NEW] | P1 |
| `review-of-the-register-for-new` | GOV-05.D | person | audit: Audit trail export filtered to commitments and regulation decisions (export exists); person: dated review note naming the sources checked | P1 |
| `review-record-covering-new-contracts-and` | GOV-05.D | person | documents: Version history of the context and interested parties register [`verity.interested_parties.documented`]; audit: Audit trail export filtered to commitments (export exists); person: dated note of what was checked | P1 |
| `vendor-inventory-with-owner-data-and` | GOV-05.E | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |

### GOV-06 Continuous control monitoring

SOC 2: CC4.1 (full). ISO 27001:2022: Cl. 9.1 (partial), A.5.36 (partial).

Decision: keep. This is Verity's own job: check runs, results and failures raised as tasks.

Stays with people: The review of repeated failures and how monitoring gaps were covered. No system can prove: GOV-06.D design weakness review.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-security-objectives-plan` | GOV-06.A | document:security-objectives-plan | template `security-objectives-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `control-test-results-across-the-observation` | GOV-06.B, GOV-06.E | person | compliance: Check run history per control [`verity.checks.runs_continuous` NEW]; compliance: Evidence currency [`verity.evidence.current`]; person: note on how each gap in monitoring was covered | P1 |
| `exceptions-found-by-monitoring-and-how` | GOV-06.C, GOV-06.D | person | tasks: Remediation tasks raised from failed checks [`verity.controls.failed_checks_tracked` NEW]; tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; `tickets.remediation_tracked` (ticketing); person: review note on checks that failed repeatedly | P1 |
| `log-of-control-deficiencies-with-owner` | GOV-06.C | check:tickets.remediation_tracked, check:verity.tasks.remediation_in_sla | tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; tasks: Remediation tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Remediation tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing) | P1 |
| `management-review-agenda-and-minutes` | GOV-06.D | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |

### GOV-07 Risk-to-control mapping

SOC 2: CC5.1 (partial). ISO 27001:2022: Cl. 6.1.3 (partial).

Decision: keep. Risk to control links already exist and a check runs on them.

Stays with people: The review of controls tied to no risk. No system can prove: GOV-07.D the review outcome.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-risk-assessment-methodology` | GOV-07.A | document:risk-assessment-methodology | template `risk-assessment-methodology`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-risk-management-policy` | GOV-07.A | document:risk-management-policy | template `risk-management-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `risks-linked-to-the-controls-that` | GOV-07.B, GOV-07.C, GOV-07.D, GOV-07.E | check:verity.risks.controls_linked | risk: Risk register with linked controls [`verity.risks.controls_linked`]; compliance: Controls with no linked risk (list for review, no pass or fail) | P1 |
| `risk-register-with-owners-ratings-and` | GOV-07.B | check:verity.risks.treated | risk: Risk register [`verity.risks.treated`]; risk: Risk register [`verity.risks.reviewed`]; risk: Risk register [`verity.risks.controls_linked`]; risk: Risk register [`verity.risks.acceptance_current`] | P1 |
| `approval-of-each-accepted-risk` | GOV-07.C | person | risk: Risk register, acceptances [`verity.risks.acceptance_current`]; risk: Risk register, acceptances [`verity.risks.acceptance_independent` NEW] | P1 |

### GOV-08 Deficiency remediation tracking

SOC 2: CC4.2 (full). ISO 27001:2022: Cl. 10.2 (full).

Decision: revise_objectives. Tasks, SLAs, corrective actions and assurance findings hold the log; Jira can supply it instead.

Stays with people: Containment notes, root cause quality, telling leadership, the wider check. No system can prove: GOV-08.F whether the cause showed a wider gap.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-corrective-action-procedure` | GOV-08.A | document:corrective-action-procedure | template `corrective-action-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `log-of-control-deficiencies-with-owner` | GOV-08.B, GOV-08.C, GOV-08.D, GOV-08.E, GOV-08.F | check:tickets.remediation_tracked, check:verity.tasks.remediation_in_sla | tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; tasks: Remediation tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Remediation tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing) | P1 |
| `internal-audit-or-readiness-assessment-report` | GOV-08.B | check:verity.audit.internal_in_12_months, person | compliance: Assurance records, internal audit [`verity.assurance.internal_audit_held` NEW]; compliance: Evidence on the internal audit control [`verity.audit.internal_in_12_months`]; person: the audit report itself, with scope, criteria, evidence examined and findings | P1 |
| `security-incident-register` | GOV-08.B | person | tasks: Issues tagged as security incidents; `alerts.incidents_resolved` (alerting); NEED ticketing; incidents: Incident register (module signed for Phase 3.1, not built); person: dated nil return for a quarter with no incident | P1 |
| `communication-of-deficiencies-to-the-people` | GOV-08.C | person | tasks: Remediation tasks with assignment notifications [`verity.tasks.owned_and_dated` NEW]; `tickets.remediation_tracked` (ticketing); person: minutes or message showing leadership was told | P1 |
| `management-review-agenda-and-minutes` | GOV-08.E, GOV-08.F | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |

### GOV-09 Assigned control ownership (RACI)

SOC 2: CC1.3 (partial), CC1.5 (partial). ISO 27001:2022: Cl. 5.3 (partial), A.5.2 (partial).

Decision: keep. Controls carry owners; the audit trail shows changes.

Stays with people: Owners' understanding of what they own. No system can prove: GOV-09.D interview.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-information-security-roles-and-responsibilities` | GOV-09.A | document:information-security-roles-and-responsibilities | template `information-security-roles-and-responsibilities`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `control-ownership-register` | GOV-09.A, GOV-09.B, GOV-09.D | check:verity.controls.owned | compliance: Control gap report with owners (export exists) [`verity.controls.owned`] | P1 |
| `updated-ownership-when-roles-change` | GOV-09.C, GOV-09.D | person | audit: Audit trail of control owner changes (export exists); iam: Ownership moved from leavers [`verity.members.leaver_ownership_moved` NEW] | P1 |
| `roster-of-joiners-and-leavers-with` | GOV-09.C | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `completed-offboarding-records-for-leavers-in` | GOV-09.C | person | tasks: Leaver checklist tasks from the offboarding task template [`verity.tasks.checklist_steps_done` NEW]; iam: Ownership moved from leavers [`verity.members.leaver_ownership_moved` NEW]; `people.leavers_deprovisioned` (hr_system+identity_provider); NEED ticketing; person: record of devices and tokens returned or wiped, and the leaver's acknowledgement of continuing duties | P1 |

### GOV-10 Designated security officer

SOC 2: CC1.3 (partial), CC1.5 (partial). ISO 27001:2022: Cl. 5.1 (partial), Cl. 5.3 (partial), A.5.2 (partial).

Decision: keep. Owner functions show who holds the security lead role and since when.

Stays with people: The written appointment, the briefings and leadership's answers. No system can prove: GOV-10.B regulator independence and GOV-10.D follow through.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `appointment-or-role-charter-naming-the` | GOV-10.A, GOV-10.B | person | template `information-security-roles-and-responsibilities`; onboarding: Owner functions and who holds them, with change history [`verity.members.owner_functions_held` NEW]; person: signed appointment memo or email from the chief executive naming the officer and deputy | P1 |
| `doc-information-security-roles-and-responsibilities` | GOV-10.A | document:information-security-roles-and-responsibilities | template `information-security-roles-and-responsibilities`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `report-or-briefing-from-the-security` | GOV-10.C, GOV-10.D | person | tasks: Recurring quarterly briefing task with the briefing attached [`verity.tasks.recurring_done_on_time` NEW]; compliance: Control gap report as briefing input (export exists); person: the briefing and the decisions it asked for | P1 |
| `management-review-agenda-and-minutes` | GOV-10.D | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |

### GOV-11 Documented disciplinary process

SOC 2: CC1.1 (partial), CC1.5 (partial). ISO 27001:2022: Cl. 7.3 (partial), A.5.4 (partial), A.6.4 (full).

Decision: keep. Only the design is a document.

Stays with people: Cases, outcomes, consistency, where records are kept. No system can prove: GOV-11.C, GOV-11.D and GOV-11.E.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `disciplinary-procedure` | GOV-11.A | person | template `human-resource-security-policy`; template `code-of-conduct`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-human-resource-security-policy` | GOV-11.A | document:human-resource-security-policy | template `human-resource-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-code-of-conduct` | GOV-11.B | document:code-of-conduct | template `code-of-conduct`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `acknowledgement-from-every-member-of-staff` | GOV-11.B | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; NEED hr_system; person: roster comparison for staff who are not Verity members | P1 |
| `sample-of-cases-showing-the-procedure` | GOV-11.C, GOV-11.D, GOV-11.E | person | person: case list kept by HR, shown to the auditor in a private session | people-only |
| `record-of-breaches-and-the-action` | GOV-11.D | person | person: private record kept by the chief executive or HR lead, with a dated nil return when empty | people-only |

### GOV-12 Fraud and insider-threat consideration

SOC 2: CC3.3 (full). ISO 27001:2022: none.

Decision: keep. The risk library ships fraud templates, so a check can find fraud risks and their links.

Stays with people: The reasoning on incentive and override, proof that actions are live. No system can prove: GOV-12.D finance interview.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-risk-assessment-methodology` | GOV-12.A | document:risk-assessment-methodology | template `risk-assessment-methodology`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `fraud-risk-assessment-covering-insider-misuse` | GOV-12.B, GOV-12.C | person | risk: Risk register filtered to fraud and insider risks [`verity.risks.fraud_assessed` NEW]; risk: Risk register [`verity.risks.controls_linked`] | P1 |
| `risk-assessment-report-with-method-and` | GOV-12.B | check:verity.risks.assessed_in_12_months | risk: Risk register report, dated [`verity.risks.assessed_in_12_months`]; risk: Risk register [`verity.risks.scope_covered` NEW]; risk: Risk register [`verity.risks.reviewed`] | P1 |
| `risks-linked-to-the-controls-that` | GOV-12.C | check:verity.risks.controls_linked | risk: Risk register with linked controls [`verity.risks.controls_linked`]; compliance: Controls with no linked risk (list for review, no pass or fail) | P1 |
| `actions-taken-on-the-fraud-risks` | GOV-12.D | person | tasks: Treatment tasks linked to fraud risks [`verity.tasks.closure_evidenced` NEW]; risk: Risk register filtered to fraud risks [`verity.risks.treatment_planned` NEW]; person: proof the change is live, such as the two person payment approval setting in the bank or finance tool | P1 |
| `approval-of-each-accepted-risk` | GOV-12.D | person | risk: Risk register, acceptances [`verity.risks.acceptance_current`]; risk: Risk register, acceptances [`verity.risks.acceptance_independent` NEW] | P1 |

### GOV-13 Internal audit

SOC 2: CC4.1 (partial), P8.1 (partial). ISO 27001:2022: Cl. 9.2.1 (full), Cl. 9.2.2 (full), A.5.35 (full), A.5.36 (partial).

Decision: revise_objectives. Assurance records hold who audited, independence confirmation and findings with tasks.

Stays with people: The report, its scope and criteria; independence judgement. No system can prove: GOV-13.C independence (interview).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `internal-audit-program-setting-frequency-methods` | GOV-13.A, GOV-13.B, GOV-13.F | person | template `internal-audit-procedure`; compliance: Assurance records planned for the cycle; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-internal-audit-procedure` | GOV-13.A, GOV-13.F | document:internal-audit-procedure | template `internal-audit-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `internal-audit-or-readiness-assessment-report` | GOV-13.B, GOV-13.C, GOV-13.E | check:verity.audit.internal_in_12_months, person | compliance: Assurance records, internal audit [`verity.assurance.internal_audit_held` NEW]; compliance: Evidence on the internal audit control [`verity.audit.internal_in_12_months`]; person: the audit report itself, with scope, criteria, evidence examined and findings | P1 |
| `control-ownership-register` | GOV-13.C | check:verity.controls.owned | compliance: Control gap report with owners (export exists) [`verity.controls.owned`] | P1 |
| `remediation-plan-for-the-gaps-found` | GOV-13.D | person | compliance: Assurance findings with linked tasks [`verity.assurance.findings_tracked` NEW]; tasks: Remediation tasks [`verity.tasks.remediation_in_sla`] | P1 |
| `management-review-agenda-and-minutes` | GOV-13.D | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |
| `log-of-control-deficiencies-with-owner` | GOV-13.D | check:tickets.remediation_tracked, check:verity.tasks.remediation_in_sla | tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; tasks: Remediation tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Remediation tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing) | P1 |
| `risk-reviews-done-after-significant-changes` | GOV-13.E | person | risk: Risk events linked to vendors, assets and scope changes [`verity.risks.reviewed_after_change` NEW]; `tickets.changes_linked` (version_control+ticketing); NEED ticketing; person: dated nil note when no trigger occurred | P1 |

### GOV-14 IT general controls coverage

SOC 2: CC5.2 (partial). ISO 27001:2022: Cl. 8.1 (partial).

Decision: keep. Scope items, assets and the trace view give the system list and its controls.

Stays with people: The coverage review sheet; systems Verity does not know. No system can prove: GOV-14.C the review judgement.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `inventory-of-in-scope-systems-and` | GOV-14.A, GOV-14.B | person | compliance: Scope items and decisions per engagement [`verity.scope.items_decided` NEW]; assets: Asset inventory filtered to compliance scope [`verity.assets.owner_assigned`]; `assets.resources_registered` (asset_discovery); person: mapping of each system to its access, change and operations controls | P1 |
| `doc-soc2-system-description` | GOV-14.A | document:soc2-system-description | template `soc2-system-description`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `asset-inventory` | GOV-14.B | check:verity.assets.owner_assigned, check:assets.resources_registered | assets: Asset inventory [`verity.assets.owner_assigned`]; assets: Asset inventory [`verity.assets.reviewed`]; `assets.resources_registered` (asset_discovery) | P1 |
| `vendor-inventory-with-owner-data-and` | GOV-14.B | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |
| `applications-inside-and-outside-single-sign-on` | GOV-14.B | person | `idp.sso_enforced` (identity_provider); `idp.connected_apps_known` (identity_provider); vendors: Vendor register and discovered applications [`verity.vendors.owner_and_tier`]; person: expense or card statement review for tools bought outside procurement | P1 |
| `review-that-every-system-is-covered` | GOV-14.C, GOV-14.D | person | linkage: Trace view from each in scope system to its controls; tasks: Coverage gap tasks [`verity.tasks.owned_and_dated` NEW]; person: the security lead's dated review sheet | P1 |
| `log-of-control-deficiencies-with-owner` | GOV-14.D | check:tickets.remediation_tracked, check:verity.tasks.remediation_in_sla | tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; tasks: Remediation tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Remediation tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing) | P1 |

### GOV-15 Periodic management review of security

SOC 2: CC1.2 (partial), CC4.2 (partial). ISO 27001:2022: Cl. 5.1 (partial), Cl. 9.1 (partial), A.5.36 (partial).

Decision: split. Assurance records of kind management review give dates and attendees; actions are tasks.

Stays with people: Minutes and decisions. No system can prove: GOV-15.B content of the review.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-management-review-procedure` | GOV-15.A | document:management-review-procedure | template `management-review-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `management-review-agenda-and-minutes` | GOV-15.B, GOV-15.D | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |
| `actions-raised-in-the-review-and` | GOV-15.D, GOV-15.E | person | tasks: Remediation tasks raised from management review [`verity.tasks.owned_and_dated` NEW]; compliance: Assurance findings on the management review record [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing); person: escalation to the oversight body of items open across two reviews | P1 |
| `minutes-showing-security-was-discussed-and` | GOV-15.E | person | tasks: Recurring oversight meeting task with minutes attached [`verity.tasks.recurring_done_on_time` NEW]; template `oversight-body-charter`; person: the minutes, showing challenge and decisions | P1 |

### GOV-16 Annual penetration test

SOC 2: CC4.1 (partial), CC7.1 (partial). ISO 27001:2022: A.5.35 (partial), A.8.29 (partial), A.8.34 (partial).

Decision: keep. Penetration test reports upload into Vulnerabilities, whose findings run on SLA.

Stays with people: Rules of engagement, tester independence, the retest letter. No system can prove: GOV-16.B signed rules of engagement; GOV-16.C independence.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `vulnerability-management-policy-with-timeframes` | GOV-16.A | person | template `operations-security-policy`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-operations-security-policy` | GOV-16.A | document:operations-security-policy | template `operations-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `rules-of-engagement-agreed-in-writing` | GOV-16.B | person | person: scope letter or statement of work signed with the testing firm, attached to its vendor record | people-only |
| `penetration-test-report-from-an-independent` | GOV-16.C, GOV-16.E | person | vulnerabilities: Uploaded penetration test reports [`verity.vulns.pentest_in_12_months` NEW]; person: the report, and a note on the tester's independence and the scope tested | P1 |
| `remediation-of-findings-with-retest-evidence` | GOV-16.D, GOV-16.E | person | vulnerabilities: Vulnerability SLA, penetration test findings [`verity.vulns.within_sla`]; vulnerabilities: Penetration test findings closed as fixed [`verity.vulns.pentest_fixes_verified` NEW]; person: the tester's retest letter or report | P1 |
| `vulnerability-register-with-remediation-and-accepted` | GOV-16.D | check:verity.vulns.within_sla | vulnerabilities: Vulnerability SLA [`verity.vulns.within_sla`]; vulnerabilities: Penetration test findings [`verity.vulns.pentest_fixes_verified` NEW] | P1 |

### GOV-17 Security policy suite

SOC 2: CC5.3 (full). ISO 27001:2022: A.5.1 (partial), A.5.10 (partial), A.5.19 (partial), A.5.23 (partial), A.6.7 (partial), A.7.7 (partial), A.7.9 (partial).

Decision: split. Documents hold the suite with approvals; the required list check makes sure each topic exists.

Stays with people: Observation that staff can reach the policies. No system can prove: None beyond observation.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `published-security-policies-covering-each-required` | GOV-17.B, GOV-17.C, GOV-17.D | check:verity.policies.reviewed | documents: Policy register [`verity.policies.reviewed`]; documents: Required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.documents.controlled`] | P1 |
| `doc-information-security-policy` | GOV-17.B | document:information-security-policy | template `information-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-access-control-policy` | GOV-17.B | document:access-control-policy | template `access-control-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-change-management-procedure` | GOV-17.B | document:change-management-procedure | template `change-management-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-incident-response-plan` | GOV-17.B | document:incident-response-plan | template `incident-response-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-business-continuity-and-disaster-recovery-plan` | GOV-17.B | document:business-continuity-and-disaster-recovery-plan | template `business-continuity-and-disaster-recovery-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-third-party-management-policy` | GOV-17.B | document:third-party-management-policy | template `third-party-management-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-cloud-services-security-policy` | GOV-17.B | document:cloud-services-security-policy | template `cloud-services-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-acceptable-use-policy` | GOV-17.B | document:acceptable-use-policy | template `acceptable-use-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-engineering-security-standard` | GOV-17.B | document:engineering-security-standard | template `engineering-security-standard`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-data-management-policy` | GOV-17.B | document:data-management-policy | template `data-management-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-secure-development-policy` | GOV-17.B | document:secure-development-policy | template `secure-development-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `approval-record-for-each-policy` | GOV-17.C | person | documents: Policy register with approval tiers [`verity.documents.controlled`] | P1 |

### GOV-18 Annual risk assessment

SOC 2: CC3.1 (partial), CC3.2 (full). ISO 27001:2022: Cl. 6.1.1 (partial), Cl. 6.1.2 (partial), Cl. 8.2 (partial).

Decision: keep. The Risk module holds the register, scoring and review dates; scope coverage can be checked against scope items and assets.

Stays with people: Leadership sign off and the conclusion where an item has no significant risk. No system can prove: GOV-18.E sign off (signature).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-risk-assessment-methodology` | GOV-18.A | document:risk-assessment-methodology | template `risk-assessment-methodology`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-risk-management-policy` | GOV-18.A | document:risk-management-policy | template `risk-management-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `risk-assessment-report-with-method-and` | GOV-18.B, GOV-18.C, GOV-18.D | check:verity.risks.assessed_in_12_months | risk: Risk register report, dated [`verity.risks.assessed_in_12_months`]; risk: Risk register [`verity.risks.scope_covered` NEW]; risk: Risk register [`verity.risks.reviewed`] | P1 |
| `asset-inventory` | GOV-18.B | check:verity.assets.owner_assigned, check:assets.resources_registered | assets: Asset inventory [`verity.assets.owner_assigned`]; assets: Asset inventory [`verity.assets.reviewed`]; `assets.resources_registered` (asset_discovery) | P1 |
| `vendor-inventory-with-owner-data-and` | GOV-18.B | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |
| `doc-isms-scope-statement` | GOV-18.B | document:isms-scope-statement | template `isms-scope-statement`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-soc2-system-description` | GOV-18.B | document:soc2-system-description | template `soc2-system-description`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `risk-register-with-owners-ratings-and` | GOV-18.C | check:verity.risks.treated | risk: Risk register [`verity.risks.treated`]; risk: Risk register [`verity.risks.reviewed`]; risk: Risk register [`verity.risks.controls_linked`]; risk: Risk register [`verity.risks.acceptance_current`] | P1 |
| `management-sign-off-on-the-assessment` | GOV-18.E | person | documents: Approval tier on the exported risk assessment report [`verity.documents.controlled`]; person: signed memo or minute from the chief executive | P1 |
| `management-review-agenda-and-minutes` | GOV-18.E | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |
| `treatment-plan-with-owners-and-due` | GOV-18.E | person | risk: Risk register, treatment plan and due date [`verity.risks.treatment_planned` NEW]; tasks: Treatment tasks linked to risks [`verity.tasks.owned_and_dated` NEW] | P1 |

### GOV-19 Risk register with treatment decisions

SOC 2: CC3.2 (partial), CC5.1 (partial). ISO 27001:2022: Cl. 6.1.1 (partial), Cl. 6.1.2 (partial), Cl. 6.1.3 (partial), Cl. 8.3 (partial).

Decision: keep. Acceptances already record requester, approver and expiry.

Stays with people: Whether the approver held the right authority. No system can prove: None of the core objectives.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-risk-assessment-methodology` | GOV-19.A | document:risk-assessment-methodology | template `risk-assessment-methodology`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-risk-management-policy` | GOV-19.A | document:risk-management-policy | template `risk-management-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `risk-register-with-owners-ratings-and` | GOV-19.B, GOV-19.C, GOV-19.D | check:verity.risks.treated | risk: Risk register [`verity.risks.treated`]; risk: Risk register [`verity.risks.reviewed`]; risk: Risk register [`verity.risks.controls_linked`]; risk: Risk register [`verity.risks.acceptance_current`] | P1 |
| `management-review-agenda-and-minutes` | GOV-19.C | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |
| `approval-of-each-accepted-risk` | GOV-19.D | person | risk: Risk register, acceptances [`verity.risks.acceptance_current`]; risk: Risk register, acceptances [`verity.risks.acceptance_independent` NEW] | P1 |

### GOV-20 Risk treatment plan

SOC 2: CC3.2 (partial), CC9.1 (partial). ISO 27001:2022: Cl. 6.1.1 (partial), Cl. 6.1.3 (partial), Cl. 8.3 (full).

Decision: revise_objectives. Risks carry a treatment plan and due date; treatment work is tasks with approval status.

Stays with people: Proof that each treatment is live, and the acceptance of what remains. No system can prove: GOV-20.D the decision to accept the remaining risk.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-risk-management-policy` | GOV-20.A | document:risk-management-policy | template `risk-management-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-risk-assessment-methodology` | GOV-20.A | document:risk-assessment-methodology | template `risk-assessment-methodology`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `treatment-plan-with-owners-and-due` | GOV-20.B, GOV-20.E, GOV-20.F | person | risk: Risk register, treatment plan and due date [`verity.risks.treatment_planned` NEW]; tasks: Treatment tasks linked to risks [`verity.tasks.owned_and_dated` NEW] | P1 |
| `risk-register-with-owners-ratings-and` | GOV-20.B, GOV-20.D, GOV-20.F | check:verity.risks.treated | risk: Risk register [`verity.risks.treated`]; risk: Risk register [`verity.risks.reviewed`]; risk: Risk register [`verity.risks.controls_linked`]; risk: Risk register [`verity.risks.acceptance_current`] | P1 |
| `risk-owner-approval-of-each-treatment-plan` | GOV-20.B | person | tasks: Treatment tasks requiring approval by the risk owner; risk: Risk register [`verity.risks.treatment_planned` NEW]; person: email or signed note where the plan is approved outside Verity | P1 |
| `evidence-that-treatments-were-completed` | GOV-20.C, GOV-20.D | person | tasks: Treatment tasks linked to risks [`verity.tasks.closure_evidenced` NEW]; `tickets.remediation_tracked` (ticketing); person: the screenshot, ticket or setting change that proves each treatment | P1 |
| `risk-owner-acceptance-of-the-remaining` | GOV-20.D | person | risk: Risk register, acceptances [`verity.risks.acceptance_current`]; risk: Risk register, acceptances [`verity.risks.acceptance_independent` NEW]; person: confirmation that the risk was rated again only after treatment was shown | P1 |
| `management-review-agenda-and-minutes` | GOV-20.E | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |

### GOV-21 Organizational structure and reporting lines

SOC 2: CC1.3 (partial). ISO 27001:2022: Cl. 5.3 (partial), A.5.2 (partial).

Decision: revise_objectives. Owner functions and an identity provider's manager field approximate the chart.

Stays with people: The chart, role descriptions, reviews of the structure. No system can prove: GOV-21.B absence of conflict of interest.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `current-organization-chart-with-reporting-lines` | GOV-21.A, GOV-21.B, GOV-21.D | person | NEED identity_provider; NEED hr_system; onboarding: Owner functions and who holds them [`verity.members.owner_functions_held` NEW]; person: chart kept by the chief executive when no system holds reporting lines | P2 |
| `role-descriptions-for-security-and-compliance` | GOV-21.A, GOV-21.D, GOV-21.E | person | template `information-security-roles-and-responsibilities`; onboarding: Owner functions and who holds them [`verity.members.owner_functions_held` NEW] | P1 |
| `doc-information-security-roles-and-responsibilities` | GOV-21.A | document:information-security-roles-and-responsibilities | template `information-security-roles-and-responsibilities`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `appointment-or-role-charter-naming-the` | GOV-21.B | person | template `information-security-roles-and-responsibilities`; onboarding: Owner functions and who holds them, with change history [`verity.members.owner_functions_held` NEW]; person: signed appointment memo or email from the chief executive naming the officer and deputy | P1 |
| `minutes-where-the-board-or-leadership` | GOV-21.C | person | tasks: Recurring structure review task [`verity.tasks.recurring_done_on_time` NEW]; person: minutes of the review and the changes agreed | P1 |
| `roster-of-joiners-and-leavers-with` | GOV-21.D | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `staff-acknowledgement-of-current-policies` | GOV-21.E | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; documents: Acknowledgement campaigns after major changes [`verity.policies.major_change_campaigned` NEW]; NEED hr_system | P1 |

### GOV-22 System description and service commitments

SOC 2: CC3.1 (full). ISO 27001:2022: Cl. 4.3 (partial).

Decision: keep. The description is a template, with facts per area from the description service and subservice organisations from the engagement.

Stays with people: Writing and approving the description; complementary controls. No system can prove: GOV-22.A that the description is accurate.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `system-description-covering-boundary-services-infrastructure` | GOV-22.A, GOV-22.C, GOV-22.D | person | template `soc2-system-description`; compliance: System description facts per area; compliance: Engagement vendors (subservice organisations) [`verity.engagement.subservice_listed` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-soc2-system-description` | GOV-22.A | document:soc2-system-description | template `soc2-system-description`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `service-commitments-and-system-requirements-shared` | GOV-22.B | person | compliance: Commitments register [`verity.commitments.owned_and_mapped` NEW]; compliance: System description facts per area; template `soc2-system-description` | P1 |
| `published-security-availability-and-privacy-commitments` | GOV-22.B | person | compliance: Commitments register [`verity.commitments.owned_and_mapped` NEW]; template `privacy-notice-outline`; NEED public_web; person: copies of the published terms, service levels and security page, with their dates | P1 |
| `vendor-inventory-with-owner-data-and` | GOV-22.C, GOV-22.D | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |
| `asset-inventory` | GOV-22.D | check:verity.assets.owner_assigned, check:assets.resources_registered | assets: Asset inventory [`verity.assets.owner_assigned`]; assets: Asset inventory [`verity.assets.reviewed`]; `assets.resources_registered` (asset_discovery) | P1 |

### GOV-23 ISMS scope and boundaries

SOC 2: none. ISO 27001:2022: Cl. 4.3 (full), Cl. 4.4 (partial).

Decision: keep. Scope statement document, engagement scope with approval, and scope items with decisions.

Stays with people: Process map and the scope review notes. No system can prove: GOV-23.A leadership approval (judgement of fit).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `scope-statement-approved-by-leadership` | GOV-23.A, GOV-23.B, GOV-23.E | check:verity.isms.scope_documented, check:verity.isms.scope_recorded | template `isms-scope-statement`; documents: Policy register [`verity.isms.scope_documented`]; compliance: Engagement scope statement [`verity.isms.scope_recorded`]; compliance: Engagement scope statement approval [`verity.isms.scope_approved` NEW] | P1 |
| `doc-isms-scope-statement` | GOV-23.A | document:isms-scope-statement | template `isms-scope-statement`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `register-of-external-and-internal-factors` | GOV-23.B | check:verity.context.documented | template `context-and-interested-parties`; documents: Policy register [`verity.context.documented`] | P1 |
| `register-of-interested-parties-and-what` | GOV-23.B | check:verity.interested_parties.documented | template `context-and-interested-parties`; documents: Policy register [`verity.interested_parties.documented`]; compliance: Commitments register (customer requirements) [`verity.commitments.owned_and_mapped` NEW] | P1 |
| `map-of-the-management-processes-and` | GOV-23.C | person | template `isms-operating-plan`; person: diagram of the processes and what each hands to the next | P1 |
| `scope-review-after-changes-to-products` | GOV-23.D | person | compliance: Scope items, decisions and changes in the period [`verity.scope.items_decided` NEW]; person: dated note recording whether the scope changed and who approved it | P1 |
| `vendor-inventory-with-owner-data-and` | GOV-23.D | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |
| `version-history-and-approval-record-for` | GOV-23.E | check:verity.documents.controlled | documents: Policy register with version history [`verity.documents.controlled`] | P1 |

### GOV-24 Internal and external factors register

SOC 2: none. ISO 27001:2022: Cl. 4.1 (full).

Decision: keep. Template with a running check.

Stays with people: The climate decision and what each factor led to. No system can prove: GOV-24.B and GOV-24.D.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `register-of-external-and-internal-factors` | GOV-24.A, GOV-24.B | check:verity.context.documented | template `context-and-interested-parties`; documents: Policy register [`verity.context.documented`] | P1 |
| `doc-context-and-interested-parties` | GOV-24.A | document:context-and-interested-parties | template `context-and-interested-parties`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `yearly-review-notes-and-decisions-taken` | GOV-24.C, GOV-24.D | person | documents: Version history of the context register [`verity.context.documented`]; tasks: Recurring yearly review task [`verity.tasks.recurring_done_on_time` NEW]; person: notes of what was added or changed | P1 |
| `version-history-and-approval-record-for` | GOV-24.C | check:verity.documents.controlled | documents: Policy register with version history [`verity.documents.controlled`] | P1 |
| `risk-assessment-report-with-method-and` | GOV-24.D | check:verity.risks.assessed_in_12_months | risk: Risk register report, dated [`verity.risks.assessed_in_12_months`]; risk: Risk register [`verity.risks.scope_covered` NEW]; risk: Risk register [`verity.risks.reviewed`] | P1 |
| `security-objectives-with-owners-targets-and` | GOV-24.D | check:verity.objectives.documented | template `security-objectives-plan`; documents: Policy register [`verity.objectives.documented`]; tasks: One task per objective with its target [`verity.tasks.owned_and_dated` NEW] | P1 |
| `scope-statement-approved-by-leadership` | GOV-24.D | check:verity.isms.scope_documented, check:verity.isms.scope_recorded | template `isms-scope-statement`; documents: Policy register [`verity.isms.scope_documented`]; compliance: Engagement scope statement [`verity.isms.scope_recorded`]; compliance: Engagement scope statement approval [`verity.isms.scope_approved` NEW] | P1 |

### GOV-25 Interested parties and their requirements

SOC 2: none. ISO 27001:2022: Cl. 4.2 (full).

Decision: keep. Template with a running check; customer requirements come from Commitments.

Stays with people: Which expectations the program takes on. No system can prove: GOV-25.B.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `register-of-interested-parties-and-what` | GOV-25.A, GOV-25.B, GOV-25.D | check:verity.interested_parties.documented | template `context-and-interested-parties`; documents: Policy register [`verity.interested_parties.documented`]; compliance: Commitments register (customer requirements) [`verity.commitments.owned_and_mapped` NEW] | P1 |
| `doc-context-and-interested-parties` | GOV-25.A, GOV-25.B, GOV-25.D | document:context-and-interested-parties | template `context-and-interested-parties`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `review-record-covering-new-contracts-and` | GOV-25.C, GOV-25.D | person | documents: Version history of the context and interested parties register [`verity.interested_parties.documented`]; audit: Audit trail export filtered to commitments (export exists); person: dated note of what was checked | P1 |
| `version-history-and-approval-record-for` | GOV-25.C | check:verity.documents.controlled | documents: Policy register with version history [`verity.documents.controlled`] | P1 |

### GOV-26 Security objectives, plans and measures

SOC 2: none. ISO 27001:2022: Cl. 5.1 (partial), Cl. 6.2 (full), Cl. 7.1 (partial), Cl. 9.1 (partial).

Decision: keep. Objectives document and tasks; no record type for measures yet.

Stays with people: Results per objective, resourcing decisions, sharing with staff. No system can prove: GOV-26.D and GOV-26.E.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-security-objectives-plan` | GOV-26.A, GOV-26.B | document:security-objectives-plan | template `security-objectives-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `security-objectives-with-owners-targets-and` | GOV-26.A, GOV-26.B, GOV-26.C, GOV-26.E | check:verity.objectives.documented | template `security-objectives-plan`; documents: Policy register [`verity.objectives.documented`]; tasks: One task per objective with its target [`verity.tasks.owned_and_dated` NEW] | P1 |
| `measures-and-results-compared-with-targets` | GOV-26.C | person | onboarding: Readiness snapshots over time; person: results per objective compared with its target, each quarter | P1 |
| `resourcing-decisions-for-the-security-program` | GOV-26.D | person | person: leadership minutes or budget sheet, including requests turned down and why | people-only |
| `management-review-agenda-and-minutes` | GOV-26.D, GOV-26.E | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |

### GOV-27 Statement of Applicability

SOC 2: none. ISO 27001:2022: Cl. 6.1.3 (partial).

Decision: keep. The Applicability page, its versions and its XLSX export are the SoA.

Stays with people: Quality of each reason, supplier behind each inherited control. No system can prove: GOV-27.B reason quality.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `statement-of-applicability-showing-every-decision` | GOV-27.A, GOV-27.B, GOV-27.C, GOV-27.D, GOV-27.E | check:verity.soa.complete | compliance: Statement of Applicability (XLSX export exists) [`verity.soa.complete`]; compliance: Statement of Applicability [`verity.soa.matches_risk_treatment` NEW]; compliance: Statement of Applicability versions [`verity.soa.version_approved` NEW]; person: review that each reason is specific | P1 |
| `treatment-plan-with-owners-and-due` | GOV-27.C | person | risk: Risk register, treatment plan and due date [`verity.risks.treatment_planned` NEW]; tasks: Treatment tasks linked to risks [`verity.tasks.owned_and_dated` NEW] | P1 |
| `risk-register-with-owners-ratings-and` | GOV-27.C | check:verity.risks.treated | risk: Risk register [`verity.risks.treated`]; risk: Risk register [`verity.risks.reviewed`]; risk: Risk register [`verity.risks.controls_linked`]; risk: Risk register [`verity.risks.acceptance_current`] | P1 |
| `supplier-certificates-behind-inherited-controls` | GOV-27.D | person | vendors: Vendor documents (SOC reports, ISO certificates) and SOC report reviews [`verity.vendors.assessed_in_cadence`]; person: which supplier performs each inherited Annex A control | P1 |
| `approval-of-each-version-by-risk` | GOV-27.E | person | compliance: Statement of Applicability versions (XLSX export exists) [`verity.soa.version_approved` NEW]; person: sign off by each risk owner, since a version records one approver | P1 |

### GOV-28 Document and record management

SOC 2: none. ISO 27001:2022: Cl. 7.5.1 (full), Cl. 7.5.2 (full), Cl. 7.5.3 (full), A.5.33 (partial), A.5.37 (partial).

Decision: revise_objectives. Documents is the store: versions, approvals, owners, review dates.

Stays with people: Settings of any other store; outside documents not held in Verity. No system can prove: None of the core objectives.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `document-control-procedure-covering-approval-versions` | GOV-28.A | person | template `document-control-procedure`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-document-control-procedure` | GOV-28.A, GOV-28.B | document:document-control-procedure | template `document-control-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `access-and-retention-settings-for-the` | GOV-28.C | person | iam: Roles and permissions export (who can read, edit and approve documents); documents: Policy register with version history [`verity.documents.controlled`]; person: screenshot of sharing and retention settings for any other document store, and the retention periods set | P1 |
| `version-history-and-approval-record-for` | GOV-28.D, GOV-28.E, GOV-28.F | check:verity.documents.controlled | documents: Policy register with version history [`verity.documents.controlled`] | P1 |
| `vendor-assurance-reports-that-were-reviewed` | GOV-28.E | person | vendors: SOC report reviews and vendor documents [`verity.vendors.assessed_in_cadence`] | P1 |
| `doc-operating-procedure-template` | GOV-28.F | document:operating-procedure-template | template `operating-procedure-template`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |

### GOV-29 Security operating plan

SOC 2: none. ISO 27001:2022: Cl. 4.4 (partial), Cl. 6.3 (partial), Cl. 8.1 (full).

Decision: revise_objectives. The programme periodic view already counts dated evidence per cadence.

Stays with people: Whether activities met their standard; change approvals outside Verity. No system can prove: GOV-29.C standard met.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `operating-plan-listing-activities-owners-and` | GOV-29.A, GOV-29.B, GOV-29.C | person | template `isms-operating-plan`; compliance: Periodic activities against the audit period (programme view) [`verity.programme.periodic_on_track` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-isms-operating-plan` | GOV-29.A | document:isms-operating-plan | template `isms-operating-plan`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `records-showing-planned-activities-were-completed` | GOV-29.B, GOV-29.C | person | compliance: Periodic activities against the audit period (programme view) [`verity.programme.periodic_on_track` NEW]; tasks: Recurring activity tasks [`verity.tasks.recurring_done_on_time` NEW]; person: reason and new date for each slip | P1 |
| `review-of-planned-changes-and-outsourced` | GOV-29.D, GOV-29.E, GOV-29.F | person | vendors: Vendor register with outsourced services and reviews [`verity.vendors.assessed_in_cadence`]; template `change-management-procedure`; person: ticket or note made before each change to the management system | P1 |
| `security-terms-agreed-in-each-vendor` | GOV-29.E | person | vendors: Vendor register, contracts on file (security addendum, NDA, master); person: the clause in each contract or DPA | P1 |
| `security-assessment-for-each-critical-vendor` | GOV-29.E | check:verity.vendors.assessed_in_cadence | vendors: Vendor register, assessments [`verity.vendors.assessed_in_cadence`] | P1 |
| `log-of-control-deficiencies-with-owner` | GOV-29.F | check:tickets.remediation_tracked, check:verity.tasks.remediation_in_sla | tasks: Remediation tasks [`verity.tasks.remediation_in_sla`]; tasks: Remediation tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Remediation tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing) | P1 |

### GOV-30 Security program improvement

SOC 2: none. ISO 27001:2022: Cl. 4.4 (partial), Cl. 6.1.1 (partial), Cl. 10.1 (full).

Decision: keep. Improvement items are tasks; audit findings feed them.

Stays with people: Decision and reason per item, review of effect. No system can prove: GOV-30.C and GOV-30.E.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `procedure-for-raising-and-deciding-improvements` | GOV-30.A | person | template `corrective-action-procedure`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-corrective-action-procedure` | GOV-30.A | document:corrective-action-procedure | template `corrective-action-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `improvement-log-with-owners-decisions-and` | GOV-30.B, GOV-30.C, GOV-30.D | person | tasks: Improvement tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Improvement tasks [`verity.tasks.closure_evidenced` NEW]; compliance: Assurance findings [`verity.assurance.findings_tracked` NEW]; person: the decision and reason on each item, benefit and effort | P1 |
| `internal-audit-or-readiness-assessment-report` | GOV-30.B | check:verity.audit.internal_in_12_months, person | compliance: Assurance records, internal audit [`verity.assurance.internal_audit_held` NEW]; compliance: Evidence on the internal audit control [`verity.audit.internal_in_12_months`]; person: the audit report itself, with scope, criteria, evidence examined and findings | P1 |
| `management-review-agenda-and-minutes` | GOV-30.B, GOV-30.E | check:verity.management_review.in_12_months, person | compliance: Assurance records, management review [`verity.assurance.management_review_held` NEW]; compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |
| `measures-and-results-compared-with-targets` | GOV-30.B | person | onboarding: Readiness snapshots over time; person: results per objective compared with its target, each quarter | P1 |
| `review-of-completed-improvements-and-their` | GOV-30.E | person | compliance: Management review record inputs [`verity.assurance.management_review_held` NEW]; person: dated note on the effect of each sampled improvement | P1 |

### GOV-31 Yearly management review by top management (proposed)

SOC 2: none. ISO 27001:2022: Cl. 5.1 (partial), Cl. 7.1 (partial), Cl. 9.3.1 (full), Cl. 9.3.2 (full), Cl. 9.3.3 (full).

Decision: proposed successor of GOV-15. Proposed successor. Assurance records carry the shipped input list, so a check can test inputs one by one.

Stays with people: Top management's judgement and decisions. No system can prove: GOV-31.C the judgement.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-management-review-procedure` | GOV-31.A, GOV-31.C | document:management-review-procedure | template `management-review-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `management-review-agenda-and-minutes` | GOV-31.B, GOV-31.C, GOV-31.D | check:verity.management_review.in_12_months, person | compliance: Evidence on the management review control [`verity.management_review.in_12_months`]; compliance: Management review record inputs [`verity.assurance.management_review_inputs_recorded` NEW]; template `management-review-procedure`; person: the minutes, with attendees and decisions | P1 |
| `actions-raised-in-the-review-and` | GOV-31.D | person | tasks: Remediation tasks raised from management review [`verity.tasks.owned_and_dated` NEW]; compliance: Assurance findings on the management review record [`verity.assurance.findings_tracked` NEW]; `tickets.remediation_tracked` (ticketing); person: escalation to the oversight body of items open across two reviews | P1 |

### GOV-32 Top management security policy statement (proposed)

SOC 2: CC5.3 (partial). ISO 27001:2022: Cl. 5.1 (partial), Cl. 5.2 (full).

Decision: proposed successor of GOV-17. Proposed successor. The policy statement template and its approval tier.

Stays with people: That the approver is top management, and availability outside the company. No system can prove: GOV-32.A fit to purpose.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `doc-information-security-policy-statement` | GOV-32.A, GOV-32.D | document:information-security-policy-statement | template `information-security-policy-statement`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `approval-record-for-each-policy` | GOV-32.A | person | documents: Policy register with approval tiers [`verity.documents.controlled`] | P1 |
| `staff-acknowledgement-of-current-policies` | GOV-32.D | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; documents: Acknowledgement campaigns after major changes [`verity.policies.major_change_campaigned` NEW]; NEED hr_system | P1 |

### HR-01 Pre-hire background checks

SOC 2: CC1.1 (partial), CC1.4 (partial). ISO 27001:2022: A.6.1 (full).

Decision: keep. No signed connector reaches HR or screening systems, so this stays P3 apart from the policy.

Stays with people: Completed checks, rechecks, where results are stored. No system can prove: HR-01.E data minimisation (observation).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `background-check-policy` | HR-01.A, HR-01.E | person | template `human-resource-security-policy`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-human-resource-security-policy` | HR-01.A | document:human-resource-security-policy | template `human-resource-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `completed-background-checks-for-a-sample` | HR-01.B, HR-01.C, HR-01.D, HR-01.E | person | NEED background_screening; NEED hr_system; `tickets.access_requests_approved` (ticketing+identity_provider); person: provider completion page per person, showing date and result only | P3 |
| `roster-of-joiners-and-leavers-with` | HR-01.B | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `approved-requests-for-a-sample-of` | HR-01.B, HR-01.C | check:tickets.access_requests_approved, person | `tickets.access_requests_approved` (ticketing+identity_provider); person: export of the access request tool when it is not connected | P2 |
| `security-terms-agreed-in-each-vendor` | HR-01.D | person | vendors: Vendor register, contracts on file (security addendum, NDA, master); person: the clause in each contract or DPA | P1 |

### HR-02 Confidentiality / IP agreements

SOC 2: C1.1 (partial), CC1.1 (partial). ISO 27001:2022: A.5.32 (partial), A.6.2 (partial), A.6.5 (partial), A.6.6 (full), A.8.30 (partial).

Decision: revise_objectives. Signed agreements live in HR or signing tools (P3). Vendor contracts of type NDA cover outside parties now.

Stays with people: Signed copies, clause content, refresh on change. No system can prove: HR-02.D clause content and HR-02.E.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `confidentiality-and-ip-agreement-template` | HR-02.A, HR-02.D | person | documents: Uploaded templates with owner, review date and approval [`verity.documents.controlled`]; template `human-resource-security-policy`; person: the agreement and clause templates kept by the company lawyer, with the yearly review note | P1 |
| `doc-human-resource-security-policy` | HR-02.A | document:human-resource-security-policy | template `human-resource-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `signed-agreements-for-a-sample-of` | HR-02.B, HR-02.C, HR-02.D, HR-02.E, HR-02.F | person | NEED esignature; NEED hr_system; person: signed copies for the people the auditor selects | P3 |
| `roster-of-joiners-and-leavers-with` | HR-02.B | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `contractor-register-with-start-and-end` | HR-02.B | person | vendors: Vendor register filtered to contractors, with engagements [`verity.vendors.contractors_bounded` NEW]; NEED hr_system; NEED identity_provider | P1 |
| `approved-requests-for-a-sample-of` | HR-02.C | check:tickets.access_requests_approved, person | `tickets.access_requests_approved` (ticketing+identity_provider); person: export of the access request tool when it is not connected | P2 |
| `vendor-inventory-with-owner-data-and` | HR-02.F | check:verity.vendors.owner_and_tier | vendors: Vendor register [`verity.vendors.owner_and_tier`]; `idp.connected_apps_known` (identity_provider) | P1 |
| `security-terms-agreed-in-each-vendor` | HR-02.F | person | vendors: Vendor register, contracts on file (security addendum, NDA, master); person: the clause in each contract or DPA | P1 |

### HR-03 Contractor lifecycle management

SOC 2: CC6.2 (partial), CC9.2 (partial). ISO 27001:2022: A.5.11 (partial), A.8.30 (partial).

Decision: keep. Vendors of type contractor with engagements give sponsor, dates and systems; the identity provider shows removal.

Stays with people: Return of devices and badges; access review sign off until the access review module. No system can prove: HR-03.D vendor lead interview.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `contractor-onboarding-and-offboarding-procedure` | HR-03.A | person | template `joiner-mover-leaver-checklists`; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-joiner-mover-leaver-checklists` | HR-03.A | document:joiner-mover-leaver-checklists | template `joiner-mover-leaver-checklists`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `contractor-register-with-start-and-end` | HR-03.B, HR-03.C, HR-03.D, HR-03.E | person | vendors: Vendor register filtered to contractors, with engagements [`verity.vendors.contractors_bounded` NEW]; NEED hr_system; NEED identity_provider | P1 |
| `account-list-export` | HR-03.B | check:idp.access_list_exported, person | `idp.access_list_exported` (identity_provider); NEED identity_provider; person: export uploaded with the steps used, for systems outside the identity provider | P2 |
| `signed-agreements-for-a-sample-of` | HR-03.C | person | NEED esignature; NEED hr_system; person: signed copies for the people the auditor selects | P3 |
| `acknowledgement-from-every-member-of-staff` | HR-03.C | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; NEED hr_system; person: roster comparison for staff who are not Verity members | P1 |
| `completion-records-for-all-staff` | HR-03.C | person | NEED learning_platform; NEED learning_platform; documents: Training material acknowledgements (in house sessions) [`verity.training.acknowledged` NEW]; NEED hr_system; person: sign off sheet for a session run in house when no tool records it | P1 |
| `approved-requests-for-a-sample-of` | HR-03.C | check:tickets.access_requests_approved, person | `tickets.access_requests_approved` (ticketing+identity_provider); person: export of the access request tool when it is not connected | P2 |
| `removal-records-for-a-sample-of` | HR-03.D | check:people.leavers_deprovisioned, person | `people.leavers_deprovisioned` (hr_system+identity_provider); vendors: Contractor engagements and vendor offboarding records [`verity.vendors.contractors_bounded` NEW]; NEED identity_provider; person: record of each device, badge and data item returned | P1 |
| `completed-access-reviews-with-reviewer-sign` | HR-03.E | person | access_reviews: Access review campaigns (module signed for Phase 3.2, not built); `idp.access_list_exported` (identity_provider); person: signed user export from each system, marked up by the reviewer | P3 |

### HR-04 Job descriptions with security responsibilities

SOC 2: CC1.4 (partial). ISO 27001:2022: Cl. 7.2 (partial), A.6.2 (partial).

Decision: keep. Job descriptions can be held in Documents for review dates; an HR system could list positions.

Stays with people: That duties match controls and access. No system can prove: HR-04.C.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `job-descriptions-that-state-security-responsibilities` | HR-04.A, HR-04.B, HR-04.C, HR-04.D | person | NEED hr_system; documents: Job descriptions held as documents with review dates [`verity.documents.controlled`]; template `competence-and-awareness-procedure`; person: job descriptions from the HR tool or shared drive | P1 |
| `doc-competence-and-awareness-procedure` | HR-04.A | document:competence-and-awareness-procedure | template `competence-and-awareness-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `current-organization-chart-with-reporting-lines` | HR-04.B | person | NEED identity_provider; NEED hr_system; onboarding: Owner functions and who holds them [`verity.members.owner_functions_held` NEW]; person: chart kept by the chief executive when no system holds reporting lines | P2 |
| `control-ownership-register` | HR-04.C | check:verity.controls.owned | compliance: Control gap report with owners (export exists) [`verity.controls.owned`] | P1 |
| `role-and-access-matrix` | HR-04.C | person | template `access-control-policy`; `idp.groups_drive_access` (identity_provider); person: matrix kept by the IT or engineering lead | P1 |

### HR-05 Offboarding and deprovisioning

SOC 2: CC6.2 (partial), CC6.3 (partial). ISO 27001:2022: A.5.11 (partial), A.6.5 (partial).

Decision: revise_objectives. Checklists can run as Tasks from a template; ownership handover is checkable; account removal needs the identity provider and an HR leaving date.

Stays with people: Return of devices, continuing duty acknowledgement. No system can prove: HR-05.E the leaver's acknowledgement (signature).

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `offboarding-checklist` | HR-05.A, HR-05.B | person | template `joiner-mover-leaver-checklists`; tasks: Offboarding task template with one sub-task per step; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-joiner-mover-leaver-checklists` | HR-05.A, HR-05.B | document:joiner-mover-leaver-checklists | template `joiner-mover-leaver-checklists`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-human-resource-security-policy` | HR-05.A | document:human-resource-security-policy | template `human-resource-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `roster-of-joiners-and-leavers-with` | HR-05.C, HR-05.D, HR-05.F | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `completed-offboarding-records-for-leavers-in` | HR-05.C, HR-05.D, HR-05.E, HR-05.F | person | tasks: Leaver checklist tasks from the offboarding task template [`verity.tasks.checklist_steps_done` NEW]; iam: Ownership moved from leavers [`verity.members.leaver_ownership_moved` NEW]; `people.leavers_deprovisioned` (hr_system+identity_provider); NEED ticketing; person: record of devices and tokens returned or wiped, and the leaver's acknowledgement of continuing duties | P1 |

### HR-06 Onboarding checklist

SOC 2: CC1.4 (partial), CC6.2 (partial). ISO 27001:2022: A.5.4 (partial).

Decision: keep. Same pattern as HR-05 for joiners.

Stays with people: That access was not copied from another user. No system can prove: HR-06.D the copy test.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `onboarding-checklist` | HR-06.A | person | template `joiner-mover-leaver-checklists`; tasks: Onboarding task template with one sub-task per step; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-joiner-mover-leaver-checklists` | HR-06.A | document:joiner-mover-leaver-checklists | template `joiner-mover-leaver-checklists`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `doc-human-resource-security-policy` | HR-06.A | document:human-resource-security-policy | template `human-resource-security-policy`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `completed-checklists-for-a-sample-of` | HR-06.B, HR-06.C, HR-06.D, HR-06.E | person | tasks: Joiner checklist tasks from the onboarding task template [`verity.tasks.checklist_steps_done` NEW]; `people.joiners_onboarded` (hr_system+identity_provider); NEED ticketing; person: HR export of joiners when no system lists them | P1 |
| `roster-of-joiners-and-leavers-with` | HR-06.B | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |
| `approved-requests-for-a-sample-of` | HR-06.B, HR-06.D | check:tickets.access_requests_approved, person | `tickets.access_requests_approved` (ticketing+identity_provider); person: export of the access request tool when it is not connected | P2 |
| `acknowledgement-from-every-member-of-staff` | HR-06.C | check:verity.policies.acknowledged | documents: Policy acknowledgements (completion export exists) [`verity.policies.acknowledged`]; documents: Policy acknowledgements, joiners [`verity.policies.acknowledged_at_join` NEW]; NEED hr_system; person: roster comparison for staff who are not Verity members | P1 |
| `completion-records-for-all-staff` | HR-06.E | person | NEED learning_platform; NEED learning_platform; documents: Training material acknowledgements (in house sessions) [`verity.training.acknowledged` NEW]; NEED hr_system; person: sign off sheet for a session run in house when no tool records it | P1 |

### HR-07 Performance management

SOC 2: CC1.4 (partial), CC1.5 (partial). ISO 27001:2022: none.

Decision: keep. Only an HR system could show completion; content stays confidential.

Stays with people: Review forms, skills gaps and follow up. No system can prove: HR-07.C and HR-07.D.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `performance-review-process` | HR-07.A | person | documents: Process guidance held as a document with review date [`verity.documents.controlled`]; NEED hr_system; person: manager guidance from the HR tool | P1 |
| `completed-reviews-showing-control-responsibilities-were` | HR-07.B, HR-07.C, HR-07.D | person | NEED hr_system; person: review form per person selected, showing security and control duties were assessed | P3 |
| `current-organization-chart-with-reporting-lines` | HR-07.B | person | NEED identity_provider; NEED hr_system; onboarding: Owner functions and who holds them [`verity.members.owner_functions_held` NEW]; person: chart kept by the chief executive when no system holds reporting lines | P2 |
| `job-descriptions-that-state-security-responsibilities` | HR-07.C | person | NEED hr_system; documents: Job descriptions held as documents with review dates [`verity.documents.controlled`]; template `competence-and-awareness-procedure`; person: job descriptions from the HR tool or shared drive | P1 |
| `completion-records-for-all-staff` | HR-07.D | person | NEED learning_platform; NEED learning_platform; documents: Training material acknowledgements (in house sessions) [`verity.training.acknowledged` NEW]; NEED hr_system; person: sign off sheet for a session run in house when no tool records it | P1 |

### HR-08 Security awareness training

SOC 2: CC1.4 (partial), CC2.2 (partial). ISO 27001:2022: Cl. 7.2 (partial), Cl. 7.3 (partial), A.5.17 (partial), A.6.3 (partial), A.8.7 (partial).

Decision: revise_objectives. A learning platform is the real source (P3); in house sessions can be recorded as acknowledgements.

Stays with people: Content quality, understanding, overdue follow up. No system can prove: HR-08.B and HR-08.E.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `training-content-and-schedule` | HR-08.A, HR-08.B, HR-08.E | person | template `competence-and-awareness-procedure`; NEED learning_platform; documents: Training material held as a document with review date [`verity.documents.controlled`] | P1 |
| `doc-competence-and-awareness-procedure` | HR-08.A | document:competence-and-awareness-procedure | template `competence-and-awareness-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `completion-records-for-all-staff` | HR-08.B, HR-08.C, HR-08.D, HR-08.E | person | NEED learning_platform; NEED learning_platform; documents: Training material acknowledgements (in house sessions) [`verity.training.acknowledged` NEW]; NEED hr_system; person: sign off sheet for a session run in house when no tool records it | P1 |
| `roster-of-joiners-and-leavers-with` | HR-08.C | check:people.leavers_deprovisioned, person | NEED hr_system; `people.leavers_deprovisioned` (hr_system+identity_provider); `people.joiners_onboarded` (hr_system+identity_provider); NEED identity_provider; iam: Members joined and disabled in the period (directory sync keeps it in step with the identity provider); person: HR or payroll export of starters and leavers | P3 |

### HR-09 Competence of people in security roles

SOC 2: none. ISO 27001:2022: Cl. 7.2 (full).

Decision: keep. Owner functions name the security roles; the record of competence is a judgement.

Stays with people: Competence records and gap actions. No system can prove: HR-09.C and HR-09.D.

| Artifact | Objectives | Today | Planned sources | Phase |
|---|---|---|---|---|
| `competence-requirements-for-each-security-role` | HR-09.A, HR-09.B | check:verity.competence.documented, person | template `competence-and-awareness-procedure`; documents: Policy register [`verity.competence.documented`]; onboarding: Owner functions (the roles with security duties) [`verity.members.owner_functions_held` NEW] | P1 |
| `doc-competence-and-awareness-procedure` | HR-09.A | document:competence-and-awareness-procedure | template `competence-and-awareness-procedure`; documents: Policy register and required documents list [`verity.documents.required_present` NEW]; documents: Policy register [`verity.policies.reviewed`] | P1 |
| `job-descriptions-that-state-security-responsibilities` | HR-09.A | person | NEED hr_system; documents: Job descriptions held as documents with review dates [`verity.documents.controlled`]; template `competence-and-awareness-procedure`; person: job descriptions from the HR tool or shared drive | P1 |
| `role-descriptions-for-security-and-compliance` | HR-09.B | person | template `information-security-roles-and-responsibilities`; onboarding: Owner functions and who holds them [`verity.members.owner_functions_held` NEW] | P1 |
| `control-ownership-register` | HR-09.B | check:verity.controls.owned | compliance: Control gap report with owners (export exists) [`verity.controls.owned`] | P1 |
| `competence-record-for-each-person-in` | HR-09.C, HR-09.D | person | NEED hr_system; NEED learning_platform; person: manager's dated assessment of how each person meets each requirement, with CV and certificates | P3 |
| `training-or-other-actions-taken-to` | HR-09.D | person | tasks: Competence gap tasks [`verity.tasks.owned_and_dated` NEW]; tasks: Competence gap tasks [`verity.tasks.closure_evidenced` NEW]; NEED learning_platform; person: check afterwards that each action worked | P1 |

## Objectives no system can prove

These rest on a judgement, an interview, a signature or a confidential record. Systems can show the
record exists and is on time; the conclusion stays with a person and the auditor.

- CS-01: CS-01.A interview on who decides; CS-01.D that the right contacts got the notice in time.
- CS-02: CS-02.C and CS-02.D, a judgement that practice meets each promise.
- CS-03: CS-03.D whether each report was routed correctly.
- CS-04: None of the core objectives; CS-04.E escalation needs an interview.
- CS-05: CS-05.C, CS-05.D and CS-05.E rest on a confidential log and interviews.
- CS-06: CS-06.D whether messages were received and understood.
- CS-07: CS-07.D that legal agreed before contact.
- CS-08: CS-08.B and CS-08.C, mostly people's records.
- GOV-01: GOV-01.C, a comparison with practice.
- GOV-02: GOV-02.B independence and GOV-02.D challenge.
- GOV-03: GOV-03.E the yearly review of the trigger list (interview).
- GOV-04: GOV-04.D breach handling.
- GOV-05: GOV-05.D the review interview.
- GOV-06: GOV-06.D design weakness review.
- GOV-07: GOV-07.D the review outcome.
- GOV-08: GOV-08.F whether the cause showed a wider gap.
- GOV-09: GOV-09.D interview.
- GOV-10: GOV-10.B regulator independence and GOV-10.D follow through.
- GOV-11: GOV-11.C, GOV-11.D and GOV-11.E.
- GOV-12: GOV-12.D finance interview.
- GOV-13: GOV-13.C independence (interview).
- GOV-14: GOV-14.C the review judgement.
- GOV-15: GOV-15.B content of the review.
- GOV-16: GOV-16.B signed rules of engagement; GOV-16.C independence.
- GOV-17: None beyond observation.
- GOV-18: GOV-18.E sign off (signature).
- GOV-19: None of the core objectives.
- GOV-20: GOV-20.D the decision to accept the remaining risk.
- GOV-21: GOV-21.B absence of conflict of interest.
- GOV-22: GOV-22.A that the description is accurate.
- GOV-23: GOV-23.A leadership approval (judgement of fit).
- GOV-24: GOV-24.B and GOV-24.D.
- GOV-25: GOV-25.B.
- GOV-26: GOV-26.D and GOV-26.E.
- GOV-27: GOV-27.B reason quality.
- GOV-28: None of the core objectives.
- GOV-29: GOV-29.C standard met.
- GOV-30: GOV-30.C and GOV-30.E.
- GOV-31: GOV-31.C the judgement.
- GOV-32: GOV-32.A fit to purpose.
- HR-01: HR-01.E data minimisation (observation).
- HR-02: HR-02.D clause content and HR-02.E.
- HR-03: HR-03.D vendor lead interview.
- HR-04: HR-04.C.
- HR-05: HR-05.E the leaver's acknowledgement (signature).
- HR-06: HR-06.D the copy test.
- HR-07: HR-07.C and HR-07.D.
- HR-08: HR-08.B and HR-08.E.
- HR-09: HR-09.C and HR-09.D.

## Content problems and gaps found

- Template `code-of-conduct` does not require acknowledgement at hire and every year, which GOV-04.A and `verity.policies.acknowledged` assume.
- Template `human-resource-security-policy` sets no recheck interval for sensitive roles (HR-01.A) and covers discipline in one sentence: no range of sanctions, right to respond or case records (GOV-11.A). No template carries the disciplinary procedure on its own.
- Template `information-security-roles-and-responsibilities` has no appointment of the security officer, no deputy and no organization chart prompt (GOV-10.A, GOV-21.A).
- Template `operations-security-policy` sets a yearly penetration test but no retest of fixed findings (GOV-16.E); the artifact `vulnerability-management-policy-with-timeframes` points to the Documents module with no template of its own.
- Template `incident-response-plan` says customers are told per contract but states no timeframe outside the health appendix (CS-01.A).
- `roster-of-joiners-and-leavers-with` names `people.leavers_deprovisioned` as its source, which covers leavers only; joiners have no source.
- `control-test-results-across-the-observation` is person only, although Verity keeps every check run.
- `security-objectives-with-owners-targets-and` says the objectives are tasks, but its source is a document check.
- `published-security-policies-covering-each-required` relies on `verity.policies.reviewed`, which passes on one published document (LD-04); `verity.documents.required_present` (CL-5) is still not in `checks.json`.
- `management-review-agenda-and-minutes` and `internal-audit-or-readiness-assessment-report` are typed `configuration`; they are records.
- Two pairs of artifacts duplicate one item on the same objective: `document-control-procedure-covering-approval-versions` and `doc-document-control-procedure` (GOV-28.A); `incident-procedure-showing-the-notification-timeframes` and `doc-incident-response-plan` (CS-01.A).
- Appendix C of `control-framework-requirements.md` gives `verity.policies.acknowledged` a 95 percent target; `checks.json` describes an all members rule. One of them is stale.
- `MANAGEMENT_REVIEW_INPUTS` in `compliance/assurance_service.py` says it is in Verity's own words, but several labels follow the standard's list closely. Worth a text policy look before more screens show it.
- Data the checks above need and do not have: an incident kind in Tasks (until the Incidents module); a review date on commitments (CS-02.C); a vendor link on supplier provided Statement of Applicability rows (GOV-27.D); an assurance kind for oversight body meetings (GOV-02); a record for an objective's measure and readings (GOV-26.C, clause 9.1); a decision field on improvement items (GOV-30.C); a sign off step on a risk assessment (GOV-18.E); a fraud mark on risk categories (templates exist); a `verity_members` capability.
- Assurance records hang on an engagement, so a workspace with no engagement cannot record an internal audit or management review at all.
- Verity members are not the staff list. Acknowledgement, training and joiner checks judge members, so staff never invited are invisible until an HR source or the proposed roster import exists (open question 1).
- No HR, learning, signing or screening connector is in the signed catalogue, so the operating evidence of HR-01, HR-02 and HR-07 stays with people until one is agreed.
- CS-06, CS-07 and HR-09 sit in the ISO pack (CL-10). The successors CS-08 and GOV-31 would too; GOV-32 maps SOC2:CC5.3 and needs the shared pack.

