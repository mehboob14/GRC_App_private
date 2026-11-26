# Research round 2: Microsoft Intune, Entra devices and Autopilot

Brief: [BRIEF.md](BRIEF.md). Round 1: [../../connectors/intune.md](../../connectors/intune.md),
[../../connectors/microsoft-defender-endpoint.md](../../connectors/microsoft-defender-endpoint.md),
[../../connectors/entra-id.md](../../connectors/entra-id.md),
[../../mdm-and-endpoint-strategy.md](../../mdm-and-endpoint-strategy.md),
[../../verification/devices-hr.md](../../verification/devices-hr.md). This file extends round 1 and does not repeat
what round 1 verified unless it changes. Source ids are `[Mn]` (section 8). "U" means unverified.

## 1. Scope

| Item | Covered |
|---|---|
| Products | Microsoft Intune (Plan 1 level features), Microsoft Entra ID device objects, Windows Autopilot, Intune app protection (MAM), Intune Data Warehouse, Windows 365 Cloud PC and Azure Virtual Desktop as Intune devices. Defender for Endpoint only for software inventory (EP-04) |
| Platforms | Windows 10 and 11 (Entra joined, hybrid joined, Autopilot, Autopilot device preparation, personal Windows with a work account, co-managed with Configuration Manager), macOS, iOS and iPadOS (ADE, device enrolment, account driven user enrolment), Android Enterprise (fully managed, dedicated, corporate owned work profile, personally owned work profile), Linux (Ubuntu 24.04 and 26.04 LTS, RHEL 9 and 10 [M30]), Windows 365 Cloud PC, AVD single and multi session |
| APIs | Microsoft Graph v1.0 and beta (`https://graph.microsoft.com`), Intune Data Warehouse API (`https://api.manage.microsoft.com/` token resource [M62]), Defender for Endpoint API (`https://api.security.microsoft.com`) |
| Go | `github.com/microsoftgraph/msgraph-sdk-go` (v1.0), shown in Microsoft's own Go samples [M35][M42]; beta module and `azidentity` paths as confirmed in round 1 (intune.md S14). Data Warehouse and Defender: plain REST |
| Date read | 2026-11-26 (all pages fetched in this session) |
| Excluded | Writes of any kind, device commands, recovery key material, Jamf or Google partner records (other files), Configuration Manager's own APIs |

## 2. Visibility by platform and channel

Cells: yes; partial (why); no; n/a. Each cell rests on the field map in section 3; where a platform behaviour is
inferred and not documented the cell says U.

### 2.1 Computers

Columns: **W-J** Windows Entra joined (includes Autopilot); **W-H** Windows hybrid joined; **W-CO** co-managed with
Configuration Manager; **W-P** personal Windows with a work account added; **MAC** macOS; **LNX** Linux; **CPC**
Windows 365 Cloud PC; **AVD-M** AVD multi session host.

| Key | W-J | W-H | W-CO | W-P | MAC | LNX | CPC | AVD-M |
|---|---|---|---|---|---|---|---|---|
| provider_device_id | yes | yes | yes | yes | yes | yes (new id after broker 2.0.2 update [M31]) | yes | yes |
| serial_number | yes | yes | yes | yes | yes | partial (Linux not listed for serial [M33], U) | U | U |
| hardware_ids | n/a | n/a | n/a | no (personal) | partial (UDID only by single GET [M1]) | n/a | n/a | n/a |
| hostname, device_name | yes | yes | yes | yes | yes | yes | yes | yes |
| manufacturer, model | yes | yes | yes | yes | yes | U | yes | yes |
| platform | yes | yes | yes | yes | yes | yes (beta `deviceType` linux [M2]) | yes (beta `deviceType` cloudPC [M2]) | partial (edition only through `skuFamily`, U) |
| os_version, os_build | partial (build sits inside `osVersion`) | same | same | same | partial (build U) | U | same as W-J | same as W-J |
| device_class | partial (beta `chassisType` [M2]) | partial | partial | partial | partial | U | yes (cloudPC) | partial (U) |
| ownership | yes | yes | yes | yes (personal) | yes | yes | yes | yes |
| enrolment_channel | yes | partial (beta `joinType` [M2]) | yes | yes | partial (ADE vs user approved from enrolment type) | partial (no Linux enrolment value seen, U) | partial | partial |
| supervised | n/a | n/a | n/a | n/a | yes | n/a | n/a | n/a |
| management_state | partial (beta only [M2]) | partial | partial | partial | partial | partial | partial | partial |
| enrolled_at | partial (Autopilot devices show registration time [M33]) | yes | yes | yes | yes | yes | yes | yes |
| last_check_in_at | yes | yes | yes | yes | yes | yes | yes | yes |
| provider_compliance_state | yes | yes | partial (`configManager` value, meaning U) | yes | yes | yes | yes (see gotchas) | partial (device targeted policy only [M54]) |
| assigned_user_* | yes | yes | yes | yes | yes | yes | yes | partial (shared host, U) |
| disk_encryption | yes | yes | yes | yes | partial (FileVault mapping of `isEncrypted` U) | partial (only through a compliance setting [M30]) | no (encryption setting not applicable [M53]) | no (not a supported setting [M54]) |
| recovery_key_escrowed | yes (BitLocker metadata [M35]) | partial (keys kept only in on premises AD are not visible, U) | yes | yes | no (no metadata API [M38]) | no | n/a | n/a |
| passcode_present, passcode_compliant | partial (setting state, only if a policy asks) | partial | partial | partial | partial | partial (complexity only [M30]) | partial | partial (no "require password" setting [M54]) |
| idle_lock_seconds | partial (policy value, origin policy) | partial | partial | partial | partial | no (no idle setting [M30]) | partial (U) | no [M54] |
| firewall_on | partial (setting state when policy requires firewall) | partial | partial | partial | partial (`firewallEnabled` setting) | no | partial (U) | partial (firewall supported [M54]) |
| os_integrity | partial (attestation at boot [M23]) | partial | partial | partial | partial (SIP setting) | no | partial (Secure Boot needs reprovision [M53]) | no [M54] |
| activation_lock_or_frp | n/a | n/a | n/a | n/a | no (never read the bypass code) | n/a | n/a | n/a |
| removable_storage_blocked | no (not researched) | no | no | no | no | no | no | no |
| local_admin_present | no (U) | no | no | no | no | no | no | no |
| av_present, av_realtime_on, av_signatures_current | yes [M3] | yes | yes | yes | no | no | yes | yes |
| edr_present | partial (beta agent `msSense` [M2], Defender connector is authority) | partial | partial | partial | partial | partial | partial | partial |
| os_update_policy_assigned | U | U | U | U | U | U | U | U |
| os_supported | partial (Defender end of support data [M58]) | partial | partial | partial | U | U | partial | partial |
| browser_versions | partial (inventory every 7 days [M33]) | partial | partial | no (personal) | partial | U | partial | partial |
| installed_apps | yes [M56] | yes | yes | no (personal: managed apps only [M32]) | yes | U | yes | yes |
| managed_apps | yes | yes | yes | yes | yes | U | yes | yes |
| device.action | yes | yes | yes | yes | yes | no (Linux not listed for wipe or retire [M66][M67]) | partial (U) | partial (wipe, lock not supported [M54]) |

