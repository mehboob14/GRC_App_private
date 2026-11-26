# Research round 2: Fleet, NinjaOne, Rippling devices and 1Password Device Trust (Kolide)

Brief: [BRIEF.md](BRIEF.md). Round 1: [../../mdm-and-endpoint-strategy.md](../../mdm-and-endpoint-strategy.md) (section 7,
customers without an MDM), [../../connectors/hr-systems.md](../../connectors/hr-systems.md) (Rippling as an HR
source), [../../verification/devices-hr.md](../../verification/devices-hr.md). Source ids are `[Fn]` Fleet, `[Nn]`
NinjaOne, `[Rn]` Rippling, `[Kn]` Device Trust (section 12). "verified [id]" means read in an official page or
official machine readable spec in this session. "unverified" means not confirmed. "third party [id]" means read
in another vendor's help page, not in the product's own documentation. All reads are dated 2026-11-26.

Verity's rule for every product here: one read only credential, GET requests only, no device commands, no live
queries, no scripts, and no call to any endpoint that returns secrets (recovery keys, passwords).

## 1. Scope

| Product | What was read | Version or date |
|---|---|---|
| Fleet (fleetdm) | REST API reference, global and host audit log references, role based access guide, fleetctl guide, API only token rotation guide, server configuration, disk encryption, lock and wipe, MDM commands, software inventory and ChromeOS guides, the built in policy library, the pricing feature table, the repository licences and the Go client source [F1 to F17] | docs from the `main` branch on 2026-11-26; latest release `fleet-v4.96.0` published 2026-11-24 [F17]. `main` can describe features not yet released |
| NinjaOne | Public API v2 OpenAPI spec (core resources, `info.version` 2.0.9-draft, 254 paths) and the authorization spec, OAuth configuration pages, MDM data and compatibility pages, instance availability page, compare plans page [N1 to N7, N10]; Secureframe and Vanta help pages for setup cross checks [N8][N9] | spec fetched 2026-11-26; NinjaOne pages updated 2025-07-15 to 2026-11-11 |
| Rippling devices (Rippling IT) | REST API reference for `GET /devices/`, `GET /devices/{id}/`, `GET /device-orders/`, software deployments, the scope reference, token rules, rate limits, query parameters and changelog [R1 to R9] | device endpoints added 2026-07-01 [R6] |
| 1Password Device Trust (formerly Kolide) | Device Trust API page, OpenAPI spec version 2026-04-07, checks overview, about, FAQ, product page, mobile checks post [K1 to K7]; Drata's Device Trust guide for check names [K8] | API page published 2026-11-04 [K1] |
| Out of scope | Secureframe, Vanta and Drata agents (covered elsewhere) | |

Platforms: macOS, Windows, Linux, iOS, iPadOS, Android, ChromeOS, as each product supports them.

## 2. Visibility by platform and channel

Cells: yes; partial with the reason; no; unverified. Footnote codes used in cells:
p1 = only through a policy or scheduled report the customer writes in Fleet (Verity reads its result, see 6.1);
p2 = present in the NinjaOne console per NinjaOne's MDM page [N6] but not found in the public API spec [N3];
p3 = Verity derives it, no provider field.

### 2.1 Fleet

Columns: A macOS company (ADE or manual MDM); B Windows company (Autopilot, Entra or manual MDM);
C desktop agent only (fleetd without Fleet MDM: Linux, or a Mac or PC managed by no MDM or another MDM);
D iOS and iPadOS company; E iOS and iPadOS personal (account driven user enrolment); F Android fully managed;
G Android work profile on a personal phone; H ChromeOS (fleetd Chrome extension).

| Key | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| provider_device_id | yes | yes | yes | yes | yes | yes | yes | yes |
| serial_number | yes | yes | yes | yes | no: a temporary enrolment id | yes | no: enterprise specific id | unverified |
| hardware_ids | yes (uuid) | yes (uuid) | yes (uuid) | yes (udid, IMEI) | no (do not collect) | yes (IMEI or MEID) | no: never returned | unverified |
| hostname, device_name | yes | yes | yes | yes | yes | yes | yes | partial: hostname blank unless set in Google Admin |
| manufacturer, model | yes | yes | yes | yes | unverified | yes | unverified | unverified |
| platform, os_version | yes | yes | yes | yes | yes | yes | yes | yes |
| os_build | yes | partial: inside `os_version` | yes | yes | yes | no: empty | no | unverified |
| device_class | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 |
| ownership | yes | yes | no: unknown without MDM | yes | yes | yes | yes | no |
| enrolment_channel | yes | yes | yes (agent_only) | yes | yes | yes | yes | yes (agent_only) |
| supervised | no | n/a | n/a | no: not a host field | no | n/a | n/a | n/a |
| management_state | yes | yes | partial: online, offline, missing only | yes | yes | yes | yes | partial |
| enrolled_at, last_check_in_at | yes | yes | yes | yes | yes | yes | yes | yes |
| provider_compliance_state, compliance_policies | yes (policies) | yes | yes | partial: p1 | partial: p1 | partial: AMAPI posture | partial | partial |
| assigned_user_email | yes | yes | partial: Free mapping only | yes | yes | yes | yes | partial: Chrome profile |
| disk_encryption | yes | yes | partial: Linux unencrypted is omitted | yes | unverified | yes | unverified | unverified |
| encryption_method | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial | partial: p3 | partial | unverified |
| recovery_key_escrowed | yes (Premium) | yes (Premium) | partial: Linux LUKS2 on four distros, Premium | no | no | no | no | no |
| passcode_present | partial: p1 | partial: p1 | partial: p1 | partial: p1 | unverified | yes | unverified | no |
| passcode_compliant | partial: p1 | partial: p1 | partial: p1 | partial: p1 | unverified | partial: posture | unverified | no |
| idle_lock_seconds, idle_lock_origin | partial: p1 | partial: p1 | partial: p1 | no | no | no | no | no |
| firewall_on | partial: p1 | partial: p1 | partial: p1 | no | no | no | no | no |
| os_integrity | partial: p1 (SIP, Gatekeeper) | partial: p1 | partial: p1 | no | no | yes (posture) | partial | no |
| activation_lock_or_frp | unverified | n/a | n/a | partial: a setting, not the state | no | unverified | no | no |
| removable_storage_blocked | partial: p1 | partial: p1 | partial: p1 | no | no | no | no | no |
| local_admin_present | partial: p1 | partial: p1 | partial: p1 | no | no | no | no | no |
| av_present, av_realtime_on, av_signatures_current | partial: p1 | partial: p1 | partial: p1 | no | no | partial: Play Protect on | no | no |
| edr_present | partial: app inventory | partial | partial | no | no | partial | no | no |
| os_update_policy_assigned | yes (Premium) | yes (Premium) | no | yes | unverified | unverified | unverified | no |
| os_update_available | partial: OS CVEs | partial | partial | partial | partial | yes | partial | no |
| security_patch_level | n/a | n/a | n/a | n/a | n/a | yes | yes | n/a |
| os_supported | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 | partial: p3 |
| browser_versions | yes | yes | yes | partial | no | partial | partial | partial |
| installed_apps | yes | yes | yes | yes | partial: Fleet installed apps only | yes | partial: work profile apps only | partial: extensions only |
| managed_apps | yes (Premium) | yes (Premium) | yes (Premium) | yes | yes | yes | yes | no |
| device.action | yes (Premium) | yes (Premium) | partial: Linux script wipe, no wiped state | yes (Premium) | unverified | yes (Free) | yes: work profile removal | no |

