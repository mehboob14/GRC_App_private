# Operations checks: shared definitions and feasibility

Shared by [jira.md](jira.md), [slack.md](slack.md), [pagerduty.md](pagerduty.md),
[datadog.md](datadog.md), [sentry.md](sentry.md), [cloudflare.md](cloudflare.md) and
[tailscale.md](tailscale.md). This file owns the check prefixes `tickets.`, `alerts.`, `observability.`
and `edge.` (AUTHORING section 3). It holds what does not change between providers: the feasibility
matrix, content corrections to existing checks, the full definitions of the new checks, the artifacts
they fill, needs handed to other prefixes, the framework reach and the owner decisions. Each connector
document holds the provider API, population and predicate for its provider, with sources.

Researched 2026-11-23. Nothing here edits content JSON (AUTHORING rule 8). The definitions in section 3
are proposals for the reconciliation step, in the shape of `seed/content/automation/checks.json`.

## 1. Feasibility matrix

S supported, P partial (why: see the connector document), N not possible, n/a not about this provider.

| Check | Jira | Slack | PagerDuty | Datadog | Sentry | Cloudflare | Tailscale |
|---|---|---|---|---|---|---|---|
| `tickets.changes_linked` | P (ticket side; PR side from version control) | n/a | n/a | n/a | n/a | n/a | n/a |
| `tickets.access_requests_approved` | P (approval side; grant side from the identity provider) | n/a | n/a | n/a | n/a | n/a | n/a |
| `tickets.remediation_tracked` | S (needs a mapping of finding tickets) | n/a | n/a | n/a | n/a | n/a | n/a |
| `alerts.security_routed` | n/a | N | S | n/a | n/a | n/a | n/a |
| `alerts.acknowledged_in_time` | n/a | N | S | n/a | n/a | n/a | n/a |
| `alerts.incidents_resolved` | n/a | N | P (owner and timeline, not the recovery steps) | n/a | n/a | n/a | n/a |
| `observability.logs_retained` | n/a | n/a | n/a | P (archive bucket retention not visible) | n/a (errors are not logs) | n/a | n/a |
| `observability.anomaly_monitors` | n/a | n/a | n/a | S (needs a category mapping) | P (error spikes only) | n/a | n/a |
| `observability.processing_monitored` | n/a | n/a | n/a | P (needs the list of jobs) | P (error alerts; cron monitors readable with `org:read`, and a missed run opens an issue that still needs an alert: see sentry.md) | n/a | n/a |
| `observability.capacity_trends` | n/a | n/a | n/a | S | n/a | n/a | n/a |
| `edge.waf_enabled` | n/a | n/a | n/a | n/a | n/a | S (Free plan: Free Managed Ruleset only) | n/a |
| `edge.zero_trust_access` | n/a | n/a | n/a | n/a | n/a | P (cannot see other paths) | P (cannot see other paths) |
| `edge.minimum_tls` | n/a | n/a | n/a | n/a | n/a | S | n/a (WireGuard, not TLS) |
| NEW `tickets.changes_approved_before_release` | S (needs a status mapping) | | | | | | |
| NEW `tickets.emergency_changes_reviewed` | S (needs an emergency marker) | | | | | | |
| NEW `tickets.access_approver_independent` | S (JSM approvals or an approver field) | | | | | | |
| NEW `tickets.security_reports_answered` | S (JSM SLA), P (Jira without SLAs) | | | | | | |
| NEW `tickets.incidents_registered` | S (with the Verity register) | | | | | | |
| NEW `alerts.on_call_covered` | | N | S | | | | |
| NEW `alerts.escalation_policies_escalate` | | N | S | | | | |
| NEW `alerts.incidents_registered` | | N | S (with the Verity register) | | | | |
| NEW `alerts.postmortems_completed` | | N | P (Professional plan and above, and only if reviews live there) | | | | |
| NEW `observability.monitors_notify_on_call` | | | | S | S | | |
| NEW `observability.production_services_monitored` | | | | S (APM or catalog tags needed) | S | | |
| NEW `observability.silent_sources_alert` | | | | S (needs the list of sources) | n/a | | |
| NEW `observability.siem_rules_enabled` | | | | S (Cloud SIEM product) | n/a | | |
| NEW `observability.security_signals_triaged` | | | | S (Cloud SIEM product) | n/a | | |
| NEW `observability.audit_trail_enabled` | | | | P (inferred, see datadog.md) | N (audit log API needs a write scope) | | |
| NEW `observability.errors_triaged_in_time` | | | | n/a | S | | |
| NEW `edge.hsts_enabled` | | | | | | S | n/a |
| NEW `edge.origin_tls_verified` | | | | | | S | n/a |
| NEW `edge.dnssec_enabled` | | | | | | S | n/a |
| NEW `edge.origin_locked` | | | | | | P (origin side not visible) | n/a |
| NEW `edge.access_policies_least_privilege` | | | | | | S | S |
| NEW `edge.devices_verified` | | | | | | P (the Device Posture Read group exists, but the posture endpoint page names no accepted permission, so the connect test probes it: see cloudflare.md) | S |
| NEW `edge.device_keys_expire` | | | | | | n/a | S |
| NEW `edge.members_current` | | | | | | n/a | S (needs a connected identity provider) |
| NEW `edge.policy_tests_defined` | | | | | | n/a | S |