### 2.2 Phones and tablets

Columns: **I-ADE** iOS or iPadOS ADE (supervised); **I-DE** device enrolment through Company Portal; **I-UE** account
driven user enrolment; **A-FM** Android fully managed; **A-DED** dedicated; **A-COPE** corporate owned work profile;
**A-WP** personally owned work profile; **MAM** app protection only, no enrolment.

| Key | I-ADE | I-DE | I-UE | A-FM | A-DED | A-COPE | A-WP | MAM |
|---|---|---|---|---|---|---|---|---|
| provider_device_id | yes | yes | yes (enrolment id lost on unenrol [M34]) | yes | yes | yes | yes | partial (per app registration, `deviceTag` groups apps [M45]) |
| serial_number | yes | yes | no [M34] | yes | yes | yes | partial (not shown on Android 12 and later [M33]) | no |
| hardware_ids (company only) | yes | yes if company | no [M34] | yes | yes | partial (no phone number [M33]) | no (rule, and not reported [M33]) | no |
| device_name, manufacturer, model | yes | yes | yes | yes | yes | yes | yes | partial (`deviceName`, `deviceType` [M45]) |
| platform, os_version | yes | yes | yes | yes | yes | yes | yes | yes (`platformVersion`) |
| security_patch_level | partial (beta `securityPatchLevel` [M2]) | partial | partial | yes (`androidSecurityPatchLevel` [M1]) | yes | yes | yes | no |
| device_class | partial | partial | partial | partial | yes (enrolment type 15 [M65]) | partial | partial | no |
| ownership | yes | yes | yes | yes | yes | yes | yes | no (treat as unknown) |
| enrolment_channel | yes | yes | yes (enum lists disagree, see 6) | yes | yes | yes | partial (no distinct value found, U) | yes (no device record) |
| supervised | yes | yes (false) | yes (never supervised [M34]) | n/a | n/a | n/a | n/a | n/a |
| management_state, lost_mode | partial (beta `lostModeState` [M2]) | partial | partial | partial | partial | partial | partial | n/a |
| last_check_in_at | yes | yes | yes | yes | yes | yes | yes | partial (app sync time) |
| provider_compliance_state | yes | yes | yes | yes | yes | yes | yes | no (app protection status needs an export job) |
| assigned_user_* | yes | yes | yes | yes | partial (often userless) | yes | yes | yes (`userId`) |
| disk_encryption | partial (passcode turns encryption on [M26]) | partial | partial | yes (always enforced [M29]) | yes | yes | yes | no |
| passcode_present, passcode_compliant | partial (setting state) | partial | partial | partial | partial | partial | partial (device and work profile passwords [M29]) | no |
| idle_lock_seconds | partial (policy value) | partial | partial | partial (policy class beta only [M27]) | partial | partial | partial | no |
| os_integrity | yes (`jailBroken`) | yes | yes | yes (`jailBroken`, Play Integrity setting [M29]) | yes | yes | yes | partial (`flaggedReasons` rootedDevice [M47]) |
| activation_lock_or_frp | no (U) | no | n/a | no (U) | no | no | n/a | n/a |
| av_*, edr_present | partial (threat partner state [M1]) | partial | partial | partial | partial | partial | partial | no |
| os_update_available | no | no | no | partial (beta setting [M27]) | partial | partial | no | no |
| installed_apps | yes | yes if company | no (managed volume only [M34]) | yes | yes | partial (work profile only [M32]) | no | no |
| managed_apps | yes | yes | yes | yes | yes | yes | yes | yes [M45] |
| device.action | yes | yes | partial (retire, lock, sync only [M34]) | yes [M66] | yes | yes | partial (retire only [M66][M67]) | U (selective wipe not researched) |

### 2.3 The second population (known to Microsoft, not managed)

Columns: **AP** registered for Autopilot, not enrolled; **REG** Entra registered only (`trustType` Workplace);
**JN** Entra or hybrid joined but `isManaged` false; **SI** devices seen in sign ins.

| Key | AP [M39] | REG [M41] | JN [M41] | SI [M44] |
|---|---|---|---|---|
| provider_device_id | yes | yes | yes | partial (`deviceId` only for registered devices) |
| serial_number | yes | no | no | no |
| manufacturer, model | yes | yes | yes | no |
| platform, os_version | partial (Windows, no version) | yes | yes | yes (`operatingSystem`) |
| ownership | partial (company by inference) | partial (`deviceOwnership` is set by Intune) | partial | no |
| enrolment_channel | automated_company, not enrolled (`enrollmentState`) | registered_only | registered_only | registered_only or unknown |
| last_check_in_at | partial (`lastContactedDateTime`) | partial (activity timestamp, 14 day steps [M43]) | partial | yes (sign in time) |
| assigned_user_* | partial (`userPrincipalName`) | partial (registered owners, U) | partial | yes |
| provider_compliance_state | no | yes (`isCompliant`) | yes | yes (`isCompliant`, `isManaged`) |
| everything else | no | no | no | partial (`browser` [M44]) |

## 3. Field map

Permission names are application permissions on Microsoft Graph unless stated. All Intune Graph calls need an active
Intune licence (round 1, intune.md S1; repeated on every page read [M1]).

