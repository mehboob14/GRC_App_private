# Research round 2: Apple focused MDMs (Jamf Pro, Iru, Mosyle, Addigy, SimpleMDM)

Brief: [BRIEF.md](BRIEF.md). Round 1: [../../mdm-and-endpoint-strategy.md](../../mdm-and-endpoint-strategy.md),
[../../connectors/jamf-pro.md](../../connectors/jamf-pro.md), [../../connectors/kandji.md](../../connectors/kandji.md),
[../../verification/devices-hr.md](../../verification/devices-hr.md). This file extends round 1 and repeats a round 1
fact only where it changes. Source ids are `[n]` (section 12). Sections 2 and 3 hold the visibility matrices,
4.3, 5.3, 7.2 and 8 the field maps, 4.2, 5.2, 7.1 and 8 the credentials, 4.5 to 4.7 and 5.4 to 5.5 limits and
gotchas, 11 the corrections.

Notation. **V [n]**: read in this session on the official page or file `[n]`. **U**: unverified, with the reason.
**T**: a third party page (a GRC competitor or a community project); it supports claims about that third party
only, so for the vendor it counts as U. Verity rule: a reading Verity proposes, not a vendor fact.

## 1. Scope

| Item | Covered |
|---|---|
| Products, in depth order | Jamf Pro (cloud and self hosted), the Jamf Platform API gateway (only for Compliance Benchmarks and Blueprints), Jamf School and Jamf Now (short); Iru Endpoint Management (formerly Kandji); Mosyle Business and Mosyle Fuse; Addigy; SimpleMDM |
| API versions read | Jamf Pro API spec 11.34.0 (`info.version` on [9]); computers inventory v4 (added 11.30.0) [3]; mobile devices v2 detail [7]; MDM commands v2 [8]; Classic API only for configuration profiles [14][15]. Platform API gateway (GA) [18][19]. Iru Endpoint Management API 1.0.0, OpenAPI 3.0 file [37]. Addigy API v2, Swagger 2.0 file [45]. SimpleMDM API v1 [48]. Mosyle: no public reference exists |
| Platforms | macOS, iOS, iPadOS for all five. tvOS and visionOS only where a field says so. Iru's Windows and Android support is out of scope here (its API lists Apple families only [37]) |
| Apple channels | Automated Device Enrollment (ADE), profile based device enrolment, account driven device enrolment, account driven user enrolment (section 2) |
| Date read | 2026-11-26. The Iru OpenAPI file and the Addigy Swagger file were downloaded and parsed in this session; every other page was fetched in this session |
| Excluded | Any write, any device command, recovery key or PIN material, location, phone numbers. Jamf Protect, Iru EDR and vulnerability products (endpoint protection research). Hexnode, Fleet and other Jamf competitors beyond SimpleMDM: not researched |

## 2. Apple rules every product inherits

What an Apple MDM can see is capped by the enrolment channel, whatever the vendor. Apple's own table
(published 28 January 2025) [30]:

| Ability | ADE | Device enrolment (profile or account driven) | Account driven user enrolment |
|---|---|---|---|
| Dictionary `enrolment_channel` | `automated_company` | `user_initiated_device` | `byod_account_driven` |
| Supervised on enrolment | yes | Mac yes; iPhone, iPad no | no |
| Read serial number and other unique ids | yes | yes | no |
| Erase the whole device | yes | yes | no (managed data only) |
| Enforce and manage FileVault | yes | yes | no |
| List every installed app | yes | yes | no (managed apps only) |
| Require a passcode / a complex one | yes / yes | yes / yes | yes / no |
| Manage Activation Lock, Managed Lost Mode (iOS) | yes | no | no |
| Query location | no | no | no |

Apple protocol facts that change checks on every product below:

| Fact | Effect on Verity | Status |
|---|---|---|
| The EraseDevice command needs neither supervision nor ADE, is forbidden on user enrolment, and needs the erase access right in the MDM profile | `devices.remote_wipe` reads the channel, not supervision or bootstrap token | V [31] |
| On a Mac with Apple silicon or T2 (macOS 12+), the fallback setting changes the reply: with `Default` the device replies Error and still erases; with `ObliterateWithWarning` it replies Acknowledged and then erases; with `DoNotObliterate` it replies Error and does not erase. The device answers once and does not retry a failed erase | an erase command's state alone never proves the outcome (see `devices.wipes_confirmed` per product) | V [31][45] |
| DDM status item `passcode.is-compliant` reads true when the device has no passcode policy at all | a compliant reading without an assigned passcode policy proves nothing | V [36] |
| `passcode.is-present` and `passcode.is-compliant` exist on iOS 16+ (including user enrolment), not on macOS | Macs need another screen lock source | V [36] |
| `diskmanagement.filevault.enabled` status exists on macOS 14+ for supervised and local enrolments | a vendor neutral FileVault signal where the MDM exposes DDM status | V [36] |
| `mdm.enrollment-type` status (none, supervised, device, user) arrives in OS 27 | lets Verity read the channel from the device itself on current OS versions | V [36] |
| The legacy passcode payload is marked deprecated in OS 27; its `maxInactivity` is minutes 0 to 15 and macOS turns it into screen saver settings | screen lock evidence moves to the DDM passcode declaration | V [32] |
| DDM passcode settings: `MaximumInactivityInMinutes` (0 to 15), `MaximumGracePeriodInMinutes`; on macOS allowed for supervised and local enrolment only | the idle limit Verity tests is a policy value | V [34] |
| Screen saver payload: `idleTime` (seconds, 0 is never), `askForPassword`, `askForPasswordDelay` (0 is immediate); forbidden on user enrolment | the Mac idle lock value, read from profile content | V [33] |
| DDM disk management settings (macOS 15+): `ExternalStorage` and `NetworkStorage`, each Allowed, ReadOnly or Disallowed | the modern removable storage control on Macs | V [35] |

## 3. Visibility by channel (Jamf Pro; other products in their sections)

Columns: **M-ADE** Mac through ADE; **M-DE** Mac device enrolment; **M-UE** Mac user enrolment; **I-ADE**,
**I-DE**, **I-UE** the same for iPhone and iPad. Cells follow Apple's limits (section 2) and Jamf's fields (4.3).

| Key | M-ADE | M-DE | M-UE | I-ADE | I-DE | I-UE |
|---|---|---|---|---|---|---|
| provider_device_id, device_name, model, os_version, os_build | yes | yes | yes | yes | yes | yes |
| serial_number | yes | yes | no (Apple) | yes | yes | no (Apple) |
| hardware_ids (UDID; IMEI not collected) | yes | yes | no | yes | yes | no |
| ownership | partial (derived) | partial (unknown unless set by rule) | partial (personal by rule) | yes (`deviceOwnershipType`) | yes | yes |
| enrolment_channel, supervised | yes | yes | yes | yes | yes | yes |
| management_state, enrolled_at, last_check_in_at | yes | yes | yes | yes | yes | yes |
| assigned_user_email | yes (if set) | yes (if set) | yes (if set) | yes (if set) | yes (if set) | yes (if set) |
| disk_encryption | yes | yes | no (Apple: no FileVault management) | yes (`dataProtected`) | yes | U |
| recovery_key_escrowed | yes | yes | no | n/a | n/a | n/a |
| passcode_present, passcode_compliant | no Mac field | no | no | yes | yes | yes (Apple DDM) |
| idle_lock_seconds | partial (profile content) | partial | no (payload forbidden) | partial (profile content) | partial | partial |
| firewall_on, os_integrity | yes | yes | U | partial (jailbreak flag) | partial | U |
| activation_lock_or_frp | yes | yes | U | yes | yes (read only; Apple allows managing it on ADE only) | U |
| removable_storage_blocked | partial (profile) | partial | no | n/a | n/a | n/a |
| local_admin_present | yes | yes | U | n/a | n/a | n/a |
| av_present | partial (XProtect only) | partial | U | n/a | n/a | n/a |
| os_update_available | yes | yes | U | U | U | U |
| installed_apps | yes | yes | no (Apple: managed only) | yes | yes | no |
| managed_apps | U | U | U | yes (`managementStatus`) | yes | yes |
| device.action (wipe) | yes (state caveat) | yes | no (Apple) | yes | yes | no |

