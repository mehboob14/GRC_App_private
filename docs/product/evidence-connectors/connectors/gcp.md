# Google Cloud

| | |
|---|---|
| Capabilities | `cloud_infrastructure`, `asset_discovery` |
| Delivery phase | Phase 3 (signed catalogue, `docs/architecture/integrations.md`: "Azure, GCP") |
| Auth model | Organisation level read only IAM roles granted to one principal: preferably a workload identity federation principal in a pool the customer creates, trusting a Verity token issuer; alternatively Verity's own service account, or a customer service account key (decision D-GCP-1) |
| Shares setup with | Nothing. Google Workspace or Cloud Identity super administrators are evidenced by the Google Workspace connector ([google-workspace.md](google-workspace.md)), not here |
| Go library | `cloud.google.com/go/asset/apiv1`, `cloud.google.com/go/securitycenter/apiv2`, `cloud.google.com/go/resourcemanager/apiv3`, `cloud.google.com/go/kms/apiv1`, `cloud.google.com/go/logging/logadmin`, `cloud.google.com/go/iam/admin/apiv1`, `cloud.google.com/go/orgpolicy/apiv2`, `cloud.google.com/go/storage`, `google.golang.org/api/compute/v1`, `google.golang.org/api/sqladmin/v1`, and `golang.org/x/oauth2/google/externalaccount` for federation [G17] |

Shared rules, outcomes and thresholds follow [aws.md](aws.md) section 5, and the keys proposed there
are reused where the meaning fits, so one check means the same thing on AWS, Azure and Google Cloud.

## 1. What it proves

Google Cloud is organised as one organisation, folders and projects. Read at the organisation, it shows
for every project: which firewall rules let the internet in, whether Cloud SQL accepts unencrypted or
public connections, whether databases are backed up, whether buckets can be read by anyone, who holds
owner and editor roles, how old service account keys are, whether KMS keys rotate, whether Security
Command Center is on and at which tier, and whether audit logs are kept long enough.

Two facts make some checks easier than on other clouds: Admin Activity audit logs are always written
and cannot be turned off [G10], and they are kept 400 days in the `_Required` bucket, which cannot be
changed [G11]. Data at rest is encrypted by Google by default (section 8 explains why that is only half
of NS-01).

What it does not prove: reviews, investigations, exceptions, restore tests, or anything about people's
sign in, which belongs to the identity provider.

## 2. Connecting: method, credentials and permissions

### 2.1 Method (decision D-GCP-1)

Organisations created on or after 3 May 2024 enforce a security baseline by default. It includes
`iam.disableServiceAccountKeyCreation` (no persistent service account keys) and
`iam.allowedPolicyMemberDomains` (IAM grants only to identities of the customer's own organisation or
Workspace customer) [G5]. That decides the options:

| Option | How | Works on a default new organisation | Verity holds |
|---|---|---|---|
| A. Workload identity federation (recommended) | The customer creates a workload identity pool and an OIDC provider that trusts Verity's token issuer, maps one subject to a principal, and grants the roles below to that principal, or to a customer service account the principal may impersonate [G6] | Yes: no key is created and the grant is to a principal in the customer's own pool (that the domain constraint accepts pool principals is unverified) | Nothing per customer; a signing key for its own issuer, in the runtime secret store |
| B. Verity's own service account | The customer grants the roles to `verity-collector@<verity-project>.iam.gserviceaccount.com` | No, unless the customer relaxes `iam.allowedPolicyMemberDomains` | A key or federation for its own service account, once |
| C. Customer service account key | The customer creates a service account and a JSON key and pastes it into Verity | No, unless the customer relaxes `iam.disableServiceAccountKeyCreation` | The key, envelope encrypted per connection |

Option A needs Verity to run an OpenID Connect issuer (discovery document and JWKS over HTTPS). The same
issuer would also serve Azure workload identity federation (azure.md section 2.1) and AWS web identity
roles, so it is one platform piece, not a Google only one. Google warns that a principal able to
impersonate a service account can escalate privilege or hide its identity [G7]; with option A the
impersonation right is limited to one customer service account that holds only read roles.

### 2.2 Permissions

Granted at the **organisation** so every current and future project is covered. A customer without an
organisation (projects under a personal account) grants the same roles per project.

