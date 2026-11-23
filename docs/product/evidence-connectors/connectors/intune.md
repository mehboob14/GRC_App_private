# Microsoft Intune

| | |
|---|---|
| Capabilities | device_management (and, through the Microsoft 365 connection, a source for asset_discovery of endpoints) |
| Delivery phase | Not in the signed catalogue. `capabilities.json` lists `intune` as `not_planned`. Needs the owner's scope decision ([strategy](../mdm-and-endpoint-strategy.md), decision D-DEV-1) |
| Auth model | OAuth 2.0 client credentials (application permissions) on Microsoft Graph, with tenant wide admin consent. The same app registration as the Entra ID connector |
| Shares setup with | The Entra ID identity connector (one app registration, one consent screen). Microsoft Defender for Endpoint ([its own file](microsoft-defender-endpoint.md)) adds permissions on a second API in the same registration |
| Go library | Microsoft Graph SDK for Go, `github.com/microsoftgraph/msgraph-sdk-go` (v1.0) and `github.com/microsoftgraph/msgraph-beta-sdk-go` (beta), with `github.com/Azure/azure-sdk-for-go/sdk/azidentity` for client credentials (module paths confirmed from each repository's go.mod [S14]) |

Check definitions referred to below (existing and NEW) are written once, provider neutral, in
[mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue). This file
says how Intune implements each one.

## 1. What it proves

Intune is the device register for companies on Microsoft 365. It shows, per Windows, macOS, iOS and
Android device: whether Intune manages it and when it last synced, whether it is encrypted, which person
it belongs to, whether it is company or personal, its OS version, and whether Intune judged it compliant
with the policies the customer assigned. Through the Defender Antivirus state that Intune reports, it also
shows antivirus health on Windows (used by the Defender connector, not here).

It does not prove that every company laptop is in Intune (a device that was never enrolled is invisible),
that a wipe was done when a person left (unless Verity saw the action), or that a screen lock is set when
the customer configures it through a configuration profile rather than a compliance policy. Those need the
roster reconciliation checks and a person.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

The Entra ID connector's app registration gains Intune permissions. The customer's administrator grants
admin consent once. Verity calls Graph with an app only token. The Intune part of Graph needs an active
Intune licence in the tenant [S1].

Granting admin consent for Microsoft Graph application permissions needs the Privileged Role
Administrator or Global Administrator role. Cloud Application Administrator and Application Administrator
cannot consent to Graph application permissions [S2].

### 2.2 Permissions

| Permission (application) | Read only | Needed for (check keys) | Role that can grant it |
|---|---|---|---|
| `DeviceManagementManagedDevices.Read.All` | yes | every devices.* check below: device list, ownership, user, encryption, OS, sync time, remote action results | Privileged Role Administrator or Global Administrator [S2][S3] |
| `DeviceManagementConfiguration.Read.All` | yes | `devices.screen_lock`, `devices.firewall_enabled` (macOS), `devices.os_current` (policy minimums), `devices.removable_storage_restricted`; compliance policies, their settings and per device status | same |
| `BitlockerKey.ReadBasic.All` | yes, metadata only (the key itself is not readable with it) | `devices.recovery_key_escrowed` (Windows) | same [S4] |
| `User.Read.All` | yes | joins devices to people for `devices.assigned_to_active_staff`, `devices.staff_have_managed_device`. Held by the Entra ID connector already | same |

`Device.Read.All` (Entra device objects, listed in [entra-id.md](entra-id.md)) is not needed by these
checks: the Intune record carries `azureADDeviceId` for matching. Not requested: any `ReadWrite` permission, `BitlockerKey.Read.All` (would expose recovery keys),
`DeviceManagementScripts.Read.All`, `DeviceManagementApps.Read.All`. Corrected: creating an Intune report
export job (`POST /deviceManagement/reports/exportJobs`, used for the firewall report) lists only
`DeviceManagementConfiguration.ReadWrite.All`, `DeviceManagementApps.ReadWrite.All` or
`DeviceManagementManagedDevices.ReadWrite.All` in Microsoft's v1.0 and beta references [S15]; one report
page names `DeviceManagementManagedDevices.Read.All` for a single report [S10]. A write permission breaks
Verity's read only rule, so Verity does not use export jobs unless a recorded test shows a read
permission is accepted. Until then the Windows part of `devices.firewall_enabled` gives `insufficient`.

### 2.3 Licences and prerequisites

- An active Intune licence for the tenant is required for every Intune Graph call [S1]. Intune Plan 1 is
  included in Microsoft 365 E3 and E5 and EMS E3 and E5 (Microsoft's Intune pricing page [S16]) and in
  Microsoft 365 Business Premium (Microsoft's Business Premium device management guide [S5]). The Learn
  licensing page now points to the pricing page instead of listing bundles [S1].
- Devices must be enrolled in Intune MDM. Devices that only register in Entra ID, or that only sync mail
  through Exchange ActiveSync, appear with another management agent and fail `devices.enrolled`.
- Vendor side: none beyond the shared multi tenant app registration of the Entra ID connector (publisher
  verification is that connector's prerequisite).

## 3. Customer setup guide (draft product text)

1. Connect Microsoft 365 first (identity). If it is already connected, open it and choose **Add device
   management**.
2. Verity shows the extra permissions it will ask for: read devices, read device policies, read BitLocker
   key information (not the keys). Nothing can be changed by Verity.
3. Sign in as a Global Administrator or Privileged Role Administrator and accept.
4. Choose what is in scope: platforms (Windows, macOS, iOS, Android) and whether personal devices count.
   Personal devices left out need a reason.
5. Tell Verity your screen lock limit (default 15 minutes) and the oldest OS versions you allow.
6. Verity reads your devices and shows results within a few minutes. Devices that have not synced for
   14 days are listed as out of contact.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Managed devices | `GET /v1.0/deviceManagement/managedDevices` [S3][S6] | `id`, `deviceName`, `serialNumber`, `azureADDeviceId`, `operatingSystem`, `osVersion`, `managementAgent`, `deviceEnrollmentType`, `managedDeviceOwnerType` (company, personal, unknown), `complianceState`, `isEncrypted`, `isSupervised`, `enrolledDateTime`, `lastSyncDateTime`, `userId`, `userPrincipalName`, `emailAddress`, `deviceActionResults` (actionName, actionState, startDateTime, lastUpdatedDateTime), `jailBroken`, `model`, `manufacturer`, `wiFiMacAddress` | `@odata.nextLink`. Corrected limits: Graph global limit 130,000 requests per 10 seconds per app across all tenants; Intune devices 2,000 requests per 20 seconds per app per tenant and 4,000 per tenant across apps; honour 429 and `Retry-After` [S7] | Device cleanup rules hide devices that have not checked in for 30 to 270 days (customer setting); hidden devices stay in Entra ID and reappear if they check in before their certificate expires [S8] |
| Compliance policies | `GET /v1.0/deviceManagement/deviceCompliancePolicies` and per policy `deviceStatuses` [S9] | per policy: type, `passwordRequired`, `passwordMinutesOfInactivityBeforeLock`, `passwordRequiredToUnlockFromIdle`, `storageRequireEncryption`, `bitLockerEnabled`, `osMinimumVersion`, assignments; per device status: status, last reported time | as above | current state only |
| BitLocker key metadata | `GET /v1.0/informationProtection/bitlocker/recoveryKeys` [S4] | key id, `deviceId`, `createdDateTime`, volume type. Never `key` (the list does not return it) [S4] | `@odata.nextLink`; `$filter` on `deviceId`, no `$top` [S4] | as long as the device object exists in Entra: deleting the device deletes its keys, with no recovery [S18] |
| Intune reports (export jobs) | `POST /v1.0/deviceManagement/reports/exportJobs` (also on beta) with report names `FirewallStatus`, `NoncompliantDevicesAndSettings`, `Devices` [S10][S19]. Needs a ReadWrite permission per Microsoft's reference (section 2.2): not used until resolved | FirewallStatus: DeviceId, FirewallStatus, LastReportedDateTime, UPN. NoncompliantDevicesAndSettings: DeviceId, PolicyName, SettingName, SettingStatus. Devices: EncryptionStatus [S10] | asynchronous job, poll until `completed`, then download; 100 export requests per tenant per minute, 48 per app [S19] | snapshot of current state |

Windows protection state (`windowsProtectionState`: real time protection, signature overdue, tamper
protection) is read by the Defender connector when that provider is chosen [S11].

## 5. Checks

Shared rules (strategy section 5.1): devices not synced for `stale_after_days` give `insufficient` on
state checks; permission missing gives `error`; a run that could not page to the end gives
`insufficient` for every check; personal devices follow the scope setting.

### 5.1 Existing checks: feasibility on Intune

| Check | Feasible | How Intune answers it | Gaps |
|---|---|---|---|
| `devices.enrolled` | yes | `managementAgent` in (`mdm`, `easMdm`, `intuneClient`, `easIntuneClient`, `configurationManagerClientMdm`, `configurationManagerClientMdmEas`) and `lastSyncDateTime` within the window. `eas` only, `unknown` and retire pending records fail [S6] | Unenrolled devices are invisible: completeness comes from `devices.staff_have_managed_device` and the asset register. Confirmed: `managementState` (for example `retirePending`) appears only in the v1.0 List example, not in the property table or the resource's JSON [S3][S6]: do not depend on it |
| `devices.disk_encrypted` | yes | `isEncrypted` per device [S6]; cross read with the `Devices` report `EncryptionStatus` only once the export permission in 2.2 is settled | On macOS, how `isEncrypted` maps to FileVault state is not stated by Microsoft (unverified); test on a fixture |
| `devices.screen_lock` | partial | A compliance policy assigned to the device with `passwordRequired` true and `passwordMinutesOfInactivityBeforeLock` at or under the limit, and the device's status for that policy compliant (`deviceStatuses`) [S9] | A lock set only through a configuration profile or the settings catalog is not read: result `insufficient` with that reason (Vanta documents the same limit) [S12]. macOS uses the same names: `passwordRequired`, `passwordMinutesOfInactivityBeforeLock` on `macOSCompliancePolicy` [S17] |
| `devices.os_current` | yes | `operatingSystem` and `osVersion` against the tenant minimum per platform | Patch level inside a Windows build needs the Windows update reports (policy scoped, beta): later |
| `devices.remote_wipe` | yes | Full wipe capable when `managementAgent` is an MDM agent and `deviceEnrollmentType` is not `userEnrollment`, `appleUserEnrollment` or `appleUserEnrollmentWithServiceAccount` (those allow removing work data only) [S6] | The mapping from enrolment type to wipe scope is Verity's reading of Microsoft's model: verify per platform on fixtures |

### 5.2 New checks: feasibility on Intune

| Check (NEW) | Feasible | How | Gaps |
|---|---|---|---|
| `devices.recovery_key_escrowed` | Windows yes, macOS no | A BitLocker key record whose `deviceId` equals the device's `azureADDeviceId` [S4] | No metadata only FileVault escrow field was found in Graph v1.0 (unverified: not found, not disproved): macOS gives `insufficient` |
| `devices.firewall_enabled` | partial | Windows: `FirewallStatus` report [S10]. macOS: `firewallEnabled` in the assigned macOS compliance policy and the device's status for it [S17] | Corrected: the export job needs a ReadWrite permission per Microsoft's reference [S15], which Verity does not request. Windows devices give `insufficient` with that reason until a read permission is proven; macOS is unaffected |
| `devices.assigned_to_active_staff` | yes | `userId` or `userPrincipalName` joined to the Entra user's `accountEnabled` (Entra ID connector) | Shared and kiosk devices need an exclusion with reason |
| `devices.staff_have_managed_device` | yes | Entra member users, minus exclusions, each with one managed device in contact | Guests and service accounts come from the Entra observation `kind` |
| `devices.leaver_devices_recovered` | partial | Devices assigned to a leaver (HR source) at the end date, then a wipe or retire in `deviceActionResults` with a completed state, or the device record retired, or reassigned | Retired devices leave the list: only Verity's daily snapshots keep the history. Needs an HR source |
| `devices.wipes_confirmed` | partial | `deviceActionResults` entries for wipe with their state and times [S6] | `actionState` values: none, pending, canceled, active, done, failed, notSupported [S20]; how long results stay on the record is not stated (unverified). Intune audit events (`GET /deviceManagement/auditEvents`) would be the stronger source; they need `DeviceManagementApps.Read.All` [S21], not requested today |
| `devices.removable_storage_restricted` | later | Needs per device status of a configuration or endpoint security policy that blocks removable storage | Per device configuration state is not on the v1.0 device resource; reports route unverified (not researched) |

## 6. Artifacts and objectives it fills

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `inventory-of-company-devices` | EP-03.B, EP-03.C, EP-05.B (and the others that share it, see strategy section 4) | EP-03, EP-05 | check only today (`devices.enrolled`, no person source) -> person + checks; split proposed in strategy section 4 |
| `screen-lock-setting-report` | EP-06.B, EP-06.C, EP-03.D | EP-06 | person -> person + `devices.screen_lock` |
| `patch-compliance-report` | EP-04.C, EP-03.D | EP-04 | person + `devices.os_current` (already listed) -> unchanged, implementation added |
| `wipe-confirmations-for-recovered-or-lost` | EP-05.C, EP-05.D | EP-05 | person -> person + `devices.wipes_confirmed`, `devices.leaver_devices_recovered` |
| `leakage-prevention-and-sharing-settings-in` | DM-19.C | DM-19 | person -> person + `devices.removable_storage_restricted` (later) |
| `asset-inventory` | LM-01.C | LM-01 | adds Intune as a device source for `assets.resources_registered` (needs a device asset type, strategy D-DEV-6) |

## 7. Framework reach

Through EP-02, EP-03, EP-04, EP-05, EP-06 and LM-01: SOC 2 CC6.1, CC6.5, CC6.7, CC6.8, CC7.1, CC2.1;
ISO 27001:2022 A.5.9, A.5.11, A.6.7, A.7.7, A.7.9, A.7.10, A.7.14, A.8.1, A.8.8, A.8.19, A.8.24. Every
mapping is partial (strategy section 3 lists them per control).

## 8. Limits and false assurance traps

- **Compliant is the customer's definition.** `complianceState` says the device met whatever policies the
  customer assigned, which may be none. Verity never reads `compliant` as encrypted or locked; each check
  reads its own setting. A device with no compliance policy counts as compliant by default: the tenant
  setting for devices without a policy defaults to Compliant [S22]. Flag devices with no assigned policy.
- **Hidden is not retired.** Cleanup rules hide stale devices without deleting them from Entra ID [S8].
  A device that vanishes from the list is recorded as `disappeared`, never as returned or wiped.
- **Policy versus state.** For screen lock Intune reports the policy evaluation, not the live idle value.
  The evidence says which one it is.
- **Co-managed and partner devices.** `managementAgent` values `jamf` and
  `googleCloudDevicePolicyController` mean another tool manages the device [S6]. Read them from that
  provider; do not double count.
- **Sync lag.** `lastSyncDateTime` is the last successful sync, not the last time the device was on.

## 9. Product and UI

- Connect form: no fields (OAuth consent). Settings: platforms in scope, personal devices in or out (with
  reason), screen lock limit, minimum OS per platform, out of contact days.
- Health states: connected, consent missing for device permissions (device checks `error`), no Intune
  licence (all device checks `error` with the licence reason), stale.
- In product guide needed: yes, because the consent needs a privileged role and the screen lock check
  depends on how the customer configured Intune.

## 10. Implementation notes

- Token: client credentials through `azidentity`, scope `https://graph.microsoft.com/.default`; the core
  hands the collector a short lived token (01-evidence-model section 1.5).
- Paging: follow `@odata.nextLink` to the end; any break gives `truncated`. Use `$select` on the list
  call; some properties are only returned on a single device GET [S6].
- Throttling: one limiter per tenant, honour 429 and `Retry-After` [S7].
- Fixtures: record a tenant with Windows, macOS, iOS and a personal Android device, one device never
  synced for 30 days, one retired device, one wipe pending and one done. Test account: an Intune free
  trial tenant, which Microsoft documents with a trial EMS subscription [S1]. The Microsoft 365 E5
  developer sandbox is limited to Visual Studio Professional or Enterprise subscribers [S23].
- Error mapping: 401 or 403 on the device list gives `error` with "permission missing"; a licence error
  gives `error` with "no Intune licence"; 404 on reports gives `insufficient` for the report based checks.
- Scope drift: the granted permission list is read from the token roles at each run; a removed permission
  turns only its checks into `error`.
- Matching: serial number first, then `azureADDeviceId` to the Entra device and Defender `aadDeviceId`.

## 11. How comparable platforms do it

| Platform | Auth and permissions | What they test |
|---|---|---|
| Vanta | App registration with `DeviceManagementManagedDevices.Read.All`, `DeviceManagementConfiguration.Read.All` and `User.Read.All` (primary user to match devices to people); reads compliance policies only, not configuration profiles [S12] | screen lock, antivirus and encryption through compliance policies; password manager and antivirus from the macOS app inventory |
| Drata | Corrected: the current guide asks `DeviceManagementManagedDevices.Read.All` and `DeviceManagementConfiguration.Read.All`, plus `DeviceManagementApps.Read.All` only for the password manager check; legacy setups also held `User.Read.All` and `DeviceManagementScripts.Read.All`. Supports macOS and Windows [S13] | Intune's own compliance result, except the password manager check and a macOS screen lock option, which read configuration policy settings |
| Secureframe | Permissions not named on the page read [S24] | screen lock, built in antivirus, firewall, disk encryption, password, device present, on Mac and Windows |
| Sprinto | Not researched in this round: unverified | |

## 12. Sources

- [S1] Microsoft Graph, managedDevice resource (Intune licence note): https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-manageddevice?view=graph-rest-1.0
- [S2] Grant tenant wide admin consent (roles that can consent): https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent and https://learn.microsoft.com/en-us/graph/permissions-overview
- [S3] List managedDevices (permissions): https://learn.microsoft.com/en-us/graph/api/intune-devices-manageddevice-list?view=graph-rest-1.0
- [S4] List BitLocker recovery keys: https://learn.microsoft.com/en-us/graph/api/bitlocker-list-recoverykeys?view=graph-rest-1.0
- [S5] Intune in Microsoft 365 Business Premium: https://learn.microsoft.com/en-us/microsoft-365/admin/security-and-compliance/m365bp-devices-enrollment
- [S6] managedDevice properties and actions: same page as S1
- [S7] Microsoft Graph throttling limits: https://learn.microsoft.com/en-us/graph/throttling-limits
- [S8] Intune device cleanup rules: https://learn.microsoft.com/en-us/intune/governance/configure-cleanup-rules
- [S9] windows10CompliancePolicy resource: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-windows10compliancepolicy?view=graph-rest-1.0
- [S10] Intune reports available through export: https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/reports-export-graph-available-reports
- [S11] windowsProtectionState resource: https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-windowsprotectionstate?view=graph-rest-1.0
- [S12] Vanta, connecting Intune: https://help.vanta.com/en/articles/11345786-connecting-vanta-microsoft-endpoint-manager-intune-mdm
- [S14] Module paths: https://github.com/microsoftgraph/msgraph-sdk-go/blob/main/go.mod , https://github.com/microsoftgraph/msgraph-beta-sdk-go/blob/main/go.mod , https://github.com/Azure/azure-sdk-for-go/blob/main/sdk/azidentity/go.mod
- [S15] Create deviceManagementExportJob (permissions): https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementexportjob-create?view=graph-rest-1.0 and the beta page
- [S16] Microsoft Intune pricing: https://www.microsoft.com/en-us/security/business/microsoft-intune-pricing
- [S17] macOSCompliancePolicy resource: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-macoscompliancepolicy?view=graph-rest-1.0
- [S18] Manage stale devices in Entra ID (BitLocker keys deleted with the device): https://learn.microsoft.com/en-us/entra/identity/devices/manage-stale-devices
- [S19] Export Intune reports with Graph: https://learn.microsoft.com/en-us/intune/device-management/reports/export-graph-apis
- [S20] deviceActionResult resource: https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-deviceactionresult?view=graph-rest-1.0
- [S21] List auditEvents: https://learn.microsoft.com/en-us/graph/api/intune-auditing-auditevent-list?view=graph-rest-1.0
- [S22] Device compliance policies (no policy assigned setting): https://learn.microsoft.com/en-us/intune/intune-service/protect/device-compliance-get-started
- [S23] Microsoft 365 Developer Program with Visual Studio: https://learn.microsoft.com/en-us/office/developer-program/join-with-visual-studio
- [S24] Secureframe, supported MDMs: https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
- [S13] Drata, Intune integration guide: https://help.drata.com/en/articles/16190016-microsoft-intune-integration-guide and https://help.drata.com/en/articles/5604949-microsoft-intune-integration-guide-windows
