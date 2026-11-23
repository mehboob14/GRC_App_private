# Microsoft Azure (Resource Manager and Defender for Cloud)

| | |
|---|---|
| Capabilities | `cloud_infrastructure`, `asset_discovery` |
| Delivery phase | Phase 3 (signed catalogue, `docs/architecture/integrations.md`: "Azure, GCP") |
| Auth model | OAuth 2.0 client credentials for a Microsoft Entra service principal in the customer's tenant, scope `https://management.azure.com/.default`, certificate credential (workload identity federation as a later option). Access is granted only through Azure RBAC role assignments: **Reader** at a management group (or subscription) scope, plus an optional Key Vault metadata role |
| Shares setup with | The Microsoft Entra ID connector ([entra-id.md](entra-id.md)) when the customer connects both: one Verity multi tenant app, one admin consent, Graph permissions from that document, Azure access from RBAC here (decision D-AZ-1) |
| Go library | Azure SDK for Go: `github.com/Azure/azure-sdk-for-go/sdk/azidentity` plus one `sdk/resourcemanager/...` module per service (section 10) and `sdk/security/keyvault/azkeys` for key metadata [S40][S41] |

Shared rules, outcomes and thresholds follow [aws.md](aws.md) section 5 so that one check means the
same thing on every cloud. New `cloud.*` keys proposed in aws.md are reused here where the meaning
fits; anything else is written as a `NEED` for the reconciliation step (AUTHORING section 3).

## 1. What it proves

Azure is where a customer's production may run instead of, or next to, AWS. Through Resource Manager
(ARM) and Microsoft Defender for Cloud it shows, per subscription: how stored data is encrypted, which
network rules let the internet in, whether the activity log is kept beyond Azure's 90 days, whether
databases are backed up, who holds owner level roles, how old storage account keys are, whether keys
in Key Vault rotate, which Defender plans watch the subscription, and how the subscription scores
against the Microsoft cloud security benchmark or CIS.

What it does not prove: that anyone reviewed a rule, investigated an alert, approved an exception or
tested a restore. Those stay with people. Sign in, MFA and administrator roles of the directory belong
to the Entra ID connector, not to this one: Azure has no root user of its own.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

Two ways, one decision (D-AZ-1):

| Option | How | Customer holds | Verity holds |
|---|---|---|---|
| A. Verity multi tenant app (recommended) | Customer admin consents to Verity's app, which creates its service principal in their tenant; the customer then assigns RBAC roles to that service principal | Nothing | One certificate for its own app, in the runtime secret store (as `01-evidence-model.md` section 1.5 says) |
| B. Customer owned app registration | Customer creates a single tenant app, uploads the public certificate Verity generates, assigns RBAC roles | The app registration | The private key, envelope encrypted per connection |

Both sign in with the client credentials grant to the scope `https://management.azure.com/.default`
and, for Key Vault metadata, `https://vault.azure.net/.default` [S32]. Client secrets are not offered:
[entra-id.md](entra-id.md) section 2 already records Microsoft's preference for certificates.

**Workload identity federation** (no stored credential at all) needs an OpenID Connect issuer that
Microsoft can reach, signing RS256 tokens; a federated credential matches the token's `issuer` and
`subject` exactly, needs the single audience `api://AzureADTokenExchange`, and an app holds at most 20
of them [S5]. Verity would have to run that issuer. Worth it only if certificate handling becomes a
burden; it is listed as a later option, not built first.

### 2.2 Permissions

| Permission (built in role or custom) | Read only | Needed for (check keys) | Who can grant it |
|---|---|---|---|
| **Reader** (`acdd72a7-3385-48ef-bd42-f606fba81ae7`), "view all resources, but does not allow you to make any changes" [S1], at the tenant root or a chosen management group, or per subscription | yes | every check except key metadata. `*/read` also covers `Microsoft.Security/*` (Defender assessments, secure scores, pricings, alerts) and `Microsoft.PolicyInsights/policyStates/summarize/read` and `queryResults/read` (policy compliance), which exist as read operations next to their `/action` twins [S4] | Owner, User Access Administrator (`18d7d88d-d35e-4fb5-a5c3-7773c20a72d9`) or Role Based Access Control Administrator (`f58310d9-a9f6-439a-9e8d-f62e7b41a168`) at that scope [S1] |
| **Key Vault metadata reader** (custom role, proposed): data actions `Microsoft.KeyVault/vaults/*/read` and `Microsoft.KeyVault/vaults/secrets/readMetadata/action`, no actions | yes | `cloud.key_rotation`, `cloud.secrets_rotated`, `cloud.tls_certificates_current`, `cloud.secrets_managed` | same as above |
| Built in **Key Vault Reader** (`21090545-7ca7-4776-b22c-e363652d74d2`) as the simple alternative | **no**, see note | same | same |
| Microsoft Graph `Application.Read.All` (application permission), optional | yes | the app registration half of `cloud.machine_credentials_rotated` | an administrator who can grant tenant wide admin consent, see [entra-id.md](entra-id.md) section 2 |

Notes:

- **Key Vault Reader is not purely read only.** Its definition also carries
  `Microsoft.Insights/alertRules/*` and `Microsoft.Support/*` [S2]. The custom role above keeps only the
  two data actions taken from that same definition. Both work only on vaults that use the Azure RBAC
  permission model; a vault on the older access policy model needs an access policy granting key, secret
  and certificate list and get, which is a vault by vault setting (section 8).
- **Security Reader** (`39bc4728-0917-49c7-9d2c-d95423bc2eb4`) is not needed: its reads
  (`Microsoft.Security/*/read`, `Microsoft.Management/managementGroups/read` and others) are inside
  Reader's `*/read` [S2]. It is not requested, to keep the grant to one role.
