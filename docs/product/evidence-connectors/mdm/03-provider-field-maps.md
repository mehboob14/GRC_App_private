# 3. Providers: credentials, what each can supply, and the field maps

Sixteen device sources were researched in round 2. This file is the comparison and the build reference.
Field level maps (endpoint, field, permission, verified or unverified per row) stay in the research files, which
are the source of truth for a collector author:

| Provider | Field map |
|---|---|
| Apple platform rules (all Apple MDMs), Apple Business API | [research/apple-platforms.md](research/apple-platforms.md) 3, 4.2 |
| Microsoft Intune, Autopilot, Entra devices, MAM | [research/microsoft-intune.md](research/microsoft-intune.md) 3 |
| Android (vocabulary), Google endpoint management, Endpoint Verification, ChromeOS, Chrome browsers, zero touch, Knox | [research/android-chromeos-google.md](research/android-chromeos-google.md) 3 |
| Jamf Pro, Iru (Kandji), Mosyle, Addigy, SimpleMDM | [research/apple-mdms.md](research/apple-mdms.md) 4 to 8 |
| Workspace ONE, JumpCloud, Hexnode, ManageEngine | [research/cross-platform-mdms-a.md](research/cross-platform-mdms-a.md) A to D |
| Fleet, NinjaOne, Rippling devices, 1Password Device Trust (Kolide) | [research/cross-platform-mdms-b.md](research/cross-platform-mdms-b.md) 3 |
| Round 1 connector files (still valid where not corrected) | [../connectors/](../connectors/) intune, jamf-pro, kandji, google-endpoint-management |

Verification logs for round 2: [research/verify-apple.md](research/verify-apple.md),
[research/verify-microsoft-google.md](research/verify-microsoft-google.md),
[research/verify-xplat-market.md](research/verify-xplat-market.md).

## 3.1 Provider overview

"Read only" means a credential exists that cannot change anything in the customer's system. "Secrets risk"
means a route the read credential can reach returns key material or passwords, so Verity's endpoint and field
allowlists (02, 2.5) are mandatory for that provider.

