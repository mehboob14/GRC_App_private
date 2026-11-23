# 5. Check registry

The readable registry of every check: the 93 shipped in `seed/content/automation/checks.json` and the new ones
the research proposes in [checks-proposed.json](checks-proposed.json). Grouped by capability. Proposals only:
nothing here changes seed content (AUTHORING rule 8). Researched and reconciled 2026-11-23.

## 5.1 Counts

| Item | Count |
|---|---|
| Shipped checks | 93 (37 running: GitHub and Verity) |
| New check keys written by the researchers | 138 |
| Aliases merged into another key | 11 |
| Proposed checks after deduplication | 127 |
| Shipped checks the research extends (providers, controls, capabilities or corrections) | 80 |
| Providers named | 57 |
| NEED entries in the coverage files | 317 (202 distinct predicates) |
| Needs resolved exactly / partly / unresolved | 83 / 141 / 93 |
| Coverage downgrades, check to control (full to partial) | 16 |
| Coverage downgrades, requirement to control (full to partial) | 8 |

## 5.2 How to read this page

- **Running**: the check has an implementation whose provider is available today (GitHub, Verity). **Planned**: in
  `checks.json`, no running implementation. **Proposed**: new, in `checks-proposed.json`.
- Providers: `S` supported, `P` partial (the connector document says why), `N` not possible.
- Controls: code then `f` full or `p` partial.
- **capability_match each** (proposed): a check written for several capabilities evaluates every connected provider
  of those capabilities on its own and passes only when all pass. Today a check with several capabilities needs all of
  them connected (for example `people.leavers_deprovisioned` needs an HR source and an identity provider). The
  merges in 5.4 need this new rule so that one connected system cannot stand in for another (an identity provider
  list must not pass for the code host list). It is an engine change for the outcome engine and the check runner.

## 5.3 By capability

### Version control (`version_control`)

Catalogue: github (available), gitlab (Phase 2), bitbucket (Phase 2).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `tickets.changes_linked` | Changes trace to approved tickets | planned | none | jira S, linear P |
| `vcs.code_scanning_enabled` | Code scanning runs on every change | planned | none | github S, gitlab P |
| `vcs.default_branch_protected` | Default branch is protected | running | github | bitbucket S, gitlab S |
| `vcs.dependency_alerts_enabled` | Dependency alerts are on | running | github | gitlab P |
| `vcs.merged_changes_reviewed` | Merged changes were reviewed | running | github | bitbucket S, gitlab S |
| `vcs.org_two_factor_required` | Two factor is required for code access | running | github | gitlab S |
| `vcs.review_required` | Merges need an approving review | running | github | bitbucket S, gitlab S |
| `vcs.secret_scanning_enabled` | Secret scanning is on | running | github | gitlab P |
| `vcs.status_checks_required` | Checks must pass before merge | running | github | bitbucket P, gitlab S |
| `vcs.unreviewed_merges_recorded` | Changes merged without review are reviewed afterward | planned | none | bitbucket P, github S, gitlab S |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `vcs.approval_resets_on_change` | New commits need a new approval | github S, gitlab S, bitbucket P | SD-06 p, SD-01 p |  |
| `vcs.dependency_alerts_within_sla` | Dependency alerts are fixed in time | github S, gitlab S, bitbucket N | SD-03 p, LM-11 p |  |
| `vcs.protection_bypass_limited` | Nobody bypasses branch protection | github S, gitlab P, bitbucket P | SD-06 p, SD-04 p |  |
| `vcs.push_protection_enabled` | Secret pushes are blocked | github S, gitlab S, bitbucket N | SD-11 p, NS-09 p |  |
| `vcs.secret_alerts_closed_in_time` | Exposed secrets are dealt with | github S, gitlab S, bitbucket N | SD-11 p, NS-09 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Every repository with a commit in the period is in scope of the connection or excluded with a recorded reason, and each in scope repository is linked to an application asset. | 4 | not defined: no repository scope completeness check was defined (cloud-code decision on repositories as assets is open). |
| Deploy keys and installed apps with their permissions are listed. | 1 | not defined: no code host machine credential check was defined. |
| Pull requests that add personal data fields carry a privacy review label or link. | 1 | not defined: no privacy review label check was defined. |
| Code scanning alerts in the period were fixed, dismissed with a reason, or carried as an exception within the timeframe. | 1 | not defined: no code scanning alert timeliness check was defined (vcs.dependency_alerts_within_sla covers dependency alerts). |
| A component list with licences can be exported for each in scope repository from the provider's dependency graph. | 1 | not defined: no dependency graph export check was defined for SD-18. |
| Dependency changes that add a component with a restricted licence are flagged at review. | 1 | not defined: no licence review check was defined. |

### Cloud infrastructure (`cloud_infrastructure`)

Catalogue: aws (Phase 2), azure (Phase 3), gcp (Phase 3), digitalocean (Phase 3), heroku (Phase 3), render (Phase 3), vercel (Phase 3), netlify (Phase 3), supabase (Phase 3), neon (Phase 3), qovery (Phase 3).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `cloud.admin_ports_closed` | No admin ports open to the internet | planned | none | aws S, azure S, digitalocean S, gcp S, neon S, supabase S |
| `cloud.audit_logging` | Audit logging is on | planned | none | aws S, azure S, gcp S, heroku P, render P |
| `cloud.backups_enabled` | Backups run and are kept | planned | none | aws S, azure S, digitalocean S, gcp S, neon S, supabase S |
| `cloud.capacity_alarms` | Capacity alarms are set | planned | none | aws P, digitalocean P, gcp P |
| `cloud.config_changes_recorded` | Configuration changes are recorded | planned | none | aws P, azure P, gcp P |
| `cloud.default_deny_ingress` | Network rules deny by default | planned | none | aws S, azure S, digitalocean S, gcp S |
| `cloud.encryption_at_rest` | Stored data is encrypted | planned | none | aws S, azure S, gcp S |
| `cloud.environments_separated` | Environments are separated | planned | none | aws S, azure S, digitalocean P, gcp S, heroku P, neon P, qovery P, supabase P |
| `cloud.hardening_baseline` | Accounts meet the hardening baseline | planned | none | aws S, azure S, gcp S, supabase P |
| `cloud.key_rotation` | Encryption keys rotate | planned | none | aws S, azure S, gcp S |
| `cloud.least_privilege` | No broad admin grants | planned | none | aws S, azure S, gcp S |
| `cloud.machine_credentials_rotated` | Machine credentials rotate | planned | none | aws S, azure S, gcp S |
| `cloud.network_segmented` | Production is segmented | planned | none | aws P, azure P, gcp P |
| `cloud.root_account_mfa` | Root accounts use two factor | planned | none | aws S |
| `cloud.secrets_managed` | Secrets live in a vault | planned | none | aws P, azure P, gcp P |
| `cloud.storage_lifecycle` | Data is deleted on schedule | planned | none | aws S, azure S, gcp S |
| `cloud.storage_versioned` | Build output keeps versions | planned | none | aws S, azure S, gcp S |
| `cloud.threat_detection` | Threat detection is on | planned | none | aws S, azure S, gcp S |
| `cloud.tls_in_transit` | Endpoints require TLS | planned | none | aws S, azure P, gcp P, supabase S |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `cloud.backup_jobs_succeeding` | Backups succeed | aws S, azure P, gcp P | BC-01 p |  |
| `cloud.backups_protected` | Backups are kept apart | aws S, azure P, gcp N | BC-01 p |  |
| `cloud.flow_logs_enabled` | Network traffic is logged | aws S, azure S, gcp P | LM-02 p |  |
| `cloud.human_users_mfa` | Cloud console users use two factor | aws S, azure N, gcp N | IAM-03 p |  |
| `cloud.restore_tested` | A restore was tested this year | aws S, azure N, gcp N | BC-02 p |  |
| `cloud.secrets_rotated` | Stored secrets rotate | aws S, azure S, gcp P | NS-09 p, IAM-10 p |  |
| `cloud.storage_public_access_blocked` | Storage is not public | aws S, azure S, gcp S | NS-04 p, LM-03 p |  |
| `cloud.threat_findings_triaged` | Threat findings are handled in time | aws S, azure S, gcp S | NS-05 p |  |
| `cloud.tls_certificates_current` | Certificates are current | aws S, azure S, gcp N | NS-02 p |  |
| `cloud.unused_credentials_disabled` | Unused cloud credentials are disabled | aws S, azure N, gcp N | IAM-10 p, IAM-12 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Outbound rules for workloads tagged high value allow only named destinations. | 2 | not defined: no egress restriction check was defined (cloud.default_deny_ingress is inbound only). |
| Temporary roles for auditors and testers expired at the agreed time. | 1 | not defined: no temporary access expiry check was defined. |
| Root and break glass sign ins and privileged role assumptions are listed from the audit log, each with the alert it raised. | 1 | not defined: no audit event listing check was defined; cloud.audit_logging only shows the trail is on. |
| Console role maximum session lengths are within the standard. | 1 | not defined: no cloud session length check was defined (idp.session_timeout covers the identity provider only). |
| Every allow rule carries an owner and purpose in a tag or description. | 1 | not defined: no rule ownership tag check was defined. |
| No allow rule points at a retired service. | 1 | not defined: no stale rule check was defined. |
| Suppression rules in the threat detection service are listed with a reason and author. | 1 | not defined: no suppression rule check was defined. |
| Each instance and managed service uses the provider's or a named time source. | 1 | not defined: no time source check was defined. |
| Each managed instance reports patch compliance from the cloud's patch manager, within the timeframe for its severity. | 1 | not defined: no cloud patch manager check was defined (proposed NS-13 has no connector check). |
| Data stores in non production accounts carry a masking or synthetic tag. | 1 | not defined: no masking tag check was defined. |
| Each database, load balancer and compute group tagged as critical runs across more than one zone or has a standby. | 1 | not defined: no zone redundancy or standby check was defined (BC-09). |

