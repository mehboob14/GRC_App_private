# Research brief: MDM and device evidence (round 2)

Shared brief for every agent researching device management for Verity. Round 1 is
`../../mdm-and-endpoint-strategy.md` and the connector files in `../../connectors/` (intune, jamf-pro, kandji,
google-endpoint-management, microsoft-defender-endpoint, crowdstrike-falcon, sentinelone) with their
verification log `../../verification/devices-hr.md`. Round 2 goes deeper: every device type, every enrolment
channel, exactly which fields Verity collects from which API, and how each field reaches an objective and a
control. Read round 1 first and extend it; do not repeat what it already verified, but correct it where it is
wrong (list corrections separately).

## Rules (from ../../AUTHORING.md, binding)

1. Accuracy first. Every claim about an API, field, permission, licence tier, platform behaviour or setup step
   cites the official documentation, read in this session (fetch the page). If you cannot confirm a fact, write
   "unverified" next to it. Never invent an endpoint, field, scope or setting.
2. Read only, least privilege. Verity never writes to a customer's system and never sends device commands.
   Name the narrowest read permission or role for each item.
3. Own words. No copied sentences from vendor, Apple, Microsoft, Google, AICPA, ISO or NIST text.
4. Plain English, short sentences, tables. No em dashes and no en dashes. Use commas, colons or "to".
5. Write only your own output file. Do not edit any other file.

## The attribute dictionary (map every provider to these keys)

Verity normalises every device source into one `device` observation. Map each provider field to these keys;
propose new keys at the end of your file if the evidence needs them (with the check that would use them).

| Group | Keys |
|---|---|
| Identity | `provider_device_id`, `serial_number`, `hardware_ids` (UDID, IMEI and MEID only for company owned), `hostname`, `device_name`, `manufacturer`, `model`, `platform` (macos, windows, ios, ipados, android, chromeos, linux, other), `os_version`, `os_build` |
| Class and ownership | `device_class` (computer, phone, tablet, shared, dedicated or kiosk, virtual, server), `ownership` (company, personal, unknown) |
| Management | `enrolment_channel` (automated_company: ADE, Autopilot, zero touch, KME; user_initiated_device; byod_account_driven: Apple user enrolment; work_profile_personal; work_profile_company; agent_only; registered_only: known to the directory but not managed; inventory_only), `supervised`, `management_state` (managed, pending, unenrolled, retired, wiped, lost_mode, removed), `enrolled_at`, `last_check_in_at`, `provider_compliance_state` and `compliance_policies` (the MDM's own verdict, kept as secondary evidence) |
| People | `assigned_user_email`, `assigned_user_provider_id`, `assignment_source` (primary user, enrolling user, manual) |
| Encryption | `disk_encryption` (on, off, in_progress, unknown, not_applicable), `encryption_method` (FileVault, BitLocker, platform data protection, LUKS, ChromeOS native), `recovery_key_escrowed` (never the key itself) |
| Lock | `passcode_present`, `passcode_compliant`, `idle_lock_seconds`, `idle_lock_origin` (policy, device_reported) |
| Hardening | `firewall_on`, `os_integrity` (SIP, Secure Boot, jailbreak or root, Play Integrity verdict), `activation_lock_or_frp`, `removable_storage_blocked`, `local_admin_present` |
| Protection | `av_present`, `av_realtime_on`, `av_signatures_current`, `edr_present` (as the MDM sees it; the EDR connector is the authority) |
| Updates | `os_update_policy_assigned`, `os_update_available`, `security_patch_level` (Android), `os_supported` (vendor support, for example ChromeOS auto update expiry), `browser_versions` |
| Software | `installed_apps` (name, identifier, version, source), company owned devices only; `managed_apps` |
| Actions | `device.action`: kind (wipe, retire or selective wipe, lock, lost mode), issued_at, state, completed_at, issued_by |

Never collected: location, personal apps or data on personal devices, files, browsing history, recovery key
material, phone numbers, messages.

## What each research file must contain

1. **Scope**: the platforms, products, editions and API versions covered, with the date read.
2. **Per platform and enrolment channel**: what the MDM can see and do (visibility matrix: rows are the
   dictionary keys, columns are the channels; cells yes, partial with why, no).
3. **Field map**: for each dictionary key, the exact API endpoint or query, the field name, the read permission,
   the licence or tier needed, and caveats. Mark each row verified (with source id) or unverified.
4. **Auth and permissions**: how a customer creates a read only credential, and what it can see.
5. **Limits**: rate limits, paging, freshness (how often devices report), history available (can Verity see
   past state, or only the present).
6. **Gotchas** that would make a check wrong (for example a field that reads true when unknown).
7. **Corrections to round 1** (file, claim, correction, source).
8. **Sources**: numbered, URL, what it supports.

Return to the caller a summary of at most 300 words: the five findings that most change Verity's plan, and the
count of verified and unverified claims.
