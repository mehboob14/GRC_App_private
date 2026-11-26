# 8. Corrections to round 1

The research files list 64 corrections to round 1 (the strategy file, the device connector files and the
market research); merged where two files corrected the same claim, they make the 61 rows below, by round 1
file, in short form; each research file's "Corrections to round 1"
section holds the full row with its sources. The independent verification logs
([research/verify-apple.md](research/verify-apple.md), [research/verify-microsoft-google.md](research/verify-microsoft-google.md),
[research/verify-xplat-market.md](research/verify-xplat-market.md)) rechecked these rows; section 8.7 records
where a verifier changed a correction.

The round 1 files are not rewritten line by line. Each carries a pointer to round 2, and a connector document
moves from plan to as built only when its package (06) is done, at which point it absorbs these rows.

## 8.1 `mdm-and-endpoint-strategy.md`

| Place | Round 1 | Round 2 | Source |
|---|---|---|---|
| 5.3 `devices.recovery_key_escrowed` | read "a key is held by the MDM" | Apple exposes only "has a key" flags; escrow is the vendor's record of receiving the key; a Mac encrypted before the escrow payload arrived needs a key rotation before its key is escrowed; "has key" alone is `fail` for escrow | apple 7, verify-apple |
| 5.3 `devices.wipes_confirmed` | "reached a completed state" | erase replies do not prove the outcome on Apple; require a later signal | apple 7, apple-mdms 11 |
| 5.5 `devices.firewall_enabled` on Intune | partial until the export permission is solved | readable per device through compliance setting states with a Read permission, when a policy evaluates firewall | microsoft 7 |
| 5.5 `devices.screen_lock` on Google | no | partial for ChromeOS (lock delay policy through the Chrome Policy API) | android 7 C8 |
| 5.5 `devices.firewall_enabled` on Google | yes | yes for Endpoint Verification desktops and ChromeOS only; Android `not_applicable` | android 7 C9 |
| 5.5 `devices.recovery_key_escrowed` macOS on Intune | no metadata field (unverified) | confirmed: the only route returns the key itself; macOS stays `insufficient` | microsoft 7 |
| 5.5 columns | Intune, Jamf, Kandji, Google, EDRs | 14 device providers in [03](03-provider-field-maps.md) 3.2 | apple-mdms 11, xplat-a, xplat-b |
| 6 observation contract | one `device` type plus `device.action` | six types and the v2 dictionary ([02](02-what-verity-collects.md)) | all |
| 6 match keys, hardware ids | IMEI and MEID as device queries | removed from Apple's main device query in iOS 26; Android personal work profiles give an enterprise specific id instead of a serial | apple 7, android 7 C1 |
| 7.2 Drata Agent | "the README does not mention disk encryption" | the help article lists encryption among its checks | market 11 C3 |
| 7.2 Vanta | no lock threshold | passes at 60 minutes idle or less; Linux encryption only | market 11 C4 |
| 7.2 Secureframe Agent | no threshold | fixed 15 minutes; the agent's result wins over an MDM | market 11 C10 |
| 7.3 Fleet licence | MIT outside `ee/`, usable | `docs/` is CC BY-SA 4.0; the Go API client package imports `ee/` code, so it cannot be imported cleanly | xplat-b 10 |
| 7.4 options | agent, MDM, attestation, Google | add: Fleet's managed cloud starts at 700 hosts, so a customer's own Fleet means self hosting; 1Password Device Trust as an agent source for personal and contractor devices | xplat-b 10 |
| 7.4 auditor acceptance | no source found | audit firm guidance accepts dated, full screen screenshots and prefers exports with their parameters | market 11 C14 |
| 2 scope, HR | Rippling only as an HR system | Rippling also exposes devices (since 1 July 2026) and is the strongest single source for leaver device recovery | xplat-b 10 |
| 9 D-DEV-2 | Intune first, then Google | wave 1 adds JumpCloud (D-MDM-1) | market 12 |

## 8.2 `connectors/intune.md`

