# 7. Control matrix

One row per control: the 133 shipped controls and the 15 proposed ones (11 successors of splits, 4 additions).
Generated from `coverage/*.json`, `coverage/*.controls.json`, `coverage/needs-resolution.json`,
`checks-proposed.json` and the seed content. The full lists of check keys and templates per control are in
[07-control-matrix.csv](07-control-matrix.csv); this page shows the counts.

## How the columns are counted

| Column | Meaning |
|---|---|
| Frameworks | SOC 2 criteria and ISO 27001 references mapped in `template_requirements.json` (shipped controls), or in the `*.controls.json` proposal (proposed controls). Mapping changes proposed for shipped controls are in [06-control-changes.md](06-control-changes.md), not here |
| Objectives | Shipped count, then the count after the proposed adds, moves and removals |
| P1, P2, P3, people | Artifact rows of the control in the coverage files, by the phase the researcher gave the artifact. "people" is people-only |
| Conn, Verity | Distinct connector checks and Verity module checks named on the control's artifacts, including needs resolved in `needs-resolution.json`. Proposed keys are counted after aliases are resolved. "e+p" is existing plus proposed |
| Docs | Distinct document templates named as sources |
| Auto by P2 | Share of the control's artifacts with at least one check source (full or partial) that can run by the end of Phase 2: a `verity.*` check, or a connector check with a provider that is available or planned for Phase 2 in `capabilities.json`. Device, endpoint and HR checks do not count, because those providers are not planned |
| Full by P2 | The same, counting only checks that fill the artifact in full (an exact need match, or a planned source marked `fills: full`). Under the pending automation rule only these can satisfy an artifact without a person (rule B); a partial check only takes satisfaction away (rule A, 01-evidence-model.md 1.2) |

## By family

| Family | Controls | Proposed | Artifacts | P1 | P2 | P3 | People only | Auto by P2 | Full by P2 |
|---|---|---|---|---|---|---|---|---|---|
| BC | 10 | 2 | 54 | 47 | 5 | 0 | 2 | 94% | 0% |
| CS | 8 | 1 | 41 | 36 | 2 | 1 | 2 | 93% | 0% |
| DM | 19 | 0 | 100 | 91 | 6 | 2 | 1 | 92% | 0% |
| EP | 8 | 1 | 47 | 29 | 1 | 17 | 0 | 74% | 0% |
| GOV | 32 | 2 | 200 | 190 | 2 | 3 | 5 | 94% | 5% |
| HR | 9 | 0 | 58 | 40 | 7 | 11 | 0 | 90% | 3% |
| IAM | 14 | 2 | 80 | 45 | 25 | 8 | 2 | 98% | 1% |
| LM | 13 | 1 | 62 | 60 | 2 | 0 | 0 | 95% | 0% |
| NS | 14 | 2 | 76 | 49 | 23 | 1 | 3 | 99% | 3% |
| PE | 3 | 0 | 18 | 15 | 0 | 1 | 2 | 89% | 6% |
| SD | 18 | 4 | 102 | 88 | 13 | 0 | 1 | 94% | 6% |
| All | 148 | 15 | 838 | 690 | 86 | 44 | 18 | 93% | 3% |

Artifact rows count an artifact once per control it serves, so the total is higher than the 338 artifact types.

## Per control

