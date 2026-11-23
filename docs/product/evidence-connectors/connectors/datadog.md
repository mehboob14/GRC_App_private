# Datadog

| | |
|---|---|
| Capabilities | observability |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | Recommended: a Datadog service account with a Service Access Token, scopes limited to the reads below, sent as a bearer token [D3]. Fallback: API key plus a scoped application key owned by the service account [D6] |
| Shares setup with | Nothing |
| Go library | `github.com/DataDog/datadog-api-client-go/v2`, packages `api/datadog`, `api/datadogV1`, `api/datadogV2` (official, generated) [D35]. Its README shows API and application key auth only, but the client source defines `datadog.ContextAccessToken`, which sends `Authorization: Bearer <token>` [D45]. A Service Access Token can also be sent in the application key header, with the API key optional [D3] |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

Datadog is where many customers keep logs, monitors and, if they bought Cloud SIEM, security detection.
It can show:

- how long security and audit logs are kept, and whether a source that falls silent raises an alert
  (LM-02);
- that monitors exist for the anomaly types, capacity and job failures, that every production service
  has one, and that high priority ones page the on call rotation (LM-09, LM-08, BC-04, SD-08);
- that Cloud SIEM detection rules are on for the conditions the alerting standard names, and that
  serious signals were triaged in time by a named person (LM-09, LM-04, NS-05);
- that Datadog records changes to its own configuration (LM-02).

It does not show that every system sends its logs (that needs the asset inventory), that an alert was
acted on beyond its triage state (incident handling is PagerDuty and the register), that archived logs
survive in the customer's bucket for the policy period (that is the cloud provider), or that alert
tuning was reviewed (LM-09.D is a person's record).

Verity has no module for monitoring, so everything here is new evidence.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

| Option | Fit | Notes |
|---|---|---|
| **Service Access Token on a service account** (recommended) | yes | Owned by a service account, so it survives staff leaving; scopes are mandatory; expiry 1 day, 1 month, 1 year, never or custom, fixed at creation; the secret is shown once [D3]. Datadog announced on 9 June 2026 that application keys stay but get no new features [D2] |
| API key plus scoped application key | fallback | Application keys with no scopes inherit all of the creator's rights, so scopes must be set [D6]. Disabling the owning user revokes its keys [D6]; owning by a service account avoids that |
| Personal Access Token | no | Tied to a person; at most one year [D4] |
| OAuth 2.0 | later | Exists for partner integrations built in Datadog's developer platform, started from the integration tile, with PKCE [D10]. Datadog said general use OAuth clients are planned later in 2026 [D2] |

Datadog runs nine sites; the API base is `https://api.<site>`, for example `api.datadoghq.com`,
`api.us3.datadoghq.com`, `api.us5.datadoghq.com`, `api.datadoghq.eu`, `api.ap1.datadoghq.com`,
`api.ap2.datadoghq.com`, `api.uk1.datadoghq.com`, `api.ddog-gov.com`, `api.us2.ddog-gov.com` [D11] [D40].

### 2.2 Scopes and permissions

| Scope (permission name) | Read only | Needed for (check keys) | Admin role that can grant |
|---|---|---|---|
| `monitors_read` | yes | `observability.anomaly_monitors`, `observability.processing_monitored`, `observability.capacity_trends`, `observability.monitors_notify_on_call`, `observability.production_services_monitored`, `observability.silent_sources_alert` | a user with `service_account_write` (in the Admin role) creates the service account; `org_app_keys_write` (any service account) or `service_account_write` (accounts you manage) creates its tokens [D3] [D9]; both are Datadog Admin role permissions by default [D8] |
| `logs_read_config` | yes | `observability.logs_retained` (indexes, retention, exclusion filters) | same |
| `logs_read_archives` | yes | `observability.logs_retained` (archives and their state) | same |
| `security_monitoring_rules_read` | yes | `observability.siem_rules_enabled` | same |
| `security_monitoring_signals_read` | yes | `observability.security_signals_triaged` | same |
| `audit_logs_read` | yes | `observability.audit_trail_enabled`, first triage time in `observability.security_signals_triaged` | same; held by the Admin role by default, so the service account needs a custom role that adds it [D8] |
| `apm_read`, `apm_service_catalog_read` | yes | `observability.production_services_monitored` (production services and catalog) | same |
| `hosts_read` | yes | `observability.capacity_trends`, `observability.production_services_monitored` (hosts by environment) | same |
| `dashboards_read` | yes | evidence for BC-04 capacity review (dashboards named in the review) | same |
| `user_access_read` | yes | optional: admin role holders for the privileged access list ([operations-checks.md](operations-checks.md) section 6). Not on the role permissions page; the List all users endpoint names it as its permission and OAuth scope [D41] | same |

Assign the service account the Datadog Read Only role plus a custom role holding `audit_logs_read`;
the token's scopes then narrow it further. The Read Only role holds every permission above by default
except `audit_logs_read`, which only the Admin role holds [D8]. Still unverified: whether the token's
scope picker offers every role permission. OAuth clients get a limited scope list while scoped
application keys may take any permission [D7], and the log index and archive endpoints name a
permission but no OAuth scope [D15] [D17]. The connect test probes each one.

### 2.3 Plan and product requirements

| Feature | Requirement | Source |
|---|---|---|
| Log index retention | Values allowed depend on the customer's contract; Standard indexing offers 3, 7, 15, 30 and over 30 days | [D15] [D31] |
| Flex Logs (long retention) | Separate tier: 3 to 15 months (Starter) or 30 to 450 days | [D32] |
| Cloud SIEM | Separate product, billed per analysed events | [D33] |
| Audit Trail | Paid add on; when on, events kept 90 days by default (3, 7, 15, 30 or 90); when off, 7 days | [D33] [D24] [D22] |
| Security signals | Kept 15 months | [D22] |

Without Cloud SIEM, its two checks read "not on plan" once per connection. Without the Audit Trail add
on, `observability.audit_trail_enabled` fails with reason `plan`, because that is the setting.

## 3. Customer setup guide (draft)

1. In Datadog, open **Organization Settings**, then **Service Accounts**, and create "Verity (read
   only)" with the Datadog Read Only role.