| Provider | Platforms | Auth | Read only credential | Secrets risk | Freshness | History from the source | Competitors integrating [market 3] |
|---|---|---|---|---|---|---|---|
| Microsoft Intune | Windows, macOS, iOS, iPadOS, Android, Linux, Cloud PC | Entra app, application permissions (shared with the Entra connector) | yes: `.Read.All` permissions only | no if `getFileVaultKey`, bypass codes and product keys are never selected | sync about every 8 hours; app inventory every 7 days [ms 5] | 60 days of daily compliance, management state and OS rows through the Data Warehouse (`get_data_warehouse`); no encryption history [ms 5] | 6 of 7 |
| Jamf Pro | macOS, iOS, iPadOS, tvOS | API Roles and Clients, client credentials | yes: six Read privileges [apple-mdms 4.2] | no, if recovery key privileges and routes are never granted | inventory daily by default (customer policy) [apple-mdms 4.5] | present only | 6 of 7 |
| Iru (Kandji) | macOS, iOS, iPadOS, tvOS, Windows (per Vanta) | API token with chosen permissions | yes: permission picker | lost mode and cellular routes carry location and phone data: keep the token off them [apple-mdms 5.5] | per Prism `last_collected_at` | present; audit events for lifecycle | 6 of 7 |
| JumpCloud | macOS, Windows, Linux, iOS, Android | service account with the Read Only role, client credentials [xplat-a B.2] | yes, but Read Only has Edit on Insights queries | FileVault key route: whether Read Only reaches it is unverified | System Insights hourly [xplat-a 0] | System Insights kept 90 days since 6 April 2026 | 6 of 7 |
| Google (endpoint management, Endpoint Verification, ChromeOS, browsers) | Android, iOS, macOS, Windows, Linux, ChromeOS | Verity's service account with domain wide delegation, read only scopes | partial: the read only scopes are the only guard; the admin privilege for mobile is full control [google C3]; ChromeOS has a true read only privilege | none on the scopes used | Endpoint Verification every 4 hours; basic mobile can take days [google 5] | mobile audit events kept about 6 months, by edition [verify-ms K6] | 2 (Chromebooks or Chrome lists only); Mac and Windows through Google: none |
| Workspace ONE UEM | all six | OAuth client (SaaS) or basic auth plus tenant code (on premises) | yes: Read REST permissions in a custom role | the device security response defines recovery key fields; a separate route returns BitLocker keys [xplat-a 0] | not stated | device audit 30 days; no command history API | 4 of 7 |
| Hexnode | all six | one API key per portal | **no**: the key has admin power, including wipe and delete [xplat-a C.2] | high | not stated | not stated | 4 of 7 |
| ManageEngine Endpoint Central, MDM Plus | Windows, macOS, Linux, mobile | Zoho OAuth with per module READ scopes (cloud); API key with Read toggles (on premises) | yes | `DataEncryption.READ` returns BitLocker keys; MDM inventory read returns Mac firmware passwords and locations [xplat-a 0] | not stated | not stated | 2 of 7 |
| Addigy | macOS, iOS, iPadOS | API key; `GET /configuration/permissions` lists what it holds | yes: View permissions per operation | no on View routes | not stated | events only | 2 of 7 |
| SimpleMDM | Apple | API key as Basic user | partial: per resource rights | **existing keys return FileVault keys by default** unless Device Secrets is off [apple-mdms 8] | not stated | logs, retention not stated | 1 of 7 |
| Mosyle | Apple | access token plus an admin's email and password (third party reading) | unverified | unknown | unknown | unknown | 0 with posture |
| Fleet | macOS, Windows, Linux, ChromeOS, iOS, Android | API only user with Observer role | partial: Observer can read disk keys and passwords; Premium can restrict an API user to an endpoint list [xplat-b 4.1] | high on Free | `seen_time` per host | policy results, vulnerability data; no state history | 1 of 7 |
| NinjaOne | Windows, macOS, Linux (RMM), mobile (MDM) | OAuth client credentials, `monitoring` scope | yes, but the scope covers the whole account, risky for MSP run accounts [xplat-b] | low | not documented | activities | 3 of 7 |
| Rippling devices | macOS, Windows | Rippling OAuth, `devices.read` (API since 1 July 2026) | yes | low | MDM sync time | no | 3 of 7 |
| 1Password Device Trust (Kolide) | macOS, Windows, Linux, mobile | API key, read only by default | yes | low | agent driven | issue history per check | 2 of 7 |
| Apple Business (API and its built in MDM) | Apple | API account, ES256 client assertion, one hour token | yes: custom role | none on device routes | per device `updatedDateTime` | audit events | population source, not counted |

## 3.2 Check support by provider

yes, partial (with the limit in the research file), no, n/a. "IdP" means the check needs an identity provider
connection for the person side.

| Check | Intune | Jamf Pro | Iru | JumpCloud | Google | Workspace ONE | Hexnode | ManageEngine | Addigy | SimpleMDM | Fleet | NinjaOne | Rippling | Device Trust |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `devices.enrolled` | yes | yes | yes | yes | partial | yes | yes | yes | partial | yes | yes | partial | yes | no (agent only) |
| `devices.disk_encrypted` | yes (Windows); macOS mapping unverified | yes | yes (Mac) | yes (computers) | yes | yes | unverified | yes | yes (macOS 14+) | yes (Mac) | yes | Windows only | yes | yes |
| `devices.recovery_key_escrowed` | Windows yes; macOS no | yes | yes | partial | no | macOS, only through the per device security call (D-MDM-12) | partial | macOS yes | partial | no | Premium yes | no | no | unverified |
| `devices.screen_lock` | partial (policy) | partial | partial | partial | ChromeOS partial; else no | partial | partial | partial | partial | partial | partial | no | no | partial |
| `devices.os_current` | yes | yes | yes | yes | partial (Android rule) | yes | yes | yes | yes | yes | yes | partial | yes | yes |
| `devices.firewall_enabled` | partial (setting state) | yes | yes | macOS yes | desktops and ChromeOS yes | partial | partial | Windows yes | yes | yes | partial | no | no | unverified |
| `devices.remote_wipe` | yes | yes | partial | yes | partial | yes | partial | partial | partial | yes | yes | partial | partial | no |
| `devices.wipes_confirmed` | partial | partial | partial | partial | partial | partial | yes | mobile yes | no | partial | Premium yes | partial | partial | no |
| `devices.removable_storage_restricted` | later | partial | partial | partial | no | partial | no | partial | unverified | unverified | partial | no | no | unverified |
| `devices.assigned_to_active_staff` | yes (IdP) | yes (IdP) | yes (IdP) | yes (no IdP needed) | yes | yes (IdP) | yes (IdP) | partial | partial (SCIM) | partial | yes | partial | yes | yes |
| `devices.staff_have_managed_device` | yes (IdP) | yes (IdP) | yes (IdP) | yes | partial | yes (IdP) | yes (IdP) | partial | partial | partial | yes | partial | yes | partial |
| `devices.leaver_devices_recovered` | partial | partial | partial | partial | partial | partial | partial | partial | partial | partial | partial | partial | yes (best) | partial |
| `devices.software_permitted` (EP-03.E) | yes (7 day lag) | yes | yes | partial | ChromeOS partial | partial | partial | yes (best) | partial | yes | yes | yes | partial | partial |

