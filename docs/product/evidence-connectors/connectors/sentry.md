# Sentry

| | |
|---|---|
| Capabilities | observability |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | Internal integration (custom integration) created by the customer, read permissions only; its token does not expire [S5] [S6] |
| Shares setup with | Nothing |
| Go library | None official found for the web API (still unverified: an absence; Sentry's API docs name no Go client and a search found only community ones). `getsentry/sentry-go` is the error reporting SDK, not an API client [S31]. `github.com/jianyuan/go-sentry/v2` (community) was archived on 27 July 2026 [S32]. Recommended: a thin `net/http` client |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

Sentry collects application errors. For Verity it shows:

- every production project has an enabled alert that notifies someone, and high priority alerts reach
  the on call tool (`observability.production_services_monitored`, `observability.monitors_notify_on_call`);
- production errors were picked up within the triage time and none sits unresolved without an owner
  (`observability.errors_triaged_in_time`, SD-08);
- error spike alerting, which is one of the three anomaly types `observability.anomaly_monitors` asks
  for.

It does not show log retention (Sentry events are not the logs LM-02 means), unusual traffic or failed
sign ins, whether the fix was correct, or reconciliation of processing outputs (SD-08.C). Error volume
in Sentry depends on the customer's SDK setup and sampling, so "no errors" is not proof of correct
processing.

## 2. Connecting: method, credentials and permissions

| Option | Fit | Notes |
|---|---|---|
| **Internal integration** (recommended) | yes | Created under Settings, Developer Settings; installs on the organisation and issues an organisation wide token at once; tokens do not expire; up to 20 tokens per integration; permissions editable later [S5] [S6]. It cannot hold more rights than the person creating it [S7]. Works on self hosted Sentry too [S10] |
| Organisation auth token | no | Fixed to CI tasks, permissions not customisable [S6] |
| Personal token | no | Stops when the person leaves the organisation; scopes cannot be edited later [S6] |
| Legacy API keys | no | Disabled for new accounts [S10] |

Who can create one: the docs do not say. In Sentry's source, creating one needs `org:write` or
`org:admin`, which only the Manager and Owner roles hold [S8] [S9].

| Permission (internal integration) | Scope it grants [S11] | Read only | Needed for (check keys) |
|---|---|---|---|
| Organization: Read | `org:read` | yes | projects, organisation settings, alerts, monitors and cron monitors (each of these endpoints accepts `org:read`, `org:write`, `org:admin` or `alerts:read` [S17] [S18] [S36]): `observability.production_services_monitored`, `observability.monitors_notify_on_call`, `observability.anomaly_monitors` |
| Issue & Event: Read | `event:read` | yes | issues and their activity: `observability.errors_triaged_in_time` |
| Member: Read | `member:read` | yes | optional: members, roles, second factor and SSO flags for the business application need ([operations-checks.md](operations-checks.md) section 6) |
| Alerts: Read | `alerts:read` | yes | optional; `org:read` already covers the alert endpoints |

The scope to permission table comes from Sentry's front end source, not the docs [S11]; the mapping of
scopes to HTTP methods is documented [S12]. Requests send `Authorization: Bearer <token>` [S10].

Not requested: the organisation audit log. Its endpoint is undocumented, marked experimental, and
needs `org:write` even to read [S24]. Reading it would break the read only rule (owner decision 8).

Plans: the free Developer plan has no API access; Team and above do [S4]. A Developer plan connection
is therefore `error` with reason `plan` on every check. Event retention: Developer 30 days, Team and
Business up to 90, Enterprise custom [S4] [S29].

Regions: US data at `sentry.io` (or `us.sentry.io`), EU at `de.sentry.io`. The organisation response
includes its region URL [S13] [S14] [S15].

## 3. Customer setup guide (draft)

1. In Sentry, as an Owner or Manager, open **Settings**, then **Developer Settings**, then **Custom
   Integrations**, and create an internal integration named "Verity (read only)".
2. Set Organization to Read, Issue & Event to Read, and Member to Read. Leave everything else at No
   Access. Save.
3. Copy the token shown on the integration page.
4. In Verity, open **Connections**, choose **Sentry**, pick your data region (US or EU, or enter your
   self hosted address), and paste the token and your organisation slug.
5. Choose the projects in scope and which environment names mean production (by default `production`
   and `prod`).
6. Mark which alert actions page your on call tool if they are not the built in PagerDuty or Opsgenie
   actions.

Verity never resolves, assigns or edits anything in Sentry.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Organisation | `GET /api/0/organizations/{org}/` [S15] | slug, region links, `require2FA`, `hasAuthProvider` | | |
| Projects | `GET /api/0/organizations/{org}/projects/` [S16] | id, slug, platform, teams, environments | cursor in the `Link` header, up to 100 | while they exist |
| Alerts (workflows) | `GET /api/0/organizations/{org}/workflows/` [S17] | id, name, enabled, environment, triggers, action filters, actions (type, target), monitor ids, last triggered, owner | cursor, up to 100 | |
| Monitors (detectors) | `GET /api/0/organizations/{org}/detectors/` [S18] | id, project, type (the filter names `error`, `metric_issue`, `issue_stream`; examples also show `uptime_domain_failure`), enabled, linked alert ids (`workflowIds`), config (shape varies by type; environment appears only in some types) | cursor, up to 100 | |
| Cron monitors | `GET /api/0/organizations/{org}/monitors/` [S36] | slug, status, mute state, schedule, environments with last and next check in (the page does not list response fields: unverified, test on a fixture) | cursor | |
| Issues | `GET /api/0/organizations/{org}/issues/` with `query`, `environment`, `statsPeriod` [S19] | id, project, status, substatus, priority, level, first seen, last seen, assigned to, unhandled | cursor; default query is `is:unresolved`, so pass an explicit query to see all | 30 to 90 days by plan [S4] |
| Issue activity | `GET /api/0/organizations/{org}/issues/{issue_id}/` (the `activity` array) [S21] | activity type, time, user | per issue | as the issue |
| Members (optional) | `GET /api/0/organizations/{org}/members/` [S27] | `orgRole`, `pending`, `expired`, `flags` (`sso:linked`, `sso:invalid`), `user.has2fa`, `user.isActive` (`user` is null for pending invites) | cursor | |

Important change: the old issue alert rule and metric alert rule endpoints were replaced by alerts
(workflows) and monitors (detectors), generally available on 7 May 2026. The old endpoints answer 410
after 17 August 2026 [S1] [S3] [S2]. Build only on the new ones.

The issue list has no resolved at field and no search term for the resolution date [S19] [S20]. The
time of resolve, assign and archive comes from the activity on each issue. Each activity item carries
`id`, `type`, `dateCreated`, `user` and `data`; the docs example shows only `first_seen` [S21]. The
other spellings come from source, which serialises the enum names in lower case: `set_resolved`,
`set_resolved_in_release`, `set_resolved_by_age`, `set_unresolved`, `set_ignored` (archive),
`set_regression`, `assigned`, `unassigned` [S22].
A separate activities endpoint exists in source but is private and capped at 100 items [S22].

Rate limits: per caller and endpoint plus a concurrency limit; headers `X-Sentry-Rate-Limit-Limit`,
`-Remaining`, `-Reset`, `-ConcurrentLimit`, `-ConcurrentRemaining`; numbers are not published [S28].

## 5. Checks

Period: daily runs over the last 30 days. Production means the mapped environment names.

| Check | Population | Predicate | Pass, fail, error, insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `observability.anomaly_monitors` (existing) | Enabled alerts and monitors of in scope projects | Error spikes are covered: a metric monitor on error count, or an alert on new and regressed issues, for each production project, notifying someone. Unusual traffic and failed sign ins are not Sentry's to show | With Sentry as the only observability connection: insufficient (error spikes shown, other types unseen). With another provider covering the rest: Sentry's part is pass or fail | daily | alerts and monitors per project | LM-09 partial |
| `observability.processing_monitored` (existing) | Jobs the customer lists, mapped to Sentry projects or cron monitors | Each job has an enabled alert that fires on its failure. Cron monitors are the better source: they are readable with `org:read` [S36], Sentry opens an issue when a monitored run is missed or fails [S37], and every plan includes at least one cron monitor [S4]. Opening an issue notifies no one by itself, so a job mapped to a cron monitor still needs an enabled alert acting on that monitor's issues [S38] | pass; fail; insufficient: no jobs listed, or a missed run cannot be shown | daily | jobs and matched alerts | SD-08 partial |
| NEW `observability.monitors_notify_on_call` | Enabled alerts on production projects that the customer marks as high priority (default: all with a production environment) | At least one action targets an on call integration (action `type` `pagerduty` or `opsgenie`, target in `config.targetIdentifier` [S39], or a webhook marked as paging); email or chat alone fails | pass; fail; error; insufficient: no alert in the population | daily | alerts, action types and targets | LM-08 partial, LM-09 partial |
| NEW `observability.production_services_monitored` | In scope projects that have a production environment | Each project has an enabled monitor with at least one enabled alert that has an action | pass; fail: projects with no working alert; insufficient: no project has a production environment | daily | projects, monitors, alerts | LM-09 partial |
| NEW `observability.errors_triaged_in_time` | Issues in production with priority high (or level fatal), first seen in the last 30 days, older than the triage time (default 72 hours) | Within the triage time the issue was assigned, resolved or archived; any still unresolved after the fix time (default 30 days) has an assignee | pass; fail: list; insufficient: activity unreadable for an issue, or the issue list cut short; error: `plan` on Developer | daily | issues with first seen, first assignment or resolve, current state | SD-08 partial |

Full definitions: [operations-checks.md](operations-checks.md) section 3.3.

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `reconciliation-results-and-how-exceptions-were` | SD-08.B | SD-08 | person + `observability.errors_triaged_in_time`, `observability.processing_monitored` (partial; SD-08.C and D stay with people) |
| `review-of-alert-tuning` | LM-09.B, LM-09.C | LM-09 | person + `observability.production_services_monitored`, `observability.monitors_notify_on_call` (partial) |
| `on-call-schedule` | LM-08.C | LM-08 | + `observability.monitors_notify_on_call` (partial) |

## 7. Framework reach

SOC 2: PI1.3 and PI1.4 (SD-08), CC7.2 (LM-09, LM-08), CC7.4 (LM-08). ISO 27001:2022: A.8.16 through
LM-09; SD-08 and LM-08 have no ISO mapping today.

## 8. Limits and false assurance traps

- **Sampling and SDK setup decide what Sentry sees.** No errors can mean no errors, or no SDK.
  Projects with no events in the period are shown separately.
- **Resolved in Sentry is not fixed.** Issues can be resolved by hand and come back as regressions;
  regressions are counted again from their regression time.
- **The new alert model is recent** (GA May 2026) [S3]. Self hosted versions may not have the new
  endpoints (still unverified: no official note says which self hosted release added them); the connection then reads `error` with that reason rather than falling back to
  removed endpoints.
- **Organisation two factor is not the same as members' two factor.** Require 2FA is Owner only, and it
  is not available with SSO, where the identity provider enforces it [S26]. Member flags are shown for
  the business application need only.

## 9. Product and UI

- **Connect form:** region (US, EU) or self hosted base URL, organisation slug, token.
- **Scope:** projects in or out with a reason; production environment names.
- **Mapping:** which alert actions page on call; high priority alerts; jobs to projects; triage and fix
  times.
- **Health:** Developer plan (no API), missing permission per check, self hosted without the new alert
  endpoints.
- **In product guide:** yes, short: where internal integrations live and which three permissions to set.

## 10. Implementation notes

- **Auth.** Bearer token; first call `GET /api/0/organizations/{org}/` to confirm the token, the region
  and `links.regionUrl`; then call the region URL [S15].
- **Paging.** Follow the `Link` header `rel="next"` until `results="false"` [S23].
- **Rate limits.** Serial requests per token, honour the `X-Sentry-Rate-Limit-*` headers [S28]; more
  tokens do not raise limits [S28].
- **Issue queries.** Always pass `query` explicitly (the default hides resolved issues) and
  `environment` [S19]. Use the organisation issues endpoint; the project one is deprecated [S35].
- **Deprecation headers.** Watch `X-Sentry-Deprecation-Date` and `X-Sentry-Replacement-Endpoint` on
  responses and raise them in telemetry [S1].
- **Fixtures.** A Team plan test organisation with two projects, one with no alert, an alert with a
  PagerDuty action, issues assigned late, resolved and regressed.

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | Installed from Sentry's integrations by an Owner; read only | Users only; no automated tests listed [S33] |
| Drata, Secureframe, Sprinto | unverified (their own pages, not Sentry's docs, would settle it); not listed in Sentry's compliance integrations directory [S34] | unverified |

Sentry's own directory lists Vanta among a few compliance tools [S34]. None of the public material tests
alert coverage or error triage times.

## 12. Sources

- [S1] https://www.sentry.help/en/articles/15015315-migrating-to-new-detectors-and-alerts-apis
- [S2] https://docs.sentry.io/api/alerts/list-a-projects-issue-alert-rules/ (now returns 404)
- [S3] https://sentry.io/changelog/monitors--alerts--now-generally-available/
- [S4] https://sentry.io/pricing/
- [S5] https://docs.sentry.io/organization/integrations/integration-platform/internal-integration/
- [S6] https://docs.sentry.io/account/auth-tokens/
- [S7] https://docs.sentry.io/organization/integrations/integration-platform/
- [S8] https://raw.githubusercontent.com/getsentry/sentry/master/src/sentry/sentry_apps/api/bases/sentryapps.py (source, not docs)
- [S9] https://docs.sentry.io/api/organizations/update-an-organization-members-roles/
- [S10] https://docs.sentry.io/api/auth/
- [S11] https://raw.githubusercontent.com/getsentry/sentry/master/static/app/constants/index.tsx (source, not docs)
- [S12] https://docs.sentry.io/api/permissions/
- [S13] https://docs.sentry.io/api/
- [S14] https://docs.sentry.io/organization/data-storage-location/
- [S15] https://docs.sentry.io/api/organizations/retrieve-an-organization/
- [S16] https://docs.sentry.io/api/organizations/list-an-organizations-projects/
- [S17] https://docs.sentry.io/api/monitors/fetch-alerts/
- [S18] https://docs.sentry.io/api/monitors/fetch-an-organizations-monitors/
- [S19] https://docs.sentry.io/api/events/list-an-organizations-issues/
- [S20] https://docs.sentry.io/concepts/search/searchable-properties/issues/
- [S21] https://docs.sentry.io/api/events/retrieve-an-issue/
- [S22] https://raw.githubusercontent.com/getsentry/sentry/master/src/sentry/types/activity.py and https://raw.githubusercontent.com/getsentry/sentry/master/src/sentry/issues/endpoints/group_activities.py (source, not docs)
- [S23] https://docs.sentry.io/api/pagination/
- [S24] https://raw.githubusercontent.com/getsentry/sentry/master/src/sentry/api/bases/organization.py and https://raw.githubusercontent.com/getsentry/sentry/master/src/sentry/core/endpoints/organization_auditlogs.py (source, not docs)
- [S25] https://www.sentry.help/en/articles/13964940-how-long-are-my-organization-s-audit-logs-stored
- [S26] https://docs.sentry.io/organization/authentication/two-factor-authentication/
- [S27] https://docs.sentry.io/api/organizations/list-an-organizations-members/
- [S28] https://docs.sentry.io/api/ratelimits/
- [S29] https://docs.sentry.io/security-legal-pii/security/data-retention-periods/
- [S30] https://docs.sentry.io/organization/authentication/sso/
- [S31] https://github.com/getsentry/sentry-go
- [S32] https://github.com/jianyuan/go-sentry
- [S33] https://help.vanta.com/en/articles/11345687-vanta-sentry-integration
- [S34] https://docs.sentry.io/organization/integrations/compliance/
- [S35] https://docs.sentry.io/api/events/list-a-projects-issues/
- [S36] https://docs.sentry.io/api/crons/retrieve-monitors-for-an-organization/
- [S37] https://docs.sentry.io/product/monitors-and-alerts/monitors/crons/job-monitoring/
- [S38] https://docs.sentry.io/product/crons/troubleshooting/
- [S39] https://docs.sentry.io/api/monitors/create-an-alert-for-an-organization/