2. Create a custom role that adds **Audit Trail read** (`audit_logs_read`) and give it to the service
   account. Skip this if you do not use Audit Trail.
3. Open the service account and choose **New Token**. Tick only the scopes Verity lists, choose one year
   as the expiry, and copy the token.
4. In Verity, open **Connections**, choose **Datadog**, pick your Datadog site, and paste the token and
   its expiry date.
5. Tell Verity what production looks like (the `env` values, by default `prod` and `production`), which
   log indexes hold security and audit logs, how a monitor pages on call (by default `@pagerduty-` and
   `@oncall-` handles), and which monitor priority counts as high.
6. List the jobs and log sources Verity should expect alerts for, or import them from the asset
   inventory.

Verity never edits monitors, indexes, rules or signals.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Monitors | `GET /api/v1/monitor` [D1]; `GET /api/v1/monitor/search` for notifications per monitor [D12] | id, name, type, query, message, tags, priority (1 high to 5 low), overall state, draft status, options (`notify_no_data`, `on_missing_data`, thresholds, `renotify_interval`); search adds parsed notification handles and last triggered time | `page` and `page_size` (default 100); without `page` all come back [D1] | while they exist |
| Log indexes | `GET /api/v1/logs/config/indexes` [D15] | name, filter, `num_retention_days` (Standard), `num_flex_logs_retention_days` (Standard plus Flex), exclusion filters (query, sample rate, enabled), daily limit | one call; up to 100 indexes by default [D16] | config |
| Log archives | `GET /api/v2/logs/config/archives` [D17] | name, query, destination (s3, gcs, azure), state (WORKING, FAILING and others) | one call | bucket retention is set in the cloud, not visible here [D17] |
| Detection rules | `GET /api/v2/security_monitoring/rules` [D18] | id, name, enabled, default or custom, deleted, type, cases (status info to critical, notifications), tags | `page[size]` up to 100 | life of the account [D22] |
| Security signals | `GET /api/v2/security_monitoring/signals` with `filter[from]`, `filter[to]` [D19] | id, rule, severity, created, triage state (open, under review, archived), archive reason, assignee, state update time and user (`state`, `archive_reason`, `assignee`, `state_update_timestamp`, `state_update_user` are documented on the triage endpoint [D20]; the list schema returns them only inside the free form `attributes.attributes` object, where the example shows a `workflow` block, so their exact paths in list results stay unverified until a fixture shows them [D19]) | cursor, `page[limit]` | 15 months [D22]; locked 30 days after creation [D21] |
| Audit Trail events | `GET /api/v2/audit/events` with `filter[query]`, `filter[from]`, `filter[to]` [D23] | time, actor, event name, asset type and id, action, changed values | cursor, `page[limit]` | 90 days when on, 7 when off [D24] |
| Production services | `GET /api/v2/apm/services?filter[env]=<env>` [D28]; `GET /api/v2/catalog/entity` [D26] | service names per environment; catalog entities, owner, lifecycle | catalog: `page[offset]`, `page[limit]` | |
| Hosts | `GET /api/v1/hosts` with `filter` [D29] | name, tags by source, up, last reported | `start`, `count` up to 1,000 | hosts that reported in the last 3 hours by default; host data kept 7 days [D29] |