## 4. Jamf Pro

### 4.1 Editions, versions and the version ladder

- The API ships with Jamf Pro, cloud and self hosted. Which commercial packages include it is not stated on the
  pages read (U). Jamf School and Jamf Now are separate products (4.10).
- Computer inventory versions move fast. `/v1/computers-inventory` was deprecated in 11.20.0 [6], `/v2` in
  11.23.0 [5], `/v3` in 11.30.0 in favour of `/v4` [4][3]. No removal dates are given (V [4][5][6]).
- v4 renamed `general.lastContactTime` to `general.lastContact`, removed `general.lastReportedIp`, and added
  `general.lastCheckIn` (V [3]). Code that reads the old name gets nothing, silently.
- Verity rule: read `GET /api/v1/jamf-pro-version` (needs only a valid token, V [10]) on every run, then call v4 on
  11.30.0 or later, v3 on 11.23 to 11.29, v2 on 11.20 to 11.22, v1 below that, and map the contact field by version.
- The mobile device detail endpoint `/v2/mobile-devices/detail` is not marked deprecated (V [7]).

### 4.2 Read only credential, step by step (Jamf Pro API Roles and Clients)

1. Settings, System, API Roles and Clients (path and 10.49.0 minimum confirmed in round 1).
2. New API role "Verity read only" with exactly these privileges:

| Privilege | Needed for | Status |
|---|---|---|
| Read Computers | `/v4/computers-inventory`, Classic `computercommands` and `computerhistory` | V [1][14] |
| Read Mobile Devices | `/v2/mobile-devices/detail`, Classic `mobiledevicecommands` | V [7][14] |
| Read Computers plus Read Mobile Devices (both) | DDM status items `/v1/ddm/{clientManagementId}/status-items` | V [9] |
| View MDM command information in Jamf Pro API | `/v2/mdm/commands` (wipe history) | V [8] |
| Read macOS Configuration Profiles | Classic `osxconfigurationprofiles` (screen saver, passcode, media payloads) | V (round 1 S13) |
| Read Mobile Device Configuration Profiles | Classic `mobiledeviceconfigurationprofiles` (iOS passcode payload) | V [14] |

3. New API client "Verity", assign the role, enable it, generate the secret (shown once). Set a short access token
   lifetime; the integration object carries `accessTokenLifetimeSeconds`, no secret expiry field (V [13]). Whether a
   client secret ever expires is not stated (U).
4. Paste the Jamf Pro URL, client id and secret into Verity. Adding a role to an existing client needs a secret
   rotation; editing a role's privileges applies to new tokens at once (round 1, V [12]).

Never granted or called: `View Disk Encryption Recovery Key` and the routes `/v4/computers-inventory/{id}/filevault`,
`/filevault`, `/view-device-lock-pin`, `/view-recovery-lock-password` (exist, V [1][3]); any Send command, erase or
remove MDM profile privilege (`/v4/computers-inventory/{id}/erase` exists, V [3]).

**Platform API gateway alternative.** A Jamf Account integration (account.jamf.com, Integrations, Create
integration) with `devices:read`, `device-actions:read`, `configuration-profiles:read` (V [18][20]). Read Computers
and Read Mobile Devices collapse into one `devices:read`; erase, unmanage and remove profile sit in a separate
`destructive-device-actions` capability (V [20]). Integrations, and so their secrets, are valid for six months
(V [18][19]). Verity rule: use API Roles and Clients for inventory; add a Platform integration only if the customer
wants Compliance Benchmark results (4.4), and warn that it must be recreated twice a year.

### 4.3 Field map

Computers: `GET /api/v4/computers-inventory?section=GENERAL&section=HARDWARE&section=OPERATING_SYSTEM&section=DISK_ENCRYPTION&section=SECURITY&section=USER_AND_LOCATION&section=LOCAL_USER_ACCOUNTS&section=CONFIGURATION_PROFILES&section=APPLICATIONS&section=SOFTWARE_UPDATES&section=PURCHASING`
(Read Computers). Mobile: `GET /api/v2/mobile-devices/detail?section=GENERAL&section=HARDWARE&section=SECURITY&section=USER_AND_LOCATION&section=APPLICATIONS&section=PROFILES&exception-handling=LENIENT`
(Read Mobile Devices). Licence: Jamf Pro, any hosting.