| Key | Endpoint (version) | Field | Least read permission | Licence | Caveats | Status |
|---|---|---|---|---|---|---|
| provider_device_id | `GET /deviceManagement/managedDevices` (v1.0) | `id`; link `azureADDeviceId` | DeviceManagementManagedDevices.Read.All | Intune P1 | Linux broker update re-enrols with new Intune and Entra ids [M31] | V [M1][M31] |
| serial_number | same | `serialNumber` | same | same | Absent for Apple user enrolment [M34] and Android personal work profile on 12 and later [M33] | V [M1][M33][M34] |
| serial_number (Autopilot) | `GET /deviceManagement/windowsAutopilotDeviceIdentities` (v1.0) | `serialNumber` | DeviceManagementServiceConfig.Read.All | Intune P1 | Devices set up by Autopilot device preparation need not be registered here [M64] | V [M39][M40][M64] |
| hardware_ids | managedDevices | `imei`, `meid`; `udid` only on a single GET with `$select` | DeviceManagementManagedDevices.Read.All | same | Read only for company owned; skip for personal | V [M1] |
| hostname, device_name | managedDevices | `deviceName`, `managedDeviceName` | same | same | | V [M1] |
| manufacturer, model | managedDevices | `manufacturer`, `model` | same | same | | V [M1] |
| platform | managedDevices | `operatingSystem`; beta `deviceType` (includes `cloudPC`, `linux`, `androidEnterprise`) | same | same | `deviceType` is beta only | V [M1][M2] |
| os_version | managedDevices | `osVersion` | same | same | Windows build is the third part of the version string (Verity reading) | V [M1] |
| os_build | beta managedDevices | `hardwareInformation.osBuildNumber` (single GET) | same | same | Per device GET cost; documented for Android in the admin centre [M33] | V [M2][M33] |
| device_class | beta managedDevices | `chassisType` (desktop, laptop, phone, tablet, enterpriseServer and others); `deviceType` cloudPC | same | same | Beta only | V [M2] |
| device_class (shared, kiosk) | Entra `GET /devices` | `profileType` (Shared) | Device.Read.All | Entra ID (U on tier) | | V [M41][M42] |
| ownership | managedDevices | `managedDeviceOwnerType` (unknown, company, personal) | DeviceManagementManagedDevices.Read.All | Intune P1 | iOS defaults to personal unless registered by serial or IMEI (search summary, U) | V [M1] |
| enrolment_channel | managedDevices | `deviceEnrollmentType`, `enrollmentProfileName`; beta `joinType`, `autopilotEnrolled`, `managementAgent` (beta adds `msSense`, `microsoft365ManagedMdm`, `intuneAosp`, `google`) | same | same | Mapping in 3.1 | V [M1][M2][M65] |
| supervised | managedDevices | `isSupervised` | same | same | Apple only | V [M1] |
| management_state | beta managedDevices | `managementState` (managed, retirePending, retireFailed, wipePending, wipeFailed, unhealthy, deletePending, retireIssued, wipeIssued, wipeCanceled, retireCanceled, discovered); `lostModeState` | same | same | Beta only; v1.0 has neither | V [M2] |
| enrolled_at | managedDevices | `enrolledDateTime` | same | same | For Autopilot devices the admin centre shows Autopilot registration time [M33]: do not use it for "before issue" | V [M1][M33] |
| last_check_in_at | managedDevices | `lastSyncDateTime` | same | same | Last successful sync only | V [M1] |
| provider_compliance_state | managedDevices | `complianceState` (unknown, compliant, noncompliant, conflict, error, inGracePeriod, configManager); `complianceGracePeriodExpirationDateTime` | same | same | Secondary evidence only | V [M1] |
| compliance_policies | `GET /deviceManagement/deviceCompliancePolicies` and `/{id}/deviceStatuses` (v1.0) | policy settings; status, `lastReportedDateTime` | DeviceManagementConfiguration.Read.All | same | `deviceComplianceDeviceStatus` has no `deviceId`, only `id`, `deviceDisplayName`, `userPrincipalName` [M10]: join by id format is U | V [M10][M21] |
| compliance_policies (per setting) | `GET /deviceManagement/deviceCompliancePolicySettingStateSummaries` then `/{id}/deviceComplianceSettingStates` (v1.0) | `setting`, `settingName`, `deviceId`, `userPrincipalName`, `state` (unknown, notApplicable, compliant, remediated, nonCompliant, error, conflict, notAssigned) | DeviceManagementConfiguration.Read.All | same | Only settings a compliance policy evaluates; exact `setting` strings (class.property) U until a fixture | V [M6][M7][M8][M9] |
| compliance_policies (no policy) | `POST /deviceManagement/reports/getDevicesWithoutCompliancePolicyReport` (v1.0) | report stream | DeviceManagementConfiguration.Read.All (or Managed Devices or Apps Read.All) | same | Synchronous report action; returns a stream; columns U | V [M17] |
| compliance_policies (noncompliant settings) | `POST /deviceManagement/reports/getNoncompliantDevicesAndSettingsReport` (v1.0) | report stream | same | same | Columns of the export version are DeviceId, PolicyName, SettingName, SettingStatus [M13]; the action's columns U | V [M16][M13] |
| assigned_user_email | managedDevices | `userPrincipalName`, `emailAddress`, `userId`; relationship `users` (primary users) | DeviceManagementManagedDevices.Read.All | same | assignment_source: `users` is the primary user [M1]; enrolling user is shown in the admin centre [M33], Graph field U | V [M1] |
| disk_encryption | managedDevices | `isEncrypted` | same | same | macOS meaning U; Windows encryption status covers the OS drive only [M37] | V [M1][M37] |
| disk_encryption (Windows, attested) | managedDevices | `deviceHealthAttestationState.bitLockerStatus` | same | same | Measured at boot, reboot needed after encryption [M23] | V [M1][M23] |
| disk_encryption (policy result) | setting states | `storageRequireEncryption`, `bitLockerEnabled` (Windows), `storageRequireEncryption` (macOS, Android) | DeviceManagementConfiguration.Read.All | same | Cloud PC: not applicable; AVD multi session: not supported [M53][M54] | V [M21][M24][M28][M53][M54] |
| encryption_method | derived from platform | FileVault, BitLocker, platform data protection, LUKS (Linux recognises dm-crypt [M30]) | n/a | n/a | Verity derivation | V [M30] (Linux), derivation otherwise |
| recovery_key_escrowed (Windows) | `GET /informationProtection/bitlocker/recoveryKeys` (v1.0) | `id`, `deviceId`, `createdDateTime`, `volumeType` (1 OS, 2 fixed, 3 removable) | BitlockerKey.ReadBasic.All | none beyond Entra (U) | Never `$select=key`. `User-Agent` header required [M35]. No `$top`. Match `deviceId` to managed device `azureADDeviceId` (U, test) | V [M35][M36] |
| recovery_key_escrowed (macOS) | none | none | n/a | n/a | The only Graph route is beta `getFileVaultKey`, which returns the key and needs DeviceManagementManagedDevices.PrivilegedOperations.All [M38]: never used. `bootstrapTokenEscrowed` is a different token [M2] | V [M38][M2] |
| passcode_present, passcode_compliant | setting states | Windows and macOS `passwordRequired`; iOS `passcodeRequired`; Android `passwordRequired` | DeviceManagementConfiguration.Read.All | Intune P1 | Only when a policy requires it | V [M21][M24][M25][M28] |
| idle_lock_seconds (origin policy) | compliance policy object | `passwordMinutesOfInactivityBeforeLock` (Windows, macOS, Android), `passcodeMinutesOfInactivityBeforeLock` (iOS) | same | same | Policy value, not a device report. iOS screen timeout (up to 15 minutes [M26]) has no v1.0 field: beta name U. Android fully managed class is beta only [M27] | V [M21][M24][M25][M27][M28] |
| idle_lock_seconds (origin device_reported) | none found | none | n/a | n/a | Intune does not report the device's live idle value | U (not found) |
| firewall_on (Windows) | setting states for the policy setting backed by `activeFirewallRequired` | `state` | DeviceManagementConfiguration.Read.All | same | `activeFirewallRequired` is on the beta policy resource only [M22]; v1.0 policy lacks it [M21]. Error state right after reboot or wake; group policy override gives Not compliant [M23] | V [M21][M22][M23][M7] |
| firewall_on (Windows report) | `FirewallStatus` export job | `FirewallStatus`, `LastReportedDateTime` | only ReadWrite documented | same | Rechecked 2026-11-26: v1.0 and beta still list ReadWrite only [M11][M12] | V [M11][M12][M13] |
| firewall_on (macOS) | setting states | `firewallEnabled` | DeviceManagementConfiguration.Read.All | same | | V [M24][M7] |
| os_integrity (Windows) | managedDevices | `deviceHealthAttestationState.secureBoot`, `.codeIntegrity`, `.bootDebugging`, `.testSigning` | DeviceManagementManagedDevices.Read.All | same | Secure Boot on devices without TPM 2.0 reports Not compliant [M23] | V [M1][M23] |
| os_integrity (macOS) | setting states | `systemIntegrityProtectionEnabled` | DeviceManagementConfiguration.Read.All | same | | V [M24] |
| os_integrity (mobile) | managedDevices; setting states | `jailBroken` (string); Android `securityRequireSafetyNetAttestationBasicIntegrity`, `...CertifiedDevice` | both | same | `jailBroken` defaults to an empty string [M1] | V [M1][M28] |
| activation_lock_or_frp | none read | `activationLockBypassCode` exists [M1] but is a secret | n/a | n/a | Never select it | V [M1] |
| av_present, av_realtime_on, av_signatures_current | `GET /deviceManagement/managedDevices/{id}/windowsProtectionState` | `malwareProtectionEnabled`, `realTimeProtectionEnabled`, `signatureUpdateOverdue`, `productStatus`, `tamperProtectionEnabled`, `lastReportedDateTime` | DeviceManagementManagedDevices.Read.All (beta also lists Configuration.Read.All) | same | v1.0 documents the path through `detectedApps/.../managedDevices/{id}` [M4]; the direct navigation exists as a relationship [M1]. Booleans default to the client setting [M3] | V [M1][M3][M4][M5] |
| edr_present | beta managedDevices | `managementAgent` value `msSense` | DeviceManagementManagedDevices.Read.All | same | Defender connector is the authority | V [M2] |
| os_update_available (Android) | beta compliance policy | `requireNoPendingSystemUpdates` | DeviceManagementConfiguration.Read.All | same | Beta, fully managed class only | V [M27] |
| security_patch_level | managedDevices | `androidSecurityPatchLevel`; beta `securityPatchLevel` (iOS and macOS format "(a)") | DeviceManagementManagedDevices.Read.All | same | | V [M1][M2] |
| os_supported | Defender `GET /api/machines/SoftwareInventoryByMachine` | `EndOfSupportStatus`, `EndOfSupportDate` | Software.Read.All (WindowsDefenderATP) | Defender vulnerability data (tier U) | Snapshot, no history [M58] | V [M58] |
| browser_versions, installed_apps | `GET /deviceManagement/detectedApps` and `/{id}/managedDevices` (v1.0) | `displayName`, `version`, `publisher`, `platform`, `deviceCount` | DeviceManagementManagedDevices.Read.All | Intune P1 | Inventory refreshes every 7 days [M33]; personal devices show managed apps only [M32] | V [M56][M33][M32] |
| browser_versions (Defender) | `GET /api/machines/SoftwareInventoryByMachine` | `SoftwareName`, `SoftwareVendor`, `SoftwareVersion`, `DeviceId` | Software.Read.All | as above | 30 calls a minute, 1,000 an hour, page up to 200,000 [M58]; only software with a CPE | V [M58] |
| managed_apps (MAM) | `GET /deviceAppManagement/managedAppRegistrations` (v1.0) | `appIdentifier`, `applicationVersion`, `deviceName`, `deviceType`, `platformVersion`, `lastSyncDateTime`, `flaggedReasons`, `userId`; relationships `appliedPolicies`, `intendedPolicies` | DeviceManagementApps.Read.All | Intune P1 | `flaggedReasons` v1.0 values: none, rootedDevice [M47] | V [M45][M46][M47] |
| device.action (current) | managedDevices | `deviceActionResults[]`: `actionName`, `actionState`, `startDateTime`, `lastUpdatedDateTime` | DeviceManagementManagedDevices.Read.All | same | How long entries stay: U | V [M1] |
| device.action (history) | `GET /deviceManagement/remoteActionAudits` (beta) | `action` (factoryReset, removeCompanyData, remoteLock, enableLostMode, and others), `actionState`, `requestDateTime`, `initiatedByUserPrincipalName`, `managedDeviceId`, `deviceActionCategory` | DeviceManagementManagedDevices.Read.All | same | Beta only; retention U; completion time not a field (state only) | V [M49][M50] |
| second population: Entra | `GET /devices` (v1.0), `delta` supported | `isManaged`, `isCompliant`, `trustType` (Workplace, AzureAd, ServerAd), `approximateLastSignInDateTime`, `deviceOwnership`, `managementType`, `enrollmentType`, `registrationDateTime`, `accountEnabled` | Device.Read.All | Entra ID (U on tier) | Activity timestamp moves in steps of 14 days plus or minus 5 [M43] | V [M41][M42][M43][M51] |
| second population: Autopilot | `GET /deviceManagement/windowsAutopilotDeviceIdentities` (v1.0) | `enrollmentState` (unknown, enrolled, pendingReset, failed, notContacted), `lastContactedDateTime`, `managedDeviceId`, `serialNumber`, `groupTag`, `userPrincipalName` | DeviceManagementServiceConfig.Read.All | Intune P1 | `productKey` is listed: do not select it | V [M39][M40] |
| second population: sign ins | `GET /auditLogs/signIns` (owned by entra-id.md) | `deviceDetail.isCompliant`, `.isManaged`, `.trustType`, `.operatingSystem`, `.browser` | AuditLog.Read.All (entra-id.md) | Entra ID P1 (entra-id.md) | `deviceId` and name only for registered devices [M44] | V [M44] |
| history (any key above) | Intune Data Warehouse `devicePropertyHistories` | daily snapshot per device: `complianceStateKey`, `managementStateKey`, `OSVersion`, `jailBroken`, `ownerTypeKey`, `azureADRegistered` | Intune API application permission `get_data_warehouse` | Intune P1 (U) | 60 days of daily rows [M61]; encryption is on the `devices` table only, not in history [M61] | V [M60][M61][M62] |

