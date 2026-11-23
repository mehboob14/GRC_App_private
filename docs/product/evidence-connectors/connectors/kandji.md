# Kandji (now Iru Endpoint Management)

| | |
|---|---|
| Capabilities | device_management (Apple platforms: Mac, iPhone, iPad, Apple TV in the API's platform filter) |
| Delivery phase | Not in the signed catalogue. `capabilities.json` lists `kandji` as `not_planned` (decision D-DEV-1). Kandji announced its rename to Iru on 22 October 2025 and switched in product branding on 8 April 2026; the API keeps the kandji.io hosts [S3][S6] (D-DEV-11 on naming) |
| Auth model | Bearer API token created by a tenant administrator, with per endpoint permissions |
| Shares setup with | Nothing |
| Go library | None official. Plain REST against the published OpenAPI file [S1] |

Check definitions: [mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue).

## 1. What it proves

Per Apple device: enrolment and agent state, last check in, OS version, serial, assigned user, blueprint,
FileVault on or off, and (through Prism, Kandji's fleet reporting) FileVault, application firewall,
desktop and screen saver, Gatekeeper and XProtect, activation lock and installed profiles across the
fleet. It also lists every MDM command sent to a device with its completion time.

The published API still lists Apple platform values only [S1]. Corrected: the Iru product itself now
manages Windows and Android as well, and the 2026 Iru agent release rebranded the Mac and Windows agents
[S3]; whether the device list returns Windows or Android records is not stated (unverified). Prism's
desktop and screen saver category documents no idle time or password column in the file [S1].

## 2. Connecting: method, credentials and permissions

### 2.1 Method

The customer creates an API token in Access (account menu in the sidebar, then Access, API tokens;
older Kandji consoles say Settings, Access) and chooses the endpoints it may call. The token is shown
once [S2]. Deleting the administrator who created a token deletes the token; suspending them does not
[S2]. API URL formats:
`https://SubDomain.api.kandji.io` (US) and `https://SubDomain.api.eu.kandji.io` (EU) [S1]. Tenants
migrated to Iru may also use `subdomain.api.iru.com` under `/api/v1`; the kandji.io hosts keep working [S3].

### 2.2 Permissions

Kandji names permissions after endpoints, grouped in sections. Iru documents the labels Device list,
Device details, Device ID, Application list, Device Library Items, Device Information and Device Activity
[S7]. The labels for commands, Prism and Users below follow the endpoint summaries in the OpenAPI file
and are unverified as permission labels (not shown on the pages read).

| Permission (endpoint) | Read only | Needed for | Who can grant |
|---|---|---|---|
| Device list (`GET /api/v1/devices`) | yes | all devices.* checks (population) | a Kandji administrator with access to Settings, Access |
| Device details (`GET /api/v1/devices/{id}/details`) | yes | `devices.disk_encrypted`, `devices.recovery_key_escrowed`, `devices.remote_wipe` | same |
| Device commands (`GET /api/v1/devices/{id}/commands`) | yes | `devices.wipes_confirmed`, `devices.leaver_devices_recovered` | same |
| Device library items or status (`GET /api/v1/devices/{id}/library-items`, `/status`) | yes | `devices.removable_storage_restricted`, profile based screen lock | same |
| Prism categories (`GET /api/v1/prism/filevault`, `application_firewall`, `desktop_and_screensaver`, `device_information`, `gatekeeper_and_xprotect`) | yes | `devices.firewall_enabled`, `devices.screen_lock`, fleet wide reads | same |
| Users (`GET /api/v1/users`) | yes | matching devices to people | same |

Never granted: the secrets endpoints (`/secrets/filevaultkey`, `/secrets/bypasscode`, `/secrets/unlockpin`,
`/secrets/recoverypassword`) [S1], any device action (`/action/erase` and others), any write.

### 2.3 Plan and limits

Rate limit 10,000 requests per hour per customer, shared by every token in the tenant and by Iru's own
compliance evidence collection [S1][S2]. Which Kandji plans include the API was not confirmed
(unverified: neither the API overview nor the specification says).

## 3. Customer setup guide (draft product text)

1. In Kandji (Iru), open Access from the account menu (older consoles: Settings, Access). Copy your API URL.
2. Add an API token named "Verity". Copy it now; it is shown once.
3. Give it read permissions only: Device list, Device details, Device commands, Device library items,
   Prism, Users. Do not give it secrets or device actions.
4. In Verity, paste the API URL and the token.
5. Choose the blueprints in scope. Blueprints left out need a reason.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Devices | `GET /api/v1/devices` [S1] | `device_id`, `device_name`, `serial_number`, `platform`, `os_version`, `model`, `last_check_in`, `user`, `blueprint_id`, `blueprint_name`, `mdm_enabled`, `agent_installed`, `agent_version`, `is_missing`, `is_removed`, `first_enrollment`, `last_enrollment`, `lost_mode_status`, `tags` | `limit` (hard maximum 300) and `offset` [S1]; 10,000 requests an hour. The file has no success schema for the list; the field names come from its device example | removed devices keep `is_removed` (how long: unverified, not documented) |
| Device details | `GET /api/v1/devices/{id}/details` | FileVault state and personal recovery key escrow, MDM and supervision state (still unverified: the file defines no success schema or example for this endpoint; a Kandji update note and third party samples show `filevault_enabled`, `filevault_prk_escrowed`, `filevault_recoverykey_type`) [S1][S4] | one call per device: 300 devices cost 300 calls | current |
| Prism | `GET /api/v1/prism/{category}` for filevault, application_firewall, desktop_and_screensaver, device_information, gatekeeper_and_xprotect, installed_profiles [S1] | per device rows. application_firewall: `status`, `block_all_incoming`, `logging`, `logging_option`, `stealth_mode`, `version`, `allow_signed_applications`, `unloading`. filevault: `status`, `key_type`, `key_escrowed`, `regeneration_needed`, `scheduled_key_rotation` [S1]. desktop_and_screensaver: the example shows only the common device columns (idle time column unverified) | `limit` (maximum 300), `offset`, `filter`, `sort_by`, `blueprint_ids`, `device_families`; large categories via `POST prism/export` then `GET prism/export/{id}` (a signed URL); the export category list may lack application_firewall and filevault, so check before relying on export [S1] | current |
| Device commands | `GET /api/v1/devices/{id}/commands` [S1] | `uuid`, `command_type`, `status` (an integer; code meanings not documented [S1]), `date_requested`, `date_completed`, `attempts`, `error_chain` | `limit`, `offset` | unverified (not documented) |
| Device activity | `GET /api/v1/devices/{id}/activity` | activity entries | `limit` (required), `offset` | unverified (not documented) |
| Users | `GET /api/v1/users` [S1] | email, id, archived state | cursor paging; filters `email`, `id`, `integration_id`, `archived` | current |

Prefer Prism for fleet wide state (a few calls) and device details only where Prism lacks a field. The
list's `filevault_enabled` filter lets a run fetch unencrypted Macs directly [S1].

## 5. Checks

### 5.1 Existing checks: feasibility on Kandji

| Check | Feasible | How | Gaps |
|---|---|---|---|
| `devices.enrolled` | yes | `mdm_enabled` true, not `is_removed`, `last_check_in` within the window. `agent_installed` alone (no MDM) fails | Never enrolled devices invisible |
| `devices.disk_encrypted` | yes (Mac) | list filter `filevault_enabled` or Prism filevault | iOS data protection follows passcode: read from details (unverified: details has no documented schema) |
| `devices.screen_lock` | partial | The device's status for the passcode or screen saver library item; Prism desktop and screen saver documents no idle time column [S1] | Prism alone gives `insufficient` unless a recorded response shows the idle time |
| `devices.os_current` | yes | `os_version` against the minimum | Pending updates not read |
| `devices.remote_wipe` | yes | `mdm_enabled` and supervision from details | Supervision field name unverified (not in the specification) |

### 5.2 New checks: feasibility on Kandji

| Check (NEW) | Feasible | How | Gaps |
|---|---|---|---|
| `devices.recovery_key_escrowed` | yes (corrected from likely) | Prism filevault `key_escrowed` [S1] | the details route has no documented field |
| `devices.firewall_enabled` | yes | Prism application_firewall `status` [S1] | status values to confirm on fixtures |
| `devices.assigned_to_active_staff` | yes, with an IdP | `user` (or `GET /api/v1/users` email) to the IdP | |
| `devices.staff_have_managed_device` | yes, with an IdP | person direction of the same join | |
| `devices.leaver_devices_recovered` | partial | erase command completed (`date_completed`), removal, or reassignment after the leaver's end date | status code meanings unknown: treat only a set `date_completed` as done |
| `devices.wipes_confirmed` | partial | erase commands in the window with `date_completed` | as above |
| `devices.removable_storage_restricted` | partial | library item status for a restrictions profile | |

## 6. Artifacts and objectives it fills

As for Jamf Pro and Intune (device inventory, screen lock report, patch report, wipe confirmations,
removable storage settings, devices as assets): EP-03.B, EP-03.C, EP-05.B, EP-06.B, EP-06.C, EP-04.C,
EP-05.C, EP-05.D, DM-19.C, LM-01.C.

## 7. Framework reach

Same as [intune.md section 7](intune.md#7-framework-reach), Apple devices only.

## 8. Limits and false assurance traps

- **Agent without MDM.** Kandji distinguishes the MDM profile from its agent. Only `mdm_enabled` counts
  as managed; a device can run the agent with the MDM profile removed.
- **Missing devices.** `is_missing` means Kandji lost contact; never treat as retired.
- **Status integers.** Command status codes are not documented in the file: do not infer success from a
  code; require `date_completed`.
- **Rebrand drift.** Hosts, permission labels and docs move from Kandji to Iru names over time; pin the
  OpenAPI file version in fixtures and test both hosts.

## 9. Product and UI

Connect form: API URL, token, region auto detected from the URL. Settings: blueprints in scope, screen
lock limit, minimum OS. Health: token invalid or revoked (401, `error`), permission missing (403 on an
endpoint, only its checks `error`), rate limited (`truncated`). In product guide: yes (token permissions).

## 10. Implementation notes

300 devices per page; with 10,000 calls an hour, per device details calls bound the fleet size per run:
use Prism first and details only for gaps. Fixtures: a Mac with MDM, one with agent only, one missing,
one removed, an erase pending and one completed, an iPhone. Example scripts live in Kandji's support
GitHub repository [S1].

## 11. How comparable platforms do it

| Platform | Token permissions | What they test |
|---|---|---|
| Drata | API URL and token with Device details, Device list, Application list, Device Library items [S5] | library items found by name: Screen Saver, FileVault, Firewall (needs the `com.apple.security.firewall` payload), Passcode, Software Update; password manager from the app list; no antivirus test |
| Vanta, Secureframe | Device details, Device list, Device ID, Application list, Device Library Items, as listed by Iru [S7] | Secureframe shows five Mac controls [S8]; what Vanta tests on Kandji was not read (unverified) |
| Scrut, Scytale, Sprinto | guides exist for Scrut and Scytale [S5]; not read (unverified) | |

## 12. Sources

- [S1] Iru Endpoint Management OpenAPI (URL formats, rate limit, endpoints, list fields): https://docs.iru.com/openapi/iru-endpoint-openapi.json (rendered at https://api-docs.iru.com/)
- [S2] Iru API overview (token shown once, creator deletion, shared rate limit): https://docs.iru.com/en/endpoint/api/iru-api-overview ; earlier Kandji Okta Workflows guide: https://support.kandji.io/kb/authorize-your-kandji-tenant-for-okta-workflows
- [S3] Iru brand update (hosts, dates, platforms): https://docs.iru.com/en/iru/platform-overview/iru-brand-update
- [S4] Kandji FileVault details announcement: https://updates.kandji.io/updates/filevault-details/
- [S6] Iru newsroom, Kandji is now Iru: https://www.iru.com/newsroom/kandji-now-iru
- [S7] Iru, integrating third party apps through the API (permission labels): https://docs.iru.com/en/endpoint/integrations/overview/integrating-third-party-apps-using-the-iru-endpoint-api
- [S8] Secureframe, supported MDMs: https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
- [S5] Drata Kandji guide: https://help.drata.com/en/articles/5831405-kandji-integration-guide-mdm ; Scrut: https://help.scrut.io/docs/integrating-kandji ; Scytale: https://help.scytale.ai/en/articles/12107575-kandji-user-guide
