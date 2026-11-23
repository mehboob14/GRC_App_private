# 6. Control changes

The consolidated breakdown of the three `coverage/*.controls.json` files: what the mapping research proposes to keep,
revise, split and add, with every successor control, the objectives that move or are added, the tenant impact, the
check mappings that must follow a split, the new capabilities proposed anywhere in the research, and the content
defects found. Proposals for qualified review (FW-5), never applied by this plan (AUTHORING section 6).

## 6.1 Decisions per control

| File | Keep | Revise objectives | Split | Add | Controls reviewed |
|---|---|---|---|---|---|
| `gov-cs-hr.controls.json` | 31 | 12 | 3 | 0 | 46 |
| `iam-ep-pe-ns-dm.controls.json` | 33 | 16 | 4 | 1 | 54 |
| `sd-lm-bc.controls.json` | 21 | 9 | 4 | 3 | 37 |
| All | 85 | 37 | 11 | 4 | 137 |

133 shipped controls reviewed; 11 splits create 11 successors and 4 controls are added, so the library would hold 148. No merge or deprecation is proposed.

Objective changes: 81 added, 40 reworded, 11 moved. A move is listed once on its source control (SD-15 also lists SD-05.D as moved in).

## 6.2 Splits

### CS-07 Contacts with authorities and security communities to CS-08 Security community memberships and advisories

Reason: ISO27001:A.5.5 (authorities) and A.5.6 (security groups) are both mapped full but are different activities: the first is an incident and legal duty owned with legal, the second is a threat input owned by security, with its own evidence and its own SoA row.

Objectives taken from CS-07: CS-07.B. New objectives: CS-08.A, CS-08.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.5.6 | full | The list of groups and feeds followed, each with an owner, kept current and producing items for the threat review, is the contact this requirement asks for. |

Tenant impact: adoption proposal: ISO 27001 workspaces are offered CS-08; CS-07 evidence tagged to memberships is listed for the owner to re-tag, nothing is copied and no green result carries over.

### GOV-15 Periodic management review of security to GOV-31 Yearly management review by top management

Reason: Bundles a quarterly management review (SOC2:CC4.2, CC1.2, the forum for control health) with the yearly review by top management that ISO27001:9.3.1 to 9.3.3 require, with its own input list, attendees and outputs. Different cadence, different body, and the ISO part does not apply to a SOC 2 only workspace.

Objectives taken from GOV-15: GOV-15.C. New objectives: GOV-31.A, GOV-31.B, GOV-31.D.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:9.3.1 | full | A yearly review by top management of whether the program fits, covers what it should and works, with attendees and decisions recorded. |
| ISO27001:9.3.2 | full | The review takes each set input and the record shows it, input by input. |
| ISO27001:9.3.3 | full | Decisions on improvements, changes and resources are recorded and tracked. |
| ISO27001:5.1 | partial | Top management reviewing the program once a year is part of leadership. Policy and objectives are shown by GOV-32 and GOV-26. |
| ISO27001:7.1 | partial | The yearly review records the resource commitments for the program as a whole. Needs per objective are in GOV-26. |

Tenant impact: adoption proposal and data migration: ISO 27001 workspaces are offered GOV-31; the 9.3 mappings move after the owner accepts; management review assurance records stay where they are and are linked to both controls; verity.management_review.in_12_months moves to GOV-31 and its history stays on GOV-15.

### GOV-17 Security policy suite to GOV-32 Top management security policy statement

Reason: Bundles the top management policy statement (ISO27001:5.2, a clause duty with its own approver and content) with the topic policy set (SOC2:CC5.3 full, ISO27001:A.5.1 and topic Annex A links). Different approver, different evidence, and SOC 2 does not ask for the statement.

Objectives taken from GOV-17: GOV-17.A. New objectives: GOV-32.D.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:5.2 | full | A statement approved by top management that fits the company, frames the objectives, commits to the requirements and to improving, is communicated to staff and is available to interested parties. |
| ISO27001:5.1 | partial | Top management setting the policy is part of leadership. Review and resourcing are shown by GOV-02, GOV-15 and GOV-31. |
| SOC2:CC5.3 | partial | The statement is the top of the policy set that deploys control activities; the topic policies are GOV-17. |

Tenant impact: adoption proposal: ISO 27001 workspaces are offered GOV-32; the policy statement document is linked to GOV-32 on acceptance; 5.2 readiness is recomputed, never copied.

### IAM-09 Segregation of duties to IAM-13 Segregation of duties in finance and payment processes

Reason: IAM-09 bundles duty separation in technology work (change author and approver, deployer and approver, administrator and log reviewer) with duty separation in finance and payment processes (create a vendor and pay it). The owner functions already give them different owners (IT lead, finance lead), the objectives give them different cadences (yearly, quarterly), and the finance part can be not applicable for a company with no in scope finance process while the technology part always applies. SOC2:CC5.1 and ISO27001:A.5.3 (full today) are reached by both parts. Identity and code host checks map to the technology part only.

Successor: owner finance_lead; applies when the company runs billing, payment, refund or finance processes inside the scope, or its services affect customers' financial reporting (profile fact affects_customer_financial_reporting).

Objectives taken from IAM-09: none. New objectives: IAM-13.A, IAM-13.B, IAM-13.C, IAM-13.D.

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:CC5.1 | partial | Separating finance and payment duties is one of the control activities that keep fraud and error risk down. |
| ISO27001:A.5.3 | partial | Keeps conflicting finance and payment duties apart, with a recorded safeguard where the team is too small. Technology duties are in IAM-09. |

Tenant impact: adoption proposal: IAM-13 is proposed to workspaces whose profile says they run in scope finance processes; a person confirms. IAM-09 keeps its evidence, history and owner. No result or risk acceptance is copied to IAM-13.

### EP-04 Patch management to NS-13 Server and container image patching

Reason: EP-04 bundles patching of staff devices (IT lead, device management, monthly device reports) with patching of servers and container images (engineering lead, cloud patching or image rebuilds, scanner results). The server part is not applicable to a company that runs only fully managed services, while devices always apply. SOC2:CC6.8, CC7.1 and ISO27001:A.8.8 are partial and reached by both. The split decides that devices.os_current maps to EP-04 and scanner and cloud patch checks map to NS-13.

Successor: owner engineering_lead; applies when the company runs servers, virtual machines or container images it maintains itself (not only fully managed services).

Objectives taken from EP-04: EP-04.E. New objectives: NS-13.A, NS-13.B, NS-13.C, NS-13.D, NS-13.E.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.8.8 | partial | Patching servers and rebuilding images within set times is how known weaknesses in production software are fixed. Finding them is LM-11 and SD-03. |
| SOC2:CC7.1 | partial | Patching is how vulnerabilities found in production systems are treated. Finding them is covered by scanning. |
| SOC2:CC6.8 | partial | Patching removes the weaknesses malicious software uses on servers. |

Tenant impact: adoption proposal: NS-13 proposed to workspaces that run their own servers or images; EP-04 keeps its history, including any server patch evidence filed so far. Overlap with LM-11 remediation is for the LM reviewer to settle. No result or acceptance is copied.

### NS-04 Hardening baselines (CIS) to NS-14 Network equipment hardening and firmware

Reason: NS-04 bundles hardening of cloud services, servers, containers and databases (engineering lead, cloud configuration checks) with hardening and firmware of network equipment such as office firewalls, routers, switches and wireless controllers (IT lead, device configuration backups). The network equipment part is not applicable to a cloud only company with no own network equipment. The ISO27001:A.8.20 rationale on NS-04 is entirely about network devices, and A.8.9 is mapped full across both.

Successor: owner it_lead; applies when the company runs its own network equipment, such as office or site firewalls, routers, switches or wireless controllers (profile facts: own premises or server sites).

Objectives taken from NS-04: none. New objectives: NS-14.A, NS-14.B, NS-14.C, NS-14.D.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.8.20 | partial | Firewalls, routers, switches and wireless controllers are hardened to an approved baseline, their configurations are backed up on change, and drift and unsupported firmware are checked at least quarterly. Moved from NS-04 with its rationale. |
| ISO27001:A.8.9 | partial | Secure configuration of network equipment. Servers, containers, databases and cloud services are NS-04. |

Tenant impact: adoption proposal: NS-14 proposed to workspaces with own premises or server sites. Engine gap: if NS-14 is not applicable, A.8.9 rests on one partial link and CL-3 reads it as partly covered; see Gaps. No result or acceptance is copied.

### DM-16 Secure data disposal to EP-08 Equipment and media wiping and disposal

Reason: DM-16 bundles wiping and disposing of devices and media (IT lead, asset disposal records, contractor certificates, per item) with deleting data from every store and copy (engineering lead, lifecycle rules and purge jobs, per deletion run). Owners, evidence and connector checks differ: verity.assets.disposal_recorded and device management belong to the first, cloud.storage_lifecycle to the second. ISO27001:A.7.14 and A.7.10 rationales are about equipment and media; A.8.10 is about data. No objective tested deletion on request or when a customer leaves, which SOC2:C1.2 and P4.3 rely on.

Successor: owner it_lead; applies when always (every company retires laptops or media).

Objectives taken from DM-16: DM-16.B, DM-16.C. New objectives: EP-08.A, EP-08.B, EP-08.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.7.14 | partial | Moved from DM-16 with its rationale: laptops, servers, drives and removable media are wiped or destroyed by a fitting method before reuse, sale or scrap, the result is confirmed, and a record or certificate is kept. |
| ISO27001:A.7.10 | partial | Moved from DM-16: drives and removable media at the end of their life are wiped or destroyed and recorded. |
| SOC2:CC6.5 | partial | Moved from DM-16: data on retired equipment is made unrecoverable before its protections end. |
| SOC2:C1.2 | partial | Confidential data on retired equipment is destroyed. Data in stores and copies is DM-16. |

Tenant impact: adoption proposal: EP-08 proposed to every workspace that has DM-16; DM-16 keeps its history, including device disposal evidence filed so far. checks.json mapping of verity.assets.disposal_recorded moves from DM-16 to EP-08 (owner decision). No result or acceptance is copied.

### SD-03 Dependency and image scanning to SD-18 Software component list and licence review

Reason: SD-03 bundles vulnerability scanning (SOC2:CC6.8, CC7.1, ISO27001:A.8.8, A.8.28, A.8.29) with a component list and licence review (ISO27001:A.5.32). The licence review has a different owner (legal with engineering), a different remediation (replace the component or approve the licence) and different applicability (a SOC 2 only workspace can leave it out), and no operating objective tested it.

Objectives taken from SD-03: none. New objectives: SD-18.A, SD-18.B, SD-18.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.5.32 | partial | Moved from SD-03. The component list records each open source component's licence, and licences that conflict with how the product is used or sold are reviewed before release. Commercial licences sit with GOV-05 and rights in staff work with HR-02. |
| ISO27001:A.5.21 | partial | A component list per release shows which third party software each release contains, which is the software part of supply chain visibility. Vulnerability scanning of those components stays with SD-03. |

Tenant impact: adoption proposal: offer SD-18 to ISO workspaces; SD-03 wording change offered, not applied (CF-6)

### LM-11 Vulnerability management program to LM-13 Vulnerability scanning coverage

Reason: SOC2:CC7.1 and ISO27001:A.8.8 are both full on LM-11, which bundles discovery coverage (scanners, targets reconciled with the asset inventory, authenticated scans) with triage, remediation and risk acceptance. They have different owners (whoever runs the scanners versus each asset owner), cadences (scan interval versus per finding SLA) and failure conclusions (a coverage gap is not a late fix). Continuous compliance plan section 4 names this split. Scanner checks then map to LM-13, register checks to LM-11.

Objectives taken from LM-11: LM-11.B. New objectives: LM-13.A, LM-13.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:CC7.1 | partial | Scans of infrastructure, containers, dependencies and the external surface at the set frequency, with targets reconciled to the asset inventory, are the discovery half of vulnerability detection. Handling what is found stays with LM-11. |
| ISO27001:A.8.8 | partial | Finding technical weaknesses across the whole estate, with authenticated scans and coverage gaps followed up. Evaluating and fixing them stays with LM-11. |

Tenant impact: adoption proposal: LM-13 offered to every workspace running LM-11; LM-11 mapping coverage changes from full to partial with an audit row; no LM-11 result or acceptance is copied to LM-13

### BC-03 Business continuity / disaster recovery plan to BC-09 Redundancy and failover of critical services

Reason: ISO27001:A.8.14 (full) is a separate Annex A control, chosen on its own in the Statement of Applicability, about technical redundancy. BC-03 bundled it with continuity planning (SOC2:CC9.1, ISO27001:A.5.29, A.5.30). The two have different owners (the business continuity owner versus engineering), different evidence (a plan and an exercise versus cloud configuration and a failover test) and different remediation (rewrite and exercise the plan versus change the architecture). A cloud check on zones and standbys needs a control to map to that is not the plan.

Objectives taken from BC-03: BC-03.D. New objectives: BC-09.A, BC-09.B, BC-09.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.8.14 | full | Moved from BC-03. The redundancy each critical service relies on is recorded against its recovery targets, kept in place and failed over in a yearly test, which shows it is enough for the availability promised. |
| SOC2:A1.2 | partial | Redundant components and a tested failover are part of the recovery infrastructure. Backups come from BC-01 and environmental protection from PE-01 and PE-03. |
| ISO27001:A.5.30 | partial | A tested failover shows technology can meet the recovery targets the continuity plan sets. Data restores come from BC-02. |

Tenant impact: adoption proposal: offer BC-09 to workspaces running BC-03; A.8.14 moves with an audit row; BC-03.D history stays on BC-03

### BC-08 Vendor security due diligence to BC-10 Oversight of outsourced development

Reason: BC-08 maps to ten requirements. ISO27001:A.8.30 (outsourced development) applies only where a supplier builds software for the company and needs its own evidence (code ownership, acceptance testing of deliveries, escrow); bundled in BC-08 it cannot be marked not applicable on its own in the Statement of Applicability. It moves to BC-10. BC-08 objectives are also revised: B repeated BC-07.C and becomes tiering, E bundled contract terms (A.5.20) with findings (now F), and G is added for ongoing delivery review (A.5.22, A.8.21).

Objectives taken from BC-08: none. New objectives: BC-10.A, BC-10.B, BC-10.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| ISO27001:A.8.30 | partial | Contracts with suppliers that build software set security requirements, code ownership, audit rights and escrow where needed, and each delivery is reviewed and tested before it goes live. Choosing the supplier stays with BC-08 and code review with SD-06. |
| SOC2:CC9.2 | partial | Manages the risk of a business partner that writes software the company runs. General vendor due diligence comes from BC-08. |

Tenant impact: adoption proposal: offer BC-10 when the profile says development is outsourced; A.8.30 rationale on BC-08 narrowed with an audit row

## 6.3 Additions

### IAM-14 Product sign in protections for customer users

Reason: No control tests how customer users sign in to the product itself. The product is inside the SOC 2 system (SOC2:CC6.1) and is an information system for ISO27001:A.8.5 and A.5.17. IAM-03, IAM-04 and IAM-06 cover staff sign in only; IAM-11 covers product sessions but not passwords, lockout, reset or second factor options.

Owner engineering_lead; applies when The company runs an application its customers' users sign in to (profile fact: public internet facing application)..

Objectives: IAM-14.A, IAM-14.B, IAM-14.C, IAM-14.D.

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:CC6.1 | partial | How users of the product authenticate is one of the logical access protections over the system. |
| ISO27001:A.8.5 | partial | Secure sign in for the product's own users. Staff sign in is IAM-03, IAM-04, IAM-06 and IAM-11. |
| ISO27001:A.5.17 | partial | How the product stores, issues and resets its users' passwords. |

Tenant impact: adoption proposal for workspaces whose profile says they run a customer facing application; the engineering-security-standard template needs a product sign in section first.

### SD-15 Processing error handling and correction

Reason: SOC2:PI1.2 and PI1.3 rest on SD-05 and SD-08 alone, each partial (LD-14). Error handling and correction is the missing activity (onboarding section 7). Receives SD-05.D.

Objectives: SD-15.A, SD-15.B, SD-15.C, SD-15.D.

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:PI1.2 | partial | Rejected and duplicate inputs are held in a monitored queue and corrected, so input errors are not lost. Validation at the boundary comes from SD-05. |
| SOC2:PI1.3 | partial | Processing errors are logged, corrected with approval and reprocessed against the reconciliation. Detecting the error comes from SD-08. |

Tenant impact: adoption proposal: offer when Processing Integrity is elected

### SD-16 Output delivery and review

Reason: SOC2:PI1.4 rests on SD-08 alone, and the SD-08 rationale says delivery to the right recipient needs its own check (onboarding section 7).

Objectives: SD-16.A, SD-16.B, SD-16.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:PI1.4 | partial | Outputs are checked before release and reach only their intended recipients on time, with wrong or late outputs corrected. SD-08 shows the outputs were produced. |

Tenant impact: adoption proposal: offer when Processing Integrity is elected

### SD-17 Direct changes to production data

Reason: SOC2:CC8.1 names changes to data. Direct changes to production data outside the application are tested by every SOC 1 and SOC 2 auditor and no SD control covers them (onboarding section 9).

Objectives: SD-17.A, SD-17.B, SD-17.C.

| Requirement | Coverage | Rationale |
|---|---|---|
| SOC2:CC8.1 | partial | Changes made straight to production data, outside the application and its release path, are requested, approved by someone other than the person who runs them, logged and reconciled with the database activity. The other change controls cover code and infrastructure. |
| ISO27001:A.8.32 | partial | Brings data fixes run by hand inside change control: approval before the change, a limited group who may run it, and a check of the database activity against approved changes. |

Tenant impact: adoption proposal: offer to every workspace with production data

## 6.4 Objectives revised on kept controls