### 3.1 Enrolment channel mapping (Verity reading, test on fixtures)

| Signal | enrolment_channel |
|---|---|
| `deviceEnrollmentType` appleBulkWithUser (3), appleBulkWithoutUser (4) [M65] | automated_company (ADE) |
| windowsAzureADJoin (5), windowsAzureADJoinUsingDeviceAuth (10), windowsBulkAzureDomainJoin (8), beta `autopilotEnrolled` true [M2][M65] | automated_company when Autopilot, else user_initiated_device |
| windowsCoManagement (9) | user_initiated_device or automated_company (Autopilot or group policy trigger [M65]) |
| windowsAutoEnrollment (7, "add work account") with owner personal | user_initiated_device, personal |
| userEnrollment (1): user driven BYOD channel [M65] | user_initiated_device (not Apple user enrolment) |
| appleUserEnrollment (11), appleUserEnrollmentWithServiceAccount (12), appleAccountDrivenUserEnrollment (25) | byod_account_driven |
| androidEnterpriseFullyManaged (16), androidEnterpriseDedicatedDevice (15) | automated_company or user_initiated_device (zero touch not distinguishable, U) |
| androidEnterpriseCorporateWorkProfile (17) | work_profile_company |
| Android personal work profile: no dedicated value found | work_profile_personal from beta `deviceType` androidForWork plus owner personal (U) |
| azureAdJoinUsingAzureVmExtension (14) | automated_company, device_class virtual |
| `managementAgent` eas only | registered_only (mail only) |
| `managementAgent` jamf, googleCloudDevicePolicyController, beta google | another provider: do not count here |
| Entra device with `isManaged` false | registered_only |
| Autopilot identity with `enrollmentState` notContacted | inventory_only (company, never enrolled) |