| Place | Round 1 | Round 2 | Source |
|---|---|---|---|
| 2.2 | reports need export jobs | synchronous report actions list Read permissions; export jobs still ReadWrite only | microsoft 7 |
| 2.2 | `Device.Read.All` not needed | needed for the second population (registered and unmanaged devices) | microsoft 7 |
| 4 | current state only | Data Warehouse keeps 60 days of daily device rows (no encryption) | microsoft 7 |
| 4 | `windowsProtectionState` read with the managed devices permission | v1.0 documents the route under `detectedApps`; beta also accepts the configuration permission | microsoft 7 |
| 5.1 `devices.enrolled` | `managementState` in the v1.0 example | a beta property with 12 values; absent from v1.0 | microsoft 7 |
| 5.1 `devices.remote_wipe` | `userEnrollment` means work data only | it means user driven BYOD enrolment; Apple user enrolment is 11, 12 and 25 | microsoft 7 |
| 5.2 `devices.wipes_confirmed` | audit events would be stronger | beta `remoteActionAudits` gives action, state, time and initiator with no new permission | microsoft 7 |
| 8 | cleanup rules only | AVD multi session records inactive 60 days are deleted outside cleanup rules | microsoft 7 |
| S10, S22 | Learn paths under `intune-service` | Intune docs moved; old paths may still resolve | microsoft 7 |

## 8.3 `connectors/jamf-pro.md`

| Place | Round 1 | Round 2 | Source |
|---|---|---|---|
| 4, 8 | first v4 version unverified | v4 from 11.30.0; v1 deprecated 11.20.0, v2 11.23.0, v3 11.30.0; use the version ladder | apple-mdms 11 |
| 4 | `lastCheckIn` seen only in filters | a v4 field; `lastContact` replaced `lastContactTime` | apple-mdms 11 |
| 4 | "SOFTWARE_UPDATES lists pending updates" | from OS 27 pending update data comes only from DDM status; whether Jamf fills it: test on fixtures | apple 7 |
| 4 | Activation Lock field reliable | Apple deprecated the device key; cross check with Apple Business | apple 7 |
| 4 (mobile) | fields kept | add `lastContactDate`; `hardwareEncryption` is an undefined integer; drop lost mode location; use LENIENT | apple-mdms 11 |
| 1, 3, 5.1 screen lock | from a screen saver payload | also the passcode payload and, from OS 27, the DDM passcode configuration | apple 7 |
| 2.2 privileges | four | add Read Mobile Device Configuration Profiles; DDM status needs both device read privileges | apple-mdms 11 |
| 5.1 `devices.remote_wipe` | needs `mdmCapable` and a bootstrap token | erase needs neither supervision nor ADE nor a bootstrap token; forbidden on user enrolment | apple 7, apple-mdms 11 |
| 5.2 `devices.wipes_confirmed` | yes | partial | apple 7, apple-mdms 11 |
| 8 "managed is not supervised" | erase differs when unsupervised | erase does not need supervision; supervision gates Lost Mode, Activation Lock, deferrals | apple 7 |
| S4 | Platform API path with tenant id | the tenant id moved to the `X-Tenant-Id` header at GA | apple-mdms 11 |

## 8.4 `connectors/kandji.md`

| Place | Round 1 | Round 2 | Source |
|---|---|---|---|
| 1, 2.2 | Prism gives activation lock data | the example shows only shared columns; fields unverified | apple-mdms 11 |
| 2.1 | token steps | add the MCP toggle (leave off) and the permissions step | apple-mdms 11 |
| 4 | device list fields from "its example" | from the Update Device example; the list route has no success example | apple-mdms 11 |
| 4 | Prism categories | 16 categories, including startup settings, local users, apps and cellular (not to be read) | apple-mdms 11 |
| 5.1 `devices.disk_encrypted` iOS | data protection follows passcode (unverified) | needs hardware encryption capability 3 and a passcode present; both must be exposed or `insufficient` | apple 7 |
| 5.1 | pending updates not read | OS 27 moved update state to DDM | apple 7 |

## 8.5 `connectors/google-endpoint-management.md`

| Place | Round 1 | Round 2 | Source |
|---|---|---|---|
| 4 Devices | `serialNumber` is the serial | on Android 12 and later personal work profiles it is the enrolment specific id | android C1 |
| 5.1 `devices.os_current` | yes | partial: Android needs the complete patch level, a supported version and a vendor window | android C2 |
| 2.1 | a custom read only role with view rights | the mobile device management privilege is full control with no view variant; the read only scopes are the only limit | android C3 |
| 8 | most phones are BYOD with basic management | unverified | android C4 |
| 2.3 | basic management wipes only the work account | for devices moved from advanced to basic, only a full wipe may be possible | android C5 |
| 1, 10 | one work profile case | GEM does not support work profiles on company owned devices; zero touch devices count as personal until added to the company inventory | android C6 |
| 4 Endpoint Verification | screen lock enabled only | attribute `is_secured_with_screenlock` exists, still not in the Devices API resource | android C7 |
| Go libraries | Cloud Identity and Directory | add Chrome Policy and Chrome Management | android C10 |