| Code | Name | Status | SOC 2 | ISO 27001 | Objectives | P1 | P2 | P3 | People | Conn e+p | Verity e+p | Docs | Auto by P2 | Full by P2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BC-01 | Automated, monitored backups | shipped | A1.2 CC9.1 PI1.5 | A.5.29 A.5.30 A.5.33 A.8.13 | 4 to 6 | 6 | 2 | 0 | 0 | 9+2 | 2+0 | 2 | 100% | 0% |
| BC-02 | Backup restore testing | shipped | A1.3 | A.5.30 A.8.13 | 5 | 4 | 1 | 0 | 0 | 1+1 | 2+2 | 2 | 100% | 0% |
| BC-03 | Business continuity / disaster recovery plan | shipped | A1.2 CC9.1 | A.5.29 A.5.30 A.5.37 A.8.14 | 5 to 4 | 4 | 0 | 0 | 0 | 0+0 | 1+2 | 2 | 100% | 0% |
| BC-04 | Capacity management | shipped | A1.1 | A.8.6 | 4 | 4 | 0 | 0 | 0 | 4+0 | 2+1 | 2 | 100% | 0% |
| BC-05 | Shadow-IT detection | shipped | CC9.2 | A.5.23 | 4 | 5 | 0 | 0 | 0 | 1+0 | 2+2 | 2 | 100% | 0% |
| BC-06 | Subprocessor management | shipped | CC9.2 P6.1 P6.4 | A.5.21 A.5.22 | 4 | 4 | 0 | 0 | 1 | 0+0 | 2+1 | 1 | 80% | 0% |
| BC-07 | Vendor inventory | shipped | CC9.2 | A.5.19 A.5.22 | 4 to 5 | 4 | 0 | 0 | 0 | 1+0 | 2+3 | 1 | 100% | 0% |
| BC-08 | Vendor security due diligence | shipped | CC9.2 P6.4 | A.5.19 A.5.20 A.5.21 A.5.22 A.5.23 A.8.21 A.8.26 A.8.30 | 5 to 7 | 9 | 0 | 0 | 0 | 0+0 | 4+5 | 2 | 100% | 0% |
| BC-09 | Redundancy and failover of critical services | proposed (from BC-03) | A1.2 | A.5.30 A.8.14 | 4 | 3 | 2 | 0 | 0 | 0+1 | 1+1 | 1 | 80% | 0% |
| BC-10 | Oversight of outsourced development | proposed (from BC-08) | CC9.2 | A.8.30 | 3 | 4 | 0 | 0 | 1 | 1+0 | 1+1 | 1 | 80% | 0% |
| CS-01 | Customer breach-notification commitment | shipped | CC2.3 |  | 4 | 4 | 1 | 0 | 0 | 1+1 | 1+2 | 1 | 100% | 0% |
| CS-02 | External security commitments | shipped | CC2.3 PI1.1 |  | 5 to 6 | 4 | 0 | 0 | 0 | 0+0 | 1+2 | 3 | 100% | 0% |
| CS-03 | Security incident reporting channel | shipped | CC2.2 CC2.3 | A.5.24 A.6.8 | 4 | 7 | 0 | 0 | 0 | 1+2 | 2+1 | 4 | 86% | 0% |
| CS-04 | Internal policy portal | shipped | CC2.2 | 5.2 7.3 A.5.1 A.6.3 | 5 | 6 | 0 | 1 | 0 | 2+1 | 3+3 | 2 | 100% | 0% |
| CS-05 | Whistleblower / ethics reporting mechanism | shipped | CC1.1 CC2.2 |  | 5 | 4 | 0 | 0 | 1 | 0+0 | 2+4 | 3 | 80% | 0% |
| CS-06 | Security communication plan | shipped |  | 7.4 A.5.1 | 4 | 5 | 0 | 0 | 0 | 1+1 | 3+3 | 1 | 100% | 0% |
| CS-07 | Contacts with authorities and security communities | shipped |  | A.5.5 A.5.6 | 4 to 3 | 4 | 1 | 0 | 0 | 1+1 | 2+2 | 1 | 100% | 0% |
| CS-08 | Security community memberships and advisories | proposed (from CS-07) |  | A.5.6 | 3 | 2 | 0 | 0 | 1 | 0+0 | 1+2 | 1 | 67% | 0% |
| DM-01 | Breach notification process | shipped | P6.6 | A.5.5 | 4 to 5 | 6 | 0 | 0 | 0 | 0+0 | 1+1 | 2 | 100% | 0% |
| DM-02 | Unauthorized-disclosure recordkeeping | shipped | P6.3 |  | 4 | 4 | 0 | 0 | 0 | 0+0 | 1+1 | 2 | 75% | 0% |
| DM-03 | Consent and choice management | shipped | P2.1 P3.2 | A.5.34 | 4 to 5 | 3 | 0 | 1 | 0 | 0+0 | 1+1 | 2 | 75% | 0% |
| DM-04 | Data classification policy | shipped | C1.1 CC2.1 | A.5.10 A.5.12 A.5.13 A.5.14 A.7.10 | 4 | 6 | 0 | 0 | 0 | 1+0 | 4+0 | 2 | 100% | 0% |
| DM-05 | Personal-information correction | shipped | P5.2 P7.1 | A.5.34 | 4 | 4 | 0 | 0 | 0 | 1+0 | 1+3 | 1 | 100% | 0% |
| DM-06 | Data inventory and data map | shipped | C1.1 CC2.1 | A.5.12 A.5.9 | 4 | 6 | 0 | 0 | 0 | 1+0 | 3+3 | 2 | 100% | 0% |
| DM-07 | Data minimization | shipped | P3.1 |  | 3 | 3 | 0 | 0 | 1 | 0+0 | 1+1 | 1 | 75% | 0% |
| DM-08 | Data retention schedule | shipped | C1.2 P4.2 PI1.5 | A.5.33 A.8.10 | 4 | 3 | 1 | 0 | 0 | 3+0 | 1+0 | 3 | 100% | 0% |
| DM-09 | Authorized-disclosure governance | shipped | P6.1 P6.2 P6.7 | A.5.14 | 4 | 7 | 0 | 0 | 0 | 1+0 | 2+2 | 3 | 100% | 0% |
| DM-10 | Data processing agreements with vendors | shipped | CC9.2 P6.4 | A.5.20 A.5.34 | 4 | 4 | 0 | 0 | 0 | 0+0 | 3+1 | 1 | 100% | 0% |
| DM-11 | Data-subject access request process | shipped | P5.1 P6.7 | A.5.34 | 4 to 5 | 6 | 0 | 0 | 0 | 1+0 | 1+3 | 1 | 100% | 0% |
| DM-12 | Limit personal-information use to purpose | shipped | P4.1 | A.5.34 | 5 | 6 | 0 | 0 | 0 | 2+0 | 1+3 | 3 | 100% | 0% |
| DM-13 | No production data in lower environments | shipped | C1.1 | A.8.33 | 3 | 4 | 1 | 0 | 0 | 1+0 | 1+0 | 3 | 80% | 0% |
| DM-14 | Privacy inquiry and complaint handling | shipped | P8.1 |  | 4 | 4 | 0 | 0 | 0 | 0+0 | 1+1 | 2 | 100% | 0% |
| DM-15 | Privacy notice | shipped | P1.1 | A.5.34 | 4 | 7 | 0 | 0 | 0 | 1+0 | 1+2 | 3 | 86% | 0% |
| DM-16 | Secure data disposal | shipped | C1.2 CC6.5 P4.3 | A.7.10 A.7.14 A.8.10 | 4 to 3 | 5 | 1 | 0 | 0 | 4+0 | 1+3 | 4 | 100% | 0% |
| DM-17 | Vendor breach-notification terms | shipped | P6.5 | A.5.20 | 4 | 6 | 0 | 0 | 0 | 0+0 | 3+2 | 1 | 100% | 0% |
| DM-18 | Masking sensitive fields | shipped |  | A.8.11 | 5 | 5 | 1 | 0 | 0 | 3+0 | 1+0 | 3 | 83% | 0% |
| DM-19 | Outbound data leak controls | shipped |  | A.5.14 A.7.10 A.8.12 | 5 | 2 | 2 | 1 | 0 | 1+2 | 1+1 | 1 | 60% | 0% |
| EP-01 | Endpoint EDR / anti-malware | shipped | CC6.8 | A.8.1 A.8.16 A.8.7 | 4 | 4 | 0 | 3 | 0 | 3+2 | 2+0 | 2 | 57% | 0% |
| EP-02 | Endpoint full-disk encryption | shipped | CC6.1 CC6.5 CC6.7 | A.7.10 A.7.9 A.8.1 A.8.24 | 4 | 4 | 0 | 1 | 0 | 1+1 | 1+1 | 2 | 80% | 0% |
| EP-03 | Device management (MDM) enrollment | shipped | CC6.5 CC6.8 | A.6.7 A.7.9 A.8.1 A.8.19 | 4 to 5 | 3 | 0 | 5 | 0 | 5+3 | 1+0 | 2 | 75% | 0% |
| EP-04 | Patch management | shipped | CC6.8 CC7.1 | A.8.8 | 5 to 4 | 4 | 0 | 1 | 0 | 2+0 | 2+0 | 2 | 80% | 0% |
| EP-05 | Remote wipe on offboarding / loss | shipped | CC6.5 | A.5.11 A.7.14 A.7.9 A.8.1 | 5 | 3 | 0 | 4 | 0 | 2+2 | 1+1 | 3 | 71% | 0% |
| EP-06 | Screen lock policy | shipped | CC6.1 | A.7.7 A.8.1 | 4 | 4 | 0 | 2 | 0 | 3+0 | 2+0 | 2 | 67% | 0% |
| EP-07 | Harmful website blocking | shipped |  | A.8.23 | 5 to 4 | 3 | 1 | 1 | 0 | 1+1 | 1+2 | 2 | 80% | 0% |
| EP-08 | Equipment and media wiping and disposal | proposed (from DM-16) | C1.2 CC6.5 | A.7.10 A.7.14 | 5 | 4 | 0 | 0 | 0 | 1+0 | 2+0 | 2 | 100% | 0% |
| GOV-01 | Annual policy review | shipped | CC5.3 | 7.5.2 7.5.3 A.5.1 | 5 | 7 | 0 | 0 | 0 | 2+0 | 3+5 | 1 | 100% | 29% |
| GOV-02 | Board / executive security oversight | shipped | CC1.2 | 5.1 7.1 | 5 | 4 | 0 | 0 | 0 | 0+0 | 1+2 | 1 | 75% | 0% |
| GOV-03 | Change-triggered risk review | shipped | CC3.4 | 6.3 8.2 A.5.8 | 5 | 6 | 1 | 0 | 0 | 3+0 | 6+2 | 2 | 100% | 0% |
| GOV-04 | Code of conduct and ethics policy | shipped | CC1.1 | A.5.10 A.5.4 A.6.2 A.6.4 | 4 | 5 | 0 | 1 | 1 | 2+1 | 2+2 | 3 | 86% | 0% |
| GOV-05 | Compliance obligations register | shipped | CC2.3 | 4.2 A.5.31 A.5.32 A.5.34 | 4 to 5 | 8 | 0 | 0 | 0 | 1+0 | 3+3 | 2 | 88% | 0% |
| GOV-06 | Continuous control monitoring | shipped | CC4.1 | 9.1 A.5.36 | 5 | 5 | 0 | 0 | 0 | 1+0 | 4+8 | 2 | 100% | 0% |
| GOV-07 | Risk-to-control mapping | shipped | CC5.1 | 6.1.3 | 5 | 5 | 0 | 0 | 0 | 0+0 | 5+2 | 2 | 100% | 0% |
| GOV-08 | Deficiency remediation tracking | shipped | CC4.2 | 10.2 | 5 to 6 | 6 | 0 | 0 | 0 | 2+1 | 4+7 | 2 | 100% | 0% |
| GOV-09 | Assigned control ownership (RACI) | shipped | CC1.3 CC1.5 | 5.3 A.5.2 | 4 | 4 | 0 | 1 | 0 | 2+1 | 2+3 | 1 | 100% | 20% |
| GOV-10 | Designated security officer | shipped | CC1.3 CC1.5 | 5.1 5.3 A.5.2 | 4 | 4 | 0 | 0 | 0 | 0+0 | 2+5 | 2 | 100% | 0% |
| GOV-11 | Documented disciplinary process | shipped | CC1.1 CC1.5 | 7.3 A.5.4 A.6.4 | 5 | 4 | 0 | 0 | 2 | 0+0 | 2+2 | 2 | 67% | 0% |
| GOV-12 | Fraud and insider-threat consideration | shipped | CC3.3 |  | 4 | 6 | 0 | 0 | 0 | 0+0 | 5+6 | 1 | 100% | 0% |
| GOV-13 | Internal audit | shipped | CC4.1 P8.1 | 9.2.1 9.2.2 A.5.35 A.5.36 | 4 to 6 | 8 | 0 | 0 | 0 | 2+0 | 5+8 | 2 | 100% | 12% |
| GOV-14 | IT general controls coverage | shipped | CC5.2 | 8.1 | 4 | 7 | 0 | 0 | 0 | 4+0 | 5+5 | 1 | 100% | 0% |
| GOV-15 | Periodic management review of security | shipped | CC1.2 CC4.2 | 5.1 7.1 9.1 9.3.1 9.3.2 9.3.3 A.5.36 | 5 to 4 | 4 | 0 | 0 | 0 | 1+0 | 1+5 | 2 | 100% | 0% |
| GOV-16 | Annual penetration test | shipped | CC4.1 CC7.1 | A.5.35 A.8.29 A.8.34 | 5 | 5 | 0 | 0 | 1 | 0+0 | 2+3 | 1 | 83% | 0% |
| GOV-17 | Security policy suite | shipped | CC5.3 | 5.1 5.2 A.5.1 A.5.10 A.5.19 A.5.23 A.6.7 A.7.7 A.7.9 | 4 to 3 | 13 | 0 | 0 | 0 | 0+0 | 2+1 | 11 | 100% | 8% |
| GOV-18 | Annual risk assessment | shipped | CC3.1 CC3.2 | 6.1.1 6.1.2 8.2 | 5 | 11 | 0 | 0 | 0 | 2+0 | 11+6 | 5 | 100% | 0% |
| GOV-19 | Risk register with treatment decisions | shipped | CC3.2 CC5.1 | 6.1.1 6.1.2 6.1.3 8.3 | 4 | 5 | 0 | 0 | 0 | 0+0 | 6+4 | 3 | 100% | 0% |
| GOV-20 | Risk treatment plan | shipped | CC3.2 CC9.1 | 6.1.1 6.1.3 8.3 | 5 to 6 | 8 | 0 | 0 | 0 | 1+0 | 6+7 | 3 | 100% | 0% |
| GOV-21 | Organizational structure and reporting lines | shipped | CC1.3 | 5.3 A.5.2 | 4 to 5 | 5 | 1 | 1 | 0 | 2+1 | 2+5 | 1 | 100% | 0% |
| GOV-22 | System description and service commitments | shipped | CC3.1 | 4.3 | 4 | 6 | 0 | 0 | 0 | 2+0 | 4+3 | 2 | 100% | 0% |
| GOV-23 | ISMS scope and boundaries | shipped |  | 4.3 4.4 | 5 | 8 | 0 | 0 | 0 | 1+0 | 7+4 | 3 | 88% | 12% |
| GOV-24 | Internal and external factors register | shipped |  | 4.1 | 4 | 7 | 0 | 0 | 0 | 0+0 | 8+5 | 3 | 100% | 14% |
| GOV-25 | Interested parties and their requirements | shipped |  | 4.2 | 4 | 4 | 0 | 0 | 0 | 0+0 | 3+2 | 1 | 100% | 25% |
| GOV-26 | Security objectives, plans and measures | shipped |  | 5.1 6.2 7.1 9.1 | 5 | 4 | 0 | 0 | 1 | 0+0 | 3+4 | 2 | 60% | 0% |
| GOV-27 | Statement of Applicability | shipped |  | 6.1.3 | 5 | 5 | 0 | 0 | 0 | 0+0 | 6+4 | 0 | 100% | 0% |
| GOV-28 | Document and record management | shipped |  | 7.5.1 7.5.2 7.5.3 A.5.33 A.5.37 | 5 to 6 | 6 | 0 | 0 | 0 | 0+0 | 3+1 | 2 | 100% | 17% |
| GOV-29 | Security operating plan | shipped |  | 4.4 6.3 8.1 | 5 to 6 | 7 | 0 | 0 | 0 | 1+0 | 3+6 | 2 | 86% | 0% |
| GOV-30 | Security program improvement | shipped |  | 10.1 4.4 6.1.1 | 5 | 7 | 0 | 0 | 0 | 0+0 | 3+7 | 2 | 86% | 0% |
| GOV-31 | Yearly management review by top management | proposed (from GOV-15) |  | 5.1 7.1 9.3.1 9.3.2 9.3.3 | 4 | 3 | 0 | 0 | 0 | 1+0 | 2+4 | 1 | 100% | 0% |
| GOV-32 | Top management security policy statement | proposed (from GOV-17) | CC5.3 | 5.1 5.2 | 2 | 3 | 0 | 0 | 0 | 0+0 | 3+3 | 1 | 100% | 33% |
| HR-01 | Pre-hire background checks | shipped | CC1.1 CC1.4 | A.6.1 | 5 | 3 | 1 | 2 | 0 | 3+2 | 1+1 | 1 | 83% | 0% |
| HR-02 | Confidentiality / IP agreements | shipped | C1.1 CC1.1 | A.5.32 A.6.2 A.6.5 A.6.6 A.8.30 | 5 to 6 | 5 | 1 | 2 | 0 | 4+2 | 3+2 | 1 | 75% | 0% |
| HR-03 | Contractor lifecycle management | shipped | CC6.2 CC9.2 | A.5.11 A.8.30 | 5 | 6 | 2 | 2 | 0 | 3+3 | 2+4 | 1 | 90% | 0% |
| HR-04 | Job descriptions with security responsibilities | shipped | CC1.4 | 7.2 A.6.2 | 4 | 4 | 1 | 0 | 0 | 1+1 | 3+2 | 2 | 100% | 20% |
| HR-05 | Offboarding and deprovisioning | shipped | CC6.2 CC6.3 | A.5.11 A.6.5 | 5 to 6 | 4 | 0 | 1 | 0 | 2+1 | 1+3 | 2 | 100% | 0% |
| HR-06 | Onboarding checklist | shipped | CC1.4 CC6.2 | A.5.4 | 5 | 6 | 1 | 1 | 0 | 3+2 | 2+4 | 2 | 100% | 0% |
| HR-07 | Performance management | shipped | CC1.4 CC1.5 |  | 4 | 3 | 1 | 1 | 0 | 0+2 | 1+2 | 1 | 80% | 0% |
| HR-08 | Security awareness training | shipped | CC1.4 CC2.2 | 7.2 7.3 A.5.17 A.6.3 A.8.7 | 4 to 5 | 3 | 0 | 1 | 0 | 2+2 | 2+2 | 1 | 100% | 0% |
| HR-09 | Competence of people in security roles | shipped |  | 7.2 | 4 | 6 | 0 | 1 | 0 | 0+1 | 4+4 | 2 | 86% | 14% |
| IAM-01 | Access provisioning approval | shipped | CC6.2 CC6.3 | A.5.15 A.5.16 A.5.18 A.8.34 | 5 to 6 | 3 | 3 | 2 | 0 | 6+2 | 1+3 | 1 | 88% | 0% |
| IAM-02 | Periodic user access reviews | shipped | CC6.2 CC6.3 | A.5.18 A.8.4 | 5 | 5 | 2 | 0 | 0 | 3+1 | 3+1 | 1 | 100% | 0% |
| IAM-03 | Enforce multi-factor authentication | shipped | CC6.1 | A.8.5 | 5 to 6 | 4 | 3 | 0 | 0 | 7+1 | 2+3 | 1 | 100% | 0% |
| IAM-04 | Enforce single sign-on | shipped | CC6.1 | A.8.5 | 4 | 4 | 1 | 0 | 0 | 2+0 | 2+2 | 2 | 100% | 0% |
| IAM-05 | Company password manager | shipped | CC6.1 | A.5.17 | 4 | 3 | 1 | 2 | 0 | 2+2 | 1+1 | 2 | 100% | 0% |
| IAM-06 | Password policy | shipped | CC6.1 | A.5.17 A.8.5 | 4 to 5 | 2 | 1 | 0 | 0 | 1+0 | 1+1 | 1 | 100% | 33% |
| IAM-07 | Privileged access management | shipped | CC6.3 | A.8.18 A.8.2 | 5 to 6 | 6 | 3 | 0 | 0 | 5+1 | 3+2 | 1 | 100% | 0% |
| IAM-08 | Role-based access and least privilege | shipped | CC5.2 CC6.1 CC6.3 | A.5.15 A.8.3 A.8.4 | 4 | 3 | 2 | 0 | 0 | 4+0 | 2+2 | 1 | 100% | 0% |
| IAM-09 | Segregation of duties | shipped | CC5.1 CC6.3 | A.5.3 | 4 | 3 | 1 | 0 | 0 | 4+0 | 1+2 | 1 | 100% | 0% |
| IAM-10 | Service and machine account governance | shipped | CC6.1 CC6.3 | A.5.16 A.8.3 | 5 | 2 | 4 | 0 | 0 | 4+1 | 1+2 | 2 | 100% | 0% |
| IAM-11 | Session timeout and management | shipped | CC6.1 | A.8.5 | 4 | 3 | 2 | 0 | 0 | 2+0 | 1+2 | 2 | 100% | 0% |
| IAM-12 | Timely access removal | shipped | CC6.2 CC6.3 | A.5.16 A.5.18 | 5 | 3 | 2 | 3 | 0 | 4+2 | 1+3 | 2 | 100% | 0% |
| IAM-13 | Segregation of duties in finance and payment processes | proposed (from IAM-09) | CC5.1 | A.5.3 | 4 | 2 | 0 | 1 | 0 | 1+0 | 1+1 | 1 | 100% | 0% |
| IAM-14 | Product sign in protections for customer users | proposed (new) | CC6.1 | A.5.17 A.8.5 | 4 | 2 | 0 | 0 | 2 | 1+0 | 3+0 | 1 | 75% | 0% |
| LM-01 | Asset and system inventory | shipped | CC2.1 CC6.1 | A.5.9 | 4 | 4 | 0 | 0 | 0 | 2+0 | 4+1 | 1 | 100% | 0% |
| LM-02 | Centralized logging and retention | shipped | CC2.1 CC7.2 | A.5.28 A.8.15 | 4 to 6 | 6 | 1 | 0 | 0 | 3+2 | 2+1 | 2 | 100% | 0% |
| LM-03 | Configuration-change detection | shipped | CC7.1 | A.8.20 A.8.9 | 4 | 3 | 0 | 0 | 0 | 4+0 | 2+0 | 2 | 100% | 0% |
| LM-04 | Security event evaluation | shipped | CC7.3 | A.5.25 A.8.16 | 4 | 4 | 0 | 0 | 0 | 2+1 | 1+1 | 1 | 100% | 0% |
| LM-05 | Incident postmortems with actions | shipped | CC7.4 CC7.5 | 10.2 A.5.26 A.5.27 | 4 to 5 | 5 | 0 | 0 | 0 | 2+2 | 2+3 | 2 | 100% | 0% |
| LM-06 | Incident recovery procedures | shipped | CC7.5 | A.5.26 | 4 | 5 | 0 | 0 | 0 | 1+1 | 1+1 | 3 | 100% | 0% |
| LM-07 | Incident response plan | shipped | CC7.4 P6.5 | A.5.24 A.5.26 A.5.28 | 5 to 7 | 7 | 0 | 0 | 0 | 1+1 | 2+1 | 1 | 86% | 0% |
| LM-08 | On-call rotation | shipped | CC7.2 CC7.4 |  | 4 | 2 | 1 | 0 | 0 | 2+2 | 1+0 | 1 | 100% | 0% |
| LM-09 | Security anomaly alerting | shipped | CC7.2 | A.8.16 | 4 | 3 | 0 | 0 | 0 | 2+0 | 1+1 | 1 | 100% | 0% |
| LM-10 | Incident tabletop exercise | shipped | CC7.4 | A.5.24 | 4 | 4 | 0 | 0 | 0 | 1+0 | 2+2 | 1 | 100% | 0% |
| LM-11 | Vulnerability management program | shipped | CC7.1 | A.8.8 | 5 to 4 | 5 | 0 | 0 | 0 | 1+0 | 2+2 | 1 | 60% | 0% |
| LM-12 | Threat source monitoring | shipped |  | A.5.7 | 5 | 7 | 0 | 0 | 0 | 0+0 | 5+4 | 1 | 100% | 0% |
| LM-13 | Vulnerability scanning coverage | proposed (from LM-11) | CC7.1 | A.8.8 | 3 | 5 | 0 | 0 | 0 | 2+0 | 2+1 | 1 | 100% | 0% |
| NS-01 | Encryption at rest | shipped | CC6.1 | A.8.24 | 4 | 3 | 2 | 0 | 0 | 2+0 | 2+0 | 2 | 100% | 20% |
| NS-02 | Encryption in transit (TLS) | shipped | CC6.7 | A.5.14 A.8.21 A.8.24 | 5 | 4 | 2 | 0 | 0 | 3+1 | 2+0 | 2 | 100% | 0% |
| NS-03 | Default-deny firewall rules | shipped | CC6.6 | A.8.20 | 4 to 6 | 3 | 1 | 0 | 0 | 3+0 | 2+1 | 1 | 100% | 0% |
| NS-04 | Hardening baselines (CIS) | shipped | CC5.2 CC6.1 CC7.1 | A.5.23 A.8.18 A.8.19 A.8.20 A.8.9 | 5 | 6 | 1 | 0 | 0 | 4+0 | 3+1 | 2 | 100% | 0% |
| NS-05 | Infrastructure threat detection | shipped | CC6.8 CC7.2 | A.8.16 | 5 | 4 | 3 | 0 | 0 | 5+1 | 3+1 | 2 | 100% | 0% |
| NS-06 | Encryption key management | shipped | CC6.1 | A.8.24 | 5 | 3 | 2 | 0 | 0 | 2+0 | 1+1 | 2 | 100% | 0% |
| NS-07 | Network segmentation | shipped | CC6.1 CC6.6 | A.8.20 A.8.22 | 4 | 3 | 1 | 0 | 1 | 1+0 | 2+1 | 1 | 100% | 0% |
| NS-08 | No management ports exposed to the internet | shipped | CC6.6 | A.8.20 | 4 | 2 | 3 | 0 | 0 | 5+2 | 2+1 | 1 | 100% | 20% |
| NS-09 | Secrets management | shipped | CC6.1 | A.5.17 | 4 | 3 | 2 | 0 | 0 | 2+2 | 1+0 | 2 | 80% | 0% |
| NS-10 | WAF and DDoS protection | shipped | CC6.6 | A.8.21 | 4 | 1 | 2 | 0 | 0 | 2+1 | 2+1 | 1 | 100% | 0% |
| NS-11 | VPN / zero-trust remote access | shipped | CC6.6 | A.6.7 A.8.21 | 4 to 5 | 4 | 1 | 1 | 0 | 3+3 | 1+1 | 2 | 100% | 0% |
| NS-12 | Time synchronization | shipped |  | A.8.17 | 4 | 5 | 1 | 0 | 0 | 1+0 | 2+1 | 2 | 100% | 0% |
| NS-13 | Server and container image patching | proposed (from EP-04) | CC6.8 CC7.1 | A.8.8 | 6 | 4 | 2 | 0 | 0 | 3+0 | 3+1 | 3 | 100% | 0% |
| NS-14 | Network equipment hardening and firmware | proposed (from NS-04) |  | A.8.20 A.8.9 | 4 | 4 | 0 | 0 | 2 | 0+0 | 2+2 | 2 | 100% | 0% |
| PE-01 | Cloud physical security (provider assurance review) | shipped | A1.2 CC6.4 CC9.2 | A.5.23 A.7.1 A.7.11 A.7.12 A.7.13 A.7.14 A.7.2 A.7.3 A.7.4 A.7.5 A.7.6 A.7.8 | 5 | 6 | 0 | 0 | 0 | 1+0 | 3+1 | 2 | 100% | 17% |
| PE-02 | Office physical access controls | shipped | CC6.4 | A.5.15 A.7.1 A.7.2 A.7.3 A.7.4 A.7.6 A.7.7 | 5 | 5 | 0 | 1 | 1 | 1+1 | 1+1 | 1 | 86% | 0% |
| PE-03 | Environmental and equipment protection at own sites | shipped |  | A.7.11 A.7.12 A.7.13 A.7.5 A.7.8 | 5 | 4 | 0 | 0 | 1 | 0+0 | 1+1 | 1 | 80% | 0% |
| SD-01 | Change authorization and approval | shipped | CC5.2 CC8.1 | A.8.19 A.8.32 | 5 | 6 | 1 | 0 | 0 | 6+1 | 2+1 | 1 | 100% | 0% |
| SD-02 | Automated testing in CI | shipped | CC8.1 PI1.3 | A.8.25 A.8.29 A.8.32 | 5 to 6 | 7 | 0 | 0 | 0 | 5+0 | 2+1 | 2 | 100% | 29% |
| SD-03 | Dependency and image scanning | shipped | CC6.8 CC7.1 | A.5.21 A.5.32 A.8.28 A.8.29 A.8.8 | 5 | 6 | 1 | 0 | 0 | 4+1 | 3+4 | 2 | 100% | 0% |
| SD-04 | Emergency change procedure | shipped | CC8.1 | A.8.32 | 5 | 5 | 0 | 0 | 0 | 1+2 | 2+1 | 1 | 100% | 0% |
| SD-05 | Input validation controls | shipped | PI1.2 | A.8.26 A.8.28 | 4 to 3 | 7 | 0 | 0 | 0 | 1+0 | 2+2 | 2 | 86% | 0% |
| SD-06 | Peer code review (branch protection) | shipped | CC8.1 | A.5.3 A.8.25 A.8.28 A.8.30 A.8.32 A.8.4 | 5 | 7 | 0 | 0 | 0 | 4+1 | 1+0 | 2 | 86% | 29% |
| SD-07 | Pipeline storage integrity | shipped | PI1.5 |  | 5 | 5 | 1 | 0 | 0 | 4+0 | 2+0 | 2 | 100% | 0% |
| SD-08 | Processing reconciliation and monitoring | shipped | PI1.3 PI1.4 |  | 4 | 4 | 0 | 0 | 0 | 2+0 | 2+0 | 1 | 100% | 0% |
| SD-09 | Processing specifications | shipped | PI1.1 |  | 4 | 4 | 1 | 0 | 0 | 3+0 | 2+0 | 1 | 100% | 0% |
| SD-10 | Secure SDLC policy | shipped | CC8.1 | A.5.37 A.5.8 A.8.25 A.8.26 A.8.27 A.8.28 A.8.29 | 5 to 6 | 7 | 0 | 0 | 1 | 1+0 | 3+0 | 1 | 75% | 0% |
| SD-11 | Secret scanning | shipped | CC6.1 CC7.1 | A.5.17 A.8.28 | 5 | 5 | 1 | 0 | 0 | 3+4 | 1+1 | 2 | 83% | 0% |
| SD-12 | Separate dev/staging/production | shipped | CC8.1 | A.8.31 | 5 | 2 | 4 | 0 | 0 | 5+0 | 1+0 | 1 | 100% | 17% |
| SD-13 | Controlled production deployments | shipped | CC8.1 | A.8.19 A.8.32 | 5 | 5 | 2 | 0 | 0 | 6+1 | 1+0 | 2 | 100% | 14% |
| SD-14 | Change traceability | shipped | CC8.1 | A.8.32 | 5 | 5 | 0 | 0 | 0 | 4+0 | 2+1 | 2 | 100% | 0% |
| SD-15 | Processing error handling and correction | proposed (new) | PI1.2 PI1.3 |  | 4 | 4 | 0 | 0 | 0 | 1+1 | 2+1 | 1 | 100% | 0% |
| SD-16 | Output delivery and review | proposed (new) | PI1.4 |  | 3 | 3 | 1 | 0 | 0 | 2+1 | 2+1 | 1 | 100% | 0% |
| SD-17 | Direct changes to production data | proposed (new) | CC8.1 | A.8.32 | 3 | 3 | 1 | 0 | 0 | 4+1 | 1+2 | 1 | 100% | 0% |
| SD-18 | Software component list and licence review | proposed (from SD-03) |  | A.5.21 A.5.32 | 3 | 3 | 0 | 0 | 0 | 0+0 | 1+1 | 1 | 67% | 0% |

Controls with no artifact row in the coverage files: none.