## 4. Auth and permissions

Same multi tenant app registration and consent as the Entra ID connector (round 1). Graph application consent needs
Privileged Role Administrator or Global Administrator (round 1, intune.md S2).

| Permission | API | Read only | Needed for | New vs round 1 |
|---|---|---|---|---|
| DeviceManagementManagedDevices.Read.All | Graph | yes | device list, protection state, detected apps, remote action audits (beta) | held |
| DeviceManagementConfiguration.Read.All | Graph | yes | compliance policies, per setting states, synchronous report actions | held |
| BitlockerKey.ReadBasic.All | Graph | yes, key not returned | BitLocker escrow metadata | held |
| DeviceManagementServiceConfig.Read.All | Graph | yes | Autopilot identities (second population) [M40] | new |
| Device.Read.All | Graph | yes | Entra device objects (second population) [M42] | new for this connector (round 1 said not needed) |
| DeviceManagementApps.Read.All | Graph | yes | MAM registrations and statuses [M46][M48]; also Intune audit events (round 1) | new, optional (BYOD phones) |
| `get_data_warehouse` | Intune (`https://api.manage.microsoft.com/`) | yes | 60 days of device history at connect time [M62] | new, optional |
| Software.Read.All | WindowsDefenderATP | yes | per device software and browser versions, end of support [M57][M58] | new, optional (EP-04) |

Never requested: any ReadWrite permission (export jobs stay out), DeviceManagementManagedDevices.PrivilegedOperations.All
(FileVault key), BitlockerKey.Read.All. Report actions under `/deviceManagement/reports/get...` use POST but are
documented with Read permissions [M16][M17][M18][M19][M20]; a recorded test must confirm a Read only token is
accepted before release, as round 1 required for exports.

What the credential sees: every managed device and policy in the tenant (no Intune scope tag limits for app only
tokens, U), every Entra device, every Autopilot record, and MAM registrations.

## 5. Limits