`devices.purchased_devices_enrolled` is not a per MDM capability: it joins a purchase source (Apple Business,
Autopilot through the Intune connection, Knox, ChromeOS pre provisioned, Rippling device orders) to whichever
connected MDM reports serial numbers. Agent only sources (Device Trust, Endpoint Verification) can show a
purchased device is known, never that it is managed.

Apple wipe confirmation is partial on every Apple vendor because Apple's erase reply does not prove the
outcome [apple G3]; Hexnode and ManageEngine "yes" rest on their own action status and still need the later
signal for Apple devices.

## 3.3 Notes per provider for the collector author

**Microsoft Intune** (extend `connectors/intune.md`).
- Permissions: DeviceManagementManagedDevices.Read.All, DeviceManagementConfiguration.Read.All,
  BitlockerKey.ReadBasic.All, and new: DeviceManagementServiceConfig.Read.All (Autopilot), Device.Read.All
  (Entra devices), optional DeviceManagementApps.Read.All (MAM), `get_data_warehouse` (history),
  Software.Read.All on Defender (browser and end of support) [ms 4].
- Firewall and lock: read per device setting states from
  `deviceCompliancePolicySettingStateSummaries/{id}/deviceComplianceSettingStates` (v1.0), no export job;
  present only when a policy evaluates the setting [ms 7, G1]. Policy objects from beta (firewall property is
  beta only), states from v1.0 [ms G2].
- Wipe history: beta `remoteActionAudits` with the managed devices read permission [ms 3]. Its rows also
  carry the device IMEI: drop it for personal and unknown ownership [verify-ms K4].
- Enrolment type: read `deviceEnrollmentType` from beta; v1.0 documents only values 0 to 12, so Android
  corporate modes, Azure VM and account driven user enrolment would otherwise be unknown [verify-ms K1].
- Never select: `activationLockBypassCode`, Autopilot `productKey`, BitLocker `key`; never call
  `getFileVaultKey` [ms G16].
- Throttling: 2,000 requests per 20 seconds per app per tenant for the devices section; no delta for Intune
  resources [ms 5].

**Jamf Pro** (extend `connectors/jamf-pro.md`).
- Read `GET /api/v1/jamf-pro-version` each run and pick the inventory version: v4 from 11.30.0 (`lastContact`,
  `lastCheckIn`), v3 for 11.23 to 11.29, v2 for 11.20 to 11.22, v1 below; a missing contact field is `error`
  [apple-mdms 4.1].
- Freshness of state uses `general.reportDate` (computers) and `lastInventoryUpdateDate` (mobile), not contact
  [apple-mdms 4.7].
- Use `exception-handling=LENIENT` on mobile detail; drop `security.lostModeLocation` [apple-mdms 4.7].
- Compliance Benchmarks only as secondary evidence through a Platform API integration that expires every six
  months (D-DEV-14).

**Iru (Kandji)**: `api.kandji.io` and `api.iru.com` both work, and the EU host `api.eu.kandji.io` must be
accepted at connect [verify-apple]; Prism categories for FileVault (`key_escrowed`),
application firewall, startup settings (SIP, secure boot, bootstrap token), apps; 10,000 calls an hour shared
with Iru's own compliance product, so back off and report `truncated` [apple-mdms 5]. Exclude `cellular` and
lost mode routes from the token.

