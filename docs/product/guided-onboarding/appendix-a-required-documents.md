# Appendix A: required documents and records

Appendix to the guided onboarding plan. Read [README.md](README.md) first.

This is the content behind the Required documents list (requirement group RD in
[part 2](02-requirements.md), screen in [part 3](03-experience.md) section 6, library changes CL-4
to CL-6 in [part 5](05-control-library-and-objectives.md)).

Source: the internal compliance review of 2026-11-21. It is Verity's own pass and has not been
checked by a second qualified person (decision D-9). Clause and criterion references are
identifiers only. No standard text is reproduced.

## How the product uses each column

| Column | Becomes |
|---|---|
| Document or record | The row title on the Required documents list |
| ISO clause or control, SOC 2 criteria | The "Needed for" chips, derived from the controls once CL-4 ships. Until then, read from this table |
| Template key | The "Start from template" action. `NEW` means Verity still has to write it (CL-6). "Product" means the row takes its state from a module and links there (RD-5). "none" means a checklist, a record or guidance |
| Verity controls | The "Supports" column and the links created with the draft (RD-3) |
| Gap | Work in part 5, by finding id |

## A.1 Master list, both frameworks

| # | Document or record | ISO clause or control | SOC 2 criteria | Template key | Verity controls | Gap |
|---|---|---|---|---|---|---|
| 1 | ISMS scope statement | 4.3, 4.4 | none | `isms-scope-statement` | GOV-23 | None. Add data flow prompt. |
| 2 | SOC 2 system description | 4.3 (supports) | CC2.2, CC2.3, CC3.1 | NEW `soc2-system-description` | GOV-22, PE-01 | Missing (LD-13). |
| 3 | Management assertion | none | report section | none, guidance | none | Guidance only. |
| 4 | Policy statement by top management | 5.1, 5.2, A.5.1 | CC5.3 | NEW `information-security-policy-statement` | GOV-17, CS-04 | Missing (LD-08). |
| 5 | Staff security policy | A.5.1, A.5.10, A.5.36, A.6.8, A.7.7, A.8.1 | CC1.1, CC2.2, CC5.3 | `information-security-policy` | GOV-17, CS-04, CS-05 | Overlaps rows 26 and 27 (LD-07). |
| 6 | Context, interested parties and obligations register | 4.1, 4.2, A.5.31 | CC2.3 | `context-and-interested-parties` | GOV-24, GOV-25, GOV-05 | Bind GOV-05 item to it. |
| 7 | Roles and responsibilities, organisation chart, security officer appointment | 5.3, A.5.2, A.5.4 | CC1.2, CC1.3, CC1.5 | `information-security-roles-and-responsibilities` | GOV-21, GOV-10, GOV-09 | Chart and appointment are uploads. |
| 8 | Oversight body charter and minutes | 5.1 | CC1.2 | NEW `oversight-body-charter` | GOV-02 | Missing template. |
| 9 | Risk assessment and treatment method | 6.1.1 to 6.1.3, 8.2, 8.3 | CC3.2, CC3.4, CC5.1 | `risk-assessment-methodology` | GOV-18, GOV-19, GOV-20, GOV-03 | Add design evidence item on GOV-18 (LD-21). |
| 10 | Risk management policy | 6.1.1, A.5.8 | CC3.1, CC3.2, CC9.1 | `risk-management-policy` | GOV-18, GOV-20 | Overlaps row 9. Recommend one, not both. |
| 11 | Risk assessment results and register | 6.1.2, 8.2 | CC3.2, CC3.3 | Product (Risk) | GOV-18, GOV-19, GOV-12 | Confirm dated report export. |
| 12 | Risk treatment plan and acceptance of remaining risk | 6.1.3, 8.3 | CC3.2, CC5.1, CC9.1 | Product (Risk, Tasks) | GOV-20, GOV-19, GOV-07 | Approval is an upload. |
| 13 | Statement of Applicability | 6.1.3 | none | Product (Applicability, XLSX) | GOV-27 | Version approval is an upload. |
| 14 | Security objectives and measurement plan, with results | 6.2, 7.1, 9.1 | CC4.1 | `security-objectives-plan` | GOV-26, GOV-06 | Results are uploads. |
| 15 | Competence requirements and records, awareness programme | 7.2, 7.3, A.6.3 | CC1.4, CC2.2 | `competence-and-awareness-procedure` | HR-09, HR-08, HR-04 | HR-09 not available to SOC 2 only workspaces. |
| 16 | Communication plan and contact list for authorities | 7.4, A.5.5, A.5.6 | CC2.2, CC2.3, P6.6 | `security-communication-plan` | CS-06, CS-07, CS-03, DM-01 | CS-06, CS-07 are ISO pack only. |
| 17 | Document and record control procedure | 7.5.1 to 7.5.3, A.5.33 | CC5.3 | `document-control-procedure` | GOV-28, GOV-01 | None. |
| 18 | Security program operating plan | 4.4, 6.3, 8.1 | none | NEW `isms-operating-plan` | GOV-29 | Missing (LD-09). |
| 19 | Operating procedures, one per routine task | A.5.37 | CC5.3 | `operating-procedure-template` | GOV-28, SD-10, BC-03, LM-06 | None. |
| 20 | Internal audit procedure, programme, reports | 9.2.1, 9.2.2, A.5.35, A.5.36, A.8.34 | CC4.1 | `internal-audit-procedure` | GOV-13 | Report is an upload. |
| 21 | Management review procedure and minutes | 9.3.1 to 9.3.3, 5.1 | CC1.2, CC4.2 | `management-review-procedure` | GOV-15 | Add design evidence item on GOV-15. |
| 22 | Corrective action procedure and log | 10.1, 10.2 | CC4.2 | `corrective-action-procedure` | GOV-08, GOV-30, LM-05 | Add design evidence item on GOV-08. |
| 23 | Code of conduct with acknowledgements | A.5.4, A.6.2, A.6.4 | CC1.1, CC1.5, CC2.2 | `code-of-conduct` | GOV-04, GOV-11 | None. |
| 24 | People security policy (screening, terms, discipline, leaving) | A.6.1, A.6.2, A.6.4 to A.6.6 | CC1.1, CC1.4, CC1.5, CC6.2 | `human-resource-security-policy` | HR-01, HR-02, HR-05, HR-06, GOV-11 | Wording (LD-01). |
| 25 | Joiner, mover and leaver checklists | A.5.11, A.5.16, A.5.18, A.6.5 | CC6.2, CC6.3 | NEW `joiner-mover-leaver-checklists` | HR-05, HR-06, HR-03, IAM-12 | Missing. |
| 26 | Acceptable use policy | A.5.10, A.5.14, A.5.17, A.6.2, A.7.7, A.8.1 | CC1.1, CC2.2, CC6.7, CC6.8 | `acceptable-use-policy` | GOV-17, GOV-04, EP-06 | None. |
| 27 | Remote working policy | A.5.14, A.6.7, A.7.7, A.7.9, A.8.1 | CC6.6, CC6.7 | `remote-working-policy` | GOV-17, NS-11, EP-03 | None. |
| 28 | Access control policy | A.5.3, A.5.15 to A.5.18, A.8.2 to A.8.5, A.8.18 | CC6.1, CC6.2, CC6.3 | `access-control-policy` | IAM-01, IAM-02, IAM-03, IAM-06, IAM-07, IAM-08, IAM-09, IAM-12 | Wording (LD-01). |
| 29 | Role and access matrix, conflicting duties matrix | A.5.3, A.5.15, A.8.3 | CC5.1, CC6.3 | Appendix B of `access-control-policy` | IAM-08, IAM-09 | Partial. No conflicting duties matrix. |
| 30 | Asset management policy and register | A.5.9 to A.5.11, A.7.9, A.7.10, A.7.14, A.8.10 | CC2.1, CC6.1, CC6.5 | `asset-management-policy`, Product (Assets) | LM-01, DM-16, EP-05 | Wording (LD-01). |
| 31 | Data classification, handling, retention and disposal policy with retention schedule | A.5.12 to A.5.14, A.5.33, A.5.34, A.8.10 | C1.1, C1.2, CC6.5, P4.2, P4.3 | `data-management-policy` | DM-04, DM-08, DM-16 | Add sharing rules section. |
| 32 | Data inventory and data flow map | A.5.9, A.5.12 | C1.1, CC2.1 (proposed) | Product (Assets) | DM-06 | No diagram template. |
| 33 | Encryption and key rules | A.8.24 | CC6.1, CC6.7 | `cryptography-policy` | NS-01, NS-02, NS-06, EP-02 | Key lifecycle thin. Row 35 completes it. |
| 34 | Operations security policy | A.5.7, A.8.6 to A.8.9, A.8.11 to A.8.13, A.8.15 to A.8.17, A.8.19, A.8.23, A.8.31, A.8.32, A.8.34 | CC6.8, CC7.1, CC7.2, CC8.1, A1.1, A1.2 | `operations-security-policy` | BC-01, BC-04, EP-01, EP-04, EP-07, LM-11, LM-12, NS-04, DM-18, DM-19 | Wording (LD-01). |
| 35 | Infrastructure security standard | A.8.9, A.8.15 to A.8.17, A.8.20 to A.8.22, A.8.24 | CC6.1, CC6.6, CC6.7, CC7.1, CC7.2 | NEW `infrastructure-security-standard` | NS-01 to NS-09, NS-11, NS-12, LM-02, LM-03, LM-09, IAM-11 | Missing (LD-10). |
| 36 | Endpoint security standard | A.7.9, A.8.1, A.8.7 | CC6.5, CC6.7, CC6.8 | NEW `endpoint-security-standard` | EP-01 to EP-06 | Missing (LD-10). |
| 37 | Secure development policy | A.8.25 to A.8.31, A.8.33 | CC7.1, CC8.1 | `secure-development-policy` | SD-10, SD-12, DM-13 | Wording (LD-01). |
| 38 | Engineering security standard | A.5.32, A.8.4, A.8.25, A.8.28, A.8.29 | CC7.1, CC8.1, PI1.2 | NEW `engineering-security-standard` | SD-02, SD-03, SD-05, SD-06, SD-11, SD-13 | Missing (LD-10). |
| 39 | Change management procedure | 6.3, A.8.9, A.8.31, A.8.32 | CC3.4, CC8.1 | `change-management-procedure` | SD-01, SD-04, SD-13, SD-14, GOV-03 | None. |
| 40 | Incident response plan with notification steps | A.5.24 to A.5.28, A.6.8 | CC2.2, CC2.3, CC7.3 to CC7.5, P6.6 | `incident-response-plan` | LM-04 to LM-07, LM-10, CS-01, CS-03, DM-01 | Health appendix optional (LD-07b). |
| 41 | Incident register for the period | A.5.25 to A.5.27 | CC7.3 to CC7.5 | Product (Tasks) or upload | LM-04, LM-05, LM-06, LM-07 | Missing evidence item (LD-20). |
| 42 | Continuity and recovery plan, with test report | A.5.29, A.5.30, A.8.13, A.8.14 | CC7.5, CC9.1, A1.2, A1.3 | `business-continuity-and-disaster-recovery-plan` | BC-03, BC-02, BC-01 | None beyond row 43. |
| 43 | Business impact analysis | A.5.29, A.5.30 | CC9.1, A1.2 | NEW `business-impact-analysis` | BC-03 | Missing (LD-16). |
| 44 | Supplier security policy, vendor register, assessments, contract terms | A.5.19 to A.5.22 | CC9.2, P6.4, P6.5 | `third-party-management-policy`, Product (Vendors) | BC-07, BC-08, BC-06, DM-10, DM-17 | Wording (LD-01). |
| 45 | Cloud services policy and provider assurance review | A.5.23, A.7 (provided by supplier) | CC6.4, CC9.2 | `cloud-services-security-policy`, Product (Vendors) | PE-01, BC-08, BC-05, NS-04 | None. |
| 46 | Physical security policy for offices | A.7.1 to A.7.6, A.7.11 | CC6.4 | `physical-security-policy` | PE-02 | Wording (LD-01). Only when offices exist. |
| 47 | Site and equipment protection standard | A.7.5, A.7.8, A.7.11 to A.7.13 | A1.2 (proposed) | NEW `site-and-equipment-protection-standard` | PE-03 | Only when own sites (LD-12). |
| 48 | Privacy notice | A.5.34 | P1.1 | NEW `privacy-notice-outline` | DM-15 | Missing (LD-11). |
| 49 | Privacy requests and complaints procedure | A.5.34 | P5.1, P5.2, P6.7, P8.1 | NEW `privacy-requests-and-complaints-procedure` | DM-05, DM-11, DM-14 | Missing (LD-11). |
| 50 | Personal data handling procedure and registers | A.5.34 | P2.1, P3.1, P3.2, P4.1, P6.1 to P6.3, P7.1 | NEW `personal-data-handling-procedure` | DM-02, DM-03, DM-07, DM-09, DM-12 | Missing (LD-11). |
| 51 | Processing integrity procedure and specifications | none | PI1.1 to PI1.5 | NEW `processing-integrity-procedure` | SD-05, SD-07, SD-08, SD-09 | Missing. Only when PI is elected. |
| 52 | Published customer commitments (terms, service levels, trust page) | 4.2 (input) | CC2.3 | none, checklist | CS-02, CS-01 | Not a template. Checklist of what to publish and review. |
| 53 | Secrecy and ownership agreement checklist | A.6.6, A.5.32 | CC1.1, C1.1 | none, checklist | HR-02 | Checklist of clauses, not agreement text. |
| 54 | Penetration test report and written rules of engagement | A.5.35, A.8.29, A.8.34 | CC4.1, CC7.1 | none, record | GOV-16 | Record only. |