| Topic | Fact | Source |
|---|---|---|
| Throttling | Intune devices section: 2,000 requests per 20 s per app per tenant, 4,000 per tenant. Most other Intune sections (device configuration, enrollment, managed applications, auditing): 1,000 per app per tenant, 2,000 per tenant. Global 130,000 per 10 s per app | V [M63] |
| Export jobs | 100 a minute per tenant, 48 per app (not used) | V [M14] |
| Defender software | JSON export 30 a minute and 1,000 an hour; file export 5 a minute and 20 an hour | V [M58] |
| Paging | `@odata.nextLink` on Graph lists; BitLocker list has no `$top` [M35] | V [M35] |
| Delta | Not offered for any Intune resource; offered for Entra `device` (token valid 7 days) | V [M51] |
| Per device cost | `udid`, `ethernetMacAddress`, `physicalMemoryInBytes`, `notes` (v1.0) and beta `hardwareInformation`, `bootstrapTokenEscrowed`, `windowsActiveMalwareCount` come back only on a single GET with `$select` | V [M1][M2] |
| Check in | Maintenance sync about every 8 hours on all platforms, at most one every 6.5 hours; new enrolments sync more often for the first hours (macOS then about hourly per the table) | V [M52] |
| Windows compliance | Firewall, antivirus, BitLocker, Defender status, OS build, real time protection and Secure Boot changes trigger near real time re-evaluation | V [M23] |
| Inventory | Hardware and software inventory refresh every 7 days from enrolment | V [M33] |
| Encryption status | Up to 24 hours to reach Intune | V [M37] |
| Entra activity | Activity timestamp updates only when 14 days (plus or minus 5) have passed; some active devices have none | V [M43] |
| History | Graph Intune resources are current state. Data Warehouse: daily snapshot at midnight UTC, `devicePropertyHistories` 60 days; most fact tables about 30 days. Defender software export: snapshot only. `getHistoricalReport` exists [M19] but its content is undocumented (U) | V [M60][M61][M58] |
| Orphans | AVD multi session records inactive 60 days or more are deleted by Intune, outside cleanup rules | V [M54] |

## 6. Gotchas that would make a check wrong

1. **Per setting states exist only for what a policy evaluates.** A device with no firewall requirement has no
   firewall state, and settings left "Not configured" are not evaluated [M23]. Absent state is `insufficient`, never
   pass.
2. **Compliance policy objects differ by version.** v1.0 `windows10CompliancePolicy` has no firewall, TPM, antivirus
   or Defender properties [M21]; they exist only in beta [M22]. Android fully managed policies exist only in beta
   [M27]. Read the policy object from beta, the states from v1.0.
3. **`deviceComplianceDeviceStatus` has no device id** [M10]. Use `deviceComplianceSettingStates`, which carries
   `deviceId` [M6].
4. **Windows attestation is measured at boot.** BitLocker via attestation reports compliant only after a reboot
   [M23]. "Encryption of data storage" checks the OS drive and only BitLocker [M23][M37].
5. **Cloud PCs.** Encryption and TPM settings report Not applicable; BitLocker and Secure Boot may report Not
   compliant; customers often exclude Cloud PCs with a filter [M53]. Treat Cloud PC encryption as `not_applicable`
   with that reason; that Windows 365 encrypts storage itself is not stated on the page read (U).
6. **AVD multi session** supports only OS version, password complexity, Defender, firewall, antivirus and MDE risk
   settings; no encryption, no require password, no idle lock; wipe, lock and BitLocker rotation are disabled
   [M54].
7. **Apple user enrolment and Android personal work profile** give no serial, UDID or IMEI [M33][M34]; match on
   Intune id and user only. Neither supports a full wipe [M34][M66].
8. **Enum lists disagree.** The managedDevice beta page lists appleACME values [M2] while the enum page lists
   appleAccountDrivenUserEnrollment (25) [M65]. Unknown values map to `unknown`, never to a default channel.
9. **`userEnrollment` is not Apple user enrolment** [M65]. Round 1 treated it as company data only (section 7).
10. **Autopilot `enrolledDateTime`** shows registration time in the admin centre [M33]; "before issue" cannot use it.
11. **Autopilot device preparation** devices are normally not Autopilot registered [M64], so "registered but never
    enrolled" misses them by design.
12. **Retire on an Entra joined BitLocker device suspends BitLocker** by removing key protectors [M67]. A retired
    leaver laptop may read unencrypted on its last report; record retire first.
13. **Retire keeps the Entra record** for iOS, macOS and Autopilot registered Windows [M67]; a device can vanish
    from Intune and stay in Entra.
14. **`jailBroken` is a string with an empty default** [M1]: empty means unknown.
15. **Inventory lag.** Detected apps and hardware are up to 7 days old [M33] while `lastSyncDateTime` is fresh.
16. **Secrets on the device record.** `activationLockBypassCode` [M1] and Autopilot `productKey` [M39] must never be
    selected; the default list returns the bypass code as null [M1].
17. **Entra activity timestamp** cannot support a 14 day stale rule; use 21 days or more [M43].
18. **Linux broker 2.0.2 and later** re-enrols devices with new ids [M31]; history must link old and new records by
    serial or name, or show a break.
19. **MDE security settings management** devices appear with beta agent `msSense` [M2]: not MDM enrolled.
20. **Co-managed devices** can return `configManager` as compliance state [M1]; what Intune evaluates in that case
    is not stated (U). Treat as `insufficient` for state checks unless setting states exist.
21. **Data Warehouse history lacks encryption**: `devicePropertyHistories` has no encryption column [M61], so
    "encrypted throughout the period" still needs Verity's daily snapshots.

## 7. Corrections to round 1

