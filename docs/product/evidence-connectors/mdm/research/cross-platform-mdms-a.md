# Cross platform MDM and UEM, part A: Workspace ONE, JumpCloud, Hexnode, ManageEngine

Round 2 research under [BRIEF.md](BRIEF.md). Round 1 did not cover these four products, so everything here is
new. Verity reads only; no endpoint below that changes state is ever called.

Status markers: "V [n]" means confirmed in source n, read in this session. "unverified" means not confirmed
(not found, not documented, or only seen in a community post or a search snippet).

## 0. Summary

| Product | Read only credential | Best for | Biggest gap |
|---|---|---|---|
| Omnissa Workspace ONE UEM | yes: OAuth client (SaaS) or basic auth plus tenant code (on premises), with a custom role of "Read Only" REST permissions | full security object per device (encryption, passcode, SIP, escrow flags), ownership, DEP | the "read" security object also carries recovery key fields; no command history read API; firewall and antivirus only as customer compliance rules |
| JumpCloud | yes: service account with the Read Only role (OAuth client credentials) | it is also the directory: device to person to account state in one source; osquery data (firewall, BitLocker, FileVault, apps) hourly | System Insights kept 90 days only; wipe results need Directory Insights (not in the Device Management package) and confirm receipt, not execution |
| Hexnode UEM | **no**: one API key per portal with admin power; custom roles have API disabled | enrolment, last report, apps with a deny list flag, per device action status | documented API returns no encryption, passcode or firewall fields although the console shows them |
| ManageEngine Endpoint Central and MDM Plus | yes: Zoho OAuth with per module READ scopes (cloud); API key with per module Read toggles (on premises) | patch health, installed and prohibited software (EP-03.E), Windows firewall per profile, mobile security object | encryption read scope also returns BitLocker recovery keys; firmware passwords sit under the MDM inventory read scope; low per endpoint rate limits with a 5 minute lockout |

## 1. Scope

| Product | Editions and API versions covered | Platforms | Date read |
|---|---|---|---|
| Workspace ONE UEM | SaaS and on premises; REST releases 2410 to 2607 listed, read 2607: MDM API v1 to v4, System API v1 [33][34][35][36] | Windows, macOS, iOS, iPadOS, Android, Linux, ChromeOS (ChromeOS and Linux depth unverified) | 2026-11-26 |
| JumpCloud | API v1 (OpenAPI 3.1), API v2 (through the official SDK references, the 3.6 MB v2 spec was not read in full), Directory Insights API 1.0 [1][2][26] | Windows, macOS, Linux (agent); macOS, iOS, iPadOS (Apple MDM); Windows MDM; Android EMM. ChromeOS: not listed by JumpCloud (unverified) | 2026-11-26 |
| Hexnode UEM | REST API v1 on `<portal>.hexnodemdm.com` [43] | iOS, iPadOS, macOS, tvOS, Android, Windows, Linux (plan dependent [55]); ChromeOS unverified | 2026-11-26 |
| ManageEngine | Endpoint Central cloud API (`/api/1.4` legacy and `/dcapi`) [60]; Endpoint Central on premises (API key) [73]; Mobile Device Manager Plus API v1 [77] | Endpoint Central agent: Windows, macOS, Linux [61]; MDM: iOS, Android, Windows, macOS, Chromebook enrolment [74] | 2026-11-26 |

---

## A. Omnissa Workspace ONE UEM

### A.1 Editions and API access

- REST API is a tenant setting: Groups & Settings > All Settings > System > Advanced > API > REST API >
  Enable API Access. V [38]
- Editions (Essentials, Standard, Advanced, Enterprise) and whether any edition lacks the REST API:
  unverified (no official edition page could be read).
- OAuth clients exist only in SaaS. On premises uses basic, certificate or directory authentication. V [38][39]

### A.2 Read only credential, step by step

SaaS (recommended):