## A.2 When a row appears

| Condition from the profile or engagement | Rows |
|---|---|
| ISO 27001 is active | 1, 4, 6, 13, 14, 15, 16, 17, 18, 20, 21, 22, and every row with an ISO reference |
| SOC 2 is active | 2, 3, and every row with a SOC 2 reference |
| Offices exist | 46 |
| Own data centre, server room or comms cabinet | 47 |
| Remote or hybrid working | 27 |
| Personal data role is controller, processor or both, or the privacy category is elected | 48, 49, 50 |
| Processing integrity is elected | 51 |
| Builds software in house | 37, 38 |
| Availability is elected, or ISO 27001 is active | 43 |
| Always | 5, 7, 9, 11, 12, 19, 23, 24, 25, 26, 28 to 36, 39 to 42, 44, 45, 52, 53, 54 |

Rows 9 and 10 overlap. The list shows row 9 and offers row 10 only to a workspace that already
has a risk management policy.

## A.3 ISO 27001 clauses that expect a document or record

What an auditor asks to see for each clause, and where it comes from in Verity.

| Clause | What an auditor asks to see | Template key | Verity control | Status |
|---|---|---|---|---|
| 4.3 | Scope of the management system | `isms-scope-statement` | GOV-23 | Covered. Check `verity.isms.scope_documented` runs. Approver seniority is not recorded. The template has no data flow diagram prompt although GOV-23 guidance asks for one (minor: add a prompt in section 2). |
| 5.2 | Policy set by top management, with the two commitments and the basis for objectives | `information-security-policy` claims it | GOV-17, CS-04 | Missing content. See LD-08. |
| 6.1.2 | The risk assessment process | `risk-assessment-methodology` | GOV-18, GOV-19 | Covered by text. GOV-18 has no design evidence item for it and no presence check (LD-04, LD-21). `risk-management-policy` overlaps and can carry a second scale. |
| 6.1.3 | The risk treatment process | `risk-assessment-methodology` | GOV-19, GOV-20, GOV-07 | Covered. |
| 6.1.3 d | Statement of Applicability | none, produced by the Applicability page and XLSX export | GOV-27 | Covered by the product. Approval of each version is an upload with no workflow. |
| 6.1.3 e, f | Treatment plan, and owner acceptance of remaining risk | none, risk module | GOV-20 | Covered by the product. "Risk owner approval of each treatment plan" is an upload. |
| 6.2 | Objectives and how they will be reached | `security-objectives-plan` | GOV-26 | Covered. Check runs. |
| 7.2 | Evidence of competence | `competence-and-awareness-procedure` | HR-09, HR-04, HR-08 | Covered. Records are uploads. |
| 7.5.1 b | Documents the organisation decides it needs | `document-control-procedure` section 1 | GOV-28 | Partial. The list lives in prose only. The checklist of A3 should be the machine form. |
| 7.5.2, 7.5.3 | Creation, approval, control of documents and records | `document-control-procedure` | GOV-28, GOV-01 | Covered. Check `verity.documents.controlled` runs. |
| 8.1 | Evidence that processes ran as planned, including changes and outsourced work | none | GOV-29 | Missing template. See LD-09. `operating-procedure-template` covers A.5.37 only. |
| 8.2 | Results of risk assessments | none, risk module | GOV-18, GOV-03 | Covered by the product. Confirm the risk module can export a dated assessment report, since the evidence item is "Risk assessment report with method and scope". |
| 8.3 | Results of risk treatment | none, risk module and Tasks | GOV-20 | Covered by the product. |
| 9.1 | What is measured, and the results | `security-objectives-plan` sections 4 and 5 | GOV-26, GOV-06, GOV-15 | Partial. The plan exists. Results are an upload ("Measures and results compared with targets"). No record type for a measure and its readings. |
| 9.2 | Audit programme and audit results | `internal-audit-procedure` (programme in Appendix A) | GOV-13 | Covered for the programme. The audit report is an upload, and `verity.audit.internal_in_12_months` accepts any non policy file on GOV-13. |
| 9.3 | Results of management reviews | `management-review-procedure` (minutes in Appendix A) | GOV-15 | Covered. Same limit on the check. |
| 10.2 | Nonconformities, actions and results | `corrective-action-procedure`, Tasks | GOV-08, LM-05 | Covered. |
| 4.1, 4.2, 5.3, 6.3, 7.4 (not mandatory as documents, always requested) | Context, interested parties, roles, planned changes, communication | `context-and-interested-parties`, `information-security-roles-and-responsibilities`, `change-management-procedure` section 6, `security-communication-plan` | GOV-24, GOV-25, GOV-21, GOV-10, GOV-29, CS-06 | Covered. |