## 8.6 `03-market-research.md`

| Place | Round 1 | Round 2 | Source |
|---|---|---|---|
| 3.3 Vanta | Jamf, Kandji, Intune | add Workspace ONE, JumpCloud, Rippling, Addigy, Hexnode, Mosyle (agent only); Iru covers macOS and Windows | market C1 |
| 3.3 Drata | Jamf, Kandji, Intune, JumpCloud; agent wins over Jamf | add Workspace ONE, Hexnode, Rippling, Custom Device Connections; Intune uses its own compliance verdict; the agent wins over any MDM | market C2 |
| 3.3 personal devices | a personnel exclusion for device checks | Drata's exclusions are per person, not per device | market C5 |
| 3.3 Scrut | built on "not stated" | osquery, Windows, macOS and Linux, every 3 hours, password manager check | market C6 |
| 3.3 Sprinto | Hexnode, Intune, Jamf | many more, 24 hour cadence, inactive after 90 days; its Jamf pages conflict; Hexnode claims unverified | market C7, C8 |
| 3.3 Secureframe | cadence not stated | daily; 19 sources | market C9 |
| 3.3 Hyperproof | not checked | proof lists for Jamf, Intune, Kandji, JumpCloud, Chrome devices; no posture tests | market C11 |
| 3.3 ServiceNow | Intune and Jamf | also Google, SCCM, Workspace ONE, Tanium, Defender, Qualys (CMDB only) | market C12 |
| 3.3 Thoropass | MDM coming soon | still none native; partners XFA and Swif | market C13 |
| O1 Fleet | MIT | MIT except `ee/` and `docs/` | xplat-b 10 |

## 8.7 What the independent verification changed

Three verifiers rechecked 241 load bearing claim rows against primary sources on 2026-11-26: 210 confirmed,
22 corrected, 9 unverified. Every correction is applied in files 01 to 07; the rows that change a check, a
credential step or a privacy rule:

| Log | Finding | Applied in |
|---|---|---|
| verify-apple | FileVault: a Mac encrypted before the escrow payload needs a key rotation to be escrowed (the "silently skipped" note was about an older payload) | 01 1.3.1, 04 4.2, 8.1 above |
| verify-apple | Apple Business `deviceEraseStatus` exists only for its built in management; a Default erase may send no reply | 01 1.3.1, 02 2.4, 05 5.9 |
| verify-apple | Apple Business can clear user linked Activation Lock on company devices; the 15 day bypass window is iPhone and iPad only | 01 1.3.1, 04 4.2 |
| verify-apple | Addigy's read only marker is not a usable allowlist; Iru EU host; SimpleMDM secret custom attributes | 03 3.3 |
| verify-microsoft-google | Intune enrolment types above 12 are beta only | 01 1.3.2, 03 3.3 |
| verify-microsoft-google | Intune may omit the serial on any Android personal work profile; IMEI never shown there | 01 1.3.3 |
| verify-microsoft-google | AVD multi session: some password settings, remote lock disabled | 01 1.3.2 |
| verify-microsoft-google | `remoteActionAudits` rows carry IMEI: drop for personal devices | 03 3.3 |
| verify-microsoft-google | Autopilot device preparation devices appear when also registered | 01 1.3.2, 1.4 |
| verify-microsoft-google | Google mobile audit retention is about 6 months by edition, not a fixed 180 days | 03 3.1 |
| verify-xplat-market | Workspace ONE escrow and passcode flags only from the per device security call, whose schema holds keys | 03 3.2, 3.3, 07 D-MDM-12 |
| verify-xplat-market | Fleet `wiped_host` is logged on send, not completion | 03 3.3 |
| verify-xplat-market | Hexnode real location and phone keys; "one key per portal" unverified | 03 3.3 |
| verify-xplat-market | JumpCloud Read Only admin key unverified (guide offers the service account only); NinjaOne OAuth pages disagree | 03 3.3 |
| verify-xplat-market | "No competitor checks phones" overstated (Sprinto lists iOS for Jamf); Vanta's JumpCloud page does not show Linux | 01 1.1, README |

None changes the connector order (D-MDM-1). Remaining unverified items are marked in the research files and
must be confirmed on a developer or trial account before code depends on them (`../04-phases-and-work-packages.md` 4.0).