| Role | Read only | Needed for (check keys) | Who can grant it |
|---|---|---|---|
| Security Reviewer (`roles/iam.securityReviewer`): permission to list all resources and the allow policies on them [G2] | yes | `cloud.least_privilege`, `cloud.access_list_exported`, `cloud.storage_public_access_blocked` (public bindings), `cloud.machine_credentials_rotated` (key listing), firewall, KMS and Cloud SQL lists | Organization Administrator (`roles/resourcemanager.organizationAdmin`), or anyone with `setIamPolicy` on the organisation |
| Cloud Asset Viewer (`roles/cloudasset.viewer`): read only access to cloud asset metadata [G3] | yes | the inventory and resource settings for most checks (`assets.resources_registered` and the resource reads in section 4) | same |
| Security Center Findings Viewer (`roles/securitycenter.findingsViewer`): read access to findings [G4] | yes | `cloud.hardening_baseline`, `cloud.threat_findings_triaged` | same |
| Security Center Admin Viewer (`roles/securitycenter.adminViewer`): admin read access to Security Command Center [G4] | yes | `cloud.threat_detection` (which services and tier are on) | same |
| Logging and Monitoring viewer roles, optional (exact role names to confirm) | yes | `cloud.audit_logging` (sinks and bucket retention), `cloud.config_changes_recorded` (log based metrics and alert policies) | same |

Viewer (`roles/viewer`) would also work but is a broad basic role that reads far more than Verity needs;
it is not requested.

**APIs to enable** in the project that holds the pool or service account, because requests are
attributed to it: Cloud Asset, Cloud Resource Manager, Security Command Center, IAM, Cloud Logging and
Cloud Monitoring (the attribution rule is unverified this round; the quota table below shows quotas are
counted per consumer project).

**Plan and licence requirements.**

| Feature | Requirement |
|---|---|
| Asset inventory, IAM, firewall, KMS, Cloud SQL, Storage settings | none |
| Admin Activity audit logs | always on, no cost to read settings [G10] |
| Security Command Center Standard | no additional charge; a limited set of capabilities; activated at the organisation [G9] |
| Security Command Center Premium or Enterprise | paid. Premium adds advanced posture and compliance management, attack paths, threat detection and compliance monitoring for Google Cloud [G9]; Security Health Analytics detectors map to benchmarks such as CIS [G9] |
| Data Access audit logs | off by default except BigQuery [G10]; retention beyond 30 days in `_Default` is billed [G12] |

## 3. Customer setup guide (draft product text)

**Connect Google Cloud**

Verity reads your Google Cloud settings at the organisation level. It never changes anything and never
holds a key.

1. In Verity, open **Connections**, choose **Google Cloud** and select **Connect**. Enter your
   organisation ID. Verity shows a short script and the values it needs.
2. Choose or create a project for Verity, for example `verity-reader`. Enable the APIs Verity lists
   (Cloud Asset, Resource Manager, Security Command Center, IAM, Logging, Monitoring).
3. Open **IAM and Admin**, **Workload Identity Federation**, and create a pool named `verity`. Add an
   **OpenID Connect** provider with the issuer URL and audience Verity shows. Keep the attribute
   mapping Verity shows (`google.subject = assertion.sub`).
4. Open **IAM and Admin**, **IAM** at the **organisation** (not the project). Select **Grant access**.
   Paste the principal Verity shows (it starts with `principal://iam.googleapis.com/`), and add these
   roles: **Security Reviewer**, **Cloud Asset Viewer**, **Security Center Findings Viewer**,
   **Security Center Admin Viewer**, and the logging and monitoring viewer roles Verity lists. You need
   the Organization Administrator role. Or run the script from step 1 in Cloud Shell, which does steps
   2 to 4.
5. Back in Verity, select **Check connection**. Verity lists every folder and project. Untick projects
   outside your audit and give each a reason.
6. For each project, choose its environment: production, staging, development or shared.

What Verity reads is listed under **What we collect** on the connection page.

## 4. What Verity collects

Cloud Asset Inventory is the main source: one paged call returns resources with their configuration,
so Verity does not need a get permission per service. Direct service calls are used where the asset
data is not enough or where the service's own answer is the evidence.

