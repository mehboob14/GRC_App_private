# Delivery plan

Three phases, seven deliverables. Each ends with a demonstration against written exit criteria, so
acceptance is observable rather than subjective.

**Build the phase you are in. Design the schema for all three.** Tables for later phases are
designed now so nothing built earlier has to change. Do not implement Phase 2 or 3 features during
Phase 1.

## Phase 1 — Core platform (3 deliverables)

Everything working end to end on manually managed data. No external connectors; the integrations
area shows placeholders.

- **1.1** Foundation, controls, evidence, dashboards, tasks. Multi-tenancy with proven isolation,
  RBAC with groups and granular permissions, platform-wide audit trail, SOC 2 control library with
  Type and Sub-type, manual evidence with validity and staleness, readiness dashboards, task
  management with SLAs and immutable history.
- **1.2** Documents and policies (templates, versions, acknowledgement campaigns), risk register
  (configurable matrix, starter library, acceptance with expiry), third-party vendor risk (full
  TPRM lifecycle).
- **1.3** Asset management, vulnerability management, and the 360-degree linkage.

**Exit criteria.** A new workspace goes end to end. Cross-tenant access fails, proven by automated
test. A task, policy, risk, vendor, asset, and vulnerability each go end to end, and the four-hop
trace is demonstrated with every step in the audit trail. Deployment from documented steps, with
versioned migrations and a demonstrated backup and restore.

## Phase 2 — Connectors, monitoring, automation (2 deliverables)

- **2.1** Connector framework and the first fifteen connectors.
- **2.2** Continuous monitoring, findings and alerting, approval workflows, AI document drafting,
  Jira two-way sync and Slack alerts.

**Exit criteria.** A workspace connects AWS and a source-control provider and reaches a populated
posture view from real collected evidence. A control moved to failing raises alerts, opens a
finding, and auto-resolves when it passes. AI drafts a policy, procedure, guideline, and standard,
each taken through review, approval, and staff acknowledgement.

## Phase 3 — ERM and remaining connectors (2 deliverables)

- **3.1** Enterprise risk management (RCSA, risk and framework assessments, incidents, KRIs, risk
  appetite, AI mitigation, configurable workflows) and additional frameworks (ISO 27001, HIPAA,
  GDPR) on the same control engine.
- **3.2** Remaining connectors, live scanner integrations, CIS hardening benchmarks, SSO, access
  reviews in full, read-only auditor access.

## Out of scope

Automated answering of inbound security questionnaires, built-in training courseware, endpoint or
device agent, SOC 1 and SOC 3 reporting, on-premises appliance packaging. Anything not listed in a
phase is scoped separately and agreed before any work starts.
