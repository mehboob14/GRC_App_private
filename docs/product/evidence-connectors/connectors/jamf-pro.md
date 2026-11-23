# Jamf Pro

| | |
|---|---|
| Capabilities | device_management (macOS, iOS, iPadOS) |
| Delivery phase | Not in the signed catalogue. `capabilities.json` lists `jamf` as `not_planned` (decision D-DEV-1) |
| Auth model | Jamf Pro API Roles and Clients: OAuth 2.0 client credentials against the customer's Jamf Pro URL |
| Shares setup with | Nothing. Jamf Pro is a separate account from the identity provider |
| Go library | No official Jamf Go SDK. Community SDK `github.com/deploymenttheory/go-api-sdk-jamfpro` exists (not Jamf's, status not re-checked). Plan: plain REST |

Check definitions: [mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue).

## 1. What it proves

For Mac fleets, Jamf Pro holds the richest per device security inventory of the MDMs in this plan:
managed and supervised state, user approved MDM, enrolment through Automated Device Enrollment, FileVault
state and recovery key validity, firewall, Gatekeeper, System Integrity Protection, XProtect version,
bootstrap token escrow, OS version and pending software updates, the assigned user, and every MDM command
sent with its completion time.

It does not report the screen saver idle time as an inventory field. Screen lock comes from the
configuration profiles the customer deploys (or an extension attribute the customer adds). It has no
company or personal flag for computers. It does not cover Windows.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

The customer creates an API Role with read privileges and an API Client that holds it, in Jamf Pro
Settings, System, API Roles and Clients (Jamf Pro 10.49.0 or later) [S1][S11]. Verity stores the client
id and secret and requests a token from `/api/v1/oauth/token` (client credentials) [S9]. Corrected: Jamf
gives no fixed lifetime; tokens are short lived, the lifetime is set per client and each token response
carries `expires_in` [S1][S9]. A client's access is the sum
of its roles' privileges. Adding or removing a role on an existing client needs a secret rotation; editing a role's
privileges applies to new tokens at once [S1].

### 2.2 Privileges

| Privilege (API Role) | Read only | Needed for | Who can grant |
|---|---|---|---|
| `Read Computers` | yes | `/v4/computers-inventory`: every devices.* check on macOS [S2] | a Jamf Pro administrator with rights to manage API Roles and Clients |
| `Read macOS Configuration Profiles` | yes | `devices.screen_lock`, `devices.removable_storage_restricted`: profile payloads and scope through the Classic API `osxconfigurationprofiles` routes [S13] (Vanta asks for it to verify screen lock enforcement [S3]) | same |
| `Read Mobile Devices` | yes | iOS and iPadOS inventory (`/v2/mobile-devices/detail`) [S10] | same |
| `View MDM command information in Jamf Pro API` | yes | `devices.wipes_confirmed`, `devices.leaver_devices_recovered` [S4] | same |

Not requested: any Create, Update or Delete privilege, `Send Computer Remote Wipe Command`, `View
Disk Encryption Recovery Key` or similar. The FileVault inventory endpoint needs that recovery key
privilege and returns personal recovery keys, so Verity never calls it [S6].

### 2.3 Licence and prerequisites

Jamf Pro (cloud or self hosted). Jamf Now and Jamf School are different products. The computers
inventory endpoints in the Jamf Pro API arrived in 10.39.0, and the Classic API computer endpoints are
deprecated from 11.15.0, with support for one more year and no removal date given [S5]. API Roles and
Clients need Jamf Pro 10.49.0 or later [S1][S11].
Vanta supports Jamf Pro Cloud only and macOS only [S3]; Verity can support self hosted Jamf Pro if the
instance is reachable from Verity's egress addresses (customer firewall rule).

## 3. Customer setup guide (draft product text)

1. In Jamf Pro, open Settings, then System, then API Roles and Clients.
2. Create a role named "Verity read only" with: Read Computers, Read macOS Configuration Profiles, Read
   Mobile Devices, and View MDM command information in Jamf Pro API. Nothing else.
3. Create an API client named "Verity", give it that role, enable it, and generate a client secret. Copy
   it now: Jamf cannot show it again.
4. In Verity, paste your Jamf Pro URL (for example `https://yourcompany.jamfcloud.com`), the client id
   and the secret.
5. Tell Verity which configuration profile sets your screen lock, or let Verity find profiles with a
   screen saver payload.
6. Choose whether computers enrolled outside Automated Device Enrollment count as company owned.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Computers | `GET /api/v4/computers-inventory` with `section=GENERAL, DISK_ENCRYPTION, SECURITY, OPERATING_SYSTEM, USER_AND_LOCATION, HARDWARE, CONFIGURATION_PROFILES, SOFTWARE_UPDATES` (detail: `/v4/computers-inventory/{id}`) [S2] | general: `remoteManagement.managed`, `supervised`, `mdmCapable`, `userApprovedMdm`, `enrolledViaAutomatedDeviceEnrollment`, `enrollmentMethod`, `managementId`, `lastContact`, `lastCheckIn` (seen in the filter list, not the schema), `reportDate`, `lastEnrolledDate`; diskEncryption: `fileVault2Enabled`, `bootPartitionEncryptionDetails.partitionFileVault2State`, `individualRecoveryKeyValidityStatus`, `institutionalRecoveryKeyPresent`; security: `firewallEnabled`, `gatekeeperStatus`, `sipStatus`, `xprotectVersion`, `activationLockEnabled`, `autoLoginDisabled`, `bootstrapTokenEscrowedStatus`, `secureBootLevel`; operatingSystem: `version`, `build`, `rapidSecurityResponse`; userAndLocation: `username`, `email`; hardware: `serialNumber`; installed configuration profiles and available software updates (top level arrays returned by their sections) [S2] | `page`, `page-size` (default page 0, size 100 [S2]), RSQL `filter`, `sort` (default `general.name:asc`). No hard rate limit; Jamf asks for at most 5 concurrent connections, exponential backoff, and a full inventory sync no more than once a day, filtered by report date in between [S7] | while the record exists |
| macOS configuration profiles | Classic API `GET /JSSResource/osxconfigurationprofiles` lists id and name; no Jamf Pro API equivalent was found [S12]. The by id route that returns payloads and scope was not read (unverified) | payload types and the keys Verity evaluates (screen saver idle time and password requirement; media restrictions), scope | as above | current |
| MDM commands | `GET /api/v2/mdm/commands` with a filter (filterable: uuid, clientManagementId, command, status, clientType, dateSent, validAfter, dateCompleted, profileIdentifier, profileId, active; dates take gt, lt, ge, le) [S4] | `commandType`, `commandState` (filter key `status`), `dateSent`, `dateCompleted`, `client.managementId`, `client.clientType`, `commandError` [S4] | Jamf's reference says every call needs at least one filter field, though the schema marks it optional [S4]; `page`, `page-size` 0 and 100 by default | not stated (unverified) |
| Mobile devices | `GET /api/v2/mobile-devices/detail` [S10] | `general.supervised`, `general.managed`, `general.deviceOwnershipType` (Institutional, UserEnrollment, AccountDrivenUserEnrollment, AccountDrivenDeviceEnrollment), `general.lastInventoryUpdateDate`, `security.passcodePresent`, `security.dataProtected`, `security.hardwareEncryption`, `hardware.serialNumber`, `userAndLocation.emailAddress` [S10] | as above | |

## 5. Checks

### 5.1 Existing checks: feasibility on Jamf Pro

| Check | Feasible | How | Gaps |
|---|---|---|---|
| `devices.enrolled` | yes | `remoteManagement.managed` true and last check in within the window | Unmanaged records still listed in Jamf fail; never enrolled Macs are invisible |
| `devices.disk_encrypted` | yes | `fileVault2Enabled` or boot partition state encrypted [S2] | `partitionFileVault2State` has 11 values (UNKNOWN, UNENCRYPTED, INELIGIBLE, DECRYPTED, DECRYPTING, ENCRYPTED, ENCRYPTING, RESTART_NEEDED, OPTIMIZING, and the two paused states) [S2]: only ENCRYPTED shows the volume is encrypted now |
| `devices.screen_lock` | partial | A profile with a screen saver payload whose idle time is at or under the limit and that requires a password, installed on the device (CONFIGURATION_PROFILES section) | No live value. A lock set by script or by the user is not seen: `insufficient`. Drata uses customer uploaded scripts for this [S8] |
| `devices.os_current` | yes | `operatingSystem.version` and build against the minimum; SOFTWARE_UPDATES lists pending updates | |
| `devices.remote_wipe` | yes | managed, `mdmCapable` and (for Apple silicon) bootstrap token escrowed | Which combination Apple requires for an erase on each Mac generation is not stated by Jamf here: unverified (Apple's deployment guide not read) |

### 5.2 New checks: feasibility on Jamf Pro

| Check (NEW) | Feasible | How | Gaps |
|---|---|---|---|
| `devices.recovery_key_escrowed` | yes | `individualRecoveryKeyValidityStatus` VALID, or `institutionalRecoveryKeyPresent` true [S2] | Validity values are VALID, INVALID, UNKNOWN, NOT_APPLICABLE [S2] |
| `devices.firewall_enabled` | yes | `security.firewallEnabled` [S2] | |
| `devices.assigned_to_active_staff` | yes, with an IdP | `userAndLocation.email` joined to the identity provider | Jamf's user field is often free text: email match only, never display name |
| `devices.staff_have_managed_device` | yes, with an IdP | as above, in the person direction | |
| `devices.leaver_devices_recovered` | partial | Leaver's devices then an erase command with `dateCompleted`, an unmanage, or reassignment | Needs Verity's own daily history and an HR source |
| `devices.wipes_confirmed` | yes | `ERASE_DEVICE` commands sent in the window with `commandState` and `dateCompleted` [S4] | `commandState` values are PENDING, ACKNOWLEDGED, NOT_NOW, ERROR, COMMAND_FORMAT_ERROR [S4]; how long commands are kept is not stated (unverified) |
| `devices.removable_storage_restricted` | partial | A restrictions profile blocking external media installed on the device | Payload keys to confirm |

Antivirus: `xprotectVersion` shows Apple's built in protection only. It does not satisfy
`endpoint.protection_active`; use an endpoint_protection provider (Jamf Protect is one, not researched
here).

## 6. Artifacts and objectives it fills

Same as [intune.md section 6](intune.md#6-artifacts-and-objectives-it-fills), for Macs: device inventory
(EP-03.B, EP-03.C, EP-05.B), screen lock report (EP-06.B, EP-06.C), patch report (EP-04.C), wipe
confirmations (EP-05.C, EP-05.D), removable storage settings (DM-19.C), and devices as assets (LM-01.C).

## 7. Framework reach

Same controls and references as Intune: SOC 2 CC6.1, CC6.5, CC6.7, CC6.8, CC7.1, CC2.1; ISO 27001:2022
A.5.9, A.5.11, A.6.7, A.7.7, A.7.9, A.7.10, A.7.14, A.8.1, A.8.8, A.8.19, A.8.24. All partial.

## 8. Limits and false assurance traps

- **Profile installed is not setting effective.** A higher priority profile or a user setting can
  differ. The evidence says the value came from a profile.
- **Managed is not supervised.** Some protections and the erase behaviour differ for unsupervised
  devices. The device observation keeps both.
- **Smart group membership is not state.** Never evaluate from smart group names; read the fields.
- **Self hosted instances** may lag on versions: v4 inventory may not exist (its first version is not
  stated: unverified). Detect the version and fall back to v1 (from 10.39.0), never to the deprecated
  Classic API computer endpoints. Only those are deprecated; configuration profiles are still read
  through the Classic API [S5][S12].

## 9. Product and UI

Connect form: Jamf Pro URL, client id, client secret. Settings: screen lock profile (pick or auto
detect), ADE only counts as company owned (yes or no), minimum macOS version, out of contact days.
Health: token rejected (`error`), privilege missing per section (only its checks `error`), slow responses
(backoff, `truncated`). In product guide: yes, with screenshots of API Roles and Clients.

## 10. Implementation notes

Fetch a token per run and renew it before `expires_in` runs out; refresh on 401 once. Page through computers with at most 5
concurrent requests [S7]. Daily full read; no webhooks in the first version. Fixtures: a supervised ADE
Mac, a user enrolled Mac, an unmanaged record, a Mac with FileVault off, one with an invalid recovery
key, an erase command pending and one completed. A Jamf Pro sandbox needs a Jamf trial or partner
instance (availability unverified: not checked). Deletion: a removed computer disappears; record `disappeared`.

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | OAuth through API Roles and Clients with read only privileges, including Read macOS Configuration Profiles, Read Accounts and Read Static Computer Groups; Jamf Pro Cloud only; macOS only [S3] | FileVault, screen lock from profile keys (`askForPassword`, `askForPasswordDelay`, `loginWindowIdleTime`), antivirus, password manager, OS version |
| Drata | A Jamf Pro standard account with the Auditor privilege set; two customer uploaded extension attribute scripts report screen saver lock and automatic updates; device email in User and Location matches people [S8] | screen saver lock, automatic updates, password manager from the application list. Corrected: the guide does not mention encryption |
| Secureframe | Read Computers, Read Mobile Devices, Read macOS Configuration Profiles; bearer token from 11.5.0 [S14] | screen lock, built in antivirus, firewall, disk encryption, password, device present |
| Sprinto | Not researched in this round: unverified | |

## 12. Sources

- [S1] Jamf Pro client credentials: https://developer.jamf.com/jamf-pro/docs/client-credentials
- [S2] Get computer inventory v4: https://developer.jamf.com/jamf-pro/reference/get_v4-computers-inventory-id
- [S3] Vanta, connecting Jamf Pro: https://help.vanta.com/en/articles/11345770-connecting-vanta-jamf-pro
- [S4] MDM commands v2: https://developer.jamf.com/jamf-pro/reference/get_v2-mdm-commands and Platform API variant https://developer.jamf.com/platform-api/reference/get_v1-tenant-tenantid-mdm-commands
- [S5] Deprecation of Classic API computer inventory endpoints: https://developer.jamf.com/jamf-pro/docs/deprecation-of-classic-api-computer-inventory-endpoints
- [S6] FileVault inventory v4: https://developer.jamf.com/jamf-pro/reference/get_v4-computers-inventory-filevault
- [S7] Jamf Pro API scalability best practices: https://developer.jamf.com/jamf-pro/docs/jamf-pro-api-scalability-best-practices
- [S8] Drata, Jamf integration guide: https://help.drata.com/en/articles/5456409-jamf-integration-guide
- [S9] Jamf Pro API token endpoint: https://developer.jamf.com/jamf-pro/reference/postoauthtoken
- [S10] Mobile device detail v2: https://developer.jamf.com/jamf-pro/reference/get_v2-mobile-devices-detail
- [S11] Jamf, understanding API Roles and Clients: https://www.jamf.com/blog/understanding-jamf-pro-api-roles-and-clients/
- [S12] Classic API macOS configuration profiles: https://developer.jamf.com/jamf-pro/reference/findosxconfigurationprofiles
- [S13] Classic API privileges and endpoint mapping: https://developer.jamf.com/jamf-pro/docs/classic-api-minimum-required-privileges-and-endpoint-mapping
- [S14] Secureframe, supported MDMs: https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
