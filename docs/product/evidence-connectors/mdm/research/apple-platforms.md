# Apple platforms: what any Apple device management service can see and do

Round 2 research, vendor neutral. Brief: [BRIEF.md](BRIEF.md). Round 1: [mdm-and-endpoint-strategy.md](../../mdm-and-endpoint-strategy.md),
[jamf-pro.md](../../connectors/jamf-pro.md), [kandji.md](../../connectors/kandji.md),
[verification/devices-hr.md](../../verification/devices-hr.md).

Status marks: **V [n]** means an official Apple page or Apple's own schema, read on 2026-11-26, states it.
**U** means unverified, with the reason. Every MDM vendor relays this Apple layer: a vendor can show less than
Apple exposes for a channel, or add fields from its own agent, but it cannot get more out of the MDM
protocol than Apple allows. Use this file to judge any Apple connector (Jamf Pro, Kandji or Iru, Intune for
Apple, Apple Business built in management, others).

## 1. Scope

| Item | Covered |
|---|---|
| Platforms | macOS, iOS, iPadOS in depth; tvOS and visionOS briefly (section 2.4) |
| OS versions | Apple's device management schema release for iOS, macOS, tvOS, visionOS and watchOS 27.2 [1]; security releases page as published 18 November 2026 (latest iOS, iPadOS and macOS 27.2.1) [57] |
| Protocols | MDM commands and queries, MDM check in, configuration profiles, Declarative Device Management (DDM) declarations and status items [1][15][29] |
| Enrolment channels | Automated Device Enrollment (ADE), profile based Device Enrollment, account driven Device Enrollment, account driven User Enrollment, Shared iPad, manual supervision with Apple Configurator [30][31] |
| Purchase program | Apple Business API 2.8 (the API formerly documented as the Apple Business Manager API) [60][62] |
| Not covered | watchOS beyond schema rows, vendor APIs (their own files), Apple School Manager beyond noting it shares the API design [61] |
| Date read | 2026-11-26, all sources fetched in this session |

Naming: Apple's 2026 guides call the purchase and identity portal **Apple Business**; organisations on Apple
Business Manager or Apple Business Essentials move into it [71][72]. The developer path
`documentation/applebusinessmanagerapi` returned 404 on 2026-11-26; the live reference is
`documentation/applebusinessapi` [60]. This file says "Apple Business (formerly Apple Business Manager)".

Read only reminder: section 3 lists commands such as `EraseDevice` only so that Verity can judge the
command records a vendor keeps. Verity never sends any command and never asks for a credential that can.

## 2. Channels and visibility matrix

### 2.1 Enrolment channels in brief

| Channel | How it starts | Minimum OS | Supervised on enrolment | Ownership signal | Dictionary `enrolment_channel` |
|---|---|---|---|---|---|
| Automated Device Enrollment | device serial is in Apple Business, assigned to a service; enrols in Setup Assistant; can be made non removable | iOS 13, iPadOS 13.1, macOS 10.14.4, tvOS 13, visionOS 2, watchOS 10 | yes | company (purchase record) | `automated_company` | 
| Profile based Device Enrollment | user installs an enrolment profile | iOS 4, iPadOS 13.1, OS X 10.7, tvOS 9 | iPhone, iPad, Apple TV: no. Mac: yes (macOS 11 or later) | unknown | `user_initiated_device` |
| Account driven Device Enrollment | user signs in with a Managed Apple Account in Settings | iOS 17, iPadOS 17, macOS 14, visionOS 1.1 | iPhone, iPad, Vision Pro: no. Mac: yes | unknown (meant for company devices, can be personal) | `user_initiated_device` (see proposal P7) |
| Account driven User Enrollment | user signs in with a Managed Apple Account; for devices the user owns | iOS 15, iPadOS 15, macOS 14, visionOS 1.1 | no | personal | `byod_account_driven` |
| Shared iPad | ADE plus the Shared iPad option; supervised iPad with 32 GB or more | iPadOS 9.3 | yes (required) | company | `automated_company`, `device_class` shared |
| Manual supervision | Apple Configurator on iPhone, iPad, Apple TV; `profiles` command on Mac | n/a | yes | company in practice, not proven | `user_initiated_device` |

Sources: channels, versions and supervision V [30]; Mac Device Enrollment supervises from macOS 11 V [32][31];
ADE options and non removable enrolment V [36]; Shared iPad requirements V [37]; account driven flows V [33].
The current guide lists only the account driven form of User Enrollment [30][34]; whether the older profile
based User Enrollment still works on current OS versions: U (not stated on the pages read).

User Enrollment data separation: when an account driven enrolment completes, the OS creates separate
encryption keys for managed data (managed app containers, keychain items, Mail, Notes, Reminders, Calendar)
and destroys them on unenrolment, whether the user or the service unenrols V [33]. Apple's 2021 WWDC session
described this as a separate managed APFS volume; the current guide describes key separation only, so the
"separate APFS volume" wording for current OS versions is U.

### 2.2 macOS visibility matrix

Cells: yes, partial (why), no, n/a. "Policy" means the value is what the service configured, not what the
device reports.

| Dictionary key | ADE (supervised) | Device Enrollment, profile or account driven (supervised from macOS 11) | Account driven User Enrollment (macOS 14+) |
|---|---|---|---|
| `serial_number` | yes | yes | no: query, check in and status item all forbid it |
| `hardware_ids` (UDID, MAC) | yes | yes | no: UDID and MAC queries forbidden; an `EnrollmentID` is used |
| `hostname` | yes | yes | yes per schema (no restriction listed) |
| `device_name` | yes | yes | yes |
| `model`, `platform` | yes | yes | yes |
| `os_version`, `os_build` | yes | yes | yes |
| `ownership` | company | unknown unless the serial is in Apple Business | personal |
| `enrolment_channel` | yes: `EnrolledViaDEP` true | partial: `EnrolledViaDEP` false; profile versus account driven is not reported by the device | yes: `IsUserEnrollment` true |
| `supervised` | yes | yes | yes (false) |
| `disk_encryption` | yes | yes | partial: `FDE_Enabled` is readable but FileVault cannot be enforced, and the DDM FileVault status item is not allowed |
| `recovery_key_escrowed` | yes (has key flags; escrow only if the escrow payload was installed first) | yes, same | no: recovery key flags and the escrow payload are forbidden |
| `passcode_present`, `passcode_compliant` | n/a: macOS has no such keys | n/a | n/a |
| `idle_lock_seconds` | policy only | policy only | no: passcode payload, screen saver payloads and the DDM passcode configuration are all unavailable |
| `firewall_on` | yes | yes | yes per schema (only the app list is forbidden) |
| `os_integrity` (SIP, Secure Boot) | yes | yes | yes per schema |
| `activation_lock_or_frp` | partial: device key deprecated in macOS 13; Apple Business status endpoint | partial, same | no: query forbidden, and the guide lists Activation Lock management as not allowed |
| `removable_storage_blocked` | policy (macOS 15 DDM) | policy | no: configuration not allowed for user enrolment |
| `local_admin_present` | no | no | no |
| `av_*`, `edr_present` | no | no | no |
| `os_update_policy_assigned` | yes (DDM) | yes (DDM; macOS Device Enrollment is supervised) | no |
| `os_update_available` | yes (DDM status, macOS 14) | yes | no |
| `installed_apps` | yes (system apps included) | yes | no: command forbidden |
| `managed_apps` | yes | yes | yes |
| action: wipe | yes | yes | no: erase forbidden; unenrolment destroys managed data |
| action: lock | yes (PIN lock) | yes | no |
| action: lost mode | n/a: no Mac lost mode | n/a | n/a |

Sources: [4][5][6][7][8][16][17][19][20][21][22][30][35]. Per cell support is in the field map (section 3).

### 2.3 iOS and iPadOS visibility matrix

