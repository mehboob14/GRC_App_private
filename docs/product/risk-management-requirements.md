# Risk management requirements

A working addendum to the signed specification. The signed documents stay untouched; this file
records how their risk requirements are read and what later phases add, so each phase starts from
an agreed reading. Where it extends the signed scope it says so, and those items are agreed before
work starts (delivery plan: "anything not listed in a phase is scoped separately").

Sources: signed specification (Deliverable 1.2 risk register, 1.3 linkage, 3.1 ERM), ER 3.6 and
3.12, the GRC-Tenant ERM module, Vanta Risk, Drata Risk Management.

## Phase 1: risk register (Deliverable 1.2, built in week 7)

Build reference: `openspec/changes/week7-risk-register/`.

| ID | Requirement | Acceptance |
|---|---|---|
| RR-1 | A workspace keeps several risk registers, each with its own type, matrix, bands, taxonomy and review cadence. | Two registers with different matrix sizes score independently. |
| RR-2 | The likelihood by impact matrix is configurable per register (3 to 6 levels each, labels and descriptions per level, severity bands on the score). | Shrinking below a stored score is refused. |
| RR-3 | A risk records title, description, category and subcategory, status, business owner, business unit, inherent and residual likelihood and impact, root cause, consequences, recommendations, treatment decision, treatment plan and due date, next review date. | Every field round trips through the form, the API, import and export. |
| RR-4 | Subcategories follow the chosen category, on the form and in the import template. | Picking a category narrows the subcategory list. |
| RR-5 | Controls link to risks; a risk with no linked control is flagged. | The flag is computed and clears when a control is linked. |
| RR-6 | Assets, vulnerabilities, evidence, tasks and issues, vendors and documents link to risks. | Links show on both the risk and, where built, the other record. |
| RR-7 | Treatment is mitigate, accept, avoid or transfer; treatment actions are tracked tasks. | An action appears in Tasks with its SLA. |
| RR-8 | Formal acceptance with approver, rationale and expiry; the requester cannot approve; expiry reopens the risk. | The daily job reopens an expired acceptance and notifies the owner. |
| RR-9 | Scheduled reviews with a cadence; overdue reviews are visible and notified. | Mark reviewed moves the next date by the cadence. |
| RR-10 | A starter risk library; adoption copies text and links suggested controls. | Library updates never change adopted risks. |
| RR-11 | Heatmap and treatment status export. | Excel export holds the register, both heatmaps and treatment status. |
| RR-12 | Import from CSV or Excel with a downloadable template and a validating preview. | Invalid rows are reported and skipped; nothing is written by the preview. |
| RR-13 | AI assist drafts narrative, category and scores from a title. | Drafts are never saved without a person applying and saving them. |
| RR-14 | Vendor findings can be promoted into the register. | The finding shows its risk; the risk links the vendor. |
| RR-15 | Every change is in the risk history and the audit trail. | Each state change writes both in one transaction. |

## Phase 2: automation around the register (Deliverables 2.1 and 2.2)

| ID | Requirement | Notes |
|---|---|---|
| RR-20 | Multi step approval workflows for acceptance, closure and material score changes: sequential or parallel steps, assignee by person, group or role, escalation on timeout. | Uses the Phase 2 workflow engine (ER 3.12 WORKFLOW_DEFINITIONS, STEPS, INSTANCES). Replaces the single approver of RR-8 without losing history. |
| RR-21 | Continuous control monitoring on a risk: when a linked control starts failing, the risk shows it, the owner is alerted, and residual scoring is flagged for review. | Uses 2.2 monitoring findings. Never changes a score automatically. |
| RR-22 | Jira and Slack: treatment actions sync two way; acceptance requests and expiries post to a channel. | Uses 2.2 integrations. |
| RR-23 | Vulnerability and asset signals: a new critical vulnerability on an asset linked to a risk raises a review prompt on that risk. | Builds on the 1.3 trace. |

## Phase 3: enterprise risk management (Deliverable 3.1)

| ID | Requirement | Data design |
|---|---|---|
| ERM-1 | **Risk and control self assessment (RCSA).** Campaigns by period send control owners assessments of design and operating effectiveness, optionally against a risk; results roll up by business unit. | RCSA_CAMPAIGNS, RCSA_ASSESSMENTS |
| ERM-2 | **Risk assessments.** A structured assessment per scope following ISO 31000 stages (scope, identify, analyse, evaluate, treat) with sign off; risks identified inside it land in a register. | RISK_ASSESSMENTS |
| ERM-3 | **Framework assessments.** Maturity per requirement with gap notes for ISO 27001, HIPAA, GDPR on the shared control engine. | FRAMEWORK_ASSESSMENTS, RESULTS |
| ERM-4 | **Incidents.** Record, classify by severity, keep a timeline, link to risks and controls; an incident on a risk prompts a rescore. | INCIDENTS, INCIDENT_EVENTS |
| ERM-5 | **Key risk indicators.** Named measures with thresholds and direction, periodic measurements, alert on breach, trend on the risk. | KRIS, KRI_MEASUREMENTS |
| ERM-6 | **Risk appetite and tolerance.** Per category appetite and tolerance thresholds; risks above appetite are flagged, above tolerance escalate to a named owner. | RISK_APPETITE |
| ERM-7 | **AI mitigation plans.** Draft treatment plans and actions from the risk, its controls and its incidents; drafts go through the normal approval. | Rule 11 |
| ERM-8 | **Configurable workflows** for risk, incident, document and vendor objects. | WORKFLOW_* (shared with RR-20) |

## Parity backlog (agreed separately before scheduling)

Benchmarked against Vanta and Drata. Shown in the product as Soon so the direction is visible.

| ID | Requirement |
|---|---|
| RB-1 | Custom fields per register (text, number, date, select, person) available on the form, filters, import and export. |
| RB-2 | Custom scoring formulas per register (weighted, additive, maximum), with a preview on existing risks before saving. |
| RB-3 | Register snapshots: a point in time copy of every risk and score, compared side by side. |
| RB-4 | Reports: board pack PDF with heatmaps, movements since the last snapshot, top risks, acceptances and overdue items. |
| RB-5 | Register level permissions: who can read or manage each register. |
| RB-6 | Risk quantification: loss magnitude and frequency ranges producing annualised loss exposure (FAIR style). |
| RB-7 | Risk to risk links (causes, aggregates) and a linkage graph from vulnerability to policy. |
| RB-8 | A larger library (Drata ships 200+), tagged by framework and industry, with bulk adoption rules. |
| RB-9 | Score history chart on a risk from `risk_events` snapshots. |
| RB-10 | Natural language questions over the register ("which high risks have no owner"). |
