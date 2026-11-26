# 2. What Verity collects: the device dictionary, version 2

Every device source, whatever the vendor, is normalised by the Go collector into the observation types below
(ADR-0016, `contracts/observations/*.schema.json`). Checks read only these types, never raw provider answers.
This version replaces the `device` row of `01-evidence-model.md` 1.4 and section 6 of
`mdm-and-endpoint-strategy.md`, and folds in every key the round 2 research proposed (research files, section
"Proposed new dictionary keys").

## 2.1 Observation types

| Type | One per | Purpose |
|---|---|---|
| `device` | device per source per run | state of one device as one source saw it |
| `device.policy` | device, policy or declaration, per run | a policy, profile, declaration or provider check assigned to the device, its settings that checks read, and its applied state |
| `device.purchase` | purchased device per run | the population an MDM cannot give: Apple Business, Autopilot, zero touch (if allowed), Knox, ChromeOS pre provisioned |
| `device.action` | remote command | wipe, retire, lock, lost mode: issued, state, completion, confirmation |
| `device.app_protection` | app registration (no device enrolment) | app protection on personal phones (Intune MAM), so mail only phones are evidenced by rule |
| `device.directory` | directory device record | identity provider registrations (Entra, Google, Okta devices) that may not be managed |

Every observation also carries the common envelope: tenant, connection, provider, `observed_at`, the API
source path, and the run's completeness per type (`complete`, `truncated`, `permission_missing`,
`unsupported_by_plan`), plus `reporting_gaps` (sections the source did not report, [google G4]).

## 2.2 `device` fields

Privacy class: **I** identifier, **S** security state, **P** person link, **O** operational. Fields marked
"company only" are dropped before storage for personal or unknown ownership (2.5).