| File | Claim | Correction | Source |
|---|---|---|---|
| intune.md 2.2 and 5.2, strategy 5.5 | Windows firewall gives `insufficient` until the export permission is solved | Partly lifted: per device firewall state is readable with DeviceManagementConfiguration.Read.All through `deviceComplianceSettingStates` when a Windows compliance policy requires firewall. Exports still list ReadWrite only (rechecked v1.0 and beta). `FirewallStatus` itself stays out | [M7][M11][M12][M22] |
| intune.md 2.2 | Reports need export jobs | Synchronous report actions (`getNoncompliantDevicesAndSettingsReport`, `getDevicesWithoutCompliancePolicyReport`, `getCachedReport`, `getHistoricalReport`, `getDeviceNonComplianceReport`) list Read permissions | [M15] to [M20] |
| intune.md 5.1 `devices.enrolled` | `managementState` appears only in the v1.0 example | It is a documented beta property with 12 values; still absent from v1.0 | [M1][M2] |
| intune.md 5.1 `devices.remote_wipe` | `userEnrollment` means work data only | `userEnrollment` is user driven BYOD enrolment; Apple user enrolment is 11, 12 and 25. Use the wipe and retire platform lists: no wipe for Android personal work profile, Apple user enrolment, AVD | [M65][M66][M67][M34][M54] |
| intune.md 5.2 `devices.wipes_confirmed` | Audit events (DeviceManagementApps.Read.All) would be the stronger source | Beta `remoteActionAudits` gives action, state, request time and initiator with DeviceManagementManagedDevices.Read.All, no new permission | [M49][M50] |
| intune.md 2.2 | `Device.Read.All` not needed | Needed for the second population (registered only and joined but unmanaged devices) | [M41][M42] |
| intune.md 4 | Compliance "current state only"; Verity's snapshots are the only history | Data Warehouse keeps 60 days of daily device rows (compliance, management state, OS, jailbreak) | [M61] |
| intune.md 5.2, strategy 5.5 `devices.recovery_key_escrowed` macOS | No metadata field found (unverified) | Confirmed for this round: the only Graph route returns the key itself and needs a privileged permission; macOS stays `insufficient` | [M38] |
| intune.md 4 | `windowsProtectionState` relationship read with Managed Devices permission | v1.0 documents the GET under `detectedApps`; beta also accepts Configuration.Read.All | [M4][M5] |
| intune.md 8 "Hidden is not retired" | Cleanup rules only | AVD multi session orphan records are deleted after 60 days inactivity outside cleanup rules | [M54] |
| intune.md S10, S22 URLs | Intune Learn paths under `intune-service` | Intune docs moved: compliance settings now under `/intune/device-security/compliance/`, export guide under `/intune/device-management/reports/` (old paths still resolve, U) | [M14][M23] |

## 8. Proposed new dictionary keys

| Key | Holds | Check that uses it |
|---|---|---|
| `compliance_setting_states` | per policy and setting: setting name, state, policy id, reported at | `devices.firewall_enabled` (Windows), `devices.screen_lock`, `devices.disk_encrypted` cross read |
| `directory_trust_type` | Entra `trustType`, `isManaged`, `isCompliant` | `devices.staff_have_managed_device` (registered only devices of staff) |
| `autopilot_state` | registered, `enrollmentState`, group tag | NEW `devices.company_devices_enrolled`: every Autopilot registered device is enrolled within N days |
| `app_protection` | per app: policy applied, flagged reasons, last sync | NEW `devices.byod_apps_protected`: personal phones reaching company data run a protected app |
| `virtual_host_type` | cloud_pc, avd_single, avd_multi | turns encryption and lock checks into `not_applicable` with reason |
| `managed_by` | raw management agent (intune, configmgr, jamf, google, mde) | `devices.enrolled` without double counting |

## 9. Sources

All read 2026-11-26.

