# Phase 3 connector catalogue (everything except Azure and Google Cloud)

Researched 2026-11-23 for the Phase 3 list in `docs/architecture/integrations.md`. Azure and Google
Cloud have full documents: [azure.md](azure.md) and [gcp.md](gcp.md). This file gives every other Phase 3
provider one section: what it is for, what it proves (said plainly when the answer is "little"), how to
connect with the least access, what Verity reads, which checks it implements, the controls touched and
the customer setup notes. A full connector document per provider is written when the owner schedules it.

Nothing here edits content JSON or code (AUTHORING rule 8). New keys and capabilities are proposals for
the reconciliation step. Facts carry a source number ([P1] ...) from section 10; "unverified" marks what
this round could not confirm on an official page. The web search budget ran out part way through, so
competitor practice was not researched for these providers (section 9).

## 1. How to read this file

- **Owned prefixes.** This round owns `scanner.`, `apps.` and `ai.`. Everything else reuses existing
  keys (`checks.json`), keys proposed by other research rounds ([aws.md](aws.md) for `cloud.`,
  [operations-checks.md](operations-checks.md) for `tickets.`, `alerts.`, `observability.`, `edge.`), or is
  written as a `NEED`.
- **Feasibility codes.** S supported, P partial (the reason follows), N not possible, n/a not about this
  provider.
- **Shared rules.** Every check follows rules 1 to 7 of `01-evidence-model.md`: the `person` source stays,
  population before predicate, empty is not proof, a missing permission or an unread page is `error` or
  `insufficient_information`, never `fail` and never `pass`.

### 1.1 Capability changes proposed