| Control | Changes | Objectives | Tenant impact |
|---|---|---|---|
| CS-02 | 1 add | CS-02.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| CS-03 | 1 reword | CS-03.A | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-05 | 1 add | GOV-05.E | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-08 | 2 reword, 1 add | GOV-08.B, GOV-08.E, GOV-08.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-13 | 2 add | GOV-13.E, GOV-13.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-20 | 1 add | GOV-20.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-21 | 1 add | GOV-21.E | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-28 | 1 reword, 1 add | GOV-28.B, GOV-28.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| GOV-29 | 1 reword, 1 add | GOV-29.D, GOV-29.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| HR-02 | 1 reword, 1 add | HR-02.B, HR-02.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| HR-05 | 1 reword, 1 add | HR-05.C, HR-05.F | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| HR-08 | 1 add | HR-08.E | none for data: objectives are content read at request time; a reworded objective with an open not applicable decision is listed for the owner to confirm again |
| IAM-01 | 1 reword, 1 add | IAM-01.B, IAM-01.F | none: objectives are content; the comparison report of AO-3 shows any control whose readiness would change. |
| IAM-02 | 1 reword | IAM-02.C | none for objectives; the CC6.3 coverage change alters what CC6.3 status means and needs the reviewer sign off of FW-5. |
| IAM-03 | 1 add | IAM-03.F | none |
| IAM-04 | 1 reword | IAM-04.D | none |
| IAM-06 | 1 add | IAM-06.E | none |
| IAM-07 | 1 reword, 1 add | IAM-07.A, IAM-07.F | none |
| IAM-12 | 2 reword | IAM-12.B, IAM-12.D | none |
| EP-03 | 1 add | EP-03.E | none |
| EP-07 | 1 move | EP-07.C | none for objectives; the A.8.23 mapping change needs FW-5 sign off. The EP-07.C letter is retired, never reused. |
| NS-02 | 1 reword | NS-02.D | none |
| NS-03 | 1 add | NS-03.E | none |
| NS-11 | 1 reword, 1 add | NS-11.D, NS-11.E | none |
| DM-01 | 1 reword, 1 add | DM-01.C, DM-01.E | none; the role fact proposes which of C and E apply, a person confirms. |
| DM-03 | 1 add | DM-03.E | none for objectives; the P3.2 change needs FW-5 sign off and only after E ships. |
| DM-08 | 1 reword | DM-08.C | none |
| DM-11 | 1 add | DM-11.E | none |
| SD-01 | 1 reword | SD-01.B | none |
| SD-02 | 1 add | SD-02.F | none |
| SD-05 | 1 move | SD-05.D | data migration: objective SD-05.D results and evidence stay on SD-05 history; SD-15 starts empty |
| SD-10 | 1 reword, 1 add | SD-10.B, SD-10.F | none |
| LM-02 | 2 reword, 2 add | LM-02.B, LM-02.C, LM-02.F, LM-02.G | none |
| LM-05 | 1 add | LM-05.E | none |
| LM-07 | 1 reword, 2 add | LM-07.C, LM-07.F, LM-07.G | none |
| BC-01 | 1 reword, 2 add | BC-01.D, BC-01.E, BC-01.F | none |
| BC-07 | 1 reword, 1 add | BC-07.D, BC-07.E | none |

## 6.5 Objectives moved or added

| Objective | Change | On control | Assurance | Statement | Why |
|---|---|---|---|---|---|
| CS-02.F | add | CS-02 | design | Where Processing Integrity is in scope, the published terms or service description say what the service processes, which inputs it accepts and what customers can expect about the completeness, accuracy and timing of its outputs. | SOC2:PI1.1 is mapped partial to CS-02 on the published terms, and no objective tested what those terms say about processing. |
| CS-07.B | move to CS-08.B | CS-08 | operating | The company belonged to or subscribed to security groups and advisory feeds that fit its technology and sector, and a named person followed each one and passed on what mattered. | Moves with ISO27001:A.5.6 to the successor control. |
| CS-08.A | add | CS-08 | design | The security groups, advisory feeds and professional bodies the company follows are listed, each chosen for its technology or sector, with a named owner and a rule for what is passed on and to whom. | The successor needs a design objective of its own. |
| CS-08.C | add | CS-08 | operating | Items passed on from these sources in the period reached the threat review or the people named, and the list of sources was checked in the last 12 months. | ISO27001:A.5.6 is about keeping the contact useful, so what came of it is tested, not membership alone. |
| GOV-05.E | add | GOV-05 | operating | Software licences and other intellectual property terms the company relies on are in the register with their limits and an owner, and use was compared with those limits in the last 12 months. | ISO27001:A.5.32 is mapped partial on licence and IP terms in the register, and no objective tested them. |
| GOV-08.F | add | GOV-08 | operating | Where a root cause could apply elsewhere, other systems and teams were checked for the same problem, and the policy, procedure or control was changed where the cause showed a wider gap. | Tests the part of ISO27001:10.2 on similar problems elsewhere and changes to the program on its own. |
| GOV-13.E | add | GOV-13 | operating | After each significant change to the organization, its services or the way security is run, a targeted independent review was held, or the change was recorded as covered by the next planned audit with a reason. | ISO27001:A.5.35 is mapped full and expects review on significant change as well as at planned intervals. |
| GOV-13.F | add | GOV-13 | design | Where the Privacy category is in scope, the audit program covers the privacy commitments, including how privacy requests and complaints are handled. | SOC2:P8.1 is mapped partial to GOV-13 (guided onboarding part 5, section 7) with no objective behind it. |
| GOV-15.C | move to GOV-31.C | GOV-31 | operating | In the last 12 months top management judged whether the program still fits the business, covers what it should and works, using the set inputs, and recorded its decisions on improvements, changes and resources. | Moves with ISO27001:9.3.1 to 9.3.3 to the successor control. |
| GOV-31.A | add | GOV-31 | design | An approved procedure sets a review by top management at least once a year and lists what it must take in: actions from earlier reviews, changes in outside and inside factors and in what interested parties need, their feedback, nonconformities and corrective actions, measurement and audit results, how far objectives were met, risk results and treatment status, and improvement ideas. | ISO27001:9.3.2 needs the inputs set in advance. |
| GOV-31.B | add | GOV-31 | operating | The record of the yearly review shows each listed input was considered, with the source record for each, or says why one did not apply. | ISO27001:9.3.2 is tested input by input, which the old GOV-15.C did in one line. |
| GOV-31.D | add | GOV-31 | operating | Each decision from the yearly review on improvements, changes to the program or resources has an owner and a date and was tracked to closure or carried to the next review. | ISO27001:9.3.3 outputs are tested on their own. |
| GOV-17.A | move to GOV-32.A | GOV-32 | design | The top level security policy is approved by top management, or by the board where a regulator requires it. It fits the purpose of the company, states the security objectives or how they are set, and commits to meeting the requirements that apply and to improving the program. | Moves with ISO27001:5.2 to the successor control. |
| GOV-32.D | add | GOV-32 | operating | The current policy statement was communicated to staff and made available to customers and other interested parties who need it, and the version they could reach was the approved one. | ISO27001:5.2 expects the statement communicated inside and available outside; this was half of the old GOV-17.D. |
| GOV-20.F | add | GOV-20 | operating | Each risk treated by transfer names the contract or insurance policy that carries it, with its cover and expiry, and a recorded decision says whether insurance is needed against business disruption. | SOC2:CC9.1 is mapped partial to GOV-20 and the guided onboarding plan adds the insurance decision; no objective tested transfer. |
| GOV-21.E | add | GOV-21 | operating | Each person holding a role with security duties was told of the role and its duties in writing, such as through a role description they acknowledged, and could describe it when asked. | ISO27001:5.3 expects roles to be communicated, and the mapping rationale says this control does not show it; no other control did. |
| GOV-28.F | add | GOV-28 | operating | An operating procedure exists for each routine task on the systems in scope, with an owner, version and review date, and the people who run those systems can reach the current version. | ISO27001:A.5.37 is owned by engineering and was folded into the documents list objective. |
| GOV-29.F | add | GOV-29 | operating | Each unplanned change to the management system or the services in scope in the period was reviewed afterwards for harm, and any action needed was raised. | ISO27001:8.1 asks for unintended changes to be reviewed, tested on its own. |
| HR-02.F | add | HR-02 | operating | Each outside party given confidential information in the period, such as a supplier, partner or prospective customer, had a non-disclosure agreement or contract confidentiality terms in force first. | ISO27001:A.6.6 is mapped full and covers outside parties, whose population is the vendor and partner list, not the joiner roster. |
| HR-05.F | add | HR-05 | operating | Each role change in the period had the access, asset and duty items of the checklist run by the date of the change, and access the new role does not need was removed. | ISO27001:A.6.5 covers change of role; movers and leavers are separate populations with separate failures. |
| HR-08.E | add | HR-08 | operating | The training checked that people understood it, such as through a quiz or a phishing exercise, and each person below the pass mark was trained again. | The SOC2:CC1.4 rationale says attendance alone does not show competence, and ISO27001:A.6.3 and 7.2 expect training to work. |
| IAM-01.F | add | IAM-01 | operating | Access to live systems for auditors, testers and outside support staff was requested, approved by the system owner before it was created, limited to the agreed level and time, and removed when the work ended. | ISO27001:A.8.34 is mapped and was not tested. |
| IAM-03.F | add | IAM-03 | operating | Each in scope system that people sign in to directly rather than through the identity provider, such as the cloud console, the code host, the password manager and applications outside single sign on, required a second factor for its own accounts. | Covers the population outside the identity provider that ISO27001:A.8.5 and IAM-03.A name. |
| IAM-06.E | add | IAM-06 | operating | Initial and reset passwords were single use and had to be changed at first sign in, and each reset done by an administrator or the help desk followed a recorded identity check. | Tests the ISO27001:A.5.17 claim. |
| IAM-07.F | add | IAM-07 | operating | Each privileged elevation and break glass use in the period was logged, raised an alert, and was reviewed afterwards by someone other than the person who used it. | Tests logged use, which the A.8.2 and A.8.18 rationales rely on. |
| IAM-13.A | add | IAM-13 | design | The conflicting duties matrix for finance and payment processes is approved. It lists the duties one person must not hold together, such as creating a vendor and approving its payment, or raising and approving a refund or credit, and the safeguard for each. |  |
| IAM-13.B | add | IAM-13 | operating | Each finance conflict was separated in the finance and payment systems, with maker checker approval where the system supports it. |  |
| IAM-13.C | add | IAM-13 | operating | Where separation was impractical, the approved safeguard, such as an independent review of logged payments, was carried out each time it was due. |  |
| IAM-13.D | add | IAM-13 | operating | Access to finance and payment systems was checked against the matrix every quarter and after each restructure, and each conflict was fixed or covered by an approved safeguard. |  |
| IAM-14.A | add | IAM-14 | design | The engineering security standard sets how customer users sign in to the product: password length and breached password screening, storage as a slow salted hash, lockout or rate limits, reset links that expire and work once, and the second factor and single sign on options offered. |  |
| IAM-14.B | add | IAM-14 | operating | The product's sign in settings in the period matched the standard for password rules, rate limiting or lockout, reset link expiry and second factor options. |  |
| IAM-14.C | add | IAM-14 | operating | Customer user passwords were stored only as slow salted hashes, and no password or reset token was written to logs. |  |
| IAM-14.D | add | IAM-14 | operating | The latest independent test of the product covered sign in, reset and session handling, and each finding was fixed or accepted. |  |
| EP-03.E | add | EP-03 | operating | Staff could install software on company devices only from the permitted list or a managed catalogue, and installs outside it were blocked, or reported and removed. | Tests the ISO27001:A.8.19 claim. |
| EP-04.E | move to NS-13.E | NS-13 |  |  | Out of cycle critical patches through the emergency change path are a production change; they follow the server part. |
| NS-13.A | add | NS-13 | design | The patch rules for servers, virtual machines and container base images are approved. They set timeframes by severity, how images are rebuilt and redeployed, and how exceptions are approved. |  |
| NS-13.B | add | NS-13 | operating | Server and image updates were applied by automation, such as managed patching or scheduled image rebuilds, not by hand. |  |
| NS-13.C | add | NS-13 | operating | Each server and running image was patched or rebuilt within the timeframe for its severity across the period. |  |
| NS-13.D | add | NS-13 | operating | Servers and images that fell behind were patched or given an approved exception. |  |
| NS-13.E | add | NS-13 | operating | Critical patches released out of cycle were applied through the emergency change path and reviewed afterwards. | Moved from EP-04.E with its letter. |
| EP-07.C | move to NS-03.E | NS-03 |  |  | Server outbound limits are network rules with an engineering owner. |
| NS-03.E | add | NS-03 | operating | Servers and administrative workstations for card data or other high value systems had no general web access and reached only named update and service destinations. | Moved from EP-07.C; interviewee changes from IT lead to engineering lead. |
| NS-14.A | add | NS-14 | design | The hardening baseline for network equipment is approved. It requires default credentials changed, management interfaces reachable only from an admin network, unused services off, configuration backed up after each change, and firmware kept within vendor support. |  |
| NS-14.B | add | NS-14 | operating | Each network device in the asset inventory matched the baseline, and its configuration was backed up after each change. |  |
| NS-14.C | add | NS-14 | operating | Network device firmware stayed within vendor support and was updated within the patch timeframes, or had an approved exception. |  |
| NS-14.D | add | NS-14 | operating | Network device drift was checked at least quarterly, and each finding was fixed or covered by an approved exception. |  |
| NS-11.E | add | NS-11 | operating | Remote sessions were logged, and the log was reviewed together with privileged access at the privileged review frequency. |  |
| DM-01.E | add | DM-01 | operating | Where the company decided the purposes of the data, each notice owed to a regulator or to affected people went within the legal deadline using the approved template, and a copy was kept, or a dated nil return was kept. | Controller side; applies to controller and both roles. |
| DM-03.E | add | DM-03 | operating | Where consent was asked, the person was told at that point what happens if they refuse or later withdraw. | Closes the SOC2:P3.2 gap. |
| DM-11.E | add | DM-11 | operating | Requests about customer data, where the company acts for the customer, were passed to that customer within the contract time, and the company gave the help the contract requires. | Processor path; the role fact proposes it, a person confirms. |
| DM-16.B | move to EP-08.B | EP-08 |  |  | Device and media disposal records. |
| DM-16.C | move to EP-08.C | EP-08 |  |  | Disposal method and certificates. |
| DM-16.E | add | DM-16 | operating | Customer data for customers who left, and personal data under an accepted erasure request, was deleted from every store within the committed time, with a record for each case, or a dated nil return was kept. | SOC2:C1.2 and P4.3 rely on disposal when data is no longer needed, including on request and at customer exit; no objective tested it. |
| EP-08.A | add | EP-08 | design | The procedure for wiping, reusing and disposing of laptops, servers, drives and removable media is approved. It sets the method for each data level, confirmation before reuse, certificates from disposal contractors and the record kept. |  |
| EP-08.B | add | EP-08 | operating | Every device and medium retired, sold, returned or reissued in the period had a disposal record with item, serial number, method, date and who did it, or a dated nil return was kept. | Moved from DM-16.B with its letter. |
| EP-08.C | add | EP-08 | operating | Each method fitted the data the item held, the result was confirmed before reuse or disposal, and a certificate was kept for each item a disposal contractor handled. | Moved from DM-16.C with its letter. |
| SD-02.F | add | SD-02 | operating | The security tests the engineering standard names, such as static analysis, ran on every change merged in the period, and each finding they raised was fixed, dismissed with a reason or carried as an approved exception before release. | ISO27001:A.8.28 and A.8.29 rely on static analysis in the pipeline (rationales on SD-02 and SD-10). No objective tested that it ran. |
| SD-18.A | add | SD-18 | design | The component and licence standard is approved. It says which builds produce a component list, which licences are allowed, restricted or not allowed for how the product is used or sold, and who may approve an exception. | New objective on successor SD-18. |
| SD-18.B | add | SD-18 | operating | Each release in the period had a component list, produced by the build, naming each component, its version and its licence. | New objective on successor SD-18. |
| SD-18.C | add | SD-18 | operating | Components with a restricted or not allowed licence were found before release and removed, replaced or approved as an exception with a reason. | New objective on successor SD-18. |
| SD-05.D | move to SD-15.D | SD-15 |  |  | Moves to SD-15 with the activity it tests. |
| SD-10.F | add | SD-10 | operating | Before release, each of those systems was checked against its approved security requirements, and any requirement not met was fixed or accepted by the approver. | ISO27001:A.8.29 relies on SD-10 for acceptance against security requirements before release. |
| SD-15.A | add | SD-15 | design | The error handling procedure is approved. It says where rejected inputs and processing errors are held, who reviews them, how a correction is approved and reprocessed, and the time allowed for each. | New control. |
| SD-15.B | add | SD-15 | operating | Each processing error in the period was logged with the date, the records affected, the cause and the correction, and was closed within the time the procedure allows. | New control. |
| SD-15.C | add | SD-15 | operating | Corrections and reprocessing were approved by someone other than the person who made them, and the reprocessed run reconciled before its output was released. | New control. |
| SD-15.D | moved in from SD-05.D | SD-15 |  |  | Moved from SD-05.D with the activity it tests. |
| SD-16.A | add | SD-16 | design | Each key output has an approved specification of its recipients, format and timing, the checks made before release, and how a wrong or late output is withdrawn and corrected. | New control. |
| SD-16.B | add | SD-16 | operating | Each scheduled output in the period was produced on time and passed its completeness and accuracy checks before release. | New control. |
| SD-16.C | add | SD-16 | operating | Outputs reached only their intended recipients, and each misdirected, late or wrong output was recorded, corrected and, where a customer was affected, reported to them. | New control. |
| SD-17.A | add | SD-17 | design | The procedure for changing production data outside the application is approved. It says when a direct change is allowed, who may request, approve and run one, that it runs as a reviewed script where possible, and what is logged. | New control. |
| SD-17.B | add | SD-17 | operating | Every direct change to production data in the period was requested and approved before it ran, by someone other than the person who ran it. | New control. |
| SD-17.C | add | SD-17 | operating | Only the listed people could change production data directly, and the database activity for the period matched the approved changes. | New control. |
| LM-02.F | add | LM-02 | operating | A source that stopped sending logs raised an alert, and each such alert was followed up until the source was sending again. | Split out of LM-02.B; ISO27001:A.8.15 and SOC2:CC2.1 rely on complete logs. |
| LM-02.G | add | LM-02 | operating | The administrators of a system could not change or delete its logs, and the few people who can change retention or delete logs in the central store were named and approved. | Split out of LM-02.C; ISO27001:A.8.15 (full) and A.5.28 rely on protected logs. |
| LM-05.E | add | LM-05 | operating | Each closed corrective action was checked for effect, by confirming the cause did not recur or by a verification recorded by someone other than its owner. | ISO27001:10.2 asks that the effect of corrective action is reviewed; LM-05 maps to it and no objective tested it. |
| LM-07.F | add | LM-07 | operating | Where an incident needed evidence, it was collected and kept as the plan sets, with a record of who collected and handled each item and when. | ISO27001:A.5.28 is mapped to LM-07 on the evidence procedure, but only the written procedure was examined. |
| LM-07.G | add | LM-07 | operating | The plan was reviewed in the last 12 months and after each significant incident, and each review was recorded. | Split out of LM-07.C (shared and reviewed). |
| LM-11.B | move to LM-13.B | LM-13 |  |  | Moves to LM-13 with the activity it tests. |
| LM-13.A | add | LM-13 | design | The vulnerability management policy sets the scan scope for infrastructure, containers, dependencies and the external surface, the minimum scan frequency, when authenticated scans are required and what counts as a significant change that triggers an extra scan. | New objective on successor LM-13. |
| LM-13.C | add | LM-13 | operating | Failed, partial and unauthenticated scans, and targets the scanner could not reach, were found and followed up, so a gap in coverage was not read as a clean result. | New objective on successor LM-13. |
| BC-01.E | add | BC-01 | operating | Rights to restore or delete backups were held by a small group that was reviewed in the period. | Split out of BC-01.D. |
| BC-01.F | add | BC-01 | operating | The configuration, infrastructure code and images needed to rebuild each service were kept in versioned storage covered by the backup policy. | ISO27001:A.8.13 covers copies of software and systems as well as data. BC-01.A names them; nothing tested them. |
| BC-03.D | move to BC-09.D | BC-09 |  |  | Moves to BC-09 with the activity it tests. |
| BC-09.A | add | BC-09 | design | For each critical service the redundancy it relies on to meet its recovery targets is recorded, such as several availability zones, a standby database or a secondary region, and approved by the engineering lead. | New objective on successor BC-09. |
| BC-09.B | add | BC-09 | operating | The recorded redundancy was in place throughout the period for each critical service. | New objective on successor BC-09. |
| BC-09.C | add | BC-09 | operating | Failover of the redundant parts was tested in the last 12 months, and the time to fail over was compared with the recovery targets. | New objective on successor BC-09. |
| BC-07.E | add | BC-07 | operating | Vendors no longer used were offboarded: their access was revoked, their copy of company data returned or deleted, and the offboarding recorded. | Split out of BC-07.D; ISO27001:A.5.22 rationale relies on removal with access revoked. |
| BC-08.F | add | BC-08 | operating | Findings and accepted risks from assessments were tracked to closure, or to an acceptance with an owner and an expiry. | Split out of BC-08.E. |
| BC-08.G | add | BC-08 | operating | At each reassessment of a critical vendor, its delivery against the agreed security and service levels was reviewed, and a material change, such as a breach, new ownership or a new subservice provider, led to an early review. | ISO27001:A.5.22 and A.8.21 rationales rely on checking delivered service levels; no objective tested it. |
| BC-10.A | add | BC-10 | design | Contracts with suppliers that build software for the company set the security requirements, who owns the code, audit rights and, where a critical system depends on the supplier's code, an escrow arrangement. | New objective on successor BC-10. |
| BC-10.B | add | BC-10 | operating | Each delivery from a development supplier was reviewed by a member of staff and tested against its security requirements before it went live. | New objective on successor BC-10. |
| BC-10.C | add | BC-10 | operating | Where escrow is required, the deposit was checked as complete and current at each review. | New objective on successor BC-10. |