### Asset discovery (`asset_discovery`)

Catalogue: aws (Phase 2), azure (Phase 3), gcp (Phase 3), bmc (Phase 3).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `assets.resources_registered` | Every system is in the asset register | planned | none | aws S, azure S, bmc S, digitalocean S, gcp S, gws P, intune P, jamf P, kandji P, qualys P, rapid7 P, tenable P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `assets.retired_resources_closed` | Removed systems are retired | aws S, azure S, gcp S, bmc S | LM-01 p |  |

### Identity provider (`identity_provider`)

Catalogue: okta (Phase 2), gws (Phase 2), entra (Phase 2).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `idp.access_list_exported` | Access lists export for review | planned | none | anthropic S, asana S, aws S, azure S, bitbucket S, entra S, gcp S, github S, gitlab S, grafana P, gws S, heroku P, hubspot S, intercom S, linear S, neon P, netlify P, notion P, okta S, onepassword P, openai S, posthog S, sendgrid S, supabase S, vercel S, zendesk S Aliases: `cloud.access_list_exported`, `vcs.access_list_exported`, `apps.access_list_exported`. |
| `idp.admins_limited` | Few administrators | planned | none | anthropic S, entra S, gws S, heroku P, hubspot P, intercom P, linear P, okta S, openai S, posthog S, sendgrid S, supabase S, vercel S, zendesk S Aliases: `apps.admins_limited`. |
| `idp.connected_apps_known` | Connected apps are known | planned | none | entra S, gws S, okta S |
| `idp.groups_drive_access` | Access comes from roles | planned | none | entra S, okta S |
| `idp.mfa_enforced` | Two factor is enforced | planned | none | entra S, gws S, okta S |
| `idp.password_policy` | Password policy meets the standard | planned | none | entra P, gws P, okta S |
| `idp.session_timeout` | Sessions time out | planned | none | entra P, gws P, okta S |
| `idp.sso_enforced` | Apps sign in through SSO | planned | none | entra P, gws P, okta P, onepassword P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `idp.access_reviews_completed` | Identity provider access reviews are finished | entra S, okta S, gws N | IAM-02 p, IAM-07 p |  |
| `idp.admin_mfa_phishing_resistant` | Administrators use phishing resistant sign in | entra S, okta P, gws P | IAM-03 p, IAM-07 p |  |
| `idp.machine_identities_owned` | App credentials have owners and expire | entra S, okta P, gws N | IAM-10 p |  |
| `idp.no_inactive_accounts` | No unused account stays active | entra S, okta S, gws S, onepassword N | IAM-12 p, IAM-02 p, HR-03 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| each active user carries a title, department and manager, so the organization chart can be rebuilt from the directory | 3 | not defined: no directory attribute completeness check was defined. |
| the published security reporting address is a group or shared mailbox with at least one active member | 1 | not defined: no mailbox membership check was defined. |
| Accounts and groups created for auditors and testers carry an end date and were disabled by it. | 1 | not defined: no temporary account expiry check was defined. |
| Sensitive admin actions require a fresh sign in. | 1 | not defined: identity-checks.md says settings do not show re-authentication for high risk actions (IAM-11.C). |
| Disabling a user revokes their sessions and refresh tokens. | 1 | not defined: identity-checks.md says settings cannot show sign out ends refresh tokens (IAM-11.D); no check was defined. |
| Files and mail in the productivity suite carry a sensitivity label where the policy requires marking. | 1 | not defined: no labelling check was defined. |
| External sharing in the mail and file suite is limited as the rules set, public links are off or expire, and leak prevention rules are on. | 1 | not defined: no productivity suite sharing check was defined (verity-iam decision on a suite capability is open). |
| Leak prevention and sharing alerts in the mail and file suite are listed with severity, status and triage time. | 1 | not defined: no leak prevention alert check was defined. |

### Password manager (`password_manager`)

Catalogue: onepassword (Phase 2).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `vault.everyone_enrolled` | Everyone uses the company vault | planned | none | onepassword S |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Password manager administrators are listed. | 4 | not defined: no password manager admin check was defined (idp.admins_limited is n/a for 1Password in the feasibility matrix). |
| The password manager requires a second factor for every member. | 2 | no provider: 1Password does not expose member two factor status (identity-checks.md section 1). |
| Shared vaults are listed with an owner and member groups, and none is shared with everyone. | 1 | no provider: the identity feasibility matrix says the 1Password list has members only, no vault access. |
| Access to break glass vault items is listed with who and when. | 1 | not defined: no vault item access event check was defined. |

### Ticketing (`ticketing`)

Catalogue: jira (Phase 2), linear (Phase 3), asana (Phase 3), clickup (Phase 3), monday (Phase 3), notion (Phase 3).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `tickets.access_requests_approved` | Access requests are approved | planned | none | asana P, entra P, gws P, jira P, linear P, okta P |
| `tickets.remediation_tracked` | Failures are tracked to closure | planned | none | asana S, clickup P, jira S, linear S, monday P, notion P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `tickets.access_approver_independent` | Access approvals are independent | jira S | IAM-01 p, IAM-09 p |  |
| `tickets.changes_approved_before_release` | Changes are approved before release | jira S | SD-01 p, IAM-09 p |  |
| `tickets.emergency_changes_reviewed` | Emergency changes are reviewed afterwards | jira S | SD-04 p |  |
| `tickets.security_reports_answered` | Security reports are answered in time | jira S | CS-03 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Each project or epic for a new system has a linked security requirements item, approved before work started and checked before release. | 1 | not defined: no security requirements link check was defined. |
| Each new system epic links a design review or threat model item. | 1 | not defined: no design review link check was defined. |
| Tickets of released changes are kept, not deleted, for at least 12 months. | 1 | not defined: no ticket retention check was defined. |

### On call and alerting (`alerting`)

