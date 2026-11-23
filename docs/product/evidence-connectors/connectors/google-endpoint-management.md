# Google endpoint management (devices in Google Workspace)

| | |
|---|---|
| Capabilities | device_management |
| Delivery phase | Not in the signed catalogue as a device source. Google Workspace is a Phase 2 identity provider (`gws`); its device side is not listed in `capabilities.json` (decisions D-DEV-1 and D-DEV-13) |
| Auth model | Service account with domain wide delegation impersonating an administrator (required for the Cloud Identity Devices API scopes), read only scopes |
| Shares setup with | The Google Workspace identity connector (same service account and delegation screen, extra scopes) |
| Go library | `google.golang.org/api/cloudidentity/v1`, `google.golang.org/api/admin/directory/v1`, `golang.org/x/oauth2/google` (JWT config with a subject for impersonation) (paths confirmed on pkg.go.dev [S11]) |

Check definitions: [mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue).

## 1. What it proves

Google Workspace knows every device that touches a Workspace account: phones and tablets under basic
or advanced mobile management, ChromeOS devices, and Windows, macOS and Linux computers that run Endpoint
Verification (a Chrome extension, plus a helper for some signals). For each it reports ownership
(company or personal), encryption state, OS version, last sync, serial number, management state including
wiping and wiped, and for desktops a set of security signals: disk encryption, screen lock, native
firewall and, on Windows with the helper, antivirus [S1][S2].

This matters for the no MDM question: Endpoint Verification is available on almost every Workspace
edition, including Business Starter [S3], so a Workspace customer without an MDM can still produce
system generated device evidence. It does not enforce anything on desktops, does not report the screen
lock timeout (only whether a password or lock is set), and cannot wipe a computer (Windows device
management aside, not researched).

## 2. Connecting: method, credentials and permissions

### 2.1 Method