Reworded objectives are listed per control in the `*.controls.json` files; rewording needs no data migration, but a
reworded objective with an open not applicable decision goes back to the owner to confirm.

## 6.6 Requirement mapping changes

| Requirement | Control | Change | Coverage now | Rationale | File |
|---|---|---|---|---|---|
| ISO27001:A.5.6 | CS-07 | removed | full to removed | Moves to CS-08; CS-07 keeps authority contacts (A.5.5). | gov-cs-hr |
| ISO27001:A.5.6 | CS-08 | full |  to full | See successor. | gov-cs-hr |
| ISO27001:9.3.1 | GOV-15 | removed | full to removed | The yearly review by top management moves to GOV-31. | gov-cs-hr |
| ISO27001:9.3.2 | GOV-15 | removed | full to removed | As above. | gov-cs-hr |
| ISO27001:9.3.3 | GOV-15 | removed | full to removed | As above. | gov-cs-hr |
| ISO27001:7.1 | GOV-15 | removed | partial to removed | Resource commitments for the program are decided at the yearly review. | gov-cs-hr |
| ISO27001:9.3.1 | GOV-31 | full |  to full | See successor. | gov-cs-hr |
| ISO27001:9.3.2 | GOV-31 | full |  to full | See successor. | gov-cs-hr |
| ISO27001:9.3.3 | GOV-31 | full |  to full | See successor. | gov-cs-hr |
| ISO27001:5.1 | GOV-31 | partial |  to partial | See successor. | gov-cs-hr |
| ISO27001:7.1 | GOV-31 | partial |  to partial | See successor. | gov-cs-hr |
| ISO27001:5.2 | GOV-17 | removed | partial to removed | The statement moves to GOV-32. CS-04 keeps its partial link for communication to staff. | gov-cs-hr |
| ISO27001:5.1 | GOV-17 | removed | partial to removed | Top management setting the policy moves with the statement. | gov-cs-hr |
| ISO27001:5.2 | GOV-32 | full |  to full | See successor. | gov-cs-hr |
| ISO27001:5.1 | GOV-32 | partial |  to partial | See successor. | gov-cs-hr |
| SOC2:CC5.3 | GOV-32 | partial |  to partial | See successor. GOV-17 keeps CC5.3 full. | gov-cs-hr |
| SOC2:CC6.3 | IAM-02 | coverage | full to partial | Reviews confirm that access still matches each person's role. Granting by role (IAM-08), removal (IAM-12) and separating duties (IAM-09) are the other parts. | iam-ep-pe-ns-dm |
| SOC2:CC6.3 | IAM-08 | coverage | full to partial | Granting access through roles at least privilege is the core of authorizing access by role. Changes, removal and periodic review sit in IAM-01, IAM-12 and IAM-02. | iam-ep-pe-ns-dm |
| ISO27001:A.5.3 | IAM-09 | coverage | full to partial | Keeps conflicting duties in technology work apart. Finance and payment duties are in IAM-13. | iam-ep-pe-ns-dm |
| ISO27001:A.8.23 | EP-07 | coverage | full to partial | Web filtering on staff devices in the office and remote. Outbound limits for servers that hold card data or other high value systems are in NS-03. | iam-ep-pe-ns-dm |
| ISO27001:A.8.23 | NS-03 | partial |  to partial | Limits outbound web access from servers that hold card data or other high value systems to named destinations. | iam-ep-pe-ns-dm |
| ISO27001:A.8.20 | NS-04 | removed | partial to removed | The NS-04 rationale for A.8.20 described network equipment only; the link moves to NS-14. | iam-ep-pe-ns-dm |
| ISO27001:A.8.9 | NS-04 | coverage | full to partial | Secure configuration of servers, containers, databases and cloud services. Network equipment is NS-14. | iam-ep-pe-ns-dm |
| SOC2:P3.2 | DM-03 | coverage | partial to full | Consent is captured before collection, and people are told what follows if they refuse or withdraw (DM-03.E). | iam-ep-pe-ns-dm |
| ISO27001:A.7.14 | DM-16 | removed | partial to removed | Moves to EP-08. | iam-ep-pe-ns-dm |
| ISO27001:A.7.10 | DM-16 | removed | partial to removed | Moves to EP-08. | iam-ep-pe-ns-dm |
| SOC2:CC6.5 | DM-16 | removed | partial to removed | Moves to EP-08. | iam-ep-pe-ns-dm |
| SOC2:C1.2 | DM-16 | coverage | full to partial | Deleting confidential data from every store and copy, including at customer exit. Wiping devices and media is EP-08. | iam-ep-pe-ns-dm |
| ISO27001:A.5.32 | SD-03 | remove |  to  | Moves to SD-18 with the component list and licence review. | sd-lm-bc |
| ISO27001:A.5.24 | LM-08 | add |  to partial | An on call rotation with escalation makes the response roles the plan names reachable at any hour. The plan itself comes from LM-07 and the exercise from LM-10. | sd-lm-bc |
| SOC2:CC7.1 | LM-11 | coverage |  to partial | LM-11 keeps the register, triage, remediation times and risk acceptance. Discovery coverage moves to LM-13, so LM-11 alone no longer covers the whole criterion. | sd-lm-bc |
| ISO27001:A.8.8 | LM-11 | coverage |  to partial | Same split: evaluating and treating weaknesses stays, finding them across the estate moves to LM-13. | sd-lm-bc |
| SOC2:CC7.1 | LM-12 | add |  to partial | Following advisories and the known exploited list surfaces newly disclosed weaknesses in software in use, which feeds detection. Scanning and remediation come from LM-11 and LM-13. Needs LM-12 adoptable by SOC 2 workspaces (CL-10). | sd-lm-bc |
| ISO27001:A.8.14 | BC-03 | remove |  to  | Moves to BC-09 with the redundancy record and the failover test. | sd-lm-bc |
| ISO27001:A.8.30 | BC-08 | rationale |  to partial | Narrowed: BC-08 chooses and reassesses the development supplier. Contract terms for code, testing of deliveries and escrow move to BC-10. | sd-lm-bc |

## 6.7 Check mappings that must follow a split

Shipped `checks.json` mappings on a split control, and where each goes. "Stays" means nothing in the research moves it.

| Check | From | To | Why | Source |
|---|---|---|---|---|
| `verity.management_review.in_12_months` | GOV-15 | GOV-31 (move) | It is a 12 month floor, which fits the yearly review. The quarterly review gets verity.assurance.management_review_held. | gov-cs-hr.controls.json |
| `scanner.scans_current` | LM-11 | LM-13 (move) | Named as a source of asset-inventory, scan-reports on this control; without the mapping its evidence does not attach here (AU-11). | sd-lm-bc.controls.json |
| `vcs.merged_changes_reviewed` | BC-08 | BC-10 (add, not mapped to BC-08 today) | Named as a source of sample-of-reviewed-changes on this control; without the mapping its evidence does not attach here (AU-11). | sd-lm-bc.controls.json |
| `scanner.scans_current` | EP-04 | NS-13 (move) | Server and image scanning goes to NS-13 with the EP-04 split. Conflict: 'What existing workspaces need' says it gains NS-13 rather than moves; see decisions. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Splits; coverage/iam-ep-pe-ns-dm.controls.json |
| `vcs.dependency_alerts_enabled` | LM-11 | LM-13 (move) | Its LM-11 rationale ('one source of vulnerability findings is switched on') is discovery coverage, which moves to LM-13 (scope includes dependencies). Extractor's reading of 'scanner and scan coverage checks to LM-13'; the document does not name this check. Its SD-03 mapping stays: dependency scanning stays on SD-03. | coverage/sd-lm-bc.md (Mapping changes paragraph) |
| `verity.assets.disposal_recorded` | DM-16 | EP-08 (move) | Equipment disposal moves to EP-08 with the DM-16 split (owner decision). | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Splits; coverage/iam-ep-pe-ns-dm.controls.json |
| `verity.vulns.within_sla` | EP-04 | NS-13 (move) | Vulnerability SLA goes to NS-13 with the EP-04 split; the LM-11 mapping stays. Same move or gain conflict as scanner.scans_current. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Splits; coverage/iam-ep-pe-ns-dm.controls.json |
| `verity.policies.reviewed` | GOV-17 | stays on GOV-17 | Shows each policy in the library that was started from a template or linked to a control is published, approved in the last 12 months and current. It does not show the library holds every policy the programme needs. | checks.json |
| `idp.access_list_exported` | IAM-09 | stays on IAM-09 | Gives the list used to find conflicting access. Judging the conflicts is done by people. | checks.json |
| `devices.os_current` | EP-04 | stays on EP-04 | Shows laptops run a supported operating system. Servers and applications need their own source. | checks.json |
| `cloud.hardening_baseline` | NS-04 | stays on NS-04 | Shows cloud configuration meets a benchmark. Operating system and container hardening need their own evidence. | checks.json |
| `cloud.storage_lifecycle` | DM-16 | stays on DM-16 | Shows storage deletes data when retention ends. Deletion from copies and vendors is separate. | checks.json |
| `vcs.dependency_alerts_enabled` | SD-03 | stays on SD-03 | Shows dependency alerts are on. Container image scanning and fixing the alerts are separate. | checks.json |
| `verity.vulns.kev_owned` | LM-11 | stays on LM-11 | Shows the most urgent findings are not unowned. | checks.json |
| `verity.vulns.within_sla` | LM-11 | stays on LM-11 | Shows no open critical or high finding is past its SLA now. Findings fixed late are not judged. | checks.json |
| `verity.vendors.assessed_in_cadence` | BC-08 | stays on BC-08 | Shows due diligence is repeated at the cadence the tier sets. | checks.json |

Proposed checks are already mapped to the successor codes where the researchers intended it (for example
`verity.vulns.assets_scanned` to LM-13, `verity.tasks.approved_before_done` to SD-17 and SD-18). Existing workspaces
never inherit a green result, a check history or a risk acceptance on a successor: each successor is an adoption
proposal a person confirms, with an audit row (IAM file, What existing workspaces need).

## 6.8 New capabilities proposed

| Capability | What it is for | Providers named | Raised in |
|---|---|---|---|
| `business_applications` | Software services staff sign in to that hold company or customer data, outside the other capabilities: access lists, admins, single sign on and two factor, member currency, API keys; also consent tools, support desks and finance or payment systems | hubspot, intercom, zendesk, posthog, sendgrid, resend, openai, anthropic; the tools of other capabilities for their own member lists (slack, sentry, datadog, pagerduty, jira, cloudflare, tailscale, grafana, linear, asana, notion and the platforms) | phase3-catalogue.md 1.1; coverage/iam-ep-pe-ns-dm.md; operations-checks.md section 6 (as business_application) |
| `ai_providers` | Services that run AI models on company data: whether retention matches the vendor review, and whether every project and key with usage is owned (`ai.*`) | openai, anthropic | phase3-catalogue.md 1.1 |
| `verity_identity` | Verity's own sign in, session audit rows and directory sync as evidence for one application, Verity itself (`verity.identity.*`) | verity | coverage/iam-ep-pe-ns-dm.md |
| `verity_members` | Members, groups and owner functions kept in Verity: leavers' records handed over, owner functions held (`verity.members.*`) | verity | coverage/gov-cs-hr.md |
| `learning_platform` | The training platform that assigns courses and records completion, overdue assignments and reminders (HR-08, HR-09). Named `security_training` in the device and HR research | none named | coverage/gov-cs-hr.md; mdm-and-endpoint-strategy.md D-HR-4 |
| `esignature` | The signing tool that holds signed confidentiality and IP agreements (HR-02, HR-03) | docusign | coverage/gov-cs-hr.md |
| `background_screening` | The screening provider: completed, cleared checks dated before first access, for hires, moves into sensitive roles and rechecks (HR-01) | checkr, certn | coverage/gov-cs-hr.md; mdm-and-endpoint-strategy.md D-HR-4 |
| `public_web` | Unauthenticated reads of the company's own public pages: security.txt, security page, terms, service levels and privacy notice, with changes dated (CS-02, CS-03) | none (Verity reads the pages) | coverage/gov-cs-hr.md |
| `productivity_suite` | Mail and file suite settings: external sharing, public links, leak prevention rules and alerts, sensitivity labels (DM-04, DM-19). Today filed under identity_provider; the owner decides | gws, entra (Microsoft 365) | coverage/iam-ep-pe-ns-dm.md |
| `verity_notifications` | Verity's delivery log of the security messages it sent (channel, time, provider message id), for CS-04.D and CS-06.B | verity | operations-checks.md section 6 (inferred) |

Changes proposed to existing capabilities:

| Capability | Change | Raised in |
|---|---|---|
| `alerting` | Remove Slack (no schedule, escalation or acknowledgement); add Better Stack and Grafana | operations-checks.md section 2; phase3-catalogue.md 1.1 |
| `asset_discovery` | Add the scanners (Tenable, Rapid7, Qualys), DigitalOcean, and the MDMs (Intune, Jamf, Kandji, Google) as device sources | phase3-catalogue.md 1.1; mdm-and-endpoint-strategy.md |
| `ci_cd` | Add Vercel, Netlify, Render, Heroku and Qovery | phase3-catalogue.md 1.1 |
| `cloud_infrastructure` | Qovery is listed but the research gives it ci_cd and business_applications only | phase3-catalogue.md (extractor finding) |
| `network_edge` | Add Vercel (firewall, partial); Tailscale must not implement `edge.minimum_tls` (WireGuard, not TLS) | phase3-catalogue.md; operations-checks.md section 2 |
| `ticketing` | Notion as a business application only (D-P3-5) | phase3-catalogue.md |
| `device_management` | Add Google Workspace (endpoint management and Endpoint Verification); show Kandji as Iru (Kandji) | mdm-and-endpoint-strategy.md D-DEV-11, D-DEV-13 |
| `endpoint_protection` | Add Microsoft Defender for Endpoint and Jamf Protect | mdm-and-endpoint-strategy.md D-DEV-12 |
| `hr_system` | Add HiBob and a CSV roster import (`roster_import`) as the interim source | mdm-and-endpoint-strategy.md D-HR-1; hr-systems.md |
| `password_manager`, `device_management` | Added to `idp.access_list_exported`, `idp.sso_enforced` and `endpoint.protection_active`, where 1Password and Intune implement them | this reconciliation (05, 5.9) |

New provider keys proposed:

| Key | Name | Capability | Phase |
|---|---|---|---|
| `gws` | Google Workspace devices (Cloud Identity Devices API and Endpoint Verification) | device_management | not in plan |
| `defender_endpoint` | Microsoft Defender for Endpoint | endpoint_protection | not in plan |
| `hibob` | HiBob | hr_system | not in plan |
| `roster_import` | People roster import (CSV) | hr_system | not in plan |
| `verity_agent` | Verity endpoint agent (Go plus osquery) | device_management | not in plan |
| `jamf_protect` | Jamf Protect | endpoint_protection | not in plan |
| `intune` | Microsoft Intune (as a device source for asset discovery) | asset_discovery | not in plan |
| `jamf` | Jamf Pro (as a device source for asset discovery) | asset_discovery | not in plan |
| `kandji` | Iru (Kandji) (as a device source for asset discovery) | asset_discovery | not in plan |
| `verity` | Verity controlled workforce import | hr_system | not in plan |
| `hubspot` | HubSpot | business_applications | Phase 3 |
| `intercom` | Intercom | business_applications | Phase 3 |
| `zendesk` | Zendesk | business_applications | Phase 3 |
| `posthog` | PostHog | business_applications | Phase 3 |
| `sendgrid` | SendGrid (Twilio) | business_applications | Phase 3 |
| `resend` | Resend | business_applications | Phase 3 |
| `openai` | OpenAI | ai_providers, business_applications | Phase 3 |
| `anthropic` | Anthropic | ai_providers, business_applications | Phase 3 |
| `docusign` | DocuSign | esignature | not in plan |
| `checkr` | Checkr | background_screening | not in plan |
| `certn` | Certn | background_screening | not in plan |

New observation types the proposed checks need (01-evidence-model.md 1.4 lists the rest): `ai.api_key`, `ai.setting`, `ai.usage`, `app.api_key`, `app.member`, `app.setting`, `audit_event`, `detection_rule`, `device.action`, `endpoint.alert`, `endpoint.sensor`, `error_issue`, `escalation_policy`, `identity.access_review`, `on_call_entry`, `person.event`, `person.screening`, `person.training`, `scanner.asset`, `scanner.scan`, `security_signal`, `service`, `verity.record`.

## 6.9 Proposed artifacts