Catalogue: pagerduty (Phase 2), slack (Phase 2).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `alerts.acknowledged_in_time` | Alerts are acknowledged in time | planned | none | betterstack P, pagerduty S |
| `alerts.incidents_resolved` | Incidents close with a timeline | planned | none | pagerduty S |
| `alerts.security_routed` | Security alerts page someone | planned | none | pagerduty S |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `alerts.escalation_policies_escalate` | Unanswered pages escalate | pagerduty S, slack N, betterstack P | LM-08 p |  |
| `alerts.incidents_registered` | Incidents in source tools are in the register | pagerduty S, slack N, jira S | LM-04 p, LM-07 p | `tickets.incidents_registered` |
| `alerts.on_call_covered` | Someone is on call at all times | pagerduty S, slack N, betterstack P | LM-08 p |  |
| `alerts.postmortems_completed` | Major incidents have a completed review | pagerduty P, slack N | LM-05 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| messages posted in the named security announcement channel in the period, with date, author and channel (Slack) | 2 | not defined: the Slack research keeps Slack to notifications and Verity never reads message content; operations-checks.md section 6 proposes a Verity notification delivery log instead. |
| Responders in each in scope on call schedule have at least one working contact method recorded. | 2 | not defined: no researcher defined a contact method check; alerts.on_call_covered leaves contact details to people. |

### Network and edge (`network_edge`)

Catalogue: cloudflare (Phase 2), tailscale (Phase 2).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `edge.minimum_tls` | Edge TLS is current | planned | none | cloudflare S |
| `edge.waf_enabled` | Web traffic is filtered | planned | none | cloudflare S, vercel P |
| `edge.zero_trust_access` | Private systems need a trusted device | planned | none | cloudflare P, tailscale P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `edge.access_policies_least_privilege` | Access rules name groups, not everyone | cloudflare S, tailscale S | NS-11 p, IAM-08 p |  |
| `edge.device_keys_expire` | Device access expires | tailscale S | NS-11 p, IAM-11 p |  |
| `edge.devices_verified` | Only approved devices connect | cloudflare P, tailscale S | NS-11 p |  |
| `edge.dnssec_enabled` | DNS answers are signed | cloudflare S | NS-02 p |  |
| `edge.hsts_enabled` | Browsers must use HTTPS | cloudflare S | NS-02 p |  |
| `edge.origin_locked` | Origins accept only edge traffic | cloudflare P | NS-10 p |  |
| `edge.origin_tls_verified` | Traffic to the origin is verified | cloudflare S | NS-02 p |  |
| `edge.policy_tests_defined` | The access policy tests its boundaries | tailscale S | NS-07 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Remote session logs are retained and exported. | 2 | not defined: no remote session log retention check was defined. |
| Secure web gateway policies block the named categories, and every enrolled device runs the gateway client. | 1 | not defined: no secure web gateway check was defined. |
| Every managed device runs the secure web gateway client, including newly enrolled ones. | 1 | not defined: no secure web gateway check was defined. |

### Observability (`observability`)

Catalogue: datadog (Phase 2), sentry (Phase 2), grafana (Phase 3), signoz (Phase 3), betterstack (Phase 3).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `observability.anomaly_monitors` | Unusual activity raises alerts | planned | none | datadog S, grafana S, sentry P, signoz P |
| `observability.capacity_trends` | Capacity trends are watched | planned | none | datadog S, grafana S, signoz P |
| `observability.logs_retained` | Logs are kept long enough | planned | none | datadog P, grafana P, signoz P |
| `observability.processing_monitored` | Processing failures are caught | planned | none | datadog P, grafana P, sentry P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `observability.audit_trail_enabled` | The monitoring tool records its own changes | datadog P, sentry N, grafana P | LM-02 p |  |
| `observability.errors_triaged_in_time` | Production errors are triaged in time | sentry S | SD-08 p |  |
| `observability.monitors_notify_on_call` | High priority alerts page someone | datadog S, sentry S, grafana S | LM-08 p, LM-09 p |  |
| `observability.production_services_monitored` | Production services are monitored | datadog S, sentry S, betterstack S | LM-09 p |  |
| `observability.security_signals_triaged` | Security signals are triaged in time | datadog S | LM-04 p, NS-05 p |  |
| `observability.siem_rules_enabled` | Detection rules are on and notify | datadog S | LM-09 p, LM-02 p, NS-05 p |  |
| `observability.silent_sources_alert` | A silent log source raises an alert | datadog S, grafana P | LM-02 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Each monitored host reports a clock offset within the allowed limit, and offsets beyond it raised an alert. | 1 | not defined: no clock offset check was defined. |
| Log timestamps from every source are stored in UTC or carry an offset. | 1 | not defined: no timestamp format check was defined. |
| Alert volume and alerts closed without action are counted per monitor for the quarter. | 1 | not defined: no alert volume check was defined. |

### Vulnerability scanner (`vulnerability_scanner`)

Catalogue: tenable (Phase 3), rapid7 (Phase 3), qualys (Phase 3).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `scanner.scans_current` | Systems are scanned monthly | planned | none | qualys S, rapid7 S, tenable S |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `scanner.authenticated_scans` | Servers get credentialed scans | tenable S, rapid7 P, qualys S | EP-04 p, LM-11 p, NS-13 p, LM-13 p |  |

### HR system (`hr_system`)

Catalogue: workday (not_planned), bamboohr (not_planned), rippling (not_planned), gusto (not_planned).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `people.joiners_onboarded` | Joiners get access through onboarding | planned | none | bamboohr S, entra P, gusto P, gws P, hibob S, okta P, rippling S, roster_import P, workday P |
| `people.leavers_deprovisioned` | Leavers lose access within a day | planned | none | bamboohr S, entra P, gusto P, gws P, hibob P, okta P, rippling S, roster_import P, workday P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `hr.background_checks_before_start` | Screening finished before start | bamboohr P, rippling N, workday P, gusto N | HR-01 p |  |
| `hr.contractors_have_end_dates` | Contractors have an end date | bamboohr P, rippling S, workday P, gusto P, hibob P | HR-03 p |  |
| `hr.roster_exported` | People list exports from the HR system | bamboohr S, rippling S, workday S, gusto S, hibob S, roster_import P | HR-05 p, HR-06 p, IAM-12 p, HR-01 p, EP-03 p, HR-03 p |  |
| `hr.training_current` | Security training is current | bamboohr S, rippling N, workday P, gusto N | HR-08 p |  |
| `people.accounts_match_roster` | Every account belongs to a current person | entra S, okta S, gws S | IAM-12 p, IAM-01 p, HR-03 p |  |
| `vault.leavers_removed` | Leavers lose password manager access | onepassword S | IAM-05 p, IAM-12 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| every active person on the HR roster has a Verity membership, so acknowledgement and training cover the whole staff | 13 | not defined: no check compares the HR roster with Verity members (13 entries rest on it). Needs a verity_members check on top of hr.roster_exported. |
| every active position has a job description, and the description has a security duties section | 3 | not defined: no job description check was defined. |
| agreements signed in the HR system for each person, with agreement type and date signed | 2 | not defined: hr-systems.md defines no agreement check. |
| an annual review cycle is configured for every employee group | 1 | not defined: no performance cycle check was defined. |
| every employee in post for the cycle has a completed performance review with reviewer and date | 1 | not defined: no performance review check was defined; the owner decided to keep review content out of Verity. |

### Device management (`device_management`)