Slack implements none of the checks above. Section 2 explains why.

## 2. Content corrections proposed for existing checks

| Item | Today | Proposal | Why |
|---|---|---|---|
| Slack as an `alerting` provider (`capabilities.json`) | Listed with PagerDuty | Remove Slack from `alerting`. Keep it as the notification channel (not a capability), and optionally under business applications for its own member list | Slack has no on call schedule, escalation or acknowledgement. A message in a channel is not a page (see [slack.md](slack.md) section 1) |
| `tickets.access_requests_approved` to IAM-01 | full | partial | It does not show that privileged grants were approved by the system owner (IAM-01.D), that each person has their own account (IAM-01.E), or that every system's grants were seen (IAM-01.B needs every in scope system connected) |
| `edge.zero_trust_access` to NS-11 | full | partial | An edge or tailnet can show a system sits behind it. It cannot show there is no other route in (cloud ingress, a public IP). NS-11.C (members match staff) and NS-11.D (sessions logged and reviewed) also remain |
| `edge.waf_enabled` to NS-10 | full | partial | NS-10.C (origin refuses traffic that bypasses the firewall) and NS-10.D (quarterly rule review) are not shown by the firewall settings |
| `edge.waf_enabled` to SD-05 | partial | keep, reword rationale | Fine as partial. Reword: "Blocks some malformed requests at the edge. Validation inside the application is tested separately." |
| `alerts.acknowledged_in_time` | LM-04 only | add LM-08 (partial) | Unacknowledged high urgency pages are the missed pages LM-08.D asks to track. Rationale: "Lists high urgency pages that were not acknowledged in time. Reviewing them and fixing cover stay with people." |
| `tickets.remediation_tracked` | GOV-08 only | add LM-05 (partial), with postmortem actions in its population | LM-05.C asks for corrective actions tracked to closure. Where they live in Jira, this check is the evidence. Rationale: "Shows postmortem actions tracked in tickets closed by their due date. Whether the actions fix the cause is reviewed by people." |
| LM-02.C has no settings artifact | Only `logging-and-retention-standard` (a document) and an interview | Add an artifact `log-retention-settings` (configuration, sources: check `observability.logs_retained`, `cloud.audit_logging`; person) to LM-02.C | Without it, `observability.logs_retained` fills no artifact and cannot move any objective |
| `edge.minimum_tls` implementations | Capability `network_edge` lists Tailscale | Implement on Cloudflare only | Tailscale traffic is WireGuard, so a TLS version setting does not exist there |

## 3. New check definitions

Each definition below uses the `checks.json` fields. `implementations` lists providers this round
proposes; the reconciliation step adds them when a collector ships. Population, predicate, period and
the four outcomes per provider are in the connector documents (section 5 of each).

Every check here follows the shared outcome rules: a missing permission or unreachable API is `error`;
a population that could not be read in full (truncated paging, a plan that hides part of it, a mapping
the customer has not set) is insufficient information; an empty population is insufficient information
unless the provider can show the population really was empty.

Several checks need a **tenant mapping**: which Jira statuses mean approved or released, which
PagerDuty services carry security alerts, which Datadog tags mark production. The mapping is set on the
connection (section 9 of each connector document), is audited, and is printed on every result so an
auditor sees what the check judged against.

### 3.1 Ticketing (`tickets.`)