| Resource | API (method and path as documented) | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Folders and projects | `GET https://cloudresourcemanager.googleapis.com/v3/projects:search` [G18] | project id and number, parent folder, state, labels | page token | live |
| Resource inventory and settings | `GET https://cloudasset.googleapis.com/v1/{scope=*/*}:searchAllResources` [G19]; `assets.list` with resource content [G20] | name, asset type, project, location, labels, state, and the resource body per type | `SearchAllResources` 400 per minute per consumer project and 1,500 per minute per organisation; `ListAssets` 100 per minute per consumer project and 800 per minute per organisation; both synchronous and paged [G8] | live |
| IAM bindings everywhere | `GET https://cloudasset.googleapis.com/v1/{scope=*/*}:searchAllIamPolicies` [G21] | resource, role, members (users, groups, service accounts, `allUsers`, `allAuthenticatedUsers`), conditions | 400 per minute per consumer project, 3,000 per minute per organisation [G8] | live |
| Firewall rules | `GET https://compute.googleapis.com/compute/v1/projects/{project}/global/firewalls` [G22]; hierarchical `GET https://compute.googleapis.com/compute/v1/locations/global/firewallPolicies` [G23] | direction, action, priority, source ranges, ports, target tags, disabled | page token; Compute API quotas | live |
| Cloud SQL | `GET https://sqladmin.googleapis.com/v1/projects/{project}/instances` [G24] | `settings.ipConfiguration` (`ipv4Enabled`, `authorizedNetworks`, `sslMode`; `requireSsl` is deprecated in favour of `sslMode`), `settings.backupConfiguration` (enabled, point in time recovery or binary log per engine, retained backups) [G13] | page token | live |
| Cloud Storage buckets | `GET https://storage.googleapis.com/storage/v1/b` [G25] | `iamConfiguration.publicAccessPrevention`, `iamConfiguration.uniformBucketLevelAccess`, `versioning`, `lifecycle`, `encryption.defaultKmsKeyName`, retention policy [G14] | page token | live |
| KMS keys | `GET https://cloudkms.googleapis.com/v1/{parent=projects/*/locations/*/keyRings/*}/cryptoKeys` [G26] | purpose, `rotationPeriod`, `nextRotationTime`, primary version state, `destroyScheduledDuration` [G15] | page token | live |
| Service account keys | `GET https://iam.googleapis.com/v1/{name=projects/*/serviceAccounts/*}/keys` [G27] | key id, `keyType` (`USER_MANAGED` or system managed), `validAfterTime`, `validBeforeTime`, `disabled` [G16]. Never key material | per service account | live |
| Security Command Center findings | `GET https://securitycenter.googleapis.com/v2/{parent=organizations/*/sources/*/locations/*}/findings` [G28] | finding category, class, severity, state, resource, event and create times, compliance mapping | page token; quotas not read this round | per SCC (unverified) |
| Security Command Center services and tier | organisation settings and service enablement (method not verified this round) | tier, services on (Security Health Analytics, Event Threat Detection) | small | live |
| Audit log configuration | `auditConfigs` in the organisation, folder and project allow policies (read with Security Reviewer) | services with Data Access logs, exempted members | with IAM reads | Admin Activity kept 400 days in `_Required`; `_Default` 30 days unless changed [G11][G12] |
| Log sinks and buckets | `GET https://logging.googleapis.com/v2/{parent=organizations/*}/sinks` [G29]; `GET https://logging.googleapis.com/v2/{parent=projects/*/locations/*}/buckets` [G30] | sink destination, filter, include children; bucket retention days, locked | page token | live |
| Log based metrics and alert policies | `GET https://logging.googleapis.com/v2/{parent=projects/*}/metrics` [G31]; `GET https://monitoring.googleapis.com/v3/{name}/alertPolicies` [G32] | metric filter; policy conditions, enabled, notification channels | page token | live |
| Organisation policies | Org Policy API v2 through `cloud.google.com/go/orgpolicy/apiv2` (REST path not re read this round) | constraint, enforced, inherited | page token | live |

Not read: log entries, object contents, secret values, key material, BigQuery data.

## 5. Checks

Population: every resource of the named types in every **in scope** project (section 9). Outcomes as
aws.md section 5: `error` on denied calls; `insufficient_information` when a project could not be read,
paging stopped, or a quota stopped the run; `not_applicable` only when everything was read and the
resource type does not exist.

### 5.1 Existing checks