Rate limits: Datadog returns `X-RateLimit-Limit`, `-Period`, `-Remaining`, `-Reset` and `-Name` and 429
when exceeded; numbers for these endpoints are not published, so the collector reads the headers [D30].

Notification handles in a monitor message include `@pagerduty-`, `@oncall-` (Datadog On-Call),
`@webhook-`, `@slack-`, `@teams-`, `@jira-` and email addresses [D13] [D14]. Opsgenie uses
`@opsgenie-<service name>`, the service name set in the Opsgenie integration tile [D42].

## 5. Checks

Period: daily runs; event checks look at the last 30 days. Every monitor check counts only enabled,
published monitors (draft status excluded).

| Check | Population | Predicate | Pass, fail, error, insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `observability.logs_retained` (existing) | Log indexes the customer marks as security or audit (default all) | Searchable days, the larger of the two retention fields, at least the LM-02 `searchable_months` (3 months, 90 days); total retention at least `retention_months` (12) through Flex, or a WORKING archive whose query covers the index | pass: Flex or Standard meets both; fail: below 90 searchable days, or under 12 months with no working archive; insufficient: the 12 months rely on an archive whose bucket retention is not confirmed by the cloud connector; error: scope missing | daily | indexes, retention values, archives and state, exclusion filters on in scope sources | LM-02 partial |
| `observability.anomaly_monitors` (existing) | Enabled monitors | For each anomaly type (error spikes, unusual traffic, failed sign ins) at least one monitor mapped to it, or found by its query (anomaly or outlier functions, log alerts on failed sign in), that notifies someone | pass; fail: types with no monitor (remedy: create one, or map an existing one); error | daily | monitors per type | LM-09 partial |
| `observability.processing_monitored` (existing) | Jobs the customer lists | Each has an enabled monitor that alerts on failure and one that alerts on missing data (the job did not run), both notifying someone | pass; fail: list; insufficient: no jobs listed | daily | jobs and matched monitors | SD-08 partial |
| `observability.capacity_trends` (existing) | Production hosts and services (mapped `env`) | Each is covered by enabled monitors on CPU, memory and disk use with a threshold below the limit, notifying someone; databases add a connections monitor where mapped. Metric names are matched from a reviewed list, and the customer can map others | pass; fail: list of gaps; insufficient: no production hosts or services found | weekly | utilisation monitors per resource | BC-04 partial |
| NEW `observability.monitors_notify_on_call` | Enabled monitors at or above the mapped priority (default 1 and 2), and Cloud SIEM rules with high or critical cases | Each message or case notification includes an on call handle (`@pagerduty-`, `@oncall-`, or a webhook the customer marks as paging); email or chat alone fails | pass; fail: list; insufficient: no monitor has a priority and no tag mapping is set | daily | monitors, handles found | LM-08 partial, LM-09 partial |
| NEW `observability.production_services_monitored` | APM services in the mapped production environments, catalog entities with a production lifecycle, and production tagged hosts when APM is not used | Each is matched by at least one enabled monitor whose query or tags reference it (by `service:` or a host scope that includes it) and that notifies someone | pass; fail: unmatched services; insufficient: no production services found (APM off and no tags) | daily | services, matched monitors, how each matched | LM-09 partial |
| NEW `observability.silent_sources_alert` | In scope log sources the customer lists | Each has an enabled log monitor on that source that alerts on missing data or a count below a threshold, notifying someone | pass; fail; insufficient: no sources listed | daily | sources and their missing data monitors | LM-02 partial |
| NEW `observability.siem_rules_enabled` | Cloud SIEM rules not deleted; the conditions the workspace's alerting standard names (LM-09.B list by default) | Each condition has at least one enabled rule mapped to it (Verity proposes a mapping from rule names and tags, the customer confirms); every enabled rule's high and critical cases notify someone | pass; fail: conditions without a rule, rules whose serious cases notify nobody; error; "not on plan" without Cloud SIEM | daily | rules, mapping, notifications | LM-09 partial, LM-02 partial, NS-05 partial |
| NEW `observability.security_signals_triaged` | High and critical signals created in the last 30 days, past their response time (default 24 hours) | Each left the open state within the response time, with an assignee or a named user on the state change; every archived one has a reason other than none. First triage time comes from the audit trail; without it, a last state change inside the window proves the first one was too | pass; fail: late, never triaged, or archived without a reason; insufficient: the last change is after the window and the audit trail cannot show the first; "not on plan" without Cloud SIEM | daily | signals, states, times, users | LM-04 partial, NS-05 partial |
| NEW `observability.audit_trail_enabled` | The organisation | Audit Trail events older than 8 days exist. With Audit Trail off Datadog keeps 7 days only [D24] | pass: older events found; fail with reason `plan` or setting: the connection has run more than 8 days and no event is older than 8 days; insufficient: the connection is younger than 8 days; error: scope missing | daily | event counts by type and age (no event content beyond type, actor and time) | LM-02 partial |