```json
[
  {
    "key": "tickets.changes_approved_before_release",
    "name": "Changes are approved before release",
    "description": "Every change ticket that reached its released status was approved first, by someone other than its requester and its implementer.",
    "capabilities": ["ticketing"],
    "implementations": ["jira"],
    "resource_type": "ticket",
    "frequency": "daily",
    "remediation": "Record the approval on the listed tickets, or raise each one released without approval as a finding.",
    "controls": [
      {"code": "SD-01", "coverage": "partial", "rationale": "Shows each ticketed change was approved before release by someone independent of it. It does not show that every production change had a ticket, which tickets.changes_linked checks against the merged code."},
      {"code": "IAM-09", "coverage": "partial", "rationale": "Shows nobody approved a change they requested or carried out, for changes tracked in tickets. Other conflicting duties need their own review."}
    ],
    "evidence_kinds": ["Change tickets with approval and release times", "Approval decisions and approvers"]
  },
  {
    "key": "tickets.emergency_changes_reviewed",
    "name": "Emergency changes are reviewed afterwards",
    "description": "Every change released through the emergency route was reviewed and approved by someone else within the set window after release.",
    "capabilities": ["ticketing"],
    "implementations": ["jira"],
    "resource_type": "ticket",
    "frequency": "daily",
    "remediation": "Hold the missing reviews now and record them on the listed tickets.",
    "controls": [
      {"code": "SD-04", "coverage": "partial", "rationale": "Shows each emergency change recorded in tickets had a review by another person within the window. Emergency changes made without a ticket are found by vcs.unreviewed_merges_recorded, and the authorization at the time stays with people."}
    ],
    "evidence_kinds": ["Emergency change tickets", "Retrospective approvals with their times"]
  },
  {
    "key": "tickets.access_approver_independent",
    "name": "Access approvals are independent",
    "description": "Every access request was approved by someone other than the requester and the person receiving the access, and each privileged request by an owner of the system.",
    "capabilities": ["ticketing"],
    "implementations": ["jira"],
    "resource_type": "ticket",
    "frequency": "daily",
    "remediation": "Have the system owner approve the listed requests, or remove the access granted on them.",
    "controls": [
      {"code": "IAM-01", "coverage": "partial", "rationale": "Shows no one approved their own access and that privileged requests were approved by a listed owner. That the grant matched the approved request is tickets.access_requests_approved."},
      {"code": "IAM-09", "coverage": "partial", "rationale": "Shows requesting and approving access sat with different people for tracked requests. Other conflicting duties need their own review."}
    ],
    "evidence_kinds": ["Access requests with requester, beneficiary and approvers", "System owner list used for privileged requests"]
  },
  {
    "key": "tickets.security_reports_answered",
    "name": "Security reports are answered in time",
    "description": "Every report received through the tracked security channel had a first response within the stated time and a recorded decision when it closed.",
    "capabilities": ["ticketing"],
    "implementations": ["jira"],
    "resource_type": "ticket",
    "frequency": "daily",
    "remediation": "Answer the listed reports and record the triage decision on each.",
    "controls": [
      {"code": "CS-03", "coverage": "partial", "rationale": "Shows reports that reached the tracker were answered within the stated time and closed with a decision. Reports sent anywhere else, and whether each incident reached the register, need other evidence."}
    ],
    "evidence_kinds": ["Security report tickets with first response times", "Resolution of each report"]
  },
  {
    "key": "tickets.incidents_registered",
    "name": "Ticketed incidents are in the register",
    "description": "Every security incident raised in the ticketing system appears in Verity's incident register, or has a recorded decision there that it was not an incident.",
    "capabilities": ["ticketing", "verity_tasks"],
    "implementations": ["jira"],
    "resource_type": "ticket",
    "frequency": "daily",
    "remediation": "Add the listed incidents to the register, or record why each is not a security incident.",
    "controls": [
      {"code": "LM-07", "coverage": "partial", "rationale": "Shows the incident register is complete against incidents raised in tickets. Severity, the notice decision and handling under the plan stay with people."},
      {"code": "LM-04", "coverage": "partial", "rationale": "Shows each possible incident raised in tickets got a recorded decision. Whether the decision was right is reviewed by people."}
    ],
    "evidence_kinds": ["Incident tickets in the period", "Matching register entries and triage decisions"]
  }
]
```

### 3.2 On call and alerting (`alerts.`)

```json
[
  {
    "key": "alerts.on_call_covered",
    "name": "Someone is on call at all times",
    "description": "For every in scope service, the first escalation level had someone on call for the whole period, with a second level behind it.",
    "capabilities": ["alerting"],
    "implementations": ["pagerduty"],
    "resource_type": "escalation_policy",
    "frequency": "daily",
    "remediation": "Fill the listed gaps in the schedule and add a backup level to the policy.",
    "controls": [
      {"code": "LM-08", "coverage": "partial", "rationale": "Shows someone, with a backup, was on call for every minute of the period on the in scope services. Contact details and whether cover meets customer commitments are reviewed by people."}
    ],
    "evidence_kinds": ["On call entries per escalation level", "Schedules and their coverage"]
  },
  {
    "key": "alerts.escalation_policies_escalate",
    "name": "Unanswered pages escalate",
    "description": "Every in scope service routes to an escalation policy that passes an unanswered page to another target within the set time.",
    "capabilities": ["alerting"],
    "implementations": ["pagerduty"],
    "resource_type": "escalation_policy",
    "frequency": "daily",
    "remediation": "Add a second level, or shorten the escalation delay, on the listed policies.",
    "controls": [
      {"code": "LM-08", "coverage": "partial", "rationale": "Shows the tool escalates an unanswered page to another person within the set time. Whether the settings match the approved escalation policy is a person's review."}
    ],
    "evidence_kinds": ["Escalation policies with levels, targets and delays", "Service to policy routing"]
  },
  {
    "key": "alerts.incidents_registered",
    "name": "Paged incidents are in the register",
    "description": "Every security or major incident in the on call tool appears in Verity's incident register, or has a recorded decision there that it was not a security incident.",
    "capabilities": ["alerting", "verity_tasks"],
    "implementations": ["pagerduty"],
    "resource_type": "incident",
    "frequency": "daily",
    "remediation": "Add the listed incidents to the register, or record why each is not a security incident.",
    "controls": [
      {"code": "LM-04", "coverage": "partial", "rationale": "Shows each paged security event got a recorded decision on whether it is an incident. Whether the decision was right is reviewed by people."},
      {"code": "LM-07", "coverage": "partial", "rationale": "Shows the incident register is complete against security incidents paged in the period. Severity, the notice decision and handling under the plan stay with people."}
    ],
    "evidence_kinds": ["Security and major incidents in the period", "Matching register entries and triage decisions"]
  },
  {
    "key": "alerts.postmortems_completed",
    "name": "Major incidents have a completed review",
    "description": "Every major or high priority incident resolved in the period has a completed post incident review within the set number of days.",
    "capabilities": ["alerting"],
    "implementations": ["pagerduty"],
    "resource_type": "incident",
    "frequency": "daily",
    "remediation": "Complete the review for the listed incidents.",
    "controls": [
      {"code": "LM-05", "coverage": "partial", "rationale": "Shows each major incident got a completed review in time. The content of the review, and its actions tracked to closure, are checked by people and the Tasks module."}
    ],
    "evidence_kinds": ["Major incidents", "Post incident reviews with status and completion time"]
  }
]
```