Catalogue: jamf (not_planned), kandji (not_planned), intune (not_planned).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `devices.disk_encrypted` | Laptop disks are encrypted | planned | none | gws S, intune S, jamf S, kandji S |
| `devices.enrolled` | Laptops are managed | planned | none | gws P, intune S, jamf S, kandji S |
| `devices.os_current` | Operating systems are patched | planned | none | gws S, intune S, jamf S, kandji S |
| `devices.remote_wipe` | Lost laptops can be wiped | planned | none | gws P, intune S, jamf S, kandji S |
| `devices.screen_lock` | Screens lock when idle | planned | none | intune P, jamf P, kandji P |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `devices.assigned_to_active_staff` | Every company device belongs to a current person | intune S, jamf S, kandji S, gws S | EP-03 p, LM-01 p |  |
| `devices.firewall_enabled` | Laptop firewalls are on | intune P, jamf S, kandji S, gws P | EP-03 p |  |
| `devices.leaver_devices_recovered` | Leavers' devices come back or are wiped | intune P, jamf P, kandji P, gws P | EP-05 p, HR-05 p, HR-03 p |  |
| `devices.recovery_key_escrowed` | Disk recovery keys are held centrally | intune P, jamf S, kandji P, gws N | EP-02 p |  |
| `devices.removable_storage_restricted` | USB storage is blocked or restricted | intune N, jamf P, kandji P, gws N | DM-19 p |  |
| `devices.staff_have_managed_device` | Every person works on a managed device | intune S, jamf S, kandji S, gws P | EP-03 p |  |
| `devices.wipes_confirmed` | Wipes are confirmed, not assumed | intune P, jamf S, kandji P, gws P | EP-05 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Installed software outside the permitted list is reported per device. | 1 | not defined: no software allow list check was defined. |
| Devices out of the baseline are listed with the date found and fixed. | 1 | not defined: the device checks are point in time; a compliance history with fix dates is not defined. |

### Endpoint protection (`endpoint_protection`)

Catalogue: crowdstrike (not_planned), sentinelone (not_planned).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `endpoint.protection_active` | Endpoint protection is running | planned | none | crowdstrike S, defender_endpoint S, intune P, sentinelone S |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `endpoint.coverage_complete` | Every managed laptop runs the protection agent | defender_endpoint S, crowdstrike S, sentinelone S | EP-01 p |  |
| `endpoint.detections_triaged` | Endpoint alerts are handled in time | defender_endpoint S, crowdstrike S, sentinelone S | EP-01 p, LM-04 p |  |
| `endpoint.prevention_enabled` | Protection blocks, not only detects | defender_endpoint P, crowdstrike S, sentinelone P | EP-01 p |  |
| `endpoint.servers_covered` | Every server runs the protection agent | defender_endpoint S, crowdstrike S, sentinelone S | EP-01 p |  |

### CI and CD (`ci_cd`)

Catalogue: github (Phase 2), gitlab (Phase 2), bitbucket (Phase 2).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `ci.deployment_history_recorded` | Deployments are recorded | planned | none | bitbucket S, github S, gitlab S, heroku S, netlify P, qovery P, render P, vercel S |
| `ci.production_deploys_controlled` | Production deployments are controlled | planned | none | bitbucket S, github S, gitlab S, qovery P, vercel P |
| `ci.required_checks_passed` | Required checks passed before merge | planned | none | bitbucket S, github S, gitlab S |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `ci.production_deploys_approved` | Production releases were approved | github S, gitlab S, bitbucket N | SD-13 p, SD-12 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Running container images were rebuilt from a current base image within the set interval. | 1 | not defined: no base image age check was defined. |
| Container image scan results exist for every image pushed to the production registries in the period. | 1 | not defined: no registry image scanning check was defined. |
| Each production deployment was preceded by a successful deployment of the same commit to staging. | 1 | not defined: no promotion order check was defined. |
| Each release build produced a component list stored with the release. | 1 | not defined: no component list (SBOM) check was defined for SD-18. |