| Check | Feasible | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|---|
| `cloud.encryption_at_rest` | Yes, mostly by default | Buckets, Cloud SQL instances, persistent disks, BigQuery datasets | Google encrypts these at rest by default, so each store passes with key source "Google managed" or the customer managed key it names (`encryption.defaultKmsKeyName` for buckets); a store whose customer managed key is disabled or destroyed fails | pass, fail, error, insufficient | daily | per store: type, key source, key state | NS-01 (existing: full; proposed partial as aws.md D-AWS-4: the key type per data class, NS-01.C, is a person's decision, and default encryption shows no decision) |
| `cloud.tls_in_transit` | Partly | Cloud SQL instances | `sslMode` refuses unencrypted connections (exact enum values to confirm in fixtures; `requireSsl` read as a fallback for older instances) | pass, fail, error, insufficient | daily | ipConfiguration per instance | NS-02 partial. Load balancer SSL policies are a later increment (not verified this round) |
| `cloud.default_deny_ingress` | Yes | Enabled `INGRESS` `allow` firewall rules and hierarchical policy rules | No allow rule from `0.0.0.0/0` or `::/0` covers all protocols or all ports; internet facing ports only from the setting (default 80, 443) | pass, fail with rules, error, insufficient | daily | rules with ranges, ports, targets | NS-03 partial. The default network's permissive rules are listed separately |
| `cloud.admin_ports_closed` | Yes | Firewall rules; Cloud SQL instances | No enabled allow rule opens 22, 3389 or a database port (setting) from `0.0.0.0/0` or `::/0`; no Cloud SQL instance with `ipv4Enabled` true has `0.0.0.0/0` in `authorizedNetworks`. Recorded exceptions pass until expiry | pass, fail, error, insufficient | daily | rules and instances open to the internet | NS-08 (existing: full; proposed partial as aws.md), NS-03 partial |
| `cloud.hardening_baseline` | Yes on Premium or Enterprise | Organisation | Security Command Center Premium or Enterprise is active and no active Security Health Analytics finding mapped to the CIS Google Cloud benchmark is open, except recorded exceptions. On Standard the check fails with reason `plan`: Standard runs only a limited detector set [G9] | pass; fail with findings or reason `plan`; error; insufficient | daily | tier, findings by benchmark item | NS-04 partial (as today) |
| `cloud.threat_detection` | Yes on Premium or Enterprise | Organisation | Event Threat Detection is enabled at the organisation (a Premium or Enterprise service [G9]) | pass; fail with reason `plan` or the service off; error; insufficient | daily | tier, service states | NS-05 partial (as today) |
| `cloud.key_rotation` | Yes | Enabled symmetric `ENCRYPT_DECRYPT` keys | `rotationPeriod` is set and no longer than the setting (default 365 days), and `nextRotationTime` is in the future. Asymmetric keys cannot rotate on a schedule and are listed for manual records | pass; fail; not applicable when no key; error; insufficient | daily | key, purpose, period, next rotation | NS-06 partial (as today) |
| `cloud.network_segmented` | Partly | Cloud SQL instances in production projects | `ipv4Enabled` is false (private IP only), or the instance has a recorded public need | pass, fail, error, insufficient | daily | ipConfiguration | NS-07 partial: a configuration reading, not a segmentation test |
| `cloud.secrets_managed` | Partly | Production projects | Secret Manager holds at least one secret in each production project (from the asset inventory) | pass, fail, error, insufficient | daily | secret names and dates | NS-09 partial (as aws.md: secrets in configuration are not visible) |
| `cloud.backups_enabled` | Yes | Cloud SQL instances in production projects | `backupConfiguration.enabled` is true and retained backups are at least the setting (default 7); point in time recovery (or binary logging) is on | pass, fail, error, insufficient | daily | backup configuration | BC-01 partial (as today). Persistent disk snapshot schedules follow later |
| `cloud.capacity_alarms` | Partly, later | Cloud SQL instances in production | An enabled alert policy covers disk and CPU utilisation of each instance (metric filter matching to be designed) | pass, fail, error, insufficient | daily | alert policies | BC-04 partial. Not in the first version |
| `cloud.audit_logging` | Yes | Organisation and projects | Admin Activity logs are always written and kept 400 days [G10][G11], which meets the default 365 day setting; where the setting asks for longer retention or for Data Access logs on named services, an organisation sink to a bucket with that retention exists and `auditConfigs` enable those logs | pass, fail with gaps, error, insufficient | daily | audit configs, sinks, bucket retention | LM-02 partial (as today) |
| `cloud.config_changes_recorded` | Recording yes, alerts partly | Organisation and projects | Changes are recorded by Admin Activity logs by design; the check passes when log based metrics with enabled alert policies exist for at least firewall rule changes, IAM policy changes, custom role changes and Cloud SQL configuration changes (filters to confirm in fixtures) | pass, fail with missing alerts, error, insufficient | daily | metrics, filters, policies | LM-03 (existing: full; proposed partial as aws.md) |
| `cloud.root_account_mfa` | Not applicable | | Google Cloud has no root user; organisation super administrators are Workspace or Cloud Identity accounts, judged by the identity provider checks in google-workspace.md | not_applicable with that reason | | | IAM-03 through the identity provider |
| `cloud.least_privilege` | Yes | All bindings from `searchAllIamPolicies` at organisation, folder and project | No user or group holds `roles/owner`, `roles/editor`, `roles/resourcemanager.organizationAdmin`, `roles/iam.securityAdmin` or a custom role granting `*.setIamPolicy` broadly, without a recorded need in Verity | pass, fail with bindings, error, insufficient | daily | binding, role, member, resource, recorded need | IAM-08 partial, IAM-07 partial (as today) |
| `cloud.machine_credentials_rotated` | Yes | `USER_MANAGED`, enabled service account keys | `validAfterTime` within the setting (default 90 days) | pass, fail with keys and ages, not applicable when none (the default on new organisations), error, insufficient | daily | service account, key id, created | IAM-10 partial (as today) |
| `cloud.environments_separated` | Yes, needs the customer's project roles | Projects in scope with roles | At least one project is production, and no project is marked both production and a lower environment | pass, fail, error: roles not set, insufficient | weekly | project list with roles and folder path | SD-12 (existing: full; proposed partial as aws.md), DM-13 partial |
| `cloud.storage_versioned` | Yes | Buckets the customer marks as build output | `versioning.enabled` true | pass, fail, error: none marked, insufficient | daily | versioning per bucket | SD-07 partial (as today) |
| `cloud.storage_lifecycle` | Yes | Buckets the customer marks with a retention class | A lifecycle rule deletes objects no later than the class's period | pass, fail, error: none marked, insufficient | weekly | lifecycle rules | DM-16 partial (as today) |
| `assets.resources_registered` | Yes | Resources of the supported types from `searchAllResources` (Compute instances, GKE clusters, Cloud SQL instances, buckets, BigQuery datasets, Cloud Run services, Cloud Functions, Artifact Registry repositories) | Each is in the Verity asset register (matched on the full resource name as `cloud_resource_id` and `external_id`) or excluded with a reason | pass, fail, error, insufficient | daily | discovered list, matches, exclusions | LM-01 partial (as today) |

### 5.2 Keys proposed in aws.md, reused here

| Check (proposed in aws.md) | Feasible on Google Cloud | Population and predicate | Controls |
|---|---|---|---|
| `cloud.storage_public_access_blocked` | Yes | Every bucket has `publicAccessPrevention` enforced (or inherits it from the organisation policy), and no resource has a binding to `allUsers` or `allAuthenticatedUsers` unless recorded as public by design | NS-04 partial, LM-03 partial |
| `cloud.access_list_exported` | Yes | The complete organisation wide binding list, dated | IAM-02 partial |
| `cloud.flow_logs_enabled` | Partly | Subnets in production projects have flow logs on (field not verified this round) | LM-02 partial |
| `cloud.backup_jobs_succeeding` | Partly | Cloud SQL backup runs in the last 30 days (endpoint not verified this round) | BC-01 partial |
| `cloud.threat_findings_triaged` | Yes on Premium or Enterprise | Active findings of class threat at or above the severity setting older than the response time setting (field names per the v2 finding, to confirm in fixtures) | NS-05 partial |
| `cloud.secrets_rotated` | Partly | Secret Manager secrets with a rotation schedule, or a version newer than the setting (fields not verified this round) | NS-09 partial |
| `assets.retired_resources_closed` | Yes | Assets whose `source` is Google Cloud still exist, or are retired in Verity within 7 days | LM-01 partial |
| `cloud.human_users_mfa`, `cloud.unused_credentials_disabled`, `cloud.backups_protected`, `cloud.tls_certificates_current` | Not in the first version | People sign in through the identity provider; key last use, backup vault locks and certificate stores were not verified this round | |

### 5.3 Needs raised (no new `cloud.*` key)

| Need | Why | For |
|---|---|---|
| NEED cloud_infrastructure: preventive guardrails that block public storage, long lived machine keys and grants to outside identities are enforced at the top of the hierarchy (organisation policies here, service control policies on AWS, Azure Policy deny on Azure) | One enforced organisation policy proves more than a daily scan of each bucket; `iam.disableServiceAccountKeyCreation` and `iam.allowedPolicyMemberDomains` are already enforced on new organisations [G5] | NS-04.B (`approved-configuration-baseline` operating side), IAM-10.D |
| NEED cloud_infrastructure: encryption keys cannot be destroyed at once (scheduled destruction of at least the setting here, soft delete and purge protection in Azure Key Vault) | `destroyScheduledDuration` is read already | NS-06.D, NS-06.E |
| NEED cloud_infrastructure: the threat detection service notifies a named contact or an on call route for high severity findings (Security Command Center notification configs; Defender security contacts) | Shows somebody is told, not that anybody acted | NS-05.C, LM-09 |

## 6. Artifacts and objectives it fills

The `person` source stays on every artifact.

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `data-store-encryption-settings` | NS-01.B, NS-01.C, NS-01.D | NS-01 | person -> person + `cloud.encryption_at_rest` |
| `public-endpoint-tls-scan` | NS-02.B, NS-02.C, NS-02.E | NS-02 | stays person in the first version (only Cloud SQL TLS is read) |
| `firewall-rule-register-with-owner-and` | NS-03.B, NS-03.C | NS-03 | person -> person + `cloud.default_deny_ingress`, `cloud.admin_ports_closed` |
| `inbound-rules-export-admin-ports` | NS-08.B, NS-08.C | NS-08 | person -> person + `cloud.admin_ports_closed` |
| `approved-exceptions-to-the-standard` | NS-04.C, NS-04.D | NS-04 | person -> person + `cloud.hardening_baseline` |
| `alerts-on-drift-that-were-investigated` | LM-03.B, LM-03.C, LM-03.D, NS-04.C, NS-04.D, NS-05.B, NS-08.D | LM-03 | person -> person + `cloud.config_changes_recorded` |
| `key-rotation-records` | NS-06.D, NS-06.E | NS-06 | person -> person + `cloud.key_rotation` |
| `secret-store-rotation-list` | NS-09.B, NS-09.C, NS-09.D, SD-11.C | NS-09 | person -> person + `cloud.secrets_managed` |
| `sample-of-alerts-that-were-investigated` | NS-05.C, NS-05.D, NS-05.E | NS-05 | person -> person + `cloud.threat_findings_triaged` (Premium or Enterprise only) |
| `inventory-of-service-accounts-and-keys` | IAM-10.B, IAM-10.C, IAM-10.D, SD-13.D | IAM-10 | person -> person + `cloud.machine_credentials_rotated` |
| `records-of-rotation-or-review` | IAM-10.D, IAM-10.E | IAM-10 | person -> person + `cloud.machine_credentials_rotated` |
| `list-of-privileged-accounts-with-approval` | IAM-07.B, IAM-01.D, IAM-03.C, IAM-10.C, SD-12.C, SD-13.D, BC-01.D | IAM-07 | person -> person + `cloud.least_privilege` |
| `account-list-export` | IAM-02.B, IAM-10.B, IAM-12.E, HR-03.B | IAM-02 | person -> person + `cloud.access_list_exported` |
| `cloud-accounts-and-production-access` | SD-12.B, SD-12.C, SD-12.E | SD-12 | person -> person + `cloud.environments_separated`, `cloud.least_privilege` |
| `backup-failure-alerts-and-follow-up` | BC-01.B, BC-01.C | BC-01 | person -> person + `cloud.backups_enabled` |
| `evidence-data-was-deleted-when-retention` | DM-08.B, DM-08.C, DM-08.D, DM-16.D, SD-07.E | DM-08 | person -> person + `cloud.storage_lifecycle` |
| `integrity-check-results` | SD-07.B, SD-07.C, SD-07.D | SD-07 | person -> person + `cloud.storage_versioned` |
| `asset-inventory` | LM-01.B, LM-01.C and others | LM-01 | Google Cloud becomes one more provider of `assets.resources_registered` |

## 7. Framework reach

The same controls as [azure.md](azure.md) section 7, with the same SOC 2 criteria (CC6.1, CC6.6,
CC6.7, CC7.1, CC7.2, CC2.1, CC5.2, CC6.2, CC6.3, CC6.8, CC8.1, CC9.1, A1.2, PI1.5, C1.1, C1.2) and
ISO 27001:2022 references (A.5.9, A.5.15 to A.5.18, A.5.28 to A.5.30, A.5.33, A.8.2 to A.8.4, A.8.9,
A.8.10, A.8.13, A.8.15, A.8.16, A.8.18 to A.8.22, A.8.24, A.8.31, A.8.33). Nothing reads "met" from
Google Cloud alone.

## 8. Limits and false assurance traps

- **Default encryption is not a decision.** Every store passes `cloud.encryption_at_rest` because Google
  encrypts by default. The evidence says so in words; NS-01.C (which data needs customer managed keys)
  stays a person's call.
- **Standard tier looks like coverage.** Security Command Center Standard is on for many organisations
  but runs a limited detector set [G9]. `cloud.hardening_baseline` and `cloud.threat_detection` fail
  with reason `plan`, never pass, on Standard.
- **Projects outside the organisation.** Projects under a personal account or a second organisation are
  invisible to an organisation grant. Verity cannot know they exist; the setup asks the customer, and
  the asset register comparison (`assets.resources_registered`) only covers what was connected.
- **Quota per consumer project.** Asset and IAM searches are counted against the calling project [G8].
  A large organisation can exhaust them; the run records `truncated` and the checks are `insufficient`.
- **Data Access logs.** Off by default [G10]. Admin Activity alone does not show who read customer data;
  if the logging standard requires that, the setting must name the services.
- **Admin Activity retention passes by itself.** 400 days covers a 12 month window. It does not prove
  anyone reviews the logs (`evidence-logs-are-reviewed` stays a person's record).
- **Disappearing resources** are marked last seen, never treated as disposed.

## 9. Product and UI

| Item | Design |
|---|---|
| Connect form | Organisation ID; the generated pool, provider and principal values; a Cloud Shell script; for option C a key upload field (hidden unless the owner enables option C) |
| Scope | Folders and projects listed after connect; all in scope by default; leaving one out needs a reason; deleted or pending deletion projects out with a system reason; environment role per project |
| Resource marks | Per bucket: build output, retention class, public by design (with reason); per Cloud SQL instance: public need |
| Health states | connected; federation token refused (issuer, audience or mapping wrong); role missing at the organisation (checks needing it in error); Security Command Center not active; quota exhausted (run truncated) |
| Settings | the AWS thresholds plus: services that need Data Access logs, minimum log retention |
| In product guide needed | **Yes.** Workload identity federation and organisation level grants are unfamiliar to many teams; the script and screenshots carry most of it |

## 10. Implementation notes

- **Auth in Go.** Option A: `golang.org/x/oauth2/google/externalaccount` with a token supplier that asks
  the core for a fresh Verity issued token per run, exchanged at Google's security token service for a
  federated token, then (when a customer service account is used) a short lived access token by
  impersonation. Option B and C use `google.golang.org/api/option` with credentials JSON. Libraries
  resolved on pkg.go.dev on 2026-11-23 [G17].
- **Paging.** Every list returns a page token; Asset searches page per scope. A run stops paging only at
  the end, or records `truncated`.
- **Rate limits.** A per consumer project limiter seeded from [G8] (400 per minute for searches, 100 per
  minute for `ListAssets`), honouring `429` and `RESOURCE_EXHAUSTED` with backoff and jitter.
- **Error mapping.** `PERMISSION_DENIED` on the organisation: health "role missing", affected checks
  `error`. `PERMISSION_DENIED` on one project (a deny policy or a VPC Service Controls perimeter): that
  project's checks `insufficient`, naming it. `SERVICE_DISABLED` for an API: health names the API to
  enable. Security Command Center not active: `cloud.threat_detection` fails with reason `plan`, other
  checks continue.
- **Scope drift.** New projects under the organisation appear automatically and are in scope with a
  banner; moved projects keep their history.
- **Deletion semantics.** Observations keep the full resource name as `external_id`; a missing resource is
  marked last seen, never deleted.
- **Fixtures.** A test organisation with two folders and three projects: one with a firewall open on 22,
  a Cloud SQL instance with `0.0.0.0/0`, a public bucket binding, an old user managed key, a key without
  rotation, and Security Command Center Standard only.

## 11. How comparable platforms do it

Not read this round: the web search budget was exhausted before the competitor pages for Google Cloud
were reached. To be added before build (unverified).

## 12. Sources

All read on 2026-11-23.

- [G2] IAM roles and permissions, IAM (Security Reviewer): https://docs.cloud.google.com/iam/docs/roles-permissions/iam
- [G3] IAM roles and permissions, Cloud Asset (Cloud Asset Viewer): https://docs.cloud.google.com/iam/docs/roles-permissions/cloudasset
- [G4] IAM roles and permissions, Security Command Center: https://docs.cloud.google.com/iam/docs/roles-permissions/securitycenter
- [G5] Secure by default organisations (baseline constraints enforced for organisations created on or after 3 May 2024): https://docs.cloud.google.com/resource-manager/docs/secure-by-default-organizations
- [G6] Workload identity federation (external OIDC or SAML providers, AWS, Azure; direct resource access or service account impersonation): https://docs.cloud.google.com/iam/docs/workload-identity-federation
- [G7] Best practices for using service accounts (impersonation risks): https://docs.cloud.google.com/iam/docs/best-practices-service-accounts
- [G8] Cloud Asset Inventory quotas and limits: https://docs.cloud.google.com/asset-inventory/docs/quota
- [G9] Security Command Center service tiers: https://docs.cloud.google.com/security-command-center/docs/service-tiers
- [G10] Cloud Audit Logs overview: https://docs.cloud.google.com/logging/docs/audit
- [G11] Cloud Logging quotas and limits (retention per bucket): https://docs.cloud.google.com/logging/quotas
- [G12] Configure log buckets: https://docs.cloud.google.com/logging/docs/buckets
- [G13] Cloud SQL Admin API, instances resource: https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/instances
- [G14] Cloud Storage JSON API, buckets resource: https://docs.cloud.google.com/storage/docs/json_api/v1/buckets
- [G15] Cloud KMS CryptoKey resource: https://docs.cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings.cryptoKeys
- [G16] IAM service account keys resource: https://docs.cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts.keys
- [G17] Go packages on pkg.go.dev (each path in the header table resolved): https://pkg.go.dev/cloud.google.com/go and https://pkg.go.dev/golang.org/x/oauth2/google/externalaccount
- [G18] Resource Manager v3 projects.search: https://docs.cloud.google.com/resource-manager/reference/rest/v3/projects/search
- [G19] Cloud Asset searchAllResources: https://docs.cloud.google.com/asset-inventory/docs/reference/rest/v1/TopLevel/searchAllResources
- [G20] Cloud Asset assets.list: https://docs.cloud.google.com/asset-inventory/docs/reference/rest/v1/assets/list
- [G21] Cloud Asset searchAllIamPolicies: https://docs.cloud.google.com/asset-inventory/docs/reference/rest/v1/TopLevel/searchAllIamPolicies
- [G22] Compute firewalls.list: https://docs.cloud.google.com/compute/docs/reference/rest/v1/firewalls/list
- [G23] Compute firewallPolicies.list: https://docs.cloud.google.com/compute/docs/reference/rest/v1/firewallPolicies/list
- [G24] Cloud SQL instances.list: https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/instances/list
- [G25] Cloud Storage buckets.list: https://docs.cloud.google.com/storage/docs/json_api/v1/buckets/list
- [G26] Cloud KMS cryptoKeys.list: https://docs.cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings.cryptoKeys/list
- [G27] IAM serviceAccounts.keys.list: https://docs.cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts.keys/list
- [G28] Security Command Center v2 findings.list: https://docs.cloud.google.com/security-command-center/docs/reference/rest/v2/organizations.sources.locations.findings/list
- [G29] Logging organizations.sinks.list: https://docs.cloud.google.com/logging/docs/reference/v2/rest/v2/organizations.sinks/list
- [G30] Logging buckets.list: https://docs.cloud.google.com/logging/docs/reference/v2/rest/v2/projects.locations.buckets/list
- [G31] Logging metrics.list: https://docs.cloud.google.com/logging/docs/reference/v2/rest/v2/projects.metrics/list
- [G32] Monitoring alertPolicies.list: https://docs.cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alertPolicies/list

## Decisions for the owner

| ID | Decision | Recommended |
|---|---|---|
| D-GCP-1 | Auth: workload identity federation with a Verity token issuer (works on default new organisations), Verity's own service account (needs a domain constraint exception), or a customer key (needs a key creation exception) | Federation. Build the issuer once for Google Cloud, Azure and AWS |
| D-GCP-2 | Treat Security Command Center Standard as `fail` with reason `plan` for the hardening and threat checks | Yes; never pass on Standard |
| D-GCP-3 | Same as D-AWS-4: make NS-01, NS-08, LM-03 and SD-12 mappings partial | Yes, for every cloud |