| Artifact | Control | Objectives | Why | Raised in |
|---|---|---|---|---|
| `acceptance-test-of-supplier-deliveries` | BC-10 | BC-10.B | BC-10.B: New objective on successor BC-10. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `backup-storage-settings-export` | BC-01 | BC-01.D | BC-01.D: Storage protection and restore rights were one objective. Restore rights move to BC-01.E, and storage protection gains a settings test. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `branch-protection-change-log` | SD-06 | SD-06.C | gitlab.md writes 'NEED version_control: a log of changes to branch protection and approval rules over the period' to support SD-06.C 'throughout the period'. Daily reads miss a rule turned off and back on between runs (github.md section 8). Key is an extractor placeholder. | connectors/gitlab.md section 6 |
| `database-activity-log-review` | SD-17 | SD-17.C | SD-17.C: New control. Note: Matching activity to approved changes is a person's review. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `device-encryption-report` | EP-02 | EP-02.B, EP-02.C | Split out of inventory-of-company-devices so a passing enrolment check cannot satisfy the encryption objectives, and so a company without an MDM can fill it by hand or by attestation. EP-02.D placement not stated (see defects). | mdm-and-endpoint-strategy.md section 4 F1 and section 3 EP-02 |
| `device-protection-agent-report` | EP-01 | EP-01.B | Split out of inventory-of-company-devices so the agent objective is tested by agent checks. endpoint.prevention_enabled has no named artifact and fits here; endpoint.servers_covered is proposed on asset-inventory instead. | mdm-and-endpoint-strategy.md section 4 F1; connectors/crowdstrike-falcon.md and microsoft-defender-endpoint.md section 6 |
| `device-wipe-capability-report` | EP-05 | EP-05.B | Split out of inventory-of-company-devices so the wipe capability objective is tested by the wipe check. | mdm-and-endpoint-strategy.md section 4 F1 |
| `escrow-verification-record` | BC-10 | BC-10.C | BC-10.C: New objective on successor BC-10. Note: No system in the catalogue reaches an escrow agent. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `evidence-handling-record-for-incidents` | LM-07 | LM-07.F | LM-07.F: ISO27001:A.5.28 is mapped to LM-07 on the evidence procedure, but only the written procedure was examined. Note: Whether evidence was captured without changing it is a person's account. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `incident-plan-acknowledgement-by-role-holders` | LM-07 | LM-07.C | LM-07.C: Sharing the plan and reviewing it were one objective with different evidence and cadence. Review moves to LM-07.G. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `infrastructure-and-configuration-change-history` | SD-01 | SD-01.B | SD-01.B: ISO27001:A.8.19 and A.8.32 rely on SD-01 for software installed on servers and for infrastructure, configuration and database changes, but the population was merges only. Note: Server software installed by hand on a host is visible only to a host agent or the cloud's run command history. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `internal-tls-enforcement-settings` | NS-02 | NS-02.D | Settings that make internal services and databases refuse unencrypted connections (database parameters, load balancer to service protocol, service mesh), exported from the cloud console, so NS-02.D can be tested by more than reading the standard. Category configuration. | coverage/iam-ep-pe-ns-dm.controls.json NS-02 new_artifacts; coverage/iam-ep-pe-ns-dm.json |
| `licence-exceptions-record` | SD-18 | SD-18.C | SD-18.C: New objective on successor SD-18. Note: Whether a licence fits how the product is sold is a legal judgement. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `log-source-gap-alerts` | LM-02 | LM-02.F | LM-02.F: Split out of LM-02.B; ISO27001:A.8.15 and SOC2:CC2.1 rely on complete logs. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `log-store-retention-and-access-settings` (alias `log-retention-settings`) | LM-02 | LM-02.C | LM-02.C has no settings artifact (only the logging-and-retention-standard document and an interview), so observability.logs_retained fills nothing. Category configuration. Fill partial for both checks. | connectors/operations-checks.md section 2, 4 and decision 5; connectors/datadog.md section 6; coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `output-delivery-log` | SD-16 | SD-16.B, SD-16.C | SD-16.B: New control. SD-16.C: New control. Note: Whether an output reached only the right recipient is shown by the delivery system's own records, read by people. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `processing-error-log` | SD-15 | SD-15.B, SD-15.C | SD-15.B: New control. SD-15.C: New control. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `product-sign-in-settings` | IAM-14 | IAM-14.B, IAM-14.C | Product sign in settings and password storage method, exported by engineering from the product's authentication configuration and the hashing setting in code. Verity cannot read the product's code or configuration; a code scanning connector could check parts later. Category configuration. | coverage/iam-ep-pe-ns-dm.controls.json IAM-14 new_artifacts; coverage/iam-ep-pe-ns-dm.json |
| `production-data-change-log` | SD-17 | SD-17.B | SD-17.B: New control. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `public-storage-settings-export` | NS-04 |  | No artifact names cloud.storage_public_access_blocked. aws.md writes 'NEED cloud_infrastructure: a dated export of public storage settings' and offers alerts-on-drift-that-were-investigated as the other home. The key is an extractor placeholder; no objective is named. | connectors/aws.md section 6 |
| `rebuild-materials-inventory` | BC-01 | BC-01.F | BC-01.F: ISO27001:A.8.13 covers copies of software and systems as well as data. BC-01.A names them; nothing tested them. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `redundancy-configuration-export` | BC-09 | BC-09.B | BC-09.B: New objective on successor BC-09. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `software-component-list-with-licences` | SD-18 | SD-18.B, SD-18.C | SD-18.B: New objective on successor SD-18. SD-18.C: New objective on successor SD-18. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `static-analysis-results-for-merged-changes` | SD-02 | SD-02.F | SD-02.F: ISO27001:A.8.28 and A.8.29 rely on static analysis in the pipeline (rationales on SD-02 and SD-10). No objective tested that it ran. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `storage-versioning-export` | SD-07 | SD-07.D | aws.md writes 'NEED cloud_infrastructure: a dated export of storage versioning' for SD-07.D (durable, versioned storage). azure.md and gcp.md instead fill the existing integrity-check-results (SD-07.B, SD-07.C, SD-07.D) with cloud.storage_versioned, so a new artifact is probably not needed. Key is an extractor placeholder. | connectors/aws.md section 6 |
| `vendor-offboarding-records` | BC-07 | BC-07.E | BC-07.E: Split out of BC-07.D; ISO27001:A.5.22 rationale relies on removal with access revoked. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |
| `vendor-service-level-review` | BC-08 | BC-08.G | BC-08.G: ISO27001:A.5.22 and A.8.21 rationales rely on checking delivered service levels; no objective tested it. | coverage/sd-lm-bc.md (Proposed artifact types); coverage/sd-lm-bc.json |

## 6.10 Content defects

Found by the researchers in shipped content, with what the reconciliation step should do. The most important first;
the full deduplicated list follows.

| Defect | Fix |
|---|---|
| `inventory-of-company-devices` is named by 11 objectives (DM-19.C, EP-01.B, EP-02.B to D, EP-03.B to D, EP-05.B, EP-06.B, EP-07.B), its only source is `devices.enrolled`, it has no person source, and its "where" points at Assets, which has no device type. A passing enrolment check would satisfy encryption, agent, wipe and lock objectives, and a company without an MDM can never satisfy it | Split by what is tested into `device-encryption-report`, `device-protection-agent-report` and `device-wipe-capability-report`, each with its device check and a person source; add a device type to Assets. EP-02.D and EP-03.D have no home in the split yet |
| 26 non document artifacts have no person source, against rule 1 of the evidence model: `acknowledgement-from-every-member-of-staff`, `asset-inventory`, `branch-protection-settings`, `classification-applied-to-systems-and-data`, `control-ownership-register`, `disposal-records-or-certificates`, `executed-data-processing-agreements-for-vendors`, `inventory-of-company-devices`, `log-of-control-deficiencies-with-owner`, `published-security-policies-covering-each-required`, `register-of-external-and-internal-factors`, `register-of-interested-parties-and-what`, `review-and-re-approval-record-for`, `review-that-the-inventory-is-complete`, `risk-assessment-report-with-method-and`, `risk-register-with-owners-ratings-and`, `risks-linked-to-the-controls-that`, `scope-statement-approved-by-leadership`, `security-assessment-for-each-critical-vendor`, `security-communication-plan`, `security-objectives-with-owners-targets-and`, `staff-acknowledgement-of-current-policies`, `statement-of-applicability-showing-every-decision`, `vendor-inventory-with-owner-data-and`, `version-history-and-approval-record-for`, `vulnerability-register-with-remediation-and-accepted` | Add `{"kind": "person"}` to each, or record why a person can never provide it |
| Four person only document artifacts duplicate a `doc-` artifact on the same objective (`change-management-policy` on SD-01.A, `secure-development-lifecycle-policy` on SD-10.A, `incident-response-plan` on LM-07.A, `business-continuity-and-disaster-recovery-plan` on BC-03.A and B) | Fold each into its `doc-` artifact |
| 97 document artifacts list only a person, although a shipped template holds the text (full list below) | Give each a document source with its template, or fold it into the `doc-` artifact (owner decision, 08) |
| Template gaps: missing sections in `access-control-policy`, `third-party-management-policy`, `cryptography-policy`, `endpoint-security-standard`, `engineering-security-standard` (also needs a product sign in section for IAM-14); no template at all for a vulnerability management policy, a backup policy, a subprocessor list or a postmortem | CL-6 template work, or point the objectives at existing sections |
| Checks that reach no artifact, so they cannot move any objective: see 05, 5.8. Shipped examples: `idp.mfa_enforced`, `idp.sso_enforced`, `vcs.org_two_factor_required`, `devices.disk_encrypted`, `devices.screen_lock`, `devices.remote_wipe`, `endpoint.protection_active` | Add them as sources of the artifacts named in the coverage files |
| Artifacts listing only a person though a check exists: `screen-lock-setting-report` (`devices.screen_lock`), `privileged-elevation-and-break-glass-log` (`idp.admins_limited`), `second-factor-enforcement-and-enrolled-users` (`idp.mfa_enforced`), `control-test-results-across-the-observation` (check run history) | Add the check as a source; keep the person |
| `roster-of-joiners-and-leavers-with` is sourced by `people.leavers_deprovisioned`, an account removal check that covers leavers only | Source it from `hr.roster_exported` and `people.joiners_onboarded`; keep the person |
| `management-review-agenda-and-minutes` is given different sources on GOV-15 and GOV-31, which `artifacts.json` cannot express | Split into a quarterly and a yearly artifact |
| `branch-protection-settings` on SD-02.B lacks `vcs.status_checks_required` | Add it |
| `access-request-procedure` (DM-11, a data subject request procedure) sits beside `access-request-and-approval-procedure` (IAM) | Rename to "data-subject-access-request-procedure", with an evidence migration |
| `management-review-agenda-and-minutes` and `internal-audit-or-readiness-assessment-report` are typed configuration | Type them as records |
| `MANAGEMENT_REVIEW_INPUTS` labels follow the standard's list too closely | Rewrite in Verity's words |
| `capabilities.json`: Slack under alerting; Qovery under cloud infrastructure; DigitalOcean missing from asset discovery; HR and device providers `not_planned` while LM-01 text and the coverage files rely on them | See 6.8 |
| Module gaps found in code: the vulnerability register matches assets loosely, drops unmatched findings, lacks first found time, explicit severity maps, scanner verified closure and `external_id`; the GitHub connector reports error instead of insufficient information on a truncated population; Tasks has no incident kind and task templates are not bound to controls; Assets has no device type; assurance records need an engagement; ISO certificates have no structured period fields | Fix before the checks that depend on them ship (phase3-catalogue.md 5.2, D-P3-2) |

### Full list (341 findings after removing exact repeats)

Document artifacts that list only a person although a template holds the text (97 artifacts). Fix: add a
`document` source for the template (and section), or fold the artifact into the `doc-` artifact named on the same objective.

| Artifact | Template holding the text | Controls | Same objective also names | Raised in |
|---|---|---|---|---|
| access-policy-requiring-multi-factor-authentication | access-control-policy | IAM-03 | doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| access-removal-procedure-with-the-timeframe | joiner-mover-leaver-checklists | IAM-12 | doc-joiner-mover-leaver-checklists | coverage/iam-ep-pe-ns-dm.md |
| access-request-and-approval-procedure | access-control-policy | IAM-01 | doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| access-request-procedure | privacy-requests-and-complaints-procedure | DM-11 | doc-privacy-requests-and-complaints-procedure | coverage/iam-ep-pe-ns-dm.md |
| access-review-procedure | access-control-policy | IAM-02, IAM-07 | doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| alerting-standard | infrastructure-security-standard, operations-security-policy | BC-04, LM-09 |  | coverage/sd-lm-bc.md |
| appointment-or-role-charter-naming-the | information-security-roles-and-responsibilities | GOV-10, GOV-21 |  | coverage/gov-cs-hr.json |
| approved-code-of-conduct | code-of-conduct | GOV-04 |  | coverage/gov-cs-hr.json |
| approved-configuration-baseline | infrastructure-security-standard, operations-security-policy | LM-03, NS-04, NS-14 |  | coverage/iam-ep-pe-ns-dm.md, coverage/sd-lm-bc.md |
| background-check-policy | human-resource-security-policy | HR-01 |  | coverage/gov-cs-hr.json |
| backup-policy-covering-scope-frequency-and | business-continuity-and-disaster-recovery-plan, operations-security-policy | BC-01, BC-02, DM-08, DM-16 |  | coverage/iam-ep-pe-ns-dm.md, coverage/sd-lm-bc.md |
| breach-notification-procedure-and-templates | incident-response-plan, security-communication-plan | DM-01 | doc-incident-response-plan, doc-security-communication-plan | coverage/iam-ep-pe-ns-dm.md |
| charter-of-the-board-or-executive | oversight-body-charter | GOV-02 |  | coverage/gov-cs-hr.json |
| competence-requirements-for-each-security-role | competence-and-awareness-procedure | HR-09 |  | coverage/gov-cs-hr.json |
| confidentiality-and-ip-agreement-template | human-resource-security-policy | HR-02 |  | coverage/gov-cs-hr.json |
| consent-withdrawal-process-and-records | personal-data-handling-procedure | DM-03 | doc-personal-data-handling-procedure | coverage/iam-ep-pe-ns-dm.md |
| contact-list-for-authorities-and-security | security-communication-plan | CS-07 |  | coverage/gov-cs-hr.json |
| contractor-onboarding-and-offboarding-procedure | joiner-mover-leaver-checklists | HR-03 |  | coverage/gov-cs-hr.json |
| correction-procedure | privacy-requests-and-complaints-procedure | DM-05 | doc-privacy-requests-and-complaints-procedure | coverage/iam-ep-pe-ns-dm.md |
| current-privacy-notice | privacy-notice-outline | DM-03, DM-09, DM-12, DM-14, DM-15 | doc-privacy-notice-outline | coverage/iam-ep-pe-ns-dm.md |
| data-classification-policy | data-management-policy | DM-04, DM-18 | doc-data-management-policy | coverage/iam-ep-pe-ns-dm.md |
| data-retention-schedule | data-management-policy | DM-08, DM-15, SD-07, SD-14 | doc-data-management-policy | coverage/iam-ep-pe-ns-dm.md, coverage/sd-lm-bc.md |
| dependency-vulnerability-triage-standard-with-timeframes | engineering-security-standard, operations-security-policy | SD-03 |  | coverage/sd-lm-bc.md |
| deployment-procedure-stating-who-may-release | change-management-procedure, engineering-security-standard | SD-13 |  | coverage/sd-lm-bc.md |
| description-of-the-confidential-reporting-mechanism | code-of-conduct, information-security-policy | CS-05 |  | coverage/gov-cs-hr.json |
| device-management-policy | endpoint-security-standard | EP-03 | doc-endpoint-security-standard | coverage/iam-ep-pe-ns-dm.md |
| disciplinary-procedure | code-of-conduct, human-resource-security-policy | GOV-11 |  | coverage/gov-cs-hr.json |
| document-control-procedure-covering-approval-versions | document-control-procedure | GOV-28 | doc-document-control-procedure | coverage/gov-cs-hr.json, coverage/gov-cs-hr.md |
| emergency-change-procedure | change-management-procedure | SD-04 |  | coverage/sd-lm-bc.md |
| encryption-in-transit-standard | cryptography-policy, infrastructure-security-standard | NS-02 | doc-cryptography-policy, doc-infrastructure-security-standard | coverage/iam-ep-pe-ns-dm.md |
| encryption-standard-stating-what-is-encrypted | cryptography-policy, infrastructure-security-standard | NS-01 | doc-cryptography-policy, doc-infrastructure-security-standard | coverage/iam-ep-pe-ns-dm.md |
| endpoint-encryption-policy | endpoint-security-standard | EP-02 | doc-endpoint-security-standard | coverage/iam-ep-pe-ns-dm.md |
| endpoint-protection-standard | endpoint-security-standard | EP-01 | doc-endpoint-security-standard | coverage/iam-ep-pe-ns-dm.md |
| environment-architecture-showing-separation | secure-development-policy | SD-12 |  | coverage/sd-lm-bc.md |
| escalation-policy | incident-response-plan | LM-08 |  | coverage/sd-lm-bc.md |
| event-triage-procedure | incident-response-plan | LM-04 | doc-incident-response-plan | coverage/sd-lm-bc.md |
| hardening-standard-such-as-cis-or | infrastructure-security-standard, operations-security-policy | NS-04, NS-14 | doc-infrastructure-security-standard, doc-operations-security-policy | coverage/iam-ep-pe-ns-dm.md |
| hazard-assessment-and-protections-for-each | site-and-equipment-protection-standard | PE-03 | doc-site-and-equipment-protection-standard | coverage/iam-ep-pe-ns-dm.md |
| incident-procedure-showing-the-notification-timeframes | incident-response-plan | CS-01 |  | coverage/gov-cs-hr.json |
| input-validation-standard | engineering-security-standard, processing-integrity-procedure | SD-05 |  | coverage/sd-lm-bc.md |
| internal-audit-program-setting-frequency-methods | internal-audit-procedure | GOV-13 |  | coverage/gov-cs-hr.json |
| job-descriptions-that-state-security-responsibilities | competence-and-awareness-procedure | HR-04, HR-07, HR-09 |  | coverage/gov-cs-hr.json |
| key-management-policy | cryptography-policy, infrastructure-security-standard | NS-06 | doc-cryptography-policy, doc-infrastructure-security-standard | coverage/iam-ep-pe-ns-dm.md |
| leakage-prevention-and-sharing-settings-in | operations-security-policy | DM-19 | doc-operations-security-policy | coverage/iam-ep-pe-ns-dm.md |
| logging-and-retention-standard | infrastructure-security-standard, operations-security-policy | LM-02 |  | coverage/sd-lm-bc.md |
| map-of-the-management-processes-and | isms-operating-plan | GOV-23 |  | coverage/gov-cs-hr.json |
| masking-standard-listing-fields-methods-and | operations-security-policy | DM-18 | doc-operations-security-policy | coverage/iam-ep-pe-ns-dm.md |
| matrix-of-conflicting-duties | access-control-policy | IAM-09, IAM-13 | doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| offboarding-checklist | joiner-mover-leaver-checklists | HR-05 |  | coverage/gov-cs-hr.json |
| onboarding-checklist | joiner-mover-leaver-checklists | CS-03, HR-06 |  | coverage/gov-cs-hr.json |
| operating-plan-listing-activities-owners-and | isms-operating-plan | GOV-29 |  | coverage/gov-cs-hr.json |
| password-policy | access-control-policy | IAM-06 | doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| patch-management-policy-with-timeframes | endpoint-security-standard, operations-security-policy | EP-04, NS-13 | doc-endpoint-security-standard, doc-operations-security-policy | coverage/iam-ep-pe-ns-dm.md |
| peer-review-standard-in-the-development | engineering-security-standard | SD-06 |  | coverage/sd-lm-bc.md |
| person-only document artifacts (summary) | see finding in the coverage file |  |  | coverage/iam-ep-pe-ns-dm.md |
| physical-access-policy-for-offices | physical-security-policy | PE-02 | doc-physical-security-policy | coverage/iam-ep-pe-ns-dm.md |
| pipeline-storage-design-showing-stages-and | processing-integrity-procedure | SD-07 |  | coverage/sd-lm-bc.md |
| policy-against-production-data-in-lower | operations-security-policy, secure-development-policy | DM-13 | doc-secure-development-policy | coverage/iam-ep-pe-ns-dm.md |
| policy-requiring-a-password-manager-for | acceptable-use-policy, access-control-policy | IAM-05 | doc-acceptable-use-policy, doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| postmortem-for-each-significant-incident | see finding in the coverage file |  |  | coverage/sd-lm-bc.md |
| privacy-inquiry-and-complaint-procedure | privacy-requests-and-complaints-procedure | DM-14 | doc-privacy-requests-and-complaints-procedure | coverage/iam-ep-pe-ns-dm.md |
| procedure-for-lost-devices-and-offboarding | endpoint-security-standard, joiner-mover-leaver-checklists | EP-05 | doc-endpoint-security-standard | coverage/iam-ep-pe-ns-dm.md |
| procedure-for-raising-and-deciding-improvements | corrective-action-procedure | GOV-30 |  | coverage/gov-cs-hr.json |
| procedure-for-responding-to-threat-detection | incident-response-plan, infrastructure-security-standard | NS-05 | doc-infrastructure-security-standard | coverage/iam-ep-pe-ns-dm.md |
| procedure-for-rotating-exposed-secrets | engineering-security-standard, infrastructure-security-standard | SD-11 |  | coverage/sd-lm-bc.md |
| procedure-listing-what-triggers-a-risk | risk-assessment-methodology | GOV-03 |  | coverage/gov-cs-hr.json |
| processing-specifications-covering-inputs-outputs-and | processing-integrity-procedure | SD-09, SD-16 |  | coverage/sd-lm-bc.md |
| published-reporting-channel-for-staff-and | incident-response-plan, security-communication-plan | CS-03 |  | coverage/gov-cs-hr.json |
| published-security-availability-and-privacy-commitments | privacy-notice-outline | CS-02, GOV-22 |  | coverage/gov-cs-hr.json |
| reconciliation-procedure | processing-integrity-procedure | SD-08 |  | coverage/sd-lm-bc.md |
| record-of-who-sits-on-the | oversight-body-charter | GOV-02 |  | coverage/gov-cs-hr.json |
| recovery-procedures | business-continuity-and-disaster-recovery-plan, incident-response-plan, operating-procedure-template | LM-06 |  | coverage/sd-lm-bc.md |
| register-of-contractual-regulatory-and-certification | context-and-interested-parties | GOV-05 |  | coverage/gov-cs-hr.json |
| register-of-external-and-internal-factors | context-and-interested-parties | GOV-23, GOV-24 |  | coverage/gov-cs-hr.json |
| register-of-interested-parties-and-what | context-and-interested-parties | GOV-05, GOV-23, GOV-25 |  | coverage/gov-cs-hr.json |
| register-of-the-purposes-personal-information | personal-data-handling-procedure | DM-07, DM-12, DM-15 | doc-personal-data-handling-procedure | coverage/iam-ep-pe-ns-dm.md |
| remote-access-standard | infrastructure-security-standard, remote-working-policy | NS-11 | doc-infrastructure-security-standard, doc-remote-working-policy | coverage/iam-ep-pe-ns-dm.md |
| role-and-access-matrix | access-control-policy | DM-12, DM-18, HR-04, IAM-08 | doc-access-control-policy | coverage/gov-cs-hr.json, coverage/iam-ep-pe-ns-dm.md |
| role-definitions-approved-by-their-owners | access-control-policy | IAM-08 | doc-access-control-policy | coverage/iam-ep-pe-ns-dm.md |
| role-descriptions-for-security-and-compliance | information-security-roles-and-responsibilities | GOV-21, HR-09 |  | coverage/gov-cs-hr.json |
| roles-and-contact-list | incident-response-plan | LM-07, LM-10 |  | coverage/sd-lm-bc.md |
| scope-statement-approved-by-leadership | isms-scope-statement | GOV-23, GOV-24 |  | coverage/gov-cs-hr.json |
| screen-lock-standard | endpoint-security-standard | EP-06 | doc-endpoint-security-standard | coverage/iam-ep-pe-ns-dm.md |
| secrets-management-standard | engineering-security-standard, infrastructure-security-standard | NS-09 | doc-infrastructure-security-standard | coverage/iam-ep-pe-ns-dm.md |
| secure-disposal-procedure | asset-management-policy, data-management-policy | DM-16, EP-08 | doc-asset-management-policy, doc-data-management-policy | coverage/iam-ep-pe-ns-dm.md |
| security-communication-plan | security-communication-plan | CS-06 |  | coverage/gov-cs-hr.json |
| security-objectives-with-owners-targets-and | security-objectives-plan | GOV-24, GOV-26 |  | coverage/gov-cs-hr.json |
| service-commitments-and-system-requirements-shared | soc2-system-description | CS-02, GOV-05, GOV-22 |  | coverage/gov-cs-hr.json |
| session-timeout-standard | infrastructure-security-standard | IAM-11 | doc-infrastructure-security-standard | coverage/iam-ep-pe-ns-dm.md |
| subprocessor-list-shared-with-customers | see finding in the coverage file | BC-06 |  | coverage/sd-lm-bc.md |
| system-description-covering-boundary-services-infrastructure | soc2-system-description | GOV-22 |  | coverage/gov-cs-hr.json |
| testing-standard-stating-what-must-pass | engineering-security-standard | SD-02 |  | coverage/sd-lm-bc.md |
| threat-sources-and-the-routine-for | operations-security-policy | LM-12 |  | coverage/sd-lm-bc.md |
| training-content-and-schedule | competence-and-awareness-procedure | CS-03, EP-07, HR-08 |  | coverage/gov-cs-hr.json, coverage/iam-ep-pe-ns-dm.md |
| trusted-time-sources-and-how-systems | infrastructure-security-standard, operations-security-policy | NS-12 | doc-infrastructure-security-standard, doc-operations-security-policy | coverage/iam-ep-pe-ns-dm.md |
| vulnerability-management-policy-with-timeframes | operations-security-policy | GOV-16, LM-11, LM-13 |  | coverage/gov-cs-hr.json, coverage/gov-cs-hr.md, coverage/sd-lm-bc.md |
| web-filtering-standard-covering-blocked-categories | operations-security-policy | EP-07 | doc-operations-security-policy | coverage/iam-ep-pe-ns-dm.md |