Full definitions of the new checks: [operations-checks.md](operations-checks.md) section 3.3.

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `log-retention-settings` (proposed new artifact) | LM-02.C | LM-02 | none today; `observability.logs_retained` (partial) + `cloud.audit_logging` + person |
| `evidence-logs-are-reviewed` | LM-02.B, LM-02.D | LM-02 | person + `observability.silent_sources_alert` (partial, B) + `observability.siem_rules_enabled` (partial, D) |
| `review-of-alert-tuning` | LM-09.B, C, D | LM-09 | person + `observability.anomaly_monitors`, `observability.monitors_notify_on_call`, `observability.production_services_monitored`, `observability.siem_rules_enabled` (partial: the alert set; the review stays with people) |
| `on-call-schedule` | LM-08.C | LM-08 | + `observability.monitors_notify_on_call` (partial: alerts reach the rotation) |
| `sample-of-evaluated-events-with-the` | LM-04.B, LM-04.D | LM-04 | person + `observability.security_signals_triaged` (partial) |
| `sample-of-alerts-that-were-investigated` | NS-05.C, D, E | NS-05 | person + `observability.security_signals_triaged` (partial; NS-05.E tuning decisions stay with people) |
| `capacity-review` | BC-04.B, C | BC-04 | person + `observability.capacity_trends` (partial) |
| `reconciliation-results-and-how-exceptions-were` | SD-08.B | SD-08 | person + `observability.processing_monitored` (partial) |
| `alerting-standard` | LM-09.A, BC-04.A | LM-09 | unchanged (a document); the checks read its condition list |

## 7. Framework reach

SOC 2: CC7.2 and CC2.1 (LM-02), CC7.2 (LM-09), CC7.2 and CC7.4 (LM-08), CC7.3 (LM-04), CC6.8 and CC7.2
(NS-05), PI1.3 and PI1.4 (SD-08), A1.1 (BC-04). ISO 27001:2022: A.8.15 and A.5.28 (LM-02), A.8.16 (LM-09,
NS-05, LM-04), A.5.25 (LM-04), A.8.6 (BC-04). Details: [operations-checks.md](operations-checks.md)
section 7.

## 8. Limits and false assurance traps

- **A monitor is not a response.** These checks prove an alert exists and goes somewhere that pages.
  Whether someone answered is PagerDuty (`alerts.acknowledged_in_time`).