### 3.3 Observability (`observability.`)

```json
[
  {
    "key": "observability.monitors_notify_on_call",
    "name": "High priority alerts page someone",
    "description": "Every enabled high priority monitor or alert rule notifies an on call destination, not only email or chat.",
    "capabilities": ["observability"],
    "implementations": ["datadog", "sentry"],
    "resource_type": "monitor",
    "frequency": "daily",
    "remediation": "Add the paging tool as a destination on the listed monitors.",
    "controls": [
      {"code": "LM-08", "coverage": "partial", "rationale": "Shows high priority alerts are sent to the paging tool. Whether someone is on call there is alerts.on_call_covered."},
      {"code": "LM-09", "coverage": "partial", "rationale": "Shows each high priority alert has a destination that leads to a response. Tuning and removing unused alerts stay with people."}
    ],
    "evidence_kinds": ["Monitors and alert rules with their notification targets"]
  },
  {
    "key": "observability.production_services_monitored",
    "name": "Production services are monitored",
    "description": "Every production service known to the monitoring tool has at least one enabled alert that notifies someone.",
    "capabilities": ["observability"],
    "implementations": ["datadog", "sentry"],
    "resource_type": "service",
    "frequency": "daily",
    "remediation": "Add an alert for each listed service.",
    "controls": [
      {"code": "LM-09", "coverage": "partial", "rationale": "Shows no production service is left without an alert. Whether the alerts cover the priority conditions is reviewed by people."}
    ],
    "evidence_kinds": ["Production services", "Monitors matched to each service"]
  },
  {
    "key": "observability.silent_sources_alert",
    "name": "A silent log source raises an alert",
    "description": "Every in scope log source has an enabled alert that fires when the source stops sending.",
    "capabilities": ["observability"],
    "implementations": ["datadog"],
    "resource_type": "log_source",
    "frequency": "daily",
    "remediation": "Add a missing data alert for each listed source.",
    "controls": [
      {"code": "LM-02", "coverage": "partial", "rationale": "Shows a source that stops sending raises an alert. Whether every in scope system sends its logs is compared with the asset inventory by people."}
    ],
    "evidence_kinds": ["In scope log sources", "Missing data monitors per source"]
  },
  {
    "key": "observability.siem_rules_enabled",
    "name": "Detection rules are on and notify",
    "description": "Enabled detection rules cover each condition the alerting standard names, and every high or critical case notifies someone.",
    "capabilities": ["observability"],
    "implementations": ["datadog"],
    "resource_type": "detection_rule",
    "frequency": "daily",
    "remediation": "Turn on a rule for each listed condition and add a notification to its high and critical cases.",
    "controls": [
      {"code": "LM-09", "coverage": "partial", "rationale": "Shows enabled detection rules exist for each condition the alerting standard names and that serious cases notify someone. Tuning stays with people."},
      {"code": "LM-02", "coverage": "partial", "rationale": "Shows security events are reviewed continuously by rules, which LM-02.D accepts in place of a daily human review. The monthly review record stays with people."},
      {"code": "NS-05", "coverage": "partial", "rationale": "Where the cloud audit trail feeds the rules, shows control plane misuse is detected. Turning on the provider's own detection service is cloud.threat_detection."}
    ],
    "evidence_kinds": ["Detection rules with state, cases and notifications", "Mapping of rules to the conditions in the alerting standard"]
  },
  {
    "key": "observability.security_signals_triaged",
    "name": "Security signals are triaged in time",
    "description": "Every high or critical security signal was taken up by a named person within the response time, and every closed signal carries a reason.",
    "capabilities": ["observability"],
    "implementations": ["datadog"],
    "resource_type": "signal",
    "frequency": "daily",
    "remediation": "Triage the listed signals and record a reason on each one closed.",
    "controls": [
      {"code": "LM-04", "coverage": "partial", "rationale": "Shows each serious security signal was looked at by a named person in time and closed with a reason. Whether it was an incident, and is in the register, stays with people."},
      {"code": "NS-05", "coverage": "partial", "rationale": "For threat detection findings that reach the SIEM, shows each was triaged within the response time. Findings that never reach the SIEM need their own evidence."}
    ],
    "evidence_kinds": ["Security signals with triage state, assignee and times"]
  },
  {
    "key": "observability.audit_trail_enabled",
    "name": "The monitoring tool records its own changes",
    "description": "The monitoring tool's audit trail is on, so changes to monitors, log retention and keys are recorded with who made them.",
    "capabilities": ["observability"],
    "implementations": ["datadog"],
    "resource_type": "organization",
    "frequency": "daily",
    "remediation": "Turn on the audit trail and keep its events for at least 90 days.",
    "controls": [
      {"code": "LM-02", "coverage": "partial", "rationale": "Shows changes to log retention, indexes and monitors are recorded with the person who made them. Who may delete logs is reviewed by people."}
    ],
    "evidence_kinds": ["Audit trail events by type and age"]
  },
  {
    "key": "observability.errors_triaged_in_time",
    "name": "Production errors are triaged in time",
    "description": "Every high priority error in production was assigned, resolved or archived within the triage time, and none stays unresolved past the fix time without an owner.",
    "capabilities": ["observability"],
    "implementations": ["sentry"],
    "resource_type": "issue",
    "frequency": "daily",
    "remediation": "Assign or resolve the listed errors.",
    "controls": [
      {"code": "SD-08", "coverage": "partial", "rationale": "Shows failures reported as production errors were picked up and handled within the target. Reconciling outputs with inputs is separate."}
    ],
    "evidence_kinds": ["Production issues with first seen, assignment and resolution times"]
  }
]
```