## A.4 SOC 2 documents and records by criteria series

| Series | Documents and records | Template key | Controls | Status |
|---|---|---|---|---|
| CC1 | Code of conduct with acknowledgements, organisation chart, role descriptions, oversight body charter and minutes, screening policy, secrecy agreements, performance review process, discipline procedure | `code-of-conduct`, `information-security-roles-and-responsibilities`, `human-resource-security-policy` | GOV-04, GOV-21, GOV-10, GOV-09, GOV-02, GOV-11, HR-01, HR-02, HR-04, HR-07 | Partial. No charter template for GOV-02, no checklist for agreements (HR-02). CC1.3 is listed on no template. |
| CC2 | Security policy acknowledged by staff, reporting channel, communication plan, published commitments, customer notification terms, system description | `information-security-policy`, `security-communication-plan`, `incident-response-plan` | CS-04, CS-03, CS-05, CS-06, CS-02, CS-01, HR-08, LM-01, LM-02 | Partial. System description missing (LD-13). CS-06 is ISO pack only. |
| CC3 | Risk method, assessment report, register, fraud assessment, change triggered reviews, statement of commitments and system requirements | `risk-assessment-methodology`, `risk-management-policy` | GOV-18, GOV-19, GOV-20, GOV-12, GOV-03, GOV-22 | Covered except GOV-22 document. |
| CC4 | Monitoring results, internal audit or readiness report, penetration test, deficiency log, management review minutes | `internal-audit-procedure`, `corrective-action-procedure`, `management-review-procedure` | GOV-06, GOV-13, GOV-16, GOV-08, GOV-15 | Covered. |
| CC5 | Policy set with approvals and yearly review, risk to control links, general technology control coverage | topic policies, `document-control-procedure` | GOV-17, GOV-01, GOV-07, GOV-19, GOV-14 | Partial. GOV-14 has no template for its coverage inventory. CC5.2 rests on one partial control (LD-14). |
| CC6 | Access policy, access matrix, reviews, encryption and key rules, network standard, endpoint standard, physical policy, provider assurance review, disposal records | `access-control-policy`, `cryptography-policy`, `physical-security-policy`, `asset-management-policy`, `data-management-policy`, `cloud-services-security-policy` | IAM-01 to IAM-12, NS-01 to NS-11, EP-01 to EP-06, PE-01, PE-02, DM-16, HR-05 | Partial. Network and endpoint standards missing (LD-10). |
| CC7 | Vulnerability and patch rules, logging and alerting standard, incident plan, incident register, post incident reviews, exercise report, on call schedule | `operations-security-policy`, `incident-response-plan` | LM-02 to LM-11, NS-04, NS-05, EP-04, SD-03, GOV-16 | Partial. No incident register item (LD-20). |
| CC8 | Change procedure, development policy, emergency changes, deployment records | `change-management-procedure`, `secure-development-policy` | SD-01, SD-02, SD-04, SD-06, SD-10, SD-12, SD-13, SD-14 | Covered. |
| CC9 | Continuity plan, impact analysis, insurance decision, vendor policy, vendor register and assessments | `business-continuity-and-disaster-recovery-plan`, `third-party-management-policy` | GOV-20, BC-01, BC-03, BC-05 to BC-08, DM-10, HR-03, PE-01 | Partial. No impact analysis, no insurance consideration (LD-16). CC9.1 is listed on no template. |
| A1 | Capacity reviews, backup rules, restore tests, continuity test, environmental protection | `operations-security-policy`, `business-continuity-and-disaster-recovery-plan` | BC-01 to BC-04 | Partial. Environmental protection unmapped (LD-15). |
| C1 | Classification and handling rules, data inventory, retention schedule, disposal records, secrecy agreements | `data-management-policy` | DM-04, DM-06, DM-08, DM-13, DM-16, HR-02 | Covered by text. C1.1 and C1.2 are listed on no template (LD-03). |
| PI1 | Processing specifications, input validation rules, reconciliation and error handling procedure, output checks, storage integrity | none | SD-05, SD-07, SD-08, SD-09, SD-02 | Missing. Every PI criterion rests on partial controls only (LD-14, LD-18). |
| P1 to P8 | Privacy notice, consent records, purpose register, retention and disposal, request and correction procedures, disclosure register, processor agreements, breach notification, complaint handling, privacy compliance review | none except P6.6 on `security-communication-plan` | DM-01 to DM-03, DM-05, DM-07 to DM-12, DM-14 to DM-17, BC-06, BC-08 | Missing (LD-11). |
| Description (description criteria, section DC 200) | System description: services, principal commitments and system requirements, the five components (infrastructure, software, people, procedures, data), boundaries, subservice organisations and whether they are carved out or included, controls expected of user entities, relevant incidents and changes in the period, criteria not applicable with reasons | none | GOV-22 (two upload items) | Missing. No product object exists (LD-13). |
| Management assertion | Signed statement by management that accompanies the description | none | none | Missing. Guidance only: the audit firm supplies the format. Verity should not ship assertion wording. |

## A.5 Order in which the list is shown

1. Scope statement, policy statement by top management, roles and responsibilities.
2. Risk method, then the risk register and treatment plan, then the Statement of Applicability.
3. Staff security policy, acceptable use, code of conduct (the three sent to all staff).
4. Topic policies in the order of the control families: access, assets and data, encryption,
   operations, development and change, incidents, continuity, suppliers, people, physical.
5. Standards and procedures that sit under those policies.
6. ISO management system procedures: document control, objectives, competence, communication,
   operating plan, internal audit, management review, corrective action.
7. SOC 2 system description, then category specific documents.
8. Records and checklists.