### Verity assets (`verity_assets`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.assets.classified` | Every asset in service is classified | running | verity | none |
| `verity.assets.disposal_recorded` | Assets taken out of service have a disposal record | running | verity | none |
| `verity.assets.owner_assigned` | Every active asset has an owner | running | verity | none |
| `verity.assets.reviewed` | Assets were reviewed on schedule | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.assets.data_stores_mapped` | Data stores carry what the data map needs | verity S | DM-06 p, DM-05 p, DM-09 p, DM-11 p, DM-12 p, DM-15 p, DM-16 p |  |
| `verity.assets.third_party_in_vendor_register` | Third party assets are linked to a vendor | verity S | BC-07 p, BC-08 p, LM-01 p |  |

### Verity vulnerabilities (`verity_vulnerabilities`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.vulns.kev_owned` | Known exploited vulnerabilities have an owner | running | verity | none |
| `verity.vulns.within_sla` | Vulnerabilities are fixed within the SLA | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.vulns.acceptances_approved` | Finding risk acceptances are approved and in date | verity S | LM-11 p, SD-03 p, SD-05 p, LM-12 p |  |
| `verity.vulns.assets_scanned` | In scope assets were scanned within the interval | verity S | LM-13 p, LM-11 p, SD-03 p |  |
| `verity.vulns.closed_within_sla` | Findings were fixed within SLA over the period | verity S | LM-11 p, SD-03 p, SD-05 p, LM-12 p |  |
| `verity.vulns.kev_triaged_same_day` | Known exploited findings are triaged the same day | verity S | LM-12 p, LM-11 p |  |
| `verity.vulns.pentest_fixes_verified` | Fixed penetration test findings were retested | verity S | GOV-16 p |  |
| `verity.vulns.pentest_in_12_months` | Penetration test in the last 12 months | verity S | GOV-16 p |  |
| `verity.vulns.triaged_in_time` | New findings are triaged in time | verity S | SD-03 p, LM-11 p, SD-02 p |  |

### Verity risk register (`verity_risks`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.risks.acceptance_current` | Risk acceptances are current | running | verity | none |
| `verity.risks.assessed_in_12_months` | Risks were assessed in the last 12 months | running | verity | none |
| `verity.risks.controls_linked` | Mitigated risks link to controls | running | verity | none |
| `verity.risks.reviewed` | Open risks are reviewed on schedule | running | verity | none |
| `verity.risks.treated` | Risks outside appetite are owned and treated | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.risks.acceptance_independent` | Risk acceptances approved by someone else, with reason and expiry | verity S | GOV-19 p, GOV-20 p, GOV-07 p, IAM-01 p, IAM-03 p, IAM-04 p, EP-02 p, EP-07 p, NS-04 p, NS-08 p, NS-13 p, NS-14 p | `verity.exceptions.in_force` |
| `verity.risks.fraud_assessed` | Fraud and insider risk assessed and linked to controls | verity S | GOV-12 p |  |
| `verity.risks.reviewed_after_change` | Risks reviewed after changes Verity sees | verity S | GOV-03 p |  |
| `verity.risks.scope_covered` | Risk assessment reaches the declared scope | verity S | GOV-18 p |  |
| `verity.risks.treatment_planned` | Mitigated risks have an owned, dated plan | verity S | GOV-20 p, GOV-12 p |  |

### Verity vendors (`verity_vendors`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.vendors.assessed_in_cadence` | Critical vendors are assessed on schedule | running | verity | none |
| `verity.vendors.dpa_on_file` | Vendors that hold personal data have a DPA | running | verity | none |
| `verity.vendors.owner_and_tier` | Vendors have an owner and a tier | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.vendors.assurance_report_reviewed` | Critical vendors' assurance reports are current and reviewed | verity S | BC-08 p, PE-01 p | `verity.vendors.assurance_reviewed` |
| `verity.vendors.breach_terms_recorded` | Vendor contracts state breach notice hours | verity S | DM-17 p, DM-10 p |  |
| `verity.vendors.contractors_bounded` | Contractor engagements have sponsor, dates and systems | verity S | HR-03 p |  |
| `verity.vendors.discovered_apps_triaged` | Discovered applications have a decision | verity S | BC-05 p |  |
| `verity.vendors.findings_in_sla` | Vendor findings are handled within their timeframe | verity S | BC-08 p |  |
| `verity.vendors.offboarding_complete` | Departed vendors were offboarded | verity S | BC-07 p |  |
| `verity.vendors.personal_data_recorded` | Vendors that receive personal data are fully recorded | verity S | DM-09 p, DM-06 p, DM-11 p, DM-15 p |  |
| `verity.vendors.security_terms_on_file` | Critical and high vendors have security terms | verity S | BC-08 p, BC-10 p |  |
| `verity.vendors.service_levels_measured` | Critical vendors' service levels are measured | verity S | BC-08 p |  |
| `verity.vendors.subprocessor_list_current` | Subprocessor list matches the vendor register | verity S | BC-06 p |  |

### Verity policies (`verity_policies`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.communication.plan_documented` | A security communication plan is in force | running | verity | none |
| `verity.competence.documented` | Competence requirements are documented | running | verity | none |
| `verity.context.documented` | The context of the organization is documented | running | verity | none |
| `verity.documents.controlled` | Published documents are controlled | running | verity | none |
| `verity.interested_parties.documented` | Interested parties and their requirements are documented | running | verity | none |
| `verity.isms.scope_documented` | A current scope statement is in force | running | verity | none |
| `verity.objectives.documented` | Security objectives are documented | running | verity | none |
| `verity.policies.acknowledged` | Staff acknowledged current policies | running | verity | none |
| `verity.policies.reviewed` | Required policies are published and current | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.documents.required_present` | Every required document exists and is current | verity S | GOV-17 p, GOV-28 p, GOV-32 p |  |
| `verity.policies.acknowledged_at_join` | Joiners acknowledge all staff documents soon after joining | verity S | GOV-04 p, HR-06 p, CS-04 p, HR-03 p |  |
| `verity.policies.major_change_campaigned` | Major policy changes re-acknowledged by staff | verity S | CS-04 p, CS-06 p |  |
| `verity.training.acknowledged` | In house training acknowledged by members | verity S | HR-08 p |  |

### Verity tasks (`verity_tasks`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.tasks.remediation_in_sla` | Remediation tasks are within SLA | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.incidents.postmortem_recorded` | Significant incidents have a postmortem and actions | verity S | LM-05 p |  |
| `verity.incidents.registered` | Incidents are registered with the required facts | verity S | LM-07 p, LM-04 p, SD-11 p, SD-16 p, LM-05 p, LM-06 p |  |
| `verity.tasks.approved_before_done` | Requests are approved before they are done | verity S | IAM-01 p, DM-12 p, IAM-08 p, SD-17 p, SD-04 p, SD-18 p, SD-01 p | `verity.tasks.change_approved_independently` |
| `verity.tasks.capa_on_time` | Corrective actions close on time | verity S | LM-05 p, LM-10 p, BC-02 p, BC-03 p, SD-15 p |  |
| `verity.tasks.checklist_steps_done` | Joiner, leaver and contractor checklists finished on time | verity S | HR-05 p, HR-06 p, HR-03 p |  |
| `verity.tasks.closure_evidenced` | Closed compliance tasks carry proof | verity S | GOV-08 p, GOV-20 p, GOV-30 p, GOV-12 p |  |
| `verity.tasks.incident_notice_decided` | Every incident has a recorded notice decision | verity S | DM-01 p, DM-02 p, DM-17 p |  |
| `verity.tasks.owned_and_dated` | Compliance tasks have an owner and a due date | verity S | GOV-08 p, GOV-15 p, GOV-30 p, GOV-14 p, HR-09 p |  |
| `verity.tasks.privacy_requests_on_time` | Privacy requests are answered on time | verity S | DM-03 p, DM-05 p, DM-11 p, DM-14 p, DM-16 p |  |
| `verity.tasks.recurring_done_on_time` | Recurring compliance work is done on time | verity S | CS-07 p, CS-08 p, GOV-02 p, GOV-10 p, GOV-21 p, GOV-24 p, GOV-29 p, IAM-02 p, IAM-07 p, IAM-09 p, IAM-10 p, IAM-13 p, NS-03 p, NS-04 p, NS-05 p, NS-06 p, NS-07 p, NS-10 p, NS-12 p, NS-14 p, EP-07 p, DM-02 p, DM-06 p, DM-07 p, DM-19 p, PE-02 p, PE-03 p, IAM-01 p, NS-11 p, LM-02 p, LM-09 p, LM-12 p, BC-04 p, BC-05 p, BC-07 p, SD-14 p, BC-02 p, BC-03 p, LM-10 p, SD-17 p, BC-09 p | `verity.tasks.reviews_on_cadence`, `verity.tasks.recurring_review_on_time` |

### Verity controls and evidence (`verity_controls`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.audit.internal_in_12_months` | An internal audit was held in the last 12 months | running | verity | none |
| `verity.controls.owned` | Every control has an owner | running | verity | none |
| `verity.evidence.current` | Controls rely on current evidence | running | verity | none |
| `verity.management_review.in_12_months` | A management review was held in the last 12 months | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.assurance.findings_tracked` | Assurance findings are owned, dated and tracked | verity S | GOV-13 p, GOV-08 p, GOV-30 p |  |
| `verity.assurance.internal_audit_held` | Internal audit held independently in the last 12 months | verity S | GOV-13 p |  |
| `verity.assurance.management_review_held` | Management review held each quarter | verity S | GOV-15 p, GOV-19 p |  |
| `verity.assurance.management_review_inputs_recorded` | Yearly management review took every set input | verity S | GOV-31 p, GOV-15 p |  |
| `verity.checks.runs_continuous` | Automated checks ran without gaps | verity S | GOV-06 p |  |
| `verity.controls.failed_checks_tracked` | Failed checks raised as owned tasks | verity S | GOV-06 p |  |

### Verity frameworks (`verity_frameworks`)

Catalogue: verity (available).

Shipped checks:

| Check | Name | Status | Runs on today | Providers the research adds |
|---|---|---|---|---|
| `verity.isms.scope_recorded` | The management system scope is recorded | running | verity | none |
| `verity.soa.complete` | Statement of Applicability is decided and reviewed | running | verity | none |

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.commitments.owned_and_mapped` | Commitments registered, owned and mapped | verity S | CS-02 p, GOV-22 p, GOV-05 p, CS-01 p |  |
| `verity.engagement.subservice_listed` | Critical suppliers accounted for in the SOC 2 engagement | verity S | GOV-22 p |  |
| `verity.isms.scope_approved` | ISMS scope approved and unchanged since | verity S | GOV-23 p |  |
| `verity.programme.periodic_on_track` | Periodic activities on schedule for the audit period | verity S | GOV-29 p |  |
| `verity.regulations.decided` | Regulations the profile points to are decided | verity S | GOV-05 p |  |
| `verity.scope.items_decided` | Scope suggestions and items are decided | verity S | GOV-14 p, GOV-23 p, GOV-22 p |  |
| `verity.soa.matches_risk_treatment` | Applicability agrees with risk treatment | verity S | GOV-27 p |  |
| `verity.soa.version_approved` | Statement of Applicability version approved and unchanged | verity S | GOV-27 p |  |

### Business applications (proposed capability) (`business_applications`)

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `apps.api_keys_current` | Application API keys are owned and in use | sendgrid P, resend P, openai S, anthropic P | IAM-10 p |  |
| `apps.members_active_in_directory` | Application members are current staff | notion P, vercel S, supabase S, hubspot S, intercom S, zendesk S, posthog S, sendgrid S, openai S, anthropic S, digitalocean N, tailscale S | IAM-12 p, HR-03 p, NS-11 p | `edge.members_current` |
| `apps.mfa_enforced` | Application members use two factor | supabase S, zendesk S, posthog S, digitalocean N | IAM-03 p |  |
| `apps.sso_enforced` | Application requires company sign in | vercel P | IAM-04 p |  |

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| Withdrawals in the consent tool are listed with the time processing stopped. | 1 | not defined: no consent management tool was researched. |
| Consent records from the consent tool carry person or ID, time, purpose, notice version and capture method. | 1 | not defined: no consent management tool was researched. |
| Chat and file sharing tools restrict external sharing as the rules set. | 1 | not defined: no sharing settings check was defined for chat or file tools. |

### Ai providers (proposed capability) (`ai_providers`)

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `ai.retention_matches_review` | AI data retention matches the review | openai S, anthropic N | BC-08 p, DM-08 p |  |
| `ai.usage_attributed` | AI usage is known and owned | openai S, anthropic S | BC-05 p, DM-12 p |  |