| Group | Field | Type and values | Class | Checks that read it | Notes |
|---|---|---|---|---|---|
| Identity | `provider_device_id` | string | I | all (match) | for personal devices this is the enrolment id: Apple enrolment id, Android `enterpriseSpecificId` |
| | `enterprise_specific_id` | string | I | match | Android personal work profiles on 12 and later report it where a serial would be [google G2] |
| | `serial_number` | string, normalised | I, company only | match, `devices.purchased_devices_enrolled` | placeholder values discarded (05 5.3.1) |
| | `hardware_ids` | UDID, IMEI, MEID | I, company only | match | IMEI and MEID left the main Apple query in iOS 26 [apple G12] |
| | `hostname`, `device_name` | string | I, company only | display, weak match | names often carry a person's name |
| | `manufacturer`, `model`, `platform`, `os_version`, `os_build` | strings; `platform` in macos, windows, ios, ipados, android, chromeos, linux, other | S | all | |
| | `os_supplemental_version` | string | S | `devices.os_current` | Apple Background Security Improvement letter and build [apple G18] |
| Class | `device_class` | computer, phone, tablet, shared, dedicated, virtual, server | O | populations | |
| | `virtual_host_type` | cloud_pc, avd_single, avd_multi, none | O | turns encryption and lock into `not_applicable` [ms G5, G6] | |
| | `ownership` | company, personal, unknown | O | populations, privacy | unknown is treated as personal until classified (D-MKT-4) |
| Management | `enrolment_channel` | automated_company, user_initiated_device, account_driven_device, byod_account_driven, work_profile_company, work_profile_personal, legacy_device_admin, agent_only, registered_only, inventory_only, unknown | O | `devices.enrolled`, `devices.remote_wipe` | unknown provider values map to `unknown`, never a default [ms G8] |
| | `managed_by` | raw agent: intune, configmgr, jamf, iru, google, mde, fleet, ... | O | no double counting across sources | [ms 8] |
| | `supervised` | boolean (Apple) | S | Lost Mode, Activation Lock management | not proof of company ownership [apple G15] |
| | `user_approved_mdm`, `bootstrap_token_escrowed` | booleans (macOS) | S | context for `devices.remote_wipe` (erase method) | not required for a wipe [apple G25] |
| | `management_state` | managed, pending, unenrolled, retired, wiped, lost_mode, removed | O | `devices.enrolled` | |
| | `provider_record_state` | present, missing, hidden, removed, deleted | O | population | Iru `is_missing`, Jamf records vanish [apple-mdms 10] |
| | `enrolled_at` | time | O | "before issue" | Autopilot shows registration time, not enrolment [ms G10] |
| | `last_check_in_at` | time | O | freshness of management | MDM channel contact |
| | `inventory_reported_at` | time | O | freshness of state checks | last state report; can be days older than check in [apple-mdms 4.7 item 2] |
| | `agent_last_seen_at` | time | O | freshness for agent channels | [xplat-b 11] |
| | `provider_compliance_state` | compliant, noncompliant, in_grace, unknown, error, not_evaluated | S | secondary evidence only | Verity judges settings itself [market 9 item 2] |
| People | `assigned_user_email`, `assigned_user_provider_id` | string | P | person checks | joined to a tenant membership, never stored as a `user_id` (CLAUDE rule 3) |
| | `assignment_source` | primary_user, enrolling_user, directory, hr_worker, manual, last_logged_on | P | person checks | |
| | `assignment_confidence` | strong, weak | P | person checks | weak never satisfies completeness [xplat-b 11] |
| Encryption | `disk_encryption` | on, off, in_progress, paused, unknown, not_applicable | S | `devices.disk_encrypted` | in_progress and paused are not on [apple-mdms 4.7 item 4] |
| | `encryption_method` | filevault, bitlocker, platform_data_protection, luks, chromeos_native | S | evidence text | |
| | `encryption_key_protected` | boolean | S | `devices.disk_encrypted` (Android) | false for Android "active with default key" [google G6] |
| | `recovery_key_escrowed` | yes, no, unknown, not_applicable | S | `devices.recovery_key_escrowed` | from the vendor's escrow record, never from a "has key" flag; the key itself is never read [apple G5] |
| | `recovery_key_escrow_source` | string | S | evidence | which flag was used |
| Lock | `passcode_present`, `passcode_compliant` | booleans (mobile) | S | `devices.screen_lock`, `devices.disk_encrypted` (iOS) | compliant counts only with a policy assigned [apple G1] |
| | `passcode_policy_assigned` | boolean | S | `devices.screen_lock` | from `device.policy` |
| | `idle_lock_seconds`, `idle_lock_origin` | integer; policy or device_reported | S | `devices.screen_lock` | device reported only on Shared iPad today [apple 3.6] |
| | `failed_unlock_limit` | integer, origin | S | `devices.unlock_attempts_limited` (proposed, CIS 4.10) | [market 10] |
| Hardening | `firewall_on` | boolean or unknown | S | `devices.firewall_enabled` | |
| | `firewall_profiles` | per profile on, off (Windows) | S | same | [xplat-a F] |
| | `firewall_default_deny` | boolean or unknown | S | stricter firewall predicate (later) | [market 10] |
| | `os_integrity` | sub keys: `sip`, `secure_boot`, `external_boot`, `boot_mode` (ChromeOS), `jailbroken_or_rooted`, `play_integrity`, `developer_mode` | S | `devices.os_integrity` (proposed) | each sub key can be `not_collected` [apple-mdms 4.7 item 5] |
| | `activation_lock_type` | org, user, none, unknown | S | `devices.activation_lock_org_controlled` (proposed) | Apple Business is authoritative [apple G13] |
| | `removable_storage_blocked` | yes, read_only, no, unknown | S | `devices.removable_storage_restricted` | usually from `device.policy` |
| | `local_admin_present` | boolean or unknown | S | later (least privilege on endpoints) | |
| Protection | `av_present`, `av_realtime_on`, `av_signatures_current`, `tamper_protection_on` | booleans or unknown | S | `endpoint.*` cross check | the EDR connector is the authority |
| | `edr_present` | boolean or unknown | S | `endpoint.coverage_complete` | |
| Updates | `os_update_policy_assigned` | boolean | S | `devices.updates_automatic` (proposed, EP-04.B) | from `device.policy` (DDM software update, Windows Update ring, Android `systemUpdate`) |
| | `os_update_available`, `os_update_pending_version` | boolean, string | S | `devices.os_current` | from Apple DDM status on OS 27 [apple G8] |
| | `security_patch_level` | date | S | `devices.os_current` (Android) | compare the complete level [google G12] |
| | `os_supported_until` | date | S | `devices.os_current` | ChromeOS `autoUpdateThrough`; Android from Verity's reviewed vendor table |
| | `browser_versions` | list of browser, version | S | `devices.browsers_current` (proposed, EP-04 "browsers") | company devices; inventory can be 7 days old [ms G15] |
| | `known_vulnerabilities` | CVE ids with KEV flag | S | later (EP-04, LM-11) | Fleet, Defender [xplat-b 11] |
| Software | `installed_apps` | list of name, identifier, version, source, signer, provider_verdict | S, company only | `devices.software_permitted` (proposed, EP-03.E) | personal devices: never; only derived booleans |
| | `managed_apps` | list of identifier, version, state | S | `devices.software_permitted` | allowed on personal devices |

## 2.3 `device.policy` fields

One row per policy, profile, declaration, compliance setting or provider check that reaches a device.

| Field | Values | Used by |
|---|---|---|
| `kind` | apple_profile, apple_declaration, intune_compliance_setting, intune_configuration, android_policy, chrome_policy, provider_check, jamf_benchmark_rule | all policy evidence |
| `policy_id`, `name`, `definition_hash` | strings | evidence, change detection |
| `topic` | passcode, screen_lock, encryption, escrow, firewall, updates, removable_storage, software, other | maps the policy to a check |
| `settings` | the subset of keys checks read, for example `max_inactivity_minutes`, `idle_time_seconds`, `ask_for_password`, `ask_for_password_delay_seconds`, `maximum_time_to_lock_ms`, `external_storage` | predicates |
| `applied_state` | installed, active, valid, compliant, noncompliant, error, conflict, not_applicable, pending | predicates |
| `state_reported_at` | time | freshness |

