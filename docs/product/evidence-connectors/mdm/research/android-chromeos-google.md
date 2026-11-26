# Android, ChromeOS and Google device sources (round 2 research)

Brief: [BRIEF.md](BRIEF.md). Round 1: [mdm-and-endpoint-strategy.md](../../mdm-and-endpoint-strategy.md),
[google-endpoint-management.md](../../connectors/google-endpoint-management.md),
[google-workspace.md](../../connectors/google-workspace.md), [devices-hr.md](../../verification/devices-hr.md).
This file extends round 1. Facts round 1 already verified are cited back to it (round 1 S numbers) and not
re-argued. Source ids here are numbered [1] to [73] (section 8).

## 1. Scope

Read on 2026-11-26.

| Area | Product, API, version | Role in Verity |
|---|---|---|
| Android Enterprise modes | Android Management API (AMAPI) v1 `enterprises.devices`, `enterprises.policies` [1][7]; Android 10, 11, 12 enterprise changes [16][17][18]; device admin deprecation [19]; feature list [21] | vendor neutral vocabulary for what any Android EMM can see and do. Not a source Verity can call (gotcha G1) |
| Android platform security | AOSP encryption pages [22][23][24]; Play Integrity verdicts [25]; Android Security Bulletins [26][27]; Android Enterprise Recommended [28]; Pixel and Samsung support windows [29][30] | rules for judging encryption, integrity and "current" |
| Purchased Android populations | zero touch customer API v1 (`androiddeviceprovisioning`) [31][32][33][34]; Samsung Knox Mobile Enrollment (KME) API [35][36][37][38] | a second population: devices the company bought, enrolled or not |
| ChromeOS | Admin SDK Directory API `chromeosdevices` [39][40]; Chrome Policy API v1 [43][44][45][46]; Chrome Management API v1 reports, telemetry, browsers [47] to [53]; Reports API `chrome` events [57] | inventory, OS support, lock policy, history |
| Managed browser | Chrome Enterprise Core through `customers.chromeBrowsers` [52][53][54] | browser versions on any OS |
| Google endpoint management (GEM) | Cloud Identity Devices API v1 [59][60][61]; Directory API `mobiledevices` [69]; Reports API `mobile` events [58]; GEM help [64] to [68]; Endpoint Verification [62][63] | Android and iOS under basic or advanced management, desktops under Endpoint Verification |

Go client libraries (confirmed on pkg.go.dev [72]):

| API | Import path | Note |
|---|---|---|
| Android Management API | `google.golang.org/api/androidmanagement/v1` | reference only; Verity does not call it (G1) |
| Zero touch customer API | `google.golang.org/api/androiddeviceprovisioning/v1` | the package defines no scope constants: pass the scope string yourself |
| Chrome Policy API | `google.golang.org/api/chromepolicy/v1` | defines `ChromeManagementPolicyReadonlyScope` |
| Chrome Management API | `google.golang.org/api/chromemanagement/v1` | scope constants not confirmed (page truncated) |
| Directory API, Cloud Identity, auth | `google.golang.org/api/admin/directory/v1`, `google.golang.org/api/cloudidentity/v1`, `golang.org/x/oauth2/google` | round 1 S11 |
| Knox KME | none found | plain REST (unverified: no official Go SDK searched for) |

## 2. Visibility by platform and channel

Cells: yes, partial (why), no, n/a. "Policy" means Verity can read what was configured, not what the device
reports. AMAPI cells describe the Android framework limits any EMM meets; a given EMM may expose less.

### 2.1 Android Enterprise modes (AMAPI as the reference)

How the modes show in AMAPI: fully managed (FM) and dedicated (DD) are `managementMode` DEVICE_OWNER with
`ownership` COMPANY_OWNED; work profile on a company owned device (WPCO, Android 8 and later in AMAPI,
recognised as company owned from Android 11 when added in setup) is PROFILE_OWNER plus COMPANY_OWNED; work
profile on a personal device (WPPO) is PROFILE_OWNER plus PERSONALLY_OWNED [2][3][10][17]. Dedicated is a
fully managed device enrolled with a userless token (`PERSONAL_USAGE_DISALLOWED_USERLESS`) [10]; AMAPI has no
separate mode value for it. Device admin (DA) is not an AMAPI mode at all; Cloud Identity reports it as
`ownershipPrivilege` DEVICE_ADMINISTRATOR [59]. GEM basic is Google basic mobile management on Android and
iOS, with no work profile and no management app required [64].