| Change | Why |
|---|---|
| NEW capability `business_applications`: "A software service staff sign in to that holds company or customer data" | The coverage files already raise needs against `business_applications` (for example `data-inventory-and-data-map`), and operations research handed over two needs for it (admin role exports, second factor per member, [operations-checks.md](operations-checks.md) section 6). The `apps.*` checks below are written against it. Providers: every SaaS in this file that exposes its members, including the platforms in section 4 |
| NEW capability `ai_providers`: "A service that runs AI models on company data" | Providers OpenAI and Anthropic. The `ai.*` checks are written against it |
| Add `tenable`, `rapid7`, `qualys` to `asset_discovery` | A scanner knows which hosts exist and when it last saw them, which `assets.resources_registered` needs |
| Add `betterstack` and `grafana` to `alerting` | Both run on call schedules and escalation (Better Stack on call calendars; Grafana's on call product is unverified this round) |
| Keep `notion` in `ticketing` only as P, or move it to `business_applications` | Notion has no ticket model; a ticket check needs the customer to map a database (section 3.5). Decision D-P3-5 |
| Providers in section 4 also join `business_applications` and, where they deploy code, `ci_cd` | Vercel, Netlify, Render, Heroku and Qovery hold the deployment history `ci.*` checks read |

## 2. New checks owned by this round

Shape follows `checks.json` and the definition tables in [identity-checks.md](identity-checks.md).
`implementations` stays empty until a collector ships.

### 2.1 Vulnerability scanner (`scanner.`)

`scanner.scans_current` already exists (LM-11 partial, EP-04 partial). Its definition is made precise
here so all three scanners mean the same thing:

| Field | `scanner.scans_current` (existing, definition proposed) |
|---|---|
| population | Verity assets in service (status `active` or `in_maintenance`) of type `infrastructure` or `cloud`, in scope of the scanner connection, plus every scanner asset matched to them |
| predicate | Each asset has a scanner record whose last scan time is within `scan_window_days` (setting, default 30, taken from the vulnerability management policy when it states one) |
| fail | Assets whose last scan is older than the window |
| insufficient | Assets with no scanner record while the customer has not confirmed the scanner account sees every asset (Qualys Readers and Tenable users see only what they are granted [P48][P39]); paging or export not finished |
| error | Authentication, permission or API failure |
| empty population | `insufficient_information`: no in service infrastructure asset in Verity proves nothing |
| frequency | daily |
| evidence kept | per asset: Verity asset id, scanner asset id, last scan time, scanner name; unmatched scanner assets listed separately |

| Field | `scanner.authenticated_scans` (NEW) |
|---|---|
| name | Servers get credentialed scans |
| description | Every in scope server was scanned with credentials, or by a local agent, within the scan window, so missing patches and local weaknesses are visible. |
| capabilities | `vulnerability_scanner` |
| resource_type | `asset` |
| frequency | daily |
| population | Assets in the `scanner.scans_current` population that run an operating system (scanner OS field present), excluding network devices the customer marks |
| predicate | The last authenticated scan (Tenable `last_authenticated_scan_date` [P45]; Qualys hosts filtered by `vm_auth_scan_date_after` [P48]; Rapid7 `credential_assessments` [P46], status values unverified) or the last agent scan (unverified per vendor) is within `scan_window_days` |
| outcomes | pass; fail lists servers scanned only from the network; insufficient as for `scanner.scans_current`; error |
| empty population | `insufficient_information` |
| remediation | Add scan credentials or install the scanner's agent on the listed servers. |
| evidence_kinds | Credentialed scan dates per host |
| controls | EP-04 partial: "Shows servers were scanned in a way that can see missing patches. Patch deadlines and their tracking are checked in the vulnerability register." LM-11 partial: "Shows scans are deep enough to find local weaknesses. The policy and the remediation record stay with Verity's register and people." When adopted: NS-13 (proposed, server patching) and LM-13 (proposed, scanning coverage) partial, same rationales |

Not proposed (YAGNI): a separate SLA check per scanner. Findings are fed into Verity's vulnerability
register (section 5), where `verity.vulns.within_sla` and `verity.vulns.kev_owned` already judge them
once for every source. An external port scan check for NS-08 (a coverage need) is feasible from
external scan findings but not proposed until a customer asks; NS-08 is served by the cloud checks first.

### 2.2 Business applications (`apps.`)

All six are written against `business_applications`. Provider support is in section 8.

| Key (NEW) | Name | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|---|
| `apps.access_list_exported` | Application access list exports | All members, guests and pending invites of the connected account (workspace, organisation or team) | The complete list was read, with role and status, dated | pass when complete; insufficient when paging stopped or the provider shows only part (for example a token that sees one project); error | weekly | the dated list | IAM-02 partial: "The access list a review starts from for this application. The review and its sign off are people's." IAM-12 partial: "Lets leftover accounts in this application be found. Matching them to leavers is `apps.members_active_in_directory`." |
| `apps.admins_limited` | Application admins are named and approved | Members holding an owner or admin role (provider role map in section 8) | Every admin is a named person (not a shared mailbox), an active member, and marked approved on the connection by a person in Verity, with a review date not passed (the same per resource decision pattern as repository scope, AU-9) | pass; fail lists admins not approved, shared or inactive; error; insufficient when roles cannot be read | daily | admins with role, last sign in where exposed, approval record | IAM-07 partial: "Lists who can administer this application and shows each was approved. Elevation and break glass use are not visible." |
| `apps.sso_enforced` | Application requires company sign in | The connected account | The account requires sign in through the company identity provider for every member, or lists the members allowed to bypass it and each has a recorded exception | pass; fail when not enforced; error; not_applicable when the provider has no SSO feature on the customer's plan (reason `plan`, shown once) | daily | SSO setting, exceptions | IAM-04 partial: "Shows this application is inside single sign on. The list of all applications and approved exceptions stay with people." |
| `apps.mfa_enforced` | Application members use two factor | Active members | The account enforces two factor, or every active member has two factor on, or sign in is SSO only (then the result says it relies on `idp.mfa_enforced`, and is insufficient when no identity provider is connected) | pass; fail lists members without two factor; error; insufficient | daily | enforcement setting, per member two factor flag | IAM-03 partial: "Covers sign in to this application. The identity provider and other systems are checked separately." |
| `apps.members_active_in_directory` | Application members are current staff | Active members of the application; capabilities `business_applications` and `identity_provider` | Each member matches an active identity provider user (immutable id where the provider exposes one, else normalised email), or is recorded as an external or service member with an owner | pass; fail lists unmatched or disabled people; insufficient when no identity provider is connected or its list is incomplete; error | daily | member, match result, directory status | IAM-12 partial: "Finds people who left but still hold this application, the outside single sign on case of IAM-12.D." HR-03 partial: "Finds contractor accounts that outlived their engagement in this application." |
| `apps.api_keys_current` | Application API keys are owned and in use | Active API keys and tokens the provider lists | Each has a name and an owner (person or service account), and was used, or created, within `key_unused_days` (setting, default 90). Keys with full access where the provider offers a narrower type are listed | pass; fail lists ownerless or unused keys; insufficient when the provider does not expose last use (the check then judges creation age only and says so); error | daily | key id or hint, owner, scope, created, last used | IAM-10 partial: "Inventories machine credentials held in this application and finds unused ones. Rotation records for keys stored elsewhere stay with people." |

### 2.3 AI providers (`ai.`)

| Key (NEW) | Name | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|---|
| `ai.retention_matches_review` | AI data retention matches the review | The AI provider organisation, and each project or workspace with its own retention setting; capabilities `ai_providers` and `verity_vendors` | The retention setting read from the provider equals the setting recorded on the vendor's engagement in Verity (for example "zero data retention" when customer data is sent) | pass; fail names the difference; insufficient when the provider does not expose the setting (Anthropic today, section 7.2) or no expected value is recorded; error | daily | provider setting per scope, expected value, engagement | BC-08 partial: "Shows the AI vendor's data handling still matches what the vendor review approved. The review and its report stay with people." DM-08 partial: "Shows prompts and outputs held by the AI vendor follow the retention set for that data. The schedule itself is a document." |
| `ai.usage_attributed` | AI usage is known and owned | Every project or workspace and every API key with usage in the last 30 days | Each is in scope on the connection with a recorded purpose (production, internal, trial) and an owner who is an active member; usage from anything unrecorded fails | pass; fail lists unrecorded projects, workspaces or keys; insufficient when usage data has not landed (Anthropic data can take up to 24 hours [P74]); error | daily | usage per project and key, purpose, owner | BC-05 partial: "Finds AI use nobody reviewed, the AI case of shadow IT. The decision to approve or remove it is a person's." DM-12 partial: "Each AI project carries a recorded purpose. Whether personal data is used for that purpose stays with people." |

AI providers also implement `apps.access_list_exported`, `apps.admins_limited` and
`apps.api_keys_current`; key hygiene is where most of their real evidence is.

### 2.4 Definition fields for `checks.json`

| Key | Capabilities | Planned providers | Resource type | Remediation (product text) | Evidence kinds |
|---|---|---|---|---|---|
| `scanner.authenticated_scans` | vulnerability_scanner | tenable, rapid7, qualys | asset | Add scan credentials or install the scanner's agent on the listed servers. | Credentialed scan dates per host |
| `apps.access_list_exported` | business_applications | section 8 | user | Connect the account with a role that can list every member. | Application member list |
| `apps.admins_limited` | business_applications | section 8 | user | Approve each listed admin in Verity, or remove the admin role. | Application administrators |
| `apps.sso_enforced` | business_applications | section 8 | application | Require single sign on for every member, or record an exception for each who must bypass it. | Sign in settings |
| `apps.mfa_enforced` | business_applications | section 8 | user | Require two factor for the account, or ask the listed members to turn it on. | Two factor settings and member status |
| `apps.members_active_in_directory` | business_applications, identity_provider | section 8 | user | Remove the listed members, or record each as an external or service member with an owner. | Member list compared with the directory |
| `apps.api_keys_current` | business_applications | section 8 | credential | Delete unused keys and give each remaining key an owner. | API key inventory |
| `ai.retention_matches_review` | ai_providers, verity_vendors | openai | vendor | Change the provider's retention setting, or update the vendor review to the setting in use. | Retention setting; vendor review |
| `ai.usage_attributed` | ai_providers | openai, anthropic | application | Record a purpose and owner for the listed projects and keys, or disable them. | Usage by project and key |

## 3. Observability and ticketing

### 3.1 Grafana (Cloud and self hosted)

| | |
|---|---|
| Capability | `observability` (existing), proposed `alerting`, `business_applications` |
| What it proves | Which alert rules exist, what they watch, and where they notify. Useful for LM-09 (alerting exists and reaches someone), BC-04 (capacity alerts) and SD-08 (job failure alerts). It does not prove anyone responded |
| Auth and minimal credential | A **service account** in the Grafana organisation with the **Viewer** role and a service account token; service accounts take organisation roles Viewer, Editor or Admin [P1]. Grafana Cloud stack level reads beyond the stack (for example access policies) use a Cloud **access policy** token with read scopes such as `alerts:read` and `metrics:read` [P4]. Whether Viewer can read the provisioning API is unverified; if not, the role needs alert provisioning read only |
| Key API resources | `GET /api/v1/provisioning/alert-rules` and `.../alert-rules/export`, rule groups per folder [P2]; contact points and notification policies under the same provisioning API (paths unverified this round); audit logs exist in Grafana Enterprise and Grafana Cloud only [P3]. Go: `github.com/grafana/grafana-openapi-client-go` [P5] |
| Existing checks | `observability.anomaly_monitors` S (rule queries mapped to categories by the customer); `observability.capacity_trends` S; `observability.processing_monitored` P (needs the list of jobs); `observability.logs_retained` P on Cloud (retention by plan, not read from the API, unverified), N self hosted (Loki retention is server configuration) |
| Operations keys reused | `observability.monitors_notify_on_call` S (notification policies route to an on call contact point); `observability.silent_sources_alert` P (a rule's no data state set to alert, field unverified); `observability.audit_trail_enabled` P (Enterprise or Cloud only [P3]) |
| `apps.` checks | `apps.access_list_exported` P (organisation users list needs an admin role, unverified), `apps.sso_enforced` unverified |
| Controls touched | LM-09, BC-04, SD-08, LM-02 (partial each, as the operations definitions say) |
| Setup notes | Create a service account under **Administration, Users and access, Service accounts**, give it **Viewer**, add a token, paste the token and the Grafana URL into Verity. Self hosted Grafana must be reachable from Verity (an allow list for Verity's egress address). |

### 3.2 SigNoz (Cloud and self hosted)

| | |
|---|---|
| Capability | `observability` |
| What it proves | Little beyond Grafana's: alert rules and their channels. Same controls, partial |
| Auth and minimal credential | The **Viewer** role gives read only access to observability data [P6]. API key mechanics (header name, key types) unverified this round |
| Key API resources | Alert rules, notification channels and retention (TTL) settings: endpoints unverified this round |
| Existing checks | `observability.anomaly_monitors` P, `observability.capacity_trends` P, `observability.logs_retained` P (retention settings, if readable) |
| Controls touched | LM-09, BC-04, LM-02 partial |
| Setup notes | Create a Viewer user or key; self hosted instances need to be reachable. Build only when a customer needs it: the API was not verified. |

### 3.3 Better Stack (Uptime and Telemetry)

| | |
|---|---|
| Capability | `observability`, proposed `alerting` |
| What it proves | That public services are monitored (uptime monitors), who is on call and how incidents were acknowledged. LM-08 (on call), LM-04 and LM-09 partial |
| Auth and minimal credential | Bearer token. **Team based tokens** (per team) or a **global API token** valid across all teams for managing anything [P7]. A read only token is not documented (unverified): ask for a team based token |
| Key API resources | Monitors list [P8]; heartbeats, on call calendars, escalation policies, incidents and Telemetry sources (paths unverified this round) |
| Existing checks | `observability.anomaly_monitors` n/a (uptime, not anomaly); `alerts.acknowledged_in_time` P (incident timestamps unverified) |
| Operations keys reused | `observability.production_services_monitored` S (every production endpoint has a monitor, needs the endpoint list); `alerts.on_call_covered` P; `alerts.escalation_policies_escalate` P |
| Controls touched | LM-08, LM-04, LM-09 partial |
| Setup notes | Create a team based token under **API tokens**; the token is full access for that team, so it needs the write credential ADR (D-P3-3). |

### 3.4 Linear, Asana, ClickUp, Monday

All four are `ticketing` providers. Each can implement `tickets.remediation_tracked` (findings open a
ticket that closes in SLA) once the customer maps which tickets are remediation work, and the
operations keys where the customer's workflow lives there. Ticket checks never prove the change or
access was right, only that the record exists in time.

| Provider | Auth and minimal credential | Key API resources | Checks | Plan notes |
|---|---|---|---|---|
| Linear | OAuth 2.0 with scope `read`, the default, read access for the user's account [P10]; personal API keys also exist [P9] (permission levels on keys unverified) | GraphQL at `https://api.linear.app/graphql`: issues with state, assignee, labels, timestamps; users; audit entries | `tickets.remediation_tracked` S; `tickets.changes_linked` P (issue to pull request links come through Linear's GitHub integration, unverified field); `tickets.access_requests_approved` P (needs a team or template); `apps.access_list_exported` S (users), `apps.admins_limited` P | Audit log on Enterprise plans, 90 days, readable by owners, recommended through the GraphQL API [P11] |
| Asana | OAuth with granular scopes: `tasks:read` (tasks lists and gets), `users:read`, `workspaces:read` [P12]; personal access tokens act as the user (unverified wording) | REST: `GET /tasks`, `GET /projects/{project_gid}/tasks`, `GET /workspaces/{workspace_gid}/users` [P12]; audit log events | `tickets.remediation_tracked` S; `tickets.access_requests_approved` P (approval tasks, field unverified); `apps.access_list_exported` S | Audit log API only for service accounts of Enterprise+, legacy Enterprise, or Enterprise with the Compliance Management add on, with a service account token [P13] |
| ClickUp | Personal API token (`pk_` prefix) or OAuth [P14]; no read only scope documented (unverified) | Tasks, lists, members (paths unverified this round) | `tickets.remediation_tracked` P | Token acts with the user's full rights: ADR D-P3-3. Audit log API unverified |
| Monday | Personal API token that mirrors all the user's permissions [P15]; OAuth scopes (for example a boards read scope) unverified | GraphQL boards, items, status columns | `tickets.remediation_tracked` P (needs a status column mapping) | Use a dedicated low permission user, since the token mirrors that user [P15]. Audit log API unverified (support page refused automated reading) |

Controls touched by all four: GOV-08 (deficiency remediation, `log-of-control-deficiencies-with-owner`),
SD-01 and SD-14 where changes are tracked there, IAM-01 where access requests are, partial each.

### 3.5 Notion

| | |
|---|---|
| Capability | `ticketing` (listed), proposed `business_applications` |
| What it proves | **Little.** Notion has no ticket model, so `tickets.*` work only if the customer maps a database's status and date properties; most customers use Notion for documents, which Verity's documents module owns. Honest value: a member list for access review |
| Auth and minimal credential | An internal integration (connection) with the **Read content** capability, which is enough to export data [P16]; user information can be requested **without email addresses** [P16], but matching members to the directory needs emails. The connection sees only pages shared with it [P17] |
| Key API resources | Databases and pages shared with the connection; users list (needs the user information capability) |
| Checks | `tickets.remediation_tracked` P (mapped database only); `apps.access_list_exported` P (workspace members only, guests unverified); `apps.members_active_in_directory` P |
| Controls touched | GOV-08 partial (mapped database), IAM-02 partial |
| Setup notes | Create the connection in Notion's integrations settings, give it Read content and user information with email, share the remediation database with it. Recommend deferring (D-P3-5). |

## 4. Cloud platforms (platform as a service)

These run customer production without the customer managing servers. Two honest points apply to all:

1. **Encryption at rest is the provider's default and not configurable** on most of them, so Verity cannot
   observe a setting. `cloud.encryption_at_rest` is not implemented for them; NS-01 is evidenced through
   the provider's own assurance report under PE-01 (`cloud-provider-assurance-report-that-was`), which a
   person reviews.
2. **The deployment and team checks are where they add proof**: who deployed what to production, whether
   previews are protected, who is a member with which role.

NEED raised for all of them (no `cloud.*` key, cloud research owns the prefix):
**NEED cloud_infrastructure: preview and staging deployments require sign in, so lower environments are
not public** (for SD-12.C and DM-13.B; Vercel `ssoProtection` and `passwordProtection` on projects [P27],
others unverified).

### 4.1 DigitalOcean

| | |
|---|---|
| Capability | `cloud_infrastructure`, `asset_discovery`, `business_applications` |
| What it proves | Network exposure (cloud firewalls, database trusted sources), backups of droplets and managed databases, alert policies, and the inventory. Good value for small customers whose whole estate is here |
| Auth and minimal credential | Personal access token with **custom scopes**. Read scopes include `account:read`, `actions:read`, `database:read`, `droplet:read`, `firewall:read`, `domain:read`, `certificate:read`; the **Read Only** option on the token page maps to alias scopes [P18]. Ask for Read Only, or the custom read set. `database:view_credentials` is a separate scope and is **not** requested |
| Key API resources | From DigitalOcean's published OpenAPI document [P20]: `GET /v2/firewalls`, `GET /v2/databases/{database_cluster_uuid}/firewall`, `GET /v2/databases/{database_cluster_uuid}/backups`, `GET /v2/droplets/{droplet_id}/backups/policy`, `GET /v2/monitoring/alerts`, `GET /v2/account`. Go: `github.com/digitalocean/godo` [P21] |
| Existing checks | `cloud.default_deny_ingress` S; `cloud.admin_ports_closed` S (firewall rules from `0.0.0.0/0` on admin and database ports; a database cluster with no trusted source); `cloud.backups_enabled` S (droplet backup policy for production droplets; managed database backups list); `cloud.capacity_alarms` P (alert policies exist per production droplet and database); `cloud.environments_separated` P (projects carry an environment, field unverified); `assets.resources_registered` S; `cloud.audit_logging` **N**: the team security history is shown in the control panel, older data needs a support ticket [P19], and no API was found |
| `apps.` checks | Team member listing and two factor status: not found in the OpenAPI document (searched), so N |
| Controls touched | NS-03, NS-08, BC-01, BC-04, SD-12, LM-01 partial |
| Setup notes | Create a token under **API, Tokens**, choose **Read Only** (or the custom read scopes Verity lists), set an expiry, paste it into Verity. One token per team. |

### 4.2 Heroku

| | |
|---|---|
| Capability | `cloud_infrastructure`, `ci_cd`, `business_applications` |
| What it proves | Release history per app (who released what and when), pipeline stages (environment separation) and team membership. Little on network or encryption, which the platform owns |
| Auth and minimal credential | OAuth scopes: `global` is read and write to everything; `identity` is read only account information; `read` and `read-protected` restrict modifying app configuration [P22]. Ask for **`read`** (not `read-protected`, which exposes protected configuration values, unverified detail). Heroku warns that some read only resources can include write credentials in metadata [P22], so the collector keeps an allow list of fields |
| Key API resources | Platform API apps, releases, pipelines, team members (paths and fields unverified this round). Go: `github.com/heroku/heroku-go/v6` [P24] |
| Existing checks | `ci.deployment_history_recorded` S (releases carry user and time; commit link unverified); `cloud.environments_separated` P (pipeline stages); `cloud.backups_enabled` **N** in the first version (Heroku Postgres backups are not in the Platform API, unverified); `cloud.audit_logging` P (Enterprise accounts export a monthly JSON audit trail archive through the CLI or Dashboard [P23]; no API confirmed) |
| `apps.` checks | `apps.access_list_exported` P, `apps.admins_limited` P (team roles, field names unverified) |
| Controls touched | SD-13, SD-14, SD-12, IAM-02 partial |
| Setup notes | Authorise Verity's OAuth client with the `read` scope from a team admin account. |

### 4.3 Render

| | |
|---|---|
| Capability | `cloud_infrastructure`, `ci_cd`, `business_applications` |
| What it proves | Deploy history and the workspace audit log (90 days). Little else confirmed |
| Auth and minimal credential | An API key created under **Account Settings**; every API request needs one [P25]. No scopes are documented (unverified): the key acts as the user. ADR D-P3-3 |
| Key API resources | Audit log endpoints for workspace and organisation events; Render keeps at least 90 days of workspace and organisation events; Scale and Enterprise plans can also export an organisation audit log; only workspace admins can export [P26]. Services, deploys, Postgres backups: unverified |
| Existing checks | `ci.deployment_history_recorded` P (fields unverified); `cloud.audit_logging` P: 90 days at the provider [P26] passes only if the policy period is 90 days or less; longer needs an export or Verity keeping the daily pulls (D-P3-6) |
| Controls touched | SD-13, LM-02 partial |
| Setup notes | Create a dedicated Render user with the lowest workspace role, then its API key. |

### 4.4 Vercel

| | |
|---|---|
| Capability | `cloud_infrastructure`, `ci_cd`, `business_applications`, and its firewall fits `network_edge` |
| What it proves | Production deployments with their creator, target and source; whether previews are protected; team members and roles; firewall configuration. Strong for SD-13 and SD-12 on front end estates |
| Auth and minimal credential | Bearer access token; the published OpenAPI document lists no OAuth scopes [P27], so a read only token is not offered (unverified as a statement of policy): ADR D-P3-3. Create it as a member with the lowest team role that can read projects |
| Key API resources | From Vercel's OpenAPI document [P27]: `GET /v7/deployments` (`creator`, `target`, `source`, `state`, `readyState`, `meta`, `createdAt`); `GET /v9/projects/{idOrName}` (`ssoProtection`, `passwordProtection`, `trustedIps`, `gitForkProtection`); `GET /v3/teams/{teamId}/members` (`role`, `confirmed`, `membershipSource`, `email`); `GET /v1/security/firewall/config`. Audit log: Enterprise plans, owner and security roles [P28]. No official Go SDK found |
| Existing checks | `ci.deployment_history_recorded` S; `ci.production_deploys_controlled` P (production target only from the production branch; branch field unverified); `edge.waf_enabled` P (firewall config, reuse of the operations key) |
| `apps.` checks | `apps.access_list_exported` S; `apps.admins_limited` S (owner role); `apps.members_active_in_directory` S; `apps.sso_enforced` P (team SAML enforcement field unverified) |
| Controls touched | SD-13, SD-14, SD-12, DM-13, NS-10, IAM-02, IAM-07, IAM-12 partial |
| Setup notes | Create a token under **Account Settings, Tokens**, scoped to the team, with an expiry; Verity reminds before it expires. |

### 4.5 Netlify

| | |
|---|---|
| Capability | `cloud_infrastructure`, `ci_cd`, `business_applications` |
| What it proves | Deploy history and team members; the team audit log on paid plans |
| Auth and minimal credential | Personal access token tied to the user's account [P29]; no scopes (unverified): ADR D-P3-3. Rate limited (limits not read this round) [P29] |
| Key API resources | Sites, deploys, team members (paths unverified). Team audit log on Pro and Enterprise, retention by plan [P30]; API access to it unverified. Go: `github.com/netlify/open-api/v2` [P31] |
| Existing checks | `ci.deployment_history_recorded` P; `apps.access_list_exported` P |
| Controls touched | SD-13, IAM-02 partial |
| Setup notes | Create the token under **Applications, Personal access tokens** from a member with the lowest role that sees all sites. |

### 4.6 Supabase

| | |
|---|---|
| Capability | `cloud_infrastructure`, `business_applications` |
| What it proves | **Good value**: database backups and point in time recovery, SSL enforcement, network restrictions, security advisor findings, organisation members with two factor status |
| Auth and minimal credential | Prefer an **OAuth integration** with read scopes: **Database Read** (database configuration, SSL enforcement), **Auth Read** (auth configuration, SAML providers), and organisation read [P33]. Personal access tokens also work but carry the user's permissions [P32]. OAuth needs Verity to register an OAuth app with Supabase |
| Key API resources | From the Management API OpenAPI document [P32]: `GET /v1/projects/{ref}/database/backups` (`pitr_enabled`, `walg_enabled`, `backups`; scope `database:read`); `GET /v1/projects/{ref}/ssl-enforcement` (`database:read`); `GET /v1/projects/{ref}/network-restrictions`; `GET /v1/projects/{ref}/advisors/security` (`database:read`); `GET /v1/organizations/{slug}/members` (`role_name`, `mfa_enabled`; `organizations:read`); `GET /v1/projects/{ref}/config/auth/sso/providers`. The Go `supabase-go` package is a client library, not the Management API |
| Existing checks | `cloud.backups_enabled` S (PITR on for production projects); `cloud.tls_in_transit` S (SSL enforced); `cloud.admin_ports_closed` S (network restrictions not open to `0.0.0.0/0`); `cloud.hardening_baseline` P (no open security advisor finding at the error level, level names unverified); `cloud.environments_separated` P (separate projects per environment, roles set by the customer) |
| `apps.` checks | `apps.access_list_exported` S; `apps.mfa_enforced` S (`mfa_enabled` per member); `apps.admins_limited` S (`role_name`); `apps.members_active_in_directory` S |
| Controls touched | BC-01, NS-02, NS-08, NS-04, SD-12, IAM-02, IAM-03, IAM-07, IAM-12 partial |
| Setup notes | Approve Verity's Supabase app for the organisation with the read scopes shown. |

### 4.7 Neon

| | |
|---|---|
| Capability | `cloud_infrastructure`, `business_applications` |
| What it proves | Point in time restore window, IP allow lists and public connection blocking, protected branches, project members |
| Auth and minimal credential | Three key types: personal (any user; access to the projects the user is a member of), organisation (administrators; admin level access to everything) and project scoped (administrators; one project) [P34]. Least privilege: a **personal key of a user with the Viewer role** (Viewers create personal keys [P34]) |
| Key API resources | From Neon's OpenAPI document [P35]: `GET /projects`, `GET /projects/{project_id}` (`history_retention_seconds`; `settings.allowed_ips` with `ips` and `protected_branches_only`; `settings.block_public_connections`; `settings.audit_log_level`), branches (`protected`), `GET /projects/{project_id}/members`. No official Go SDK found |
| Existing checks | `cloud.backups_enabled` S (restore window at least the setting); `cloud.admin_ports_closed` S (production projects have an allow list or block public connections); `cloud.environments_separated` P (production branch protected, separate projects or branches per environment) |
| `apps.` checks | `apps.access_list_exported` P (project members; organisation members unverified) |
| NEED | The coverage need "database audit logging is on for every production database" (proposed SD-17) may be met by `audit_log_level`; its meaning is unverified |
| Controls touched | BC-01, NS-08, SD-12, IAM-02 partial |
| Setup notes | Invite a Verity reader user with the Viewer role, sign in as it, create a personal API key. |

### 4.8 Qovery

| | |
|---|---|
| Capability | `ci_cd`, `business_applications` (Qovery deploys onto the customer's own AWS, Google Cloud or Azure account, so cloud checks come from that cloud's connector) |
| What it proves | Deployment control: who deployed which environment, and environment modes. Partial |
| Auth and minimal credential | An API token carries a role from Qovery's RBAC, chosen at creation; API policy tokens carry a narrower policy instead [P36]. Choose the lowest read role (role names unverified) |
| Key API resources | Organisation, projects, environments, deployment history, members (paths unverified). Go: `github.com/qovery/qovery-client-go` [P37] |
| Existing checks | `ci.deployment_history_recorded` P; `ci.production_deploys_controlled` P; `cloud.environments_separated` P |
| Controls touched | SD-13, SD-12 partial |
| Setup notes | Create the token under organisation settings with a read only role or policy. |

## 5. Vulnerability scanners: feeding Verity's vulnerability register

### 5.1 Design

A scanner connector does not keep its own copy of findings. It reads findings and assets, normalises
them, and hands them to the vulnerabilities module (`backend/src/verity/modules/vulnerabilities`), which
already deduplicates on asset, definition (CVE or normalised title) and locator, enriches CVEs with EPSS,
CISA KEV and exploit data, scores risk, starts SLA clocks from the tenant's policy, escalates breaches
and expires acceptances in its daily sweep (`service.py`: `import_findings`, `_ingest`,
`refresh_and_sweep`). Each run becomes one `VulnReport` (`report_type` `vulnerability_scan`,
`scan_tool` the provider), so an auditor walks from a finding to the run that reported it.

Flow per run: collector exports findings since the last successful run (plus a full refresh weekly) ->
core ingestion maps each to a `FindingRow` -> `import_findings(actor=System)` -> enrichment and SLA as
today -> `scanner.scans_current` and `scanner.authenticated_scans` evaluate the asset half -> the
existing `verity.vulns.within_sla` and `verity.vulns.kev_owned` evaluate the register.

### 5.2 Gaps found in the module (code read 2026-11-23)

| Gap | Where | Effect | Proposal |
|---|---|---|---|
| Assets are matched by `asset_id` or by **name** only | `_ingest`, `by_name = {r.name.lower(): ...}` | Scanner hosts named by IP or FQDN do not match; they are counted as `unmatched` and **dropped** | Match on `cloud_resource_id`, `fqdn`, `hostname`, `ip_address`, `primary_mac` (all columns on `assets`) in that order; keep unmatched findings (below) |
| Unmatched rows are discarded | `_ingest`: `unmatched += 1; continue` | A finding on an unregistered host disappears; the register looks cleaner than the estate | NEED verity_vulnerabilities: findings on hosts not in the asset register are kept as unmatched and raise asset register work (LM-01, proposed LM-13) |
| First detection is the **import time** | `first_detected_at=now` | SLA starts when Verity first sees the finding, not when the scanner found it; a first sync of an old backlog shows nothing overdue | NEED verity_vulnerabilities: imported findings keep the scanner's first found time, and the SLA due date is computed from it (LM-11.D, LM-12.C). Requires a `first_found` field on `FindingRow` |
| Severity words | `_SEVERITY_WORDS` maps `0..4` and a few words; anything else becomes `medium` | Rapid7 `severe` and Qualys level `5` would be stored as **medium** | Each collector maps its scale explicitly (section 5.3) before the module sees it; the module should reject an unknown severity instead of defaulting (a code change for the module owner) |
| No scanner driven closure | `verify_instance` closes only from `pending_retest`, by a person | A fix the scanner confirmed stays open until someone clicks | NEED verity_vulnerabilities: a finding the scanner reports fixed after a rescan moves to verified fixed with the scanner as verifier (actor System, the run's report), and every closure as fixed in the period has such a rescan or a person's retest (LM-11.E). The docstring already anticipates it ("or, later, a scanner") |
| No external id per instance | `_ingest` does not set `external_id` | A re-run cannot tell an instance from a new one by provider id; the semantic key copes, but the provider's own id is lost | Set `source` to the provider and `external_id` to the provider's finding or detection id (rule 9) |

### 5.3 Severity maps

| Provider | Provider scale | Verity |
|---|---|---|
| Tenable | `info`, `low`, `medium`, `high`, `critical` (export filter values [P42]) | same words |
| Rapid7 InsightVM | `none`, `informational`, `low`, `moderate`, `severe`, `critical` [P46] | none and informational -> info; moderate -> medium; severe -> high; critical -> critical |
| Qualys | levels 1 to 5, 5 the most severe (names unverified this round); QDS 1 to 100 with bands Critical 90 to 100, High 70 to 89, Medium 40 to 69, Low 1 to 39 [P48] | 5 -> critical, 4 -> high, 3 -> medium, 2 -> low, 1 -> info (proposed; to confirm with the KnowledgeBase); QDS kept as a separate field |

### 5.4 Tenable (Nessus, Tenable Vulnerability Management)

| | |
|---|---|
| Capability | `vulnerability_scanner`, proposed `asset_discovery` |
| What it proves | Which hosts were scanned and when, whether scans were credentialed, and the findings that drive the register. LM-11, EP-04 partial; with the register, LM-12.C |
| Auth and minimal credential | API keys per user account, sent as the `X-ApiKeys` header [P40]. Roles: Read-Only (0) "can view information without being able to make changes, run scans, or manage settings", Basic (16), Scan Operator (24), Standard (32), Scan Manager (40), Administrator (64) [P38]. Vulnerability exports need **at least Basic [16]** plus **Can View** on the assets exported [P41], so the least privilege user is **Basic with Can View on all assets** |
| Key API resources | Export vulnerabilities, get export status, download chunk; export assets v1 and v2 [P41] (exact paths per the reference, not re read this round). Filters: `state` OPEN, REOPENED, FIXED (the UI's new and active map to OPEN, resurfaced to REOPENED); without a state filter, OPEN and REOPENED seen since `since` and FIXED fixed since `since` [P42]; without any time filter only the last 30 days [P41]; `num_assets` 50 to 5,000 per chunk [P41]. Asset attributes `last_scan_time`, `last_authenticated_scan_date`, `last_licensed_scan_date` [P45] |
| Limits | 429 with `retry-after` when the per user per minute allowance is used [P44]; at most ten or three active concurrent exports per container depending on the endpoint [P43]. Official SDK is Python (pyTenable); no official Go SDK found |
| Checks | `scanner.scans_current` S; `scanner.authenticated_scans` S; feeds `verity.vulns.within_sla`, `verity.vulns.kev_owned`; `assets.resources_registered` P (proposed asset discovery) |
| Nessus Professional and Tenable Security Center | Not researched to the end: the Nessus API page was not found and Security Center was not read (unverified). Customers on Nessus Professional keep the existing `.nessus` upload path (`parse_xml` already reads `ReportHost` and `ReportItem`) |
| Controls touched | LM-11, EP-04, LM-12, LM-01 partial; proposed LM-13, NS-13 |
| Setup notes | Create a user with the **Basic** role, grant it **Can View** on all assets, generate API keys as that user, paste both keys into Verity. Confirm in Verity that the user sees all assets (it changes "not scanned" from insufficient to fail). |

### 5.5 Rapid7 InsightVM (formerly Nexpose)

| | |
|---|---|
| Capability | `vulnerability_scanner`, proposed `asset_discovery` |
| What it proves | As Tenable: scan recency, credential status, findings with first and last found dates |
| Auth and minimal credential | Insight Platform API key in the `X-Api-Key` header against `https://{region}.api.insight.rapid7.com/vm/` [P46]. Two key types: a **user key** that inherits the permissions of its user (any user can create one), and an **organisation key**, a super key only platform or organisation administrators can create [P47]. Use a **user key** of a user with a read only product role (role name unverified). The v4 API also contains Start Scan, Stop Scan and Update Scan Engine Configuration [P46], so the user's role must not allow those |
| Key API resources | Cloud Integrations API v4 [P46]: `POST /v4/integration/assets` (search), `GET /v4/integration/assets/{id}`, `POST /v4/integration/vulnerabilities`, `POST /v4/integration/sites`, `GET /v4/integration/scan`. Asset fields `host_name`, `ip`, `mac`, `last_scan_start`, `last_scan_end`, `last_assessed_for_vulnerabilities`, `credential_assessments`, and per asset `new`, `same`, `remediated` findings with `first_found`, `last_found`, `status` |
| Limits | Pages of up to 500 with `page` and `size`, up to 10,000 results; beyond that the `cursor` parameter, which also gives a repeatable read [P46]. Rate limits not documented in the specification (unverified). No official Go SDK found. On premises Security Console API v3: not read this round |
| Checks | `scanner.scans_current` S; `scanner.authenticated_scans` P (credential assessment values unverified); feeds the register; `remediated` lets the scanner driven closure proposal work |
| Controls touched | LM-11, EP-04, LM-12, LM-01 partial |
| Setup notes | In the Insight Platform, sign in as a read only Verity user, open **API key management**, create a **user key**, choose the region, paste both into Verity. |

### 5.6 Qualys VMDR

| | |
|---|---|
| Capability | `vulnerability_scanner`, proposed `asset_discovery` |
| What it proves | As Tenable, with Qualys's own detection score (QDS) |
| Auth and minimal credential | A Qualys user with the **API access** method; the API server URL depends on the customer's platform (pod) [P49]. Every request needs the `X-Requested-With` header [P48]; some endpoints accept basic authentication only [P48]. Least privilege: a **Reader** user. Readers and Scanners see only hosts in their account (assigned through asset groups, or tags when tag based scoping is on); Managers see all hosts; Auditors cannot see VM hosts [P48]. So the Reader must be given every asset group, or the population is partial |
| Key API resources | Host List Detection `GET or POST /api/2.0/fo/asset/host/vm/detection/?action=list`: latest status per detection (NEW, ACTIVE, FIXED, REOPENED) and history; filters `status` (New, Active, Re-Opened, Fixed), `detection_updated_since`, `vm_auth_scan_date_after` and `_before`, `show_qds`, `truncation_limit` (0 for none), `id_min`; output includes `LAST_VM_SCANNED_DATE` and `FIRST_FOUND_DATETIME` [P48] |
| Limits | Rate and concurrency limits per subscription and service level; headers `X-RateLimit-Limit`, `X-RateLimit-Window-Sec`, `X-RateLimit-Remaining`, `X-RateLimit-ToWait-Sec`, `X-Concurrency-Limit-Limit`; a blocked call returns `409 Conflict` [P48]. Large detection outputs are truncated and continued with `id_min` [P48]. No official Go SDK found |
| Checks | `scanner.scans_current` S; `scanner.authenticated_scans` S (authenticated scan date filters); feeds the register |
| Controls touched | LM-11, EP-04, LM-12, LM-01 partial |
| Setup notes | Create a Reader user with API access, add every asset group to it, note your Qualys platform URL, paste user, password and URL into Verity. The password is stored envelope encrypted and never logged. |

## 6. Asset discovery: BMC Helix Discovery

| | |
|---|---|
| Capability | `asset_discovery` (listed in `capabilities.json` as `bmc`) |
| What it proves | A discovered inventory of hosts, software and cloud services to compare with Verity's asset register: `assets.resources_registered` and the proposed `assets.retired_resources_closed`, LM-01 partial. Only for customers who already run it; it is an enterprise tool |
| Auth, API, roles | **Unverified.** BMC's documentation site refused automated reading (HTTP 403) this round, so the REST API version, the token flow, the search (query language) endpoint and the least privilege user group could not be confirmed. Nothing is stated here as fact |
| Checks | `assets.resources_registered` (expected S), `assets.retired_resources_closed` (expected S), both pending verification |
| Controls touched | LM-01 partial |
| Next step | Redo the research with access to BMC's documentation or a customer's appliance before any build (decision D-P3-7). |

## 7. Business applications, email delivery and AI providers

### 7.1 Business applications

These hold customer data (CRM, support, analytics). What they can prove is **access**: who has an
account, who is an admin, whether sign in is protected, and sometimes an audit log. They prove nothing
about the controls in their own product beyond that; their own security is BC-08 vendor due diligence.

| Provider | Auth and minimal credential | Key API resources | `apps.` checks | Plan notes and traps |
|---|---|---|---|---|
| HubSpot | Private app access token with read scopes (exact scope names for users and account activity unverified this round) | User provisioning API (users and permission sets, `/settings/v3/users`) [P52]; account activity: `GET /account-info/v3/activity/login` (each login attempt, successful or not, in the past 90 days), `GET /account-info/v3/activity/security`, and `GET /account-info/v3/activity/audit-logs` (Enterprise accounts only) [P51] | `apps.access_list_exported` S; `apps.admins_limited` P (super admin flag, unverified); `apps.members_active_in_directory` S; `apps.mfa_enforced` unverified | Login history is 90 days [P51]; a Type 2 period needs Verity to keep daily pulls |
| Intercom | OAuth with **Read admins** and **Read admin activity logs** among the extended scopes [P54] | `GET /admins/activity_logs`, which requires the `read_admins` OAuth scope; US, EU and Australian API servers [P53] | `apps.access_list_exported` S (admins); `apps.admins_limited` P; `apps.members_active_in_directory` S; two factor and SSO status unverified | The region decides the API host [P53] |
| Zendesk | **OAuth only.** Zendesk's Developer Terms forbid sharing API credentials with third parties, and an integration used by many customers must use **global OAuth** tokens [P56]; token scopes such as `read` [P58] | Users with `two_factor_auth_enabled` [P57]; `GET /api/v2/audit_logs` with cursor pagination, Enterprise plan only, for admins with audit log access [P55] | `apps.access_list_exported` S (agents and admins); `apps.mfa_enforced` S (per user flag [P57]); `apps.admins_limited` S; `apps.members_active_in_directory` S | Verity must register a global OAuth client with Zendesk before any customer can connect (review process and lead time unverified), D-P3-4 |
| PostHog | Personal API keys limited to the scopes granted [P59] (project limits as described there); Cloud US and EU hosts | `GET /api/organizations/:organization_id/members/` (scope `organization_member:read`; fields `level`, `is_2fa_enabled`, `has_social_auth`, `last_login`) [P60]; `GET /api/projects/:project_id/activity_log/` (scope `activity_log:read`) [P61] | `apps.access_list_exported` S; `apps.mfa_enforced` S (`is_2fa_enabled`); `apps.admins_limited` S (`level`); `apps.members_active_in_directory` S | Private endpoints are rate limited (numbers not read) [P59] |

Controls touched: IAM-02, IAM-03, IAM-04, IAM-07, IAM-12, HR-03, partial each, through the artifacts in
section 8.2. Data inventory needs from the coverage files (`data-inventory-and-data-map`: "business
applications that hold personal data are listed") are met by the vendor register, not by these APIs.

### 7.2 Email delivery: SendGrid and Resend

| Provider | Auth and minimal credential | Key API resources | Checks | What it proves |
|---|---|---|---|---|
| SendGrid (Twilio) | API key with restricted scopes; read scopes include `teammates.read`, `api_keys.read`, `access_settings.whitelist.read`, `access_settings.activity.read`, `user.settings.enforced_tls.read` [P62] | `GET /v3/teammates` (`user_type` owner, admin or teammate; `is_admin`) [P63]; enforced TLS settings [P64]; API keys; IP access management. Go: `github.com/sendgrid/sendgrid-go` [P65] | `apps.access_list_exported` S; `apps.admins_limited` S; `apps.api_keys_current` P (last use unverified); `apps.members_active_in_directory` S | **Little**: who can send mail as the company and whether outbound TLS is enforced (NS-02 partial, for one channel) |
| Resend | API keys have `full_access` (create, delete, get, update any resource) or `sending_access` (send only) [P66]; **no read only key** | Domains with SPF and DKIM record status [P67]; API keys. Go: `github.com/resend/resend-go/v3` [P68] | `apps.api_keys_current` P | **Little**, and reading needs a full access key. Recommend not building (D-P3-3) |

### 7.3 OpenAI

| | |
|---|---|
| Capability | proposed `ai_providers`, `business_applications` |
| What it proves | Who is in the organisation and its projects, which API keys and service accounts exist with their last use, the organisation and project data retention setting, usage per project and key, and an audit log of admin actions. Real evidence for IAM-02, IAM-07, IAM-10, BC-05 and BC-08 when a customer uses OpenAI in its product |
| Auth and minimal credential | An **Admin API key**. Admin keys work only on administration endpoints [P69]. The admin key object has no scope or permission field in OpenAI's published specification [P70], so it is read and write across administration: ADR D-P3-3. Who can create one (organisation owners) is unverified this round |
| Key API resources | From OpenAI's OpenAPI specification [P70]: `GET /v1/organization/users` (`role`, `email`, `added_at`); `GET /v1/organization/projects`; `GET /v1/organization/projects/{project_id}/users`; `.../service_accounts`; `.../api_keys` (`created_at`, `last_used_at`, `expires_at`, `owner`, `owner_project_access`); `GET /v1/organization/admin_api_keys` (`created_at`, `last_used_at`, `expires_at`, `owner`); `GET /v1/organization/data_retention` and `GET /v1/organization/projects/{project_id}/data_retention` (`type`: `zero_data_retention`, `modified_abuse_monitoring`, `enhanced_zero_data_retention`, `enhanced_modified_abuse_monitoring`); `GET /v1/organization/audit_logs` (event types include `api_key.created`, `login.succeeded`, `login.failed`, `ip_allowlist.*`, `project.*`, `role.*`); `GET /v1/organization/usage/completions` and the other usage endpoints; `GET /v1/organization/costs`; roles, groups, invites, certificates. Go: `github.com/openai/openai-go` [P71] (whether it covers administration endpoints is unverified) |
| Checks | `ai.retention_matches_review` S; `ai.usage_attributed` S (usage grouped by project and key); `apps.access_list_exported` S; `apps.admins_limited` S (owner role); `apps.api_keys_current` S (`last_used_at` exposed); `apps.members_active_in_directory` S |
| Traps | Audit logging may need to be switched on in the organisation's settings before events are kept (unverified this round); until confirmed, an empty audit log is `insufficient`, never "no admin actions". Usage endpoints show traffic, not content: whether personal data was sent stays with people |
| Controls touched | IAM-02, IAM-07, IAM-10, IAM-12, BC-05, BC-08, DM-08, DM-12 partial |
| Setup notes | An organisation owner creates an admin key in the organisation settings, names it "Verity", and pastes it into Verity. Verity calls only list and get endpoints, and says so on the connection page. |

### 7.4 Anthropic

| | |
|---|---|
| Capability | proposed `ai_providers`, `business_applications` |
| What it proves | Members and roles, workspaces and their members, API keys with creator and status, usage and cost per workspace and key, and whether the Compliance API is enabled. Same controls as OpenAI, except data retention, which the Admin API does not expose |
| Auth and minimal credential | Console organisations: an **Admin API key** (`sk-ant-admin...`); only members with the admin role can provision one [P72]. It also allows writes (member, invite, workspace and key changes) [P73]: ADR D-P3-3. The Admin API also accepts a personal or service account key not scoped to one workspace, with the same permissions as the linked account [P72]; whether a non admin role can read the lists Verity needs is unverified and worth testing, because it would avoid an admin credential. Claude Enterprise organisations use scoped keys created by the primary owner, with scopes such as `read:analytics`, `read:org_audit` and `read:compliance_org_data` [P73][P74] |
| Key API resources | From the Admin API reference [P73]: `GET /v1/organizations/users`; `GET /v1/organizations/invites`; `GET /v1/organizations/workspaces` (with `data_residency`) and `.../workspaces/{workspace_id}/members`; `GET /v1/organizations/api_keys` (`created_at`, `created_by`, `expires_at`, `name`, `partial_key_hint`, `principal`, `status`; **no last used field**); `GET /v1/organizations/service_accounts` (OAuth only); `GET /v1/organizations/compliance_settings` (`state` enabled or disabled); usage and cost analytics `GET /v1/organizations/analytics/usage` and `/cost` (beta), from 1 January 2026, within the last 365 days, at most 31 days per request, data typically within 4 hours and up to 24 hours [P74]. Admin API keys can read only the Compliance API's activity feed [P72]. Go: `github.com/anthropics/anthropic-sdk-go` [P75], admin endpoints under the beta organisation client (per Anthropic's SDK documentation) |
| Checks | `ai.usage_attributed` S (group by `workspace_id` and `api_key_id`; lag up to 24 hours); `ai.retention_matches_review` **insufficient** (no retention endpoint found in the reference, searched 2026-11-23; the setting is contractual and stays a person's upload); `apps.access_list_exported` S; `apps.admins_limited` S (roles `admin`, `developer`, `billing`, `user`, `claude_code_user` [P73]); `apps.api_keys_current` P (creation age only, no last use); `apps.members_active_in_directory` S |
| Controls touched | IAM-02, IAM-07, IAM-10, IAM-12, BC-05, BC-08 partial |
| Setup notes | An organisation admin creates an Admin API key in the Claude Console named "Verity" and pastes it into Verity. Claude Enterprise: the primary owner creates a key with the read scopes Verity lists. |

## 8. Coverage summary

### 8.1 Provider by check

| Provider | Checks it can implement (S or P) |
|---|---|
| Grafana | `observability.anomaly_monitors`, `.capacity_trends`, `.processing_monitored`, `.logs_retained` (Cloud), `.monitors_notify_on_call`, `.silent_sources_alert`, `.audit_trail_enabled`; `apps.access_list_exported` |
| SigNoz | `observability.anomaly_monitors`, `.capacity_trends`, `.logs_retained` (all P, API unverified) |
| Better Stack | `observability.production_services_monitored`; `alerts.acknowledged_in_time`, `.on_call_covered`, `.escalation_policies_escalate` |
| Linear, Asana, ClickUp, Monday | `tickets.remediation_tracked`; Linear and Asana also `tickets.access_requests_approved` (P), `apps.access_list_exported` |
| Notion | `tickets.remediation_tracked` (P, mapped database); `apps.access_list_exported`, `apps.members_active_in_directory` (P) |
| DigitalOcean | `cloud.default_deny_ingress`, `.admin_ports_closed`, `.backups_enabled`, `.capacity_alarms`, `.environments_separated`; `assets.resources_registered` |
| Heroku | `ci.deployment_history_recorded`; `cloud.environments_separated`, `.audit_logging` (Enterprise); `apps.access_list_exported`, `.admins_limited` |
| Render | `ci.deployment_history_recorded`; `cloud.audit_logging` (90 days) |
| Vercel | `ci.deployment_history_recorded`, `.production_deploys_controlled`; `edge.waf_enabled`; `apps.access_list_exported`, `.admins_limited`, `.members_active_in_directory`, `.sso_enforced` |
| Netlify | `ci.deployment_history_recorded`; `apps.access_list_exported` |
| Supabase | `cloud.backups_enabled`, `.tls_in_transit`, `.admin_ports_closed`, `.hardening_baseline`, `.environments_separated`; `apps.access_list_exported`, `.mfa_enforced`, `.admins_limited`, `.members_active_in_directory` |
| Neon | `cloud.backups_enabled`, `.admin_ports_closed`, `.environments_separated`; `apps.access_list_exported` |
| Qovery | `ci.deployment_history_recorded`, `.production_deploys_controlled`; `cloud.environments_separated` |
| Tenable, Rapid7, Qualys | `scanner.scans_current`, `scanner.authenticated_scans`; through the register `verity.vulns.within_sla`, `verity.vulns.kev_owned`; `assets.resources_registered` (proposed) |
| BMC Helix Discovery | `assets.resources_registered`, `assets.retired_resources_closed` (unverified) |
| HubSpot, Intercom, Zendesk, PostHog | `apps.access_list_exported`, `.admins_limited`, `.members_active_in_directory`; Zendesk and PostHog also `apps.mfa_enforced` |
| SendGrid | `apps.access_list_exported`, `.admins_limited`, `.members_active_in_directory`, `.api_keys_current` |
| Resend | `apps.api_keys_current` (not recommended) |
| OpenAI | `ai.retention_matches_review`, `ai.usage_attributed`; `apps.access_list_exported`, `.admins_limited`, `.api_keys_current`, `.members_active_in_directory` |
| Anthropic | `ai.usage_attributed`; `apps.access_list_exported`, `.admins_limited`, `.api_keys_current` (P), `.members_active_in_directory` |

### 8.2 Artifacts and objectives filled by the new checks

The `person` source stays on each.

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `scan-reports` | LM-11.B, LM-11.C | LM-11 | today `scanner.scans_current` + person; gains `scanner.authenticated_scans` and three collectors |
| `patch-compliance-report` | EP-04.B, EP-04.C, EP-04.D, EP-03.D | EP-04 | today `devices.os_current`, `scanner.scans_current` + person; gains `scanner.authenticated_scans` |
| `vulnerability-register-with-remediation-and-accepted` | LM-11.C, LM-11.D, LM-11.E, LM-12.C, GOV-16.D, SD-03.C, SD-03.E, SD-05.C | LM-11 | unchanged sources (`verity.vulns.within_sla`); the register now fills from scanners automatically |
| `actively-exploited-vulnerabilities-and-time-taken` | LM-12.C | LM-12 | person -> person + `verity.vulns.kev_owned` once the first found NEED (section 5.2) is met |
| `account-list-export` | IAM-02.B, IAM-10.B, IAM-12.E, HR-03.B | IAM-02 | + `apps.access_list_exported`, `apps.members_active_in_directory` |
| `list-of-privileged-accounts-with-approval` | IAM-07.B, IAM-01.D, IAM-03.C, IAM-10.C, SD-12.C, SD-13.D, BC-01.D | IAM-07 | + `apps.admins_limited` (meets the operations need for admin exports per tool) |
| `second-factor-enforcement-and-enrolled-users` | IAM-03.B, IAM-03.C, IAM-03.D, IAM-03.E | IAM-03 | + `apps.mfa_enforced` (meets the operations need for second factor per tool) |
| `applications-inside-and-outside-single-sign-on` | IAM-04.B, IAM-04.C, IAM-04.D, GOV-14.B | IAM-04 | + `apps.sso_enforced` (B); exceptions (C) stay a person |
| `removal-records-for-a-sample-of` | IAM-12.B, IAM-12.C, IAM-12.D, IAM-04.D, IAM-11.D, HR-03.D | IAM-12 | + `apps.members_active_in_directory` (D, systems outside single sign on) |
| `inventory-of-service-accounts-and-keys` | IAM-10.B, IAM-10.C, IAM-10.D, SD-13.D | IAM-10 | + `apps.api_keys_current` |
| `records-of-rotation-or-review` | IAM-10.D, IAM-10.E | IAM-10 | + `apps.api_keys_current` (E: unused keys found) |
| `review-of-newly-discovered-applications` | BC-05.B, BC-05.C, BC-05.D | BC-05 | + `ai.usage_attributed` (AI use found) |
| `security-assessment-for-each-critical-vendor` | BC-08.C, BC-08.E, DM-17.C, GOV-29.E, SD-10.B | BC-08 | + `ai.retention_matches_review` (the reviewed setting still holds) |
| `data-retention-schedule` | DM-08.A, DM-08.B, DM-08.D, DM-15.B, SD-07.E, SD-14.D | DM-08 | + `ai.retention_matches_review` (B, D: data held by the AI vendor) |
| `register-of-the-purposes-personal-information` | DM-12.B and others | DM-12 | + `ai.usage_attributed` (each AI project has a purpose) |

### 8.3 Framework reach of the new checks

| Check | Controls | SOC 2 | ISO 27001:2022 |
|---|---|---|---|
| `scanner.authenticated_scans` | EP-04, LM-11 | CC6.8, CC7.1 | A.8.8 |
| `apps.access_list_exported`, `apps.members_active_in_directory` | IAM-02, IAM-12, HR-03 | CC6.2, CC6.3, CC9.2 | A.5.11, A.5.16, A.5.18, A.8.4, A.8.30 |
| `apps.admins_limited` | IAM-07 | CC6.3 | A.8.2, A.8.18 |
| `apps.sso_enforced`, `apps.mfa_enforced` | IAM-04, IAM-03 | CC6.1 | A.8.5 |
| `apps.api_keys_current` | IAM-10 | CC6.1, CC6.3 | A.5.16, A.8.3 |
| `ai.retention_matches_review` | BC-08, DM-08 | CC9.2, P6.4, C1.2, P4.2 | A.5.19 to A.5.23, A.8.10, A.5.33 |
| `ai.usage_attributed` | BC-05, DM-12 | CC9.2, P4.1 | A.5.23, A.5.34 |

## 9. Limits, traps and what was not verified

- **Write capable credentials.** Render, Vercel, Netlify, ClickUp, Monday, Better Stack, Resend, the
  OpenAI admin key and the Anthropic Console admin key cannot be made read only from what was found.
  `integrations.md` says a connector that needs write access needs an ADR (D-P3-3).
- **Population visibility.** Scanner users (Qualys Readers, Tenable users without Can View on all
  assets) and app tokens tied to one user see only part of the account. Every check here treats "not
  visible" as `insufficient`, and asks the customer to confirm full visibility once.
- **Short provider retention.** HubSpot logins 90 days [P51], Render audit 90 days [P26], Linear audit 90
  days [P11]. A 12 month Type 2 period needs Verity to keep its daily pulls as evidence (D-P3-6).
- **Default encryption on platforms** is not a setting Verity can see (section 4).
- **The register can look clean** when unmatched scanner findings are dropped or SLA clocks start at
  import (section 5.2). These are module fixes, not connector ones.
- **Not verified this round:** BMC Helix Discovery entirely; SigNoz and Better Stack endpoints; ClickUp
  and Monday audit logs and scopes; Heroku, Render, Netlify and Qovery endpoint paths and fields; HubSpot
  scope names; Intercom and HubSpot two factor fields; Tenable export endpoint paths (names confirmed,
  paths not re read); Nessus Professional and Security Center APIs; Rapid7 read only role name and rate
  limits; Qualys severity names; OpenAI admin key creator and audit log activation; whether OpenAI's Go
  SDK covers admin endpoints; whether an Anthropic non admin key can read members and keys.
- **Comparable platforms** (Vanta, Drata, Secureframe, Sprinto) were not researched for these providers:
  the shared web search budget was exhausted. To be added per provider when its full document is written.

## 10. Sources

All read on 2026-11-23. Verity code read: `backend/src/verity/modules/vulnerabilities/service.py`
(`import_findings`, `_ingest`, `_norm_severity`, `verify_instance`, `refresh_and_sweep`) and `models.py`;
`backend/src/verity/modules/assets/models.py`.

- [P1] Grafana, service accounts: https://grafana.com/docs/grafana/latest/administration/service-accounts/
- [P2] Grafana, alerting provisioning HTTP API: https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/alerting_provisioning/
- [P3] Grafana, audit a Grafana instance (Enterprise and Cloud): https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/audit-grafana/
- [P4] Grafana Cloud, access policies and scopes: https://grafana.com/docs/grafana-cloud/platform/security-and-account-management/security-and-access/authentication-and-permissions/access-policies/
- [P5] grafana-openapi-client-go: https://pkg.go.dev/github.com/grafana/grafana-openapi-client-go
- [P6] SigNoz, authentication and roles: https://signoz.io/docs/userguide/authentication/
- [P7] Better Stack, getting started with the Uptime API: https://betterstack.com/docs/uptime/api/getting-started-with-uptime-api/
- [P8] Better Stack, list all existing monitors: https://betterstack.com/docs/uptime/api/list-all-existing-monitors/
- [P9] Linear, GraphQL API: https://linear.app/developers/graphql
- [P10] Linear, OAuth 2.0 authentication: https://linear.app/developers/oauth-2-0-authentication
- [P11] Linear, audit log: https://linear.app/docs/audit-log
- [P12] Asana, OAuth scopes: https://developers.asana.com/docs/oauth-scopes
- [P13] Asana, audit log API: https://developers.asana.com/reference/audit-log-api
- [P14] ClickUp, authentication: https://developer.clickup.com/docs/authentication
- [P15] monday.com, authentication: https://developer.monday.com/api-reference/docs/authentication
- [P16] Notion, capabilities: https://developers.notion.com/reference/capabilities
- [P17] Notion, authorization overview: https://developers.notion.com/guides/authorization/overview
- [P18] DigitalOcean, API token scopes: https://docs.digitalocean.com/reference/api/scopes/
- [P19] DigitalOcean, view security history: https://docs.digitalocean.com/platform/teams/how-to/view-security-history/
- [P20] DigitalOcean, API reference and its OpenAPI document: https://docs.digitalocean.com/reference/api/digitalocean/ and https://api-engineering.nyc3.cdn.digitaloceanspaces.com/spec-ci/DigitalOcean-public.v2.yaml
- [P21] godo: https://pkg.go.dev/github.com/digitalocean/godo
- [P22] Heroku, OAuth (scopes): https://devcenter.heroku.com/articles/oauth
- [P23] Heroku, audit trails for Enterprise accounts: https://devcenter.heroku.com/articles/audit-trail
- [P24] heroku-go: https://pkg.go.dev/github.com/heroku/heroku-go/v6
- [P25] Render, API: https://render.com/docs/api
- [P26] Render, audit logs: https://render.com/docs/audit-logs
- [P27] Vercel, REST API and OpenAPI document: https://vercel.com/docs/rest-api and https://openapi.vercel.sh/
- [P28] Vercel, audit logs: https://vercel.com/docs/audit-log
- [P29] Netlify, get started with the API: https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/
- [P30] Netlify, team audit log: https://docs.netlify.com/manage/accounts-and-billing/team-management/team-audit-log/
- [P31] Netlify open-api Go: https://pkg.go.dev/github.com/netlify/open-api/v2
- [P32] Supabase, Management API introduction and OpenAPI document: https://supabase.com/docs/reference/api/introduction and https://api.supabase.com/api/v1-json
- [P33] Supabase, OAuth integration scopes: https://supabase.com/docs/guides/integrations/build-a-supabase-oauth-integration/oauth-scopes
- [P34] Neon, API keys: https://neon.com/docs/manage/api-keys
- [P35] Neon, API reference and OpenAPI document: https://neon.com/docs/reference/api and https://neon.tech/api_spec/release/v2.json
- [P36] Qovery, API token: https://www.qovery.com/docs/configuration/organization/api-token
- [P37] qovery-client-go: https://pkg.go.dev/github.com/qovery/qovery-client-go
- [P38] Tenable, roles: https://developer.tenable.com/docs/roles
- [P39] Tenable, permissions: https://developer.tenable.com/docs/permissions
- [P40] Tenable, authorization: https://developer.tenable.com/docs/authorization
- [P41] Tenable, export vulnerabilities (reference): https://developer.tenable.com/reference/exports-vulns-request-export
- [P42] Tenable, refine vulnerability export requests: https://developer.tenable.com/docs/refine-vulnerability-export-requests
- [P43] Tenable, concurrency limiting: https://developer.tenable.com/docs/concurrency-limiting
- [P44] Tenable, rate limiting: https://developer.tenable.com/docs/rate-limiting
- [P45] Tenable, common asset attributes: https://developer.tenable.com/docs/common-asset-attributes
- [P46] Rapid7, InsightVM Cloud Integrations API v4 (specification `insightvm-api-v4.json` behind this page): https://help.rapid7.com/insightvm/en-us/api/integrations.html
- [P47] Rapid7, managing platform API keys: https://docs.rapid7.com/insight/managing-platform-api-keys/
- [P48] Qualys API (VM and PA) User Guide, version 10.41.1, 16 November 2026: https://cdn2.qualys.com/docs/qualys-api-vmpc-user-guide.pdf
- [P49] Qualys, platform identification: https://www.qualys.com/platform-identification/
- [P50] BMC Helix Discovery documentation (refused automated reading, HTTP 403): https://docs.bmc.com/
- [P51] HubSpot, account activity and audit logs API: https://developers.hubspot.com/docs/api-reference/legacy/account/audit-logs/guide
- [P52] HubSpot, user provisioning API: https://developers.hubspot.com/docs/api-reference/legacy/account/settings/user-provisioning/guide
- [P53] Intercom, list activity logs: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/admins/listactivitylogs
- [P54] Intercom, OAuth scopes: https://developers.intercom.com/docs/build-an-integration/learn-more/authentication/oauth-scopes
- [P55] Zendesk, audit logs: https://developer.zendesk.com/api-reference/ticketing/account-configuration/audit_logs/
- [P56] Zendesk, security and authentication: https://developer.zendesk.com/api-reference/introduction/security-and-auth/
- [P57] Zendesk, users: https://developer.zendesk.com/api-reference/ticketing/users/users/
- [P58] Zendesk, OAuth tokens: https://developer.zendesk.com/api-reference/ticketing/oauth/oauth_tokens/
- [P59] PostHog, API overview: https://posthog.com/docs/api
- [P60] PostHog, members API: https://posthog.com/docs/api/members
- [P61] PostHog, activity log API: https://posthog.com/docs/api/activity-log
- [P62] SendGrid, API key permissions: https://www.twilio.com/docs/sendgrid/api-reference/api-key-permissions
- [P63] SendGrid, retrieve all teammates: https://www.twilio.com/docs/sendgrid/api-reference/teammates/retrieve-all-teammates
- [P64] SendGrid, enforced TLS settings: https://www.twilio.com/docs/sendgrid/api-reference/settings-enforced-tls/retrieve-current-enforced-tls-settings
- [P65] sendgrid-go: https://pkg.go.dev/github.com/sendgrid/sendgrid-go
- [P66] Resend, create API key: https://resend.com/docs/api-reference/api-keys/create-api-key
- [P67] Resend, get domain: https://resend.com/docs/api-reference/domains/get-domain
- [P68] resend-go: https://pkg.go.dev/github.com/resend/resend-go/v3
- [P69] OpenAI, administration API overview: https://developers.openai.com/api/reference/administration/overview
- [P70] OpenAI, OpenAPI specification (official repository, `openapi.yaml` on `master`): https://github.com/openai/openai-openapi
- [P71] openai-go: https://pkg.go.dev/github.com/openai/openai-go
- [P72] Anthropic, Admin API guide: https://platform.claude.com/docs/en/manage-claude/admin-api.md
- [P73] Anthropic, Admin API reference: https://platform.claude.com/docs/en/api/admin.md
- [P74] Anthropic, Usage and Cost Analytics API: https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api.md
- [P75] anthropic-sdk-go: https://pkg.go.dev/github.com/anthropics/anthropic-sdk-go

## Decisions for the owner

| ID | Decision | Recommended |
|---|---|---|
| D-P3-1 | Add capabilities `business_applications` and `ai_providers`, and add scanners to `asset_discovery` | Yes; names match the coverage files |
| D-P3-2 | Fix the vulnerability module before any scanner ships: match assets on host identifiers, keep unmatched findings, carry first found time, explicit severity maps, scanner verified closure, provider `external_id` | Yes; without them a connected scanner makes the register look better than the estate |
| D-P3-3 | One ADR for providers whose API offers no read only credential (Render, Vercel, Netlify, ClickUp, Monday, Better Stack, Resend, OpenAI and Anthropic admin keys): accept with mitigations (dedicated lowest role user, expiring token, GET only allow list in the collector, shown to the customer), or do not build | Accept for OpenAI, Anthropic, Vercel; defer the rest; never build Resend |
| D-P3-4 | Register a Zendesk global OAuth client (Zendesk requires it for multi customer integrations) | Yes, before Zendesk is scheduled; lead time unknown |
| D-P3-5 | Notion: keep in `ticketing` as partial, or treat it as a business application only | Business application only (access list) |
| D-P3-6 | Keep daily pulls of short lived provider audit logs (HubSpot, Render, Linear) as evidence so a 12 month period can be shown | Decide with the evidence retention design; not needed for the first build |
| D-P3-7 | BMC Helix Discovery: research again with documentation access before any commitment | Yes |
| D-P3-8 | Build order inside Phase 3 | Scanners (with D-P3-2), then Supabase, Vercel, DigitalOcean, OpenAI, Anthropic; the rest on customer demand |