**JumpCloud**: service account with Read Only; it is also a directory, so person checks can run without a
separate identity provider; System Insights (osquery tables) gives FileVault, BitLocker, firewall and apps
hourly but only 90 days are kept; wipe results need Directory Insights, not in the Device Management package,
and confirm receipt only [xplat-a B].

**Google**: add the Chrome Policy and Chrome Management Go libraries (`google.golang.org/api/chromepolicy/v1`,
`google.golang.org/api/chromemanagement/v1`) to round 1's Cloud Identity and Directory libraries [google C10];
exclude `lastKnownNetwork`, `deviceFiles`, `screenshotFiles` from the ChromeOS field mask [google G17]; never
collect `mobiledevices.applications` for personal phones [google G16].

**Workspace ONE**: OAuth only on SaaS; quota 5,000 a minute and 50,000 a day shared with every integration on
the tenant; firewall and antivirus exist only as customer compliance rules; no command history read API
[xplat-a A]. The bulk `securityinfosearch` route returns status strings only and needs a `user` parameter; the
escrow flags, `IsPasscodePresent` and `IsEncrypted` come only from the per device `GET /devices/{id}/security`,
whose schema also holds `PersonalRecoveryKey` and `UnlockPin`. Using it falls under D-MDM-12; without it,
escrow is `insufficient` on Workspace ONE [verify-xplat X1].

**Hexnode**: no read only credential (one key per portal with admin power: the "one per portal" part is
unverified [verify-xplat X5]) and no encryption, passcode or firewall fields in the documented API. Not
buildable under Verity's rules without an owner exception (D-MDM-14). Recommended: attestation path until
Hexnode offers a scoped key. If ever built, the privacy drop list uses Hexnode's real location and phone keys
(there is no `location_history` field) [verify-xplat X4].

**ManageEngine**: best least privilege model and the strongest permitted software evidence; 50 to 120 calls a
minute with a five minute lockout; nine data centres; encryption status Linux only and firewall Windows only
through the API; exclude the encryption and firmware password scopes [xplat-a D].

**Addigy**: check the key's own permissions with `GET /api/v2/configuration/permissions` and refuse a key with
more than View rights; build the read allowlist by hand, because the Swagger file's `x-mcp-readonly` marker is
not a reliable list (it marks 77 operations, only one of them a GET) [apple-mdms 7, verify-apple].

**SimpleMDM**: refuse a key that holds Device Secrets; `show_secrets` defaults to true on existing keys, and
`include_secret_custom_attributes` must stay off [apple-mdms 8, verify-apple].

**Mosyle**: do not build until Mosyle provides a reference and a token only method (D-DEV-15, D-DEV-16).

**Fleet**: require Fleet Premium's endpoint allowlist for the API only user, or show the secrets warning; write
a small `net/http` client (importing Fleet's `server/service` pulls in `ee/` code) [xplat-b 9]. For
`devices.wipes_confirmed` read `mdm.device_status` wiped or the command result; the `wiped_host` activity is
logged when a wipe is sent, not when it finishes [verify-xplat X3].

**NinjaOne**: thin for compliance (Windows encryption and antivirus, patches, software); its `monitoring`
scope spans the whole account. NinjaOne's own OAuth pages disagree on client credentials, so the connect step
tests the token before saving [verify-xplat X7].

**JumpCloud credential**: the service account with the Read Only role is the documented path; whether a Read
Only admin's personal API key behaves the same is unverified, so the setup guide offers only the service
account [verify-xplat X6].

**Rippling devices**: encryption, enrolment, MDM provider, lifecycle (wiped, lost, sold), worker, queued
actions and warehouse return orders, next to the HR worker record in the same tenant: the strongest single
source for `devices.leaver_devices_recovered` [xplat-b 3.3].

**1Password Device Trust (Kolide)**: agent only, built for personal and contractor devices, read only keys,
pass or fail per check with issue history; 270 requests a minute; pin the API version header [xplat-b 3.4].

**Apple Business API**: the purchase population for every Apple MDM; poll `GET /v1/orgDevices` (cursor,
up to 1,000 a page), the assigned server, and `activationLockStatus`; never create webhooks (a write)
[apple 4.2]. Its built in MDM exposes FileVault, firewall, erase and lock status through `GET /v1/mdmDevices`,
which could make it an Apple source with no vendor in between (D-MDM-15).