- **Log Analytics Reader** (`73c42c96-874c-492b-b04d-ab87d138a893`) and **Monitoring Reader**
  (`43d0d8ad-25c7-4714-9337-8ba259a9fe05`) can search log data [S3]. Verity reads log *settings*, not
  log contents, so neither is requested.
- A role assigned at a management group is inherited by every subscription below it, including ones
  created later. Scope drift is therefore mostly growth, which section 9 handles.

**Plan and licence requirements.**

| Feature | Requirement |
|---|---|
| ARM reads, Azure Policy compliance, activity log settings, backup settings | none beyond the subscription |
| Secure score and Microsoft cloud security benchmark recommendations | Foundational CSPM, free and on by default [S18] |
| Regulatory compliance assessments (CIS, ISO 27001 and other standards in Defender) | Defender CSPM, paid [S18] |
| Threat detection | the paid Defender plans per resource type (servers, storage, SQL and others), visible through pricings [S15] |
| Activity log beyond 90 days | a diagnostic setting to a Log Analytics workspace or storage account, billed by Azure Monitor [S33] |

**Vendor side prerequisites** for option A: one multi tenant app registration owned by Verity, with no
Graph permissions unless the customer also connects Entra ID; publisher verification as described in
[entra-id.md](entra-id.md) section 2 (same app, same lead time).

## 3. Customer setup guide (draft product text)

**Connect Microsoft Azure**

Verity reads your Azure settings. It cannot change anything: you give it the Reader role, which only
views.

1. In Verity, open **Connections**, choose **Microsoft Azure** and select **Connect**.
2. Select **Grant consent**. Sign in with a Microsoft account that can approve apps for your whole
   organisation, and accept. This adds an app called **Verity** to your Microsoft Entra ID. If you
   already connected Entra ID to Verity, skip this step: it is the same app.
3. In the Azure portal, open **Management groups**. Choose the group that holds every subscription
   Verity should check. **Tenant Root Group** covers all of them. If you do not use management groups,
   open each subscription instead.
4. Open **Access control (IAM)**, select **Add**, then **Add role assignment**.
5. Choose **Reader**, select **Next**, choose **User, group, or service principal**, select
   **Select members**, search for **Verity**, and select it. Select **Review + assign**. You need the
   Owner, User Access Administrator or Role Based Access Control Administrator role to do this.
6. Optional, for key rotation checks: repeat steps 4 and 5 with the role **Verity Key Vault metadata
   reader**. Verity shows a one click template that creates this role. It reads key and secret dates,
   never their values.
7. Back in Verity, select **Check connection**. Verity lists every subscription it can see. Untick the
   ones that are not part of your audit, and give each a reason.
8. For each subscription, choose its environment: production, staging, development or shared.

What Verity reads is listed under **What we collect** on the connection page.

## 4. What Verity collects

All ARM calls go to `https://management.azure.com`. Resource Graph is used for wide inventory reads,
and direct ARM calls for settings Resource Graph does not carry or where the exact API response is the
evidence.

