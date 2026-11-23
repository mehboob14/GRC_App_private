# PagerDuty

| | |
|---|---|
| Capabilities | alerting |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | Read only General Access REST API key (account level), pasted by an Admin or the Account Owner, with the account's region |
| Shares setup with | Nothing |
| Go library | `github.com/PagerDuty/go-pagerduty` (listed by PagerDuty as supported by PagerDuty) [P27]. Latest tag v1.8.0 of 9 January 2024; later work, including v3 schedules, is on the main branch but untagged [P28]. The README does not mention the EU, but the client takes `pagerduty.WithAPIEndpoint(endpoint)`, which points it at `https://api.eu.pagerduty.com` (checked in `client.go` on main, 2026-11-23) [P28] |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

PagerDuty records, by machine, who was on call, where alerts were routed, when a page fired, who
acknowledged it and when it was resolved. That gives Verity operating evidence for LM-08 (on call)
that today is a screenshot of a schedule, and response times for LM-04 and LM-06 that a person would
otherwise copy into a spreadsheet:

- someone, with a backup, was on call for every minute of every day (`alerts.on_call_covered`);
- an unanswered page escalates to another person within the set time (`alerts.escalation_policies_escalate`);
- security alert sources route to a rotation with high urgency (`alerts.security_routed`);
- high urgency pages were acknowledged within the target, and the ones that were not are listed
  (`alerts.acknowledged_in_time`, LM-04 and LM-08.D);
- resolved incidents have an owner and a timeline (`alerts.incidents_resolved`);
- every security or major incident reached Verity's incident register (`alerts.incidents_registered`);
- major incidents got a completed review, where reviews are kept in PagerDuty (`alerts.postmortems_completed`).

What it does **not** prove: that the evidence of an incident's handling is right (severity, customer
notice, recovery steps), that the escalation policy in the tool is the approved one (LM-08.A is a
document), or that every alert source that should page is connected to PagerDuty at all. A configured
destination alone does not show response (continuous compliance plan, section 7), which is why the
checks read incidents and log entries, not just settings.

Beyond Verity's own register: the register holds what a person wrote about an incident; PagerDuty adds
the machine recorded times and the completeness test. See [operations-checks.md](operations-checks.md)
section 5.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

| Option | Fit | Why |
|---|---|---|
| **General Access REST API key, read only** (recommended) | yes | Account level, so it does not depend on one person. Ticking "Read-only API Key" restricts it to GET calls [P1]. Created by an Admin or the Account Owner [P1]. Sent as `Authorization: Token token=<key>` [P2] |
| User API token | no | Needs Advanced Permissions on the account (Professional and above) and acts with that person's rights; stops when they leave [P1] [P25] |
| Scoped OAuth, client credentials (app token) | no for a vendor | App tokens are issued only for the account that registered the app; on other accounts a published app gets user tokens only [P8] |
| Scoped OAuth, user token | later | Access token 1 day, refresh 30 days, rolling one year [P5]; acts as the consenting user, PKCE required [P5]. Useful if a marketplace style install is wanted later |
| Classic OAuth | no | Legacy app type with only `read` and `write` scopes [P5] [P6] |

Base URLs: `https://api.pagerduty.com` (US) and `https://api.eu.pagerduty.com` (EU). PagerDuty can
forward US calls to the EU but recommends calling the EU address directly [P4]. Every call sends
`Accept: application/vnd.pagerduty+json;version=2` [P3].

### 2.2 Permissions

A read only key reaches every GET endpoint the account's plan offers. For a later scoped OAuth app, the
read scopes per check are (names from the official schema) [P9]:

| Scope (scoped OAuth) | Read only | Needed for (check keys) | Who can grant |
|---|---|---|---|
| `services.read` | yes | `alerts.security_routed`, scope discovery, every check (service to policy routing) | key: Admin or Account Owner; app: Manager, Global Admin or Account Owner registers [P7] |
| `escalation_policies.read` | yes | `alerts.escalation_policies_escalate`, `alerts.on_call_covered`, `alerts.security_routed` | same |
| `schedules.read`, `oncalls.read` | yes | `alerts.on_call_covered` | same |
| `incidents.read` (also covers log entries; there is no separate log entry scope) | yes | `alerts.acknowledged_in_time`, `alerts.incidents_resolved`, `alerts.incidents_registered` | same |
| `priorities.read` | yes | priority threshold mapping for major incidents | same |
| `incident_reviews.read` | yes | `alerts.postmortems_completed` | same |
| `users.read`, `teams.read` | yes | names of acknowledgers and owners, team filter | same |
| `audit_records.read` | yes | optional: configuration change history | same, and the plan must include Audit Trail [P20] |

Analytics is not used. The analytics list and metrics endpoints are POST calls, which under scoped
OAuth need `analytics.write` [P10] [P9]; a read only key is limited to GET calls [P1], so it cannot call
them (confirmed 2026-11-23 from those two facts; no page says it in one sentence). Response
times are computed from incidents and log entries instead, which also keeps the evidence per incident.

### 2.3 Plan requirements

| Feature | Plans | Source |
|---|---|---|
| REST API, read only keys | all current plans | [P1] |
| Historic data you can query | Free 3 months, Professional 1 year, Starter and above included (no figure given) | [P25] |
| Post incident reviews | Professional and above (support page also names legacy Business and Enterprise plans) | [P25] [P26] |
| Audit Trail (and its API) | not on Free or Professional; Starter and above; legacy Business and Enterprise plans. Without it the API answers 402 | [P25] [P20] [P21] |