| Key | Computers (v4) | Mobile (v2 detail) | Status |
|---|---|---|---|
| provider_device_id | `id`; `general.managementId` (the id MDM commands and DDM use) | `general.managementId`; the record id field name not confirmed | V [1]; mobile id U |
| serial_number | `hardware.serialNumber` | `hardware.serialNumber` | V [1][7] |
| hardware_ids | `udid`, `hardware.provisioningUdid`, `hardware.macAddress` | `general.udid`, `hardware.wifiMacAddress` (IMEI not requested) | V [1][2][7] |
| hostname | none distinct from `general.name` | n/a | U (no field) |
| device_name | `general.name` | `general.displayName` | V [1][7] |
| manufacturer | `hardware.make` | Apple (implicit) | V [1] |
| model | `hardware.model`, `hardware.modelIdentifier` | `hardware.model`, `hardware.modelIdentifier`, `hardware.modelNumber` | V [1][7] |
| platform | endpoint (macOS); `general.platform` (values not listed); `operatingSystem.name` | endpoint plus model | V [1]; values U |
| os_version, os_build | `operatingSystem.version`, `build`, `supplementalBuildVersion`, `rapidSecurityResponse` | `general.osVersion`, `osBuild`, `osSupplementalBuildVersion`, `osRapidSecurityResponse` | V [1][7] |
| device_class | computer | phone or tablet from model; `general.sharedIpad` marks shared | V [7] |
| ownership | no field. Verity rule: ADE means company; `appleEnrollmentType` user means personal; else the tenant setting. `purchasing.purchased`, `leased` support company | `general.deviceOwnershipType`: Institutional, UserEnrollment, AccountDrivenUserEnrollment, AccountDrivenDeviceEnrollment | V [1][7] |
| enrolment_channel | `general.enrolledViaAutomatedDeviceEnrollment`, `general.appleEnrollmentType` (none, supervised, device, user, unknown), `general.enrollmentMethod.objectType` | `general.appleEnrollmentType`, `general.enrollmentMethodPrestage` (set for ADE prestage), `deviceOwnershipType` | V [1][2][7] |
| supervised | `general.supervised` | `general.supervised` | V [1][7] |
| management_state | `general.remoteManagement.managed`, `general.mdmCapable.capable`; a deleted record disappears | `general.managed`, `security.lostModeEnabled` (lost_mode) | V [1][7] |
| enrolled_at | `general.lastEnrolledDate`, `general.initialEntryDate` | `general.lastEnrolledDate` | V [1][7] |
| last_check_in_at | `general.lastContact` (v4; `lastContactTime` on v1 to v3), `general.lastCheckIn` (new in v4), `general.reportDate` (last inventory) | `general.lastContactDate`, `general.lastInventoryUpdateDate` | V [1][3][7]; meanings not described by Jamf, U |
| provider_compliance_state, compliance_policies | none in inventory; Compliance Benchmark rule results (4.4) | same | V [22] |
| assigned_user_email | `userAndLocation.email` | `userAndLocation.emailAddress` | V [1][7] |
| assigned_user_provider_id | `localUserAccounts[].userAzureActiveDirectoryId` (only with Jamf's Entra integration) | none | V [1]; population U |
| assignment_source | not labelled by Jamf; record `manual` unless a directory lookup filled it | same | U |
| disk_encryption | `diskEncryption.fileVault2Enabled`; `bootPartitionEncryptionDetails.partitionFileVault2State`; `operatingSystem.fileVault2Status` (NOT_APPLICABLE, NOT_ENCRYPTED, BOOT_ENCRYPTED, SOME_ENCRYPTED, ALL_ENCRYPTED); DDM `diskmanagement.filevault.enabled` | `security.dataProtected`, `blockLevelEncryptionCapable`, `fileLevelEncryptionCapable`; `hardwareEncryption` is an integer Jamf does not define | V [1][7][9][36]; integer meaning U |
| encryption_method | FileVault | platform data protection | V (by platform) |
| recovery_key_escrowed | `diskEncryption.individualRecoveryKeyValidityStatus` (VALID, INVALID, UNKNOWN, NOT_APPLICABLE), `institutionalRecoveryKeyPresent` | n/a | V [1] |
| passcode_present, passcode_compliant | none for Macs (`localUserAccounts[].passwordMinLength` and similar are policy fields, meaning U) | `security.passcodePresent`, `passcodeCompliant`, `passcodeCompliantWithProfile` | V [1][7] |
| idle_lock_seconds, idle_lock_origin | profile content: Classic `GET /JSSResource/osxconfigurationprofiles/id/{id}` returns `general.payloads` as a string (format not documented), `scope`; join to installed profiles from `configurationProfiles[]` (`profileIdentifier`, `uuid`, `lastInstalled`). Keys: screen saver `idleTime`, passcode `maxInactivity`. Origin: policy | Classic mobile profiles (Read Mobile Device Configuration Profiles) for `maxInactivity`; installed list `profiles[]`. `passcodeLockGracePeriodEnforcedSeconds` is the grace period, not the idle lock | V [1][7][14][15][32][33]; payload string format U |
| firewall_on | `security.firewallEnabled` | n/a | V [1] |
| os_integrity | `security.sipStatus` (NOT_COLLECTED, NOT_AVAILABLE, DISABLED, ENABLED), `secureBootLevel`, `externalBootLevel`, `gatekeeperStatus`, `attestationStatus`, `lockdownModeEnabled` | `security.jailBreakDetected`, `attestationStatus`, `lockdownModeEnabled` | V [1][7] |
| activation_lock_or_frp | `security.activationLockEnabled`, `security.recoveryLockEnabled` | `security.activationLockEnabled` | V [1][7] |
| removable_storage_blocked | profile content (legacy media keys U); DDM `ExternalStorage` through Jamf Blueprints is not readable per device (4.4) | n/a | U |
| local_admin_present | `localUserAccounts[].admin` | n/a | V [1] |
| av_present, av_realtime_on, av_signatures_current | `security.xprotectVersion` (Apple's built in scanner only) | n/a | V [1] |
| edr_present | an EDR app in `applications[]` (match by `bundleId`), secondary only | n/a | V [1] (field); match rule is Verity's |
| os_update_policy_assigned | not researched | not researched | U |
| os_update_available | `softwareUpdates[]` (`name`, `version`, `packageName`) | DDM `softwareupdate.*` status items through [9] | V [1][9] |
| os_supported | none; Verity keeps its own Apple support table | none | V (absence) [1] |
| browser_versions, installed_apps | `applications[]`: `name`, `bundleId`, `version`, `path`, `macAppStore`, `updateAvailable` | `applications[]`: `identifier`, `name`, `version`, `shortVersion`, `managementStatus` | V [1][7] |
| managed_apps | no managed flag on the computer app list | `applications[].managementStatus` | V [7]; computers U |
| device.action | `GET /api/v2/mdm/commands?filter=command==ERASE_DEVICE;dateSent=ge=...`: `commandType` (ERASE_DEVICE, DEVICE_LOCK, ENABLE_LOST_MODE ...), `commandState` (PENDING, ACKNOWLEDGED, NOT_NOW, ERROR, COMMAND_FORMAT_ERROR), `dateSent`, `dateCompleted`, `client.managementId`, `client.clientType`, `commandError`. No issuer field | same endpoint, `clientType` MOBILE_DEVICE | V [8]; issued_by U (no field) |

DDM status (both platforms): `GET /api/v1/ddm/{clientManagementId}/status-items` returns `statusItems[]` of `key`,
`value` (string) and `lastUpdateTime`; one call per device (V [9]).

### 4.4 Compliance Benchmarks and Blueprints (provider verdict, secondary)

| Feature | What the API exposes | Pass or fail per device | Status |
|---|---|---|---|
| Compliance Benchmarks (mSCP based, from 11.16) | Platform API `GET https://{region}.api.jamfcloud.com/compliance-benchmarks/v1/benchmarks/{id}/devices?rule-id=...`: `deviceId`, `deviceName`, `state` PASSED, FAILED or UNKNOWN; rule stats and a compliance percentage endpoint; permission `compliance-benchmarks:read`; header `X-Environment-Id` | yes, per rule; no timestamp in the result | V [21][22][25] |
| Benchmark prerequisites | Jamf Pro sign in through OIDC SSO in Jamf Account (local users and SAML not supported); the API is titled Beta | | V [22][25][26] |
| Benchmark mechanics | creates policies, profiles, scripts, extension attributes and smart groups in Jamf Pro | | V [26] |
| Blueprints (DDM) | `GET .../blueprints/v1/blueprints/{blueprintId}/report`: only counts `succeeded`, `failed`, `pending`; `blueprints:read` | no (aggregate only) | V [23] |
| Platform device inventory | `GET .../devices/v1/devices`: `id`, `serialNumber`, `lastCheckInTime`, `lastInventoryUpdateTime`, `enrollmentType`, `userId`, `operatingSystemVersion`; page size 1 to 1000; `devices:read` | n/a | V [24]; which products it covers U |

Verity rule: keep benchmark results as `provider_compliance_state` and `compliance_policies` evidence beside Verity's
own checks, never instead of them (a rule's definition is Jamf's, not the control's).

### 4.5 Freshness and history

| Item | Fact | Status |
|---|---|---|
| Mac inventory cadence | collected by a customer policy, usually daily; an extra inventory policy refreshes the report date without resetting the timer | V [11] |
| Mobile inventory cadence | global setting, daily by default, can be weekly or monthly, never more often than daily | V [11] |
| Sync advice | full read at most every 24 hours; between full reads filter computers on `general.reportDate`, mobiles on `lastInventoryUpdateDate`; webhooks for near real time | V [11] |
| History | present state only. Verity keeps its own daily snapshots for "throughout the period" | V (no history fields) [1][7] |
| After a wipe | the computer stays in Jamf Pro and its inventory is unchanged; the MDM profile and Jamf framework are removed | V [16] |
| MDM command retention | not stated; Jamf's log flushing API lists retention policies by qualifier but documents only "policy" logs | U [8][17] |

### 4.6 Limits

No built in rate limit; at most 5 concurrent connections, exponential backoff (round 1, V [11]). Page index starts
at 0, page size defaults to 100, no maximum stated (V [2]). `/v2/mdm/commands` needs at least one filter (round 1).
Platform API: 200 requests a second per client, `x-ratelimit-*` headers, 900 second tokens, region locked tokens,
an environment token can get 403 on product routes (needs a tenant scoped integration) (V [19]).

### 4.7 Gotchas

1. **Version drift.** A v4 tenant read with v3 code (or the reverse) loses the contact time. Treat a missing
   contact field as `error`, never as "out of contact".
2. **Contact is not inventory.** `lastContact` can be today while `reportDate` is a week old (inventory policy set
   weekly). Freshness for state checks uses the inventory date (proposed key, section 10).
3. **Wipe evidence.** `ACKNOWLEDGED` shows the command reached the device, and `ERROR` does not prove it stayed
   intact (Apple fallback, section 2). Inventory does not change after a wipe [16]. Confirm a wipe by a later
   signal: no contact after the command plus a new enrolment of the same serial, or the record retired.
4. **FileVault states.** `fileVault2Enabled` can be true while the boot partition is ENCRYPTING or paused; pass
   only ENCRYPTED, or `fileVault2Status` ALL_ENCRYPTED or BOOT_ENCRYPTED per the owner's rule.
5. **Not collected is not off.** `sipStatus` NOT_COLLECTED and `individualRecoveryKeyValidityStatus` UNKNOWN give
   `insufficient`, not `fail`.
6. **Passcode compliance without a policy reads true** (Apple [36]); require an assigned passcode profile or
   declaration before `passcodeCompliant` counts.
7. **Location inside SECURITY.** The mobile SECURITY section carries `lostModeLocation` with coordinates [7].
   Verity needs the section for passcode and encryption, so the collector must drop that object before storage.
8. **STRICT by default.** The mobile detail call returns 500 for the whole page if one device's data is bad;
   `exception-handling=LENIENT` returns 200 with that section null [7], which Verity records as `insufficient`.
9. **Scope is not installed.** A profile scoped to all computers may not be installed; read the device's
   `configurationProfiles[]` and only then the payload.
10. **Platform integrations expire** after six months [18]; a forgotten renewal turns benchmark evidence into
    `error`.

### 4.8 Checks Jamf Pro can support

| Check | Support | How |
|---|---|---|
| devices.enrolled | yes | managed true and contact within `stale_after_days` |
| devices.disk_encrypted | yes | Mac FileVault fields; iOS `dataProtected` with `passcodePresent` |
| devices.recovery_key_escrowed | yes (Mac) | VALID personal key or institutional key present |
| devices.screen_lock | partial | Mac: installed profile with `idleTime` or `maxInactivity` at or under the limit and a password required; iOS: `passcodePresent` plus an installed passcode profile. No live idle value |
| devices.os_current | yes | OS version and build against the minimum |
| devices.firewall_enabled | yes (Mac) | `security.firewallEnabled` |
| devices.remote_wipe | yes | managed device channel (not user enrolment) [31] |
| devices.wipes_confirmed | partial | ERASE_DEVICE commands plus a later confirming signal (gotcha 3) |
| devices.removable_storage_restricted | partial | legacy media payload in an installed profile (keys U); DDM disk management not readable per device |
| devices.assigned_to_active_staff | yes, with an IdP | email join |
| devices.staff_have_managed_device | yes, with an IdP | person direction |
| devices.leaver_devices_recovered | partial | Verity history plus HR end date |
| EP-03.E permitted software | yes for company Macs and iOS; managed apps only on user enrolment | `applications[]` against the customer's allow or deny list |

### 4.9 Go approach

No official Jamf Go SDK. Jamf's own tools named on the Platform pages are `jamf-cli` and a Terraform provider (V
[18]); their language was not checked (U). Plan: plain REST with `net/http` and `encoding/json`; token by a form
POST to `/api/v1/oauth/token` (client credentials, round 1), renewed before `expires_in`.

### 4.10 Jamf School and Jamf Now

| Product | API | Credential | Status |
|---|---|---|---|
| Jamf School | REST at `https://<school>.jamfcloud.com/api`, Basic auth with `NetworkID:APIKey`; version header `X-Server-Protocol-Version`; key created at Organization, Settings, API with chosen methods; reference at `/api/docs` inside the tenant | a key limited to the device read methods (a read only preset is not described) | V [27][28]; device fields U |
| Jamf Now | no API; only the web console | none | V [29] |

Verity rule: Jamf School is an education product, low priority; Jamf Now customers use the attestation path.

## 5. Iru (formerly Kandji)

### 5.1 Rename, hosts, plans

- The rename and hosts were confirmed in round 1. Re-read: either `api.kandji.io` or `api.iru.com` works for
  migrated tenants, and existing `api.kandji.io` scripts keep working (V [39]). The API overview now shows only the
  tenant URL `<tenant>.api.kandji.io` under "Your organization's API URL" (V [38]).
- The OpenAPI file still says Kandji is changing to Iru and points to Settings, Access for the API URL (V [37]).
- Which plans include the API: still not stated by Iru (U).

### 5.2 Read only credential, step by step

1. Account menu, Access, API tokens, Add Token: name "Verity", description; leave **Enable MCP** off (V [38]).
2. Copy the token (shown once), then choose Configure to set permissions (or Skip) (V [38]).
3. Tick only GET permissions. Permissions are per token, grouped in sections, and the activity log records them as
   method plus route pairs, so one route can be readable but not writable (V [38]). No read only preset is
   described (V [38]).
4. Needed routes: device list, device details (optional), device commands, device library items and status,
   Prism categories in 5.3, users, ADE devices, audit events. Exact labels for commands, Prism, users and audit:
   U (round 1 had the same gap).
5. Never: `/secrets/filevaultkey`, `/secrets/bypasscode`, `/secrets/unlockpin`, `/secrets/recoverypassword`,
   `/details/lostmode` (returns `last_location` coordinates), Prism `cellular` (IMEI, MEID, phone numbers), any
   `/action/*` (V [37]).
6. Deleting the admin who made the token deletes it; suspending them does not (round 1).

### 5.3 Field map

Population: `GET /api/v1/devices` (`limit` required, hard maximum 300, `offset`). Prism: `GET /api/v1/prism/{category}`
(`limit` up to 300, `offset`, JSON `filter` such as `{"apple_silicon":{"eq":true}}`, `blueprint_ids`,
`device_families` Mac, iPhone, iPad, tvOS). Every Prism row carries `device_id`, `serial_number`,
`device__user_email`, `blueprint_name`, `last_collected_at` (V [37]). Licence: U.

| Key | Endpoint and field | Status |
|---|---|---|
| provider_device_id | `device_id` | V [37] |
| serial_number | `serial_number` | V [37] |
| hardware_ids | UDID not in any example read; Prism `cellular` has IMEI but must not be called | U |
| hostname | Prism `device_information.host_name`, `local_hostname` | V [37] |
| device_name | `device_name` | V [37] |
| model | `model`; Prism `model_id`, `model_name` | V [37] |
| platform | `platform` (Mac, iPad, iPhone, AppleTV) | V [37] |
| os_version, os_build | `os_version`; Prism `os_build`, `supplemental_build_version`, `marketing_name` | V [37] |
| device_class | from `platform`; Prism `shared_ipad` | V [37] |
| ownership | no field. Verity rule: a serial listed in `GET /api/v1/integrations/apple/ade/devices` is company owned | V [37] (ADE list); rule is Verity's |
| enrolment_channel | ADE list membership (`mdm_device.enrolled_at`, `profile_status`, `device_assigned_by`); device versus user enrolment not exposed | V [37]; user enrolment U |
| supervised | no documented field (details route has no success schema) | U |
| management_state | `mdm_enabled`, `agent_installed`, `is_missing`, `is_removed`, `lost_mode_status`; ADE `mdm_device.enrollment_status` is an undocumented integer | V [37]; integer meaning U |
| enrolled_at | `first_enrollment`, `last_enrollment`; Prism `first_enrollment_date`, `last_enrollment_date` | V [37] |
| last_check_in_at | `last_check_in`; Prism `last_checkin`, `last_checkin_agent`, `last_checkin_mdm`; agent tries every 15 minutes, up to 30 minutes after a Mac restart | V [37][40] |
| provider_compliance_state, compliance_policies | `GET /api/v1/devices/{id}/status` or `/library-items`: per item `name`, `type`, `status` (PASS and PENDING seen), `reported_at`, `last_audit_log`; blueprint from `blueprint_id`, `blueprint_name`. Console states: success, error, pending, remediated | V [37][41]; full status value list U |
| assigned_user_email, assigned_user_provider_id | device `user` (a string in the example), list filter `user_email_exact`; Prism `device__user_email`, `device__user_id`; `GET /api/v1/users`: `email`, `id`, `active`, `archived`, `device_count`, `integration.type` | V [37] |
| assignment_source | users come from directory integrations; device assignment origin not labelled | V [37]; origin U |
| disk_encryption | list filter `filevault_enabled`; Prism `filevault.status` | V [37] (round 1) |
| recovery_key_escrowed | Prism `filevault.key_escrowed`, `key_type`, `regeneration_needed` | V [37] (round 1) |
| passcode_present, passcode_compliant | no documented field (iOS details have no schema); a Passcode library item's status only | U |
| idle_lock_seconds | only when the customer uses a custom profile: `GET /api/v1/library/custom-profiles/{id}` returns `profile` (the XML payload), `runs_on_mac`, `runs_on_iphone`; built in Screen Saver and Passcode items expose status, not settings | V [37]; built in settings U |
| firewall_on | Prism `application_firewall.status`, `block_all_incoming`, `stealth_mode` | V [37] (round 1) |
| os_integrity | Prism `startup_settings.sip`, `ssv`, `secure_boot_level`, `external_boot_level`, `bootstrap_token_escrowed`; `gatekeeper_and_xprotect.gatekeeper_status` | V [37] |
| activation_lock_or_frp | Prism `activation_lock` category exists, but its example shows only the shared device columns | U (column names) |
| removable_storage_blocked | Prism `installed_profiles.profile_data[].type` (payload types per installed profile); keys only through custom profile content | V [37]; keys U |
| local_admin_present | Prism `local_users`: `username`, `type` ("Standard" in the example; the admin value is not shown), `secure_token`, `filevault_user`, `hidden_user` | V [37]; admin value U |
| av_present, edr_present | library item type `threat-security-policy` with `edr_status.status`, `malware_posture`; Prism `gatekeeper_and_xprotect.xprotect_version` | V [37] |
| os_update_available, os_update_policy_assigned | no OS update field found; a managed OS library item's status only | U |
| browser_versions, installed_apps | Prism `apps`: `name`, `bundle_id`, `version`, `path`, `obtained_from`, `signature`, `team_id` (macOS, iOS, iPadOS, tvOS) | V [37] |
| managed_apps | not distinguished in Prism `apps` | U |
| device.action | `GET /api/v1/devices/{id}/commands`: `command_type`, `status` (integer, meanings undocumented), `date_requested`, `date_completed`, `last_pushed`, `attempts`, `user`, `error_chain`; audit events (`GET /api/v1/audit/events`) record enrolment, deletion and MDM removal | V [37]; status meanings U |

### 5.4 Freshness, history, limits

| Item | Fact | Status |
|---|---|---|
| Rate limit | 10,000 requests an hour per customer, shared by every token and by Iru's own compliance evidence collection; over the limit the body says the limit was exceeded | V [37][38] |
| Paging | devices and Prism: `limit` up to 300 plus `offset`; ADE devices: `page`, 300 a page; users and audit events: cursor; audit events up to 500 a page with `start_date`, `end_date` | V [37] |
| Bulk | Prism export (`POST /api/v1/prism/export`, then a signed URL) supports 12 categories, not `application_firewall`, `filevault`, `cellular` or `certificates` | V [37] |
| Cost per run | Prism is fleet wide: a 1,200 Mac fleet costs about 4 calls per category. Device details, status and commands are per device, so a 3,000 device fleet with three per device calls uses 9,000 of the 10,000 hourly budget | arithmetic on V [37] |
| History | present state, plus `last_changed_at` and `last_collected_at` per Prism row; audit events give lifecycle history, retention not stated | V [37]; retention U |

### 5.5 Gotchas

1. **Copied examples.** The `activation_lock` and `desktop_and_screensaver` examples repeat the device information
   columns, so their real columns are unknown until a fixture is recorded.
2. **Status integers.** Command `status` and ADE `enrollment_status` are integers with no published meaning.
   Treat only `date_completed` as completion, and even then apply Apple's erase caveat (section 2).
3. **Shared budget with a competitor's feature.** Iru's own compliance product draws on the same hourly limit
   [38]; Verity must back off and report `truncated`, not fail checks.
4. **Agent versus MDM.** `agent_installed` without `mdm_enabled` is not managed; `is_missing` is lost contact, not
   retired (round 1).
5. **PII in neighbouring routes.** Lost mode details and Prism `cellular` return location and phone data; the token
   must not hold those routes, so a 403 there is the desired state.

### 5.6 Checks Iru can support

| Check | Support | How |
|---|---|---|
| devices.enrolled | yes | `mdm_enabled`, not `is_removed`, `last_checkin_mdm` fresh |
| devices.disk_encrypted | yes (Mac); iOS U | Prism `filevault.status` |
| devices.recovery_key_escrowed | yes (Mac) | Prism `key_escrowed` |
| devices.screen_lock | partial | custom profile content, or library item PASS with the setting confirmed by a person |
| devices.os_current | yes | `os_version`, `os_build` |
| devices.firewall_enabled | yes | Prism `application_firewall.status` |
| devices.remote_wipe | partial | `mdm_enabled`; user enrolment not exposed (U) |
| devices.wipes_confirmed | partial | erase commands with `date_completed` plus a later signal |
| devices.removable_storage_restricted | partial | installed payload types; keys only from custom profiles |
| devices.assigned_to_active_staff | yes, with an IdP | `user_email` join; Iru `users.active` as a second view |
| devices.staff_have_managed_device | yes, with an IdP | person direction |
| devices.leaver_devices_recovered | partial | Verity history, audit events, HR end date |
| EP-03.E permitted software | yes | Prism `apps` |

Go approach: no official SDK; plain REST against the OpenAPI file [37] (generate types from it or hand write the
few structs). Iru's example scripts live in its support GitHub repository (V [37]).

## 6. Mosyle (Business and Fuse)

| Item | Finding | Status |
|---|---|---|
| Plans with API | the pricing table lists "Integrations with Google, Microsoft, Okta, AD & API" on Fuse, Business Premium and Business Free | V [42] |
| Public reference | none found. Integrators say the reference sits inside the console (Organization, API Integration) | U (T [43][44]) |
| Host and auth | `businessapi.mosyle.com/v1`: an access token from the API Integration page plus a login with a Mosyle admin's email and password returning a bearer token; the education product uses `managerapi.mosyle.com/v2` with a 24 hour bearer token | U (T [44]) |
| Least privilege | a dedicated admin limited to View on every area plus the API integration rights, token generated while signed in as that admin | U (T [43]) |
| Device list | `listdevices` per OS (`mac`, `ios`, `tvos`, `visionos`), `page_size`; fields seen by a community project: `deviceudid`, `serial_number`, `device_name`, `device_model`, `osversion`, `asset_tag`, `tags`, dates as Unix seconds | U (T [44]) |
| Encryption, AV | a GRC vendor states Mosyle Business offers no API for disk encryption or antivirus status | U (T [43]) |
| Last check in, OS version | OS version is in the community field list; a last check in field was not seen | U |

Verity rule: do not build Mosyle until Mosyle supplies its reference (partner or customer copy) and a test tenant.
If the encryption gap is real, Mosyle can support `devices.enrolled` (partly), `devices.os_current` and the people
joins only; everything else stays with the attestation path. Using an admin's password in a connector conflicts with
Verity's credential rules and needs an owner decision (section 9).

## 7. Addigy

### 7.1 API, credential and permissions

- Swagger 2.0 file at `https://api.addigy.com/api/v2/documentation/godoc_swagger.json`, base path `/api/v2`; the
  file says the API gives read and write access to nearly all data; endpoints may be marked Beta; `/oa/` routes
  span child organizations with `multitenancy` (V [45]).
- Auth: an API key in the `x-api-key` header per the file's security definition (V [45]). Addigy's migration guide
  is reported to say bearer token in `Authorization` (U, search summary only [47]); test both on a fixture.
- Steps: Account, Integrations, create an API key (V [45]); the key is shown once (U [47]).
- Permissions are named per operation in its description: **View Devices** (devices and facts, DDM status, device
  compliance status), **View end users** (end user assignments), **View System Events** (events) (V [45]).
  Never: Execute Commands (erase and others), View APNs Certificates (V [45]).
- `GET /api/v2/configuration/permissions` lists the key's permissions as identifiers such as
  `com.addigy.devices.view`, so Verity can refuse a key that holds more than it needs (V [45]).
- Read operations carry `x-mcp-readonly: true` in the file, a usable allow list for the collector (V [45]).
- Plans that include the API: U.

### 7.2 Field map

Main read: `POST /api/v2/o/{organization_id}/devices` with `page` (from 1), `per_page`, `query.filters`
(`audit_field`, `operation`, `value`), `desired_fact_identifiers`; returns `items[]` of `agentid`, `orgid`,
`audit_date`, `agent_audit_date`, `facts{identifier: {value, type, error_msg}}` and `metadata.total` (V [45]).
Fact identifiers are listed at run time by `GET /api/v2/o/{organization_id}/facts` (`identifier`, `name`,
`provider`, `return_type`) (V [45]); the built in identifiers themselves are not in the file (U).
Second read: `POST /api/v2/o/{organization_id}/ddm/devices/statuses` (Apple DDM status reports, `limit` 1 to 2000,
cursor in `X-Next-After`) (V [45]).

| Key | Source | Status |
|---|---|---|
| provider_device_id | `agentid`; DDM `udid` | V [45] |
| serial_number | DDM `device.identifier.serial-number`; a serial fact (filter example) | V [45] |
| device_name, model, os_version, os_build | DDM `device_name`, `device.model.*`, `device.operating-system.version`, `build-version` | V [45] |
| enrolment_channel, supervised | facts "Enrolled via DEP", "User Enrollment", "Has MDM Profile Approved" (display names) | V [46]; identifiers U |
| management_state, last_check_in_at | `audit_date`, `agent_audit_date`; `GET /api/v2/mdm/devices/{device_uuid}` `last_response` (time and status of the last MDM reply) | V [45]; meanings U |
| provider_compliance_state | `GET /api/v2/o/{organization_id}/device/compliance/benchmark/status?agent_id=`: `is_compliant`, `failed_rules[]`, `last_updated` per benchmark (View Devices) | V [45] |
| assigned_user_email | `POST .../end-users/devices/query` (agent to end user) then `.../end-users/query` (`emails[]`, `active`, `external_id`); needs the end users feature (SCIM); per page 1 to 100. The response also has `addresses`: drop | V [45] |
| disk_encryption | DDM `diskmanagement.filevault.enabled` (macOS 14+, supervised); FileVault facts | V [36][45]; fact ids U [47] |
| recovery_key_escrowed | a FileVault escrow fact is reported by Addigy's support pages | U [47] |
| passcode_present, passcode_compliant | DDM `passcode.is-present`, `is-compliant` (iOS); facts "Passcode Present", "Passcode Compliant", "Passcode Compliant with Profiles" | V [36][45][46] |
| idle_lock_seconds | profile reads (`/mdm/configurations/profile/{payload_group_id}`) exist; their permission and payload format not read | U |
| firewall_on | fact "Firewall Enabled", plus block all incoming and stealth mode | V [46]; identifier U |
| os_integrity | facts "Secure Boot Level", "External Boot Level" (macOS 15+ on T2); SIP fact not found | V [46]; SIP U |
| installed_apps, managed_apps | DDM `mdm.app[]` (managed apps) and `package.list`; full app inventory fact not confirmed | V [45]; full list U |
| os_update_available | DDM `softwareupdate.pending-version`, `install-state` | V [45] |
| device.action | no command history route in the v2 file; `POST /api/v2/events/query` (View System Events) returns events with `action`, `result.status`, `date`; whether erase commands are logged there is not stated | V [45] (absence of a history route); erase events U |

Limits: no rate limit and no `per_page` maximum for devices in the file (U). Freshness cadence: U.

### 7.3 Checks Addigy can support

| Check | Support |
|---|---|
| devices.enrolled | partial (fact ids and the meaning of `audit_date` to confirm on a fixture) |
| devices.disk_encrypted | yes on macOS 14+ through DDM status; facts for older Macs (U) |
| devices.recovery_key_escrowed | partial (fact U) |
| devices.screen_lock | partial on iOS (passcode facts, no idle time); Mac U |
| devices.os_current | yes |
| devices.firewall_enabled | yes (fact present; identifier resolved at connect) |
| devices.remote_wipe | partial (enrolment facts) |
| devices.wipes_confirmed | no today: `insufficient` until events are shown to record erases |
| devices.removable_storage_restricted | U |
| devices.assigned_to_active_staff, devices.staff_have_managed_device | partial: only where the end users (SCIM) feature is on |
| devices.leaver_devices_recovered | partial |
| EP-03.E permitted software | partial (managed apps and packages only, until an app fact is confirmed) |

Go approach: no official SDK; plain REST. The Swagger file can generate Go types; keep only the dozen read routes.

## 8. SimpleMDM

| Item | Finding | Status |
|---|---|---|
| Auth | API key as the HTTP Basic user name with an empty password, HTTPS only; key at Settings, API | V [48] |
| Least privilege | keys carry permissions (the docs mention a Device Secrets permission and per resource modify rights); a read only per resource setting is described only by a third party | V [48]; read only setting U (T [49]) |
| Secrets trap | `show_secrets` returns `filevault_recovery_key`, PINs and passwords when the key has Device Secrets; it defaults to false for new keys but **true for existing keys** | V [48] |
| Device list | `GET /api/v1/devices`: `limit` 1 to 100 (default 10), `starting_after`, `has_more`; `include_awaiting_enrollment` defaults to false | V [48] |
| Device fields | `status`, `enrolled_at`, `last_seen_at`, `enrollment_channels`, `os_version`, `build_version`, `model_name`, `serial_number`, `unique_identifier`, `is_supervised`, `is_dep_enrollment`, `is_user_approved_enrollment`, `passcode_present`, `passcode_compliant`, `passcode_compliant_with_profiles`, `filevault_enabled`, `firewall.enabled`, `block_all_incoming`, `stealth_mode`, `system_integrity_protection_enabled`, `is_activation_lock_enabled`, `recovery_lock_password_enabled`, `hardware_encryption_caps`, `os_update{...}`, `managed_apple_id`; also `imei`, `phone_number`, `location_latitude`, `location_longitude` (drop) | V [48] |
| Apps, profiles, users | per device installed apps; profiles list shows only directly assigned profiles (not group inherited); macOS user accounts | V [48] |
| History | `GET /api/v1/logs?serial_number=` (namespace, event type, time, metadata); a wipe unenrolls the device from SimpleMDM; retention and the wipe event name not stated | V [48]; retention U |
| Limits | no account wide rate limit stated; some routes return 429 | V [48] |
| Checks | enrolled yes; disk_encrypted yes (Mac); recovery_key_escrowed no (only the secret itself exists); screen_lock partial (iOS passcode fields; Mac profiles only when directly assigned); os_current yes; firewall_enabled yes; remote_wipe yes (channel fields); wipes_confirmed partial (logs plus unenrolment); removable_storage U; people joins partial (no user email on the device record, only `managed_apple_id`); permitted software yes | V [48] for the fields; feasibility is Verity's reading |
| Go | no official SDK; plain REST | V [48] (none named) |

## 9. Check support across products

| Check | Jamf Pro | Iru | Addigy | SimpleMDM | Mosyle |
|---|---|---|---|---|---|
| devices.enrolled | yes | yes | partial | yes | U |
| devices.disk_encrypted | yes | yes (Mac) | yes (macOS 14+) | yes (Mac) | no (T [43]) |
| devices.recovery_key_escrowed | yes | yes | partial | no | U |
| devices.screen_lock | partial | partial | partial | partial | U |
| devices.os_current | yes | yes | yes | yes | U (likely) |
| devices.firewall_enabled | yes | yes | yes | yes | U |
| devices.remote_wipe | yes | partial | partial | yes | U |
| devices.wipes_confirmed | partial | partial | no | partial | U |
| devices.removable_storage_restricted | partial | partial | U | U | U |
| devices.assigned_to_active_staff | yes (IdP) | yes (IdP) | partial (SCIM) | partial | U |
| devices.staff_have_managed_device | yes (IdP) | yes (IdP) | partial (SCIM) | partial | U |
| devices.leaver_devices_recovered | partial | partial | partial | partial | U |
| EP-03.E permitted software | yes | yes | partial | yes | U |

Decisions this raises for the owner (new, numbered after D-DEV-13):

| # | Decision | Options | Recommended |
|---|---|---|---|
| D-DEV-14 | Jamf Compliance Benchmarks as secondary evidence | read them (Platform integration renewed every six months); ignore | read when the customer already uses them |
| D-DEV-15 | Mosyle | wait for docs; build on community knowledge; never | wait, attestation meanwhile |
| D-DEV-16 | Connectors that need an admin password (Mosyle) | refuse; accept a dedicated limited admin | refuse until a token only method exists |
| D-DEV-17 | Order after Jamf and Iru | Addigy then SimpleMDM; demand driven | demand driven |

## 10. Proposed new dictionary keys

| Key | Why | Check that uses it |
|---|---|---|
| `inventory_reported_at` | last state report, separate from `last_check_in_at` (Jamf `reportDate`, `lastInventoryUpdateDate`; Iru `last_collected_at`; Addigy `audit_date`) | freshness rule for every state check |
| `passcode_policy_present` | Apple reports compliance as true when no policy exists [36] | devices.screen_lock |
| `os_integrity_detail` (SIP, secure boot level, external boot level, attestation) as named sub keys | one boolean hides "not collected" | devices.firewall_enabled neighbour; a future hardening check |
| `bootstrap_token_escrowed` | readable on Jamf, Iru and Addigy; needed for some Apple silicon management, not for erase [31] | none now; evidence context for devices.remote_wipe |
| `device.action.confirmed_by` (command_state, later_signal, none) | erase replies do not prove the outcome [31] | devices.wipes_confirmed, devices.leaver_devices_recovered |
| `provider_record_state` (missing, removed, deleted) | Iru `is_missing`, `is_removed`; Jamf records vanish | devices.enrolled population |

## 11. Corrections to round 1

| File | Claim | Correction | Source |
|---|---|---|---|
| jamf-pro.md 4, 8 | first version of v4 inventory unverified; fall back to v1 on older servers | v4 arrived in 11.30.0; v1 deprecated 11.20.0, v2 11.23.0, v3 11.30.0; use the version ladder in 4.1 | [3][4][5][6] |
| jamf-pro.md 4 | `lastCheckIn` seen in the filter list, not the schema | it is a v4 `general` field added in 11.30.0; `lastContact` replaced `lastContactTime` | [1][3] |
| this brief's own list | v1 and v2 inventory, `lastContactTime`, `lastInventoryUpdate` | v1 and v2 are deprecated; v4 uses `lastContact`; the inventory date is `general.reportDate` (computers) and `lastInventoryUpdateDate` (mobile) | [1][3][7] |
| jamf-pro.md 5.1 | remote wipe needs `mdmCapable` and, on Apple silicon, an escrowed bootstrap token (unverified) | Apple's erase needs neither supervision nor ADE nor a bootstrap token; it is forbidden on user enrolment | [31] |
| jamf-pro.md 5.2, strategy 5.5 | `devices.wipes_confirmed` on Jamf: yes | partial: ACKNOWLEDGED or ERROR does not settle the outcome, and inventory is unchanged after a wipe | [16][31] |
| jamf-pro.md 2.2 | four privileges | add Read Mobile Device Configuration Profiles for iOS passcode payloads; DDM status needs Read Computers and Read Mobile Devices together | [9][14] |
| jamf-pro.md 4 (mobile) | fields kept | add `general.lastContactDate`; `security.hardwareEncryption` is an undefined integer; SECURITY also carries lost mode location to drop; use `exception-handling=LENIENT` | [7] |
| jamf-pro.md S4 | Platform API variant `/v1/tenant/{tenantId}/mdm/commands` | that path form was the beta; at GA the tenant id moved to the `X-Tenant-Id` header | [18][19] |
| kandji.md 1, 2.2 | Prism gives activation lock data | the `activation_lock` example shows only shared device columns, so its fields are unverified | [37] |
| kandji.md 2.1 | token steps | add the Enable MCP toggle (leave off) and the Configure or Skip permissions step | [38] |
| kandji.md 4 | device list fields from "its device example" | they come from the Update Device response example; the list route has no success example; `user` is a string there | [37] |
| kandji.md 4 | Prism categories | 16 categories exist, including `startup_settings` (SIP, secure boot, bootstrap token), `local_users`, `apps`, `cellular` (must not be read) | [37] |
| strategy 5.5 | no Addigy, SimpleMDM or Mosyle column | added in section 9 | [42][45][48] |

## 12. Sources

| # | URL | Supports |
|---|---|---|
| 1 | https://developer.jamf.com/jamf-pro/reference/get_v4-computers-inventory-id | v4 sections and every computer field and enum |
| 2 | https://developer.jamf.com/jamf-pro/reference/get_v4-computers-inventory | list parameters, sort and filter fields, `appleEnrollmentType` |
| 3 | https://developer.jamf.com/jamf-pro/changelog/11300-additions | v4 routes, `lastContact`, `lastCheckIn`, removed `lastReportedIp` |
| 4 | https://developer.jamf.com/jamf-pro/changelog/11300-deprecations | v3 inventory deprecated for v4 |
| 5 | https://developer.jamf.com/jamf-pro/changelog/11230-deprecations | v2 inventory deprecated |
| 6 | https://developer.jamf.com/jamf-pro/changelog/11200-deprecations | v1 inventory deprecated |
| 7 | https://developer.jamf.com/jamf-pro/reference/get_v2-mobile-devices-detail | mobile sections, fields, ownership values, LENIENT mode, lost mode location |
| 8 | https://developer.jamf.com/jamf-pro/reference/get_v2-mdm-commands | command types, states, filters, privilege |
| 9 | https://developer.jamf.com/jamf-pro/reference/get_v1-ddm-clientmanagementid-status-items | DDM status items, privileges, spec version 11.34.0 |
| 10 | https://developer.jamf.com/jamf-pro/reference/get_v1-jamf-pro-version | version endpoint |
| 11 | https://developer.jamf.com/jamf-pro/docs/jamf-pro-api-scalability-best-practices | inventory cadence, sync advice, concurrency |
| 12 | https://developer.jamf.com/jamf-pro/docs/client-credentials | role and secret rotation rules |
| 13 | https://developer.jamf.com/jamf-pro/reference/get_v1-api-integrations | `accessTokenLifetimeSeconds`, no secret expiry field |
| 14 | https://developer.jamf.com/jamf-pro/docs/classic-api-minimum-required-privileges-and-endpoint-mapping | Classic privileges for commands, history, mobile profiles |
| 15 | https://developer.jamf.com/jamf-pro/reference/findosxconfigurationprofilesbyid | profile by id: `payloads` string, scope |
| 16 | https://learn.jamf.com/r/en-US/jamf-pro-documentation-11.30.0/Remote_Commands_for_Computers | wipe keeps the record and inventory; EACS default |
| 17 | https://developer.jamf.com/jamf-pro/reference/get_v1-log-flushing | retention policy schema |
| 18 | https://developer.jamf.com/platform-api/reference/getting-started-with-platform-api.md | Jamf Account integrations, six month validity, token endpoint, headers, tools |
| 19 | https://developer.jamf.com/platform-api/reference/platform-api-fundamentals.md | scopes, 200 requests a second, 900 second tokens, regions, GA |
| 20 | https://developer.jamf.com/platform-api/reference/jamf-pro-permissions-map.md | privilege to capability mapping |
| 21 | https://developer.jamf.com/platform-api/reference/compliance-benchmarks/llms.txt | benchmark report endpoints |
| 22 | https://developer.jamf.com/platform-api/reference/v1getdevicesforbenchmarkrule.md | per device PASSED, FAILED, UNKNOWN; Beta title |
| 23 | https://developer.jamf.com/platform-api/reference/getblueprintstatus.md | blueprint report counts only |
| 24 | https://developer.jamf.com/platform-api/reference/get_v1-devices-1.md | Platform device inventory fields and paging |
| 25 | https://support.jamf.com/en/articles/10932419-compliance-benchmarks-faq | 11.16, OIDC SSO requirement |
| 26 | https://learn.jamf.com/r/en-US/jamf-compliance-benchmarks-configuration-guide/Compliance_Benchmarks | benchmark components, SSO |
| 27 | https://developer.jamf.com/developer-guide/docs/jamf-school | Jamf School URL, auth, version header |
| 28 | https://learn.jamf.com/r/en-US/jamf-school-documentation/Jamf_School_API | Jamf School key creation |
| 29 | https://support.jamf.com/en/articles/11031272-can-i-use-the-jamf-now-api | Jamf Now has no API |
| 30 | https://support.apple.com/guide/deployment/dep08f54fcf6/web | enrolment methods and abilities |
| 31 | https://raw.githubusercontent.com/apple/device-management/release/mdm/commands/device.erase.yaml | erase enrolment rules and reply behaviour |
| 32 | https://raw.githubusercontent.com/apple/device-management/release/mdm/profiles/com.apple.mobiledevice.passwordpolicy.yaml | passcode payload, deprecation in OS 27 |
| 33 | https://raw.githubusercontent.com/apple/device-management/release/mdm/profiles/com.apple.screensaver.yaml | screen saver keys |
| 34 | https://raw.githubusercontent.com/apple/device-management/release/declarative/declarations/configurations/passcode.settings.yaml | DDM passcode keys |
| 35 | https://raw.githubusercontent.com/apple/device-management/release/declarative/declarations/configurations/diskmanagement.settings.yaml and https://developer.apple.com/tutorials/data/documentation/devicemanagement/diskmanagementsettings.json | external storage control |
| 36 | https://github.com/apple/device-management/tree/release/declarative/status (passcode.is-compliant, passcode.is-present, diskmanagement.filevault.enabled, mdm.enrollment-type) | DDM status semantics |
| 37 | https://docs.iru.com/openapi/iru-endpoint-openapi.json | Iru routes, parameters, examples, rate limit |
| 38 | https://docs.iru.com/en/endpoint/api/iru-api-overview | token steps, permissions model, shared limit |
| 39 | https://docs.iru.com/en/iru/platform-overview/iru-brand-update | hosts after the rename |
| 40 | https://docs.iru.com/en/endpoint/devices/device-check-in/troubleshooting-agent-check-ins.md | 15 minute agent check in |
| 41 | https://docs.iru.com/en/endpoint/library/library-items-profiles/library-item-status-activity-timeline.md | library item states |
| 42 | https://business.mosyle.com/pricing | Mosyle plans listing API |
| 43 | https://support.secureframe.com/en/articles/15111581-mosyle | third party: Mosyle admin role, no encryption API |
| 44 | https://github.com/grokability/snipe-it/issues/19790 | third party: Mosyle hosts, login, device fields |
| 45 | https://api.addigy.com/api/v2/documentation/godoc_swagger.json (viewer: https://api.addigy.com/api/v2/documentation/) | Addigy routes, auth header, permissions, DDM status, erase notes |
| 46 | https://addigy.com/blog/new-security-device-facts/ | Addigy MDM security fact names |
| 47 | https://support.addigy.com/hc/en-us/articles/45221168205331-Migration-Guide-API-v1-to-API-v2 | search summary only (page returned 403): bearer header, fact identifiers |
| 48 | https://api.simplemdm.com/v1 | SimpleMDM auth, devices, secrets, logs, limits |
| 49 | https://docs.jupiterone.io/integrations/directory/simplemdm | third party: SimpleMDM read permissions per resource |