- [M1] managedDevice v1.0: https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-manageddevice?view=graph-rest-1.0
- [M2] managedDevice beta: https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-manageddevice?view=graph-rest-beta
- [M3] windowsProtectionState v1.0: https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-windowsprotectionstate?view=graph-rest-1.0
- [M4] Get windowsProtectionState v1.0: https://learn.microsoft.com/en-us/graph/api/intune-devices-windowsprotectionstate-get?view=graph-rest-1.0
- [M5] Get windowsProtectionState beta: https://learn.microsoft.com/en-us/graph/api/intune-devices-windowsprotectionstate-get?view=graph-rest-beta
- [M6] deviceComplianceSettingState: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-devicecompliancesettingstate?view=graph-rest-1.0
- [M7] List deviceComplianceSettingStates (permission): https://learn.microsoft.com/en-us/graph/api/intune-deviceconfig-devicecompliancesettingstate-list?view=graph-rest-1.0
- [M8] deviceCompliancePolicySettingStateSummary: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-devicecompliancepolicysettingstatesummary?view=graph-rest-1.0
- [M9] List setting state summaries (permission): https://learn.microsoft.com/en-us/graph/api/intune-deviceconfig-devicecompliancepolicysettingstatesummary-list?view=graph-rest-1.0
- [M10] deviceComplianceDeviceStatus: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-devicecompliancedevicestatus?view=graph-rest-1.0
- [M11] Create exportJob v1.0 (ReadWrite only): https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementexportjob-create?view=graph-rest-1.0
- [M12] Create exportJob beta (ReadWrite only): https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementexportjob-create?view=graph-rest-beta
- [M13] Reports available for export (FirewallStatus, NoncompliantDevicesAndSettings, MAM, attestation columns): https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/reports-export-graph-available-reports
- [M14] Export Intune reports with Graph (export throttling): https://learn.microsoft.com/en-us/intune/device-management/reports/export-graph-apis
- [M15] deviceManagementReports methods: https://learn.microsoft.com/en-us/graph/api/resources/intune-reporting-devicemanagementreports?view=graph-rest-1.0
- [M16] getNoncompliantDevicesAndSettingsReport: https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementreports-getnoncompliantdevicesandsettingsreport?view=graph-rest-1.0
- [M17] getDevicesWithoutCompliancePolicyReport: https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementreports-getdeviceswithoutcompliancepolicyreport?view=graph-rest-1.0
- [M18] getCachedReport: https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementreports-getcachedreport?view=graph-rest-1.0
- [M19] getHistoricalReport: https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementreports-gethistoricalreport?view=graph-rest-1.0
- [M20] getDeviceNonComplianceReport: https://learn.microsoft.com/en-us/graph/api/intune-reporting-devicemanagementreports-getdevicenoncompliancereport?view=graph-rest-1.0
- [M21] windows10CompliancePolicy v1.0: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-windows10compliancepolicy?view=graph-rest-1.0
- [M22] windows10CompliancePolicy beta (`activeFirewallRequired`): https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-windows10compliancepolicy?view=graph-rest-beta
- [M23] Windows compliance settings: https://learn.microsoft.com/en-us/intune/device-security/compliance/ref-windows-settings
- [M24] macOSCompliancePolicy v1.0: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-macoscompliancepolicy?view=graph-rest-1.0
- [M25] iosCompliancePolicy v1.0: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-ioscompliancepolicy?view=graph-rest-1.0
- [M26] iOS and iPadOS compliance settings: https://learn.microsoft.com/en-us/intune/device-security/compliance/ref-ios-ipados-settings
- [M27] androidDeviceOwnerCompliancePolicy (beta only): https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-androiddeviceownercompliancepolicy?view=graph-rest-beta
- [M28] androidWorkProfileCompliancePolicy v1.0: https://learn.microsoft.com/en-us/graph/api/resources/intune-deviceconfig-androidworkprofilecompliancepolicy?view=graph-rest-1.0
- [M29] Android Enterprise compliance settings: https://learn.microsoft.com/en-us/intune/device-security/compliance/ref-android-enterprise-settings
- [M30] Linux compliance settings: https://learn.microsoft.com/en-us/intune/device-security/compliance/ref-linux-settings
- [M31] Linux deployment guide: https://learn.microsoft.com/en-us/intune/fundamentals/platform-guide-linux
- [M32] What an organisation can see: https://learn.microsoft.com/en-us/intune/user-help/enrollment/data-visibility
- [M33] Device details (7 day inventory, per platform fields): https://learn.microsoft.com/en-us/intune/device-management/inventory-and-status/device-details
- [M34] Apple User Enrollment overview: https://learn.microsoft.com/en-us/intune/device-enrollment/apple/user-enrollment-methods-ios
- [M35] List BitLocker recoveryKeys: https://learn.microsoft.com/en-us/graph/api/bitlocker-list-recoverykeys?view=graph-rest-1.0
- [M36] bitlockerRecoveryKey (volumeType): https://learn.microsoft.com/en-us/graph/api/resources/bitlockerrecoverykey?view=graph-rest-1.0
- [M37] Encryption report: https://learn.microsoft.com/en-us/intune/device-configuration/endpoint-security/monitor-encryption
- [M38] getFileVaultKey (beta): https://learn.microsoft.com/en-us/graph/api/intune-devices-manageddevice-getfilevaultkey?view=graph-rest-beta
- [M39] windowsAutopilotDeviceIdentity: https://learn.microsoft.com/en-us/graph/api/resources/intune-enrollment-windowsautopilotdeviceidentity?view=graph-rest-1.0
- [M40] List windowsAutopilotDeviceIdentities (permission): https://learn.microsoft.com/en-us/graph/api/intune-enrollment-windowsautopilotdeviceidentity-list?view=graph-rest-1.0
- [M41] Entra device resource: https://learn.microsoft.com/en-us/graph/api/resources/device?view=graph-rest-1.0
- [M42] List devices (permission): https://learn.microsoft.com/en-us/graph/api/device-list?view=graph-rest-1.0
- [M43] Manage stale devices (activity timestamp): https://learn.microsoft.com/en-us/entra/identity/devices/manage-stale-devices
- [M44] deviceDetail (sign ins): https://learn.microsoft.com/en-us/graph/api/resources/devicedetail?view=graph-rest-1.0
- [M45] managedAppRegistration: https://learn.microsoft.com/en-us/graph/api/resources/intune-mam-managedappregistration?view=graph-rest-1.0
- [M46] List managedAppRegistrations (permission): https://learn.microsoft.com/en-us/graph/api/intune-mam-managedappregistration-list?view=graph-rest-1.0
- [M47] managedAppFlaggedReason: https://learn.microsoft.com/en-us/graph/api/resources/intune-mam-managedappflaggedreason?view=graph-rest-1.0
- [M48] List managedAppStatuses (permission): https://learn.microsoft.com/en-us/graph/api/intune-mam-managedappstatus-list?view=graph-rest-1.0
- [M49] remoteActionAudit (beta): https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-remoteactionaudit?view=graph-rest-beta
- [M50] List remoteActionAudits (beta, permission): https://learn.microsoft.com/en-us/graph/api/intune-devices-remoteactionaudit-list?view=graph-rest-beta
- [M51] Delta query supported resources: https://learn.microsoft.com/en-us/graph/delta-query-overview
- [M52] Policy refresh intervals: https://learn.microsoft.com/en-us/intune/device-configuration/troubleshoot-device-profiles
- [M53] Windows 365 known issues (Cloud PC compliance): https://learn.microsoft.com/en-us/windows-365/enterprise/known-issues-enterprise
- [M54] AVD multi session with Intune: https://learn.microsoft.com/en-us/intune/solutions/azure-virtual-desktop-multi-session
- [M55] AVD single session with Intune: https://learn.microsoft.com/en-us/intune/solutions/azure-virtual-desktop
- [M56] List detectedApps (permission): https://learn.microsoft.com/en-us/graph/api/intune-devices-detectedapp-list?view=graph-rest-1.0
- [M57] Defender, get installed software: https://learn.microsoft.com/en-us/defender-endpoint/api/get-installed-software
- [M58] Defender, export software inventory per device: https://learn.microsoft.com/en-us/defender-endpoint/api/get-assessment-software-inventory
- [M59] Co-management workloads: https://learn.microsoft.com/en-us/intune/configmgr/comanage/workloads
- [M60] Data Warehouse data model (daily snapshot): https://learn.microsoft.com/en-us/intune/developer/data-warehouse/ref-data-model
- [M61] Data Warehouse devices (`devicePropertyHistories` 60 days): https://learn.microsoft.com/en-us/intune/developer/data-warehouse/ref-devices
- [M62] Data Warehouse app only auth: https://learn.microsoft.com/en-us/intune/developer/data-warehouse/configure-app-only-auth
- [M63] Graph throttling limits (Intune): https://learn.microsoft.com/en-us/graph/throttling-limits
- [M64] Autopilot device preparation: https://learn.microsoft.com/en-us/autopilot/device-preparation/overview
- [M65] deviceEnrollmentType enum: https://learn.microsoft.com/en-us/graph/api/resources/intune-shared-deviceenrollmenttype?view=graph-rest-beta
- [M66] Wipe action: https://learn.microsoft.com/en-us/intune/device-management/actions/wipe
- [M67] Retire action: https://learn.microsoft.com/en-us/intune/device-management/actions/retire

Not found in this session (404): a `deviceCompliancePolicyState` page in v1.0 or beta and the
`intune-devices-deviceenrollmenttype` enum page; neither managedDevice page lists a per device policy state
relationship [M1][M2], so Verity does not build on `managedDevices/{id}/deviceCompliancePolicyStates`.

AVD single session [M55] and co-management workloads [M59] were read for context: single session VMs are treated
like physical Windows Enterprise desktops and do not support wipe or remote lock [M55]; the compliance workload can
stay with Configuration Manager [M59].