| Dictionary key | ADE (supervised) | Device Enrollment, profile or account driven (unsupervised) | Account driven User Enrollment | Shared iPad (ADE, supervised) |
|---|---|---|---|---|
| `serial_number` | yes | yes | no | yes |
| `hardware_ids` (UDID, IMEI, MEID, EID, MAC) | yes | yes | no | yes |
| `hostname` | n/a | n/a | n/a | n/a |
| `device_name` | yes | yes | yes | yes |
| `model`, `platform`, `os_version`, `os_build` | yes | yes | yes | yes |
| `ownership` | company | unknown unless in Apple Business | personal | company |
| `enrolment_channel` | partial: no ADE flag on iOS before 27; inferred from supervision and Apple Business | partial | yes: `IsUserEnrollment` | yes: `IsMultiUser` |
| `supervised` | yes | yes (false unless supervised with Configurator) | yes (false) | yes |
| `passcode_present` | yes | yes | partial: SecurityInfo key forbidden; DDM status item allowed | partial: passcode policies not supported on Shared iPad |
| `passcode_compliant` | yes | yes | partial: overall flag allowed, profile flag forbidden | partial |
| `idle_lock_seconds` | policy (device caps the user's choice) | policy | no: the limit is ignored, only "never" is removed (Apple pages disagree, gotcha G11) | yes, device reported (`AutoLockTime`, iOS 17) |
| `disk_encryption` | yes (inferred from caps and passcode) | yes | partial (passcode presence only through DDM) | partial |
| `recovery_key_escrowed` | n/a | n/a | n/a | n/a |
| `firewall_on`, `removable_storage_blocked` | n/a | n/a | n/a | n/a |
| `os_integrity` | no jailbreak signal; attestation of properties only | same | same | same |
| `activation_lock_or_frp` | partial: device key deprecated in iOS 16; bypass code (supervised); Apple Business status endpoint | partial: Activation Lock cannot be managed | no | partial |
| `os_update_policy_assigned` | yes (DDM; deferrals and automatic actions need supervision) | partial: enforcement allowed, deferrals not | no | yes |
| `os_update_available` | yes (DDM status, iOS 17) | yes | no | yes |
| `installed_apps` | yes | yes | partial: managed apps only | yes |
| `managed_apps` | yes | yes | yes | yes |
| action: wipe | yes | yes | no | yes (device channel) |
| action: lock | yes | yes | yes | yes |
| action: lost mode | yes | no (needs supervision) | no | yes |

Sources: [4][5][6][8][10][11][12][16][17][18][20][30][35][37][38].

### 2.4 tvOS and visionOS in brief

- tvOS: ADE and supervision exist; no passcode keys, no FileVault; `HardwareEncryptionCaps`, `EraseDevice`
  and DDM status items (from tvOS 16) apply V [4][5][10][16].
- visionOS: behaves like iOS for this purpose. User Enrollment is allowed from 1.1, passcode keys and DDM
  passcode status exist, `EraseDevice` is allowed except on user enrolment, Lost Mode does not exist
  (`EnableLostMode` is n/a) V [5][10][12][16].

## 3. Field map (Apple layer)

The read permission at the Apple layer is the MDM **access right** the enrolment profile grants the service
(for example `AllowQuerySecurity`). Verity never holds these; it reads the vendor's copy. Licence or tier:
none at the Apple layer. "Forbidden UE" means the schema marks the key or command `forbidden` under user
enrolment [2].

### 3.1 Identity

| Key | Apple source (exact names) | Platforms, minimum OS | Channel limits | Access right | Caveats | Status |
|---|---|---|---|---|---|---|
| `provider_device_id` | device enrolment: `UDID` (query, check in, DDM `device.identifier.udid`); user enrolment: `EnrollmentID` in check in and every response | all | UDID forbidden UE; `EnrollmentID` required UE | none for UDID | the vendor's own id is a vendor field; `EnrollmentID` is per enrolment, so re-enrolment gives a new one | V [4][6][24] |
| `serial_number` | `DeviceInformation` query `SerialNumber`; DDM `device.identifier.serial-number`; Apple Business `serialNumber` | query all; status iOS 16, macOS 13 | forbidden UE in query, check in and status item | `AllowQueryDeviceInformation` | Apple Business holds serials of purchased devices with no MDM at all | V [4][16][24][64] |
| `hardware_ids` | `UDID`; `ProvisioningUDID` (macOS 11.3; differs from UDID on Apple silicon); `ServiceSubscriptions[]` `IMEI`, `MEID`, `EID` (iOS 12); MACs `WiFiMAC`, `EthernetMAC`, `BluetoothMAC`; Apple Business `imei`, `meid`, `eid`, MAC fields | see left | all forbidden UE | `AllowQueryNetworkInformation` for MACs and `ServiceSubscriptions` | top level `IMEI` and `MEID` queries were deprecated in iOS 16 and **removed in iOS 26** | V [4][7][64] |
| `hostname` | `HostName`, `LocalHostName` (Bonjour) | macOS 10.11 only | no UE restriction listed | `AllowQueryDeviceInformation` | not applicable on iOS | V [4] |
| `device_name` | `DeviceName` | all | none listed | `AllowQueryDeviceInformation` | user set unless the service sets it: Mac on any channel but UE, iOS only on ADE | V [4][30] |
| `manufacturer` | fixed value Apple | all | none | none | | V (definition) |
| `model` | `Model`, `ModelName`, `ProductName`, `ModelNumber` (iOS 16.4, macOS 13.3); DDM `device.model.family`, `.identifier`, `.marketing-name`; Apple Business `deviceModel`, `productType` | all | none listed | `AllowQueryDeviceInformation` | | V [4][16][53][64] |
| `platform` | DDM `device.operating-system.family` (iOS, iPadOS, macOS, tvOS); Apple Business `productFamily` | iOS 15, macOS 13 | allowed UE | none | separates iOS from iPadOS directly | V [16][48][64] |
| `os_version` | `OSVersion`; DDM `device.operating-system.version`; Background Security Improvement letter `SupplementalOSVersionExtra` and DDM `device.operating-system.supplemental.extra-version` | query all; supplemental iOS 16.1, macOS 13 | allowed UE (OS version query is allowed on every channel) | `AllowQueryDeviceInformation` | the plain version misses the improvement letter, for example "(a)" | V [4][16][30][54] |
| `os_build` | `BuildVersion`, `SupplementalBuildVersion`; DDM `.build-version`, `.supplemental.build-version` | as above | allowed UE | `AllowQueryDeviceInformation` | | V [4][16] |

### 3.2 Class, ownership, management, people

| Key | Apple source | Platforms, minimum OS | Channel limits | Access right | Caveats | Status |
|---|---|---|---|---|---|---|
| `device_class` | from model family; Shared iPad: `IsMultiUser` (iOS 9.3), DDM `mdm.is-shared-ipad` (iPadOS 27) | | | `AllowQueryDeviceInformation` | no Apple key marks a kiosk or single app device in the query and status lists read | V [4][16] |
| `ownership` | no device key. User Enrollment means personal; ADE means the device is in Apple Business; other channels are unknown until the serial is matched in Apple Business `GET /v1/orgDevices` | | | | supervision alone does not prove company ownership (G15) | V [30][34][36][63] |
| `enrolment_channel` | SecurityInfo `ManagementStatus`: `EnrolledViaDEP` (macOS 10.13.2 only), `IsUserEnrollment` (iOS 13, macOS 10.15), `UserApprovedEnrollment` (macOS 10.13.2); DDM `mdm.enrollment-type` none, supervised, device, user (all platforms, 27.0) | see left | | `AllowQuerySecurity` | the device does not say whether Device Enrollment was profile based or account driven; the service knows which flow it served (U: per vendor) | V [6][16] |
| `supervised` | `IsSupervised` | iOS 6, macOS 10.15, tvOS 9 | | `AllowQueryDeviceInformation` | Mac Device Enrollment is supervised from macOS 11 | V [4][31][32] |
| `management_state` | no single key. Unenrolled: `CheckOut` check in, sent once and on a best effort basis; lost mode: `IsMDMLostModeEnabled` (iOS 9.3, forbidden UE); pending: `AwaitingConfiguration` (held in Setup Assistant; DDM `mdm.is-awaiting-configuration` from 27); wiped: inferred (G3) | | | `AllowQueryDeviceInformation` | a removed or erased device that fails to check out looks only "silent" | V [4][16][24][28] |
| `enrolled_at` | no query returns an enrolment date; the service records when the `Authenticate` and `TokenUpdate` check ins arrived | | | | vendor field | V [4][24] |
| `last_check_in_at` | not a device key; the device connects only after a push, or polls by itself after a `NotNow` | | | | vendor field; staleness rules in section 5 | V [26][27] |
| `provider_compliance_state` | Apple has no overall verdict. Device verdicts that exist: `PasscodeCompliant`, `PasscodeCompliantWithProfiles`, DDM declaration `active` and `valid` | | | `AllowQuerySecurity` | | V [6][16] |
| `assigned_user_email` | no query returns a user email for device channels. macOS user channel responses carry `UserShortName`, `UserLongName`, `UserID`; account driven enrolments authenticate with a Managed Apple Account; Apple Business built in management lists `enrolledUserId` | | | | whether a vendor stores the Managed Apple Account as the assigned user: U (vendor) | V [6][33][68] |
| `assigned_user_provider_id` | Apple Business `enrolledUserId` (built in management only); Apple Business users API | | | Apple Business "View Users" | | V [68][70] |
| `assignment_source` | enrolling user for account driven channels; manual otherwise | | | | vendor field | U (vendor behaviour) |

### 3.3 Encryption and lock

| Key | Apple source | Platforms, minimum OS | Channel limits | Access right | Caveats | Status |
|---|---|---|---|---|---|---|
| `disk_encryption` (macOS) | SecurityInfo `FDE_Enabled`; DDM `diskmanagement.filevault.enabled`; Apple Business built in `isFileVaultEnabled` | macOS 10.9; status macOS 14 | DDM item allowed only on supervised and local enrolments | `AllowQuerySecurity` | Apple's keys are on or off only: no `in_progress` or paused state (vendors that show those read them with their own agent: U). Apple silicon without FileVault still encrypts with a volume key, but that is not FileVault (G6) | V [5][6][16][58][68] |
| `disk_encryption` (iOS, iPadOS) | SecurityInfo `HardwareEncryptionCaps` (1 block, 2 file, 3 both) together with `PasscodePresent`; Apple states data protection needs caps 3 and a passcode | iOS 4 | `PasscodePresent` forbidden UE: use DDM `passcode.is-present` | `AllowQuerySecurity` | an inference, not a device flag; strength depends on the passcode | V [5][6][16][59] |
| `encryption_method` | FileVault on macOS; platform data protection on iOS, iPadOS, visionOS, tvOS | | | | | V [41][58] |
| `recovery_key_escrowed` | `FDE_HasPersonalRecoveryKey`, `FDE_HasInstitutionalRecoveryKey` (macOS 10.9); escrow evidence: `FDE_PersonalRecoveryKeyCMS` present in a SecurityInfo response (macOS 10.13) after the `com.apple.security.FDERecoveryKeyEscrow` payload was installed before FileVault was turned on, or after a `RotateFileVaultKey` with a reply certificate | macOS | all forbidden UE; the escrow payload is forbidden UE | `AllowQuerySecurity` | the CMS value is key material: Verity never reads it and needs a vendor boolean. "Has key" is not "escrowed" (G5) | V [5][6][22][23][42] |
| `passcode_present` | iOS: SecurityInfo `PasscodePresent`; DDM `passcode.is-present` | iOS 4; status iOS 16, visionOS 1.1 | SecurityInfo key forbidden UE; status item allowed UE | `AllowQuerySecurity` | macOS has neither (both n/a) | V [5][16] |
| `passcode_compliant` | `PasscodeCompliant` (all requirements, Exchange included); `PasscodeCompliantWithProfiles`; DDM `passcode.is-compliant` | iOS 4; status iOS 16 | profile flag forbidden UE | `AllowQuerySecurity` | the DDM item reads true when no passcode policy exists (G1); macOS n/a | V [5][6][16] |
| `idle_lock_seconds` | device reported only on Shared iPad: `AutoLockTime` seconds (iOS 17), `PasscodeLockGracePeriodEnforced`. Policy elsewhere: passcode payload `maxInactivity` (minutes), `maxGracePeriod`; DDM `com.apple.configuration.passcode.settings` `MaximumInactivityInMinutes`, `MaximumGracePeriodInMinutes`; macOS `com.apple.screensaver` (device channel) and `com.apple.screensaver.user` (user channel) `idleTime` seconds, `askForPassword`, `askForPasswordDelay` seconds | see section 3.6 | see section 3.6 | `AllowInspection` (profile list) | `ProfileList` returns payload types, not payload values (G10) | V [5][9][17][20][21] |
| `idle_lock_origin` | `device_reported` only for Shared iPad; `policy` on every other Apple channel | | | | | V [5][9] |

### 3.4 Hardening and protection

| Key | Apple source | Platforms, minimum OS | Channel limits | Access right | Caveats | Status |
|---|---|---|---|---|---|---|
| `firewall_on` | SecurityInfo `FirewallSettings`: `FirewallEnabled`, `BlockAllIncoming`, `StealthMode`, `LoggingEnabled` (12); Apple Business built in `isFirewallEnabled` | macOS 10.12 | allowed UE except the `Applications` list | `AllowQuerySecurity` | the firewall payload can be installed only on device and ADE channels | V [5][6][56][68] |
| `os_integrity` (macOS) | `SystemIntegrityProtectionEnabled`; `SecureBoot` `SecureBootLevel` (off, medium, full, not supported), `ExternalBootLevel`, `ReducedSecurity` (Apple silicon at medium); `AuthenticatedRootVolumeEnabled` (macOS 11); `IsRecoveryLockEnabled` (11.5, Apple silicon) | macOS | no UE restriction on SIP and Secure Boot | `AllowQuerySecurity` | | V [5][6] |
| `os_integrity` (iOS) | no jailbreak or integrity key in the DeviceInformation or SecurityInfo lists; `DevicePropertiesAttestation` (iOS 16, macOS 14) returns an Apple signed certificate chain describing device properties on A11 or later and Apple silicon | | attestation allowed UE | none listed | which properties the certificate carries per channel: U (OID list not read) | V [4][7] |
| `activation_lock_or_frp` | `IsActivationLockEnabled` (deprecated iOS 16, macOS 13; forbidden UE); `IsActivationLockSupported` (macOS); `ManagementStatus.IsActivationLockManageable` (macOS 10.15); `IsDeviceLocatorServiceEnabled` (Find My, iOS 7); Apple Business `GET /v1/orgDevices/{id}/activationLockStatus`: `isLocked`, `lockType` MDM, USER, NONE | see left | | `AllowQueryDeviceInformation`; Apple Business "Get the Activation Lock status for a device" | Apple Business is the live source for devices it holds (G13) | V [4][6][7][62][67][71] |
| `removable_storage_blocked` | DDM `com.apple.configuration.diskmanagement.settings` `Restrictions.ExternalStorage` Allowed, ReadOnly, Disallowed (also `NetworkStorage`) | macOS 15 | supervised and local only | n/a | only policy plus the declaration's `active` and `valid` state; no effective mount state | V [16][19] |
| `local_admin_present` | none: `UserList` (macOS, supervised) has no admin flag; `AutoSetupAdminAccounts` lists only admin accounts the service created | | | | needs a vendor agent or attestation | V [4][25] |
| `av_present`, `av_realtime_on`, `av_signatures_current`, `edr_present` | none in the DeviceInformation, SecurityInfo or status item lists | | | | XProtect versions shown by vendors come from their agents: U | V [4][5][16] |

### 3.5 Updates, software, actions

| Key | Apple source | Platforms, minimum OS | Channel limits | Access right | Caveats | Status |
|---|---|---|---|---|---|---|
| `os_update_policy_assigned` | DDM `com.apple.configuration.softwareupdate.settings` (iOS 18, macOS 15) and `com.apple.configuration.softwareupdate.enforcement.specific` (`TargetOSVersion`, `TargetBuildVersion`, `TargetLocalDateTime`; iOS 17, macOS 14), state through `management.declarations` `active` and `valid` | see left | macOS: supervised only. iOS: supervised or device; deferrals and automatic actions supervised only. Not UE | n/a | the `com.apple.SoftwareUpdate` profile and the restriction deferral keys were **removed in OS 27** | V [3][14][16][18] |
| `os_update_available` | DDM `softwareupdate.pending-version` (`os-version`, `build-version`, `target-local-date-time`), `softwareupdate.install-state` (none, downloading, prepared, installing, failed), `softwareupdate.failure-reason` (`count`, `reason`, `timestamp`), `softwareupdate.install-reason` | iOS 17, macOS 14 | macOS supervised; iOS supervised or device; not UE | n/a | MDM commands `AvailableOSUpdates`, `OSUpdateStatus`, `ScheduleOSUpdate`, `ScheduleOSUpdateScan` were **removed in OS 27** (G8). An empty pending version means nothing is pending, not that the device is current | V [3][14][15][16] |
| `security_patch_level` | Apple analogue: the Background Security Improvement letter (`SupplementalOSVersionExtra`, DDM `...supplemental.extra-version`) | iOS 16.1, macOS 13 | | | improvements ship only for the latest versions | V [4][16][49][51] |
| `os_supported` | not a device field; Verity computes it from Apple's security releases list and Apple's note that older majors do not get every fix | | | | section 3.8 | V [49][57] |
| `browser_versions` | macOS `InstalledApplicationList` includes system apps; iOS 26 and later also include system apps | | forbidden on macOS UE | `AllowQueryApplications` | reading Safari's version from that list: U (not tested) | V [8] |
| `installed_apps` | `InstalledApplicationList`: `Identifier`, `Name`, `Version`, `ShortVersion`, `Source` (iOS 17.2), `HasUpdateAvailable` | iOS 5, macOS 10.7 | macOS: forbidden UE. iOS UE: managed apps only, DDM managed apps excluded | `AllowQueryApplications` | from OS 26 costly fields appear only if requested | V [8][35] |
| `managed_apps` | `ManagedApplicationList` (iOS 5, macOS 11); DDM `app.managed.list` (iOS 17.2, macOS 26) | | allowed UE | `AllowAppInstallation` | | V [8][16] |
| `device.action` wipe | `EraseDevice` (right: Device Erase; supervision not required); macOS keys `ObliterationBehavior`, `PIN`; iOS `ReturnToService`; `EACSPreflight` query (macOS 13.3); Apple Business built in `deviceEraseStatus` ERASED, NOT_ERASED | all | forbidden UE | `AllowDeviceErase` | response is `Acknowledged` or `Error` and is not retried (G3) | V [4][10][44][68] |
| `device.action` lock | `DeviceLock` with `Message`, `PhoneNumber`, macOS `PIN`; response `MessageResult` | iOS 4, macOS 10.7 | iOS allowed UE; macOS forbidden UE | `AllowPasscodeRemovalAndLock` | Mac lock uses Find My and needs a recovery partition; on Apple silicon before macOS 11.5 it deactivates the Mac | V [11][45] |
| `device.action` lost mode | `EnableLostMode`, `DisableLostMode`; state `IsMDMLostModeEnabled` | iOS 9.3, supervised only | forbidden UE; not on macOS or visionOS | none listed | erasing a device also turns lost mode off | V [4][12][45] |
| `device.action` retire or selective wipe | no command; unenrolment (by user or service) destroys the managed data keys | account driven channels | | | the evidence is the unenrolment, so `CheckOut` or silence (G4) | V [33] |
| `device.action` `issued_at`, `issued_by`, `state`, `completed_at` | not device data: the service keeps the queue; the device returns `Status` (Acknowledged, Error, CommandFormatError, Idle, NotNow) per `CommandUUID`; results are cached and resent after a disconnect | | | | Apple says a command counts as executed only once `Acknowledged` or `Error` arrives | V [6][26][27] |

### 3.6 Screen lock detail

| Platform | How it is set | What comes back | Evidence Verity can claim |
|---|---|---|---|
| macOS | passcode payload `maxInactivity` (minutes, at most 60) and `maxGracePeriod`, which macOS turns into screen saver settings; or DDM passcode configuration `MaximumInactivityInMinutes` (range 0 to 15; several configurations combine to the smallest); or `com.apple.screensaver` `idleTime` (seconds, 0 means never) with `askForPassword` and `askForPasswordDelay` (seconds, 0 immediate, 2147483647 turns the requirement off) | nothing about the effective idle time: `ProfileList` shows the payload types installed; DDM shows the declaration `active` and `valid` | policy value plus "installed" or "active and valid". `idle_lock_origin` = policy |
| iOS, iPadOS | passcode payload `maxInactivity` (minutes) or DDM `MaximumInactivityInMinutes`; the user may pick any Auto-Lock value up to the limit | `PasscodePresent`, `PasscodeCompliant`, `PasscodeCompliantWithProfiles`, DDM passcode status | policy value, bounded on the device, with device compliance flags. Stronger than macOS |
| iOS User Enrollment | the passcode payload forces only a 6 digit non simple passcode; the schema says `maxInactivity` is ignored apart from removing "never"; the deployment page says the key is honoured | `PasscodeCompliant`, DDM passcode status | `insufficient` for an idle time limit (G11) |
| Shared iPad | passcode policies are not supported | `AutoLockTime` (seconds, iOS 17) and `PasscodeLockGracePeriodEnforced` | device reported value |

Sources: V [5][9][17][20][21][38][39][40]. The passcode payload (`com.apple.mobiledevice.passwordpolicy`) is
**deprecated in iOS, macOS, visionOS and watchOS 27** V [3][20]; the DDM passcode configuration is its
successor and is available on macOS only for supervised and local enrolments V [17]. The deployment page
gives iOS Auto-Lock choices of one to five minutes or never V [39]; the schema gives a DDM range of 0 to 15
minutes V [17]. Vanta's Jamf check reads a `loginWindowIdleTime` key (jamf-pro.md S3); that key is not in
Apple's current `com.apple.screensaver` schema [21], so Verity should not rely on it: U.

### 3.7 FileVault and escrow detail

- States from Apple: on or off only (`FDE_Enabled`, DDM `diskmanagement.filevault.enabled`) V [6][16].
- Recovery keys: one personal recovery key per encrypted volume; the service can hide it from the user;
  institutional recovery key by certificate is not supported on Apple silicon V [23][42].
- Escrow: the escrow payload gives the Mac a certificate; the Mac wraps the personal key in CMS and returns
  it in the SecurityInfo response; because the wrap is asymmetric the service itself may not be able to
  decrypt it without an extra admin step V [22][42]. The payload must be system scoped, only one per Mac, and
  the system gives no warning if FileVault was already on when it arrived V [22].
- What MDM data can prove: that a key exists (`FDE_HasPersonalRecoveryKey`) and that an encrypted key was
  delivered (vendor flag derived from receiving `FDE_PersonalRecoveryKeyCMS`). It cannot prove the key is
  still valid after a user changed it outside management, or that anyone can decrypt it. Vendor validity
  flags (Jamf `individualRecoveryKeyValidityStatus`) are the vendor's own test: U for the method.
- Enforcement in Setup Assistant from macOS 14; on macOS 26.4 or later FileVault is on by default during
  Setup Assistant V [36][42][58].
- FileVault payload settings need supervision or user approved enrolment when installed manually (macOS
  10.15 and later) V [23].

### 3.8 Software updates and Apple's support pattern

- Enforcement and deferral move entirely to DDM in OS 27 (section 3.5) V [3][15].
- Deferrals of 1 to 90 days on supervised devices; over the air updates stay available for up to 180 days
  after release so the longest deferral can still install V [50].
- Background Security Improvements (formerly Rapid Security Responses) ship only for the latest OS versions,
  ignore deferrals, can be removed by the user unless the service blocks rollback, and are reported through
  the supplemental version status items V [49][51][18].
- Apple's stated position: because of architecture and system dependencies, earlier major versions do not
  receive fixes for all known issues V [49]. Apple publishes no lifecycle commitment in the pages read.
- Observed on Apple's security releases list (9 November 2026): macOS 27.2.1, 26.7.3 and 15.8.3 all shipped;
  iOS and iPadOS 27.2.1, 26.7.3 (iPhone 11 and later) and 18.7.12 (only iPhone XS, XS Max, XR and iPad 7th
  generation) shipped V [57]. Reading: macOS currently patches three majors; iOS 18 is patched only for
  hardware that cannot run iOS 26. This is a snapshot, not a policy.
- Proposal for `os_supported`: a version counts as supported when Apple shipped a security release for that
  major in the last N days (setting) and, for iOS, the device model is in that release's "available for" list.
  The check result should say "fully patched" only for the latest major (G19).

### 3.9 Wipe, lost mode and Activation Lock detail

- `EraseDevice` needs no supervision, works on the device and ADE channels on every platform, is forbidden on
  User Enrollment, and erases even a locked device without warning V [10][44].
- Mac erase method: macOS 12 and later use Erase All Content and Settings on Apple silicon and T2 Macs.
  Requirements: Apple silicon needs a bootstrap token held by the service; both need to start from the first
  partition with a signed system volume, not from an external disk; T2 needs Full Security and no firmware
  password. Otherwise the Mac falls back to obliteration, after which macOS must be reinstalled. Intel Macs
  before T2 always obliterate V [44][10]. `EACSPreflight` (macOS 13.3) reports success, not supported, or a
  reason in advance V [4][44].
- Response meaning by `ObliterationBehavior`: `Default`: if preflight fails the Mac answers `Error` and
  still tries to obliterate. `DoNotObliterate`: preflight failure answers `Error` and nothing happens; if
  preflight passes but the erase then fails, the answer was already `Acknowledged` and nothing is erased.
  `ObliterateWithWarning`: answers `Acknowledged` and obliterates if needed. `Always`: obliterates V [10][44].
- The device acknowledges first and then erases; it does not retry its response V [10][44].
- Return to Service (iPhone, iPad, Apple TV, Vision Pro): an erase can carry Wi-Fi and enrolment data so the
  device re-enrols by itself; DDM `mdm.is-return-to-service` from 27 V [10][16][55].
- Lost Mode: supervised iPhone and iPad only; location can be queried only while in Lost Mode; leaving it is
  only possible by the service V [12][45]. Verity never collects location.
- Activation Lock: organisation linked (managed through Apple Business by the service) or user linked
  (personal Apple Account with Find My); on supervised devices it is off unless the service allows it; the
  device bypass code is available for 15 days after supervision V [13][46]. On a Mac with macOS 11 or later
  enrolled through Device Enrollment, Activation Lock may already be on before the service can manage it V [46].

### 3.10 DDM status channel

- Minimum versions: DDM from iOS 15, iPadOS 15, macOS 13, tvOS 16, visionOS 1.1, watchOS 10 (status items
  `management.declarations` and `management.client-capabilities`) V [16][29].
- Status items relevant to Verity: `device.operating-system.version`, `.build-version`,
  `.supplemental.extra-version`, `.supplemental.build-version`, `device.identifier.serial-number`,
  `device.model.*`, `passcode.is-present`, `passcode.is-compliant` (iOS, visionOS, watchOS; not macOS),
  `diskmanagement.filevault.enabled` (macOS 14), `softwareupdate.*` (iOS 17, macOS 14), `app.managed.list`,
  `management.declarations`, and from 27 `mdm.enrollment-type`, `mdm.is-shared-ipad`,
  `security.lockdown-mode` V [16].
- Freshness: the device sends a report when a subscribed item changes, and a full report every 24 hours;
  the service must subscribe to each item, except `management.*` items, which are always sent V [29][47].
- On macOS and Shared iPad the device and user channels report separately V [29].
- Each item lists allowed enrolment types in the schema; for example the serial number item excludes user
  enrolment, the passcode items include it V [2][16].

## 4. Auth and permissions

### 4.1 Apple layer

The MDM protocol grants access rights to the service in the enrolment profile; Verity is never a party to
that channel and reads through the vendor (vendor files hold the read only credential). Relevant rights:
`AllowQueryDeviceInformation`, `AllowQueryNetworkInformation`, `AllowQuerySecurity`, `AllowInspection`
(profile list), `AllowQueryApplications`, `AllowAppInstallation` (managed app list) V [4][5][8][9].

### 4.2 Apple Business API (purchased device population)

| Step | Detail | Status |
|---|---|---|
| Who creates it | an Organization Administrator, in Apple Business: Settings, then API, then Add API Account; up to 50 API accounts; a role is chosen for the account | V [70] |
| Least privilege role | a custom role (up to 15 custom roles; permissions are granular) holding only: "View device management services and add devices with Apple Configurator" (covers the GET device and service endpoints) and "Get the Activation Lock status for a device"; optional "View Users" and "Access audit events using the API" | V [70][71] |
| Caveat on that permission | its name also covers adding devices with Apple Configurator in the portal; the API endpoints it unlocks are all reads. Whether an API account can use the portal side: U | V [70] for the mapping; rest U |
| Never granted | assign, unassign or release devices; schedule migration; manage Blueprints; create, edit or delete Configurations; webhook management (creating a webhook writes to the customer's organisation) | V [70][60] |
| Built in management devices | `GET /v1/mdmDevices` and `/details`: the permission that gates them is not in the API account table | U (not listed [70]) |
| Credentials | Apple Business generates a private key (.pem, generated once, downloaded by the administrator) and an Edit view shows the connection details; the developer guide names them client id and key id and says they are returned "when you upload a public key", so the two pages describe the key origin differently | V [61][70] |
| Token | client assertion JWT with header `alg` ES256 and `kid` (key id) and claims `sub` (client id), `aud` `https://account.apple.com/auth/oauth2/v2/token`, `iat`, `exp` (at most 180 days after `iat`), `jti`. Then `POST https://account.apple.com/auth/oauth2/token` with `grant_type=client_credentials`, `client_id`, `client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer`, `client_assertion`, `scope=business.api`. Access token lasts 3600 seconds; get a new one on expiry or on any 401 | V [61] |
| Verity handling | hold the private key envelope encrypted (CLAUDE rule 8), mint a short lived assertion per run rather than storing a 180 day assertion | proposal |

Read endpoints (base `https://api-business.apple.com`):

| Endpoint | Gives | Status |
|---|---|---|
| `GET /v1/orgDevices` | every device added to the organisation: `serialNumber`, `productFamily`, `productType`, `deviceModel`, `partNumber`, `orderNumber`, `orderDateTime`, `addedToOrgDateTime`, `updatedDateTime`, `purchaseSourceType` (APPLE, RESELLER, MANUALLY_ADDED), `purchaseSourceId`, `status` (ASSIGNED, UNASSIGNED), `imei`, `meid`, `eid`, MAC addresses, migration fields; `fields[orgDevices]` selects fields; filters on serial, order number, family, purchase source, status, added date, order date (with GT, GTE, LT, LTE); `limit` up to 1000 and a cursor | V [63][64] |
| `GET /v1/orgDevices/{id}` | one device; `releasedFromOrgDateTime` is returned only on single device reads | V [64] |
| `GET /v1/orgDevices/{id}/relationships/assignedServer` and `/assignedServer` | the service the device is assigned to | V [66] |
| `GET /v1/orgDevices/{id}/activationLockStatus` | `isLocked`, `lockType` (MDM, USER, NONE); 404 if the organisation does not hold that serial | V [67] |
| `GET /v1/mdmServers` | `serverName`, `serverType` (MDM, APPLE_CONFIGURATOR, APPLE_MDM), `status` (ACTIVE, INACTIVE, DELETED), `deviceCount`, `lastConnectedDateTime`, `defaultProductFamilies` | V [65] |
| `GET /v1/mdmServers/{id}/relationships/devices` | serials assigned to that service, `limit` up to 1000 | V [66] |
| `GET /v1/mdmDevices`, `GET /v1/mdmDevices/{id}/details` | Apple Business built in management only: `deviceName`, `serialNumber`, `productFamily`, `enrolledUserId`; details add `osVersion`, `platform`, `lastCheckInDateTime`, `isFileVaultEnabled`, `isFirewallEnabled`, `deviceEraseStatus`, `deviceLockStatus`, `lostModeStatus`, storage, MACs, IMEI, MEID | V [68] |
| `GET /v1/auditEvents` | organisation audit events; `filter[startTimestamp]` and `filter[endTimestamp]` required; cursor paging | V [69] |

How it gives Verity an independent population: Apple Business lists what the company bought through Apple,
an authorised reseller or carrier linked to the organisation, or added by hand with Apple Configurator,
whether or not it ever enrolled V [63][64][72]. Joining `orgDevices` (status ASSIGNED and the assigned
server) to the MDM inventory by serial finds company devices that were never enrolled, enrolled in the wrong
service, or released. Devices bought at retail without the organisation's customer number are not in it, so
this is the "known purchases" population, not every device (G16).

## 5. Limits

| Item | Detail | Status |
|---|---|---|
| Device reporting | the device talks to the service only after an APNs push or by itself after a `NotNow`; there is no fixed device interval in the protocol, so inventory age depends on the vendor's schedule | V [26][27]; vendor cadence U |
| Inactive devices | Apple suggests treating a device as inactive after it ignores pushes for several days to a week | V [28] |
| Unenrolment signal | `CheckOut` is sent once, best effort, only if the profile asked for it | V [24][28] |
| DDM status | change driven, plus a full report every 24 hours | V [47] |
| History | the device reports present state only; no Apple query returns past state. Command history lives only in the vendor. Verity must keep its own daily observations | V [4][5][26] |
| Apple Business API paging | cursor paging; `limit` maximum 1000; keep filters identical across pages | V [63] |
| Apple Business API rate | 429 Too Many Requests is documented on every endpoint; no number is published | V [63] (429); numbers U |
| Apple Business audit retention | not stated | U |
| Apple Business updates | `updatedDateTime` per device; webhooks exist (API 2.8) but need a write to create, so Verity polls | V [62][64] |

## 6. Gotchas that would make a check wrong

| # | Gotcha | Effect on a check | Source |
|---|---|---|---|
| G1 | DDM `passcode.is-compliant` reads true when no passcode policy exists | `passcode_compliant` true proves nothing without an assigned policy (proposal P2) | V [16] |
| G2 | macOS has no passcode present or compliant keys at all | Mac screen lock is policy evidence only | V [5][16] |
| G3 | An `Acknowledged` erase is sent before the erase runs and never retried; on Mac `Default` can answer `Error` and still erase, `DoNotObliterate` can answer `Acknowledged` and not erase | `devices.wipes_confirmed` needs a second signal (device silent afterwards, new enrolment, Return to Service status, or Apple Business `deviceEraseStatus`) | V [10][44][68] |
| G4 | `CheckOut` is best effort and sent once | removal can only be inferred from silence; do not read "no CheckOut" as "still managed" | V [24][28] |
| G5 | `FDE_HasPersonalRecoveryKey` true does not mean the key was escrowed; escrow installed after FileVault was on is silently skipped | `devices.recovery_key_escrowed` must read the vendor's escrow flag, never the "has key" flag | V [6][22] |
| G6 | Apple silicon Macs encrypt user data with a volume key even with FileVault off | do not treat "hardware encrypted" as FileVault; `FDE_Enabled` is the test | V [58] |
| G7 | iOS encryption is inferred from `HardwareEncryptionCaps` 3 plus a passcode; under User Enrollment the SecurityInfo passcode key is withheld | read DDM `passcode.is-present` for user enrolled devices, else `insufficient` | V [5][6][16] |
| G8 | OS 27 removed the MDM update commands and the update queries | any vendor field such as "available updates" for OS 27 devices must now come from DDM; an empty list may mean "no data", not "current" | V [3][14][15] |
| G9 | The passcode payload is deprecated in OS 27; the DDM passcode configuration replaces it, takes the smallest of several values, and caps inactivity at 15 minutes | screen lock evaluation must read declarations as well as profiles | V [3][17][20] |
| G10 | `ProfileList` returns payload type and identifier, not settings; encrypted profiles omit even the payload list | the idle value comes from the vendor's profile definition, not the device | V [9] |
| G11 | Apple's schema says User Enrollment ignores `maxInactivity` (only "never" is removed); the deployment payload page says user enrolled devices honour it | treat User Enrollment idle lock as `insufficient` until tested | V [20][39] |
| G12 | Top level `IMEI` and `MEID` queries were removed in iOS 26 | a vendor field may go empty on iOS 26; use `ServiceSubscriptions` or Apple Business | V [4][7] |
| G13 | `IsActivationLockEnabled` is deprecated (iOS 16, macOS 13) | vendor Activation Lock fields may be stale; Apple Business `activationLockStatus` is authoritative for devices it holds | V [4][7][67] |
| G14 | `EnrolledViaDEP` exists only on macOS; `mdm.enrollment-type` arrives only in 27 and its "supervised" value merges ADE with manual supervision | iOS `automated_company` must come from Apple Business or the vendor | V [6][16] |
| G15 | Mac Device Enrollment (macOS 11+) and account driven Device Enrollment on Mac both supervise | supervised Mac is not proof of company ownership | V [30][32] |
| G16 | Apple Business lists only devices linked to the organisation; `releasedFromOrgDateTime` only on single device reads | the purchase population misses retail buys; list reads cannot show released devices | V [63][64] |
| G17 | Apple Business `status` ASSIGNED means assigned to a service, not enrolled; assigning does not change a current enrolment | join to the MDM inventory before claiming enrolment | V [64][72] |
| G18 | The OS version string omits the Background Security Improvement letter | `devices.os_current` must read the supplemental fields | V [4][16][51] |
| G19 | Older majors do not receive every fix | "supported" and "fully patched" are different results | V [49] |
| G20 | Lost Mode exists only on supervised iPhone and iPad; Mac uses a PIN lock | lost mode checks give `not_applicable` on Mac, `insufficient` on unsupervised iOS | V [12][45] |
| G21 | DDM status on macOS and Shared iPad comes per channel | a user channel value is not the device value | V [29] |
| G22 | `InstalledApplicationList` content differs by channel and OS (managed only on iOS UE, system apps on macOS and OS 26+, costly fields omitted from 26) | app checks need per channel population rules | V [8] |
| G23 | Command `ErrorCode` and `ErrorDomain` values can change between releases | never key a check on error codes | V [26] |
| G24 | Shared iPad does not support passcode policies | passcode checks on Shared iPad are `not_applicable` with reason, idle lock is device reported | V [37][38] |
| G25 | An Apple silicon Mac without a bootstrap token, or a T2 Mac with a firmware password or below Full Security, can still be wiped, but by obliteration | `devices.remote_wipe` should record the erase method, not fail on a missing token | V [44][10] |
| G26 | The Activation Lock bypass code is retrievable only for 15 days after supervision | leaver recovery can fail on user linked locks; Apple Business shows `lockType` USER | V [13][46][67] |
| G27 | `PasscodePresent` and `PasscodeCompliant` are SecurityInfo keys, not DeviceInformation queries | vendor mappings and test fixtures must use the right command | V [4][5] |

## 7. Corrections to round 1

| File | Claim | Correction | Source |
|---|---|---|---|
| jamf-pro.md 5.1 `devices.remote_wipe`, verification devices-hr.md row 112 | Apple's erase prerequisites per Mac are unverified | Confirmed: Apple silicon needs a bootstrap token for Erase All Content and Settings; Apple silicon and T2 need first partition boot and a signed system volume; T2 needs Full Security and no firmware password. Missing them does not block a wipe: the Mac falls back to obliteration (then needs macOS reinstall). Pre T2 Intel always obliterates. The check should pass on "erase possible" and record the method | [10][44] |
| jamf-pro.md 5.2 `devices.wipes_confirmed` (yes); strategy 5.3 predicate "reached a completed state" | erase commands with `commandState` and `dateCompleted` confirm the wipe | Change to partial on every Apple vendor. Apple's completion state is an acknowledgement sent before the erase, never retried; Mac `Default` can report `Error` and erase, `DoNotObliterate` can report `Acknowledged` and not erase. Require a corroborating signal (G3) | [10][44] |
| jamf-pro.md 8 "Managed is not supervised" | erase behaviour differs for unsupervised devices | `EraseDevice` needs no supervision on any platform; only User Enrollment forbids it. Supervision gates Lost Mode, Activation Lock management, update deferrals and many restrictions | [10][12][13][18] |
| jamf-pro.md 1, 3 step 5, 5.1 `devices.screen_lock` | screen lock comes from a profile with a screen saver payload | Also from the passcode payload `maxInactivity` (macOS converts it to screen saver settings) and, from OS 27, mainly from the DDM passcode configuration. Verity must look for all three | [17][20][21][3] |
| jamf-pro.md 4 "SOFTWARE_UPDATES lists pending updates", kandji.md 5.1 "Pending updates not read" | the MDM can list available and pending updates | From OS 27 Apple removed `AvailableOSUpdates` and `OSUpdateStatus`; pending update data now comes only from DDM status items (supervised Macs; supervised or device enrolled iOS). Whether Jamf and Kandji fill these from DDM for OS 27 devices: U, test on fixtures | [3][14][15][16] |
| jamf-pro.md 4 `security.activationLockEnabled` and mobile fields | Activation Lock state is a reliable inventory field | Apple deprecated the device key in iOS 16 and macOS 13; cross check with Apple Business `activationLockStatus` | [4][7][67] |
| kandji.md 5.1 `devices.disk_encrypted` | iOS data protection follows passcode: read from details (unverified) | Apple's rule is explicit: data protection needs `HardwareEncryptionCaps` 3 and `PasscodePresent` true; a vendor must expose both or the result is `insufficient` | [6] |
| strategy 5.3 `devices.recovery_key_escrowed` predicate | "a recovery key for the OS volume is held by the MDM" can be read | Apple exposes only "has a key" flags and the encrypted key itself; escrow can be shown only by the vendor's record of receiving it, and an escrow payload installed after FileVault was on is silently skipped. Add: evidence must name the vendor flag used; "has key" alone is `fail` for escrow, not `pass` | [6][22][42] |
| BRIEF dictionary `hardware_ids`, strategy 6 match keys | IMEI and MEID are device queries | Removed from the top level DeviceInformation query in iOS 26; available through `ServiceSubscriptions` (iOS 12) and Apple Business `imei`, `meid` | [4][7][64] |
| Task framing and BRIEF wording | "Apple Business Manager API (announced 2025)" | The product is now Apple Business and the reference is the Apple Business API (2.8, 4 November 2026) at `developer.apple.com/documentation/applebusinessapi`; the old path returns 404 | [60][62][71] |

Cross checks with sibling round 2 files (not round 1; listed so they can be aligned):
- mdm/05-process.md 5.6 "Wipe possible" macOS cell says "full erase when supervised or company owned": Apple
  allows erase on any Mac channel except User Enrollment, supervision is not required [10].
- market-and-audit.md: the User Enrollment passcode limit marked "current behaviour unverified" is confirmed
  by Apple's current schema (6 digit, non simple, forced PIN) [20][17]. Its note that Activation Lock and
  Lost Mode are not in the User Enrollment command lists is consistent with [12][13].

## 8. Sources

All fetched 2026-11-26. Apple's schema files are on the `release` branch of Apple's own repository
`github.com/apple/device-management`, which Apple's deployment guide links as the Device Management Client
Schema project [1].

1. Apple device management schema, README (release matches OS 27.2): https://github.com/apple/device-management/tree/release
2. Schema definitions (meaning of supervised, userenrollment modes, allowed-enrollments): https://github.com/apple/device-management/blob/release/docs/schema.md
3. Schema CHANGES (27.0 removals and deprecations, 27.2 additions): https://github.com/apple/device-management/blob/release/CHANGES.md
4. DeviceInformation command schema (queries, access rights, UE modes): https://github.com/apple/device-management/blob/release/mdm/commands/information.device.yaml
5. SecurityInfo command schema (per key platforms and UE modes): https://github.com/apple/device-management/blob/release/mdm/commands/information.security.yaml
6. SecurityInfoResponse.SecurityInfo and sub dictionaries (ManagementStatus, FirewallSettings, SecureBoot): https://developer.apple.com/documentation/devicemanagement/securityinforesponse/securityinfo-data.dictionary
7. DeviceInformationResponse.QueryResponses (deprecations, removals): https://developer.apple.com/documentation/devicemanagement/deviceinformationresponse/queryresponses-data.dictionary
8. InstalledApplicationList and ManagedApplicationList schemas: https://github.com/apple/device-management/blob/release/mdm/commands/application.installed.list.yaml and https://github.com/apple/device-management/blob/release/mdm/commands/application.managed.list.yaml
9. ProfileList schema: https://github.com/apple/device-management/blob/release/mdm/commands/profile.list.yaml
10. EraseDevice schema (ObliterationBehavior, ReturnToService, response behaviour): https://github.com/apple/device-management/blob/release/mdm/commands/device.erase.yaml
11. DeviceLock schema: https://github.com/apple/device-management/blob/release/mdm/commands/device.lock.yaml
12. EnableLostMode and DisableLostMode schemas: https://github.com/apple/device-management/blob/release/mdm/commands/device.lostmode.enable.yaml and https://github.com/apple/device-management/blob/release/mdm/commands/device.lostmode.disable.yaml
13. ActivationLockBypassCode schema: https://github.com/apple/device-management/blob/release/mdm/commands/device.activationlock.bypasscode.yaml
14. Removed update commands and profile (AvailableOSUpdates, OSUpdateStatus, ScheduleOSUpdate, SoftwareUpdate): https://github.com/apple/device-management/blob/release/mdm/commands/system.update.available.yaml, https://github.com/apple/device-management/blob/release/mdm/commands/system.update.status.yaml, https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.SoftwareUpdate.yaml
15. Removed commands and profiles: https://developer.apple.com/documentation/devicemanagement/removed-commands-and-profiles
16. DDM status items (passcode.is-compliant, passcode.is-present, diskmanagement.filevault.enabled, mdm.enrollment-type, mdm.is-shared-ipad, device.identifier.*, device.operating-system.*, device.model.*, softwareupdate.*, management.declarations, app.managed.list): https://github.com/apple/device-management/tree/release/declarative/status ; index: https://developer.apple.com/documentation/devicemanagement/status-items
17. DDM passcode settings configuration: https://github.com/apple/device-management/blob/release/declarative/declarations/configurations/passcode.settings.yaml
18. DDM software update settings and specific enforcement: https://github.com/apple/device-management/blob/release/declarative/declarations/configurations/softwareupdate.settings.yaml and https://github.com/apple/device-management/blob/release/declarative/declarations/configurations/softwareupdate.enforcement.specific.yaml
19. DDM disk management settings: https://github.com/apple/device-management/blob/release/declarative/declarations/configurations/diskmanagement.settings.yaml
20. Passcode payload (deprecated in 27; UE behaviour): https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.mobiledevice.passwordpolicy.yaml
21. Screen saver payloads: https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.screensaver.yaml and https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.screensaver.user.yaml
22. FileVault recovery key escrow payload: https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.security.FDERecoveryKeyEscrow.yaml
23. FileVault payload and RotateFileVaultKey: https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.MCX.FileVault2.yaml and https://github.com/apple/device-management/blob/release/mdm/commands/rotate.file.vault.key.yaml
24. CheckOut and Authenticate check in: https://github.com/apple/device-management/blob/release/mdm/checkin/checkout.yaml and https://github.com/apple/device-management/blob/release/mdm/checkin/authenticate.yaml
25. UserList schema: https://github.com/apple/device-management/blob/release/mdm/commands/user.list.yaml
26. Sending MDM commands to a device: https://developer.apple.com/documentation/devicemanagement/sending-mdm-commands-to-a-device
27. Handling NotNow status responses: https://developer.apple.com/documentation/devicemanagement/handling-notnow-status-responses
28. Dealing with inactive managed devices and invalid push tokens: https://developer.apple.com/documentation/devicemanagement/dealing-with-inactive-managed-devices-and-invalid-push-tokens
29. Leveraging the declarative management data model; Integrating declarative management: https://developer.apple.com/documentation/devicemanagement/leveraging-the-declarative-management-data-model-to-scale-devices and https://developer.apple.com/documentation/devicemanagement/integrating-declarative-management
30. Enrollment methods for Apple devices (versions, supervision, capability table): https://support.apple.com/guide/deployment/enrollment-methods-for-apple-devices-dep08f54fcf6/web
31. About Apple device supervision: https://support.apple.com/guide/deployment/about-device-supervision-dep1d89f0bff/web
32. Device Enrollment and device management: https://support.apple.com/guide/deployment/device-enrollment-and-device-management-depd1c27dfe6/web
33. Account-driven enrollment methods (data separation, unenrolment): https://support.apple.com/guide/deployment/account-driven-enrollment-methods-dep4d9e9cd26/web
34. User Enrollment and device management: https://support.apple.com/guide/deployment/user-enrollment-and-device-management-dep23db2037d/web
35. Device management service User Enrollment information (payloads, commands, queries): https://support.apple.com/guide/deployment/device-management-service-user-enrollment-dep6ae3f1d5a/web
36. Automated Device Enrollment and device management: https://support.apple.com/guide/deployment/automated-device-enrollment-management-dep73069dd57/web
37. Shared iPad overview: https://support.apple.com/guide/deployment/shared-ipad-overview-dep9a34c2ba2/web
38. Enforce password policies: https://support.apple.com/guide/deployment/enforce-password-policies-depeadc2af0b/web
39. Passcode payload settings: https://support.apple.com/guide/deployment/passcode-payload-settings-dep4d6a472a/web
40. Passcode declarative configuration: https://support.apple.com/guide/deployment/passcode-declarative-configuration-depf72b010a8/web
41. Intro to FileVault: https://support.apple.com/guide/deployment/intro-to-filevault-dep82064ec40/web
42. Manage FileVault with device management: https://support.apple.com/guide/deployment/manage-filevault-with-device-management-dep0a2cb7686/web
43. Use secure token, bootstrap token, and volume ownership: https://support.apple.com/guide/deployment/use-secure-and-bootstrap-tokens-dep24dbdcf9e/web
44. Erase Apple devices: https://support.apple.com/guide/deployment/erase-devices-dep0a819891e/web
45. Lock and locate Apple devices: https://support.apple.com/guide/deployment/lock-and-locate-devices-depb980a0be4/web
46. Activation Lock on Apple devices: https://support.apple.com/guide/deployment/activation-lock-depf4ab94ef1/web
47. Intro to declarative device management (status channel, 24 hour full report): https://support.apple.com/guide/deployment/intro-to-declarative-device-management-depb1bab77f8/web
48. Declarative status reports: https://support.apple.com/guide/deployment/declarative-status-reports-depd90ee8a5f/web
49. About software updates (older versions not fully patched): https://support.apple.com/guide/deployment/about-software-updates-depc4c80847a/web
50. Install and enforce software updates: https://support.apple.com/guide/deployment/install-and-enforce-software-updates-depd30715cbb/web
51. Background Security Improvements: https://support.apple.com/guide/deployment/background-security-improvements-dep93ff7ea78/web
52. Security queries: https://support.apple.com/guide/deployment/security-queries-dep5872f7b3c/web
53. Device information queries: https://support.apple.com/guide/deployment/device-information-queries-depa9e8e14a4/web
54. Installed app queries and operating system queries: https://support.apple.com/guide/deployment/installed-app-queries-dep5bada31d1/web and https://support.apple.com/guide/deployment/operating-system-queries-dep8b8b23369/web
55. Use Return to Service: https://support.apple.com/guide/deployment/use-return-to-service-for-apple-devices-dep17cb455a0/web
56. Firewall payload settings: https://support.apple.com/guide/deployment/firewall-payload-settings-dep8d306275f/web
57. Apple security releases (published 18 November 2026): https://support.apple.com/en-us/100100
58. Apple Platform Security, Data Protection overview: https://support.apple.com/guide/security/data-protection-overview-secf6276da8a/web
59. Apple Platform Security, Passcodes and passwords: https://support.apple.com/guide/security/passcodes-and-passwords-sec20230a10d/web
60. Apple Business API reference (2.8; `applebusinessmanagerapi` path returned 404): https://developer.apple.com/documentation/applebusinessapi
61. Implementing OAuth for the Apple School Manager and Apple Business API: https://developer.apple.com/documentation/apple-school-and-business-manager-api/implementing-oauth-for-the-apple-school-manager-and-apple-business-api
62. Apple School Manager and Apple Business APIs changelog: https://developer.apple.com/documentation/apple-school-and-business-manager-api/apple-school-manager-and-apple-business-api-changelog
63. Get Organization Devices: https://developer.apple.com/documentation/applebusinessapi/get-org-devices
64. OrgDevice attributes and relationships: https://developer.apple.com/documentation/applebusinessapi/orgdevice/attributes-data.dictionary and https://developer.apple.com/documentation/applebusinessapi/orgdevice/relationships-data.dictionary
65. Get Device Management Services; MdmServer attributes; MdmServerStatus: https://developer.apple.com/documentation/applebusinessapi/get-mdm-servers, https://developer.apple.com/documentation/applebusinessapi/mdmserver/attributes-data.dictionary, https://developer.apple.com/documentation/applebusinessapi/mdmserverstatus
66. Device serials for a service; assigned service for a device: https://developer.apple.com/documentation/applebusinessapi/get-all-device-ids-for-an-mdmserver and https://developer.apple.com/documentation/applebusinessapi/get-the-assigned-server-id-for-an-orgdevice
67. Activation Lock status endpoint, attributes, type: https://developer.apple.com/documentation/applebusinessapi/get-the-activation-lock-status-information-for-an-orgdevice, https://developer.apple.com/documentation/applebusinessapi/activationlockstatus/attributes-data.dictionary, https://developer.apple.com/documentation/applebusinessapi/activationlocktype
68. Built in management devices and details: https://developer.apple.com/documentation/applebusinessapi/get-apple-mdm-enrolled-devices, https://developer.apple.com/documentation/applebusinessapi/mdmdevice/attributes-data.dictionary, https://developer.apple.com/documentation/applebusinessapi/mdmdevicedetail/attributes-data.dictionary, https://developer.apple.com/documentation/applebusinessapi/deviceerasestatus
69. Get Audit Events: https://developer.apple.com/documentation/applebusinessapi/get-audit-events
70. Apple Business, Create an Apple Business API account (data access table, roles, key download): https://support.apple.com/guide/business/create-an-apple-business-api-account-axm33189f66a/web
71. Apple Business, Intro to roles and permissions (custom roles, Device API Manager, migration from Apple Business Manager): https://support.apple.com/guide/business/intro-to-roles-and-permissions-axm97dd59159/web
72. Apple Business, Intro to Apple Business; Manage the built in device management service; Intro to device management services: https://support.apple.com/guide/business/intro-to-apple-business-axm7909096bf/web, https://support.apple.com/guide/business/manage-the-built-in-device-management-service-axmc7864dd73/web, https://support.apple.com/guide/business/intro-to-device-management-services-axm659f6bd48/web

## 9. Proposed new dictionary keys

| # | Key | Values | Check that uses it | Source |
|---|---|---|---|---|
| P1 | `os_supplemental_version` | Background Security Improvement letter and build | `devices.os_current`: a device on the right minor but without the current improvement is behind | [4][16][51] |
| P2 | `passcode_policy_assigned` | boolean plus origin (profile, declaration) and `active`/`valid` | `devices.screen_lock` and any passcode check: compliance counts only when a policy is assigned (G1) | [9][16][17] |
| P3 | `purchase_record` | `in_purchase_program`, `purchase_source_type`, `assigned_service`, `added_at`, `released_at` | new `devices.purchased_are_enrolled`: every Apple Business device assigned to an active service and present, in contact, in that MDM; and completeness for `devices.enrolled` | [63][64][65][66] |
| P4 | `activation_lock_type` | org, user, none, unknown | new `devices.activation_lock_org_controlled`: no company device locked to a personal Apple Account; feeds `devices.leaver_devices_recovered` | [46][67] |
| P5 | `erase_method` and `erase_ack_status` | eacs, obliteration, unknown; acknowledged, error, not_now, pending | `devices.remote_wipe` (method recorded, not failed) and `devices.wipes_confirmed` (G3) | [4][10][44] |
| P6 | `bootstrap_token_escrowed` and `user_approved_mdm` | boolean, macOS | `devices.remote_wipe` (EACS on Apple silicon) and FileVault enforcement feasibility | [6][23][43][44] |
| P7 | `enrolment_channel` value `account_driven_device` | split from `user_initiated_device` | ownership defaults: account driven Device Enrollment is meant for company devices yet can be personal; a separate value keeps the D-DEV-7 rule auditable | [30][33] |
| P8 | `declaration_states` | list of identifier, type, `active`, `valid`, reasons | policy assigned evidence for screen lock, updates and removable storage from OS 27 | [16][29] |

## Claim count

Status marks in this file: 137 verified (V, each naming its source ids; several rows bundle more than one
fact under one mark) and 18 unverified (U, each with its reason). The ten corrections in section 7 cite
their sources directly and are not counted again.