| Resource | API (method, path, api-version as documented) | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Management groups and subscriptions | `GET /providers/Microsoft.Management/managementGroups/{groupId}/descendants?api-version=2020-05-01` [S10]; `GET /subscriptions?api-version=2022-12-01` [S9] | id, name, parent, state, tags | `nextLink`. ARM token bucket: reads 250 per bucket, refill 25 per second, per subscription and per service principal, also per tenant; `429` with `Retry-After`; headers `x-ms-ratelimit-remaining-subscription-reads` and `-tenant-reads` [S6] | live |
| Inventory of every resource | `POST /providers/Microsoft.ResourceGraph/resources?api-version=2024-04-01` [S8] | id, type, location, resource group, tags, `properties` subset per type | at most 1,000 rows per response, `$skipToken`; quota about 15 queries per 5 seconds per user, headers `x-ms-user-quota-remaining` and `x-ms-user-quota-resets-after`; a principal with access to more than 10,000 subscriptions gets the first 10,000 and `x-ms-tenant-subscription-limit-hit: true`; group subscriptions under 300 per query [S7] | live |
| Policy compliance | `POST /subscriptions/{id}/providers/Microsoft.PolicyInsights/policyStates/latest/summarize?api-version=2024-10-01` [S11] | per assignment and definition: compliant and non compliant resource counts | `$top`; ARM limits | latest evaluation |
| Defender recommendations | `GET /{scope}/providers/Microsoft.Security/assessments?api-version=2020-01-01` [S12] | assessment, resource, status, severity | `nextLink` | live |
| Secure score | `GET /subscriptions/{id}/providers/Microsoft.Security/secureScores?api-version=2020-01-01` [S13]; `.../secureScoreControls?api-version=2020-01-01` [S14] | score, max, percentage, per control | small | live |
| Defender plans | `GET /{scopeId}/providers/Microsoft.Security/pricings?api-version=2024-01-01` [S15] | plan name, `pricingTier` (Free or Standard), `subPlan` | small | live |
| Regulatory compliance | `GET /subscriptions/{id}/providers/Microsoft.Security/regulatoryComplianceStandards?api-version=2019-01-01-preview` [S16] and its controls and assessments | standard, state, passed, failed, skipped counts | `nextLink` | live |
| Security contacts | `GET /subscriptions/{id}/providers/Microsoft.Security/securityContacts?api-version=2023-12-01-preview` [S17] | emails present, roles notified, alert severity (values not kept beyond a count and domain) | small | live |
| Defender alerts | `Microsoft.Security/alerts` list per subscription (path and api-version unverified this round) | alert id, type, severity, status, start and update times | `nextLink` | per Defender (unverified) |
| Storage accounts | `GET /subscriptions/{id}/providers/Microsoft.Storage/storageAccounts?api-version=2026-09-01` [S19] | `encryption` (key source, `requireInfrastructureEncryption`), `minimumTlsVersion`, `supportsHttpsTrafficOnly`, `allowBlobPublicAccess`, `publicNetworkAccess`, `allowSharedKeyAccess`, `keyCreationTime`, `keyPolicy.keyExpirationPeriodInDays` | `nextLink`; storage provider: 100 list and 800 read operations per 5 minutes per subscription and region [S6] | live |
| Blob service settings | `GET .../storageAccounts/{name}/blobServices/default?api-version=2026-09-01` [S20] | `isVersioningEnabled`, `deleteRetentionPolicy`, `containerDeleteRetentionPolicy` | one per account, counts against the 800 reads | live |
| Lifecycle rules | `GET .../storageAccounts/{name}/managementPolicies/default?api-version=2026-09-01` [S21] | rules, filters, delete and tier actions with ages | one per account | live |
| Azure SQL servers | `GET /subscriptions/{id}/providers/Microsoft.Sql/servers?api-version=2025-01-01` [S22] | `publicNetworkAccess`, `minimalTlsVersion`, administrators | `nextLink` | live |
| SQL encryption, auditing, firewall | `GET .../servers/{s}/databases/{d}/transparentDataEncryption`, `GET .../servers/{s}/auditingSettings`, `GET .../servers/{s}/firewallRules` (all `api-version=2025-01-01`) [S23][S25][S24] | TDE `state`; audit state and destination; every firewall rule's start and end address | per server and database | live |
| SQL backups | `GET .../databases/{d}/backupShortTermRetentionPolicies` and `.../backupLongTermRetentionPolicies` (`2025-01-01`) [S26][S27] | `retentionDays`, `diffBackupIntervalInHours`, long term weekly, monthly, yearly retention | per database | live |
| Network security groups | `GET /subscriptions/{id}/providers/Microsoft.Network/networkSecurityGroups?api-version=2026-03-01` [S28] | every rule: `direction`, `access`, `sourceAddressPrefix(es)`, `destinationPortRange(s)`, protocol, priority; `defaultSecurityRules`; attached subnets and network interfaces | `nextLink`; network provider: 10,000 reads per 5 minutes [S6] | live |
| Flow logs | `GET .../networkWatchers/{w}/flowLogs?api-version=2026-03-01` [S29] | target resource, enabled, retention, destination | per watcher | live |
| Key vaults | `GET /subscriptions/{id}/providers/Microsoft.KeyVault/vaults?api-version=2024-11-01` [S30] | `enableSoftDelete`, `softDeleteRetentionInDays`, `enablePurgeProtection`, `enableRbacAuthorization`, `publicNetworkAccess` | `nextLink` | live |
| Keys, secrets and certificates (metadata only) | data plane `GET {vaultBaseUrl}/keys?api-version=2025-07-01` [S31]; `GET {vaultBaseUrl}/keys/{name}/rotationpolicy?api-version=2025-07-01` (documented as needing keys/get) [S32]; secret and certificate lists (paths unverified this round) | key name, type, enabled, created, updated, expiry; rotation `lifetimeActions` (`timeAfterCreate`, `timeBeforeExpiry`) and `expiryTime`; secret and certificate dates. **Never values** | `maxresults`, `nextLink`; Key Vault service throttling (separate guidance, not read this round) | live |
| Activity log export | `GET /subscriptions/{id}/providers/Microsoft.Insights/diagnosticSettings?api-version=2021-05-01-preview` [S34] | destinations (`workspaceId`, `storageAccountId`, `eventHubAuthorizationRuleId`), categories enabled (`Administrative`, `Security`, `Policy` and others) | small | Azure keeps activity log events 90 days, then deletes them [S33] |
| Log Analytics retention | `GET /subscriptions/{id}/providers/Microsoft.OperationalInsights/workspaces?api-version=2026-03-01` | `retentionInDays` of each destination workspace | `nextLink` | live |
| Activity log alerts | `GET /subscriptions/{id}/providers/Microsoft.Insights/activityLogAlerts?api-version=2020-10-01` [S35] | enabled, scopes, condition (operation names), action groups | small | live |
| Backup | `GET /subscriptions/{id}/providers/Microsoft.RecoveryServices/vaults?api-version=2026-11-01` [S36]; `GET .../vaults/{v}/backupProtectedItems` and `.../backupPolicies` (`2026-11-01`) [S37][S38] | protected items with source resource id, policy, retention; vault settings | `nextLink` | live |
| Role assignments | `GET /{scope}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01` [S39] and role definitions | principal id and type, role definition, scope, condition | `nextLink` | live |

Not read: log contents, blob or file contents, secret values, storage keys (listing keys is an action,
not a read, and Reader does not grant it), virtual machine guest settings.

## 5. Checks

Population: every resource of the named types in every **in scope** subscription (section 9).
Outcomes follow aws.md section 5: `error` on a denied call or an unreachable API; `insufficient_information`
when a subscription could not be read, paging stopped early, Resource Graph reported the 10,000
subscription limit, or throttling cut the run; `not_applicable` only when every subscription was read
and none holds the resource type. Thresholds marked "setting" use the same defaults as AWS.

### 5.1 Existing checks