Sources for the matrix: host fields, enrolment status values, BYOD identifiers and platform only fields [F1];
encryption omission rule [F1]; escrow scope and Linux distros [F9]; wipe and lock platforms and tiers [F10];
software visibility per platform and BYOD [F12]; ChromeOS limits [F13]; built in policies [F14]; tiers [F7].

### 2.2 NinjaOne

Columns: W Windows agent; M macOS agent; L Linux agent; AN Android MDM; IO iOS and iPadOS MDM.

| Key | W | M | L | AN | IO |
|---|---|---|---|---|---|
| provider_device_id, device_name, hostname | yes | yes | yes | yes | yes |
| serial_number | yes | yes | yes | yes | yes |
| hardware_ids | partial: MAC only | partial | partial | yes (IMEI, MEID) | yes |
| manufacturer, model | yes | yes | yes | yes | yes |
| platform (`nodeClass`) | yes | yes | yes | yes | yes |
| os_version, os_build | yes | yes | yes | partial: only `system.build` in the API | partial: same |
| device_class | yes (workstation, server, VM, chassis type) | yes | yes | partial | partial |
| ownership | no | no | no | partial: p2 | partial: p2 |
| enrolment_channel | yes (agent_only) | yes | yes | partial: p2 | partial: p2 |
| supervised | n/a | n/a | n/a | n/a | partial: p2 |
| management_state | yes (approval status, offline) | yes | yes | yes | yes |
| enrolled_at, last_check_in_at | yes | yes | yes | yes | yes |
| provider_compliance_state | yes (health status) | yes | yes | unverified | unverified |
| assigned_user_email | partial: assigned owner if set | partial | partial | partial | partial |
| disk_encryption, encryption_method | yes (BitLocker per volume) | partial: FileVault on and off events only | no | partial: p2 | partial: p2 |
| recovery_key_escrowed | no | no | no | no | no |
| passcode_present, passcode_compliant | no | no | no | partial: p2 | partial: p2 |
| idle_lock_seconds, firewall_on, os_integrity, removable_storage_blocked, local_admin_present | no | no | no | no | no |
| av_present, av_realtime_on, av_signatures_current | yes (antivirus status) | partial: product dependent, unverified | unverified | no | no |
| os_update_available | yes (pending OS patches) | unverified | unverified | no | no |
| browser_versions, installed_apps | yes | yes | unverified | unverified | unverified |
| device.action | no | no | no | yes (erase activity codes) | yes |

Sources: device schemas, query reports, activity codes [N3]; mobile data in the console [N6]; MDM platforms
[N7]; macOS and Linux encryption gap, third party [N8].

### 2.3 Rippling devices

Columns: RM macOS on Rippling MDM; RW Windows on Rippling MDM; RI iOS and iPadOS on Rippling MDM; OM device
recorded in Rippling but managed by another MDM (`mdm_provider` not `RIPPLING`); UN not enrolled (inventory only).

| Key | RM | RW | RI | OM | UN |
|---|---|---|---|---|---|
| provider_device_id, serial_number, model, platform, os_version | yes | yes | yes | yes | yes |
| hardware_ids, hostname, device_name, manufacturer, os_build | no | no | no | no | no |
| device_class | partial: p3 from platform | partial | partial | partial | partial |
| ownership, supervised, enrolment_channel detail | no | no | no | no | no |
| management_state | yes (enrolment status, lifecycle state) | yes | yes | partial | yes (unenrolled, lifecycle) |
| enrolled_at | no: only record creation | no | no | no | no |
| last_check_in_at | yes (agent and MDM sync times) | yes | partial: agent time unverified on iOS | partial | partial |
| assigned_user_email, assigned_user_provider_id | yes (worker) | yes | yes | yes | yes |
| disk_encryption | yes | yes | unverified | partial: as recorded | unverified |
| encryption_method | partial: p3 FileVault | partial: p3 BitLocker | unverified | partial | no |
| every lock, hardening, protection, update and software key | no | no | no | no | no |
| device.action | partial: pending actions and lifecycle | partial | partial | no | no |

Platforms in the API are only MACOS, WINDOWS, IOS and IPADOS [R1]. Linux and Android are not in the enum.

### 2.4 1Password Device Trust (Kolide)

Columns: DC desktop agent on a company device; DP desktop agent on a personal device; KI Kolide app on iOS;
KA Kolide app on Android.

| Key | DC | DP | KI | KA |
|---|---|---|---|---|
| provider_device_id, device_name, model, platform, os_version | yes | yes | yes | yes |
| serial_number, hardware_ids (hardware UUID) | yes | yes (personal: keep only for matching, policy decision) | partial: may not apply | partial |
| device_class (`form_factor`) | yes | yes | yes | yes |
| ownership | no | no | no | no |
| enrolment_channel | yes (agent_only) | yes (agent_only) | partial: MDM enrolment check if configured | partial |
| management_state | partial: registered, auth state | partial | partial | partial |
| enrolled_at (`registered_at`), last_check_in_at | yes | yes | yes | yes |
| provider_compliance_state, compliance_policies | yes (auth state, checks, issues) | yes | yes | yes |
| assigned_user_email | yes (registered owner) | yes | yes | yes |
| disk_encryption | yes (check result) | yes | no check named | no check named |
| recovery_key_escrowed | unverified | unverified | no | no |
| passcode_present, passcode_compliant | partial: desktop screen lock checks | partial | yes (passcode check) | yes (lock screen check) |
| idle_lock_seconds | unverified | unverified | no | no |
| firewall_on | unverified | unverified | no | no |
| os_integrity | partial: Gatekeeper | partial | yes (jailbreak) | yes (root) |
| av_present, av_realtime_on | partial: Windows Security Center check | partial | no | no |
| os_update_available | yes (up to date checks) | yes | yes | partial: Google Pixel only |
| installed_apps | partial: reporting tables, unverified | do not collect | no | no |
| device.action | no | no | no | no |

Check names come from the tenant's own `GET /checks` (slug, name, platforms) [K2]; the examples above come from
Drata's mapping list, third party [K8], and the mobile checks post [K7].

## 3. Field map

### 3.1 Fleet

Permission for every row: an API only user with the global Observer role [F4][F5]. Endpoints are under
`https://<customer fleet server>/api/v1/fleet/` [F1]. "Premium" means Fleet Premium [F7].