Rules: a policy scoped to a device but not reported installed does not count [apple-mdms 4.7 item 9]; an
Intune per setting state exists only where a compliance policy evaluates that setting, so its absence is
`insufficient` [ms G1]; encrypted Apple profiles hide their payloads [apple G10].

## 2.4 `device.purchase`, `device.action`, `device.app_protection`, `device.directory`

| Type | Fields |
|---|---|
| `device.purchase` | `source` (apple_business, autopilot, zero_touch, knox, chromeos_preprovisioned), `serial_number`, `hardware_ids` (company only), `model`, `purchase_source_type`, `order_number`, `added_at`, `released_at`, `assigned_service` (Apple Business MDM server or Autopilot profile), `enrolment_state` (Autopilot `enrollmentState`, Knox state), `last_contacted_at` |
| `device.action` | `device`, `kind` (wipe, retire, lock, lost_mode, unlock), `issued_at`, `issued_by` (provider account, kept as text only), `state` (pending, acknowledged, error, not_now, completed, failed, cancelled), `completed_at`, `erase_method` (eacs, obliteration, factory_reset, work_profile_removal, unknown), `confirmed_by` (command_state, later_signal, none), `confirming_signal` (no contact after the command plus re-enrolment of the serial; Apple Business `deviceEraseStatus`, which exists only for devices under Apple Business built in management; Rippling `FULL_WIPED`; record retired) |
| `device.app_protection` | `app_identifier`, `app_version`, `platform`, `platform_version`, `policy_applied`, `flagged_reasons` (for example rooted device), `last_sync_at`, `assigned_user_provider_id` |
| `device.directory` | `directory` (entra, google, okta), `directory_device_id`, `trust_type` (registered, joined, hybrid), `is_managed`, `is_compliant`, `approximate_last_sign_in_at`, `account_enabled`, `owner_user_provider_id` |

Why `confirmed_by` matters: an Apple erase reply can be Error while the Mac erases, or Acknowledged while
nothing happens [apple G3]. A wipe counts as confirmed only with a later signal.

## 2.5 Privacy rules (enforced in the normaliser, before anything is stored)

Applied when `ownership` is personal or unknown, or the channel is `byod_account_driven` or
`work_profile_personal` [market 7.3]:

| Never stored | Why |
|---|---|
| serial number, UDID, IMEI, MEID, MAC addresses | the platforms withhold them on personal channels on purpose; matching uses the enrolment id |
| phone number, including partial digits | no check needs it |
| location, network data (SSID, IP, carrier) | never needed; regulators name it as a risk |
| full installed app list | personal apps are private; keep managed apps and derived booleans only |
| device name and hostname | they often carry a person's or family member's name |
| local account names, files, processes, browsing history, messages, contacts | never needed |
| anything from the personal profile or account | do not capture private use |

For **every** device, whatever the ownership, the collector never requests or keeps: recovery keys or key
material (FileVault, BitLocker, LUKS), Activation Lock bypass codes, recovery lock and firmware passwords, lost
mode location, Autopilot product keys, device query or live query output. Several providers return such
secrets on routes a read credential can reach (Fleet Observer, SimpleMDM keys with Device Secrets, Workspace
ONE security response, ManageEngine `DataEncryption.READ`, JumpCloud FileVault route) [xplat-a 0][xplat-b 4.1]
[apple-mdms 8]. So the collector has an **endpoint allowlist and a field allowlist per provider**; anything
else is dropped in the parser, and a test per provider feeds a fixture containing the secret fields and
asserts they never reach an observation.

A connection whose credential could read secrets carries `credential_reads_secrets: true` and shows a warning
the workspace admin must accept (D-MDM-12).

Every rule here has a fixture test per provider (personal device fixture, secrets fixture).

## 2.6 Retention and use

- Device observations are kept for the workspace's evidence retention (default: the audit period plus one
  year); raw batches in object storage only as long as the run's evidence file needs them.
- Device data is used only as control evidence. Verity never computes activity, usage or productivity per
  person [market 7.3 G1].
- The customer privacy pack (D-MDM-13): the field list per provider and ownership, a worker notice template,
  DPIA inputs, and a note that German customers may need works council agreement.

## 2.7 What the customer sees before connecting (copy for the before you connect screen)

| Verity reads | Verity never reads |
|---|---|
| which devices exist, who they belong to, how they are managed | where any device is |
| encryption on or off, and whether a recovery key is held centrally | recovery keys, passwords, PINs or bypass codes |
| screen lock and passcode settings | messages, mail, files, photos, browsing |
| OS version, update and patch state | personal apps on personal devices |
| firewall, protection agent and integrity flags | phone numbers |
| company apps and versions on company devices | anything from a personal profile |
| wipe and lock commands and whether they completed | (and Verity never sends a command) |