| Key | FM | DD | WPCO | WPPO | DA (legacy) | GEM basic |
|---|---|---|---|---|---|---|
| `provider_device_id` | yes | yes | yes | yes | EMM specific | yes (Cloud Identity `name`) |
| `serial_number` | yes | yes | yes (the Android 12 identifier removal is optional for company owned [16]) | no on Android 12 and later: `hardwareInfo.serialNumber` then holds the enterprise specific ID [1][16]; yes before 12, since profile owners keep access [18] | likely no on Android 10 and later (only device and profile owners are exempt from the identifier restriction [18]; inference) | partial: on Android 12 work profiles GEM reports the enrolment specific ID instead [65]; otherwise unverified |
| `hardware_ids` (IMEI, MEID) | yes, `networkInfo` with network reporting on [1] | yes | yes (inference from [16]) | no on 12 and later [16]; never collected (personal) | likely no (inference [18]) | never collected (personal by default) |
| `hostname`, `device_name` | no field | no | no | no | no | no |
| `manufacturer`, `model` | yes | yes | yes | yes | EMM specific | yes |
| `platform`, `os_version`, `os_build` | yes, needs software reporting on [1] | yes | yes | yes | EMM specific | yes; OS sync can take days [68] |
| `device_class` | partial: phone or tablet not reported | partial: only from the enrolment token or policy [10] | partial | partial | no | no |
| `ownership` | yes `ownership` | yes | yes | yes | EMM specific | partial: GEM label from the company owned inventory, not from the mode [64][65] |
| `enrolment_channel` | partial: `enrollmentTokenName` only; zero touch or KME needs a match to the purchase list (section 3) | partial | partial | yes (work_profile_personal) | yes (legacy, see 7) | registered_only |
| `supervised` | n/a (Apple) | n/a | n/a | n/a | n/a | n/a |
| `management_state` | yes `appliedState` (ACTIVE, DISABLED, DELETED, PROVISIONING, LOST, and more) [1] | yes | yes | yes, but a profile the user removed stays unknown to the server [1] | EMM specific | yes Cloud Identity `managementState` |
| `enrolled_at` | yes `enrollmentTime` | yes | yes | yes | EMM specific | partial: `deviceUsers.firstSyncTime` |
| `last_check_in_at` | yes `lastStatusReportTime`, `lastPolicySyncTime` | yes | yes | yes | EMM specific | yes `lastSyncTime` |
| `provider_compliance_state` | yes `policyCompliant`, `nonComplianceDetails` | yes | yes | yes | EMM specific | partial: audit event `DEVICE_COMPLIANCE_CHANGED_EVENT` [58] |
| `assigned_user_email` | partial: AMAPI `user` holds only a non personal account id [9]; the EMM maps the person | no (userless) | partial | partial | EMM specific | yes `deviceUsers.userEmail` |
| `disk_encryption` | yes `deviceSettings.encryptionStatus` (device settings reporting on) [1] | yes | yes | yes (device level; not in the list of fields withheld from WPPO [7]) | EMM specific | yes; sync can take days [68] |
| `encryption_method` | platform data protection (file based on devices launched with 10 and later [23]) | same | same | same | same | same |
| `recovery_key_escrowed` | n/a (no user recovery key on Android; Verity's classification) | n/a | n/a | n/a | n/a | n/a |
| `passcode_present` | yes `deviceSettings.isDeviceSecure` [1] | yes | yes | yes | EMM specific | partial `deviceUsers.passwordState` [61] |
| `passcode_compliant` | yes via `nonComplianceDetails` on `passwordPolicies` | yes | yes (device and profile scopes [8]) | yes; complexity buckets on Android 12 and later [8][16] | no: password policies stop working for DA apps targeting API 29 [19] | partial: basic enforces a basic passcode [67] |
| `idle_lock_seconds`, `idle_lock_origin` | policy only: `maximumTimeToLock` [7] | policy only | policy only; enforced screen timeout needs Android 15 [7] | policy only; whether it applies on WPPO unverified | no | no |
| `firewall_on` | n/a (no Android firewall signal) | n/a | n/a | n/a | n/a | n/a |
| `os_integrity` | yes `securityPosture` (Play Integrity) [1] | yes | yes | yes | no | yes `compromisedState` (rooted only) [59] |
| `activation_lock_or_frp` | policy only: factory reset protection is settable on FM [21]; no device field | policy only | no: FRP not available on work profiles [21] | no [21] | no | no |
| `removable_storage_blocked` | policy only: `usbDataAccess`, company owned only [7] | policy only | policy only | no [7] | no | no |
| `local_admin_present` | n/a | n/a | n/a | n/a | n/a | n/a |
| `av_present`, `av_realtime_on` | partial: `deviceSettings.verifyAppsEnabled` (Play Protect) [1] | partial | partial | partial | no | partial `androidSpecificAttributes.verifyAppsEnabled` [59] |
| `av_signatures_current` | no | no | no | no | no | no |
| `edr_present` | partial: app report shows the agent package | partial | partial (work profile apps) | partial (work profile apps only; inference) | no | no |
| `os_update_policy_assigned` | policy: `systemUpdate` type [7] | policy | policy | unverified | no | no |
| `os_update_available` | yes `softwareInfo.systemUpdateInfo.updateStatus` (API level 26 and later) [1] | yes | yes | yes | no | no |
| `security_patch_level` | yes `softwareInfo.securityPatchLevel` [1] | yes | yes | yes | EMM specific | yes `securityPatchTime` [59] |
| `os_supported` | computed by Verity (section 2.3) | same | same | same | same | same |
| `browser_versions` | partial: Chrome package in app reports | partial | partial | partial (work profile Chrome only) | no | no |
| `installed_apps` | yes `applicationReports` (app reporting on) [1] | yes | work profile apps only (unverified) | never collected | no | never collected (see G16) |
| `managed_apps` | yes | yes | yes | yes (work profile) | no | partial (Android app management [67]) |
| `device.action` | wipe is a factory reset; lock, lost mode [6] | same | wipe or work profile only [21]; lost mode yes [6] | wipe removes only the work profile [6]; no lost mode [6] | wipe still possible [19] | account wipe only [68]; full wipe needs advanced [67] |

### 2.2 ChromeOS, Endpoint Verification desktops, managed browsers

| Key | ChromeOS enrolled (`chromeosdevices`) | Endpoint Verification desktop (round 1) | Chrome Enterprise Core browser |
|---|---|---|---|
| `provider_device_id` | yes `deviceId` [39] | yes | yes `browserPermanentId` or `virtualDeviceId` [52] |
| `serial_number` | yes `serialNumber` [39] | yes [62] | yes `serialNumber` [52] |
| `hardware_ids` | partial: `meid` of a 3G card only [39] | no | no |
| `hostname`, `device_name` | no hostname; admin annotations `annotatedAssetId`, `notes` [39] | yes `hostname` (not on ChromeOS) [62] | yes `machineName` [52] |
| `manufacturer`, `model` | partial: `model` only [39] | yes | no |
| `platform`, `os_version`, `os_build` | yes `osVersion`, `platformVersion`, `firmwareVersion`, `chromeOsType` (ChromeOS or Flex) [39] | yes | yes `osPlatform`, `osVersion` [52] |
| `device_class` | partial: kiosk licence type (`deviceLicenseType` KIOSK_UPGRADE) [39] | no | no |
| `ownership` | company (enterprise enrolment; Verity's classification) | per `ownerType` | unknown |
| `enrolment_channel` | partial: `status` PRE_PROVISIONED marks zero touch registration [39] | registered_only | inventory_only (a browser, not a device) |
| `management_state` | yes `status` (ACTIVE, DELINQUENT, DISABLED, DEPROVISIONED, INACTIVE, and more) [39] | round 1 | no |
| `enrolled_at` | yes `firstEnrollmentTime`, `lastEnrollmentTime` [39] | round 1 | no |
| `last_check_in_at` | yes `lastSync` [39] | yes; reports every 4 hours [63] | yes `lastActivityTime`, `lastPolicyFetchTime` [52] |
| `provider_compliance_state` | partial `osVersionCompliance` (meaning not documented) [39] | no | no |
| `assigned_user_email` | partial: `annotatedUser` (admin text) or `recentUsers[0].email` (managed users only) [39] | yes | partial `annotatedUser` [52] |
| `disk_encryption`, `encryption_method` | on by design (Google states user data is encrypted with tamper resistant hardware [41]); not reported per device in `chromeosdevices` | yes `encryption_status`, also on ChromeOS [62] | n/a |
| `passcode_present`, `passcode_compliant` | policy only: Lock screen, Quick unlock, Lock screen PIN settings [42] | partial `is_secured_with_screenlock` (where it appears in the API: unverified) [62] | n/a |
| `idle_lock_seconds`, `idle_lock_origin` | policy only: AC and battery "screen lock delay in seconds" under Idle settings [42], read through the Chrome Policy API (schema name unverified) | no | n/a |
| `firewall_on` | partial via Endpoint Verification on ChromeOS [62] | yes | n/a |
| `os_integrity` | yes `bootMode` Verified or Dev [39]; history in `DEVICE_BOOT_STATE_CHANGE` [57] | partial (secure boot on Windows) | n/a |
| `activation_lock_or_frp` | no (forced re-enrolment not researched) | n/a | n/a |
| `removable_storage_blocked` | policy only (schema not researched: unverified) | no | n/a |
| `av_*`, `edr_present`, `local_admin_present` | n/a | Windows only with helper (round 1) | n/a |
| `os_update_policy_assigned` | policy (auto update schemas not researched: unverified) | no | no |
| `os_update_available` | partial `osUpdateStatus.state`, `targetOsVersion` [39] | no | no |
| `security_patch_level` | n/a | n/a | n/a |
| `os_supported` | yes `autoUpdateThrough`, `extendedSupportEligible`, `extendedSupportEnabled` [39] | no | no |
| `browser_versions` | yes, `countChromeVersions` with system SYSTEM_CROS [48] | yes `chromeBrowserInfo.browserVersion` [59] | yes `browsers[].browserVersion` [52] |
| `installed_apps`, `managed_apps` | partial: aggregate app counts and app to device lookups (`countInstalledApps`, `findInstalledAppDevices`) [47] | no | partial: extensions per browser (field list not confirmed) |
| `device.action` | not researched (unverified) | none | none |

### 2.3 Judging "current" on Android and ChromeOS

| Signal | Rule for Verity | Source |
|---|---|---|
| Bulletin cadence | Android Security Bulletins come out monthly, on the first Monday | [26] |
| Patch level meaning | each bulletin has two levels; the second (the 5th of the month) covers every fix of that bulletin and earlier ones. Compare the complete level, not the first | [27] |
| Supported Android versions | the November 2026 bulletin lists AOSP 14, 15, 16, 16 QPR2 and 17 as updated versions. Treating 13 and earlier as unsupported is an inference from that list | [27] |
| Integrity and patch age | on Android 13 and later, Play Integrity's strong label needs patches from the last year on every partition; on 12 and earlier it does not | [25] |
| Device side flag | AMAPI `systemUpdateInfo.updateStatus` SECURITY_UPDATE_AVAILABLE says an update is waiting | [1] |
| Vendor support end | Pixel 8 and later get 7 years, Pixel 6 and 7 get 5 years; Samsung extended security support by up to 7 years from January 2024 and lists monthly or quarterly models; Android Enterprise Recommended devices must publish an end date and update frequency. No API gives these dates: Verity keeps a reviewed table | [28][29][30] |
| ChromeOS | 10 years of updates from the platform release; `autoUpdateThrough` per device; some models must opt in to extended updates | [39][56] |

Proposed predicate for `devices.os_current` on Android: complete patch level no older than
`android_patch_max_age_days` (setting, default 90, owner decision), Android version in the latest bulletin's
list, and the model inside its vendor support window when the table knows it (otherwise `insufficient` for
that clause only).

## 3. Field map

Read permissions use the Google admin privilege names. "DWD" means the round 1 service account with domain
wide delegation (round 1 S12). "Role on SA" means an admin role assigned directly to Verity's service account.

| Key | Source and call | Field | Read permission | Tier or licence | Caveats | Status |
|---|---|---|---|---|---|---|
| reference only | AMAPI `GET /v1/{enterprise}/devices` [4] | Device resource [1] | scope `androidmanagement` only, no read only scope [4] | EMM projects only [11] | Verity cannot call it (G1); fields below with AMAPI are what the customer's EMM can pass on | verified [1][4][11] |
| `provider_device_id` | AMAPI | `name` | EMM | EMM | | verified [1] |
| `serial_number` | AMAPI | `hardwareInfo.serialNumber` | EMM | EMM | WPPO Android 12 and later: equals `enterpriseSpecificId` | verified [1] |
| `hardware_ids` | AMAPI | `networkInfo.imei`, `networkInfo.meid`, `hardwareInfo.euiccChipInfo[].eid` | EMM | EMM | needs network reporting; EID on company owned Android 13 and later; IMEI absent on WPPO 12 and later | verified [1][16] |
| `manufacturer`, `model` | AMAPI | `hardwareInfo.manufacturer`, `brand`, `model` | EMM | EMM | | verified [1] |
| `os_version`, `os_build` | AMAPI | `softwareInfo.androidVersion`, `androidBuildNumber`, `apiLevel` | EMM | EMM | `softwareInfo` needs `softwareInfoEnabled`; `apiLevel` is top level | verified [1] |
| `ownership` | AMAPI | `ownership` | EMM | EMM | COMPANY_OWNED, PERSONALLY_OWNED | verified [3] |
| `enrolment_channel` | AMAPI | `managementMode` with `ownership`; `enrollmentTokenName`, `enrollmentTokenData` | EMM | EMM | DD and FM share DEVICE_OWNER | verified [1][2][10] |
| `management_state` | AMAPI | `appliedState`, `state` | EMM | EMM | LOST only on company owned | verified [1] |
| `enrolled_at`, `last_check_in_at` | AMAPI | `enrollmentTime`, `lastStatusReportTime`, `lastPolicySyncTime` | EMM | EMM | report cadence not documented | verified fields [1]; cadence unverified |
| `provider_compliance_state`, `compliance_policies` | AMAPI | `policyCompliant`, `nonComplianceDetails[]` (`settingName`, `nonComplianceReason`, `specificNonComplianceReason`), `appliedPolicyName`, `appliedPolicyVersion` | EMM | EMM | | verified [1] |
| `assigned_user_provider_id` | AMAPI | `user.accountIdentifier`, `userName` | EMM | EMM | no email; Google forbids personal data in it | verified [9] |
| `disk_encryption` | AMAPI | `deviceSettings.encryptionStatus` (UNSUPPORTED, INACTIVE, ACTIVATING, ACTIVE, ACTIVE_DEFAULT_KEY, ACTIVE_PER_USER), `isEncrypted` | EMM | EMM | needs `deviceSettingsEnabled`; prefer the enum (G5) | verified [1] |
| `passcode_present` | AMAPI | `deviceSettings.isDeviceSecure` | EMM | EMM | | verified [1] |
| `passcode_compliant` | AMAPI | `nonComplianceDetails` for `passwordPolicies`; `appliedPasswordPolicies[]` | EMM | EMM | applied list carries no compliance data | verified [1][8] |
| `idle_lock_seconds` (policy) | AMAPI policy | `maximumTimeToLock` (milliseconds, 0 means no limit), `screenTimeoutSettings` | EMM | EMM | never device reported; enforced timeout on FM Android 9 and later, WPCO Android 15 and later | verified [7] |
| `os_integrity` | AMAPI | `securityPosture.devicePosture` (SECURE, AT_RISK, POTENTIALLY_COMPROMISED), `postureDetails[].securityRisk` (UNKNOWN_OS, COMPROMISED_OS, HARDWARE_BACKED_EVALUATION_FAILED) | EMM | EMM | built on Play Integrity | verified [1] |
| `removable_storage_blocked` (policy) | AMAPI policy | `deviceConnectivityManagement.usbDataAccess` | EMM | EMM | company owned only | verified [7] |
| `av_present` | AMAPI | `deviceSettings.verifyAppsEnabled` | EMM | EMM | Play Protect scanning, not an antivirus product | verified [1] |
| `os_update_policy_assigned` | AMAPI policy | `systemUpdate.type` (AUTOMATIC, WINDOWED, POSTPONE), freeze periods | EMM | EMM | freeze periods also hold security patches | verified [7] |
| `os_update_available` | AMAPI | `softwareInfo.systemUpdateInfo.updateStatus` | EMM | EMM | UNKNOWN below API 26 | verified [1] |
| `security_patch_level` | AMAPI | `softwareInfo.securityPatchLevel` (date string) | EMM | EMM | | verified [1] |
| `installed_apps`, `managed_apps` | AMAPI | `applicationReports[]` (`packageName`, `versionName`, `applicationSource`, `state`) | EMM | EMM | needs `applicationReportsEnabled`; events kept 30 hours | verified [1] |
| `device.action` | AMAPI | operations from `issueCommand` (WIPE, LOCK, START_LOST_MODE) | EMM | EMM | retention of operations not documented | verified commands [6]; history unverified [15] |
| `serial_number`, `ownership`, `management_state` | Cloud Identity `GET /v1/devices` (round 1) | `serialNumber`, `ownerType`, `managementState` | `cloud-identity.devices.readonly`, DWD | round 1 S3, S8 | `ownerType` follows the company owned inventory (G3) | verified [59][60] |
| `hardware_ids` | Cloud Identity | `imei`, `meid` | same | same | collect only when `ownerType` COMPANY | verified [59] |
| `os_version`, `os_build` | Cloud Identity | `osVersion`, `releaseVersion`, `buildNumber`, `kernelVersion`, `bootloaderVersion` | same | same | | verified [59] |
| `enrolment_channel` | Cloud Identity | `androidSpecificAttributes.ownershipPrivilege` (DEVICE_ADMINISTRATOR, PROFILE_OWNER, DEVICE_OWNER), `supportsWorkProfile`, `ownerProfileAccount` | same | same | the only Google field that reveals legacy device admin | verified [59] |
| `os_integrity` | Cloud Identity | `compromisedState`, `androidSpecificAttributes.verifiedBoot`, `ctsProfileMatch`, `hasPotentiallyHarmfulApps`, `enabledDeveloperOptions`, `enabledUsbDebugging`, `enabledUnknownSources` | same | same | COMPROMISED today means rooted only | verified [59] |
| `disk_encryption` | Cloud Identity | `encryptionState` | same | same | round 1 | verified [59] |
| `security_patch_level` | Cloud Identity | `securityPatchTime` | same | same | a timestamp, not a date string | verified [59] |
| `browser_versions` | Cloud Identity | `endpointVerificationSpecificAttributes.browserAttributes[].chromeBrowserInfo.browserVersion`, `browserManagementState` | same | Endpoint Verification editions (round 1 S3) | desktops with the extension only | verified [59] |
| `assigned_user_email`, `passcode_present` | Cloud Identity `GET /v1/devices/{d}/deviceUsers` | `userEmail`, `passwordState`, `managementState`, `firstSyncTime` | same | same | account `compromisedState` is about the account, not the device | verified [61] |
| history (OS, patch, integrity, compliance, ownership, actions) | Reports API `activities.list`, application `mobile` (round 1 S15) | `DEVICE_SYNC_EVENT` (`OS_VERSION`, `SECURITY_PATCH_LEVEL`, `BASIC_INTEGRITY`, `CTS_PROFILE_MATCH`), `OS_UPDATED_EVENT`, `DEVICE_COMPLIANCE_CHANGED_EVENT`, `DEVICE_OWNERSHIP_CHANGE_EVENT`, `DEVICE_COMPROMISED_EVENT`, `DEVICE_ACTION_EVENT` | `admin.reports.audit.readonly` | device audits need Frontline Standard or Plus, Enterprise, Business Plus, Education Standard or Plus, Cloud Identity Premium [67] | 180 days (round 1 S15) | verified [58][67] |
| `provider_device_id`, `serial_number` | Directory `chromeosdevices.list`, `projection=FULL` [40] | `deviceId`, `serialNumber` | `admin.directory.device.chromeos.readonly`; privilege Manage ChromeOS Devices (read only) | ChromeOS device licence (`deviceLicenseType`) | BASIC projection drops fields | verified [39][40][55] |
| `management_state`, `enrolled_at`, `last_check_in_at` | same | `status`, `firstEnrollmentTime`, `lastEnrollmentTime`, `lastSync`, `deprovisionReason`, `lastDeprovisionTimestamp` | same | same | | verified [39] |
| `os_version`, `os_build`, `platform` | same | `osVersion`, `platformVersion`, `firmwareVersion`, `chromeOsType` | same | same | | verified [39] |
| `os_integrity` | same | `bootMode` (Verified, Dev) | same | same | | verified [39] |
| `os_supported` | same | `autoUpdateThrough`, `extendedSupportEligible`, `extendedSupportStart`, `extendedSupportEnabled` | same | same | `autoUpdateExpiration` is deprecated | verified [39] |
| `os_update_available` | same | `osUpdateStatus.state`, `targetOsVersion`, `updateTime`, `updateCheckTime` | same | same | | verified [39] |
| `assigned_user_email` | same | `annotatedUser`, `recentUsers[]` (`type`, `email`) | same | same | email only for managed users | verified [39] |
| `os_supported` (fleet) | Chrome Management `reports:countChromeDevicesReachingAutoExpirationDate` | `deviceAueCountReports[]` (`model`, `count`, `aueMonth`, `aueYear`, `expired`) | `chrome.management.reports.readonly`; privilege unverified | Chrome licence | aggregate by model | verified [49] |
| `browser_versions` (fleet) | Chrome Management `reports:countChromeVersions` | `browserVersions[]` (`version`, `count`, `channel`, `system`, `deviceOsVersion`) | `chrome.management.reports.readonly`; likely View Chrome Versions Report (unverified mapping) | Chrome Enterprise Core or ChromeOS | aggregate; no device id | verified fields [48]; privilege unverified [55] |
| `os_update_available` (telemetry) | Chrome Management `customers.telemetry.devices` | `osUpdateStatus` | `chrome.management.telemetry.readonly`; Manage ChromeOS Devices (read only) | ChromeOS | needs `ReportDeviceOsUpdateStatus` policy; uploads every 3 hours by default | verified [50][51] |
| `browser_versions`, `serial_number`, `hostname` | Chrome Management `GET /v1/customers/{c}/chromeBrowsers` | `browsers[].browserVersion`, `channel`, `serialNumber`, `machineName`, `osPlatform`, `osVersion`, `lastActivityTime` | `chrome.management.browsers.readonly`; privilege Managed Browsers is read and write (G18) | Chrome Enterprise Core, no cost [54] | page size 50 | verified [52][53][54] |
| `idle_lock_seconds`, `passcode_*` (ChromeOS policy) | Chrome Policy `POST /v1/customers/my_customer/policies:resolve` with `policySchemaFilter` `chrome.users.*` and `chrome.devices.*` | resolved `value`, `sourceKey` per org unit | `chrome.management.policy.readonly`; privileges Manage User Settings and Manage ChromeOS Device Settings (both read and write) | ChromeOS | exact schema names for idle and lock: unverified, discover them with `policySchemas` | verified API [43][44][45]; schema names unverified |
| purchase population | zero touch `GET /v1/customers/{id}/devices` | `deviceIdentifier` (`serialNumber`, `imei`, `imei2`, `meid`, `manufacturer`, `model`, `deviceType`), `configuration`, `claims[]` | scope `androidworkzerotouchemm` (whole API, no read only) | zero touch customer account | `pageSize` 1 to 100, listed as required | verified [31][32][33] |
| purchase population | KME `GET /kcs/v1/kme/devices/list` | response fields unverified; console shows IMEI or MEID, serial and statuses Pending, Unassigned, Profile assigned, Provisioned, Failed to provision | Knox OAuth scope `kme.devices:view` (read only) | Knox Mobile Enrollment (free tier not checked: unverified) | regional base URL | verified scope and path [36]; fields unverified; statuses verified [38] |

How the fields reach checks (round 1 keys, section 5 of the strategy): `serial_number`, `hardware_ids`
and `enterprise_specific_id` feed matching for every check; `management_state`, `last_check_in_at` feed
`devices.enrolled`; `disk_encryption` feeds `devices.disk_encrypted` (EP-02.B); `passcode_*` and
`idle_lock_*` feed `devices.screen_lock` (EP-06.B, C); `security_patch_level`, `os_supported`,
`os_update_available` feed `devices.os_current` (EP-04.C); `device.action` feeds `devices.wipes_confirmed`
and `devices.leaver_devices_recovered` (EP-05); `assigned_user_email` feeds
`devices.assigned_to_active_staff` (EP-03.C); the purchase population feeds the new check in 9.

## 4. Auth and permissions

| Source | How the customer makes a read only credential | What it can see | Least privilege notes |
|---|---|---|---|
| Google Workspace device data (GEM, Endpoint Verification) | round 1: add scopes to Verity's DWD entry; subject is one named admin | every device in the account | Google's privilege list names one Mobile Device Management privilege with full control and no view variant [70]: the subject holds a manage privilege and only the read only scopes keep Verity read only. Correction C3 |
| ChromeOS inventory | DWD scope `admin.directory.device.chromeos.readonly`, subject with a custom role holding Manage ChromeOS Devices (read only) [55] | all ChromeOS devices, every org unit the role covers | a true read only privilege exists here |
| Chrome Management telemetry and reports | a role assigned directly to Verity's service account is supported for telemetry, no DWD needed [51]; scopes `chrome.management.telemetry.readonly`, `chrome.management.reports.readonly` | telemetry per device; reports as counts | Telemetry needs Manage ChromeOS Devices (read only) plus per field Telemetry API rights [50][51]; reports privilege not confirmed |
| Chrome Policy API | role on SA or DWD [45]; scope `chrome.management.policy.readonly`, which Google says permits no changes [45] | resolved user and device policies per org unit | reading `chrome.users.*` needs Manage User Settings and `chrome.devices.*` needs Manage ChromeOS Device Settings, both read and write privileges [44][55] |
| Managed browsers | scope `chrome.management.browsers.readonly` [53] | every enrolled Chrome browser | console privilege Managed Browsers is read and write [55]; which privilege the API checks: unverified |
| Android EMM data | through the EMM's own API (Intune, Workspace ONE and others: their research files) | what the EMM stores from its DPC | AMAPI itself has only the full `androidmanagement` scope [4], is limited to EMMs, Device Trust providers and OEMs [11], and enterprises are listed per EMM Cloud project [12]. Verity is none of these |
| Zero touch | the customer links Verity's service account to its zero touch account through Google's request form, confirmed by email [34]; users must have accepted the zero touch terms or calls fail with 403 [33] | every device claimed to the customer, with its configuration | the one scope covers the whole API, and Owner and Admin have equal API access [33]: no read only path exists. Owner decision D-ACG-3 |
| Samsung KME | the customer registers a client in the Knox portal (the auth page names the Knox Developer Portal [37]; who may do it: unverified), then Verity requests a `client_credentials` token at `https://api.samsungknox.com/ams/v1/oauth2/token` with scope `kme.devices:view`; tokens last up to 60 minutes [37] | devices uploaded by resellers and their KME status | `kme.devices:view` is read only; `kme.devices` would add profile and approval writes [36]. The client secret is a connector credential: envelope encrypted (rule 8) |

## 5. Limits

| Source | Paging | Quota | Freshness | History |
|---|---|---|---|---|
| AMAPI (reference) | `pageSize` default 10, max 100 [4] | 60 queries a minute per action and resource; 1,000 per 100 seconds per project [11] | report cadence not documented (unverified); `STATUS_REPORT` Pub/Sub notifications exist [14] | present state; app events 30 hours, memory events deleted after a while [1] |
| Cloud Identity Devices | default 20, max 100 (round 1) | unverified | GEM basic: OS and encryption sync can take a few days [68]; Endpoint Verification reports every 4 hours and checks posture hourly [63] | present only; history through Reports API `mobile` events, 180 days [58] (round 1 S15) |
| Directory `chromeosdevices` | `maxResults` up to 300 [40] | Directory quota (round 1 W29) | `lastSync` per device | present; `activeTimeRanges` gives usage by date [39]; boot mode changes in Reports `chrome` events [57] |
| Chrome Management reports | `pageSize` max and default 100 for versions [48] | unverified | not stated | point in time counts |
| Chrome Management telemetry | not read | unverified | OS update status at upload, every 3 hours by default; heartbeat every 2 minutes on change [50] | recent samples only (unverified depth) |
| Chrome Policy API | `pageSize` default 100, max 1000 on resolve [43] | 50 a second per project, 10 per user; 2,500 a minute per project, 10,000 per organisation [46] | policy as configured now | none: Verity's daily snapshot is the history |
| `chromeBrowsers` | max and default 50 [53] | unverified | `lastActivityTime` | present |
| Zero touch | 1 to 100 [31] | unverified | changes when resellers claim devices | present claims; no claim dates in the fields read |
| KME | `pageNum` from 0, `pageSize` default 100 [35] | unverified | changes on reseller upload | present |

## 6. Gotchas that would make a check wrong

| # | Gotcha | Effect and rule |
|---|---|---|
| G1 | AMAPI is not reachable by Verity: full scope only, restricted users, enterprises bound to the EMM's project [4][11][12] | never plan an "AMAPI connector"; read Android through the EMM that manages it |
| G2 | On WPPO Android 12 and later, `serialNumber` is the enterprise specific ID, not the hardware serial [1][16] | matching on serial against a purchase list or another MDM fails silently; mark such matches as `enterprise_specific_id`, never as serial |
| G3 | GEM `ownerType` COMPANY means the serial is in the company owned inventory; device owner rights alone do not set it, and an Android 12 work profile device added to the inventory still reads personal and gets blocked [64][65][66] | `ownership` from GEM is a label. Cross check with `ownershipPrivilege` |
| G4 | Reporting sections only appear when the EMM policy turns them on (`softwareInfoEnabled`, `deviceSettingsEnabled`, `networkInfoEnabled`, `applicationReportsEnabled`) [1][7] | a missing section is `insufficient`, never `fail` or `pass` |
| G5 | Google's JSON omits fields left at their default, and in Go a missing bool reads false [71] (whether AMAPI and EMM APIs do this: likely, confirm on fixtures) | an absent `isEncrypted` is unknown. Use `encryptionStatus`, and treat a missing `deviceSettings` object as unknown |
| G6 | `encryptionStatus` ACTIVE_DEFAULT_KEY: storage is encrypted but no user credential protects the key [1] | `disk_encryption` on, but evidence must show `passcode_present`; propose fail when both are not true |
| G7 | `appliedPasswordPolicies` is what was applied, with no compliance data [1] | read compliance from `nonComplianceDetails`, not from the applied list |
| G8 | Android never reports its idle timeout; `maximumTimeToLock` 0 means no limit [7] | `idle_lock_origin` is always `policy`; 0 or unset fails the 15 minute standard |
| G9 | Fully managed and dedicated share DEVICE_OWNER [2][10] | kiosks need the userless token or a policy tag to be excluded from `devices.assigned_to_active_staff` |
| G10 | If a user removes the work profile or resets the device, AMAPI never learns of it [1] | stale `lastStatusReportTime` is the only sign; apply the round 1 freshness rule before trusting ACTIVE |
| G11 | AMAPI `delete` attempts a wipe on company devices and removes the work profile on personal ones [5] | a read only connector must never call delete or patch; Verity holds no such scope anyway |
| G12 | Patch level dates come in a partial (1st) and complete (5th) level per month [27] | compare the complete level, or a device can look a month newer than its coverage |
| G13 | Play Integrity's strong label checks patch age only on Android 13 and later [25] | do not read SECURE posture as "patched" on Android 12 and earlier |
| G14 | Cloud Identity `compromisedState` means rooted Android only [59]; `deviceUsers.compromisedState` is the account [61] | do not use either as an iOS or desktop integrity signal |
| G15 | ChromeOS `annotatedUser` is free text an admin typed [39]; `recentUsers` email shows only managed users | assignment source is `manual` or last sign in, labelled weak |
| G16 | Directory `mobiledevices.applications` lists Android apps that touch Workspace data, also on personal phones [69] | never collect it for personal devices (BRIEF "never collected") |
| G17 | `chromeosdevices` also carries `lastKnownNetwork` IP addresses and downloadable `deviceFiles` and `screenshotFiles` [39] | exclude them in the field mask; they are location and file data |
| G18 | Reading browser inventory and Chrome policy needs privileges Google labels read and write [44][55] | the read only OAuth scope is the only guard; say so in the setup guide |
| G19 | Chrome Policy `resolve` without `sourceKey` means the customer default [43]; an unset idle delay uses the device default [42] | unset is `fail` for EP-06, with the reason "no lock delay set" |
| G20 | `osVersionCompliance` values are listed but not defined [39] | do not treat COMPLIANT as "supported"; use `autoUpdateThrough` and the update policy |
| G21 | GEM does not support work profiles on company owned devices [64] | WPCO devices exist only through another EMM |
| G22 | Legacy device admin can still wipe, but password and keyguard policies stop working for apps targeting API 29 [19], and GEM does not offer it on Android 10 and later [64] | `ownershipPrivilege` DEVICE_ADMINISTRATOR fails `devices.enrolled` with reason "legacy device admin" (proposal) |

## 7. Corrections to round 1

| # | File | Claim | Correction | Source |
|---|---|---|---|---|
| C1 | google-endpoint-management.md 4, Devices row | `serialNumber` listed as the device serial | on Android 12 and later work profiles on personal devices, the reported value is the enrolment specific ID, not the serial | [1][16][65] |
| C2 | google-endpoint-management.md 5.1, `devices.os_current` | yes, via `osVersion`, `securityPatchTime`, `osVersionCompliance` | partial: Android needs the complete patch level, a supported Android version and a vendor window (2.3); `osVersionCompliance` is undefined, so ChromeOS uses `autoUpdateThrough` | [27][39] |
| C3 | google-endpoint-management.md 2.1 | the impersonated admin needs a custom read only role with mobile and device view rights | Google lists Mobile Device Management as one privilege with full device control and no view variant; no read only MDM privilege was found. The read only scopes are the only limit. Cloud Identity privilege names stay unverified | [70] |
| C4 | google-endpoint-management.md 8 | most phones in Workspace are BYOD with basic management | no source given or found: unverified | none |
| C5 | google-endpoint-management.md 2.3 | basic management can wipe the work account but not the whole device | add: for Android devices moved from advanced to basic, only a whole device wipe may be possible | [68] |
| C6 | google-endpoint-management.md 1 and 10 | Android covered as one "work profile" case | GEM does not support work profiles on company owned devices; zero touch devices get device owner rights under GEM but count as personal until added to the company owned inventory | [64][66] |
| C7 | google-endpoint-management.md 4, Endpoint Verification text | "the page says only whether a screen lock is enabled" | the page names the attribute `is_secured_with_screenlock` for macOS, Windows, Linux and ChromeOS. The Devices API resource still has no field for it, so the check result does not change | [59][62] |
| C8 | mdm-and-endpoint-strategy.md 5.5, `devices.screen_lock` on Google | no | partial for ChromeOS (screen lock delay readable as policy through the Chrome Policy API, origin `policy`); still no for Endpoint Verification desktops and for GEM phones | [42][43] |
| C9 | mdm-and-endpoint-strategy.md 5.5, `devices.firewall_enabled` on Google | yes | yes only for Endpoint Verification desktops and ChromeOS; Android has no firewall signal (not applicable, not fail) | [59][62] |
| C10 | google-endpoint-management.md, Go library row | Cloud Identity and Directory only | add `google.golang.org/api/chromepolicy/v1` and `google.golang.org/api/chromemanagement/v1` for ChromeOS policy, telemetry and browsers | [72] |
| C11 | verification/devices-hr.md 162 | Google quotas unverified | Chrome Policy API quotas now verified; Cloud Identity Devices quota still unverified | [46] |

## 8. Sources

1. AMAPI Device resource: https://developers.google.com/android/management/reference/rest/v1/enterprises.devices (fields, enums, identifier rules by Android version, WPPO serial rule)
2. AMAPI ManagementMode: https://developers.google.com/android/management/reference/rest/v1/ManagementMode
3. AMAPI Ownership: https://developers.google.com/android/management/reference/rest/v1/Ownership
4. AMAPI devices.list: https://developers.google.com/android/management/reference/rest/v1/enterprises.devices/list (paging, only scope)
5. AMAPI devices.delete: https://developers.google.com/android/management/reference/rest/v1/enterprises.devices/delete (wipe behaviour)
6. AMAPI issueCommand: https://developers.google.com/android/management/reference/rest/v1/enterprises.devices/issueCommand (commands per mode)
7. AMAPI Policy resource: https://developers.google.com/android/management/reference/rest/v1/enterprises.policies (maximumTimeToLock, screenTimeoutSettings, systemUpdate, usbDataAccess, status reporting)
8. AMAPI PasswordRequirements: https://developers.google.com/android/management/reference/rest/v1/PasswordRequirements
9. AMAPI User: https://developers.google.com/android/management/reference/rest/v1/User
10. AMAPI provisioning by mode: https://developers.google.com/android/management/provision-device
11. AMAPI permissible usage and quotas: https://developers.google.com/android/management/permissible-usage
12. AMAPI enterprises.list: https://developers.google.com/android/management/reference/rest/v1/enterprises/list
13. AMAPI introduction: https://developers.google.com/android/management/introduction
14. AMAPI notifications: https://developers.google.com/android/management/notifications
15. AMAPI operations: https://developers.google.com/android/management/reference/rest/v1/enterprises.devices.operations
16. Android 12 for enterprise: https://developer.android.com/work/versions/android-12 (identifier removal, enrolment specific ID, password complexity)
17. Android 11 for enterprise: https://developer.android.com/work/versions/android-11 (company owned work profile)
18. Android 10 privacy changes: https://developer.android.com/about/versions/10/privacy/changes (non resettable identifiers, device and profile owner exemption)
19. Device admin deprecation: https://developers.google.com/android/work/device-admin-deprecation
20. AOSP device management overview: https://source.android.com/docs/devices/admin
21. Android Enterprise feature list: https://developers.google.com/android/work/requirements (wipe and FRP by solution set)
22. AOSP encryption: https://source.android.com/docs/security/features/encryption
23. AOSP file based encryption: https://source.android.com/docs/security/features/encryption/file-based
24. AOSP full disk encryption: https://source.android.com/docs/security/features/encryption/full-disk (removed in Android 13)
25. Play Integrity verdicts: https://developer.android.com/google/play/integrity/verdicts
26. Android Security Bulletin overview: https://source.android.com/docs/security/bulletin/asb-overview
27. Android Security Bulletin, November 2026: https://source.android.com/docs/security/bulletin/2026/2026-11-01
28. Android Enterprise Recommended requirements: https://www.android.com/enterprise/recommended/requirements/
29. Pixel update support: https://support.google.com/pixelphone/answer/4457705
30. Samsung security update scope: https://security.samsungmobile.com/workScope.smsb
31. Zero touch customer devices.list: https://developers.google.com/zero-touch/reference/customer/rest/v1/customers.devices/list
32. Zero touch Device resource: https://developers.google.com/zero-touch/reference/customer/rest/v1/customers.devices
33. Zero touch customer authorisation: https://developers.google.com/zero-touch/guides/customer/auth
34. Zero touch service accounts: https://developers.google.com/zero-touch/guides/customer/service-accounts
35. Knox Mobile Enrollment server integration: https://docs.samsungknox.com/dev/knox-mobile-enrollment/server-integration/get-started/
36. Knox OAuth scopes: https://docs.samsungknox.com/dev/knox-cloud-authentication/knox-oauth-2-0-authentication/scopes-for-knox-cloud-services-apis/
37. Knox OAuth, get access token: https://docs.samsungknox.com/dev/knox-cloud-authentication/knox-oauth-2-0-authentication/for-customers-resellers-and-msps/step-1-get-access-token/
38. KME view and manage devices: https://docs.samsungknox.com/admin/knox-mobile-enrollment/how-to-guides/manage-devices/view-and-manage-devices/
39. Directory API chromeosdevices resource: https://developers.google.com/workspace/admin/directory/reference/rest/v1/chromeosdevices
40. Directory API chromeosdevices.list: https://developers.google.com/workspace/admin/directory/reference/rest/v1/chromeosdevices/list
41. Chrome device security features: https://support.google.com/chrome/a/answer/1290515
42. ChromeOS user and browser settings (Lock screen, Idle settings): https://support.google.com/chrome/a/answer/2657289
43. Chrome Policy API resolve: https://developers.google.com/chrome/policy/reference/rest/v1/customers.policies/resolve
44. Chrome Policy schemas and privileges: https://developers.google.com/chrome/policy/guides/policy-schemas
45. Chrome Policy API setup: https://developers.google.com/chrome/policy/guides/setup
46. Chrome Policy API quotas: https://developers.google.com/chrome/policy/guides/api-quotas
47. Chrome Management API reference index: https://developers.google.com/chrome/management/reference/rest
48. countChromeVersions: https://developers.google.com/chrome/management/reference/rest/v1/customers.reports/countChromeVersions
49. countChromeDevicesReachingAutoExpirationDate: https://developers.google.com/chrome/management/reference/rest/v1/customers.reports/countChromeDevicesReachingAutoExpirationDate
50. Telemetry devices: https://developers.google.com/chrome/management/reference/rest/v1/customers.telemetry.devices
51. Telemetry API guide: https://developers.google.com/chrome/management/guides/telemetry_api
52. chromeBrowsers resource: https://developers.google.com/chrome/management/reference/rest/v1/customers.chromeBrowsers
53. chromeBrowsers.list: https://developers.google.com/chrome/management/reference/rest/v1/customers.chromeBrowsers/list
54. Chrome Enterprise Core: https://chromeenterprise.google/products/chrome-enterprise-core/
55. Chrome admin roles and privileges: https://support.google.com/chrome/a/answer/2984343
56. ChromeOS Auto Update policy: https://support.google.com/chrome/a/answer/6220366
57. Reports API chrome events: https://developers.google.com/workspace/admin/reports/v1/appendix/activity/chrome
58. Reports API mobile (Devices) events: https://developers.google.com/workspace/admin/reports/v1/appendix/activity/mobile
59. Cloud Identity Devices resource: https://docs.cloud.google.com/identity/docs/reference/rest/v1/devices
60. Cloud Identity devices.list: https://docs.cloud.google.com/identity/docs/reference/rest/v1/devices/list
61. Cloud Identity deviceUsers: https://docs.cloud.google.com/identity/docs/reference/rest/v1/devices.deviceUsers
62. Endpoint Verification device information: https://docs.cloud.google.com/endpoint-verification/docs/device-information
63. Endpoint Verification sync: https://docs.cloud.google.com/endpoint-verification/docs/sync-data
64. About Android device management with GEM: https://knowledge.workspace.google.com/admin/devices/about-android-device-management-with-google-endpoint-management
65. Android 12 and GEM: https://knowledge.workspace.google.com/admin/devices/android-12-and-google-endpoint-management
66. GEM zero touch enrolment: https://knowledge.workspace.google.com/admin/devices/set-up-automatic-zero-touch-enrollment-for-android
67. Compare mobile management features: https://knowledge.workspace.google.com/admin/devices/compare-mobile-management-features
68. Set up basic mobile device management: https://knowledge.workspace.google.com/admin/devices/set-up-basic-mobile-device-management
69. Directory API mobiledevices resource: https://developers.google.com/workspace/admin/directory/reference/rest/v1/mobiledevices
70. Administrator privilege definitions: https://knowledge.workspace.google.com/admin/users/administrator-privilege-definitions
71. ProtoJSON format (default values omitted): https://protobuf.dev/programming-guides/json/
72. Go packages: https://pkg.go.dev/google.golang.org/api/androidmanagement/v1 , https://pkg.go.dev/google.golang.org/api/androiddeviceprovisioning/v1 , https://pkg.go.dev/google.golang.org/api/chromepolicy/v1 , https://pkg.go.dev/google.golang.org/api/chromemanagement/v1
73. Device Trust from Android Enterprise (search summary only, not read; an on device SDK for allowlisted IdP, MTD and EDR apps, so not a Verity path): https://developers.google.com/android/management/device-trust-api

## 9. Proposed dictionary keys and check

| Proposal | Values | Check that uses it |
|---|---|---|
| `enterprise_specific_id` (identity) | AMAPI `hardwareInfo.enterpriseSpecificId`, GEM enrolment specific ID | matching and duplicate counting for personal Android 12 and later work profiles, which have no serial (G2) |
| `enrolment_channel` value `legacy_device_admin` | from `ownershipPrivilege` DEVICE_ADMINISTRATOR | `devices.enrolled` fails with "legacy device admin" (G22) |
| `reporting_gaps` (management) | list of sections the source did not report: software, device settings, network, apps | every state check turns `insufficient` for the gap instead of failing (G4) |
| `os_supported_until` (updates) | ChromeOS `autoUpdateThrough`; Android from Verity's reviewed vendor table | `devices.os_current` support clause (2.3) |
| new observation `device.purchase` | source (zero_touch, kme, chromeos_preprovisioned), serial, IMEI only for company owned, model, claimed configuration | NEW `devices.purchased_devices_enrolled` "Every device the company bought is under management": population is every device in the purchase lists; pass when a managed device matches on serial or IMEI and checked in within `stale_after_days`; fail when none; insufficient when a purchase list read is incomplete. EP-03 partial: finds bought devices that never enrolled, which an MDM alone cannot see (strategy F1, EP-03.B) |

Owner decisions raised: D-ACG-1 the default `android_patch_max_age_days` (90 proposed); D-ACG-2 whether
Verity keeps a vendor support table for Android models; D-ACG-3 whether to accept a zero touch credential
that cannot be read only (recommend no, use KME and ChromeOS PRE_PROVISIONED only, or ask the customer for a
CSV export).