Other defects, by kind:

#### Artifact (30)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| LM-02.C | LM-02.C has only logging-and-retention-standard (a document) and an interview; no settings artifact exists, so observability.logs_retained cannot move any objective. | Add artifact log-retention-settings (configuration; sources check observability.logs_retained, cloud.audit_logging; person) to LM-02.C. | connectors/operations-checks.md section 2; connectors/datadog.md section 6 |
| access-request-procedure | The key names the data subject access request procedure (DM-11), beside access-request-and-approval-procedure for IAM; easy to confuse. | Rename to data-subject-access-request-procedure, with a migration of any evidence that references it. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 9 |
| account-list-export | On HR-03 the account list must come from the customer's systems; Verity's own members list is not this population. | Keep idp.access_list_exported as the source; do not substitute the members list. | coverage/gov-cs-hr.json notes, HR-03 |
| artifacts naming unimplemented checks | Many artifacts name catalogued checks that have no implementation (tickets.changes_linked, ci.*, vcs.unreviewed_merges_recorded, vcs.code_scanning_enabled, alerts.*, scanner.scans_current, cloud.*, idp.*), for example change-requests-with-approval-for-a, test-run-results-for-a-sample, emergency-changes-with-their-after-the, scan-reports, recovery-records-for-incidents, inventory-of-service-accounts-and-keys, asset-inventory. In practice they are person only today. | The control page must say provide it for now (EC-6) until a provider implements the check. | coverage/sd-lm-bc.md (Content problems found) |
| asset-inventory, branch-protection-settings | Extractor lookup: both artifacts list only check sources and no person source, while aws.md section 6 restates rule 1 of 01-evidence-model.md that 'person' stays as a source on every artifact. | Add {"kind": "person"} to both artifacts' sources. | extractor lookup of artifacts.json; rule quoted in connectors/aws.md section 6 |
| branch-protection-settings | On SD-02.B the shipped check sources are vcs.default_branch_protected and vcs.review_required, but the check that shows required status checks is vcs.status_checks_required, which the plan uses here as full. Extractor's reading of the SD-02 table; the document does not call it out. | Add vcs.status_checks_required to the artifact's check source. | coverage/sd-lm-bc.md (SD-02 table) |
| business-continuity-and-disaster-recovery-plan | Person only document artifact that duplicates doc-business-continuity-and-disaster-recovery-plan on BC-03.A and B (and on the proposed BC-09.A). | Give it the template source business-continuity-and-disaster-recovery-plan, or retire it. | coverage/sd-lm-bc.md (Content problems found; BC-03, BC-09) |
| change-management-policy | Person only document artifact that duplicates doc-change-management-procedure on SD-01.A (and is used on SD-01.E). A workspace is asked for the same document twice. | Give it the template source change-management-procedure, or retire it in favour of the doc- artifact. | coverage/sd-lm-bc.md (Content problems found; SD-01) |
| control-test-results-across-the-observation | Person only, although Verity keeps every check run (GOV-06). | Source it from the check run history with verity.checks.runs_continuous. | coverage/gov-cs-hr.md Content problems and gaps found |
| incident-procedure-showing-the-notification-timeframes | Duplicates doc-incident-response-plan on the same objective (CS-01.A); it is person only. | Merge into doc-incident-response-plan, or give it the incident-response-plan template source. | coverage/gov-cs-hr.md Content problems and gaps found |
| incident-response-plan | Person only document artifact that duplicates doc-incident-response-plan on LM-07.A (also used on LM-07.E and the new LM-07.F). | Give it the template source incident-response-plan, or retire it. | coverage/sd-lm-bc.md (Content problems found; LM-07) |
| internal-audit-or-readiness-assessment-report | Typed configuration; it is a record. | Change its category to record. | coverage/gov-cs-hr.md Content problems and gaps found |
| inventory-of-company-devices | AR-EP-06 is named by 11 objectives (DM-19.C, EP-01.B, EP-02.B, EP-02.C, EP-02.D, EP-03.B, EP-03.C, EP-03.D, EP-05.B, EP-06.B, EP-07.B). Its only source is devices.enrolled and it has no person source. Every artifact uses combine any, so under rule B a passing enrolment check would satisfy the encryption, agent, wipe, screen lock and web filter objectives, and a company without an MDM could never satisfy it at all, against evidence model rule 1.3.1. | Split by what is tested: inventory-of-company-devices keeps enrolment and reconciliation (EP-03.B, EP-03.C) with devices.enrolled, devices.staff_have_managed_device, devices.assigned_to_active_staff and a person source; new device-encryption-report (EP-02.B, EP-02.C); new device-protection-agent-report (EP-01.B); new device-wipe-capability-report (EP-05.B); EP-06.B uses screen-lock-setting-report; EP-07.B uses report-of-filter-coverage-and-blocked; DM-19.C uses leakage-prevention-and-sharing-settings-in. Every one keeps a person source (decision D-DEV-5). | mdm-and-endpoint-strategy.md section 4 F1 |
| inventory-of-company-devices | Gap found while extracting: the F1 split does not say where EP-02.D (exceptions for unencrypted devices) and EP-03.D (baseline applied, drift fixed) go. Both test inventory-of-company-devices today. | Likely EP-02.D to device-encryption-report (plus approved-exceptions) and EP-03.D to the baseline reports (patch-compliance-report, screen-lock-setting-report) plus a home for devices.firewall_enabled. Needs the control mapping research to confirm. | mdm-and-endpoint-strategy.md section 4 F1 (gap noted by the extractor) |
| inventory-of-company-devices | Sources list only the check devices.enrolled and its 'where' says it lives in the Assets module, but Assets has no endpoint or device type. It is used by EP-01, EP-02, EP-03, EP-05, EP-06, EP-07 and DM-19, where the planned sources are endpoint.protection_active, devices.disk_encrypted and devices.remote_wipe (none listed as sources), and EP-07 and DM-19 plan a person source (device management export or a sheet) that the artifact lacks. Device management is not in the signed catalogue, so today nothing can fill it. | Add the device checks and a person source to its sources, and add an endpoint asset type before device management connectors land. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 5; coverage/iam-ep-pe-ns-dm.json |
| log-of-control-deficiencies-with-owner | Its only sources are checks (tickets.remediation_tracked, verity.tasks.remediation_in_sla); it has no person source, against evidence model rule 1 that every artifact keeps one. Seen in operations-checks section 4 (Today column) and artifacts.json. | Add a person source. | connectors/operations-checks.md section 4 |
| management-review-agenda-and-minutes | Typed configuration; it is a record. | Change its category to record. | coverage/gov-cs-hr.md Content problems and gaps found |
| management-review-agenda-and-minutes | Found during extraction: the plan gives this one artifact different sources per control (GOV-15 row: verity.assurance.management_review_held, without verity.management_review.in_12_months; GOV-31 row: in_12_months and management_review_inputs_recorded, without management_review_held). artifacts.json sources are per artifact, not per control, so this cannot be represented as is. The shipped where text says quarterly meeting notes. | Split into a quarterly management review minutes artifact (GOV-15) and a yearly management review record artifact (GOV-31), or union the sources. | coverage/gov-cs-hr.json |
| privileged-elevation-and-break-glass-log | Person only, although idp.admins_limited can show PIM eligible versus active roles and activation events on Entra with P2. | Add check idp.admins_limited as a source (Entra with PIM only), keep person. | connectors/identity-checks.md section 3; connectors/entra-id.md section 6 |
| report-of-filter-coverage-and-blocked | EP-07 (harmful website blocking, ISO A.8.23 full) has no automated source; the artifact is person only. | NEED network_edge plus device_management: every managed device appears in the DNS or web filter's device list (EP-07.B, partial). Owned by operations research. | mdm-and-endpoint-strategy.md section 4 F7 and section 5.4 |
| roster-of-joiners-and-leavers-with | Filled by people.leavers_deprovisioned, a check about account removal, so a passing removal check stands in for the roster itself. The artifact is named by 17 objectives. | Source it from hr.roster_exported (fills full, it is the roster) and keep person. Keep people.leavers_deprovisioned on removal-records-for-a-sample-of, where it already is. | mdm-and-endpoint-strategy.md section 4 F3; connectors/hr-systems.md section 10 |
| roster-of-joiners-and-leavers-with | Names people.leavers_deprovisioned as its source, which covers leavers only; joiners have no source. Its category is configuration. | Add people.joiners_onboarded as a source and the hr_system need; until an HR source exists use the roster import (open question 1) and the iam members joined and disabled report as a proxy. | coverage/gov-cs-hr.md Content problems and gaps found |
| screen-lock-setting-report | Lists only a person source although devices.screen_lock exists, so the check would never reach its artifact. | Add devices.screen_lock as a check source; keep person. | mdm-and-endpoint-strategy.md section 4 F2 |
| second-factor-enforcement-and-enrolled-users; applications-inside-and-outside-single-sign-on | Both are person only today. idp.mfa_enforced, vcs.org_two_factor_required and idp.sso_enforced feed no artifact at all, while the phase 3 document adds apps.mfa_enforced and apps.sso_enforced as sources. | When the apps.* checks are added as sources, add idp.mfa_enforced and vcs.org_two_factor_required to the IAM-03 artifact and idp.sso_enforced to the IAM-04 artifact (extraction cross check; identity research may already raise it). | artifacts.json cross check while verifying connectors/phase3-catalogue.md 8.2 |
| secure-development-lifecycle-policy | Person only document artifact that duplicates doc-secure-development-policy on SD-10.A. | Give it the template source secure-development-policy, or retire it. | coverage/sd-lm-bc.md (Content problems found; SD-10) |
| security-assessment-for-each-critical-vendor | Section 8.2 says the person source stays, but artifacts.json gives this artifact only a check source (verity.vendors.assessed_in_cadence). | Confirm whether a person source should be added (extraction cross check). | connectors/phase3-catalogue.md 8.2 vs artifacts.json |
| security-incident-register | Where text says Tasks module, one task per incident, but Tasks has no incident marker and no notice decision field. | Ship a Security incident task template with a structured notice decision, or the Phase 3.1 Incidents module; then add verity.incidents.registered as a source. | coverage/sd-lm-bc.md (Content problems found) |
| security-objectives-with-owners-targets-and | Its where text says the objectives are tasks (one task per objective), but its source is a document check (verity.objectives.documented) (GOV-24, GOV-26). | Add the Tasks source with verity.tasks.owned_and_dated and the template security-objectives-plan; keep the document check. | coverage/gov-cs-hr.md Content problems and gaps found |
| signed-agreements-for-a-sample-of | An acknowledgement campaign is not a signed contract and must not be offered as one (HR-02, HR-03). | Keep the source as esignature or HR system needs plus person uploads. | coverage/gov-cs-hr.json notes |
| vulnerability-register-with-remediation-and-accepted | Section 8.2 says 'The person source stays on each', but artifacts.json gives this artifact only a check source (verity.vulns.within_sla), no person source. | Confirm whether a person source should be added (found by extraction cross check, not stated in the document). | connectors/phase3-catalogue.md 8.2 vs artifacts.json |