1. Create a role: Accounts > Administrators > Roles (role creation path from [39], which links to "Create
   Administrator Role"; exact menu path unverified). Tick only these Read Only REST permissions V [39]:
   `REST API Devices Read`, `REST API Compliance Policy Read`, `REST API Profiles Read`, `Updates Policy Read
   access`, `REST API Apps Read`, `REST API Apps For Device Read`, `REST API Users Read`, `REST API Groups Read`,
   `REST API Smart Groups Read`.
2. Do not tick `REST API MDM Devices` or `REST API MDM Profiles`: they are Edit permissions that send lock and
   unlock commands. V [39]
3. Groups & Settings > Configurations, search "OAuth", open OAuth Client Management, Add. Enter Name,
   Description, Organization Group (the top customer group, so every device is in scope) and the role from
   step 1. Status Enabled. Save. V [39]
4. Copy the Client ID and Client Secret before closing; they cannot be shown again. V [39]
5. Give Verity the client id, secret, the API host (`asNNNN.awmdm.com`, found under the REST API settings page)
   and the region. V [37][39]
6. Verity posts `grant_type=client_credentials` to the regional token URL with Basic `client_id:secret`
   V [39]: `uat.uemauth.workspaceone.com`, `na.uemauth.workspaceone.com` (US, Canada),
   `emea.uemauth.workspaceone.com` (UK, Germany), `apac.uemauth.workspaceone.com` (India, Japan, Singapore,
   Australia, Hong Kong), path `/connect/token`.
7. Calls go to `https://asNNNN.awmdm.com/api/...` with the token and `Accept: application/json;version=1` (or
   the version the endpoint needs). V [37]

On premises: create a dedicated admin with the role from step 1, then in the REST API settings Add a service
with Account Type Admin to get an API key; send it as header `aw-tenant-code` with basic auth for the admin.
V [38][34]. Certificate auth is the alternative. V [38]

What it sees: the organization group the client is attached to and its children (`lgid` defaults to the
caller's group). V [34]

### A.3 Visibility by platform and channel

Channels: Apple ADE (automated_company), Apple device enrolment (user_initiated_device), Apple user enrolment
(byod_account_driven), Windows OMA-DM (Autopilot or user), Android work profile (personal), Android fully
managed (company). Cells say what the API exposes, not what the console shows.

| Key | Apple ADE | Apple device enrol | Apple user enrol | Windows | Android work profile | Android fully managed |
|---|---|---|---|---|---|---|
| identity (id, serial, name, model, os) | yes | yes | partial: serial and UDID not reported under user enrolment (Apple behaviour, unverified here) | yes | partial: hardware ids limited (unverified) | yes |
| ownership | yes | yes | yes | yes | yes | yes |
| enrolment_channel | yes (`EnrolledViaDEP`) | partial (`UserApprovedEnrollment`) | partial (`ManagedBy`, unverified mapping) | partial | unverified | unverified |
| supervised | yes | yes | yes (false) | no | no | no |
| last_check_in_at | yes | yes | yes | yes | yes | yes |
| disk_encryption | yes | yes | yes | yes | yes | yes |
| recovery_key_escrowed | macOS yes | macOS yes | no | partial (BitLocker protector endpoint, fields unverified) | n/a | n/a |
| passcode_present, compliant | yes | yes | yes | partial | yes | yes |
| idle_lock_seconds | partial: profile only | partial | partial | partial | partial | partial |
| firewall_on | partial: profile only | partial | no | partial: compliance rule | n/a | n/a |
| os_integrity | yes (SIP, compromised) | yes | yes | yes (health attestation into compromised) | yes (compromised) | yes |
| activation_lock_or_frp | yes | yes | no | n/a | no | unverified |
| removable_storage_blocked | partial: profile installed | partial | no | partial | partial | partial |
| security_patch_level | n/a | n/a | n/a | n/a | yes | yes |
| installed_apps | yes | yes | no (personal) | yes | managed only (unverified) | yes |
| device.action | partial: event log | partial | partial | partial | partial | partial |

### A.4 Field map

Permission for every row: the read only role in A.2. Tier: any edition with REST API (unverified per edition).

| Key | Endpoint | Field | Caveat | Status |
|---|---|---|---|---|
| provider_device_id | `GET /api/mdm/devices/search` | `Id.Value`, `Uuid` | v2 and v3 calls use the UUID | V [34] |
| serial_number | same | `SerialNumber` | | V [34] |
| hardware_ids | same | `Udid`, `Imei`, `MacAddress` | keep IMEI only for company owned | V [34] |
| hostname | same | `HostName` | described as the macOS host name | V [34] |
| device_name | same | `DeviceFriendlyName`, `DeviceReportedName` | friendly name is admin set | V [34] |
| manufacturer | same | `DeviceManufacturerId`, `OEMInfo` | id only; name lookup endpoint unverified | V [34] |
| model | same | `Model` | | V [34] |
| platform | same | `Platform` (example "Apple"), `PlatformId` | Apple covers iOS and macOS: split by `Model` or OS string | V [34] |
| os_version | same | `OperatingSystem` | | V [34] |
| os_build | same | `OSBuildVersion` | | V [34] |
| device_class | same | `Model`; picklist `/picklists/devicetypes` | no class field | V [34] |
| ownership | same | `Ownership`: `C` corporate, `E` employee, `S` shared, `Undefined` | | V [34] |
| enrolment_channel | same | `EnrolledViaDEP`, `UserApprovedEnrollment`, `DepTokenSource`, `ManagedBy` (Unknown, MDM, Workspace, AppCatalog, AppLevel, VmWorkspace, HubRegistered, WorkspaceOneRegistered, HubManaged) | Android work profile versus fully managed: no field found | V [34] |
| supervised | same | `IsSupervised` | | V [34] |
| management_state | same | `EnrollmentStatus` (example "Enrolled") | other values unverified; lost mode is a PUT endpoint, its read field unverified | V [34] |
| enrolled_at | same | `LastEnrolledOn` | last enrolment, not first | V [34] |
| last_check_in_at | same | `LastSeen` | | V [34] |
| provider_compliance_state | same; `GET /api/mdm/devices/{deviceId}/compliance` | `ComplianceStatus`; `ComplianceSummary` with `CompliantStatus`, `PolicyName`, `LastComplianceCheck`, `ActionTaken` | secondary evidence only | V [34] |
| assigned_user_email | search; `GET /api/mdm/devices/{id}/user` | `UserEmailAddress`, `UserName`, `UserId`, `EnrollmentUserUuid` | assignment_source = enrolling user | V [34] |
| disk_encryption | search; `GET /api/mdm/devices/securityinfosearch` | `DataEncryptionYN` (Y or N), `DataProtectionStatus`; security: `IsEncrypted`, `EncryptionStatus`, `BlockLevelEncryption`, `FileLevelEncryption`, `PercentComplete` | value sets unverified; test on fixtures | V [34] |
| encryption_method | `GET /api/mdm/devices/{deviceUuid}/bitlocker/drives` | BitLocker drive model | field names unverified | V [34] (path) |
| recovery_key_escrowed | `securityinfosearch` | `HasPersonalRecoveryKey`, `HasInstitutionalRecoveryKey`; Windows: `.../bitlocker/drives/{volume}/protectors` | the same object holds key fields (gotcha A.6) | V [34] |
| passcode_present | `securityinfosearch` | `IsPasscodePresent` | | V [34] |
| passcode_compliant | same | `IsPasscodeCompliant` | against the passcode profile | V [34] |
| idle_lock_seconds | `GET /api/mdm/devices/{id}/profiles`; profile body `GET /api/mdm/profiles/{profileUuid}` (v3) | profile payload | payload key names unverified; `PasscodeLockGracePeriod` is the grace period, not idle time | V [34][36] (paths) |
| firewall_on | compliance results | rule "Firewall Status" (Windows OMA-DM only) | only when the customer built that rule | V [40] |
| os_integrity | search; security | `CompromisedStatus`, `SystemIntegrityProtectionEnabled`, `SecureBoot`, `AuthenticatedRootVolumeEnabled`, `AppleManagedDeviceAttestationStatus` | Windows health attestation feeds compromised status | V [34][42] |
| activation_lock_or_frp | search; security | `IsActivationLockEnabled`, `IsActivationLockManageable` | | V [34] |
| removable_storage_blocked | `GET /api/mdm/profiles/{profileuuid}/devices` | install state INSTALLED, NOT_INSTALLED, OUT_OF_DATE | which profile blocks storage is customer config | V [34] |
| local_admin_present | `GET .../security/managed-admin-information` | ADE managed admin only | general local admins: no | V [34] |
| av_present, av_realtime_on | compliance results | rule "Antivirus Status" | Windows only | V [40] |
| edr_present | apps | app list | | V [34] |
| os_update_policy_assigned | `/api/mdm/updates`, `.../device-status` | update deployment state | needs `Updates Policy Read access` | V [34][39] |
| os_update_available | `GET /api/mdm/devices/{uuid}/osupdate` (v2) | available updates | Apple focus, unverified for Windows | V [35] |
| security_patch_level | search | `SecurityPatchDate` | Android | V [34] |
| os_supported | none | | | no |
| installed_apps | `GET /api/mdm/devices/{deviceUuid}/apps/search` | app list | personal app collection depends on the privacy setting | V [34][40] |
| managed_apps | same | managed flag | field unverified | unverified |
| device.action | `GET /api/mdm/devices/{id}/eventlog`; `GET /api/mdm/ogs/{og_id}/devices/audit` | `Severity`, `TimeStamp`, `Source`, `Event`, `AdminAccount` | audit start date at most 30 days back; event text for wipes unverified | V [34] |

### A.5 Limits, freshness, history

- Paging: `page` is 0 based, `pagesize` defaults to 500; v2 search caps at 500. V [34][35]
- Throttling is a tenant setting: 5,000 calls per minute and 50,000 calls per day by default. Over the
  minute limit the server drops requests. V [38]
- Freshness: `LastSeen`; the console marks a device inactive after 480 minutes by default. V [41]
- History: event log by `dayrange` (retention unverified); device audit only 30 days back. V [34]. Present
  state otherwise: Verity's daily snapshot is the history.

### A.6 Gotchas

- **Key material under a read permission.** `DeviceSecurityInfo` defines `PersonalRecoveryKey`,
  `StaticRecoveryKey`, `GracePeriodRecoveryKey`, `OldPersonalRecoveryKeyValue` and `UnlockPin`, and the API also
  has a decrypted BitLocker key endpoint. V [34]. Whether a read only role receives them filled in is
  unverified. Verity must never call the BitLocker key path and must decode security info into a struct
  without those fields.
- **Compliant means "met the customer's rules".** Firewall and antivirus exist only as rules the customer
  chose. V [40]
- **Deleting is not wiping evidence.** Deleting a device removes it from the list and sends an enterprise
  wipe; the record stays on the allowlist. Wipe Protection can hold wipes in a queue. V [41]
- **Shared quota.** The daily quota covers every integration on the tenant. V [38]
- **Organization group scope.** A client attached to a child group silently misses other devices. V [34]
- Drop `PhoneNumber`; never call `/gps`. V [34]

### A.7 Go approach

No official Go SDK found (unverified). Plain REST with `net/http`; the client credentials token is one form
POST. Decode into structs that list only allowed fields.

### A.8 Checks supported

| Check | Support | How |
|---|---|---|
| `devices.enrolled` | yes | `EnrollmentStatus` = Enrolled and `LastSeen` in window |
| `devices.disk_encrypted` | yes | `IsEncrypted` or `EncryptionStatus` |
| `devices.recovery_key_escrowed` | macOS yes, Windows partial | `Has*RecoveryKey`; BitLocker protectors |
| `devices.screen_lock` | partial | `IsPasscodePresent` and `IsPasscodeCompliant`; idle value only from the profile |
| `devices.os_current` | yes | `OperatingSystem`, `OSBuildVersion`, `SecurityPatchDate` |
| `devices.firewall_enabled` | partial | Windows compliance rule; macOS profile installed |
| `devices.remote_wipe` | yes | ownership plus enrolment type plus `ManagedBy` = MDM |
| `devices.wipes_confirmed` | partial | event log and 30 day audit; no command history read API found in MDM v1 to v4 [34][35][36] |
| `devices.removable_storage_restricted` | partial | profile install state |
| `devices.assigned_to_active_staff` | yes, with an IdP | `UserEmailAddress` joined to the IdP |
| `devices.staff_have_managed_device` | yes, with an IdP | same join, person side |
| `devices.leaver_devices_recovered` | partial | snapshots; enterprise wipe and delete look like a disappearance |
| EP-03.E permitted software | partial | "Application List" compliance rule results plus installed apps [40] |

---

## B. JumpCloud

### B.1 Editions and API access

| Package | MDM | System Insights | Directory Insights |
|---|---|---|---|
| Device Management | yes | yes | no |
| SSO | no | no | yes |
| Device Identity Management | yes | yes | no |
| Platform Essentials, Platform, Platform Prime | yes | yes | yes |

V [23]. API access per package is not listed (unverified); every admin can hold a key once API access is
enabled. V [20]. System Insights must be enabled for the org and each device. V [16]. Android EMM needs
Platform, Platform+ or the Device Management SKU. V [22]

### B.2 Read only credential, step by step

Preferred: a service account.

1. An Administrator with Billing signs in (only that role can create service accounts). V [19]
2. Settings > Service Accounts > New. Name it "Verity read only"; role **Read Only**. V [19]
3. Key Type: Client Secret; pick a Secret Lifetime (30 to 365 days); Activate. V [19]
4. Copy the Client ID and Client Secret (shown once). Send them to Verity with the Org ID and region. V [19]
5. Verity posts client credentials to `https://admin-oauth.id.jumpcloud.com/oauth2/token` with
   `grant_type=client_credentials` and `scope=api`; the token lasts about an hour. Calls send the bearer
   token and `x-org-id`. V [19]
6. Rotation: two secrets per account allowed; an email goes out 7 days before expiry. V [19]

Fallback: a dedicated Read Only admin; an Administrator with Billing enables its API access; the admin
generates a key under My API Key (prefix `jca_`, default expiry 90 days), sent as `x-api-key`. V [20][1].
Service accounts are not available to MSP customers. V [19]

What Read Only sees: read on Users, Groups, Devices (MDM included) and Commands, but **Edit on Insights**
(System and Directory Insights querying). V [18]

Base URLs: `console.jumpcloud.com/api`, `console.eu.jumpcloud.com/api`, `console.in.jumpcloud.com/api`. V [1].
Directory Insights: `POST https://api.jumpcloud.com/insights/directory/v1/events` (EU host unverified). V [26]

### B.3 Visibility by platform and channel

| Key | macOS ADE (MDM + agent) | macOS agent only or device MDM | Windows agent (MDM optional) | Linux agent | iOS or iPadOS device MDM | iOS user enrolment | Android company owned | Android personal |
|---|---|---|---|---|---|---|---|---|
| identity | yes | yes | yes | yes | yes | partial | unverified | unverified |
| enrolment_channel | yes (`mdm.dep`, `enrollmentType`) | yes | partial (`mdm.vendor`) | yes (agent) | yes | yes | unverified | unverified |
| supervised | yes | no | n/a | n/a | yes | yes (false) | n/a | n/a |
| last_check_in_at | yes | yes | yes | yes | partial | partial | unverified | unverified |
| disk_encryption | yes | yes | yes | yes | no field found | no | unverified | unverified |
| recovery_key_escrowed | partial (`fde.keyPresent`) | partial | partial | partial | n/a | n/a | n/a | n/a |
| passcode_present | n/a | n/a | n/a | n/a | yes | yes | unverified | unverified |
| idle_lock_seconds | partial: policy plus `managed_policies` | partial | partial: policy | partial: policy | no | no | partial: passcode policy | partial |
| firewall_on | yes (`alf`) | yes | partial (`windows_security_products`) | no | n/a | n/a | n/a | n/a |
| removable_storage_blocked | partial: policy status | partial | partial: policy status | partial: policy | no | no | no | no |
| local_admin_present | yes (`userMetrics.admin`) | yes | yes | yes | n/a | n/a | n/a | n/a |
| av and protection | no | no | yes (`windows_security_products`) | no | n/a | n/a | n/a | n/a |
| installed_apps | yes | yes | yes | yes | unverified | no (personal) | unverified | no |
| device.action | partial | partial | partial | partial | partial | partial | unverified | unverified |

### B.4 Field map

Permission for every row: the Read Only service account. Tier: Device Management package or higher; System
Insights rows need System Insights enabled.

| Key | Endpoint | Field | Caveat | Status |
|---|---|---|---|---|
| provider_device_id | `GET /api/systems` (v1) | `_id` | `fields` parameter limits the payload | V [1] |
| serial_number | same; `GET /api/v2/applemdms/{id}/devices` | `serialNumber`; `SerialNumber` | | V [1][10] |
| hardware_ids | same | `networkInfo.imei`, `networkInfo.meid`; `Udid` | spec marks network info as PII; company owned only | V [1][10] |
| hostname | v1 systems | `hostname` | | V [1] |
| device_name | same | `displayName`; Apple `DeviceInformationDeviceName` | | V [1][10] |
| manufacturer | same | `hwVendor` | | V [1] |
| model | Apple devices; `GET /api/v2/systeminsights/system_info` | `DeviceInformationModelName`; computer model column | system_info columns unverified | V [10] (Apple) |
| platform | v1 systems | `os`, `osFamily`, `arch` | value lists unverified | V [1] |
| os_version | v1 systems; `/v2/systeminsights/os_version` | `version`, `osVersionDetail.major/minor/patch`; `Version`, `Major`, `Minor`, `Patch` | | V [1][8] |
| os_build | `/v2/systeminsights/os_version` | `Build` | | V [8] |
| device_class | v1 systems | `desktopCapable` | no class field | V [1] |
| ownership | v1 systems | `mdm.enrollmentType` = user means personal Apple | no general ownership field found | unverified |
| enrolment_channel | v1 systems | `mdm.vendor` (unknown, none, internal, external), `mdm.enrollmentType` (unknown, automated device, device, user), `mdm.dep`, `mdm.userApproved`, `provisionMetadata.provisioner.type` | | V [1] |
| supervised | Apple devices | `DeviceInformationIsSupervised` | | V [10] |
| management_state | v1 systems; Apple devices | `active`, `mdm.enrollmentStatus` (0 or 1), `mdm.lostModeStatus`, `mdm.deviceLockStatus`; `Enrolled` | enum meanings unverified | V [1][10] |
| enrolled_at | v1 systems; Apple devices | `created`; `CreatedAt` | record creation, not MDM enrolment | V [1][10] |
| last_check_in_at | v1 systems | `lastContact` | agent contact; MDM check in time not found | V [1] |
| provider_compliance_state | v1 systems; `GET /api/v2/systems/{id}/policystatuses` | `policyStats` (success, failed, pending, total, unsupportedOs); per policy `State`, `Success`, `ExitStatus`, `EndedAt` | | V [1][2][11] |
| assigned_user_provider_id | v1 systems; `GET /api/v2/systems/{id}/users` | `primarySystemUser.id`; bound users | assignment_source: manual (admin binding) | V [1][2] |
| assigned_user_email | `GET /api/systemusers/{id}` | `email`, `state` (STAGED, ACTIVATED, SUSPENDED), `suspended`, `employeeIdentifier` | JumpCloud is also the directory | V [1][15] |
| disk_encryption | v1 systems; `/v2/systeminsights/bitlocker_info`; `/v2/systeminsights/disk_encryption` | `fde.active`; `ProtectionStatus`, `ConversionStatus`; `Encrypted`, `EncryptionStatus` (encrypted, not encrypted, undefined) | osquery does not document BitLocker status values; JumpCloud's table omits `filevault_status` | V [1][4][5][30][31] |
| encryption_method | bitlocker_info; disk_encryption | `EncryptionMethod`; `Type` | | V [4][5] |
| recovery_key_escrowed | v1 systems | `fde.keyPresent` | no description in the spec; reading it as "key held" is an inference; never call `GET /api/v2/systems/{id}/fdekey` (returns the key) | V [1][14] (field), unverified (meaning) |
| passcode_present | Apple devices | `SecurityInfoPasscodePresent` | | V [10] |
| passcode_compliant | Apple devices | not present in the model | | unverified |
| idle_lock_seconds | policy plus `/v2/systeminsights/managed_policies` | policy template "Lock Screen (Screen Saver)" Timeout (Seconds); device side `Domain`, `Name`, `Value` | policy values are not in the documented policy read model; managed preference key names unverified | V [27][6][13] |
| idle_lock_origin | as above | policy status = policy; managed_policies = device_reported | | V [6][11] |
| firewall_on | `/v2/systeminsights/alf`; `/v2/systeminsights/windows_security_products` | `GlobalState` (0 off, 1 on with exceptions, 2 block all); `Type`, `State` | Windows type and state values not documented; table not for Windows Server | V [3][7][29][32] |
| os_integrity | `/v2/systeminsights/sip_config` | SIP configuration | columns unverified | V [16] (table) |
| activation_lock_or_frp | Apple devices | `SecurityInfoIsActivationLockManageable`, `HasActivationLockBypassCodes` | | V [10] |
| removable_storage_blocked | policies plus policy statuses | Windows "Removable Storage", macOS "USB External Storage Restriction"; exit status 0 = applied | needs policy template names; status means "applied without error" | V [28][11][13] |
| local_admin_present | v1 systems | `userMetrics[].admin`, `managed`, `suspended` | | V [1] |
| av_present, av_signatures_current | windows_security_products | `Name`, `State`, `SignaturesUpToDate` | | V [7][32] |
| os_update_available | `/v2/systeminsights/patches` | installed patches (Windows) | lists installed, not missing | V [2] (path) |
| browser_versions | `/v2/systeminsights/chrome_extensions`, apps, programs | | | V [2][16] |
| installed_apps | `/v2/systeminsights/apps` (macOS), `/programs` (Windows), packages (Linux) | `Name`, `Version`, `Publisher`, `InstallDate` | company owned only | V [9][16] |
| managed_apps | software management | | API unverified | unverified |
| device.action | Directory Insights `service: mdm` | event `mdm_command_result`, request type such as `EraseDevice` | confirms receipt only; 90 days | V [24][25][26] |

### B.5 Limits, freshness, history

- Paging: v1 `limit` defaults to 10, maximum 100; `skip` from 0; sort by `_id` when paging. V [1][21]
- Rate limits: no figures published; back off on 429 (30, 60, 120, 240 seconds is the vendor example). V [21]
- Directory Insights: `limit` up to 10,000; page with `X-Search_after`. V [26]
- Freshness: System Insights collects hourly; offline devices keep their last state. V [16]
- History: System Insights kept 90 days since 6 April 2026 (before that, kept until the device was deleted);
  a device silent for 90 days loses its data. V [16][17]. Directory Insights events kept 90 days. V [26]
  Whether System Insights keeps one row per collection or only the latest: unverified.

### B.6 Gotchas

- **Read Only can query Insights** (Edit on Insights). V [18]
- **Erase confirmation.** The MDM erase event shows the device received the command, not that it erased.
  V [24]. iOS lock state is not visible after the command. V [25]
- **Built in commands.** The v1 erase and lock endpoints say they are for Linux and Windows; Macs use Apple
  MDM commands. V [1]. Personal iOS (user enrolment) cannot be erased. V [25]
- **Directory Insights is not in the Device Management package**, so `devices.wipes_confirmed` gives `error`
  (licence) there. V [23]
- **A policy "success" is an exit status, not a measured value.** V [27][28]
- **macOS Tahoe 26** ignores most lock screen policy settings except timeout and password delay. V [27]
- **System Insights may be off** for a device: `systemInsights.state` (enabled, disabled, deferred). V [1].
  Off gives `insufficient`, not `fail`.
- **PII.** `networkInfo.simInfo.phoneNumber` comes back on the system object. V [1]. Use `fields` to exclude it.

### B.7 Go approach

`github.com/TheJumpCloud/jcapi-go` is official but generated by swagger-codegen at package version 3.0.0 and
lacks newer tables such as `alf`. V [2]. Use plain REST.

### B.8 Checks supported

| Check | Support | How |
|---|---|---|
| `devices.enrolled` | yes | `active`, `lastContact` in window; MDM state from `mdm.*` |
| `devices.disk_encrypted` | yes (computers) | `fde.active` cross read with `bitlocker_info` or `disk_encryption`; mobile: no field |
| `devices.recovery_key_escrowed` | partial | `fde.keyPresent`, meaning unverified |
| `devices.screen_lock` | partial | policy assigned and applied; macOS managed preference value |
| `devices.os_current` | yes | `osVersionDetail`, `os_version` table |
| `devices.firewall_enabled` | macOS yes, Windows partial, Linux no | `alf.GlobalState`; `windows_security_products` |
| `devices.remote_wipe` | yes | MDM enrolled Apple (not user enrolment), Windows and Linux agent, Android company owned |
| `devices.wipes_confirmed` | partial | Directory Insights receipt events; Platform packages only |
| `devices.removable_storage_restricted` | partial | policy and status |
| `devices.assigned_to_active_staff` | yes, no IdP needed | `primarySystemUser` to `systemusers.state` |
| `devices.staff_have_managed_device` | yes, no IdP needed | ACTIVATED users with a bound system in contact |
| `devices.leaver_devices_recovered` | partial | SUSPENDED users and their systems, plus snapshots |
| EP-03.E permitted software | partial | installed apps against a Verity list; no block evidence |

---

## C. Hexnode UEM

### C.1 Editions and API access

Plans: Pro, Enterprise, Ultimate, Ultra; the pricing page does not list API access. V [55]. Custom technician
roles need Ultimate or Ultra. V [54]. FileVault from Ultimate, BitLocker and patching on Ultra. V [55]

### C.2 Credential, step by step (no read only option)

1. Admin > API, tick Enable API Access. V [49]
2. Copy the portal API key on the same page (view, revoke or reset). V [52]
3. Send it raw in the `Authorization` header. V [52]
4. The key can also be fetched with `POST /api-token-auth/` and an admin's username and password. V [50]

What it can do: the API key is not tied to a technician role in any page read; custom roles have API
"entirely disabled". V [54]. Read Only Technician exists for the console only. V [53]. **There is no read
only API credential.** The key reaches wipe, lock and delete actions. V [43]

### C.3 Visibility by platform and channel (documented API only)

| Key | Apple ADE | Apple device enrol | Apple user enrol | Windows | Android work profile | Android fully managed |
|---|---|---|---|---|---|---|
| identity and OS | yes | yes | partial (unverified) | yes | yes | yes |
| supervised | yes | yes | yes | n/a | n/a | n/a |
| last report | yes | yes | yes | yes | yes | yes |
| encryption, passcode, firewall | unverified: console only [56] | unverified | unverified | unverified | unverified | unverified |
| installed_apps | yes | yes | unverified | yes | yes | yes |
| device.action | yes | yes | yes | yes | yes | yes |

### C.4 Field map

Permission: the portal API key. Tier: unverified.

| Key | Endpoint | Field | Caveat | Status |
|---|---|---|---|---|
| provider_device_id | `GET /api/v1/devices/` | `id` | | V [44] |
| serial_number | same | `serial_number` | | V [44] |
| hardware_ids | `GET /api/v1/devices/{id}/` | `udid`, `device.imei_1`, `imei_2`, `meid` | company owned only | V [45] |
| hostname | details | `network.local_host_name` | | V [45] |
| device_name | list | `device_name` | | V [44] |
| manufacturer | details | `device.manufacture` | | V [45] |
| model | list; details | `model_name`; `device.model`, `product_name` | | V [44][45] |
| platform | details | `platform`, `device.os_name` | list filter takes ios, android, windows | V [44][45] |
| os_version | list | `os_version` | | V [44] |
| os_build | details | `device.build_version` | | V [45] |
| device_class | details | `device.device_type`, `device.is_kiosk` | | V [45] |
| ownership | details | `owned_by` (integer) | value meanings unverified | V [45] |
| enrolment_channel | none | | | unverified |
| supervised | details | `device.is_supervised` | | V [45] |
| management_state | list; details | `enrollment_status`, `agent_active`, `lostmode`, `disenrolled_time` | values unverified | V [44][45] |
| enrolled_at | list | `enrolled_time` | | V [44] |
| last_check_in_at | list; details | `last_reported` (list), `lastreported`, `lastscanned` (details) | names differ between the two calls | V [44][45] |
| provider_compliance_state | list; `GET /api/v1/devices/{id}/policies/` | `compliant`; policy `id`, `name`, `version` | | V [44][47] |
| assigned_user_email | details | `user.email`, `user.id` | list has only id and name | V [44][45] |
| disk_encryption, encryption_method | none in documented samples | console: FileVault, BitLocker Encryption Status, LUKS | | unverified |
| recovery_key_escrowed | policy | macOS policy `filevault.escrow_recovery_key` | policy intent, not device state; console shows key fields | V [57][56] |
| passcode_present, passcode_compliant | none in API samples | console: Passcode compliance | | unverified |
| idle_lock_seconds | policy | macOS `password.max_inactivity` (never, 1 to 15 minutes) | reading a policy back through Policy Details: no sample response | V [57], unverified [58] |
| firewall_on | policy | macOS `firewall.firewall_enabled` | device state console only | V [57][56] |
| os_integrity, activation_lock, local admin, antivirus, patches | none in API samples | console fields exist | | unverified |
| removable_storage_blocked | none | macOS policy has no USB payload | | V [57] (absence) |
| installed_apps | details | `applications[]`: `name`, `identifier`, `app_version`, `managed`, `black_listed`, `status` | | V [45] |
| managed_apps | details | `applications[].managed` | | V [45] |
| device.action | `GET /api/v1/devices/{id}/action_status/` | `action_label`, `status`, `created_time`, `finished_time`, `error_code`, `error_message` | status values unverified | V [46] |

### C.5 Limits, freshness, history

- Paging: `page` from 1, `per_page` default 100, maximum 250. V [44][46]
- Rate limit: 429 exists; no figures. V [51]. A per device daily cap is mentioned only in a community thread
  (unverified).
- Freshness: `lastreported` and `lastscanned`; scan interval unverified. History: action status per device,
  paged; retention unverified.

### C.6 Gotchas

- **Full admin key.** Violates Verity's read only rule unless the owner accepts it.
- **Location and phone numbers arrive** in device details and user details (`latitude`, `longitude`,
  `location_history`, `phoneno`). V [45][48]. Drop at parse.
- **List and details disagree** on names (`last_reported` and `lastreported`). V [44][45]
- **The console shows more than the API documents.** V [56][45]
- **Per device calls.** Email and apps need one details call per device.

### C.7 Go approach

No SDK (unverified). REST.

### C.8 Checks supported

| Check | Support | How |
|---|---|---|
| `devices.enrolled` | yes | `enrollment_status`, `last_reported` |
| `devices.disk_encrypted` | unverified | not in the documented API |
| `devices.recovery_key_escrowed` | partial | policy intent only |
| `devices.screen_lock` | partial | policy `max_inactivity` |
| `devices.os_current` | yes | `os_version`, `build_version` |
| `devices.firewall_enabled` | partial | macOS policy only |
| `devices.remote_wipe` | partial | platform and supervision; ownership values unverified |
| `devices.wipes_confirmed` | yes | `action_status` |
| `devices.removable_storage_restricted` | no | |
| `devices.assigned_to_active_staff` | yes, with an IdP | `user.email` |
| `devices.staff_have_managed_device` | yes, with an IdP | same |
| `devices.leaver_devices_recovered` | partial | `disenrolled_time`, action status, snapshots |
| EP-03.E permitted software | partial | `black_listed` flag |

---

## D. ManageEngine Endpoint Central and Mobile Device Manager Plus

### D.1 Editions and API access

| Feature | Professional | Enterprise | UEM | Security |
|---|---|---|---|---|
| Role based administration | yes | yes | yes | yes |
| BitLocker management | add on | add on | add on | yes |
| FileVault encryption | no | no | yes | yes |
| Remote wipe for laptops | no | no | yes | yes |
| USB device management | no | yes | yes | yes |
| Prohibit software | no | yes | yes | yes |

V [74]. MDM for Windows and macOS laptops needs UEM or Security. V [74]. API access per edition not listed
(unverified).

### D.2 Read only credential, step by step

Cloud (nine data centres: `endpointcentral.manageengine.<com|eu|in|com.au|cn|jp|ca|uk|sa>`, accounts at
`accounts.zoho.<same>`). V [71]

1. Create an Endpoint Central user for Verity with the Guest role (read on Inventory, Patch, Configurations,
   MDM, Reports). V [75]. Guest rights for BitLocker and Device Control are not stated (unverified).
2. Sign in to the Zoho API console (`api-console.zoho.<dc>`) as that user. V [71]
3. Create a Self Client; Generate Code with scopes V [72][60]: `DesktopCentralCloud.Common.READ`,
   `DesktopCentralCloud.Inventory.READ`, `DesktopCentralCloud.PatchMgmt.READ`,
   `DesktopCentralCloud.DeviceControl.READ`; MDM: `MDMOnDemand.MDMInventory.READ` [78].
4. Hand Verity the client id, secret and code (3 minute default life). V [72]
5. Verity exchanges at `https://accounts.zoho.<dc>/oauth/v2/token` for a refresh token (no expiry) and an
   access token (1 hour). V [72][78]
6. Header: `Authorization: Zoho-oauthtoken <token>`. V [61]

On premises: Admin > Integrations > API Key Management; per module Read toggles; expiry defaults to "Never
Expires"; shown once; sent in `Authorization`. V [73]

### D.3 Visibility by platform and channel

| Key | Windows agent | macOS agent | Linux agent | Apple MDM | Android MDM |
|---|---|---|---|---|---|
| identity and OS | yes | yes | yes | yes | yes |
| serial_number | partial (`servicetag`) | partial | partial | yes | yes |
| ownership | no | no | no | yes | yes |
| last_check_in_at | yes | yes | yes | partial | partial |
| disk_encryption | yes (BitLocker) | via MDM | yes (LUKS) | yes | yes |
| recovery_key_escrowed | no safe path | via MDM | no | yes (FileVault flags) | n/a |
| passcode | unverified | unverified | unverified | yes | yes |
| firewall_on | yes (per profile) | unverified | unverified | n/a | n/a |
| removable_storage_blocked | partial | partial | unverified | partial | partial |
| os_update and patch health | yes | yes | yes | partial | partial |
| installed_apps and prohibited | yes | yes | yes | yes | yes |
| device.action | unverified | unverified | unverified | yes | yes |

### D.4 Field map

| Key | Endpoint (scope) | Field | Caveat | Status |
|---|---|---|---|---|
| provider_device_id | `GET /api/1.4/som/computers` (Common.READ); MDM `GET /api/v1/mdm/devices` (MDMInventory.READ) | `resource_id`; `device_id` | | V [61][77] |
| serial_number | `GET /dcapi/inventory/viewData/scanComputers` (Inventory.READ); MDM list | `servicetag`; `serial_number` | computer list has no serial | V [64][77] |
| hardware_ids | MDM list | `udid` | | V [77] |
| hostname | som computers | `resource_name`, `fqdn_name` | | V [61] |
| device_name | som computers; MDM | `managedcomputer.friendly_name`; `device_name` | | V [61][77] |
| manufacturer, model | hardware summary; MDM | `model`, `product_name` | computer fields unverified | V [77] |
| platform | som computers; MDM | `os_platform` (1 Windows, 2 Mac, 3 Linux); `platform_type` | | V [61][77] |
| os_version, os_build | som computers; scanComputers | `os_name`, `os_version`, `service_pack`; `build_number` | | V [61][64] |
| ownership | MDM list | `owned_by` (1 corporate, 2 personal) | | V [77] |
| enrolment_channel | som computers | agent: `installation_status` (22 installed); `modernappdetails.enrollment_type` | MDM channel field unverified | V [61] |
| supervised | MDM details | `is_supervised` | | V [77] |
| management_state | som computers; MDM | `managed_status`, `computer_live_status` (1, 2, 3); `managed_status`, `is_removed`, `unregistered_time` | MDM values undocumented | V [61][77] |
| enrolled_at | som computers; MDM | `agent_installed_on`; `registered_time` | | V [61][77] |
| last_check_in_at | som computers; MDM summary | `agent_last_contact_time`; `last_contact_time` | | V [61][77] |
| provider_compliance_state | `GET /dcapi/patch/reports/systemHealth` (PatchMgmt.READ) | `Health` | | V [67] |
| assigned_user_email | som computers; MDM list | `owner_email_id`; `user.user_email` | source of owner field unverified | V [61][77] |
| disk_encryption | `GET /api/1.4/bitlocker/bitlockerreports` (DataEncryption.READ); Linux `.../diskEncryptionStatus` (Inventory.READ); MDM details | `encryption_status`, `protection_status`; `encryptionStatus`; `security.storage_encryption` | Linux endpoint is Linux only | V [68][62][77] |
| encryption_method | same | `encryption_method`; `encryptionMethod` | | V [68][62] |
| recovery_key_escrowed | MDM `GET .../filevault` | `is_personal_recovery_key`, `is_institution_recovery_key` | Windows: only `recoverykeydetails`, which returns keys | V [77][69] |
| passcode_present, passcode_compliant | MDM details | `security.passcode_present`, `security.passcode_complaint` (sic) | | V [77] |
| firewall_on | `GET /dcapi/inventory/computers/{id}/firewall` (Inventory.READ) | `domainProfileStatus`, `privateProfileStatus`, `publicProfileStatus` | Windows | V [63] |
| os_integrity | MDM details | `security.device_rooted` | | V [77] |
| removable_storage_blocked | `GET /api/1.4/reports/dcm/computerdevstatus` (DeviceControl.READ) | `diskdrive.status_id`, `wpd.status_id` | id meanings undocumented | V [70] |
| os_update_available | systemHealth | `MissingOsPatches`, `LastPatchedTime` | | V [67] |
| installed_apps | `GET /dcapi/inventory/computers/{id}/softwareInfo`; `/viewData/software` | `invsw.software_name`, `software_version`; `is_usage_prohibited` | | V [65][66] |
| device.action | MDM `GET .../commandhistory` | `command_name`, `command_status`, `added_time`, `command_life[].updated_time` | | V [77] |

### D.5 Limits, freshness, history

- Rate limits: 120 per minute (systemHealth 50), 5 minute lock, HTTP 429. V [61][64][65][67]
- Paging: systemHealth `pageLimit` up to 1,000. V [67]
- Zoho token limits: 10 access tokens per refresh token per 10 minutes. V [78]
- Freshness: agent every 90 minutes. V [76]
- History: MDM command history with `start_time`, `end_time`, `days`. V [77]

### D.6 Gotchas

- **`DataEncryption.READ` returns BitLocker recovery keys.** V [69]
- **`MDMInventory.READ` returns Mac firmware passwords and locations.** V [77]
- **Two products, two scope families** (`DesktopCentralCloud.*` and `MDMOnDemand.*`). V [60][78]
- **Lockout.** A burst over the limit locks for 5 minutes. V [61]
- **Self Client codes expire fast.** V [72]

### D.7 Go approach

No SDK (unverified). REST.

### D.8 Checks supported

| Check | Support |
|---|---|
| `devices.enrolled` | yes |
| `devices.disk_encrypted` | yes (BitLocker add on) |
| `devices.recovery_key_escrowed` | macOS yes, Windows no |
| `devices.screen_lock` | partial (mobile) |
| `devices.os_current` | yes |
| `devices.firewall_enabled` | Windows yes |
| `devices.remote_wipe` | partial |
| `devices.wipes_confirmed` | mobile yes |
| `devices.removable_storage_restricted` | partial |
| `devices.assigned_to_active_staff` | partial |
| `devices.staff_have_managed_device` | partial |
| `devices.leaver_devices_recovered` | partial |
| EP-03.E permitted software | yes |

---

## E. Cross product check support

| Check | Workspace ONE | JumpCloud | Hexnode | ManageEngine |
|---|---|---|---|---|
| `devices.enrolled` | yes | yes | yes | yes |
| `devices.disk_encrypted` | yes | yes (computers) | unverified | yes |
| `devices.recovery_key_escrowed` | macOS yes | partial | partial | macOS yes |
| `devices.screen_lock` | partial | partial | partial | partial |
| `devices.os_current` | yes | yes | yes | yes |
| `devices.firewall_enabled` | partial | macOS yes | partial | Windows yes |
| `devices.remote_wipe` | yes | yes | partial | partial |
| `devices.wipes_confirmed` | partial | partial | yes | mobile yes |
| `devices.removable_storage_restricted` | partial | partial | no | partial |
| `devices.assigned_to_active_staff` | yes (IdP) | yes (no IdP) | yes (IdP) | partial |
| `devices.staff_have_managed_device` | yes (IdP) | yes (no IdP) | yes (IdP) | partial |
| `devices.leaver_devices_recovered` | partial | partial | partial | partial |
| EP-03.E permitted software | partial | partial | partial | yes |

## F. Proposed dictionary keys

| Key | Why | Check |
|---|---|---|
| `last_inventory_at` | inventory time differs from check in | state checks freshness |
| `firewall_profiles` | Windows per profile state | `devices.firewall_enabled` |
| `assigned_policies[]` | policy evidence | `devices.screen_lock`, `devices.removable_storage_restricted` |
| `installed_apps[].provider_verdict` | deny list flags | new `devices.software_permitted` (EP-03.E) |

## G. Corrections to round 1

None: round 1 makes no claim about these four products. Gaps: `capabilities.json` lists Jamf, Kandji and Intune
only; strategy section 5.5 has no columns for these products.

## H. Sources

1. JumpCloud API v1 spec: https://docs.jumpcloud.com/api/1.0/index.yaml
2. jcapi-go v2 README: https://github.com/TheJumpCloud/jcapi-go/blob/master/v2/README.md
3. Get-JcSdkSystemInsightAlf: https://github.com/TheJumpCloud/jcapi-powershell/blob/master/SDKs/PowerShell/JumpCloud.SDK.V2/docs/exports/Get-JcSdkSystemInsightAlf.md
4. Get-JcSdkSystemInsightBitlockerInfo: same folder, Get-JcSdkSystemInsightBitlockerInfo.md
5. Get-JcSdkSystemInsightDiskEncryption: same folder
6. Get-JcSdkSystemInsightManagedPolicy: same folder
7. Get-JcSdkSystemInsightWindowsSecurityProduct: same folder
8. Get-JcSdkSystemInsightOSVersion: same folder
9. Get-JcSdkSystemInsightProgram: same folder
10. Get-JcSdkAppleMdmDevice: same folder
11. Get-JcSdkPolicyStatus: same folder
12. Get-JcSdkPolicyResult: same folder
13. Get-JcSdkPolicy: same folder
14. Get-JcSdkSystemFdeKey: same folder
15. Get-JcSdkUser (v1): https://github.com/TheJumpCloud/jcapi-powershell/blob/master/SDKs/PowerShell/JumpCloud.SDK.V1/docs/exports/Get-JcSdkUser.md
16. System Insights: https://jumpcloud.com/support/system-insights
17. System Insights retention update: https://jumpcloud.com/?p=145210
18. Admin portal roles: https://jumpcloud.com/support/admin-portal-roles
19. Service accounts: https://jumpcloud.com/support/service-account-for-apis
20. JumpCloud APIs: https://jumpcloud.com/support/jumpcloud-apis
21. API best practices: https://jumpcloud.com/support/best-practices-jumpcloud-api
22. Android EMM: https://jumpcloud.com/support/get-started-android-emm
23. Pricing: https://jumpcloud.com/pricing
24. Erase Device: https://jumpcloud.com/support/understand-the-erase-device-mdm-command
25. MDM commands: https://jumpcloud.com/support/mdm-commands
26. Directory Insights spec: https://docs.jumpcloud.com/new/api/insights/directory/index.yaml
27. macOS lock screen policy: https://jumpcloud.com/support/create-a-mac-lock-screen-policy
28. Windows removable storage: https://jumpcloud.com/support/manage-removable-storage-on-windows-devices
29. osquery alf: https://raw.githubusercontent.com/osquery/osquery/master/specs/darwin/alf.table
30. osquery bitlocker_info: https://raw.githubusercontent.com/osquery/osquery/master/specs/windows/bitlocker_info.table
31. osquery disk_encryption: https://raw.githubusercontent.com/osquery/osquery/master/specs/posix/disk_encryption.table
32. osquery windows_security_products: https://raw.githubusercontent.com/osquery/osquery/master/specs/windows/windows_security_products.table
33. Workspace ONE UEM APIs: https://developer.omnissa.com/workspace-one-uem-apis/
34. MDM API v1 (2607): https://raw.githubusercontent.com/euc-dev/ws1-uem-apis/main/docs/versions/2607/mdmv1.json
35. MDM API v2: https://raw.githubusercontent.com/euc-dev/ws1-uem-apis/main/docs/versions/2607/mdmv2.json
36. MDM API v3: https://raw.githubusercontent.com/euc-dev/ws1-uem-apis/main/docs/versions/2607/mdmv3.json
37. Bruno getting started: https://developer.omnissa.com/workspace-one-uem-apis/bruno/
38. REST API settings: https://docs.omnissa.com/SystemSettings-VSaaS/RestAPIforWorkspaceONEUEM
39. Using UEM with REST API: https://docs.omnissa.com/WorkspaceONE-UEM-Console-Basics-VSaaS/UsingUEMFunctionalityWithRESTAPI
40. Compliance rules: https://docs.omnissa.com/WorkspaceONE-UEM-Managing-Devices-VSaaS/CompliancePolicyRulesAndActions
41. Device List View: https://docs.omnissa.com/WorkspaceONE-UEM-Managing-Devices-VSaaS/DeviceListView
42. Windows compliance: https://docs.omnissa.com/Windows_Desktop_Management-VSaaS/uemWindeskCompliance
43. Hexnode Devices API: https://www.hexnode.com/mobile-device-management/developers/devices/
44. List All Devices: https://www.hexnode.com/mobile-device-management/developers/devices/list-all-devices/
45. Retrieve Device Details: https://www.hexnode.com/mobile-device-management/developers/devices/retrieve-device-details/
46. Action Status: https://www.hexnode.com/mobile-device-management/developers/devices/action-status/
47. List Device Policies: https://www.hexnode.com/mobile-device-management/developers/devices/list-device-policies/
48. Retrieve User Details: https://www.hexnode.com/mobile-device-management/developers/users/retrieve-user-details/
49. Authentication: https://www.hexnode.com/mobile-device-management/developers/setting-up-an-api/authentication/
50. Retrieve API Key: https://www.hexnode.com/mobile-device-management/developers/setting-up-an-api/retrieve-api-key/
51. Status codes: https://www.hexnode.com/mobile-device-management/developers/setting-up-an-api/status-and-error-codes/
52. Does Hexnode have APIs: https://www.hexnode.com/mobile-device-management/help/does-hexnode-have-apis/
53. Technicians and roles: https://www.hexnode.com/mobile-device-management/help/configuring-technicians-and-roles-in-hexnode/
54. Custom technician roles: https://www.hexnode.com/mobile-device-management/help/configuring-custom-technician-roles-using-hexnode-mdm/
55. Hexnode pricing: https://www.hexnode.com/pricing/
56. Device details page: https://www.hexnode.com/mobile-device-management/help/how-to-view-and-monitor-device-details-in-hexnode-uem/
57. macOS policies API: https://www.hexnode.com/mobile-device-management/developers/policies/macos-policies/
58. Policy Details API: https://www.hexnode.com/mobile-device-management/developers/policies/policy-details/
59. Reports API: https://www.hexnode.com/mobile-device-management/developers/reports/
60. Endpoint Central API index: https://www.manageengine.com/products/desktop-central/help/api/cloud/api-index.html
61. Get Computers: https://www.manageengine.com/products/desktop-central/help/api/cloud/computers-getcomputers.html
62. Disk encryption status: https://www.manageengine.com/products/desktop-central/help/api/cloud/inventory-get-disk-encryption-status.html
63. Firewall details: https://www.manageengine.com/products/desktop-central/help/api/cloud/inventory-get-computer-firewall-details.html
64. Scan computers: https://www.manageengine.com/products/desktop-central/help/api/cloud/inventory-get-scan-computers-list.html
65. Installed software: https://www.manageengine.com/products/desktop-central/help/api/cloud/inventory-get-installed-software-list.html
66. Software info: https://www.manageengine.com/products/desktop-central/help/api/cloud/inventory-get-computer-software-info.html
67. System health: https://www.manageengine.com/products/desktop-central/help/api/cloud/system-report-get-system-health-report.html
68. BitLocker reports: https://www.manageengine.com/products/desktop-central/help/api/cloud/bitlocker-reports.html
69. Recovery key details: https://www.manageengine.com/products/desktop-central/help/api/cloud/recovery-key-details-report.html
70. Device control status: https://www.manageengine.com/products/desktop-central/help/api/cloud/dcm-get-computer-dev-status.html
71. Data centres: https://www.manageengine.com/products/desktop-central/oauth-authentication-endpoint-domain.html
72. Zoho Self Client: https://www.manageengine.com/products/desktop-central/api/cloud_index.html
73. API key generation: https://www.manageengine.com/products/desktop-central/api-key-generation.html
74. Edition matrix: https://www.manageengine.com/products/desktop-central/edition-comparison-matrix.html
75. User roles: https://www.manageengine.com/products/desktop-central/help/access-management/user_role_and_permission.html
76. Agent communication: https://www.manageengine.com/products/desktop-central/help/cloud/device-onboarding/agent-communication-guide.html
77. MDM Plus devices API: https://www.manageengine.com/mobile-device-management/api/devices/
78. MDM Plus OAuth: https://www.manageengine.com/mobile-device-management/api/oauth/