| Key | Endpoint and field | Tier | Caveats | Status |
|---|---|---|---|---|
| provider_device_id | `GET /hosts` `id` | Free | integer, unique per Fleet server | verified [F1] |
| serial_number | `hardware_serial` | Free | personal iOS and Android: an enrolment id, not the serial | verified [F1] |
| hardware_ids | `uuid`; iOS `udid`, `service_subscriptions[].imei`; Android `imei` or `meid` | Free | Android IMEI never returned for personal; read only on company devices | verified [F1] |
| hostname, device_name | `hostname`, `computer_name`, `display_name` | Free | ChromeOS hostname blank by default | verified [F1][F13] |
| manufacturer, model | `hardware_vendor`, `hardware_model`, `hardware_marketing_name`; Android `manufacturer` | Free | | verified [F1] |
| platform | `platform` (`darwin`, `windows`, `ios`, `ipados`, `android`, `chrome`, Linux distro values) | Free | exact Linux values not listed; map by `platform_like` and label | partial: Linux values unverified |
| os_version, os_build | `os_version`, `build`; Android `security_update_version` folded into `os_version` | Free | Windows build sits inside `os_version` | verified [F1] |
| device_class | derived from `platform`, `hardware_model` | Free | no class field; Windows Server excluded by MDM filters but no flag found | unverified (no field found) |
| ownership | `mdm.enrollment_status` (`On (automatic)`, `On (manual)`, `On (personal)`, `On (manual - personal)`, `Pending`, `Off`, null); `mdm.is_personal_enrollment` | Free | `is_personal_enrollment` stays true after a mobile host unenrols | verified [F1] |
| enrolment_channel | same status; `On (automatic)` covers ADE, Autopilot and fully managed Android; agent only when status is `Off` or null and `orbit_version` or `osquery_version` is set | Free; account driven iOS and fully managed Android are Premium | channel mapping is Verity's reading | verified [F1][F7] |
| supervised | no host field found | | only `is_supervised` on enrolment profile settings | unverified (not found) |
| management_state | `mdm.enrollment_status`; `mdm.device_status` (`unlocked`, `locked`, `locking`, `unlocking`, `wiped`, `wiping`) and `mdm.pending_action` with `include_device_status=true`; `status` (`new`, `online`, `offline`, `mia`, `missing`); removal through the `deleted_host` activity | Free | `mia` means not seen for more than 30 days | verified [F1][F2] |
| enrolled_at | `last_enrolled_at` (agent), `last_mdm_enrolled_at` (MDM), `created_at` (first enrolment) | Free | | verified [F1] |
| last_check_in_at | `seen_time`, `last_mdm_checked_in_at`, `detail_updated_at`, `policy_updated_at` | Free | mobile online state is derived from MDM check in | verified [F1] |
| provider_compliance_state, compliance_policies | host `policies[]` (`id`, `name`, `query`, `platform`, `response` pass, fail or empty, `critical`) with `populate_policies=true`; `issues.failing_policies_count`; `GET /global/policies`, `GET /fleets/:id/policies` (Premium) | Free | empty `response` means not run on that host | verified [F1] |
| assigned_user_email | `end_users[].idp_username`, `end_users[].other_emails[]` with `source` (`google_chrome_profiles`, `custom`, `managed_apple_id`) via `populate_end_users=true` | IdP details Premium; mapping Free | Chrome profile mapping is weak | verified [F1][F7] |
| assigned_user_provider_id | `end_users[].idp_id` | Premium | | verified [F1] |
| assignment_source | `idp` when `idp_username` set; else `other_emails[].source` | | mapping to the dictionary values is Verity's | verified [F1] |
| disk_encryption | `disk_encryption_enabled` (omitted when unknown, and omitted for Linux hosts whose root volume reports unencrypted); `mdm.os_settings.disk_encryption.status` (`verified`, `verifying`, `action_required`, `enforcing`, `failed`, `removing_enforcement`); Android `encryption_type` | field Free; enforcement status Premium | omission is never "off" | verified [F1][F9] |
| encryption_method | by platform: FileVault, BitLocker (C: drive with TPM), LUKS2 | | | verified [F9] |
| recovery_key_escrowed | `mdm.encryption_key_available`; `mdm.os_settings.disk_encryption.status` `verified`; activity `escrowed_disk_encryption_key` | Premium | never call `GET /hosts/:id/encryption_key` | verified [F1][F2][F9] |
| passcode_present | Android `passcode_protected`; other platforms through a policy | Free | | verified [F1] |
| idle_lock_seconds, idle_lock_origin | a scheduled report the customer adds, read with `GET /reports/:id/report` (`results[].columns`, `last_fetched`); `managed_policies` gives the policy value, `preferences` or registry gives the device value | Free | Verity cannot add the report itself (read only) | verified [F1] |
| firewall_on, os_integrity, removable_storage_blocked, local_admin_present, av_* | policy results; built in examples: macOS firewall, Windows firewall per profile, SIP, Gatekeeper, antivirus healthy on each desktop OS | Free | the policy SQL is the customer's | verified [F1][F14] |
| os_integrity (Android) | `security_posture`, `security_posture_details[].security_risk`, `play_protect_enabled`, `adb_enabled` | Free | raw AMAPI enums; unspecified values omitted | verified [F1] |
| os_update_policy_assigned | iOS `os_update_minimum_version`, `os_update_deadline`; `GET /config` `mdm.macos_updates`, `mdm.ios_updates`, `mdm.windows_updates` (per fleet on Premium) | Premium | macOS host example shows no minimum field | verified [F1][F7] |
| configuration profiles (weak signal for removable storage and lock) | host `mdm.profiles[]` (`name`, `status`, `operation_type`) on `GET /hosts/:id` | Free | listing profile contents needs Technician or above, so Observer sees names and status only | verified [F1][F4] |
| os_update_available | `GET /os_versions` `vulnerabilities[]`; Android `system_update_status` | Free; CVSS, EPSS, KEV Premium | | verified [F1] |
| security_patch_level | Android `security_update_version` | Free | | verified [F1] |
| installed_apps, browser_versions | `GET /hosts/:id/software` (`name`, `source`, `installed_versions[].version`, `bundle_identifier`, `vulnerabilities`, `signature_information`, `last_opened_at`) | Free | personal mobile: managed or work profile apps only | verified [F1][F12] |
| managed_apps | same endpoint: `software_package`, `app_store_app`, `status` | Premium | | verified [F1][F7] |
| device.action | activities `wiped_host`, `failed_wipe` (Windows only), `locked_host`, `unlocked_host` via `GET /activities` and `GET /hosts/:id/activities`; `GET /commands?host_identifier=` (`request_type`, `status`, `updated_at`); `GET /commands/results`; `mdm.device_status` | wipe of desktops and Apple mobile Premium; Android wipe Free | Linux wipe shows no state | verified [F1][F2][F10][F11] |

Never read from Fleet: `geolocation`, `service_subscriptions` and `telephony_infos` (phone numbers, ICCID), iOS
`organization_info`, `itunes_store_account_hash`, lock time location data, and the secret endpoints in 4.1 [F1][F10].

### 3.2 NinjaOne

Permission for every row: an OAuth client with the `monitoring` scope only [N1]. Base URL
`https://<region>.ninjarmm.com/api/v2` (region host from third party pages, see 4.2). The spec does not state a
scope per operation; all operations list `monitoring`, `management` and `control` together [N3], so that each
GET works with `monitoring` alone is unverified.