- **Matching monitors to services is a reading of queries and tags.** A service matched only by a
  broad host monitor is shown with how it matched, so a reviewer can judge it.
- **Archived logs live in the customer's bucket.** Datadog shows the archive is working, not how long
  the bucket keeps files. Without the cloud check the 12 month answer is insufficient information.
- **Exclusion filters drop logs from an index.** They are listed for in scope sources. Archives receive every
  ingested log, indexed or not, so excluded logs still reach a matching archive [D43]; only the first
  archive whose filter matches gets a log.
- **Audit Trail state is inferred.** The docs describe only a settings page switch, held by Audit
  Trail Write, and no API that reports the state [D24], so the check reads event age. Turning it on or
  off is itself logged as an audit event with asset type `audit_trail_state` and
  `asset.new_value.enabled` [D44]; the collector should keep the latest such event as supporting
  evidence (an absence of the event proves nothing, since it ages out).
- **Signals lock after 30 days** [D21], and Verity reads 30 days, so late triage is still visible;
  a run gap longer than that loses the chance to see it.
- **Hosts disappear after 7 days** [D29]. Capacity coverage is judged on hosts that reported recently,
  and the asset inventory is the full list.

## 9. Product and UI

- **Connect form:** site (nine choices), Service Access Token or API key plus application key, expiry
  date.
- **Scope:** log indexes (security or audit, in or out), production environments, services.
- **Mapping:** paging handles, high priority threshold, anomaly types to monitors, jobs, log sources,
  SIEM conditions to rules. Each mapping shows what it currently matches.
- **Health:** token expiring; scope missing per check; Cloud SIEM or Audit Trail not on plan; mapping
  incomplete.
- **In product guide:** yes. Service account, custom role for audit read, scopes and site choice.

## 10. Implementation notes

- **Auth.** Bearer Service Access Token, or `DD-API-KEY` and `DD-APPLICATION-KEY` headers for the
  fallback. The token pages spell them `dd-api-key` and `dd-application-key` (header names are case
  insensitive) and the authentication page names no header [D3] [D5]; the API reference curl examples
  now send `Authorization: Bearer` [D1]. Validate keys with `GET /api/v1/validate` [D5]. Datadog orgs
  created after 20 August 2025 have One-Time Read mode on by default, so application key secrets show
  once only (corrected 2026-11-23: was "show secrets once only", which is the default, not a fixed
  rule) [D6]; the form must say so.
- **Paging.** Monitors: page through `page`. Rules: `page[number]`. Signals and audit events: cursors.
  Hosts: `start` and `count`.
- **Rate limits.** Read the `X-RateLimit-*` headers and back off before zero; numbers are not published
  [D30].
- **Deprecated fields.** Monitor options `locked`, `silenced` and others are deprecated [D1]; read mute
  state from downtimes instead (endpoint not researched here). Rule fields `filters` and
  `queries.metric` are deprecated [D18]. The service definition API covers schema v2.2 and earlier; use
  the catalog entity API for v3 [D27].
- **Scope drift.** A 403 on one endpoint marks only its checks `error`, with the permission named.
- **Fixtures.** A trial org with Log Management, a Flex index, a failing archive, monitors with and
  without priorities and handles, Cloud SIEM default rules, signals in each triage state.

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | API key and application key, region choice; scopes `monitors_read`, `user_access_read`, plus `logs_read_config`, `logs_read_data`, `security_monitoring_rules_read`, `security_monitoring_notification_profiles_read` for Cloud SIEM | SIEM audit log retention, SIEM monitoring and alerting, infrastructure monitoring [D36] |
| Drata | API key and an application key from a service account with a custom role (security notification rules, usage, log archives and log configuration read) | Logs centrally stored, access to log sinks, logs retained 365 days (with AWS), CPU, storage and queue monitored, logs monitored for suspicious activity, capacity monitoring [D37] |
| Secureframe | API key with `user_access_read` | Monitoring alerts, monitoring dashboards [D38] |
| Sprinto | API key and application key with `monitors_read`, `user_access_read`, `incident_read` | Infrastructure monitored, incidents closed, leaver access removed [D39] |