### 3.4 Network and edge (`edge.`)

```json
[
  {
    "key": "edge.hsts_enabled",
    "name": "Browsers must use HTTPS",
    "description": "Every public zone sends a strict transport security header with a long enough lifetime.",
    "capabilities": ["network_edge"],
    "implementations": ["cloudflare"],
    "resource_type": "zone",
    "frequency": "daily",
    "remediation": "Turn on HSTS for the zone with a lifetime of at least 180 days.",
    "controls": [
      {"code": "NS-02", "coverage": "partial", "rationale": "Shows browsers are told to refuse plain HTTP to the zone, which NS-02.C asks. Internal traffic is separate."}
    ],
    "evidence_kinds": ["HSTS settings per zone"]
  },
  {
    "key": "edge.origin_tls_verified",
    "name": "Traffic to the origin is verified",
    "description": "The edge connects to each origin over TLS and checks the origin's certificate.",
    "capabilities": ["network_edge"],
    "implementations": ["cloudflare"],
    "resource_type": "zone",
    "frequency": "daily",
    "remediation": "Install a trusted or origin certificate and set the zone's encryption mode to Full (strict).",
    "controls": [
      {"code": "NS-02", "coverage": "partial", "rationale": "Shows the hop from the edge to the origin is encrypted and the origin certificate is validated. Traffic between internal services and to databases needs its own evidence."}
    ],
    "evidence_kinds": ["Encryption mode per zone"]
  },
  {
    "key": "edge.dnssec_enabled",
    "name": "DNS answers are signed",
    "description": "Every zone whose DNS the edge serves has DNSSEC active.",
    "capabilities": ["network_edge"],
    "implementations": ["cloudflare"],
    "resource_type": "zone",
    "frequency": "daily",
    "remediation": "Turn on DNSSEC and add the DS record at the registrar.",
    "controls": [
      {"code": "NS-02", "coverage": "partial", "rationale": "Shows answers for the company's domains are signed, so a client is not sent to a forged endpoint. It supports the endpoint authentication NS-02 relies on; no objective asks for it by name."}
    ],
    "evidence_kinds": ["DNSSEC status per zone"]
  },
  {
    "key": "edge.origin_locked",
    "name": "Origins accept only edge traffic",
    "description": "Each proxied hostname reaches its origin through a tunnel, or the edge presents a client certificate that the origin can require.",
    "capabilities": ["network_edge"],
    "implementations": ["cloudflare"],
    "resource_type": "hostname",
    "frequency": "daily",
    "remediation": "Serve the listed hostnames through a tunnel, or turn on authenticated origin pulls and require the certificate at the origin.",
    "controls": [
      {"code": "NS-10", "coverage": "partial", "rationale": "Shows the edge is set up so the origin can refuse traffic that bypasses the firewall. That the origin does refuse it needs a cloud network check or a test."}
    ],
    "evidence_kinds": ["Tunnels and their hostnames", "Authenticated origin pull settings"]
  },
  {
    "key": "edge.access_policies_least_privilege",
    "name": "Access rules name groups, not everyone",
    "description": "No access rule lets everyone reach everything, and every rule that reaches production names a group, a tag or the company identity provider.",
    "capabilities": ["network_edge"],
    "implementations": ["cloudflare", "tailscale"],
    "resource_type": "policy",
    "frequency": "daily",
    "remediation": "Replace the listed rules with rules for named groups.",
    "controls": [
      {"code": "NS-11", "coverage": "partial", "rationale": "Shows access is granted per application or tag to named groups, which NS-11.D asks. Logging and review of sessions stay with people."},
      {"code": "IAM-08", "coverage": "partial", "rationale": "Shows network access to production is granted through groups. Whether group membership matches roles is idp.groups_drive_access and a person's review."}
    ],
    "evidence_kinds": ["Access policy or application policies", "Rules flagged as open to everyone"]
  },
  {
    "key": "edge.devices_verified",
    "name": "Only approved devices connect",
    "description": "New devices need approval before they can connect, and administrative applications require a device check.",
    "capabilities": ["network_edge"],
    "implementations": ["cloudflare", "tailscale"],
    "resource_type": "policy",
    "frequency": "daily",
    "remediation": "Turn on device approval, and add a device posture requirement to the listed applications.",
    "controls": [
      {"code": "NS-11", "coverage": "partial", "rationale": "Shows the remote access tool enforces the device rules the standard sets, which NS-11.B asks. The second factor at sign in is enforced in the identity provider (idp.mfa_enforced)."}
    ],
    "evidence_kinds": ["Device approval settings", "Device posture requirements per application"]
  },
  {
    "key": "edge.device_keys_expire",
    "name": "Device access expires",
    "description": "Device keys expire within the set number of days, and no person's device has expiry turned off.",
    "capabilities": ["network_edge"],
    "implementations": ["tailscale"],
    "resource_type": "device",
    "frequency": "daily",
    "remediation": "Shorten the key expiry, and turn expiry back on for the listed devices.",
    "controls": [
      {"code": "NS-11", "coverage": "partial", "rationale": "Shows each device must sign in again through the identity provider within the set time, so a lost device or a leaver loses access when the key expires."},
      {"code": "IAM-11", "coverage": "partial", "rationale": "Shows remote access sessions have a maximum length. Idle timeouts, and sessions in other systems, are separate."}
    ],
    "evidence_kinds": ["Key expiry setting", "Devices with expiry turned off"]
  },
  {
    "key": "edge.members_current",
    "name": "Remote access members are current staff",
    "description": "Every active member of the remote access tool is an active user in the identity provider.",
    "capabilities": ["network_edge", "identity_provider"],
    "implementations": ["tailscale"],
    "resource_type": "user",
    "frequency": "daily",
    "remediation": "Suspend or remove the listed members.",
    "controls": [
      {"code": "NS-11", "coverage": "partial", "rationale": "Shows only current staff hold remote access, which NS-11.C asks."},
      {"code": "IAM-12", "coverage": "partial", "rationale": "Shows leavers do not keep remote access. How fast it was removed is people.leavers_deprovisioned."}
    ],
    "evidence_kinds": ["Remote access members", "Identity provider status of each member"]
  },
  {
    "key": "edge.policy_tests_defined",
    "name": "The access policy tests its boundaries",
    "description": "The access policy holds tests that expect paths into production to be denied from sources that should not reach it, so a change that opens such a path is refused.",
    "capabilities": ["network_edge"],
    "implementations": ["tailscale"],
    "resource_type": "policy",
    "frequency": "daily",
    "remediation": "Add deny tests for each production tag to the policy.",
    "controls": [
      {"code": "NS-07", "coverage": "partial", "rationale": "Shows the network policy asserts blocked paths into production and every policy change is tested against them before it applies. Paths outside the tailnet need a cloud check or a penetration test."}
    ],
    "evidence_kinds": ["Policy tests and the production tags they protect"]
  }
]
```