| Check | Feasible | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|---|
| `cloud.encryption_at_rest` | Yes | Storage accounts, SQL databases, managed disks | Storage accounts are always encrypted by the service, so the observation records the key source and infrastructure encryption; every SQL database has TDE `state` Enabled; managed disks report their encryption type (Resource Graph field, unverified name) | pass; fail lists SQL databases with TDE off and disks without encryption; error; insufficient | daily | per store: type, id, encrypted, key source | NS-01 (existing: full; same proposal as aws.md D-AWS-4 to make it partial: the standard and the key type per data class stay with people) |
| `cloud.tls_in_transit` | Partly | Storage accounts, SQL servers | `minimumTlsVersion` is TLS1_2 or later and `supportsHttpsTrafficOnly` is true; SQL `minimalTlsVersion` is 1.2 or later | pass, fail, error, insufficient | daily | settings per resource | NS-02 partial. App Service, Front Door and Application Gateway policies are a later increment (fields not verified this round) |
| `cloud.default_deny_ingress` | Yes | Inbound NSG rules on NSGs attached to a subnet or network interface | No `Allow` inbound rule has source `*`, `Internet`, `0.0.0.0/0` or `::/0` with destination port `*`; open ports to the internet only from the setting (default 80, 443) | pass, fail with rules, error, insufficient | daily | every inbound allow rule with source, ports, attachment | NS-03 partial. Subnets and interfaces with no NSG are listed for review (Azure's behaviour without an NSG is unverified this round) |
| `cloud.admin_ports_closed` | Yes | Inbound NSG rules; SQL server firewall rules | No allow rule opens 22, 3389 or a database port (setting, AWS defaults) to `*`, `Internet`, `0.0.0.0/0` or `::/0`; no SQL firewall rule spans `0.0.0.0` to `255.255.255.255`. The `0.0.0.0` to `0.0.0.0` rule ("allow Azure services") is listed as a finding with its own reason. Recorded exceptions pass until expiry | pass, fail with rules, error, insufficient | daily | public rules, exceptions applied | NS-08 (existing: full; proposed partial as in aws.md), NS-03 partial |
| `cloud.hardening_baseline` | Yes, two routes | Subscriptions in scope | Route 1 (Defender CSPM): the CIS Microsoft Azure Foundations standard is enabled in regulatory compliance and has no failed control except recorded exceptions. Route 2 (free): a CIS or Microsoft cloud security benchmark policy initiative is assigned and its summarized policy states show no non compliant resource except exceptions. The connection setting says which baseline the customer's standard names | pass; fail with failed controls or non compliant resources; error when neither route is set up; insufficient | daily | standard or initiative, counts, failing items | NS-04 partial (as today). A secure score is reported for context only; a score is not a pass |
| `cloud.threat_detection` | Yes | Subscriptions in scope, with the resource types present in each | For every resource type present that has a Defender plan (servers, storage, SQL, Key Vault, Resource Manager at least), that plan's `pricingTier` is Standard (exact plan names to confirm in fixtures) | pass, fail with missing plans, error, insufficient | daily | pricings per subscription, resource types present | NS-05 partial (as today) |
| `cloud.key_rotation` | Yes, with the Key Vault role | Enabled RSA and EC keys in vaults in scope | Each key has a rotation policy with a `Rotate` action whose `timeAfterCreate` (or `timeBeforeExpiry` against `expiryTime`) is within the setting (default 365 days), or its current version is younger than the setting | pass; fail; not applicable when no key exists; error when the role is missing; insufficient when a vault uses access policies Verity was not given | daily | key, version dates, policy | NS-06 partial (as today) |
| `cloud.network_segmented` | Partly | SQL servers, storage accounts and key vaults marked as data stores | `publicNetworkAccess` is Disabled (private endpoints only), or the store has a recorded public need | pass, fail, error, insufficient | daily | public network setting per store | NS-07 partial. A configuration reading, not the segmentation test NS-07.D asks for |
| `cloud.secrets_managed` | Partly | Production subscriptions | At least one key vault holds secrets in each production subscription. Secrets kept in app settings are not visible without reading their values, so that half stays with `vcs.secret_scanning_enabled` and a person | pass, fail, error, insufficient | daily | vault and secret names, dates (no values) | NS-09 partial (as today) |
| `cloud.backups_enabled` | Yes | SQL databases and virtual machines in production subscriptions | SQL short term `retentionDays` at least the setting (default 7); each production VM is a protected item of a Recovery Services vault whose policy keeps backups at least the setting | pass, fail, error, insufficient | daily | per store: method, retention, policy | BC-01 partial (as today). PostgreSQL and MySQL flexible servers follow when their fields are verified |
| `cloud.capacity_alarms` | Not in the first version | | Metric alerts exist in Azure Monitor, but the alert list API was not verified this round | | | | BC-04: stays with people until added |
| `cloud.audit_logging` | Yes | Subscriptions in scope | A subscription diagnostic setting sends at least the `Administrative`, `Security` and `Policy` categories to a Log Analytics workspace whose `retentionInDays` is at least the setting (default 365), or to a storage account whose lifecycle keeps logs at least that long. Without one, the activity log lasts 90 days [S33] and the check fails | pass, fail, error, insufficient | daily | diagnostic settings, destination retention | LM-02 partial (as today) |
| `cloud.config_changes_recorded` | Recording yes, alerts partly | Subscriptions in scope | The activity log records control plane changes by design; the check passes when enabled activity log alerts cover at least: NSG and NSG rule changes, policy assignment changes, SQL firewall rule changes, security solution changes (the CIS set; exact operation names to confirm in fixtures) | pass, fail with missing alerts, error, insufficient | daily | alerts, operations, action groups | LM-03 (existing: full; proposed partial as in aws.md: investigating each alert is a person's record) |
| `cloud.root_account_mfa` | Not applicable | | Azure has no root user. Owners and Global Administrators are Entra identities, judged by `idp.mfa_enforced` and `idp.admin_mfa_phishing_resistant` in [entra-id.md](entra-id.md) | not_applicable with that reason | | | IAM-03 through the identity provider |
| `cloud.least_privilege` | Yes | Role assignments at management group, subscription and resource group scope | No user, group or service principal holds Owner, Contributor, User Access Administrator, Role Based Access Control Administrator, or a custom role whose actions include `*`, at management group or subscription scope, without a recorded need in Verity (owner, reason, review date). Break glass accounts pass when recorded | pass, fail with principals, error, insufficient | daily | assignment, role, scope, recorded need | IAM-08 partial, IAM-07 partial (as today) |
| `cloud.machine_credentials_rotated` | Yes, app half optional | Storage accounts with `allowSharedKeyAccess` true; app registration secrets and certificates when Graph `Application.Read.All` is granted | `keyCreationTime` of both storage keys within the setting (default 90 days), or a `keyPolicy` with expiry within it; app credentials created within the setting | pass, fail with credentials and ages, error, insufficient when the Graph half is not granted and app credentials are in scope | daily | account, key created, policy; app, credential start | IAM-10 partial (as today) |
| `cloud.environments_separated` | Yes, needs the customer's subscription roles | Subscriptions in scope with the environment the customer gives each | At least one subscription is production, and no subscription is marked both production and a lower environment | pass, fail, error: roles not set, insufficient | weekly | subscription list with roles and management group path | SD-12 (existing: full; proposed partial as in aws.md), DM-13 partial |
| `cloud.storage_versioned` | Yes | Storage accounts the customer marks as build output | `isVersioningEnabled` true and blob soft delete on | pass, fail, error: none marked, insufficient | daily | blob service settings | SD-07 partial (as today) |
| `cloud.storage_lifecycle` | Yes | Storage accounts the customer marks with a retention class | A management policy deletes blobs no later than the class's period | pass, fail, error: none marked, insufficient | weekly | lifecycle rules | DM-16 partial (as today) |
| `assets.resources_registered` | Yes | Resources of the supported types from Resource Graph (virtual machines, scale sets, SQL servers and databases, storage accounts, key vaults, AKS clusters, App Service apps, container registries, public IPs) | Each is in the Verity asset register (matched on the ARM resource id as `cloud_resource_id` and `external_id`) or excluded with a reason | pass, fail with unregistered resources, error, insufficient | daily | discovered list, matched asset, exclusions | LM-01 partial (as today) |

### 5.2 Keys proposed in aws.md, reused here

| Check (proposed in aws.md) | Feasible on Azure | Azure population and predicate | Controls |
|---|---|---|---|
| `cloud.storage_public_access_blocked` | Yes | Every storage account has `allowBlobPublicAccess` false, or `publicNetworkAccess` Disabled. That the account flag blocks anonymous access for every container is Microsoft's documented behaviour (page not re read this round, unverified) | NS-04 partial, LM-03 partial (as aws.md) |
| `cloud.access_list_exported` | Yes | All role assignments at every in scope scope, with principal type, read completely for every subscription; principal names resolved from the Entra ID connector when connected | IAM-02 partial |
| `cloud.flow_logs_enabled` | Yes | Each virtual network (or NSG) in a production subscription with at least one network interface has an enabled flow log | LM-02 partial |
| `cloud.backup_jobs_succeeding` | Partly | Recovery Services backup job history (endpoint not verified this round); SQL point in time restore is a platform feature, so SQL databases pass on retention alone | BC-01 partial |
| `cloud.backups_protected` | Partly | Vault immutability and soft delete settings (field names not verified this round) | BC-01 partial |
| `cloud.secrets_rotated` | Yes, with the Key Vault role | Each enabled secret has an expiry, or was updated within the setting (default 365 days); values never read | NS-09 partial, IAM-10 partial |
| `cloud.threat_findings_triaged` | Yes | Defender alerts at or above the severity setting (default high) with status Active older than the response time setting (default 7 days) | NS-05 partial |
| `cloud.tls_certificates_current` | Yes, with the Key Vault role | Certificates in Key Vault: none expired, none expiring within 14 days without auto renewal | NS-02 partial |
| `assets.retired_resources_closed` | Yes | Assets whose `source` is Azure still exist in Resource Graph, or are retired in Verity within 7 days | LM-01 partial |
| `cloud.human_users_mfa`, `cloud.unused_credentials_disabled` | Not applicable | People sign in through Entra ID; see entra-id.md | |

### 5.3 Needs raised (no new `cloud.*` key)

| Need | Why | For |
|---|---|---|
| NEED cloud_infrastructure: every key vault that holds keys, secrets or certificates has soft delete and purge protection on | A vault without purge protection lets one administrator destroy a key and every copy at once; `enableSoftDelete` and `enablePurgeProtection` are read already | NS-06.D and NS-06.E (`key-rotation-records`), BC-01 for keys that protect backups |
| NEED cloud_infrastructure: the threat detection service notifies a named security contact or an on call route for high severity alerts | Defender `securityContacts` shows whether anyone is told; it does not show anyone acted | NS-05.C (`procedure-for-responding-to-threat-detection` operating side), LM-09 |
| The coverage need "configuration rule findings are listed with first seen and resolved times, and each open past the response time is flagged" (NS-04, NS-05, NS-08, LM-03) | Defender assessments give status per resource; first seen time is not confirmed in the fields read this round | the reconciliation step decides whether `cloud.threat_findings_triaged` widens or a new key is added |

## 6. Artifacts and objectives it fills

The `person` source stays on every artifact (rule 1 of `01-evidence-model.md`).

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `data-store-encryption-settings` | NS-01.B, NS-01.C, NS-01.D | NS-01 | person -> person + `cloud.encryption_at_rest` |
| `public-endpoint-tls-scan` | NS-02.B, NS-02.C, NS-02.E | NS-02 | person -> person + `cloud.tls_in_transit` (Azure front doors only), `cloud.tls_certificates_current` |
| `firewall-rule-register-with-owner-and` | NS-03.B, NS-03.C | NS-03 | person -> person + `cloud.default_deny_ingress`, `cloud.admin_ports_closed` (owner and purpose stay with people) |
| `inbound-rules-export-admin-ports` | NS-08.B, NS-08.C | NS-08 | person -> person + `cloud.admin_ports_closed` |
| `approved-exceptions-to-the-standard` | NS-04.C, NS-04.D | NS-04 | person -> person + `cloud.hardening_baseline` (lists what fails; the approval is a person's) |
| `alerts-on-drift-that-were-investigated` | LM-03.B, LM-03.C, LM-03.D, NS-04.C, NS-04.D, NS-05.B, NS-08.D | LM-03 | person -> person + `cloud.config_changes_recorded` |
| `key-rotation-records` | NS-06.D, NS-06.E | NS-06 | person -> person + `cloud.key_rotation` |
| `secret-store-rotation-list` | NS-09.B, NS-09.C, NS-09.D, SD-11.C | NS-09 | person -> person + `cloud.secrets_managed`, `cloud.secrets_rotated` |
| `sample-of-alerts-that-were-investigated` | NS-05.C, NS-05.D, NS-05.E | NS-05 | person -> person + `cloud.threat_findings_triaged` |
| `inventory-of-service-accounts-and-keys` | IAM-10.B, IAM-10.C, IAM-10.D, SD-13.D | IAM-10 | person -> person + `cloud.machine_credentials_rotated` |
| `records-of-rotation-or-review` | IAM-10.D, IAM-10.E | IAM-10 | person -> person + `cloud.machine_credentials_rotated` |
| `list-of-privileged-accounts-with-approval` | IAM-07.B, IAM-01.D, IAM-03.C, IAM-10.C, SD-12.C, SD-13.D, BC-01.D | IAM-07 | person -> person + `cloud.least_privilege` |
| `account-list-export` | IAM-02.B, IAM-10.B, IAM-12.E, HR-03.B | IAM-02 | person -> person + `cloud.access_list_exported` |
| `cloud-accounts-and-production-access` | SD-12.B, SD-12.C, SD-12.E | SD-12 | person -> person + `cloud.environments_separated`, `cloud.least_privilege` |
| `backup-failure-alerts-and-follow-up` | BC-01.B, BC-01.C | BC-01 | person -> person + `cloud.backups_enabled`, `cloud.backup_jobs_succeeding` |
| `evidence-data-was-deleted-when-retention` | DM-08.B, DM-08.C, DM-08.D, DM-16.D, SD-07.E | DM-08 | person -> person + `cloud.storage_lifecycle` (rules exist; deletions that ran are not read) |
| `integrity-check-results` | SD-07.B, SD-07.C, SD-07.D | SD-07 | person -> person + `cloud.storage_versioned` |
| `asset-inventory` | LM-01.B, LM-01.C and the other objectives that cite it | LM-01 | today `verity.assets.owner_assigned` + `assets.resources_registered` (already a source); Azure becomes one more provider |
| `evidence-logs-are-reviewed` | LM-02.B, LM-02.D | LM-02 | stays person: the export setting is shown by `cloud.audit_logging`, the review is not |

## 7. Framework reach

Through the controls above (mappings from `seed/content/{soc2,iso27001}/template_requirements.json`):

| Control | SOC 2 | ISO 27001:2022 |
|---|---|---|
| NS-01, NS-06, NS-09 | CC6.1 | A.8.24, A.5.17 |
| NS-02 | CC6.7 | A.5.14, A.8.21, A.8.24 |
| NS-03, NS-07, NS-08 | CC6.6, CC6.1 | A.8.20, A.8.22 |
| NS-04 | CC6.1, CC7.1, CC5.2 | A.8.9, A.8.18, A.8.19, A.8.20, A.5.23 |
| NS-05 | CC6.8, CC7.2 | A.8.16 |
| LM-01 | CC2.1, CC6.1 | A.5.9 |
| LM-02 | CC7.2, CC2.1 | A.8.15, A.5.28 |
| LM-03 | CC7.1 | A.8.9, A.8.20 |
| BC-01 | A1.2, CC9.1, PI1.5 | A.8.13, A.5.29, A.5.30, A.5.33 |
| IAM-02, IAM-07, IAM-08, IAM-10 | CC6.1, CC6.2, CC6.3, CC5.2 | A.5.15, A.5.16, A.5.18, A.8.2, A.8.3, A.8.4 |
| SD-07, SD-12, DM-13, DM-16 | PI1.5, CC8.1, C1.1, C1.2 | A.8.31, A.8.33, A.8.10 |

No criterion reads "met" from Azure alone (CF-4): every control here also needs its document and a
person's review.

## 8. Limits and false assurance traps

- **A clean result over part of the estate.** Reader at one subscription when the customer has five
  shows five times less. Verity lists every subscription the tenant reports through the management group
  tree and marks unconnected ones; a check is `insufficient` while an in scope subscription is unread.
- **Resource Graph caps.** More than 10,000 visible subscriptions returns a partial answer with a header
  flag [S7]; Verity treats it as `insufficient`, never as the whole estate.
- **Free tier versus paid.** Secure score is free; CIS assessments in Defender need Defender CSPM [S18].
  Without it, `cloud.hardening_baseline` must use an assigned policy initiative or report `fail` with
  reason `plan`, never pass on a secure score.
- **Activity log is 90 days.** A Type 2 period of 12 months cannot be evidenced from Azure's own
  store; only the export proves retention [S33].
- **Key Vault permission models.** Vaults on access policies ignore RBAC data roles. Their keys are
  `insufficient` until the customer adds an access policy, and the check says which vaults.
- **"Allow Azure services" on SQL.** The `0.0.0.0` firewall rule opens the server to every Azure tenant's
  services, not just the customer's. It is reported, not silently passed.
- **Defender plans per resource type.** A Standard plan for servers says nothing about storage. The
  check compares plans with resource types actually present.
- **Deleted resources.** A resource that disappears from Resource Graph is not proof of disposal;
  `assets.retired_resources_closed` asks a person to retire it in Verity.
- **Encryption by default.** Storage encryption cannot be turned off, so a pass shows the platform
  default, not a customer decision on key ownership (NS-01.C).

## 9. Product and UI

| Item | Design |
|---|---|
| Connect form | Option A: tenant ID (or the primary domain) and **Grant consent**. Option B: tenant ID, client ID, and Verity's generated certificate to download and upload |
| Scope | After connect, Verity lists management groups and subscriptions. Every subscription is in scope by default; leaving one out needs a reason (AU-9). Disabled subscriptions are out with a system reason. Each subscription gets an environment role |
| Resource marks | Per storage account: build output, retention class; per store: data store, public by design (with reason) |
| Health states | connected; consent missing; Reader missing at a scope; Key Vault role missing (only key checks in error); throttled (run truncated); subscription limit reached |
| Settings | the AWS thresholds (key and credential ages, backup retention, database ports, open web ports, log retention, response time), plus the baseline route (CIS or Microsoft cloud security benchmark) |
| In product guide needed | **Yes.** RBAC assignment at a management group is unfamiliar to many customers, and the consent and role steps happen in two different portals |

## 10. Implementation notes

- **Libraries (all on pkg.go.dev, checked 2026-11-23 [S41]):** `sdk/azidentity` (`NewClientCertificateCredential`;
  `NewClientAssertionCredential` for later federation), `sdk/resourcemanager/managementgroups/armmanagementgroups`,
  `resources/armsubscriptions`, `resourcegraph/armresourcegraph`, `policyinsights/armpolicyinsights`,
  `security/armsecurity`, `storage/armstorage`, `sql/armsql`, `network/armnetwork`,
  `keyvault/armkeyvault`, `monitor/armmonitor`, `recoveryservices/armrecoveryservicesbackup`,
  `authorization/armauthorization`, and `sdk/security/keyvault/azkeys` for key metadata. Pin each module's
  current major version in `go.mod`; several carry `/vN` suffixes.
- **Tokens.** One token per resource (ARM, Key Vault); azidentity caches and refreshes. For option A,
  the token request names the customer tenant ID; a tenant that has not consented returns an Entra error
  that maps to the "consent missing" health state, not to `fail`.
- **Throttling.** Honour `Retry-After` on 429 and read the remaining read headers [S6]; for Resource
  Graph, back off on `x-ms-user-quota-remaining: 0` for `x-ms-user-quota-resets-after` [S7]. Group
  subscriptions in Resource Graph queries (under 300 per query). Storage account list operations are
  scarce (100 per 5 minutes per region), so take the account list from Resource Graph and call ARM only
  for blob service and management policy reads.
- **Paging.** `nextLink` for ARM, `$skipToken` for Resource Graph, `nextLink` for Key Vault data plane.
  A run that cannot finish paging records `truncated`.
- **Error mapping.** 401 or `AADSTS` consent errors: health `consent missing`, every check `error`.
  403 `AuthorizationFailed` on a scope: that scope's checks `error`, others continue. Key Vault 403 on a
  vault: key checks `insufficient` naming the vault. 404 on a Defender endpoint for an unregistered
  `Microsoft.Security` provider: `error` with reason "Defender for Cloud not registered".
- **Scope drift.** Each run re-lists the management group tree; new subscriptions appear as in scope
  with a banner, removed ones keep history and stop being read.
- **Deletion semantics.** A resource missing from a run is marked `last_seen_at`, never deleted;
  observations keep the ARM id as `external_id`.
- **Fixtures.** Recorded with go-vcr against a test tenant with two subscriptions under one management
  group: one compliant, one with an open NSG, a SQL server with TDE off, a vault on access policies, no
  diagnostic setting.

## 11. How comparable platforms do it

| Platform | Auth and scope | What they test | Source |
|---|---|---|---|
| Vanta | A service principal with admin consent; Microsoft Graph for directory data and the Azure Reader RBAC role at a subscription or management group (Tenant Root Group for tenant wide); Key Vault Reader when keys are in Key Vault; connected by a Global Administrator or Privileged Role Administrator | Cloud resource configuration tests (detail not read this round) | [S42][S43] |
| Drata, Secureframe, Sprinto | Not read this round (web search budget exhausted); to be added before build | | unverified |

## 12. Sources

All read on 2026-11-23.

- [S1] Azure built in roles, and the General category (Reader holds the `*/read` control plane action): https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles and https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/general
- [S2] Azure built in roles for Security (Key Vault Reader, Security Reader definitions): https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/security
- [S3] Azure built in roles for Monitor: https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/monitor
- [S4] Azure permissions for management and governance (Microsoft.PolicyInsights operations): https://learn.microsoft.com/en-us/azure/role-based-access-control/permissions/management-and-governance
- [S5] Workload identity federation considerations: https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-considerations
- [S6] Azure Resource Manager throttling: https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/request-limits-and-throttling
- [S7] Resource Graph throttled requests: https://learn.microsoft.com/en-us/azure/governance/resource-graph/concepts/guidance-for-throttled-requests
- [S8] Resource Graph resources REST: https://learn.microsoft.com/en-us/rest/api/azureresourcegraph/resourcegraph/resources/resources
- [S9] Subscriptions list: https://learn.microsoft.com/en-us/rest/api/resources/subscriptions/list
- [S10] Management group descendants: https://learn.microsoft.com/en-us/rest/api/managementgroups/management-groups/get-descendants
- [S11] Policy states summarize for subscription: https://learn.microsoft.com/en-us/rest/api/policyinsights/policy-states/summarize-for-subscription
- [S12] Defender for Cloud assessments list: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/assessments/list
- [S13] Secure scores list: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/secure-scores/list
- [S14] Secure score controls list: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/secure-score-controls/list
- [S15] Defender pricings list: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/pricings/list
- [S16] Regulatory compliance standards list: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/regulatory-compliance-standards/list
- [S17] Security contacts list: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/security-contacts/list
- [S18] Cloud security posture management (Foundational CSPM and Defender CSPM features): https://learn.microsoft.com/en-us/azure/defender-for-cloud/concept-cloud-security-posture-management
- [S19] Storage accounts list: https://learn.microsoft.com/en-us/rest/api/storagerp/storage-accounts/list
- [S20] Blob service properties: https://learn.microsoft.com/en-us/rest/api/storagerp/blob-services/get-service-properties
- [S21] Storage management policies: https://learn.microsoft.com/en-us/rest/api/storagerp/management-policies/get
- [S22] SQL servers list: https://learn.microsoft.com/en-us/rest/api/sql/servers/list
- [S23] SQL transparent data encryption: https://learn.microsoft.com/en-us/rest/api/sql/transparent-data-encryptions/list-by-database
- [S24] SQL firewall rules: https://learn.microsoft.com/en-us/rest/api/sql/firewall-rules/list-by-server
- [S25] SQL server auditing settings: https://learn.microsoft.com/en-us/rest/api/sql/server-blob-auditing-policies/list-by-server
- [S26] SQL short term retention: https://learn.microsoft.com/en-us/rest/api/sql/backup-short-term-retention-policies/list-by-database
- [S27] SQL long term retention: https://learn.microsoft.com/en-us/rest/api/sql/long-term-retention-policies/list-by-database
- [S28] Network security groups list all: https://learn.microsoft.com/en-us/rest/api/virtualnetwork/network-security-groups/list-all
- [S29] Flow logs list: https://learn.microsoft.com/en-us/rest/api/network-watcher/flow-logs/list
- [S30] Key vaults list by subscription: https://learn.microsoft.com/en-us/rest/api/keyvault/keyvault/vaults/list-by-subscription
- [S31] Key Vault get keys: https://learn.microsoft.com/en-us/rest/api/keyvault/keys/get-keys/get-keys
- [S32] Key Vault get key rotation policy: https://learn.microsoft.com/en-us/rest/api/keyvault/keys/get-key-rotation-policy/get-key-rotation-policy
- [S33] Azure Monitor activity log (90 day retention): https://learn.microsoft.com/en-us/azure/azure-monitor/platform/activity-log
- [S34] Subscription diagnostic settings: https://learn.microsoft.com/en-us/rest/api/monitor/subscription-diagnostic-settings/list
- [S35] Activity log alerts: https://learn.microsoft.com/en-us/rest/api/monitor/activity-log-alerts/list-by-subscription-id
- [S36] Recovery Services vaults: https://learn.microsoft.com/en-us/rest/api/recoveryservices/vaults/list-by-subscription-id
- [S37] Backup protected items: https://learn.microsoft.com/en-us/rest/api/backup/backup-protected-items/list
- [S38] Backup policies: https://learn.microsoft.com/en-us/rest/api/backup/backup-policies/list
- [S39] Role assignments list for scope: https://learn.microsoft.com/en-us/rest/api/authorization/role-assignments/list-for-scope
- [S40] azidentity: https://pkg.go.dev/github.com/Azure/azure-sdk-for-go/sdk/azidentity
- [S41] Azure SDK for Go module pages (each path in section 10 resolved on pkg.go.dev): https://pkg.go.dev/github.com/Azure/azure-sdk-for-go/sdk/resourcemanager
- [S42] Vanta, Azure integration guide: https://help.vanta.com/en/articles/15693150-azure-integration-guide
- [S43] Vanta, Azure quickstart: https://help.vanta.com/en/articles/15605280-azure-quickstart

## Decisions for the owner

| ID | Decision | Recommended |
|---|---|---|
| D-AZ-1 | One Verity multi tenant app shared with the Entra ID connector, or a customer owned app registration per connection | Shared multi tenant app with a certificate: one consent, no customer secret |
| D-AZ-2 | Ship a custom "Key Vault metadata reader" role template instead of asking for the built in Key Vault Reader, which also allows classic alert rule and support ticket writes | Custom role |
| D-AZ-3 | Hardening baseline route: require Defender CSPM for CIS, or accept a free policy initiative | Accept both; the customer's hardening standard names which |
| D-AZ-4 | Same as D-AWS-4: make NS-01, NS-08, LM-03 and SD-12 mappings partial | Yes, for every cloud |