The pricing page states its plan amounts as of 3 November 2026 and warns that customers who bought
earlier may have different entitlements [P25] (corrected 2026-11-23: was "PagerDuty changed its plans
on 3 November 2026"; the page announces no change). Verity therefore reads feature availability from API answers (402) rather than
from the plan name.

## 3. Customer setup guide (draft)

1. Sign in to PagerDuty as an Admin or the Account Owner.
2. Open **Integrations**, then **API Access Keys**, and create a new key named "Verity (read only)".
3. Tick **Read-only API Key**. Copy the key; PagerDuty shows it once.
4. In Verity, open **Connections**, choose **PagerDuty**, pick your region (US or EU) and paste the key.
5. Choose the services in scope (all active services by default) and tick the ones that receive
   security alerts, such as your SIEM, cloud threat detection or endpoint protection.
6. Set the targets Verity should judge against, or keep the defaults: acknowledge high urgency pages
   within 30 minutes, escalate an unanswered page within 30 minutes, the priority that counts as major.
7. If you write post incident reviews in PagerDuty, turn that option on.

Verity never acknowledges, resolves, creates or edits anything in PagerDuty.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Services | `GET /services` with `include[]=integrations` [P11] | id, name, status (active, warning, critical, maintenance, disabled), escalation policy, urgency rule, support hours, integrations (vendor, name), teams, acknowledgement and auto resolve timeouts | classic paging | while it exists |
| Escalation policies | `GET /escalation_policies` [P13] | rules (delay in minutes, targets of user or schedule), number of loops, services, team | classic | while it exists |
| Schedules | `GET /schedules/{id}` with `since`, `until` [P14] | final schedule entries, overrides, `rendered_coverage_percentage` (set only when `since` or `until` is given) | | while it exists |
| On call | `GET /oncalls` with `since`, `until`, `escalation_policy_ids[]` [P16] | user, schedule, policy, level, start, end (null means permanent) | own rate limits; future shifts up to 90 days | computed |
| Incidents | `GET /incidents` with `since`, `until`, `service_ids[]`, `urgencies[]` [P3] | id, number, created, resolved, status, urgency, priority, service, policy, assignments, acknowledgements, last status change and by whom | window up to 6 months (default 1 month) [P3]; offset plus limit at most 10,000 [P23] | Free 3 months, Professional 1 year [P25] |
| Log entries | `GET /incidents/{id}/log_entries` [P17] | type, created, agent (user, service, integration), channel | classic | as incidents |
| Post incident reviews | `GET /incidents/reviews` [P22] | incident id, status (started, in review, completed), created, completed | cursor, up to 100 | |
| Audit records (optional) | `GET /audit/records` [P19] | time, actor, method, action, resource, before and after values | cursor; each call covers at most 31 days [P19] | 12 months [P20] |

Log entry types used: `trigger_log_entry`, `acknowledge_log_entry` (the schema also spells it
`acknowledgement_log_entry`; accept both), `assign_log_entry`, `escalate_log_entry`,
`exhaust_escalation_path_log_entry`, `resolve_log_entry` [P9] [P18].

Rate limits: 960 requests per minute per account key, 429 with error code 2020 and `ratelimit-*`
headers that some 429 answers omit; PagerDuty asks for serial requests per token [P24].

Audit Trail does not record changes to escalation policy levels or users, schedule overrides, service
integrations, disabling a service or maintenance windows [P21]. Verity's daily snapshots of policies,
schedules and services are therefore the change history for the checks below, not the audit trail.

## 5. Checks

In scope services: those the customer selects, all active services by default. Period: daily runs; the
incident checks look at the last 30 days, the coverage check at the last full day.

| Check | Population | Predicate | Pass, fail, error, insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `alerts.security_routed` (existing) | Services the customer marks as carrying security alerts | Service not disabled; urgency rule gives high urgency (constant high passes, severity based passes with a note); its escalation policy has a level targeting a schedule or user; at least one integration | pass; fail: list; error: key or region wrong; insufficient: no service marked (empty proves nothing) | daily | services, urgency rule, policy, integrations | LM-09 partial |
| `alerts.acknowledged_in_time` (existing) | High urgency incidents created in the last 30 days on in scope services, past their target | The first acknowledgement, or a resolve by a person, came within the target (default 30 minutes) of the trigger. An incident its source resolved before the target with no human action is left out with that reason | pass; fail: list with times; error; insufficient: incident list truncated or log entries unreadable for any incident. Empty: pass only if the incident list was read in full for the window, with the count of zero stated | daily | per incident: trigger, first acknowledgement, by whom | LM-04 partial; propose LM-08 partial |
| `alerts.incidents_resolved` (existing) | High urgency incidents resolved in the last 30 days on in scope services | Each had a person as owner (an assignment or acknowledgement by a user) and a readable timeline from trigger to resolve | pass; fail: no human owner, or resolved by timeout with no person involved; error; insufficient: log entries unreadable | daily | timelines and owners | LM-06 partial |
| NEW `alerts.on_call_covered` | Escalation policies of in scope services | For the last full day (UTC), the on call entries at level 1 cover every minute, and a level 2 with a different target also covers every minute. The next 7 days are shown as a warning, not judged | pass; fail: gaps with their times, or no backup level; error; insufficient: a schedule type whose on call entries cannot be computed. v3 (shift based) schedules are absent from the v2 `/schedules` list and v2 `GET /schedules/{id}` does not render their entries; read them from `GET /v3/schedules/{id}?include[]=final_schedule` (`computed_shift_assignments`) [P15]. Whether `GET /oncalls` covers v3 schedules is unverified, test | daily | on call entries per level, gaps | LM-08 partial |
| NEW `alerts.escalation_policies_escalate` | Escalation policies of in scope services | At least two levels, each with a target; level 1 escalates within the set delay (default 30 minutes); level 2 targets someone other than level 1 | pass; fail: list; error | daily | policies with levels, targets and delays | LM-08 partial |
| NEW `alerts.incidents_registered` | Incidents in the last 30 days on services marked as security, plus any at or above the mapped major priority | Each has a Verity register entry (synced with `source` pagerduty and the incident id, or linked by a person), or a recorded decision that it was not a security incident | pass; fail: list; error; insufficient: register sync off and nothing linked. Empty: pass only when the incident list was read in full | daily | incidents and their register entries | LM-04 partial, LM-07 partial |
| NEW `alerts.postmortems_completed` | Only when the customer says reviews live in PagerDuty: incidents at or above the major priority resolved between 14 and 44 days ago | A review with status completed, completed within 14 days of resolution (default) | pass; fail: missing or late; error: 402 or plan without reviews reads as "not on plan", and the artifact stays with people | daily | incidents, review status and dates | LM-05 partial |

Full definitions of the new checks: [operations-checks.md](operations-checks.md) section 3.2.

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `on-call-schedule` | LM-08.B, C, D | LM-08 | person + `alerts.on_call_covered` (full for LM-08.B over the period it ran; contact details stay with people) + `alerts.acknowledged_in_time` (partial, LM-08.D) |
| `escalation-policy` | LM-08.A, LM-08.C | LM-08 | person + `alerts.escalation_policies_escalate` (partial: the configuration; approval of the policy stays with people) |
| `sample-of-evaluated-events-with-the` | LM-04.B, C, D | LM-04 | person + `alerts.acknowledged_in_time` + `alerts.incidents_registered` (partial) |
| `recovery-records-for-incidents` | LM-06.B, C, D | LM-06 | `alerts.incidents_resolved` now implemented (partial: owner and timeline; LM-06.C and D stay with people) |
| `security-incident-register` | LM-07.D, LM-04.C and others | LM-07 | person + `alerts.incidents_registered` (partial: completeness) |
| `postmortem-for-each-significant-incident` | LM-05.B, C, D | LM-05 | person + `alerts.postmortems_completed` (partial) |
| `review-of-alert-tuning` | LM-09.B, C, D | LM-09 | person + `alerts.security_routed` (partial: routing, not the review) |

## 7. Framework reach

SOC 2: CC7.2 and CC7.4 (LM-08), CC7.2 (LM-09), CC7.3 (LM-04), CC7.4 and P6.5 (LM-07), CC7.4 and CC7.5
(LM-05, LM-06). ISO 27001:2022: A.5.24 to A.5.27 and A.8.16 through LM-04, LM-05, LM-06, LM-07 and LM-09.
LM-08 has no ISO mapping in the current pack ([operations-checks.md](operations-checks.md) section 7).

## 8. Limits and false assurance traps

- **Scope is the trap.** A clean result over services the customer chose says nothing about alert
  sources that never reach PagerDuty. The result names the services judged and those left out with
  their reasons.
- **Auto resolved pages.** A page its source cleared before anyone answered is not a response. It is
  left out only when it cleared before the response was due, and the count is shown.
- **Coverage is computed, not reported.** The on call entries are PagerDuty's rendering of schedules
  and overrides. A schedule edited after the fact changes past rendering; Verity's daily result for
  that day is kept as the record (unverified whether past entries change: the v3 upgrade guide says
  shifts already produced by a deleted rotation event stay on the record [P15], but no page covers v2
  edits; test on a fixture).
- **History is short on low plans.** Free keeps 3 months [P25]. Verity's daily results are the
  history, so a connection made late in an audit window cannot reach back further.
- **Audit Trail gaps** listed in section 4 [P21]. Do not present the audit records as the history of
  escalation settings.
- **Analytics numbers are not used**, so Verity's response times may differ from PagerDuty's own
  reports, which update within about a day [P10]. The evidence lists each incident's times so the
  difference can be explained.

## 9. Product and UI

- **Connect form:** region (US or EU), read only API key, optional account subdomain for display.
- **Scope:** services with team, status and integration names; in or out with a reason; a tick for
  "carries security alerts".
- **Targets:** acknowledgement target, escalation delay, major priority, review days; each prefilled
  from the workspace procedure when one sets it, otherwise the defaults of owner decision 6.
- **Health:** key invalid or region wrong; Audit Trail not on plan (402); reviews not on plan; history
  shorter than the audit window.
- **In product guide:** yes, short: where to create the key and the read only tick.

## 10. Implementation notes

- **Auth.** Static key in the `Authorization: Token token=` header [P2]. Test with `GET /abilities` or a
  one item `GET /services`; a 401 is a bad key, a 403 on one endpoint is that check's `error`.
- **Paging.** Classic paging uses `limit` up to 100, `offset`, `more`; `total` only with `total=true`;
  offset plus limit above 10,000 returns 400 [P23]. Slice incident queries by day so no slice passes the
  ceiling; audit records and reviews use cursors.
- **Rate limits.** One request at a time per key, limiter at 900 per minute, back off on 429 and on
  error code 2020 even without headers [P24].
- **Log entry types.** Accept both acknowledge spellings [P9] [P18]. Agent type tells a person from an
  integration or a timeout.
- **Changes in the API.** Service alert grouping fields and `alert_creation` are deprecated [P12]; do
  not read them. Some schedule list endpoints lost paging on 25 September 2026 [P12].
- **Deletion.** A deleted service or policy disappears from lists; Verity marks it removed in
  `connection_resources` with the date, and earlier results keep it.
- **Fixtures.** Record on a Free test account (5 users): two services, a two level policy, a schedule
  with a gap, incidents acknowledged late, auto resolved and escalated to exhaustion.

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | not public (help article returns 404) | User access only: PagerDuty accounts tied to current staff; no automated tests listed [P29] |
| Drata, Secureframe, Sprinto | unverified (integration pages return 404 and the catalogues did not list PagerDuty) | unverified |

No public material describes testing on call coverage, escalation or acknowledgement times. These
checks are new ground for Verity.

## 12. Sources

- [P1] https://docs.pagerduty.com/account-admin/api-access-keys
- [P2] https://docs.pagerduty.com/developer/authentication
- [P3] https://docs.pagerduty.com/developer/api/reference/rest/incidents/list-incidents
- [P4] https://docs.pagerduty.com/get-started/service-regions
- [P5] https://docs.pagerduty.com/developer/oauth-functionality
- [P6] https://docs.pagerduty.com/integrations/apps/scoped-oauth-apps
- [P7] https://docs.pagerduty.com/developer/register-an-app
- [P8] https://docs.pagerduty.com/developer/private-apps
- [P9] https://raw.githubusercontent.com/PagerDuty/api-schema/main/reference/REST/openapiv3.json (official REST schema)
- [P10] https://docs.pagerduty.com/developer/api/reference/rest/analytics/get-analytics-incidents
- [P11] https://docs.pagerduty.com/developer/api/reference/rest/services/list-services.md
- [P12] https://docs.pagerduty.com/developer/api-changelog.md
- [P13] https://docs.pagerduty.com/developer/api/reference/rest/escalation-policies/list-escalation-policies.md
- [P14] https://docs.pagerduty.com/developer/api/reference/rest/schedules/get-schedule.md
- [P15] https://docs.pagerduty.com/developer/schedules-v2-to-v3-upgrade.md
- [P16] https://docs.pagerduty.com/developer/api/reference/rest/on-calls/list-on-calls.md
- [P17] https://docs.pagerduty.com/developer/api/reference/rest/incidents/list-incident-log-entries
- [P18] https://docs.pagerduty.com/developer/api/reference/rest/log-entries/get-log-entry.md
- [P19] https://docs.pagerduty.com/developer/api/reference/rest/audit/list-audit-records
- [P20] https://docs.pagerduty.com/developer/audit-records-api.md
- [P21] https://docs.pagerduty.com/incident-management/analytics/audit-trail.md
- [P22] https://docs.pagerduty.com/developer/api/reference/rest/post-incident-reviews/list-incident-reviews.md
- [P23] https://docs.pagerduty.com/developer/pagination.md
- [P24] https://docs.pagerduty.com/developer/rest-api-rate-limits.md
- [P25] https://www.pagerduty.com/pricing/
- [P26] https://docs.pagerduty.com/incident-management/after-incident/post-incident-reviews.md
- [P27] https://docs.pagerduty.com/developer/api-client-libraries.md
- [P28] https://github.com/PagerDuty/go-pagerduty, https://github.com/PagerDuty/go-pagerduty/tags, https://github.com/PagerDuty/go-pagerduty/commits/main
- [P29] https://www.vanta.com/integrations/pagerduty

The older hosts developer.pagerduty.com and support.pagerduty.com redirect to docs.pagerduty.com as of
2026-11-23; the addresses above are the pages read.