## 4. Artifacts these checks fill

`today` is the source list in `artifacts.json`. Every artifact keeps its `person` source (evidence model
rule 1). `fills` follows evidence model rule 2: `full` only when the check collects the artifact itself
for the whole population.

| Artifact | Objectives | Today | Planned check sources (fills) |
|---|---|---|---|
| `change-requests-with-approval-for-a` | SD-01.B to E, GOV-03.B, GOV-03.C, SD-09.D, DM-18.B | check `tickets.changes_linked`, `vcs.merged_changes_reviewed`; person | + `tickets.changes_approved_before_release` (partial) |
| `change-records-linking-request-review-and` | SD-14.B to E | check `tickets.changes_linked`, `ci.deployment_history_recorded`; person | Jira implements `tickets.changes_linked` (partial) |
| `emergency-changes-with-their-after-the` | SD-04.B, C, D, EP-04.E | check `vcs.unreviewed_merges_recorded`; person | + `tickets.emergency_changes_reviewed` (partial) |
| `approved-requests-for-a-sample-of` | IAM-01.B to E, IAM-08.C, HR-01.B, C, HR-02.C, HR-03.C, HR-06.B, D | check `tickets.access_requests_approved`; person | Jira implements it (partial); + `tickets.access_approver_independent` (partial) |
| `log-of-control-deficiencies-with-owner` | GOV-08.B to E and 16 others | check `tickets.remediation_tracked`, `verity.tasks.remediation_in_sla` | Jira implements `tickets.remediation_tracked` (partial) |
| `corrective-actions-tracked-to-closure` | LM-05.C | person | + `tickets.remediation_tracked` (partial, with the LM-05 mapping of section 2) |
| `sample-of-reports-received-and-how` | CS-03.C, CS-03.D | person | + `tickets.security_reports_answered` (partial) |
| `security-incident-register` | LM-07.C, D, E, LM-04.C, LM-05.B, LM-06.B, CS-01.C, CS-03.D, NS-05.D, NS-09.D, SD-11.E, GOV-08.B and 6 others | person | + `tickets.incidents_registered`, `alerts.incidents_registered` (partial: completeness against the source, not the content) |
| `sample-of-evaluated-events-with-the` | LM-04.B, C, D | person | + `alerts.incidents_registered`, `observability.security_signals_triaged`, `alerts.acknowledged_in_time` (partial) |
| `on-call-schedule` | LM-08.B, C, D | person | + `alerts.on_call_covered` (full for LM-08.B: it is the schedule for the whole period), `alerts.acknowledged_in_time` (partial, LM-08.D) |
| `escalation-policy` | LM-08.A, LM-08.C | person | + `alerts.escalation_policies_escalate` (partial: the configuration, not the approval) |
| `recovery-records-for-incidents` | LM-06.B, C, D | check `alerts.incidents_resolved`; person | PagerDuty implements it (partial) |
| `postmortem-for-each-significant-incident` | LM-05.B, C, D | person | + `alerts.postmortems_completed` (partial) |
| `review-of-alert-tuning` | LM-09.B, C, D, NS-05.E | person | + `observability.anomaly_monitors`, `observability.monitors_notify_on_call`, `observability.production_services_monitored`, `observability.siem_rules_enabled`, `alerts.security_routed` (partial: the alert set, not the review) |
| `evidence-logs-are-reviewed` | LM-02.B, LM-02.D, NS-12.D | person | + `observability.silent_sources_alert` (partial, LM-02.B), `observability.siem_rules_enabled` (partial, LM-02.D) |
| `sample-of-alerts-that-were-investigated` | NS-05.C, D, E | person | + `observability.security_signals_triaged` (partial) |
| `capacity-review` | BC-04.B, C, D | person | + `observability.capacity_trends` (partial: alerts and thresholds, not the review) |
| `reconciliation-results-and-how-exceptions-were` | SD-08.B, C, D | person | + `observability.processing_monitored`, `observability.errors_triaged_in_time` (partial, SD-08.B only) |
| `public-endpoint-tls-scan` | NS-02.B, C, E | person | + `edge.minimum_tls`, `edge.hsts_enabled`, `edge.origin_tls_verified` (partial: edge settings, not a scan of every endpoint) |
| `review-of-web-application-firewall-rules` | NS-10.B, C, D | person | + `edge.waf_enabled`, `edge.origin_locked` (partial) |
| `remote-access-settings-and-members` | NS-11.B, C, D, NS-08.D | person | + `edge.zero_trust_access`, `edge.access_policies_least_privilege`, `edge.devices_verified`, `edge.device_keys_expire`, `edge.members_current` (partial each; together they are the settings and member list) |
| `segmentation-test-results` | NS-07.B, NS-07.D | person | + `edge.policy_tests_defined` (partial: tests inside the tailnet only) |
| `session-limit-settings-export` | IAM-11.B, C, D | person | + `edge.device_keys_expire` (partial, remote access only) |
| `log-retention-settings` (proposed, section 2) | LM-02.C | none yet | `observability.logs_retained` (partial), `cloud.audit_logging` (partial); person |