Reuse the identity connector's service account. The customer's super administrator adds the device
scopes to the domain wide delegation entry. The Cloud Identity Devices API scopes require domain wide
delegation: Google does not support a service account calling the Devices API directly, so it must
impersonate an administrator through delegation (or use end user OAuth) [S12]. The impersonated
administrator needs device read rights (a custom read only admin role with mobile and device management
view rights: exact privilege names unverified, Google's setup page does not name them [S12]).

### 2.2 Scopes

| Scope | Read only | Needed for | Who can grant |
|---|---|---|---|
| `https://www.googleapis.com/auth/cloud-identity.devices.readonly` | yes | all devices.* checks for computers, phones and ChromeOS through the Devices API [S4] | super administrator (delegation) |
| `https://www.googleapis.com/auth/admin.directory.device.mobile.readonly` | yes | mobile details through the Directory API (password status, compromised status, patch level) [S5] | same |
| `https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly` | yes | ChromeOS details: OS version, auto update end date, update status [S6][S13] | same |
| `https://www.googleapis.com/auth/admin.reports.audit.readonly` | yes | wipe history from the admin audit log: application `mobile`, event `DEVICE_ACTION_EVENT` with `ACTION_TYPE` `DEVICE_WIPE` or `ACCOUNT_WIPE` and `ACTION_EXECUTION_STATUS` [S14][S15] | same |

Not requested: `cloud-identity.devices` (write), `admin.directory.device.mobile.action` (wipe, block).

### 2.3 Editions

- Basic mobile management: available on nearly all editions; reports OS version and encryption; can wipe
  the work account but not the whole device [S7][S8].
- Advanced mobile management adds full device wipe and device approvals; not available on Business
  Starter, Business Standard, Education Fundamentals, Essentials or Cloud Identity Free [S8].
- Endpoint Verification: Frontline, Business, Enterprise, Education, Essentials, Nonprofits, legacy G Suite
  Basic and Business, and Cloud Identity Free and Premium; usually on by default [S3].

## 3. Customer setup guide (draft product text)

1. Connect Google Workspace first. Open it and choose **Add devices**.
2. Verity shows the extra read only scopes. Copy them into Admin console, Security, API controls, Domain
   wide delegation, on the Verity entry.
3. For laptops without an MDM: turn on Endpoint Verification in Admin console, Devices, and ask staff to
   install the Chrome extension (and the helper on Windows for antivirus).
4. In Verity, choose whether personal devices count.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Devices | `GET https://cloudidentity.googleapis.com/v1/devices?customer=customers/my_customer` with `view=COMPANY_INVENTORY` and again with `USER_ASSIGNED_DEVICES` [S4] | `name`, `deviceType` (ANDROID, IOS, GOOGLE_SYNC, WINDOWS, MAC_OS, LINUX, CHROME_OS, GOOGLEBOOK), `ownerType` (COMPANY, BYOD), `encryptionState` (ENCRYPTED, NOT_ENCRYPTED, UNSUPPORTED_BY_DEVICE), `managementState` (APPROVED, BLOCKED, PENDING, UNPROVISIONED, WIPING, WIPED), `compromisedState`, `osVersion`, `securityPatchTime`, `lastSyncTime`, `serialNumber`, `hostname`, `model`, `deviceId`, `endpointVerificationSpecificAttributes.additionalSignals` (keys `av_installed`, `av_enabled`, `is_os_native_firewall_enabled`, `is_secure_boot_enabled`, `hotfixes`, `windows_domain_name`, plus admin configured file, registry and plist signals) [S1] | `pageSize` default 20, up to 100, `pageToken` [S4]; quotas not read (unverified: not checked) | how long inactive devices stay listed: unverified (not stated on the pages read) |
| Device users | `GET /v1/devices/{device}/deviceUsers` [S9] | `userEmail`, `managementState` (APPROVED, BLOCKED, PENDING_APPROVAL, UNENROLLED, WIPING, WIPED), `passwordState` (PASSWORD_SET, PASSWORD_NOT_SET), `compromisedState`, `firstSyncTime`, `lastSyncTime` | per device call | |
| Mobile devices | `GET https://admin.googleapis.com/admin/directory/v1/customer/{customerId}/devices/mobile` [S5] | `status`, `type`, `os`, `model`, `serialNumber`, `email`, `lastSync`, `encryptionStatus`, `devicePasswordStatus`, `deviceCompromisedStatus`, `securityPatchLevel`, `privilege`, `adbStatus`, `developerOptionsStatus`, `unknownSourcesStatus` [S10] | `maxResults` up to 100 [S5] | |
| ChromeOS devices | Directory API `chromeosdevices` [S6] | `status`, `lastSync`, `osVersion`, `osVersionCompliance`, `osUpdateStatus`, `autoUpdateThrough` (replaces the deprecated `autoUpdateExpiration`), `annotatedUser`, `recentUsers`, `serialNumber` | `maxResults` up to 300 [S13] | |

What Endpoint Verification collects per platform (OS version, disk encryption, screen lock, native
firewall on macOS, Windows, Linux and ChromeOS; antivirus and hotfixes on Windows only with the helper)
is documented [S2]; the page says only whether a screen lock is enabled. Corrected: `additionalSignals`
has no screen lock key [S1]. The only candidate is `deviceUsers.passwordState` (PASSWORD_SET or
PASSWORD_NOT_SET), which Google describes as a password on the device user without saying it is the
desktop screen lock [S9] (unverified: confirm on fixtures).

## 5. Checks

### 5.1 Existing checks: feasibility on Google

| Check | Feasible | How | Gaps |
|---|---|---|---|
| `devices.enrolled` | partial | `managementState` APPROVED and `lastSyncTime` within the window | Endpoint Verification is inventory, not management. Decision: count it as "known", not "managed" (strategy section 7). Default: desktops seen only through Endpoint Verification fail `devices.enrolled` with reason "reported, not managed" |
| `devices.disk_encrypted` | yes | `encryptionState` ENCRYPTED [S1] | |
| `devices.screen_lock` | no for the timeout | lock or password set only | The idle timeout is not reported: result `insufficient` with that reason, never pass |
| `devices.os_current` | yes | `osVersion`, `securityPatchTime` (mobile), `osVersionCompliance` (ChromeOS) | |
| `devices.remote_wipe` | partial | Advanced management and company owned: full wipe; basic: account wipe only [S7][S8] | Desktops without Windows device management: no wipe, `fail` with reason |

### 5.2 New checks: feasibility on Google

| Check (NEW) | Feasible | How | Gaps |
|---|---|---|---|
| `devices.recovery_key_escrowed` | no | not reported | `insufficient` |
| `devices.firewall_enabled` | yes (corrected from likely) | `additionalSignals.is_os_native_firewall_enabled` [S1], collected on Windows, macOS, Linux and ChromeOS [S2] | value type to confirm on fixtures |
| `devices.assigned_to_active_staff` | yes | `deviceUsers.userEmail` to the Workspace user's state (identity connector) | |
| `devices.staff_have_managed_device` | yes | person direction | depends on the `devices.enrolled` decision above |
| `devices.leaver_devices_recovered` | partial | device or device user `managementState` WIPED after the leaver's end date | account wipe on a personal phone counts only if the policy says so |
| `devices.wipes_confirmed` | partial | WIPING then WIPED transitions in Verity's daily history; admin audit log `DEVICE_ACTION_EVENT` with its execution status as the event source [S14] | the audit query reaches back 180 days by default [S15] |
| `devices.removable_storage_restricted` | no | not reported | |

`endpoint.protection_active`: not implemented here. Endpoint Verification's antivirus signal on Windows
says an antivirus product is installed and on; it is not an EDR's health. It can feed
`endpoint.coverage_complete` only as the device population.

## 6. Artifacts and objectives it fills

Device inventory (EP-03.B, EP-03.C), encryption (EP-02.B), OS currency (EP-04.C), wipe state (EP-05.B,
EP-05.C for phones), devices as assets (LM-01.C). Screen lock artifacts stay with people.

## 7. Framework reach

EP-02, EP-03, EP-04, EP-05, LM-01: SOC 2 CC6.1, CC6.5, CC6.7, CC6.8, CC7.1, CC2.1; ISO 27001:2022 A.5.9,
A.5.11, A.6.7, A.7.9, A.7.10, A.7.14, A.8.1, A.8.8, A.8.24. All partial; EP-06 not reached.

## 8. Limits and false assurance traps

- **Known is not managed.** Endpoint Verification reports what the browser and helper can see on a
  device nobody manages. It cannot enforce or wipe. Saying "managed" would overstate EP-03.
- **Signals from user space.** The helper runs as the signed in user and sees only what that user can
  see [S2].
- **Personal phones.** Most phones in Workspace are BYOD with basic management. Ownership decides whether
  they are in the population.
- **Duplicates.** The same laptop can appear through Endpoint Verification and through another MDM.
  Match on serial number before counting.

## 9. Product and UI

Settings on the Google Workspace connection: device types in scope, personal devices in or out, whether
Endpoint Verification desktops count as managed (default no). Health: delegation scope missing (device
checks `error`), Endpoint Verification off (desktop population empty: `insufficient` with a hint). In
product guide: yes, including how staff install Endpoint Verification.

## 10. Implementation notes

JWT with `Subject` set to the delegated administrator. Two list views are needed: company inventory
(includes unassigned imported devices) and user assigned devices [S4]. Device users need a call per
device: batch and respect 429. Fixtures: an Android work profile, a company iPhone, a Mac and a Windows
laptop with Endpoint Verification (Windows with and without helper), a wiped device.

## 11. How comparable platforms do it

Whether Vanta, Drata, Secureframe or Sprinto read Google Workspace devices as an MDM source was not
researched in this round (unverified: not checked). Secureframe's list of supported device sources does
not include Google Workspace [S16].

## 12. Sources

- [S1] Cloud Identity Devices resource: https://docs.cloud.google.com/identity/docs/reference/rest/v1/devices
- [S2] Endpoint Verification device information: https://docs.cloud.google.com/endpoint-verification/docs/device-information
- [S3] Turn Endpoint Verification on or off (editions): https://knowledge.workspace.google.com/admin/devices/turn-endpoint-verification-on-or-off
- [S4] devices.list: https://docs.cloud.google.com/identity/docs/reference/rest/v1/devices/list
- [S5] Directory API mobiledevices.list: https://developers.google.com/workspace/admin/directory/reference/rest/v1/mobiledevices/list
- [S6] Directory API chromeosdevices: https://developers.google.com/workspace/admin/directory/reference/rest/v1/chromeosdevices
- [S7] Set up basic mobile device management: https://knowledge.workspace.google.com/admin/devices/set-up-basic-mobile-device-management
- [S8] Compare mobile management features: https://knowledge.workspace.google.com/admin/devices/compare-mobile-management-features
- [S9] devices.deviceUsers: https://docs.cloud.google.com/identity/docs/reference/rest/v1/devices.deviceUsers
- [S10] Directory API mobiledevices resource: https://developers.google.com/workspace/admin/directory/reference/rest/v1/mobiledevices
- [S11] Go packages: https://pkg.go.dev/google.golang.org/api/cloudidentity/v1 , https://pkg.go.dev/google.golang.org/api/admin/directory/v1 , https://pkg.go.dev/golang.org/x/oauth2/google
- [S12] Set up the Devices API (delegation): https://docs.cloud.google.com/identity/docs/how-to/setup-devices
- [S13] Directory API chromeosdevices.list (scopes, page size): https://developers.google.com/workspace/admin/directory/reference/rest/v1/chromeosdevices/list
- [S14] Reports API mobile device audit events: https://developers.google.com/workspace/admin/reports/v1/appendix/activity/mobile
- [S15] Reports API activities.list (scope, 180 day default reach): https://developers.google.com/workspace/admin/reports/reference/rest/v1/activities/list
- [S16] Secureframe, supported MDMs: https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