| Key | Endpoint and field | Caveats | Status |
|---|---|---|---|
| provider_device_id | `GET /v2/devices-detailed` `id`, `uid` | polymorphic list: `deviceType` (`AgentDevice`, `MdmDevice`, `UnmanagedDevice`, `VMGuest`, NMS and cloud monitors) | verified [N3] |
| serial_number, manufacturer, model | `system.serialNumber`, `system.biosSerialNumber`, `system.manufacturer`, `system.model`; also `GET /v2/queries/computer-systems` | | verified [N3] |
| hardware_ids | MDM `network[].imei`, `network[].meid`; agent `macAddresses` | MDM `network[]` also holds `phoneNumber` and `iccId`: drop them | verified [N3] |
| hostname, device_name | `systemName`, `dnsName`, `netbiosName`, `displayName` | | verified [N3] |
| platform, device_class | `nodeClass` (`WINDOWS_WORKSTATION`, `WINDOWS_SERVER`, `MAC`, `LINUX_WORKSTATION`, `ANDROID`, `APPLE_IOS`, `APPLE_IPADOS`, `AOSP`, `CHROMEOS` and more); `system.virtualMachine`; `references.role.chassisType` | | verified [N3] |
| os_version, os_build | agent `os.name`, `os.buildNumber`, `os.releaseId`, `os.needsReboot`; MDM `system.build` | no OS version field on the MDM schema | verified [N3] |
| management_state | `approvalStatus` (`PENDING`, `STAGED`, `APPROVED`, `DECOMMISSIONED`), `offline`, `maintenance.status` | | verified [N3] |
| enrolled_at, last_check_in_at | `created`, `lastContact`, `lastUpdate` (epoch seconds) | | verified [N3] |
| provider_compliance_state | `GET /v2/queries/device-health` `healthStatus` (`UNKNOWN`, `HEALTHY`, `NEEDS_ATTENTION`, `UNHEALTHY`) | NinjaOne's own rollup | verified [N3] |
| compliance_policies | `policyId`, `rolePolicyId`, `references.policy.name` | policy content not read | verified [N3] |
| assigned_user_email, assigned_user_provider_id | `assignedOwnerUid`, `references.assignedOwner.email`; `GET /v2/user/end-users` (`uid`, `email`, `enabled`, `assignedDeviceIds`) | whether `references` is returned without an expand parameter is unverified | verified [N3] |
| assignment_source | assigned owner = manual; `lastLoggedInUser` (a username) = derived | | partial: semantics unverified |
| disk_encryption, encryption_method | `GET /v2/queries/volumes?include=bl`: `bitLockerStatus.protectionStatus` (`PROTECTED`, `UNPROTECTED`, `UNKNOWN`, `PENDING`), `conversionStatus`, `encryptionMethod` | Windows only. macOS: activity codes `FILEVAULT_ENABLED`, `FILEVAULT_DISABLED` only. No macOS or Linux state, third party [N8] | verified [N3] |
| av_present, av_realtime_on, av_signatures_current | `GET /v2/queries/antivirus-status`: `productName`, `productState`, `definitionStatus`, `version`, `timestamp`; device health threat counts | value sets of `productState` and `definitionStatus` not in the spec | partial: values unverified |
| os_update_available | `GET /v2/queries/os-patches` (pending, failed, rejected: `name`, `severity`, `status`, `kbNumber`); history `GET /v2/queries/os-patch-installs` | | verified [N3] |
| installed_apps, browser_versions | `GET /v2/queries/software` (`name`, `publisher`, `version`, `installDate`, `productCode`, `deviceId`) | MDM device coverage unverified | verified [N3] |
| device.action | `GET /v2/activities` (`activityType` `MDM`, `statusCode` such as `MDM_ERASE_STATUS_CREATED`, `MDM_ERASE_STATUS_UPDATED`, `AOSP_ERASE_DEVICE_STATUS_COMPLETED`, `MDM_LOCK_DEVICE_STATUS_UPDATED`, `MDM_ACTION_DEVICE_STATUS_FAILED`; `activityTime`, `userId`, `deviceId`) | what UPDATED means (done or failed) is in `status` text, values unverified | verified [N3] |
| ownership, supervised, passcode, mobile encryption | not in the spec | shown in the console [N6] | unverified (not found in API) |
| recovery_key_escrowed, idle lock, firewall, integrity, removable storage | not in the spec | custom fields filled by customer scripts are the only route (`GET /v2/queries/custom-fields`) | unverified (not found) |

Never read from NinjaOne: `GET /v2/device/{id}/geolocation/history`, `publicIP`, `network[].phoneNumber`,
`network[].iccId` [N3].

### 3.3 Rippling devices

Base URL `https://rest.ripplingapis.com` (round 1, hr-systems.md R1, R7). Scope `devices.read` [R3].

| Key | Endpoint and field | Caveats | Status |
|---|---|---|---|
| provider_device_id, serial_number, model, platform | `GET /devices/` `id`, `serial_number`, `model`, `platform` (`MACOS`, `WINDOWS`, `IOS`, `IPADOS`) | | verified [R1] |
| os_version | `os_name`, `os_version` | | verified [R1] |
| management_state | `enrollment_status` (`ENROLLED`, `WAITING_FOR_CONNECTION`, `ERROR`, `UNENROLLED`); `is_managed`; `lifecycle_state` (`INIT`, `ACTIVE`, `ACTIVATING`, `LOCKED`, `LOCKING`, `INACTIVE`, `PENDING_MDM`, `CLEANING`, `READY`, `DECOMMISSIONING`, `DECOMMISSIONED`, `FULL_WIPING`, `FULL_WIPED`, `E_CYCLED`, `SOLD`, `MDM_LOCKED`, `LOST`, `LOST_PLAYING_SOUND`) | `SOLD` added 2026-11-05 as a breaking change [R6] | verified [R1][R6] |
| enrolment_channel | `mdm_provider` (`RIPPLING`, `INTUNE`, `JAMFCLOUD`, `KANDJI`, `FLEETDM` and others; null when not managed) | no ADE or manual distinction | verified [R1] |
| last_check_in_at | `last_checkin_at` (Rippling agent), `last_mdm_sync_at` | | verified [R1] |
| assigned_user_provider_id, assigned_user_email | `worker_id`, then `GET /workers/{id}` `work_email` and `status` with `workers.read` | do not use `expand=worker`: the worker object carries sensitive HR fields | verified [R1][R2][R3] |
| disk_encryption | `is_encrypted` (FileVault on macOS, BitLocker on Windows) | iOS meaning not stated; a null can mean redacted | verified [R1][R8] |
| device.action | `pending_actions` (expand) or `pending_actions_id`: `action_type` (for example `FULL_WIPE`, `SOFT_WIPE`, `LOCK_DEVICE`, `ENABLE_LOST_MODE`, `ROTATE_FILEVAULT_KEY`), `state`, `queued_at` | queued actions only, no completed history | verified [R1] |
| leaver return evidence | `GET /device-orders/` (`device-orders.read`): `order_type` (for example Warehouse Return), `status` (`CREATED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELING`, `CANCELED`), `worker_id`, `completed_at` | no device id on the order | verified [R7] |
| managed software catalogue | `GET /software-deployments/` (`software-deployments.read`) | configuration, not per device installs | verified [R3] |
| every other key | not in the schema | | unverified (not found) |

### 3.4 1Password Device Trust (Kolide)

Base URL `https://api.kolide.com`, header `X-Kolide-Api-Version: 2026-04-07` [K1][K2]. A default key is read only [K1].