Objectives no connector here can ever prove: approval of a policy or procedure (LM-08.A, LM-09.A,
LM-07.A), the quality of a triage decision (LM-04.D), whether a review was carried out and acted on
(LM-09.D, NS-10.D, BC-04.B), the content of a postmortem (LM-05.D), whether a customer notice was
required and sent (CS-01.D), and the interviews.

## 5. Where these connectors add proof beyond Verity's own modules

Verity's Tasks module already holds remediation tasks and issues with SLAs and corrective actions
(`verity.tasks.remediation_in_sla`), and its incident register is a filtered view of Tasks (LM-07
evidence: "Tasks module, one task per incident"). A connector adds proof only where the work or the
signal does not start in Verity:

| What Verity's modules already show | What the connectors add |
|---|---|
| Remediation tasks raised in Verity are within SLA now | Findings tracked only in Jira, and tasks closed late (the Verity check judges open tasks only) |
| Incidents someone entered in the register | Completeness: incidents raised in Jira or paged in PagerDuty that never reached the register (`*.incidents_registered`) |
| The incident record a person wrote | Machine recorded times: when the page fired, who acknowledged, when it resolved, who was on call |
| Nothing about change approval | Approval before release and independence of the approver, from the tool where changes are approved |
| Nothing about access requests outside Verity | Approval records for access requests in JSM |
| Nothing about monitoring, edge or remote access | All of `observability.*` and `edge.*` |

Proposed (owner decision 3): incidents from Jira and PagerDuty are **synced** into the register as
`Integratable` task rows (`source`, `external_id`, `synced_at`, CLAUDE.md rule 9), landing as issues
awaiting a triage decision. A person decides "incident" or "not an incident", and that decision is the
LM-04.B record. The `*.incidents_registered` checks then evaluate the reconciliation.

## 6. Needs handed to other prefixes

Written as AUTHORING section 3 asks, for the reconciliation step.

| Need | Raised by | For |
|---|---|---|
| NEED identity_provider: the identity provider behind the remote access tool requires a second factor for every member (reuse `idp.mfa_enforced`, joined on the members of the tailnet or Access) | Tailscale, Cloudflare Access | NS-11.B, IAM-03.B |
| NEED cloud_infrastructure: security groups or firewalls in front of each origin allow inbound web traffic only from the edge's published ranges, or no public port where a tunnel is used | `edge.origin_locked` | NS-10.C |
| NEED cloud_infrastructure: each archive bucket that holds logs keeps them for the policy period (`cloud.storage_lifecycle` with a log bucket population) | `observability.logs_retained` | LM-02.C |
| NEED verity_tasks: incidents imported from a connector land in the register with a triage decision field; the register exposes completeness against `source` and `external_id` | `*.incidents_registered` | LM-04.B, LM-07.D |
| NEED verity (notifications): a delivery log of security messages Verity sent (channel, time, provider message id) | Slack | CS-04.D, CS-06.B (`sample-of-messages-sent-under-the`) |
| NEED business application (Slack, Sentry, Datadog, PagerDuty, Jira, Cloudflare, Tailscale): an export of the accounts holding admin roles in the tool, for the privileged access list | every connector here | IAM-07.B, IAM-02.B (`list-of-privileged-accounts-with-approval`, `account-list-export`) |
| NEED business application (Slack, Sentry): every active member has a second factor or signs in through SSO | Slack, Sentry | IAM-03.B, IAM-04.B for those tools |