### Learning platform (proposed capability) (`learning_platform`)

Unresolved needs:

| Need | Entries | Reason |
|---|---|---|
| overdue assignments with each reminder sent and the date of escalation | 4 | not defined: no reminder and escalation check was defined. |
| the courses assigned in the period, with topics, audience and due rule | 2 | not defined: no course assignment export check was defined. |

### Verity identity (proposed capability) (`verity_identity`)

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.identity.leavers_removed_by_sync` | Leavers at the identity provider lose Verity access | verity S | IAM-12 p, IAM-11 p |  |
| `verity.identity.roles_from_groups` | Verity roles come from identity provider groups | verity S | IAM-08 p, IAM-07 p, IAM-01 p, IAM-03 p, IAM-09 p, IAM-10 p |  |
| `verity.identity.second_factor_on_sign_in` | Sign ins to Verity used a second factor | verity S | IAM-03 p |  |
| `verity.identity.sign_in_settings` | Verity's own sign in settings meet the standard | verity S | IAM-06 p, IAM-11 p |  |
| `verity.identity.sso_required` | Verity sign in goes through the identity provider | verity S | IAM-04 p, IAM-12 p |  |

### Verity members (proposed capability) (`verity_members`)

Proposed checks:

| Check | Name | Providers | Controls | Aliases |
|---|---|---|---|---|
| `verity.members.leaver_ownership_moved` | Leavers' compliance records handed over | verity S | GOV-09 p, HR-05 p |  |
| `verity.members.owner_functions_held` | Security owner functions are held without a gap | verity S | GOV-10 p, GOV-21 p, HR-09 p |  |

## 5.4 Aliases resolved

Where researchers wrote the same predicate under different keys, one key stays and the others are recorded as
aliases (they are never created). Canonical keys that are shipped checks are extended in
`checks-proposed.json` under `existing_check_extensions`.

| Alias | Canonical key | Why |
|---|---|---|
| `cloud.access_list_exported` | `idp.access_list_exported` (shipped) | Same predicate (the complete, dated list of accounts and roles was read for every in scope account) on cloud infrastructure. |
| `vcs.access_list_exported` | `idp.access_list_exported` (shipped) | Same predicate on version control (members, owners, outside collaborators, repository admins). |
| `apps.access_list_exported` | `idp.access_list_exported` (shipped) | Same predicate on a business application (members, guests, pending invites). |
| `apps.admins_limited` | `idp.admins_limited` (shipped) | Same predicate as idp.admins_limited (admin roles held only by named, approved people) on a business application. |
| `tickets.incidents_registered` | `alerts.incidents_registered` | Same reconciliation (every incident in a source tool is in the Verity register or has a not an incident decision) from a ticketing source. Kept the alerting key, as the operations research recommended: incidents are the native object there. |
| `edge.members_current` | `apps.members_active_in_directory` | Same predicate (every active member of a tool is an active identity provider user, or a recorded external or service member) on the remote access tool. apps.members_active_in_directory is the more general wording. |
| `verity.exceptions.in_force` | `verity.risks.acceptance_independent` | Same records and predicate (risk acceptances approved by someone other than the requester, with a reason and an expiry) for acceptances recorded as exceptions to a control. When the check runs for a control, the population is that control's exceptions. |
| `verity.tasks.change_approved_independently` | `verity.tasks.approved_before_done` | Same predicate (a task from a template that requires approval was approved by an active member who is neither its owner nor an assignee) for change templates. The timing rule (before work, before resolution, or within a window after an emergency change) becomes a template setting. |
| `verity.tasks.reviews_on_cadence` | `verity.tasks.recurring_done_on_time` | Three researchers wrote the same predicate on recurring task series linked to a control. Kept the most general key; approval where the template requires it is folded in. |
| `verity.tasks.recurring_review_on_time` | `verity.tasks.recurring_done_on_time` | Same predicate on recurring task series; its per cadence grace (2, 7, 30 days) becomes the default grace parameter. |
| `verity.vendors.assurance_reviewed` | `verity.vendors.assurance_report_reviewed` | Same predicate (a current assurance report reviewed by a named person within 12 months, customer controls marked reviewed) on hosting providers linked to PE-01. Population widened to critical vendors plus vendors linked to a control as a hosting provider. |

## 5.5 Similar keys kept apart

These look alike but read a different source, population or predicate, so they stay separate checks.

| Check | Related to | Why kept apart |
|---|---|---|
| `idp.no_inactive_accounts` | `cloud.unused_credentials_disabled` | User accounts against cloud passwords and access keys. |
| `vault.leavers_removed` | `people.leavers_deprovisioned` | Same leaver population and removal time, on the password manager instead of the identity provider. |
| `hr.training_current` | `verity.training.acknowledged` | Training in the HR system against in house material acknowledged in Verity. |
| `cloud.human_users_mfa` | `idp.mfa_enforced` | Local cloud users outside the identity provider; root is its own check. |
| `cloud.human_users_mfa` | `cloud.root_account_mfa` | Local cloud users outside the identity provider; root is its own check. |
| `cloud.secrets_rotated` | `cloud.secrets_managed` | Different population, age limit and controls. |
| `cloud.secrets_rotated` | `cloud.machine_credentials_rotated` | Different population, age limit and controls. |
| `vcs.dependency_alerts_within_sla` | `verity.vulns.within_sla` | Owner decision D-GH-2: judge alerts in GitHub now, import them into the register later. |
| `ci.production_deploys_approved` | `ci.production_deploys_controlled` | Practice per deployment against the setting. |
| `alerts.incidents_registered` | `verity.incidents.registered` | Facts in each register entry, against completeness of the register against a source tool. |
| `alerts.postmortems_completed` | `verity.incidents.postmortem_recorded` | Same aim, different record: the postmortem in Verity Tasks with actions, against the review status in the on call tool. |
| `apps.mfa_enforced` | `idp.mfa_enforced` | Accepts per member two factor, which a policy check does not. |
| `apps.mfa_enforced` | `vcs.org_two_factor_required` | Accepts per member two factor, which a policy check does not. |
| `apps.sso_enforced` | `idp.sso_enforced` | Read from the application side, which an identity provider cannot see. |
| `verity.assurance.findings_tracked` | `verity.tasks.capa_on_time` | Different populations: corrective actions of issues and incidents, assurance findings, all linked tasks. |
| `verity.assurance.internal_audit_held` | `verity.audit.internal_in_12_months` | Adds independence of the performer. |
| `verity.assurance.management_review_held` | `verity.management_review.in_12_months` | Quarterly cadence; the 12 month check moves to GOV-31. |
| `verity.policies.acknowledged_at_join` | `verity.policies.acknowledged` | Joiners within days of joining, against the annual population. |
| `verity.risks.acceptance_independent` | `verity.vulns.acceptances_approved` | Finding acceptances in Vulnerabilities, not risk acceptances. |
| `verity.risks.acceptance_independent` | `verity.risks.acceptance_current` | Independence, reason and expiry, against an acceptance in date. |
| `verity.tasks.capa_on_time` | `verity.tasks.remediation_in_sla` | Different populations: corrective actions of issues and incidents, assurance findings, all linked tasks. |
| `verity.tasks.capa_on_time` | `verity.tasks.owned_and_dated` | Different populations: corrective actions of issues and incidents, assurance findings, all linked tasks. |
| `verity.tasks.checklist_steps_done` | `people.joiners_onboarded` | Checklist steps in Verity against accounts created at the identity provider. |
| `verity.vendors.breach_terms_recorded` | `verity.vendors.security_terms_on_file` | Vendors holding personal data and the breach notice field only, against critical and high vendors and every security term. |
| `verity.vendors.personal_data_recorded` | `verity.vendors.subprocessor_list_current` | The record fields, against the published list matching them. |
| `verity.vulns.assets_scanned` | `scanner.scans_current` | Same aim from a different source: Verity's register of imported scans against Assets, versus the scanner's own history. Kept apart; the scan interval default conflicts (92 against 30 days) and goes to the owner. |
| `verity.vulns.closed_within_sla` | `verity.vulns.within_sla` | Period view of fixes made, against the state of open findings now. |
| `verity.vulns.kev_triaged_same_day` | `verity.vulns.kev_owned` | Triage time against ownership; share the triage logic. |

## 5.6 Needs resolution

Every `NEED <capability>: <predicate>` in `coverage/*.json` was matched to a check key or marked unresolved. Per
entry detail: [coverage/needs-resolution.json](coverage/needs-resolution.json).

| Match | Entries | Distinct predicates |
|---|---|---|
| exact | 83 | 53 |
| partial | 141 | 90 |
| unresolved | 93 | 59 |
| total | 317 | 202 |

Resolved entries point at a shipped check 100 times and at a proposed check 124 times.
Unresolved: 90 because no researcher defined a check, 3 because no researched provider can collect it.

| Capability | Exact | Partial | Unresolved |
|---|---|---|---|
| `alerting` | 3 | 2 | 4 |
| `background_screening` | 0 | 1 | 0 |
| `business_applications` | 0 | 12 | 3 |
| `ci_cd` | 3 | 5 | 4 |
| `cloud_infrastructure` | 14 | 30 | 12 |
| `device_management` | 5 | 9 | 2 |
| `endpoint_protection` | 2 | 2 | 0 |
| `esignature` | 0 | 0 | 2 |
| `hr_system` | 18 | 5 | 20 |
| `identity_provider` | 7 | 22 | 10 |
| `learning_platform` | 4 | 2 | 6 |
| `network_edge` | 5 | 2 | 4 |
| `observability` | 1 | 12 | 3 |
| `password_manager` | 1 | 0 | 8 |
| `public_web` | 0 | 0 | 3 |
| `ticketing` | 2 | 28 | 3 |
| `version_control` | 18 | 7 | 9 |
| `vulnerability_scanner` | 0 | 2 | 0 |

The largest unresolved need: "every active person on the HR roster has a Verity membership" (13 entries). No
check compares a roster with Verity members, so acknowledgement and training checks only ever see members. It
needs a `verity_members` check on top of `hr.roster_exported`, and the roster source decision (08, people topic).

A partial match never satisfies an artifact on its own under rule A; it is listed so the reconciliation step adds
the check as a source with `fills: partial`.

## 5.7 Coverage downgrades

Every proposal to move a mapping from full to partial, gathered from all documents. All 16 full links from a check
to a control in `checks.json` are proposed for partial: no connector check proves a whole control.

| Check | Control | Reason | Raised in |
|---|---|---|---|
| `cloud.encryption_at_rest` | NS-01 | The encryption standard, the key type per data class (NS-01.C) and the 'fixed and recorded' half of NS-01.D need people. Default encryption on S3, Azure Storage and Google Cloud shows no customer decision. | connectors/aws.md (5.1, D-AWS-4); connectors/azure.md (5.1, D-AZ-4); connectors/gcp.md (5.1, D-GCP-3); coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `cloud.admin_ports_closed` | NS-08 | NS-08.D, the alert on opening an admin port and the approved route for admin access, are not shown by the rule reading. | connectors/aws.md (5.1, D-AWS-4); connectors/azure.md (5.1, D-AZ-4); connectors/gcp.md (5.1, D-GCP-3); connectors/phase3-catalogue.md 4.1, 4.6, 4.7; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `cloud.config_changes_recorded` | LM-03 | Investigation of each alert (LM-03.C) is a person's record; alerting is also only partly covered on every cloud. | connectors/aws.md (5.1, D-AWS-4); connectors/azure.md (5.1, D-AZ-4); connectors/gcp.md (5.1, D-GCP-3) |
| `cloud.environments_separated` | SD-12 | Production access limits (SD-12.C) and the promotion order (SD-12.D) are not shown; the check only reads the customer's environment roles per account, subscription or project. | connectors/aws.md (5.1, D-AWS-4); connectors/azure.md (5.1, D-AZ-4); connectors/gcp.md (5.1, D-GCP-3); connectors/phase3-catalogue.md 4.1, 4.2, 4.4, 4.6, 4.7, 4.8 |
| `devices.enrolled` | EP-03 | EP-03 has a design objective and operating objectives no device check proves. New rationale: shows each device the MDM knows is managed and in contact; devices never enrolled, enrolment before issue and the policy are evidenced separately. Not implemented, so no workspace's readiness changes. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2); mdm-and-endpoint-strategy.md sections 4 (F4) and 5.2; decision D-DEV-4 |
| `devices.disk_encrypted` | EP-02 | New rationale: shows each managed device is encrypted; key escrow, checks before issue and approved exceptions are evidenced separately. Not implemented, so no readiness changes. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2); mdm-and-endpoint-strategy.md sections 4 (F4) and 5.2; decision D-DEV-4 |
| `devices.screen_lock` | EP-06 | New rationale: shows the lock is enforced at or under the limit; the standard and fixes are evidenced separately. Not implemented, so no readiness changes. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2); mdm-and-endpoint-strategy.md sections 4 (F4) and 5.2; decision D-DEV-4 |
| `endpoint.protection_active` | EP-01 | New rationale: shows each sensor is healthy and current; devices without a sensor, prevention settings and alert handling are separate checks. Not implemented, so no readiness changes. | coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2); mdm-and-endpoint-strategy.md sections 4 (F4) and 5.2; decision D-DEV-4 |
| `idp.sso_enforced` | IAM-04 | An identity provider sees only apps connected to it. IAM-04.B needs the vendor register compared, and IAM-04.C needs approved exceptions. | connectors/identity-checks.md section 5; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `idp.password_policy` | IAM-06 | Settings cannot show passwords were changed after an exposure (IAM-06.D). On Entra the length rule is fixed by Microsoft; Google has no lockout setting. | connectors/identity-checks.md section 5; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `idp.session_timeout` | IAM-11 | Settings do not show re-authentication for high risk actions (IAM-11.C) or that sign out ends refresh tokens (IAM-11.D). Entra and Google have no idle timeout. | connectors/identity-checks.md section 5; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `people.leavers_deprovisioned` | IAM-12 | Disabling the identity provider account does not prove access to systems outside single sign on was removed (IAM-12.D). | connectors/identity-checks.md section 5; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `vault.everyone_enrolled` | IAM-05 | Membership does not show shared credentials are kept in team vaults (IAM-05.C). | connectors/identity-checks.md section 5; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `tickets.access_requests_approved` | IAM-01 | It does not show that privileged grants were approved by the system owner (IAM-01.D), that each person has their own account (IAM-01.E), or that every system's grants were seen (IAM-01.B needs every in scope system connected). | connectors/operations-checks.md section 2; operations owner decision 4; connectors/phase3-catalogue.md 3.4; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `edge.zero_trust_access` | NS-11 | An edge or tailnet can show a system sits behind it, not that there is no other route in (cloud ingress, a public IP). NS-11.C (members match staff) and NS-11.D (sessions logged and reviewed) also remain. | connectors/operations-checks.md section 2; operations owner decision 4; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |
| `edge.waf_enabled` | NS-10 | NS-10.C (origin refuses traffic that bypasses the firewall) and NS-10.D (quarterly rule review) are not shown by the firewall settings. | connectors/operations-checks.md section 2; operations owner decision 4; connectors/phase3-catalogue.md 4.4; coverage/iam-ep-pe-ns-dm.md (Gaps and content problems found, rows 1 and 2) |

Requirement to control mappings proposed to move from full to partial (they change framework status and need
the qualified reviewer, FW-5):

| Requirement | Control | Reason | Raised in |
|---|---|---|---|
| SOC2:CC6.3 | IAM-02 | Two full links (IAM-02, IAM-08) cannot both be true; neither alone authorizes, changes and removes access. Needs FW-5 reviewer sign off. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes, Mapping changes); coverage/iam-ep-pe-ns-dm.controls.json |
| SOC2:CC6.3 | IAM-08 | Two full links (IAM-02, IAM-08) cannot both be true; neither alone authorizes, changes and removes access. Needs FW-5 reviewer sign off. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes, Mapping changes); coverage/iam-ep-pe-ns-dm.controls.json |
| ISO27001:A.5.3 | IAM-09 | Finance and payment duties move to the proposed IAM-13 (partial there). Needs FW-5 reviewer sign off. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes, Mapping changes); coverage/iam-ep-pe-ns-dm.controls.json |
| ISO27001:A.8.23 | EP-07 | Server outbound limits (EP-07.C) move to NS-03 as NS-03.E; NS-03 gains a partial A.8.23 link. Needs FW-5 reviewer sign off. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes, Mapping changes); coverage/iam-ep-pe-ns-dm.controls.json |
| ISO27001:A.8.9 | NS-04 | Network equipment moves to the proposed NS-14 (partial there). Needs FW-5 reviewer sign off. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes, Mapping changes); coverage/iam-ep-pe-ns-dm.controls.json |
| SOC2:C1.2 | DM-16 | Equipment wiping moves to the proposed EP-08 (partial there). Needs FW-5 reviewer sign off. | coverage/iam-ep-pe-ns-dm.md (Proposed control changes, Mapping changes); coverage/iam-ep-pe-ns-dm.controls.json |
| SOC2:CC7.1 | LM-11 | LM-11 keeps the register, triage, remediation times and risk acceptance. Discovery coverage moves to the proposed LM-13, so LM-11 alone no longer covers the whole criterion. Offered with an audit row; needs the owner's go and the reviewer's sign off because it changes framework readiness. | coverage/sd-lm-bc.md (Mapping changes) |
| ISO27001:A.8.8 | LM-11 | Same split: evaluating and treating weaknesses stays on LM-11, finding them across the estate moves to LM-13. Needs the owner's go and the reviewer's sign off. | coverage/sd-lm-bc.md (Mapping changes) |

Requirements that leave a control for a successor at the same coverage (not a loss, listed because readiness
moves with them):

| Requirement | From | Change | Raised in |
|---|---|---|---|
| ISO27001:A.5.6 | CS-07 | removed: Moves to CS-08; CS-07 keeps authority contacts (A.5.5). Not a loss of coverage: the requirement maps full to the proposed successor CS-08 instead, once the owner accepts the split. | coverage/gov-cs-hr.md Proposed control changes |
| ISO27001:9.3.1 | GOV-15 | removed: The yearly review by top management moves to GOV-31. Not a loss of coverage: the requirement maps full to the proposed successor GOV-31 instead, once the owner accepts the split. | coverage/gov-cs-hr.md Proposed control changes |
| ISO27001:9.3.2 | GOV-15 | removed: As above. Not a loss of coverage: the requirement maps full to the proposed successor GOV-31 instead, once the owner accepts the split. | coverage/gov-cs-hr.md Proposed control changes |
| ISO27001:9.3.3 | GOV-15 | removed: As above. Not a loss of coverage: the requirement maps full to the proposed successor GOV-31 instead, once the owner accepts the split. | coverage/gov-cs-hr.md Proposed control changes |
| ISO27001:A.8.14 | BC-03 | removed (moves to BC-09 as full): Not a full to partial change, listed because it changes readiness: A.8.14 leaves BC-03 for the proposed BC-09 with the redundancy record and failover test. Moves with an audit row; needs the owner's go and the reviewer's sign off. | coverage/sd-lm-bc.md (Mapping changes; What existing workspaces need) |

More requirement mapping changes (adds, removals, the DM-03 raise) are in [06-control-changes.md](06-control-changes.md).

## 5.8 Checks that fill no artifact

A check that no artifact names cannot move an objective (01-evidence-model.md 1.2).

- Shipped checks named by no artifact in `artifacts.json` today: 47. After the coverage plan, the needs
  resolution and the extensions are applied: 0.
- Proposed checks with no artifact: 2: `devices.firewall_enabled`, `edge.dnssec_enabled`. Each needs an artifact or should be dropped.

## 5.9 Conflicts resolved

| Conflict | Resolution |
|---|---|
| `tickets.incidents_registered` and `alerts.incidents_registered` test one reconciliation from two tools; the drafts disagreed on the empty population (insufficient against pass) | One key, `alerts.incidents_registered`, capabilities alerting and ticketing with capability_match each, requires `verity_tasks`. Empty population passes only when the source returned the complete list for the period, otherwise insufficient information (rule 4) |
| Three access list keys (`cloud.`, `vcs.`, `apps.access_list_exported`) and the shipped `idp.access_list_exported`; the cloud and code research asked to keep one key per capability so an identity provider list cannot stand in for the code host list | Folded into the shipped `idp.access_list_exported` (AUTHORING: reuse a key whose meaning fits), with capability_match each so every connected system must produce its own complete list. Control mappings were inconsistent (IAM-02 only; IAM-02, 07, 12; IAM-02, 09): the union is kept, each partial with its own rationale |
| `apps.admins_limited` repeats the shipped `idp.admins_limited` | Folded into `idp.admins_limited` with capability_match each |
| `edge.members_current` (operations) and `apps.members_active_in_directory` (phase 3) | One key, `apps.members_active_in_directory`, capabilities business_applications and network_edge, requires identity_provider |
| Three recurring task keys from three researchers; grace 14 days for every cadence against 2, 7 and 30 days by cadence; one added approval | One key, `verity.tasks.recurring_done_on_time`, grace by cadence as the default, approval where the template requires it |
| Two vendor assurance review keys on different populations (hosting providers on PE-01, critical vendors on BC-08) | One key, `verity.vendors.assurance_report_reviewed`, population is the union |
| `verity.tasks.change_approved_independently` and `verity.tasks.approved_before_done` | One key, `verity.tasks.approved_before_done`; the timing rule becomes a template setting |
| `verity.exceptions.in_force` and `verity.risks.acceptance_independent` read the same risk acceptances | One key, `verity.risks.acceptance_independent`; for a control, the population is that control's exceptions |
| Two proposed artifacts for LM-02.C: `log-retention-settings` (operations) and `log-store-retention-and-access-settings` (SD, LM, BC mapping, which also splits the objective) | Keep `log-store-retention-and-access-settings`; the other is its alias |
| Capability names: `business_application` against `business_applications`; `security_training` against `learning_platform` | `business_applications` and `learning_platform`, the names the coverage NEEDs already use |
| Scanners listed as implementations of `verity.vulns.within_sla` and `verity.vulns.kev_owned` | Recorded as feeding the vulnerability register (`fed_by`), not as implementations: the check reads the register |
| 1Password on `idp.access_list_exported` and `idp.sso_enforced`, Intune on `endpoint.protection_active`, outside the check's capability | password_manager and device_management added to those checks with capability_match each |
| Scan interval: `scanner.scans_current` 30 days, LM-13.B quarterly, `verity.vulns.assets_scanned` 92 days | Both keys kept (different sources); the default goes to the owner (08) |
| `evidence-logs-are-reviewed`: the AWS research adds `cloud.audit_logging` and `cloud.flow_logs_enabled`, the Azure research keeps it with people | Added as partial sources: under rule A they show the logs exist and never satisfy the review alone |
| `scanner.scans_current` and `verity.vulns.within_sla` after the EP-04 split: the IAM file says both move to NS-13 and also that they stay | Move to NS-13, as the IAM researcher recommends (EP-04 becomes company devices only). `scanner.scans_current` also moves from LM-11 to LM-13 (SD, LM, BC file) |
| `verity.vulns.assets_scanned` was listed as an alias of `scanner.scans_current` | Kept apart (5.5): one reads Verity's register, the other the scanner |
| Slack listed under `alerting` | Proposed to leave alerting; it implements no check (operations decision 2) |
| Azure research recommends one shared multi tenant app; Entra and unified setup research recommend customer owned evidence apps first | Not resolved here: an owner decision (08, credentials topic) |