| Key | Endpoint and field | Caveats | Status |
|---|---|---|---|
| provider_device_id, device_name | `GET /devices` `id`, `name` | name editable by admins | verified [K2] |
| serial_number, hardware_ids | `serial`, `hardware_uuid` | may not apply to some devices | verified [K2] |
| model, platform, os_version, device_class | `hardware_model`, `device_type` (`Mac`, `Linux`, `Windows`, `iOS`, `Android`), `operating_system`, `form_factor` (`Computer`, `Tablet`, `Phone`) | iPadOS reports as `iOS` with form factor Tablet (Verity's reading) | verified [K2] |
| enrolled_at, last_check_in_at | `registered_at`, `last_seen_at`, `last_authenticated_at` | | verified [K2] |
| provider_compliance_state | `auth_state` (`Good`, `Notified`, `Will Block`, `Blocked`), `will_block_at` | | verified [K2] |
| compliance_policies | `GET /checks` (`slug`, `name`, `compatible_platforms`, `type` osquery, custom or external, `osquery_sql_template`, `targeting_configuration`) | | verified [K2] |
| assigned_user_email | `registered_owner_info.identifier` then `GET /people/{id}` `email`; `GET /deprovisioned_people` | | verified [K2] |
| disk_encryption, passcode, os_integrity, av, os_update_available | `GET /devices/{id}/check_results` (`check_slug`, `status` `passing`, `failing`, `errored`, `inapplicable`, `stale`, `pending`, `out_of_scope`, `unknown`; `ran_at`; `exemption_reason`, `exemption_expires_at`; `check_result_data`) or `GET /checks/{id}/results` | the mapping of check slug to key is set per tenant at setup | verified [K2][K3] |
| failure history | `GET /issues` (`detected_at`, `resolved_at`, `exempted`, `last_rechecked_at`, `check_information`, `device_information`) | | verified [K2] |
| installed_apps | `GET /reporting/tables`, `GET /reporting/tables/{name}/table_records` | table names are not in the spec | unverified |
| ownership, supervised, recovery_key_escrowed, idle_lock_seconds, firewall_on, device.action | not in the schema | firewall and escrow checks may exist in the catalogue | unverified |

Never read from Device Trust: `GET /live_query_campaigns/{id}/query_results` (results of admin run SQL, which can
include personal data on BYOD), and on personal devices only `status`, never `check_result_data`.

## 4. Auth and permissions

### 4.1 Fleet

**Plans with API access.** The REST API and API only users are Free [F7]. Premium ($7 per host per month on the
pricing page) adds fleets, Observer+ and Technician roles, per fleet users, and API endpoint restrictions for API
only users [F1][F4][F7]. Self hosting is Free; Fleet's managed cloud is Premium and offered only to customers
with 700 or more hosts [F7].

**Customer steps (draft product text):**
1. A Fleet global admin opens **Settings > Users > Create user** and picks **API-only**, or runs
   `fleetctl user create --name 'Verity' --api-only`; the default role is Observer [F5].
2. Role: **global Observer**. Not fleet scoped: a fleet scoped user cannot list global activities and misses
   Unassigned hosts [F1][F4].
3. Premium: limit the user's API endpoints to the GET list Verity shows (below). Endpoint limits never add
   rights beyond the role [F1].
4. Copy the token shown at creation. API only tokens do not expire; rotation means a new user, then deleting
   the old one [F6].
5. Paste the Fleet server URL and token into Verity. Verity calls `GET /api/v1/fleet/me` (expects
   `api_only: true`, role observer), `GET /config` (reads `license.tier`) and `GET /version` [F1].

**Verity's endpoint list** (all GET): `/me`, `/version`, `/config`, `/hosts`, `/hosts/count`, `/host_summary`,
`/hosts/:id`, `/hosts/:id/software`, `/hosts/:id/activities`, `/activities`, `/global/policies`,
`/fleets`, `/fleets/:id/policies`, `/os_versions`, `/reports/:id/report`, `/commands`, `/commands/results` [F1].

**What Observer can see that Verity must never call.** The Observer role can read hosts' disk encryption keys,
macOS Recovery Lock passwords and managed local account passwords, and can start live reports marked
`observer_can_run` [F1][F4]. Escrow is a Premium feature [F7], so on Premium the endpoint restriction in step 3
is the only way to remove that access. On Free there are no escrowed keys, but Recovery Lock and managed
account features are also Premium, so the exposure is limited (Verity's reading). Fleet records
`read_host_disk_encryption_key` and `viewed_host_recovery_lock_password` activities [F2][F3], so Verity can show
in its evidence that its user never read a secret.

### 4.2 NinjaOne

**Plans.** NinjaOne does not publish prices; its compare plans page has an "API Access" row but the text read
does not show which plans include it [N10] (unverified).

**Customer steps (draft product text):**
1. A NinjaOne system administrator opens **Administration > Apps > API > Client app IDs > Add** [N1]. Only
   system administrators can configure OAuth for the public API [N1].
2. Application platform: **API Services (machine-to-machine)**. This label comes from Secureframe's guide,
   third party [N8]; NinjaOne's 2025 page lists only Native, Single Page and Web [N2] (unverified in NinjaOne's
   own docs).
3. Scopes: **Monitoring** only (read only access to monitoring data and organisation structure) [N1].
4. Grant type: **Client Credentials** only, no redirect URI (third party [N8]; `client_credentials` is a valid
   `grant_type` in NinjaOne's token schema [N3]).
5. Save; copy the client id and secret (where the secret is shown: unverified).
6. In Verity, pick the region (`app` US East, `us2` US West, `eu`, `ca`, `oc`: third party [N8][N9]; NinjaOne
   lists US, EU, OC, CA and a FedRAMP instance without hostnames [N5]) and paste both values.
7. Verity posts to `https://<region>.ninjarmm.com/ws/oauth/token` with `grant_type=client_credentials` and
   `scope=monitoring` (path verified [N3]; host per region third party).

**What it can see.** Monitoring covers the whole NinjaOne account. A NinjaOne account can hold many
organisations (`/v2/organizations`), and no per organisation restriction for a client app was found
(unverified). Verity filters by the customer's `organizationId` with the device filter `df`.

### 4.3 Rippling

**Plans.** The endpoint lists devices managed in Rippling IT [R1], so the customer needs Rippling's device
management product (name and packaging unverified). Some APIs need a separate entitlement from the Rippling
account manager [R4]; whether devices does is unverified.

**Customer steps (draft product text):**
1. A Rippling user whose permission profile can see devices and workers opens **Developer > API credentials >
   New API token** [R4]. Rippling suggests IT or security admins hold the API token admin permission [R4].
2. Name it "Verity (read only)" and pick scopes `devices.read`, `device-orders.read`, `workers.read` [R3].
   Add nothing ending in `read-write`.
3. Copy the token once; it cannot be viewed again [R4].
4. Paste it into Verity. Verity reads `__meta.redacted_fields` on the first call to confirm the profile can see
   the fields [R8].

**What it can see.** The intersection of the creator's permission profile and the scopes [R4]. The token is
revoked when its owner is terminated or after 30 days unused [R4]: a daily run keeps it alive, an owner
leaving breaks it. Creation notifies the owner, API token admins and super admins [R4].

### 4.4 1Password Device Trust (Kolide)

**Plans.** Device Trust is sold as Device Trust Core (browser extension enforcement, needs 1Password Business)
and Device Trust Connect (adds identity provider sign in checks) [K5][K6]. Prices are not shown [K6]
(unverified). Write permissions on API keys are a premium feature and absent on some legacy plans [K1]; read
keys need none of them.

**Customer steps (draft product text):**
1. A Device Trust admin with Full Access opens the avatar menu, **Settings > Developers > API Keys > Create
   New Key** [K1].
2. Name it "Verity" and name the responsible admin (both appear in the audit log and the Privacy Center) [K1].
3. Leave every write permission unticked (remove devices, manage user requests, manage device groups, refresh
   check, update devices, create live query) [K1].
4. Save and copy the `k2sk_v1_...` key [K1]. Paste it into Verity.

**What it can see.** Every read endpoint in 2.4 and 3.4, including admin users, audit and auth logs, people and
live query results [K2]. Verity calls only devices, checks, check results, issues, people and deprovisioned
people.

## 5. Limits, freshness and history

| Product | Rate limit | Paging | Freshness | History |
|---|---|---|---|---|
| Fleet | no general API limit documented (unverified); login is limited, 429 with `retry-after` [F1]. Self hosted capacity is the customer's: Fleet warns that `populate_software`, `populate_end_users` and `device_mapping` with large pages overload the server [F1] | hosts: `page`, `per_page`, `order_key`, `after`; no paging metadata in the example, so page until a short page and compare with `GET /hosts/count` [F1]. Software and commands return `meta.has_next_results`; activities up to 10,000 per page; commands `per_page` up to 1,000 and `page` up to 100 [F1] | host details, policies and labels refresh every hour by default (server settings) [F8]; software hourly [F12]; `seen_time` per contact [F1]; iOS vitals come from MDM DeviceInformation [F1] | vitals and policy results are current state only (no history endpoint found). Activities are kept unless activity expiry is on; host activities stay until the host is deleted [F1]. Apple wipe and lock commands are kept; other Apple commands 24 hours or 30 days; Windows commands 30 days [F11]. Host expiry can delete silent hosts after N days [F1] |
| NinjaOne | not stated in the pages and spec read (unverified) | devices: `pageSize` and `after` (last id); query reports: `cursor` with `cursor.expires`; activities: `pageSize`, `olderThan`, `newerThan`, `before`, `after` [N3] | `lastContact`, `lastUpdate`, per row `timestamp` [N3]; agent interval unverified | activities and patch install history are queryable by date [N3]; retention unverified |
| Rippling | 600 requests per 10 seconds per token per path; 429 with backoff or `Retry-After` [R5] | `limit` 1 to 100 (default 50), `cursor`, `next_link`; expand depth 2; filter up to 64 nodes [R5] | `last_checkin_at`, `last_mdm_sync_at` [R1]; interval unverified | none: present state and queued actions only [R1]; Verity's daily snapshot is the history |
| Device Trust | 270 requests per minute; 429 with `Retry-After` and `RateLimit-*` headers (the sample shows a limit of 15, which conflicts) [K1] | cursor, `per_page` 1 to 100 (default 25); blank `next` ends [K1] | checks run on a schedule and at authentication; interval not given [K3][K5]; `ran_at` per result [K2] | issues keep `detected_at` and `resolved_at`, and `/issues` filters on `resolved_at` [K2]; audit logs [K2]; check results are latest only |

## 6. Gotchas that would make a check wrong

### 6.1 Fleet

- **Missing is not false.** `disk_encryption_enabled` is left out when Fleet does not know, and also for Linux
  hosts whose root volume reports unencrypted [F1]. An absent field on Linux can mean "known unencrypted".
  Verity: absent on Linux gives `fail` only with a policy or report that proves it; otherwise `insufficient`.
- **Policies are the customer's SQL.** A policy named "Screen lock" can test anything. Verity records the
  policy `query` text and its hash with each result, and maps a policy to a check only when the customer picks
  it at setup and the SQL matches a reviewed pattern (for example the built in screen lock and firewall
  policies [F14]). A changed SQL hash makes the result `insufficient` until reviewed.
- **An empty policy response** means not run on that host [F1]: `insufficient`, not `fail`.
- **Built in screen lock policies differ from Verity's limit.** The macOS one checks only that a password is
  required (any delay) and the Windows one allows up to 1,800 seconds [F14]. Verity compares the value from a
  report to `max_idle_lock_minutes`; a pass of the Fleet policy alone is not enough.
- **`is_personal_enrollment` is sticky** on mobile after unenrolment [F1]: use `enrollment_status` for the
  current state and the sticky flag only for history.
- **Personal mobile identifiers are enrolment ids**, not serials [F1]: never match them to an asset register
  serial.
- **Deleting a host erases its wipe record.** Fleet says to wait for a wipe to finish before deleting [F10];
  `preserve_host_activities_on_reenrollment` defaults to false on new servers [F1], so a wiped and re enrolled
  host can lose its earlier activities. Verity must snapshot `mdm.device_status` and commands daily.
- **Linux wipe has no wiped state** [F10]: `devices.wipes_confirmed` gives `insufficient` for Linux unless a
  script result proves it. Observer can read script results (`GET /scripts/results/:execution_id`, exit code
  and output) [F1]; whether the Linux wipe leaves an execution id Verity can find is unverified.
- **`failed_wipe` exists only for Windows** [F2]. Apple failures show as command status `Error` [F1].
- **Moving a host to a fleet without disk encryption deletes its escrowed key** [F9]: escrow can drop to false
  without any device change.
- **Renames.** Teams are now "fleets" and queries are now "reports"; responses carry both `team_id` and
  `fleet_id` [F1]. Self hosted servers run many versions and Fleet removes deprecated endpoints (one was removed
  in 4.93) [F1]. Verity reads `/version`, sets a minimum version and handles both names.
- **Observer reads secrets** (4.1). On Premium, refuse to connect if the user is not endpoint restricted, or
  show a warning the owner accepts (decision for the owner).
- **Location data.** Hosts carry `geolocation` when GeoIP is set up, and iOS lock collects location [F1][F10];
  Verity drops both.

### 6.2 NinjaOne

- **RMM is not MDM.** Desktops are managed by the NinjaOne agent, not an MDM channel: `devices.enrolled` needs
  an owner decision on whether an RMM agent counts as managed.
- **macOS and Linux encryption are not in the API.** Secureframe reports the same [N8]. FileVault events exist
  only as activities [N3]: Verity must not infer current state from the last event older than the window.
- **Mobile security fields are console only** [N6] versus [N3]: no passcode, ownership or encryption for MDM
  devices through the API read.
- **Unknown value sets** for antivirus `productState` and `definitionStatus` [N3]: build the mapping from
  fixtures; unmapped values give `insufficient`.
- **Account wide credential** in MSP style accounts (4.2): a customer whose NinjaOne is run by an MSP must ask
  the MSP, and the credential may see other clients' devices. Verity keeps only the chosen organisation.
- **Region.** The host must be one of the regional subdomains even when the portal uses another domain, third
  party [N8].

### 6.3 Rippling

- **Null can mean redacted**, not false [R8]: `is_encrypted` null is `insufficient`.
- **`is_managed` true with another `mdm_provider`** means Rippling only records it [R1]: read the device from
  that MDM's connector and do not double count.
- **Breaking enum growth**: `lifecycle_state` gained `SOLD` in November 2026 [R6]. Unknown values give
  `insufficient`, never a crash.
- **No action history.** Only queued actions are listed [R1]; a completed wipe shows only as `FULL_WIPED` at
  the time Verity looks.
- **Token dies with its owner** or after 30 days unused [R4]: health shows "token revoked" with that reason.
- **Platforms limited** to macOS, Windows, iOS, iPadOS in the API [R1].

### 6.4 Device Trust

- **Agent, not management.** Device Trust cannot enforce settings or wipe; it warns or blocks sign in [K4][K5].
  `devices.enrolled` stays a fail or "known only" for agent devices.
- **Check status has eight values** [K2]; only `passing` passes. `stale` means the check options changed after
  the last run [K3]; `inapplicable` and `out_of_scope` remove the device from that check's population with the
  reason recorded.
- **Exemptions** carry `exemption_reason` and expiry [K2]: Verity shows them as approved exceptions only if the
  reason is recorded, and treats an expired exemption as a fail.
- **Drata reads a NULL result as a failure** [K8]; Verity treats it as `insufficient`.
- **Check catalogue names vary** by tenant and custom checks share the namespace: map by `slug`, keep
  `osquery_sql_template` for custom checks in the evidence.

## 7. Check support by product

yes = the check can run as defined; partial = with the stated limit; no = cannot.

| Check | Fleet | NinjaOne | Rippling | Device Trust |
|---|---|---|---|---|
| `devices.enrolled` | yes on MDM platforms; agent only hosts need the owner's ruling | partial: MDM mobiles yes; desktops are RMM agents | yes: `enrollment_status`, `is_managed`, MDM sync time | no: agent only ("known only") |
| `devices.disk_encrypted` | yes (Linux and personal mobile caveats) | partial: Windows only | yes: macOS and Windows | yes: desktop checks |
| `devices.recovery_key_escrowed` | yes on Premium (macOS, Windows, Linux LUKS2 on four distros); no on Free | no | no | unverified |
| `devices.screen_lock` | partial: customer report or policy; Android passcode only | no | no | partial: desktop lock and mobile passcode checks; idle value unverified |
| `devices.os_current` | yes | partial: desktops yes, mobile build only | yes | yes |
| `devices.firewall_enabled` | partial: customer policy (macOS, Windows) | no | no | unverified |
| `devices.remote_wipe` | yes: capability from enrolment status (company full, personal work data only); Linux needs scripts | partial: MDM mobiles only | partial: Rippling MDM devices (Verity's reading) | no |
| `devices.wipes_confirmed` | yes on Premium for macOS, Windows, iOS; Android on Free; Linux no | partial: activity codes, outcome text unverified | partial: `FULL_WIPED` state, no history | no |
| `devices.removable_storage_restricted` | partial: customer policy or report | no | no | unverified (custom check) |
| `devices.assigned_to_active_staff` | yes with IdP mapping (Premium); partial with Free mapping | partial: assigned owner if set | yes: worker in the same tenant | yes: registered owner |
| `devices.staff_have_managed_device` | yes | partial | yes | partial: shows an agent device, not a managed one |
| `devices.leaver_devices_recovered` | partial: needs HR source and snapshots | partial | yes, best of the four: worker end and status, device lifecycle and warehouse return orders in one tenant; partial for want of a device id on orders | partial: deprovisioned people and their devices, no wipe |
| Permitted software (EP-03.E) | yes: per host inventory with source, bundle id and code signature on company devices; managed catalogue on Premium | yes on agent devices (inventory with install date) | partial: managed catalogue only, no installed inventory | partial: custom checks or reporting tables (unverified) |

## 8. Fleet as the base for customers without an MDM

**What Verity gets from a customer's own Fleet.** One read only token gives: every enrolled computer and mobile,
with ownership and channel; disk encryption and, on Premium, key escrow; OS version and OS CVEs; full software
inventory with versions, CVEs and code signatures; the customer's policies with their SQL and pass or fail per
host; person mapping; lock and wipe state and history; and an audit trail that proves Verity's user read no
secret [F1][F2][F9][F12]. Screen lock time, firewall and USB come only through policies or reports the customer
adds, which Verity can supply as reviewed SQL for the customer to paste (Verity never writes them).

**What it does not solve for small customers.**
- Fleet's managed cloud is only for 700 or more hosts [F7]. A 30 person company would self host a Fleet server
  (Fleet documents MySQL and Redis based deployments; detail not read this round) or buy from a partner.
- Lock, wipe, escrow, OS update enforcement and IdP mapping are Premium [F7]. Free Fleet gives inventory,
  encryption state, policies and software, which already covers EP-02 (state), EP-04 and EP-03.E.

**Options for Verity.**

| Option | What it means | Licence position | Fit |
|---|---|---|---|
| Connector to the customer's Fleet | the device_management connector described here | no Fleet code used | cheap; serves companies that already run Fleet |
| Verity hosts Fleet Free per tenant | Verity runs servers and gives customers fleetd installers | MIT outside `ee/`; Free features only; EE code may not be used in production without a subscription and may not be sublicensed [F15] | turns Verity into an MDM operator; no escrow or wipe |
| Verity hosts Fleet Premium as a partner | Fleet lists Premium multi tenancy for service providers [F7] | needs a commercial agreement (terms unverified) | strongest evidence; a business decision |
| Verity's own agent on Orbit and osquery | round 1 option A | Orbit is MIT [F15], osquery Apache-2.0 or GPL-2.0 (round 1 A2) | same build costs as round 1 |

Recommendation: add the Fleet connector and the Device Trust connector to the catalogue as low cost sources
(both are pure GET APIs with read only keys); keep round 1's "no Verity agent now". For customers with no MDM
and BYOD or contractors, Device Trust is the better fit of the products here: it is built for personal and
contractor devices, self installed, shows people what it checks, and Verity can read pass or fail without raw
device data [K4][K6]. Fleet suits customers that want management and can host it.

## 9. Go approach

| Product | Reusable client | Recommendation |
|---|---|---|
| Fleet | The admin API client is `Client` in `github.com/fleetdm/fleet/v4/server/service` (`client.go`, `client_hosts.go`), MIT files. The same package's `handler.go` imports `github.com/fleetdm/fleet/v4/ee/server/service/scep` [F16], so importing it compiles EE licensed code and the whole server. The module requires Go 1.27.4 and has about 400 `go.mod` lines [F16] | do not import. Write a small `net/http` client for the 17 GET endpoints with Verity's own structs; copying field names from MIT files keeps the MIT notice. No separate Fleet Go SDK was found (unverified) |
| NinjaOne | OpenAPI 3.0.1 spec, version 2.0.9-draft, with polymorphic device lists [N3] | hand written client for about 8 endpoints; `golang.org/x/oauth2/clientcredentials` for the token if it is already a dependency, otherwise a few lines of form POST. No official Go SDK found (unverified) |
| Rippling | plain REST, cursor paging [R1][R5] | `net/http`; share the HR connector's client and token handling |
| Device Trust | OpenAPI 3.0.0 spec, dated versions [K2] | generate types or hand write; pin `X-Kolide-Api-Version: 2026-04-07` |

## 10. Corrections to round 1

| File | Claim | Correction | Source |
|---|---|---|---|
| mdm-and-endpoint-strategy.md 7.3 | Fleet is MIT outside `ee/`; Verity could use the MIT parts | Partly right. `docs/` is CC BY-SA 4.0, not MIT. The Go API client sits in `server/service`, whose `handler.go` imports an `ee/` package, so "using the MIT parts" excludes that package. `orbit/` is MIT. The EE licence also allows copying and changing EE code for development and testing without a subscription | [F15][F16] |
| mdm-and-endpoint-strategy.md 2; connectors/hr-systems.md | Rippling appears only as an HR system | Rippling's REST API has exposed devices since 2026-07-01 (`devices.read`): encryption, enrolment, MDM provider, lifecycle, worker assignment, queued actions, plus device orders. Rippling is also a `device_management` candidate, and the strongest single tenant source for `devices.leaver_devices_recovered` | [R1][R3][R6][R7] |
| mdm-and-endpoint-strategy.md 7.4 | options cover agent, MDM connectors, attestation, Google | Fleet's managed cloud requires 700 or more hosts, so "the customer's own Fleet" means self hosting for small customers | [F7] |
| 03-market-research.md (O1) | Fleet is open source, mostly Go, MIT | MIT except `ee/` (EE licence) and `docs/` (CC BY-SA 4.0) | [F15] |
| this research request | "1Password Extended Access Management, Device Trust" | the current product page sells Device Trust Core and Device Trust Connect within 1Password's Unified Access platform; it does not mention Extended Access Management | [K6] |

## 11. Proposed new dictionary keys

| Key | Meaning | Sources | Check that uses it |
|---|---|---|---|
| `agent_last_seen_at` | last contact of an agent, separate from `last_check_in_at` for the MDM channel | Fleet `seen_time` vs `last_mdm_checked_in_at`; Rippling `last_checkin_at` vs `last_mdm_sync_at` | `devices.enrolled` freshness per channel; `endpoint.coverage_complete` |
| `wipe_scope` | full, work_data_only, none, unknown | Fleet enrolment status and wipe rules; Android work profile removal [F1][F10] | `devices.remote_wipe` (round 1 section 6 lists wipe scope, the dictionary does not) |
| `provider_checks` | list of provider policy or check id, name, definition hash, result, ran_at | Fleet policies, Device Trust checks [F1][K2] | `devices.screen_lock`, `devices.firewall_enabled`, `devices.removable_storage_restricted` when the value comes from a customer defined policy |
| `assignment_confidence` | strong (IdP, SCIM, HR worker), weak (browser profile, last logged on user) | Fleet `other_emails.source`; NinjaOne `lastLoggedInUser`; Rippling `worker_id` | `devices.assigned_to_active_staff`, `devices.staff_have_managed_device` |
| `known_vulnerabilities` | CVE ids on the OS and apps, with KEV flag where given | Fleet host software and OS versions [F1]; NinjaOne vulnerability counts [N3] | a patch or vulnerability check for EP-04 (NEED) |
| connector attribute `credential_reads_secrets` | the stored credential could read recovery keys or passwords | Fleet Observer rights [F4] | connector health warning, not a device check |

## 12. Sources

Fleet
- [F1] Fleet REST API reference: https://fleetdm.com/docs/rest-api/rest-api (read as https://raw.githubusercontent.com/fleetdm/fleet/main/docs/API/rest-api.md): hosts, host fields and notes, roles per endpoint, API only users and endpoint limits, policies, reports, software, OS versions, activities, commands, wipe, config, version, paging
- [F2] Fleet global audit logs: https://fleetdm.com/docs/api/global-audit-logs: `wiped_host`, `failed_wipe`, `mdm_enrolled`, `mdm_unenrolled`, `deleted_host`, `escrowed_disk_encryption_key`
- [F3] Fleet host audit logs: https://fleetdm.com/docs/api/host-audit-logs: `read_host_disk_encryption_key` and other host activities
- [F4] Role based access: https://fleetdm.com/guides/role-based-access: Observer rights including secrets and live reports; Premium roles
- [F5] fleetctl guide, API only user: https://fleetdm.com/guides/fleetctl: creation, default Observer role, non expiring token
- [F6] Rotate an API only user's token: https://fleetdm.com/guides/rotate-api-only-user-token: rotation by new user
- [F7] Pricing: https://fleetdm.com/pricing and feature table https://raw.githubusercontent.com/fleetdm/fleet/main/handbook/company/pricing-features-table.yml: tiers, $7 per host, managed cloud at 700+ hosts, multi tenancy
- [F8] Fleet server configuration: https://fleetdm.com/docs/configuration/fleet-server-configuration: detail, policy and label update intervals (1 hour default)
- [F9] Enforce disk encryption: https://fleetdm.com/guides/enforce-disk-encryption: escrow per platform, status values, key deletion on fleet move
- [F10] Lock and wipe hosts: https://fleetdm.com/guides/lock-wipe-hosts: platforms, Premium, Linux script wipe, delete after wipe, iOS location on lock
- [F11] MDM commands: https://fleetdm.com/guides/mdm-commands: command history retention
- [F12] Software inventory reference: https://fleetdm.com/guides/software-inventory-reference: sources per platform, BYOD limits, hourly refresh
- [F13] ChromeOS: https://fleetdm.com/guides/chrome-os: extension, hostname, limits
- [F14] Built in policy library: https://raw.githubusercontent.com/fleetdm/fleet/main/docs/01-Using-Fleet/standard-query-library/standard-query-library.yml: screen lock, firewall, SIP, Gatekeeper, antivirus policies
- [F15] Licences: https://raw.githubusercontent.com/fleetdm/fleet/main/LICENSE , https://raw.githubusercontent.com/fleetdm/fleet/main/ee/LICENSE , https://raw.githubusercontent.com/fleetdm/fleet/main/orbit/LICENSE
- [F16] Go client and module: https://github.com/fleetdm/fleet/blob/main/server/service/client.go , https://github.com/fleetdm/fleet/blob/main/server/service/client_hosts.go , https://github.com/fleetdm/fleet/blob/main/server/service/handler.go (imports `ee/server/service/scep`), https://github.com/fleetdm/fleet/blob/main/go.mod
- [F17] Fleet releases: https://github.com/fleetdm/fleet/releases (latest `fleet-v4.96.0`, 2026-11-24)

NinjaOne
- [N1] OAuth token configuration (updated 2026-09-06): https://www.ninjaone.com/docs/application-programming-interface-api/oauth-token-configuration/: menu path, scopes, system administrators only
- [N2] How to set up an API OAuth token (updated 2025-07-15): https://www.ninjaone.com/docs/integrations/how-to-set-up-api-oauth-token/: platforms and grant types listed then
- [N3] Public API v2 specs: https://app.ninjarmm.com/apidocs/NinjaRMM-API-v2.json (2.0.9-draft) and https://app.ninjarmm.com/apidocs/authorization.json, shown at https://app.ninjarmm.com/apidocs/: device schemas, query reports, activities and codes, paging, token request
- [N4] Public API operations: https://www.ninjaone.com/docs/application-programming-interface-api/public-api-operations/: OAuth 2.0, docs location
- [N5] Integration availability by instance: https://www.ninjaone.com/docs/integrations/integration-feature-availability-by-instance/: US, EU, OC, CA, FedRAMP
- [N6] MDM data per enrolment type (updated 2026-11-11): https://www.ninjaone.com/docs/mdm/mdm-data-details-enrollment-type/: mobile fields in the console
- [N7] MDM device and OS compatibility: https://www.ninjaone.com/docs/mdm/device-and-os-compatibility/: iOS 10+, iPadOS, Android 8+
- [N8] Secureframe, NinjaOne (third party): https://support.secureframe.com/en/articles/15111587-ninjaone: machine to machine app, Monitoring, client credentials, regions, no macOS or Linux encryption
- [N9] Vanta, connecting NinjaOne (third party): https://help.vanta.com/en/articles/11534632-connecting-vanta-ninjaone: region names
- [N10] NinjaOne compare plans: https://www.ninjaone.com/compare-plans/: API Access row

Rippling
- [R1] List devices: https://developer.rippling.com/documentation/rest-api/reference/list-devices: fields, enums, filters, expand
- [R2] Retrieve a device: https://developer.rippling.com/documentation/rest-api/reference/get-devices: expandable worker object
- [R3] API scope reference: https://developer.rippling.com/documentation/rest-api/essentials/permissions: `devices.read`, `device-orders.read`, `software-deployments.read`, `workers.read`
- [R4] API tokens and permissions: https://developer.rippling.com/documentation/rest-api/essentials/api-tokens: creation, owner profile, 30 day revocation, entitlement note
- [R5] Usage and rate limits: https://developer.rippling.com/documentation/rest-api/essentials/api-limits
- [R6] Changelog: https://developer.rippling.com/documentation/rest-api/essentials/changelog: device endpoints 2026-07-01, `SOLD` 2026-11-05, `limit` 2026-08-25
- [R7] List device orders: https://developer.rippling.com/documentation/rest-api/reference/list-device-orders
- [R8] Developer index and agent rules: https://developer.rippling.com/llms.txt: null may mean redacted
- [R9] Query parameters: https://developer.rippling.com/documentation/rest-api/essentials/query-parameters

1Password Device Trust (Kolide)
- [K1] Device Trust API (published 2026-11-04): https://support.1password.com/device-trust-api/: base URL, key creation, default read only, write permissions, rate limit, paging, versioning
- [K2] OpenAPI spec 2026-04-07: https://support.1password.com/files/device-trust/openapi-2026-04-07.json: endpoints and schemas
- [K3] Checks overview: https://support.1password.com/device-trust-checks-overview/: status meanings, schedule
- [K4] About Device Trust: https://support.1password.com/device-trust-about/: warn or block, osquery, privacy statement
- [K5] FAQ: https://support.1password.com/device-trust-frequently-asked-questions/: Core and Connect, about 100 checks, run at authentication
- [K6] Product page: https://1password.com/product/device-trust: Core, Connect, platforms, BYOD and contractors, Unified Access
- [K7] Mobile checks (2024-10-08): https://1password.com/blog/introducing-mobile-checks-for-device-trust: iOS and Android checks, MDM enrolment check
- [K8] Drata, Device Trust guide (third party, updated 2026-03-04): https://help.drata.com/en/articles/10298210-1password-device-trust-kolide-integration-guide: check names mapped, nightly import, NULL as failure

Internal: `docs/product/evidence-connectors/06-control-changes.md` (EP-03.E wording), round 1 files listed at the top.