## 7. Framework reach

Through the controls mapped above (from `template_requirements.json`; `~` partial mapping):

| Control | SOC 2 | ISO 27001:2022 | Reached by |
|---|---|---|---|
| SD-01 | CC8.1, CC5.2~ | A.8.19~, A.8.32~ | Jira |
| SD-04 | CC8.1~ | A.8.32~ | Jira |
| SD-14 | CC8.1~ | A.8.32~ | Jira |
| IAM-01 | CC6.2, CC6.3~ | A.5.15~, A.5.16~, A.5.18~, A.8.34~ | Jira |
| IAM-09 | CC6.3~, CC5.1~ | A.5.3 | Jira |
| GOV-08 | CC4.2 | 10.2 | Jira |
| CS-03 | CC2.2~, CC2.3~ | A.5.24~, A.6.8 | Jira |
| LM-04 | CC7.3 | A.5.25, A.8.16~ | Jira, PagerDuty, Datadog |
| LM-05 | CC7.4~, CC7.5~ | 10.2~, A.5.26~, A.5.27 | Jira, PagerDuty |
| LM-06 | CC7.5 | A.5.26~ | PagerDuty |
| LM-07 | CC7.4, P6.5~ | A.5.24~, A.5.26~, A.5.28~ | Jira, PagerDuty |
| LM-08 | CC7.2~, CC7.4~ | none mapped | PagerDuty, Datadog, Sentry |
| LM-09 | CC7.2 | A.8.16~ | PagerDuty, Datadog, Sentry |
| LM-02 | CC7.2~, CC2.1~ | A.5.28~, A.8.15 | Datadog |
| NS-05 | CC6.8~, CC7.2~ | A.8.16~ | Datadog |
| SD-08 | PI1.3~, PI1.4~ | none mapped | Datadog, Sentry |
| BC-04 | A1.1 | A.8.6 | Datadog |
| NS-02 | CC6.7~ | A.5.14~, A.8.21~, A.8.24~ | Cloudflare |
| NS-10 | CC6.6~ | A.8.21~ | Cloudflare |
| SD-05 | PI1.2~ | A.8.26~, A.8.28~ | Cloudflare |
| NS-11 | CC6.6~ | A.6.7~, A.8.21~ | Cloudflare, Tailscale |
| IAM-08 | CC6.1~, CC6.3, CC5.2~ | A.5.15~, A.8.3~, A.8.4~ | Cloudflare, Tailscale |
| NS-07 | CC6.1~, CC6.6~ | A.8.20~, A.8.22 | Tailscale |
| IAM-11 | CC6.1~ | A.8.5~ | Tailscale |
| IAM-12 | CC6.2~, CC6.3~ | A.5.16~, A.5.18~ | Tailscale |

LM-08 (on call) has no ISO 27001 mapping today, so PagerDuty's strongest evidence reaches ISO only
through LM-04, LM-07 and LM-09. That is a mapping question for the ISO pack, not a connector gap.

## 8. Decisions for the owner

1. **Jira auth for the first release.** A service account with a scoped API token (customer pasted,
   up to 365 days) or Verity's OAuth 2.0 (3LO) app. The app shares one 65,000 point per hour quota across
   every customer from 2 March 2026 and carries a personal data reporting duty; token traffic is exempt
   from the points quota. Recommended: scoped API token first, OAuth app once Atlassian grants a per
   tenant quota tier. See [jira.md](jira.md) section 2.
2. **Slack's role.** Recommended: notification channel only, removed from `alerting` (section 2). Optional
   later: a business application check of member two factor, which needs an admin's user token.
3. **Incident sync.** Import Jira and PagerDuty incidents into the Verity register as synced issues
   awaiting triage (section 5), or keep the register manual and only reconcile.
4. **Coverage downgrades** in section 2 (IAM-01, NS-10, NS-11 from full to partial).
5. **New artifact** `log-retention-settings` for LM-02.C (section 2).
6. **Default thresholds** used by the new checks until the workspace's procedures set them: first
   response to a security report 2 business days, acknowledgement of a high urgency page 30 minutes,
   escalation delay 30 minutes, signal triage 24 hours, error triage 72 hours, post incident review
   within 14 days, HSTS lifetime 180 days, device key expiry 180 days. Each is a proposal, not a rule
   from a standard.
7. **DNSSEC.** Keep `edge.dnssec_enabled` mapped to NS-02 partial, or drop it until an objective asks
   for it.
8. **Sentry audit log.** Leave it out (reading it needs the `org:write` scope; rechecked 2026-11-23 in
   Sentry's source, `OrganizationAuditPermission`, since the docs do not list the endpoint), or accept a write scope
   for one read. Recommended: leave it out.
9. **Cloudflare Free plan WAF.** Does the Free Managed Ruleset satisfy `edge.waf_enabled`? Recommended:
   no, fail with reason `plan` (the full managed ruleset needs Pro), so a customer either upgrades or
   records the gap. See [cloudflare.md](cloudflare.md) section 5.