Differences in Verity's design: a service account token instead of a person's key, checks that a
production service has a monitor and that high priority monitors page someone, and signal triage times.
Drata's 365 day check depends on AWS, which matches Verity's insufficient information answer when the
archive bucket cannot be seen.

## 12. Sources

- [D1] https://docs.datadoghq.com/api/latest/monitors/get-all-monitors.md
- [D2] https://www.datadoghq.com/blog/datadog-api-authentication.md
- [D3] https://docs.datadoghq.com/account_management/service-access-tokens.md
- [D4] https://docs.datadoghq.com/account_management/personal-access-tokens.md
- [D5] https://docs.datadoghq.com/api/latest/authentication.md
- [D6] https://docs.datadoghq.com/account_management/api-app-keys/
- [D7] https://docs.datadoghq.com/api/latest/scopes/
- [D8] https://docs.datadoghq.com/account_management/rbac/permissions/
- [D9] https://docs.datadoghq.com/account_management/org_settings/service_accounts.md
- [D10] https://docs.datadoghq.com/developers/authorization/oauth2_in_datadog.md
- [D11] https://docs.datadoghq.com/getting_started/site.md
- [D12] https://docs.datadoghq.com/api/latest/monitors/monitors-search.md
- [D13] https://docs.datadoghq.com/monitors/notify.md
- [D14] https://docs.datadoghq.com/service_management/on-call/triggering_pages.md
- [D15] https://docs.datadoghq.com/api/latest/logs-indexes/get-all-indexes.md
- [D16] https://docs.datadoghq.com/logs/log_configuration/indexes.md
- [D17] https://docs.datadoghq.com/api/latest/logs-archives/get-all-archives.md
- [D18] https://docs.datadoghq.com/api/latest/security-monitoring/list-rules.md
- [D19] https://docs.datadoghq.com/api/latest/security-monitoring/get-a-list-of-security-signals.md
- [D20] https://docs.datadoghq.com/api/latest/security-monitoring/change-the-triage-state-of-a-security-signal.md
- [D21] https://docs.datadoghq.com/security/cloud_siem/triage_and_investigate/investigate_security_signals.md
- [D22] https://docs.datadoghq.com/data_security/data_retention_periods.md
- [D23] https://docs.datadoghq.com/api/latest/audit/get-a-list-of-audit-logs-events.md
- [D24] https://docs.datadoghq.com/account_management/audit_trail.md
- [D25] https://docs.datadoghq.com/account_management/audit_trail/events.md
- [D26] https://docs.datadoghq.com/api/latest/software-catalog/get-a-list-of-entities.md
- [D27] https://docs.datadoghq.com/api/latest/service-definition.md
- [D28] https://docs.datadoghq.com/api/latest/apm/get-service-list.md
- [D29] https://docs.datadoghq.com/api/latest/hosts/get-all-hosts-for-your-organization.md
- [D30] https://docs.datadoghq.com/api/latest/rate-limits.md
- [D31] https://www.datadoghq.com/pricing/?product=log-management
- [D32] https://docs.datadoghq.com/logs/log_configuration/flex_logs.md
- [D33] https://www.datadoghq.com/pricing/list/
- [D34] https://www.datadoghq.com/blog/cloud-siem-changes/
- [D35] https://github.com/DataDog/datadog-api-client-go
- [D36] https://help.vanta.com/en/articles/11345784-integrating-vanta-datadog
- [D37] https://help.drata.com/en/articles/6414118-datadog-connection
- [D38] https://support.secureframe.com/hc/en-us/articles/26817462663315-Datadog
- [D39] https://docs.sprinto.com/integrations/overview/datadog-integration
- [D40] https://docs.datadoghq.com/api/latest/apm.md
- [D41] https://docs.datadoghq.com/api/latest/users/list-all-users/
- [D42] https://docs.datadoghq.com/integrations/opsgenie/
- [D43] https://docs.datadoghq.com/logs/log_configuration/archives/
- [D44] https://docs.datadoghq.com/security/default_rules/def-000-atd/
- [D45] https://raw.githubusercontent.com/DataDog/datadog-api-client-go/master/api/datadog/client.go (source, not docs; `PrepareRequest`)