#### Check (38)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| 14 connector checks in IAM, EP, NS | All 14 checks.json links from a connector check to a control in these families are full with the rationale 'which is what the control states' (cloud.encryption_at_rest NS-01, cloud.admin_ports_closed NS-08, idp.sso_enforced IAM-04, idp.password_policy IAM-06, idp.session_timeout IAM-11, people.leavers_deprovisioned IAM-12, vault.everyone_enrolled IAM-05, tickets.access_requests_approved IAM-01, edge.waf_enabled NS-10, edge.zero_trust_access NS-11, devices.enrolled EP-03, devices.disk_encrypted EP-02, devices.screen_lock EP-06, endpoint.protection_active EP-01). EC-3 is broken. | Make all 14 partial with a rationale naming what remains (see downgrades). | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 1 |
| NEED (proposed SD-17): database audit logging on for every production database | Neon's settings.audit_log_level may meet this coverage need, but its meaning is unverified. | Verify audit_log_level before mapping Neon to the SD-17 need. | connectors/phase3-catalogue.md 4.7 |
| NEED cloud_infrastructure: preview and staging deployments require sign in | No check verifies that lower environments (preview and staging deployments) are not public (SD-12.C, DM-13.B). Raised for all section 4 platforms; Vercel exposes ssoProtection and passwordProtection on projects [P27], others unverified. Cloud research owns the cloud. prefix, so no key was proposed. | Cloud research to propose a cloud.* key for this need. | connectors/phase3-catalogue.md 4 (intro) |
| SendGrid enforced TLS | Section 7.2 says SendGrid proves whether outbound TLS is enforced (NS-02 partial, for one channel; scope user.settings.enforced_tls.read) but names no check key for it. | Merger to decide whether a check is needed; otherwise it stays person evidence. | connectors/phase3-catalogue.md 7.2 |
| alerts.acknowledged_in_time | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of sample-of-evaluated-events-with-the (LM-04) and on-call-schedule (LM-08.D), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| alerts.security_routed | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of review-of-alert-tuning (LM-09.B, C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| assets.resources_registered | resource_type is cloud_resource and its rationale says devices need their own source, so it cannot carry MDM devices. | Reuse it for devices once F5 is decided, with MDM providers (intune, jamf, kandji, gws) added to the asset_discovery capability. | mdm-and-endpoint-strategy.md section 4 F6 |
| cloud.audit_logging | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of the proposed log-retention-settings (LM-02.C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| cloud.secrets_managed | The shipped description says application secrets are held in a secrets manager, not in configuration or code. No cloud connector can show the second half without reading secret values, which Verity refuses; the predicate on every cloud is only 'a secrets manager is in use in each production scope'. | Reword the description to what is checked, and keep the configuration half with vcs.secret_scanning_enabled and a person (NS-09 stays partial). | connectors/aws.md sections 5.1 and 8; connectors/azure.md 5.1; connectors/gcp.md 5.1 |
| devices.disk_encrypted, devices.remote_wipe, devices.screen_lock, endpoint.protection_active | Lookup in artifacts.json: no artifact lists these checks as a source (inventory-of-company-devices lists only devices.enrolled; screen-lock-setting-report is person only). Once implemented they would reach no objective. | Resolved by the F1 split and F2: device-encryption-report, device-wipe-capability-report, device-protection-agent-report and screen-lock-setting-report take them. | mdm-and-endpoint-strategy.md section 4 F1, F2 (confirmed by lookup in objectives/artifacts.json) |
| edge.minimum_tls | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of public-endpoint-tls-scan (NS-02.B, C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| edge.waf_enabled | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of review-of-web-application-firewall-rules (NS-10.B, C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| edge.zero_trust_access | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of remote-access-settings-and-members (NS-11.B, C, D), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.admin_mfa_phishing_resistant | azure.md cites this key for Azure owners and Global Administrators, but it is not in checks.json; it is proposed in entra-id.md. | The merger should make sure the identity part defines it, since cloud.root_account_mfa on Azure points to it. | connectors/azure.md 5.1 |
| idp.connected_apps_known | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of review-of-newly-discovered-applications (BC-05.B), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.groups_drive_access | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of group-and-role-membership-export (IAM-08.B, C, IAM-09.B), not on Google, keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.mfa_enforced | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of second-factor-enforcement-and-enrolled-users (IAM-03.B, D, E), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.password_policy | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of identity-provider-password-settings (IAM-06.B, C), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.session_timeout | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of session-limit-settings-export (IAM-11.B; Okta partly C), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.sso_enforced | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of applications-inside-and-outside-single-sign-on (IAM-04.B), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| idp.stale_accounts | The proposed provider content example names requirement check idp.stale_accounts, which does not exist. | Use idp.no_inactive_accounts. | 02-integration-model.md section 2.5 |
| observability.anomaly_monitors | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of review-of-alert-tuning (LM-09.B, C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| observability.capacity_trends | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of capacity-review (BC-04.B, C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| observability.logs_retained | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of the proposed log-retention-settings (LM-02.C), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| observability.processing_monitored | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of reconciliation-results-and-how-exceptions-were (SD-08.B), keeping the person source. | connectors/operations-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| people.joiners_onboarded | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of completed-checklists-for-a-sample-of (HR-06.B), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| people.leavers_deprovisioned | Needs an HR source, which is in no signed phase, and cannot see systems outside single sign on (IAM-12.D). Its full link to IAM-12 can never be met. | Partial, plus the CSV roster import of control-framework-requirements question 1. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 2 |
| people.leavers_deprovisioned, people.joiners_onboarded | Both need an hr_system source and every hr_system provider is not_planned, so neither can run in the signed scope, although people.leavers_deprovisioned maps IAM-12 full. | The roster CSV import as the interim hr_system provider roster_import (D-HR-1), then HR connectors on the extension. | mdm-and-endpoint-strategy.md section 2; connectors/hr-systems.md section 9 |
| scanner.scans_current | Mapped to EP-04, which after the split is company devices only; it proves server and application scanning. | Move the mapping to NS-13. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Splits |
| vault.everyone_enrolled | No artifact in artifacts.json lists this existing check as a source (verified during extraction), so the engine never counts it and it moves no objective. | Add it as a check source of password-manager-members-against-staff-list (IAM-05.B), keeping the person source. | connectors/identity-checks.md section 3/4; connectors/identity-checks.md section 5 last row |
| vcs.default_branch_protected | The built GitHub connector does not read a ruleset's bypass list (the connector README says so), so the check can pass on a ruleset that every admin bypasses. | Read GET /repos/{o}/{r}/rulesets/{id} (Metadata read) and add vcs.protection_bypass_limited. | connectors/github.md section 2.1 |
| vcs.merged_changes_reviewed | Direct pushes to the default branch are not looked for: the check reads merged pull requests only, so it can pass while unreviewed code reached the branch (empty is not proof). | Read rule suites (GET /repos/{o}/{r}/rulesets/rule-suites, Administration read, rule_suite_result=bypass, up to a month) and, only if D-GH-3 accepts Contents read, default branch commits not linked to a pull request; feed both into vcs.unreviewed_merges_recorded. Until then the result should say 'every pull request was reviewed'. | connectors/github.md sections 2.1 and 8 |
| vcs.merged_changes_reviewed | Stale approvals (given before later commits) are reported but not judged; they count under GitHub's rules. | Add vcs.approval_resets_on_change for the setting and keep the note on the evidence. | connectors/github.md section 2.1 |
| vcs.status_checks_required | Passes when any context is required, so a required lint job satisfies 'tests must pass'. | Keep the predicate (it is the setting), print the required contexts on the result, and judge the operating side with ci.required_checks_passed. | connectors/github.md section 2.1 |
| verity.assets.disposal_recorded | Mapped to DM-16 (data deletion) although it proves equipment disposal, which the split moves to EP-08. | Move the mapping to EP-08 (owner decision). | coverage/iam-ep-pe-ns-dm.controls.json DM-16 |
| verity.policies.acknowledged | Appendix C of control-framework-requirements.md gives it a 95 percent target; checks.json describes an all members rule. One of them is stale. | Decide the rule and update the stale one (see decisions). | coverage/gov-cs-hr.md Content problems and gaps found |
| verity.policies.reviewed | The artifact published-security-policies-covering-each-required relies on verity.policies.reviewed, which passes on one published document (guided onboarding finding LD-04). verity.documents.required_present (CL-5) is still not in checks.json. | Add verity.documents.required_present and list it on the artifact next to policies.reviewed. | coverage/gov-cs-hr.md Content problems and gaps found |
| verity.vulns.within_sla | Mapped to EP-04, which after the split is company devices only; vulnerability SLA belongs to server and image patching. | Move the mapping to NS-13 (LM-11 mapping stays). | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Splits |

#### Mapping (20)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| 22 shipped checks | Extractor lookup: these shipped checks are named by no artifact today, so none of them changes an objective: vcs.status_checks_required, vcs.secret_scanning_enabled, vcs.dependency_alerts_enabled, vcs.org_two_factor_required, vcs.code_scanning_enabled, cloud.encryption_at_rest, cloud.tls_in_transit, cloud.default_deny_ingress, cloud.admin_ports_closed, cloud.hardening_baseline, cloud.threat_detection, cloud.network_segmented, cloud.secrets_managed, cloud.backups_enabled, cloud.capacity_alarms, cloud.audit_logging, cloud.config_changes_recorded, cloud.root_account_mfa, cloud.environments_separated, cloud.storage_versioned, cloud.storage_lifecycle, ci.production_deploys_controlled. | The section 6 artifact proposals in the six documents cover all of them except ci.production_deploys_controlled (see existing_check_changes); github.md names the problem only for vcs.org_two_factor_required. | extractor lookup of artifacts.json; connectors/github.md section 6 |
| CS-06 | CS-06 has no SOC 2 mapping (noted while tracing the Slack needs). | Review the SOC 2 mapping for CS-06. | connectors/slack.md section 7 |
| ISO27001:A.8.20 on NS-04 | The NS-04 rationale for A.8.20 describes network equipment only. | Remove A.8.20 from NS-04 and map it partial to the proposed NS-14. | coverage/iam-ep-pe-ns-dm.controls.json NS-04 |
| LM-08 | LM-08 (on call) has no ISO 27001 mapping, so PagerDuty's strongest evidence reaches ISO only through LM-04, LM-07 and LM-09. | A mapping question for the ISO pack (not a connector gap). | connectors/operations-checks.md section 7; connectors/pagerduty.md section 7; connectors/sentry.md section 7 |
| LM-08 | No ISO 27001 mapping, so an ISO only workspace would not see on call cover. | Add ISO27001:A.5.24 (partial). | coverage/sd-lm-bc.md (Content problems found; Mapping changes) |
| LM-11 | SOC2:CC7.1 and ISO27001:A.8.8 are full on LM-11, which bundles discovery coverage with triage, remediation and acceptance (different owners, cadences and failure conclusions). | Split out LM-13 and change LM-11 coverage to partial. | coverage/sd-lm-bc.md (Proposed control changes, LM-11) |
| LM-12 | Sits in the ISO pack, so SOC 2 workspaces cannot adopt it (CL-10). | Move it out of the ISO pack and add SOC2:CC7.1 (partial). | coverage/sd-lm-bc.md (Content problems found; Mapping changes) |
| SD-05 | Onboarding lists SD-05 as on demand when Processing Integrity is elected, but it maps ISO27001:A.8.26 and A.8.28, which apply to any ISO workspace. | Make SD-05 adoptable without Processing Integrity. | coverage/sd-lm-bc.md (Content problems found) |
| SD-08 | SD-08 has no ISO 27001 mapping in the current pack. | Review in the ISO pack. | connectors/operations-checks.md section 7; connectors/sentry.md section 7 |
| SOC2:CC6.3 on IAM-02 and IAM-08 | Mapped full from both controls; two full links cannot both be true and neither alone authorizes, changes and removes access. | Partial on both. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Mapping changes |
| artifacts with only partial sources | Found during extraction, not stated in the document: these artifacts have no person, document or full source in the plan, only module reports and checks that fill partial: approval-of-each-accepted-risk (GOV-07, GOV-12, GOV-19); asset-inventory (GOV-14, GOV-18, GOV-22); contractor-register-with-start-and-end (HR-02, HR-03); fraud-risk-assessment-covering-insider-misuse (GOV-12); log-of-control-deficiencies-with-owner (GOV-01, GOV-06, GOV-08, GOV-13, GOV-14, GOV-29); published-security-policies-covering-each-required (CS-04, GOV-01, GOV-17); remediation-plan-for-the-gaps-found (GOV-13); risk-assessment-report-with-method-and (GOV-12, GOV-18, GOV-24); risk-register-with-owners-ratings-and (GOV-03, GOV-07, GOV-18, GOV-19, GOV-20, GOV-27); risks-linked-to-the-controls-that (GOV-07, GOV-12); security-assessment-for-each-critical-vendor (GOV-29); staff-acknowledgement-of-current-policies (CS-04, CS-05, CS-06, GOV-21, GOV-32); treatment-plan-with-owners-and-due (GOV-18, GOV-20, GOV-27); updated-ownership-when-roles-change (GOV-09); vendor-assurance-reports-that-were-reviewed (GOV-28); vendor-inventory-with-owner-data-and (GOV-03, GOV-05, GOV-14, GOV-18, GOV-22, GOV-23, HR-02); vulnerability-register-with-remediation-and-accepted (GOV-16). Under rule A (a partial check can only take satisfaction away) nothing can satisfy them. Several of them are check only today, where a passing check satisfies the artifact alone. | Decide whether a Verity module report counts as the satisfying source, add a person source, or mark the check fill full for these Verity held records. | coverage/gov-cs-hr.json |
| checks named as sources on unmapped controls | An artifact can name any check, but a check's evidence attaches only to controls in its own controls list (AU-11). 31 existing checks are named on SD, LM and BC controls they do not map to. | Add the partial mappings listed in existing_check_changes (add_control). | coverage/sd-lm-bc.md (Existing checks used on controls they do not map to) |
| ci.production_deploys_controlled | Extractor lookup: no artifact in artifacts.json names this check, and none of the six documents adds it to one, so it changes no objective even after these proposals. | Extractor suggestion: add it to deployment-history-for-a-sample-of (SD-13.C accepts 'ran through a protected environment with named reviewers') or branch-protection-settings (SD-13.B). Needs the merger's judgement. | extractor lookup of artifacts.json against connectors/github.md section 6 |
| data-inventory-and-data-map | Coverage files raise a need against business_applications for this artifact ('business applications that hold personal data are listed'). The phase 3 research says these needs are met by the vendor register, not by the business application APIs. | Point that need at the vendor register (verity_vendors) rather than business_applications. | connectors/phase3-catalogue.md 7.1 |
| devices.enrolled, devices.disk_encrypted, devices.screen_lock, endpoint.protection_active | Mapped full to EP-03, EP-02, EP-06 and EP-01. Each control has a design objective and operating objectives no device check proves (AUTHORING rule 5). | Change to partial with rationales naming what remains (see downgrades). None is implemented, so no workspace's readiness changes (D-DEV-4). | mdm-and-endpoint-strategy.md section 4 F4 |
| vcs.code_scanning_enabled | Maps only to SD-05, but static analysis is what ISO27001:A.8.28 and A.8.29 rely on through SD-02 and SD-10, and no objective tested that it ran. | Map it to SD-02 (partial); SD-02.F added. | coverage/sd-lm-bc.md (Content problems found) |
| vcs.merged_changes_reviewed | The doc says this running GitHub check is used for IAM-09 and DM-18 and 'stays on IAM-09' after the split, but checks.json maps it only to SD-01 and SD-06. | Add partial mappings to IAM-09 (author and approver are different people) and DM-18 (masking changes approved), or stop describing it as on IAM-09. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Splits; How to read this file |
| vcs.org_two_factor_required | The check maps to IAM-03 but no artifact names it, so it changes no objective (reconciliation gap). | Add vcs.org_two_factor_required as a check source of second-factor-enforcement-and-enrolled-users (IAM-03.B). | connectors/github.md section 6 |
| vcs.secret_scanning_enabled | The doc says this running GitHub check is used for NS-09, but checks.json maps it only to SD-11. | Add a partial mapping to NS-09. | coverage/iam-ep-pe-ns-dm.md How to read this file; NS-09 |
| verity.tasks.remediation_in_sla | Used as a source on LM-05, LM-10, BC-02 and BC-03 artifacts and on the deficiency log of many controls, but maps only to GOV-08, so its evidence never attaches to those controls. | Attach each result to the control its task is linked to (as document checks do); same for tickets.remediation_tracked. | coverage/sd-lm-bc.md (Content problems found) |

#### Objective (31)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| BC-01 | ISO27001:A.8.13 covers copies of software and systems; BC-01.A names them but nothing tested them. BC-01.D bundled storage protection with restore rights. | Add BC-01.F (rebuild materials) and BC-01.E (restore rights); reword D with a settings test. | coverage/sd-lm-bc.md (Objective changes) |
| BC-03.A, BC-03.C | Bundled the redundancy each service relies on, and failover tests, with continuity planning (ISO27001:A.8.14 is its own Annex A control). | Reword A and C; move redundancy and failover to BC-09. | coverage/sd-lm-bc.md (Objective changes) |
| BC-07.D | Bundled the yearly register review with offboarding, an event per vendor with its own record; ISO27001:A.5.22 relies on removal with access revoked. | Reword D; add BC-07.E (offboarding). | coverage/sd-lm-bc.md (Objective changes) |
| BC-08.B | Repeated BC-07.C (register complete). | Reword to tiering: each supplier with access has a current tier that sets the depth of its assessment. | coverage/sd-lm-bc.md (Content problems found; Objective changes) |
| BC-08.E | Bundled contract terms (ISO27001:A.5.20) with tracking of findings. ISO27001:A.5.22 and A.8.21 rationales rely on checking delivered service levels and no objective tested it. | Reword E; add BC-08.F (findings) and BC-08.G (delivery review). | coverage/sd-lm-bc.md (Objective changes) |
| DM-01.C | Bundled customer notices under contract (processor) with regulator and individual notices (controller). | Limit C to customer notices; add E for regulator and individual notices where the company is controller. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| DM-03 | SOC2:P3.2 is partial because the consequences of declining consent are not communicated; no objective tested it. | Add E; then P3.2 becomes full. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| DM-08.C | Tested deletion of backups, archives and analytics copies, which duplicates DM-16.D. | Reword C to 'the schedule covers every copy'; the deletion test stays in DM-16.D. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| DM-11 | Objectives assume the company is the controller; the processor path (requests about customer data passed to the customer within the contract time) was untested. | Add E. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| DM-16 | No objective tested deletion when a customer leaves or on an erasure request, which SOC2:C1.2 and P4.3 rely on. | Add DM-16.E. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| EP-03 | The A.8.19 rationale claims device management enforces the permitted software list; no operating objective tested it. | Add E: software installs limited to the permitted list. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| EP-07.C | Server outbound web limits are network rules owned by engineering, not the staff web filter. | Move to NS-03 as NS-03.E; retire the letter EP-07.C. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-01 | SOC2:CC6.3 is mapped on approving changes to access, but B only tests joiners; ISO27001:A.8.34 (auditor and tester access to live systems) is mapped and no objective tests it. | Reword B to add movers; add F for auditor, tester and outside support access approved by the system owner, time limited and removed. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-02 | The A.8.4 rationale relies on the code host, build pipelines and package registries being in review scope, which C did not say. | Reword C to name them. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-03 | A.8.5 and IAM-03.A require a second factor on every system, but B tests only the identity provider; vcs.org_two_factor_required and cloud.root_account_mfa had no objective to land on. | Add F: second factor on systems people sign in to directly (cloud console, code host, password manager, apps outside SSO). | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-04 | D tested leaver removal, which duplicates IAM-12.C and D. | Reword D to 'apps behind SSO refuse local passwords'; move the leaver side to IAM-12.D. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-06 | The A.5.17 rationale claims single use initial and reset passwords and an identity check before a reset; no operating objective tested it. | Add E. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-07 | A.8.2 is mapped full but A only approves the review procedure; the A.8.2 and A.8.18 rationales rely on logged use, which no objective tested. | Reword A to cover granting rules, break glass and logging; add F: each elevation and break glass use logged, alerted and reviewed. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-12 | CC6.3 and A.5.18 rationales claim modification on role change, but B only lists leavers; D now needs the list of apps outside SSO. | Reword B to add role changes; D gains the list of apps outside SSO. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| IAM-14 | No control tested how the product authenticates its customers' users (IAM-03, IAM-04, IAM-06 cover staff; IAM-11 only product sessions). | Add IAM-14 with objectives A to D. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| LM-02.B, LM-02.C | Each bundled two parts of ISO27001:A.8.15 with different evidence (source coverage with gap alerts; retention with protection from administrators). Retention was tested by interview alone. | Reword B and C; add LM-02.F (gap alerts) and LM-02.G (protection); retention gains a settings test. | coverage/sd-lm-bc.md (Objective changes) |
| LM-05 | ISO27001:10.2 asks that corrective action is checked for effect; no objective tested it. | Add LM-05.E. | coverage/sd-lm-bc.md (Objective changes) |
| LM-07 | ISO27001:A.5.28 is mapped on the evidence procedure but only the written plan was examined; LM-07.C bundled sharing the plan with reviewing it. | Add LM-07.F (evidence handled as the plan sets) and LM-07.G (review); reword C to acknowledgement by role holders. | coverage/sd-lm-bc.md (Objective changes) |
| NS-02.D | An operating objective (internal and database traffic encrypted) tested only by reading the standard and an interview, so it cannot show operation. | Give it the proposed settings artifact internal-tls-enforcement-settings. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| NS-11.D | Bundled a configuration fact (access per application) with a monitoring duty (sessions logged and reviewed); they fail independently. | Split into D (per application access) and E (sessions logged and reviewed). | coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Objective revisions; coverage/iam-ep-pe-ns-dm.controls.json |
| SD-01.B | Tested a population of merges only, though ISO27001:A.8.19 and A.8.32 rely on SD-01 for server software, infrastructure, configuration and database changes. | Reword to cover the whole change population, with the proposed infrastructure-and-configuration-change-history artifact. | coverage/sd-lm-bc.md (Objective changes) |
| SD-02 | ISO27001:A.8.28 and A.8.29 rely on static analysis in the pipeline; no objective tested that it ran. SD-02.E applies only with Processing Integrity. | Add SD-02.F; SD-02.E reads not applicable when Processing Integrity is out of scope. | coverage/sd-lm-bc.md (Objective changes) |
| SD-03.A | Bundled the component list with licences (ISO27001:A.5.32) into the dependency triage standard. | Reword SD-03.A; move the component and licence standard to SD-18.A. | coverage/sd-lm-bc.md (Objective changes) |
| SD-05.D | Rejects and duplicates in a monitored queue is processing integrity error handling (PI1.2), not secure input validation. | Move to SD-15.D. | coverage/sd-lm-bc.md (Proposed control changes, SD-05) |
| SD-10.B | Bundled approval of security requirements before build with the check before release that ISO27001:A.8.29 relies on. | Reword SD-10.B; add SD-10.F for verification before release. | coverage/sd-lm-bc.md (Objective changes) |
| people-only objectives | These rest on a person's judgement, a signature or a record no catalogued system holds: SD-01.E, SD-02.E, SD-04.C, SD-04.E, SD-07.D, SD-09.B, SD-09.C, SD-10.C, SD-10.D, SD-11.D, SD-12.E, SD-16.C, SD-18.C, LM-03.D, LM-04.D, LM-05.D, LM-05.E, LM-06.C, LM-06.D, LM-07.D, LM-07.E, LM-07.F, LM-10.B, LM-10.C, LM-12.B, LM-12.D, LM-12.E, BC-02.C, BC-03.B, BC-04.B, BC-06.C, BC-08.D, BC-10.C. People only artifacts: escrow-verification-record, notices-to-customers-of-subprocessor-changes, secure-coding-training-completion-for-developers. | No fix; checks can show the record exists and is on time, not that it is right. The control page should say so. | coverage/sd-lm-bc.md (What no system can prove) |

#### Template (18)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| access-control-policy | Asks for a second factor only on privileged production access, has no single sign on rule and no session limits, and its example password minimum is eight characters against IAM-06.A's 12. | Add the sections (CL-6 work), or point the objectives at infrastructure-security-standard and operations-security-policy. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 4 |
| backup policy | No template exists for a backup policy. | Create a template, or use operations-security-policy 'Backups and restore tests' with the continuity plan Appendix B. | coverage/sd-lm-bc.md (Content problems found) |
| code-of-conduct | The template does not require acknowledgement at hire and every year, which GOV-04.A and verity.policies.acknowledged assume. | Add acknowledgement at hire and yearly to the template text. | coverage/gov-cs-hr.md Content problems and gaps found |
| confidentiality-and-ip-agreement-template | Verity ships no agreement text on purpose; Appendix A row 53 asks for a clause checklist instead (HR-02). The plan points the artifact at human-resource-security-policy, which is not an agreement. | Ship the clause checklist named in Appendix A row 53, not agreement text. | coverage/gov-cs-hr.json notes, HR-02 |
| cryptography-policy | No rotation interval and no key service or HSM rule; infrastructure-security-standard section 3 holds those. | Add the rule, or point NS-06, NS-01, NS-02 and EP-02 objectives at infrastructure-security-standard section 3. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 4 |
| endpoint-security-standard | No web filtering section (EP-07 relies on operations-security-policy instead). | Add a web filtering section or keep EP-07 on operations-security-policy. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 4 |
| engineering-security-standard | Nothing on how customer users sign in to the product; the proposed IAM-14 needs a product sign in section. | Add a product sign in section before IAM-14 ships. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 4; coverage/iam-ep-pe-ns-dm.md (Proposed control changes) Addition |
| escalation-policy, alerting-standard, logging-and-retention-standard | Observed during extraction, not raised by the research: these document category artifacts have only a person source, and no matching template exists in document_templates.json. | Add document templates (or map to an existing one such as incident-response-plan or operations-security-policy) and list them as document sources. | artifacts.json, document_templates.json (extraction check) |
| human-resource-security-policy | Sets no recheck interval for sensitive roles (HR-01.A). | Add a recheck interval for sensitive roles. | coverage/gov-cs-hr.md Content problems and gaps found |
| human-resource-security-policy | Covers discipline in one sentence: no range of sanctions, no right to respond and no case records (GOV-11.A). No template carries the disciplinary procedure on its own. | Add a disciplinary procedure template (or a full section) with the range of sanctions, the right to respond and how case records are kept; source the artifact disciplinary-procedure from it. | coverage/gov-cs-hr.md Content problems and gaps found |
| incident-response-plan | Says customers are told per contract but states no timeframe outside the health appendix (CS-01.A). | State a notification timeframe in the main plan, compared with the shortest contractual one. | coverage/gov-cs-hr.md Content problems and gaps found |
| information-security-roles-and-responsibilities | Has no appointment of the security officer, no deputy and no organization chart prompt (GOV-10.A, GOV-21.A). | Add an appointment section with a deputy and an organization chart prompt. | coverage/gov-cs-hr.md Content problems and gaps found |
| operations-security-policy | Sets a yearly penetration test but no retest of fixed findings (GOV-16.E). | Add retest of fixed findings to the template. | coverage/gov-cs-hr.md Content problems and gaps found |
| performance-review-process | No template exists for the performance review process (HR-07). | Add a template or keep the artifact person only. | coverage/gov-cs-hr.json notes, HR-07 |
| postmortem | No postmortem template ships, so verity.incidents.postmortem_recorded cannot read the content (timeline, impact, root cause, detection gap). | Add a postmortem template. | coverage/sd-lm-bc.md (Content problems found; verity.incidents.postmortem_recorded) |
| subprocessor list | No template exists for the published subprocessor list. | Create one, held as a Documents entry linked to BC-06. | coverage/sd-lm-bc.md (Content problems found) |
| third-party-management-policy | No data processing agreement requirement and no breach notice timeframe in hours (DM-10.A, DM-17.A); verity.vendors.breach_terms_recorded has no policy maximum to read. | Add both sections. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 4 |
| vulnerability management policy | No template exists; the vulnerability-management-policy-with-timeframes and dependency triage artifacts point at a policy that is not a template. | Create a template, or use the operations-security-policy section 'Finding and fixing vulnerabilities'. | coverage/sd-lm-bc.md (Content problems found) |

#### Capability (16)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| ai_providers | No capability for AI model providers exists. | Add capability ai_providers: 'A service that runs AI models on company data', providers openai and anthropic. The ai.* checks are written against it (D-P3-1). | connectors/phase3-catalogue.md 1.1 |
| alerting | betterstack and grafana are listed only under observability, but both run on call schedules and escalation (Grafana's on call product is unverified), and Better Stack implements alerts.acknowledged_in_time and the proposed alerts.* keys, which are written against alerting. | Add betterstack and grafana to alerting. | connectors/phase3-catalogue.md 1.1, 3.1, 3.3 |
| asset_discovery | tenable, rapid7 and qualys are not listed under asset_discovery although a scanner knows which hosts exist and when it last saw them, which assets.resources_registered needs. | Add tenable, rapid7, qualys to asset_discovery (D-P3-1). | connectors/phase3-catalogue.md 1.1 |
| asset_discovery | digitalocean is listed only under cloud_infrastructure, but section 4.1 gives it capability asset_discovery and assets.resources_registered S. | Add digitalocean to asset_discovery. | connectors/phase3-catalogue.md 4.1 (cross checked against capabilities.json) |
| business_applications | Capability does not exist in capabilities.json, yet the coverage files already raise needs against it (for example data-inventory-and-data-map) and operations research handed over two needs for it (admin role exports, second factor per member, operations-checks.md section 6). | Add capability business_applications: 'A software service staff sign in to that holds company or customer data'. The apps.* checks are written against it (D-P3-1). | connectors/phase3-catalogue.md 1.1 |
| business_applications providers | Section 1.1 says every SaaS in the file that exposes its members joins business_applications, including the platforms in section 4. | Members: grafana, linear, asana, notion, digitalocean, heroku, render, vercel, netlify, supabase, neon, qovery, hubspot, intercom, zendesk, posthog, sendgrid, resend, openai, anthropic (see capabilities_proposed). | connectors/phase3-catalogue.md 1.1, sections 3 to 7 |
| capabilities.json | No business_applications capability (Appendix A lists it for Phase 3) and no verity_identity. Productivity suite sharing and leak prevention settings (Google Workspace, Microsoft 365) have no capability; this doc files them under identity_provider. | Add both capabilities; decide whether the suite settings deserve their own. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 8 |
| ci_cd | Vercel, Netlify, Render, Heroku and Qovery hold the deployment history the ci.* checks read, but ci_cd lists only github, gitlab and bitbucket. | Add vercel, netlify, render, heroku, qovery to ci_cd. | connectors/phase3-catalogue.md 1.1, 4.2 to 4.5, 4.8 |
| ci_cd: github | capabilities.json lists GitHub under CI and CD as planned for Phase 2 although the GitHub connector exists. Deployments, workflow runs and check results need new read permissions (unverified), so ci.* checks are P2 even on GitHub. | Make the capability listing say GitHub version control is live and GitHub CI and CD reads are Phase 2. | coverage/sd-lm-bc.md (Content problems found) |
| cloud_infrastructure | qovery is listed under cloud_infrastructure, but section 4.8 gives its capabilities as ci_cd and business_applications only, because Qovery deploys onto the customer's own AWS, Google Cloud or Azure account and cloud checks come from that cloud's connector. Section 4.8 still lists cloud.environments_separated P for Qovery. | Move qovery to ci_cd and business_applications; decide whether cloud.environments_separated stays implementable from Qovery's environment modes. | connectors/phase3-catalogue.md 4.8 (cross checked against capabilities.json) |
| idp.sso_enforced, idp.access_list_exported (1Password) | Inferred during extraction, not raised by the research: identity-checks.md marks 1Password partial for these identity_provider checks, but 1Password is a password_manager provider, so it cannot be an implementation unless the checks gain that capability or 1Password is treated as a business application in scope. | Decide whether these rows become password_manager implementations, business application evidence, or notes only. | connectors/identity-checks.md section 1; connectors/1password.md section 5.1 |
| network_edge | Vercel's firewall fits network_edge and implements edge.waf_enabled P, but vercel is not under network_edge. | Add vercel to network_edge. | connectors/phase3-catalogue.md 4.4 |
| single_sign_on | The provider content example lists capability single_sign_on, which capabilities.json does not have. | Add single_sign_on as a capability or drop it from the example. | 02-integration-model.md section 2.5 |
| ticketing | notion is listed under ticketing but has no ticket model; a ticket check works only if the customer maps a database. | Keep notion in ticketing only as partial, or move it to business_applications (D-P3-5; recommended business application only). | connectors/phase3-catalogue.md 1.1, 3.5 |
| vault.everyone_enrolled | Capabilities are password_manager only, but every active employee needs a staff list; the vault alone cannot say who is missing. | Capabilities password_manager and hr_system. | connectors/identity-checks.md section 5 |
| verity_members | Checks on memberships and owner functions need a verity_members capability, which is not in capabilities.json. | Add capability verity_members (provider verity). | coverage/gov-cs-hr.md Content problems and gaps found |

#### Provider (18)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| bitbucket | There is no read only scope for Bitbucket branch restrictions; admin:repository:bitbucket can edit restrictions, the branching model and default reviewers. Verity's read only rule means a write capable scope needs an ADR (docs/architecture/integrations.md). | D-BB-1; if adopted, a GET only transport wrapper in the collector and a warning in setup. | connectors/bitbucket.md section 2.2 |
| bmc | BMC Helix Discovery research is entirely unverified: the documentation site refused automated reading (HTTP 403), so REST API version, token flow, search endpoint and least privilege group are unknown. It is an enterprise tool, only for customers who already run it. | Research again with documentation access or a customer's appliance before any build (D-P3-7). | connectors/phase3-catalogue.md 6 |
| device_management (capabilities.json) | Google Workspace is not listed as a device source although its Cloud Identity Devices API and Endpoint Verification report device state. | Add gws to device_management (D-DEV-13), riding on the Phase 2 Google Workspace connector. | mdm-and-endpoint-strategy.md section 4 F8; connectors/google-endpoint-management.md |
| digitalocean | Section 4.1 lists business_applications as a capability, yet team member listing and two factor status were not found in the OpenAPI document, so every apps.* check is N. | Leave digitalocean out of business_applications until a member API is found. | connectors/phase3-catalogue.md 4.1 |
| endpoint_protection (capabilities.json) | Microsoft Defender for Endpoint is missing; only CrowdStrike and SentinelOne are listed. The artifact alerts-that-were-reviewed-and-acted already names Microsoft Defender as a place the evidence comes from. | Add defender_endpoint to endpoint_protection (D-DEV-12). | mdm-and-endpoint-strategy.md section 4 F8; connectors/microsoft-defender-endpoint.md |
| entra versus intune | 02 section 2.1 and entra-id.md treat Intune device evidence as a capability of the Microsoft connection, while capabilities.json lists intune as a separate device_management provider. | Decide whether Intune is a capability of the entra provider or its own provider key (devices research). | 02-integration-model.md section 2.1; connectors/entra-id.md |
| heroku | Heroku warns that some read only resources can include write credentials in metadata. | Collector keeps an allow list of fields; request scope read, not read-protected. | connectors/phase3-catalogue.md 4.2 |
| hr_system (capabilities.json) | HiBob is not listed; only Workday, BambooHR, Rippling and Gusto. | Add hibob to hr_system. | mdm-and-endpoint-strategy.md section 4 F8; connectors/hr-systems.md |
| hr_system, learning_platform, esignature, background_screening | No HR, learning, signing or screening connector is in the signed catalogue, so the operating evidence of HR-01, HR-02 and HR-07 stays with people until one is agreed. | Agree a connector as an extension, or keep these manual and say so in the product. | coverage/gov-cs-hr.md Content problems and gaps found |
| kandji (capabilities.json) | Kandji renamed itself Iru in October 2025; the catalogue still says Kandji. The API keeps the kandji.io hosts, and upgraded tenants may use api.iru.com (unverified). | Show 'Iru (Kandji)' and keep the key kandji (D-DEV-11). | mdm-and-endpoint-strategy.md section 4 F8; connectors/kandji.md |
| openai audit log | Audit logging may need to be switched on in the organisation's settings before events are kept (unverified). | Until confirmed, an empty audit log is insufficient, never 'no admin actions'. | connectors/phase3-catalogue.md 7.3 |
| population visibility | Qualys Readers and Tenable users without Can View on all assets, and app tokens tied to one user, see only part of the account. | Every check treats not visible as insufficient and asks the customer to confirm full visibility once. | connectors/phase3-catalogue.md 9, 2.1 |
| rapid7 (Nexpose on premises) | integrations.md lists 'Rapid7 Nexpose'; research covers InsightVM Cloud Integrations API v4 only; on premises Security Console API v3 not read. The v4 API also has Start Scan, Stop Scan and Update Scan Engine Configuration, so the user's role must not allow those. Read only role name and rate limits unverified. | Use a user key of a read only user; research v3 before supporting on premises consoles. | connectors/phase3-catalogue.md 5.5 |
| short provider retention | HubSpot logins 90 days, Render audit 90 days, Linear audit 90 days (Enterprise). A 12 month Type 2 period cannot be shown from the provider alone. | Verity keeps its daily pulls as evidence (D-P3-6). | connectors/phase3-catalogue.md 9 |
| slack (alerting) | Slack is listed as an alerting provider in capabilities.json, but it has no on call schedule, escalation, acknowledgement or incident record; a channel message is not a page. It implements none of the alerts checks. | Remove Slack from alerting. Keep it as Verity's notification channel (not a capability), optionally under business applications for its own member list. Catalogue card: notifications only. | connectors/operations-checks.md section 2; connectors/slack.md sections 1, 9 |
| tailscale (edge.minimum_tls) | The network_edge capability lists Tailscale, which would make it an implementation candidate for edge.minimum_tls, but Tailscale traffic is WireGuard and has no TLS version setting. | Implement edge.minimum_tls on Cloudflare only. | connectors/operations-checks.md section 2 |
| tenable (Nessus Professional, Security Center) | integrations.md lists 'Tenable Nessus'; only Tenable Vulnerability Management was researched. Nessus API page not found, Security Center not read. | Nessus Professional customers keep the existing .nessus upload path (parse_xml already reads ReportHost and ReportItem). | connectors/phase3-catalogue.md 5.4 |
| write capable credentials | Render, Vercel, Netlify, ClickUp, Monday, Better Stack, Resend, the OpenAI admin key and the Anthropic Console admin key cannot be made read only from what was found. integrations.md requires an ADR for a connector that needs write access. | One ADR (D-P3-3) with mitigations: dedicated lowest role user, expiring token, GET only allow list in the collector, shown to the customer. | connectors/phase3-catalogue.md 9, D-P3-3 |

#### Module (42)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| ASSET_TYPES (backend/src/verity/modules/assets/models.py) | Asset types are application, infrastructure, data, cloud, third_party, business_service: no device. Laptops cannot be registered as assets, so LM-01.C and DM-16.B for laptops have no home. The artifacts inventory-of-company-devices and asset-inventory both say their home is the Assets module filled from the device tool, which the module cannot hold today. | Decision D-DEV-6: add a device type (schema change, migration, CHECK constraint) or keep devices outside the asset register. The correlation keys serial_number, primary_mac, hostname and os_normalized already exist. | mdm-and-endpoint-strategy.md section 4 F5 |
| assets: ASSET_TYPES | Assets has no endpoint or device type (application, infrastructure, data, cloud, third party, business service), so laptops are recorded as infrastructure and the device inventory has no home. | Add an endpoint type (migration) before device management connectors land. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 5 (backend/src/verity/modules/assets/models.py) |
| assets: data map fields | Retention and encryption per data store exist only as custom fields. | Accept custom fields with fixed keys, or add columns (owner decision). | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 12 |
| backend/src/verity/modules/connectors/github.py | The plan versus permission inference uses the repository's permissions.admin flag; with a GitHub App that flag describes the installation, not a person (unverified). | Re-derive for the App: the App holds Administration read on every installed repository, so an absent security_and_analysis means the plan. | connectors/github.md section 2.1 |
| backend/src/verity/modules/connectors/github.py | The fine grained personal token ties the connection to one person: a leaver's token stops the connection, and it can see the person's own repositories. | Move to a Verity GitHub App (D-GH-1); keep the token as fallback for GitHub Enterprise Server or customers who refuse apps. | connectors/github.md sections 2.1 and 2.2 |
| backend/src/verity/modules/connectors/github.py | When the population is cut short, the built connector reports error instead of insufficient_information, the outcome 01-evidence-model.md 1.3 names. | Report insufficient_information for a truncated population. | connectors/github.md section 5 |
| compliance: Statement of Applicability supplier rows | Supplier provided rows in the Statement of Applicability do not name the vendor, so no check can join them to supplier certificates (GOV-27.D). | Add a vendor link on supplier provided rows. | coverage/gov-cs-hr.md Content problems and gaps found |
| compliance: assurance kinds | No assurance record kind exists for an oversight body meeting (GOV-02, CS-05.E, GOV-15.E). | Add an oversight body meeting kind; until then use a recurring task with minutes attached. | coverage/gov-cs-hr.md Content problems and gaps found |
| compliance: assurance records need an engagement | Assurance records hang on an engagement, so a workspace with no engagement cannot record an internal audit or management review at all. | Allow assurance records without an engagement, or make an engagement a precondition shown in the product. | coverage/gov-cs-hr.md Content problems and gaps found |
| compliance: commitments review date | Commitments carry no review date, so the yearly comparison of promises with practice (CS-02.C) cannot be checked. | Add a review date to commitments. | coverage/gov-cs-hr.md Content problems and gaps found |
| frontend/src/features/connectors/connector-catalogue.ts | The integration catalogue is hard coded in the frontend and can drift from what the backend supports. | Move it to provider content (02 section 2.5). | 02-integration-model.md section 2.3 |
| hr_system / staff roster | No staff roster in Verity and no HR connector in any signed phase; seven controls compare against a roster (IAM-01, IAM-05, IAM-12, EP-03, EP-05, NS-11, PE-02). Verity members are not a roster and must never fill roster-of-joiners-and-leavers-with. | Build the proposed CSV roster import. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 6 |
| iam: members are not the staff list | Acknowledgement, training and joiner checks judge Verity members, so staff never invited are invisible until an HR source or the proposed roster import exists (open question 1). | Offer the roster import (CSV) as the staff population until an HR connector is agreed. | coverage/gov-cs-hr.md Content problems and gaps found |
| objectives measures | No record type holds an objective's measure and its readings (GOV-26.C, GOV-30, Appendix A.3 clause 9.1). | Add a measure and readings record for security objectives. | coverage/gov-cs-hr.md Content problems and gaps found |
| risk: assessment sign off | The Risk module has no sign off step on a risk assessment (GOV-18.E). | Add a sign off step, or route the exported report through a document approval meanwhile. | coverage/gov-cs-hr.md Content problems and gaps found |
| risk: dated assessment report export | Unverified whether the Risk module exports a dated assessment report (Appendix A.3, clause 8.2) for risk-assessment-report-with-method-and (GOV-12, GOV-18, GOV-24). | Confirm the export exists, or build it. | coverage/gov-cs-hr.json notes |
| risk: fraud category mark | Risk categories have no fraud mark (fraud templates exist), which verity.risks.fraud_assessed needs. | Add a fraud mark on risk categories. | coverage/gov-cs-hr.md Content problems and gaps found |
| tasks | No incident kind (security-incident-register relies on an incident template convention until the Incidents module, Phase 3.1) and no custom fields, so a notice decision can only be a subtask. | Incident template with notice decision and notice sent subtasks now; Incidents module later. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 10 |
| tasks: improvement decision | Tasks has no decision field for improvement items; the decision is a comment today (GOV-30.C). | Add a decision field (accepted, rejected, with reason) on improvement items. | coverage/gov-cs-hr.md Content problems and gaps found |
| tasks: incident kind | Tasks has no incident kind; until the Incidents module (Phase 3.1) exists the security incident register is a convention on issues (CS-01, CS-03, CS-06, CS-07, GOV-08). | Add an incident kind or a fixed tag convention in Tasks until the Incidents module ships. | coverage/gov-cs-hr.md Content problems and gaps found |
| tasks: incident marker | Tasks has no incident marker and no notice decision field, yet the security incident register (LM-07.D) is meant to live there. | Ship a Security incident task template with a structured notice decision field, or the Phase 3.1 Incidents module, before verity.incidents.registered can run. Imported incidents need source and external_id for the connector reconciliation checks. | coverage/sd-lm-bc.md (Content problems found) |
| tasks: issue actions | verity.tasks.remediation_in_sla covers tasks, not issue actions until they are promoted to tasks. | verity.tasks.capa_on_time reads issue actions directly. | coverage/sd-lm-bc.md (verity.tasks.capa_on_time) |
| tasks: per record access | Tasks has no per record access limit, so code of conduct breach records and disciplinary cases are kept out of Verity (GOV-04, GOV-11). | Keep them out, or build restricted records first. | coverage/gov-cs-hr.md GOV-04, GOV-11 |
| tasks: recurring series to control link | Recurring task series are not linked to controls. | Link the series to the control through the links table for verity.tasks.recurring_review_on_time. | coverage/sd-lm-bc.md (verity.tasks.recurring_review_on_time) |
| tasks: report channel | Tasks has no field for a security report's channel (CS-03.C, CS-03.D). | Add a tag or category convention for reports from the security address. | coverage/gov-cs-hr.md CS-03 |
| tasks: template to control binding | Task templates are not bound to controls (template_id exists, the binding does not), so verity.tasks.change_approved_independently cannot find its population. | Add a binding between task templates and controls. | coverage/sd-lm-bc.md (verity.tasks.change_approved_independently) |
| vendors | No lawful basis field (DM-09) and no sign in method per application (IAM-04.B); discovered apps wait for the identity connectors. | Add lawful basis and sign in method fields when DM-09 and IAM-04 automation is built. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 11 |
| vendors: ISO certificates | ISO certificates are documents without structured period fields, so their validity cannot be evaluated like a SOC report review. | Add structured validity dates for certificates. | coverage/sd-lm-bc.md (verity.vendors.assurance_report_reviewed) |
| vendors: contract terms | The security terms required per tier are not a tiering policy setting, and code ownership and escrow are not contract fields (needed for BC-10). | Add required terms per tier to the tiering policy, and code ownership and escrow fields to contracts. | coverage/sd-lm-bc.md (verity.vendors.security_terms_on_file) |
| vendors: customer data flag | Vendors have no flag for customer data as opposed to staff data; Verity does not publish the subprocessor list or record customer notices. vendor_subprocessors is fourth parties, not the company's list. | Add a customer data flag on vendors and a published list document linked to BC-06. | coverage/sd-lm-bc.md (Content problems found) |
| vendors: discovered apps source | vendor_discovered_apps has no connector source until an identity provider connector ships, so BC-05 is manual in P1. A reason for ignored apps needs confirming in the schema. | Feed discovered apps from the Phase 2 identity provider connectors; confirm an ignore reason field. | coverage/sd-lm-bc.md (Content problems found; verity.vendors.discovered_apps_triaged) |
| verity notifications | No delivery log of security messages Verity sent (channel, time, provider message id), so sample-of-messages-sent-under-the (CS-04.D, CS-06.B, C) cannot gain a module source. | Record every send attempt and the provider's answer in the notifications module, complete with failures, and list it as a source of that artifact (partial: sent, not read). | connectors/slack.md sections 4, 6, 10; connectors/operations-checks.md section 6 |
| verity_tasks (incident register) | The register is a filtered view of Tasks. Imported incidents need to land with a triage decision field, and the register must expose completeness against source and external_id, or the *.incidents_registered checks cannot be evaluated. | Add the triage decision field and source based completeness (NEED verity_tasks). | connectors/operations-checks.md sections 5, 6 |
| verity_vulnerabilities: asset matching | _ingest matches assets by asset_id or by name only (by_name = {r.name.lower(): ...}). Scanner hosts named by IP or FQDN do not match; they are counted as unmatched and dropped. | Match on cloud_resource_id, fqdn, hostname, ip_address, primary_mac (all columns on assets), in that order; keep unmatched findings. | connectors/phase3-catalogue.md 5.2 |
| verity_vulnerabilities: external_id | _ingest does not set external_id per instance; a re-run cannot tell an instance from a new one by provider id, and the provider's own id is lost. | Set source to the provider and external_id to the provider's finding or detection id (rule 9). | connectors/phase3-catalogue.md 5.2 |
| verity_vulnerabilities: first detection time | first_detected_at=now: the SLA starts when Verity first sees the finding, not when the scanner found it, so a first sync of an old backlog shows nothing overdue. | NEED verity_vulnerabilities: imported findings keep the scanner's first found time and the SLA due date is computed from it (LM-11.D, LM-12.C). Requires a first_found field on FindingRow. | connectors/phase3-catalogue.md 5.2 |
| verity_vulnerabilities: scanner driven closure | verify_instance closes only from pending_retest, by a person; a fix the scanner confirmed stays open until someone clicks. | NEED verity_vulnerabilities: a finding the scanner reports fixed after a rescan moves to verified fixed with the scanner as verifier (actor System, the run's report), and every closure as fixed in the period has such a rescan or a person's retest (LM-11.E). The docstring already anticipates it. | connectors/phase3-catalogue.md 5.2 |
| verity_vulnerabilities: severity words | _SEVERITY_WORDS maps 0..4 and a few words; anything else becomes medium, so Rapid7 'severe' and Qualys level 5 would be stored as medium. | Each collector maps its scale explicitly (section 5.3 maps: Tenable same words; Rapid7 none and informational to info, moderate to medium, severe to high, critical to critical; Qualys 5 critical, 4 high, 3 medium, 2 low, 1 info, QDS kept separately, to confirm with the KnowledgeBase). The module should reject an unknown severity instead of defaulting (code change for the module owner). | connectors/phase3-catalogue.md 5.2, 5.3 |
| verity_vulnerabilities: unmatched findings dropped | _ingest does 'unmatched += 1; continue', so a finding on an unregistered host disappears and the register looks cleaner than the estate. | NEED verity_vulnerabilities: findings on hosts not in the asset register are kept as unmatched and raise asset register work (LM-01, proposed LM-13). | connectors/phase3-catalogue.md 5.2 |
| vulnerabilities: acceptance length | A maximum risk acceptance length is not a setting. | Add a maximum acceptance length setting (default 12 months) for verity.vulns.acceptances_approved. | coverage/sd-lm-bc.md (verity.vulns.acceptances_approved) |
| vulnerabilities: scan targets | Imported vulnerability scan reports record findings, not the targets scanned, so scan coverage (LM-11.B, now LM-13.B) cannot be shown from Verity: a clean asset leaves no trace. | Add a target list to vuln_reports. | coverage/sd-lm-bc.md (Content problems found) |
| vulnerabilities: triage time | Vulnerability settings hold remediation days per severity but no triage time, so SD-03.D and verity.vulns.triaged_in_time have no parameter to test against. | Add a triage time per severity to the vulnerability settings. | coverage/sd-lm-bc.md (Content problems found) |

#### Other (20)

| Item | Finding | Proposal | Source |
|---|---|---|---|
| 03-market-research 3.10 item 1 | Recommends vendor apps for Entra and Google and an Okta catalogue API Service Integration, which conflicts with the unified setup recommendation. | Reconcile (see the decision Identity provider connection model conflict). | 03-market-research.md section 3.10; connectors/identity-providers-unified-setup.md section 6 |
| Keycloak SCIM and organizations | verity.identity.leavers_removed_by_sync needs a lifecycle feed (SCIM or LDAP) into Keycloak; the runbook records that this Keycloak build's SCIM server does not place users in organizations. | Resolve the lifecycle feed before building the check. | coverage/iam-ep-pe-ns-dm.md Verity's own sign in and directory sync as evidence |
| Keycloak brokering claims | Unverified whether Keycloak passes the upstream provider's authentication method claims (amr, acr) through brokering; verity.identity.second_factor_on_sign_in depends on it. | Verify; until then the check reports insufficient information when the claim is absent. | coverage/iam-ep-pe-ns-dm.md Verity's own sign in and directory sync as evidence |
| LM-01 devices | The LM-01 text says devices have no source in the catalogue because device management is not planned, while capabilities.json lists device_management (jamf, kandji, intune). Extractor's note, the document does not raise the conflict. | Reconcile with mdm-and-endpoint-strategy.md and the devices research. | coverage/sd-lm-bc.md (LM-01) |
| MANAGEMENT_REVIEW_INPUTS | In compliance/assurance_service.py it says it is in Verity's own words, but several labels follow the standard's list closely. | Give the labels a text policy look before more screens show them. | coverage/gov-cs-hr.md Content problems and gaps found |
| Verity check runner (ME-2) | The runner for Verity checks is not built, so every P1 check here, existing or new, is planned only. | Build ME-2. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 16 |
| access-and-retention-settings-for-the | Backups and platform retention of the Documents module are Verity's own controls; the customer relies on Verity as a supplier for them (GOV-28). | Treat Verity as a supplier in the customer's vendor list and supply its assurance, rather than asking the customer for settings. | coverage/gov-cs-hr.json notes, GOV-28 |
| approved-requests-for-a-sample-of objectives | identity-checks.md section 3 lists IAM-01.B to E, HR-06.B, D, IAM-08.C, HR-03.C and omits HR-01.B, HR-01.C and HR-02.C, which objectives.json and operations-checks.md section 4 include. | Use the objectives.json list. | connectors/identity-checks.md section 3; connectors/operations-checks.md section 4 |
| apps.admins_limited role map | Section 2.2 says the provider role map is in section 8; section 8 has no role map. Role fields are spread over sections 3 to 7 (Vercel owner, Supabase role_name, PostHog level, SendGrid user_type and is_admin, OpenAI owner, Anthropic admin roles; Heroku, HubSpot unverified). | Write a role map per provider when the checks are built. | connectors/phase3-catalogue.md 2.2, 8 |
| competitor practice | Vanta, Drata, Secureframe and Sprinto were not researched for any phase 3 provider; the shared web search budget was exhausted. | Add per provider when its full connector document is written. | connectors/phase3-catalogue.md 9 |
| credential pattern table | 02 section 2.2 lists Google Workspace and Jira under vendor app consent and Datadog as API key plus application key, while the connector documents recommend Verity's service account with domain wide delegation for Google, a scoped API token on a service account first for Jira, and a Service Access Token for Datadog. | Align the table with the connector documents. | 02-integration-model.md section 2.2; connectors/google-workspace.md; connectors/jira.md; connectors/datadog.md |
| current-organization-chart-with-reporting-lines | Owner functions name only security roles; reporting lines need the directory's manager field (GOV-21, HR-04, HR-07). | Read title, department and manager from the identity provider (NEED identity_provider, P2) or the HR system (P3). | coverage/gov-cs-hr.json notes |
| docs/architecture/check-catalogue.md | Says 81 tests, and Appendix C of control-framework-requirements.md says Verity tests are planned; checks.json has 93 checks and the 30 verity checks run. | Regenerate the catalogue and update Appendix C. | coverage/sd-lm-bc.md (Content problems found) |
| entra provider content example | The example's auth fields ask for a client_secret, while entra-id.md uses a certificate credential with a Verity generated key pair and no secret. | Replace the secret field with the certificate download and tenant and client ids. | 02-integration-model.md section 2.5; connectors/entra-id.md section 2 |
| key-rotation-records, inventory-of-service-accounts-and-keys, records-of-rotation-or-review, list-of-privileged-accounts-with-approval | azure.md and gcp.md section 6 describe these as 'person -> person + check', but artifacts.json already lists cloud.key_rotation, cloud.machine_credentials_rotated and cloud.least_privilege on them (aws.md correctly says 'already lists'). | No content change: Azure and Google Cloud just become further implementations of checks already named. | connectors/azure.md section 6; connectors/gcp.md section 6 |
| observation types for members | 01-evidence-model.md 1.4 lists repository, branch_rule, change, review, pipeline_run and deployment for version_control and ci_cd, but no type for organization members, which vcs.access_list_exported and vcs.org_two_factor_required read. | Add a member or account observation type for version_control (for example aligned with identity.user fields). | extractor observation from 01-evidence-model.md 1.4 and connectors/github.md section 4 |
| observation types for phase 3 capabilities | 01-evidence-model.md 1.4 defines no observation type for vulnerability_scanner (scanner asset, finding), business_applications (application member, API key, sign in setting) or ai_providers (retention setting, usage). The phase 3 document does not propose any. | Add observation types for these capabilities before the checks are built (extraction observation). | 01-evidence-model.md 1.4 vs connectors/phase3-catalogue.md |
| pack placement | CS-06, CS-07 and HR-09 sit in the ISO pack (CL-10). The successors CS-08 and GOV-31 would too; GOV-32 maps SOC2:CC5.3 and needs the shared pack. | Place CS-08 and GOV-31 in the ISO pack and GOV-32 in the shared pack. | coverage/gov-cs-hr.md Content problems and gaps found |
| phase 3 unverified facts | Not verified this round: BMC Helix Discovery entirely; SigNoz and Better Stack endpoints; ClickUp and Monday audit logs and scopes; Heroku, Render, Netlify and Qovery endpoint paths and fields; HubSpot scope names; Intercom and HubSpot two factor fields; Tenable export endpoint paths (names confirmed, paths not re read); Nessus Professional and Security Center APIs; Rapid7 read only role name and rate limits; Qualys severity names; OpenAI admin key creator and audit log activation; whether OpenAI's Go SDK covers admin endpoints; whether an Anthropic non admin key can read members and keys; whether a Grafana Viewer can read the alert provisioning API; Grafana's on call product; Grafana and Intercom SSO status. | Verify each before the provider is built. | connectors/phase3-catalogue.md 9 |
| readiness engine CL-3 | Coverage cannot depend on applicability: a split with a conditional successor lowers ISO status when the successor is not applicable (A.5.3 with IAM-13, A.8.9 with NS-14). | Model 'full when the sibling is not applicable' before the splits ship. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found) row 14 |
