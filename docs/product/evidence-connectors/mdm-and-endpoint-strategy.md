# Device, endpoint and HR evidence: what it serves, the checks, and customers without an MDM

> **Round 2 (2026-11-26):** device management is researched further in [mdm/](mdm/README.md): channels per
> platform, the device dictionary v2, 16 providers, 28 checks, the process and work packages. Where the two
> disagree, round 2 wins; the corrections are listed in [mdm/08-corrections-to-round-1.md](mdm/08-corrections-to-round-1.md).
> Endpoint protection (EDR) and HR sections here are unchanged.

Authoring rules: [AUTHORING.md](AUTHORING.md). Evidence model: [01-evidence-model.md](01-evidence-model.md).
Connector files: [intune.md](connectors/intune.md), [microsoft-defender-endpoint.md](connectors/microsoft-defender-endpoint.md),
[jamf-pro.md](connectors/jamf-pro.md), [kandji.md](connectors/kandji.md),
[google-endpoint-management.md](connectors/google-endpoint-management.md),
[crowdstrike-falcon.md](connectors/crowdstrike-falcon.md), [sentinelone.md](connectors/sentinelone.md),
[hr-systems.md](connectors/hr-systems.md).

## 1. Summary

- Device management, endpoint protection and HR are **not in the signed catalogue** and the delivery plan
  lists an endpoint or device agent as out of scope (`docs/product/delivery-plan.md`, Out of scope). Every
  connector in this round is therefore an extension the owner must agree with the client (D-DEV-1).
- Device and endpoint evidence serves seven endpoint controls (EP-01 to EP-07), plus parts of LM-01,
  HR-03, HR-05, IAM-12, NS-11, DM-16 and DM-19. HR evidence is the population for 17 objectives through
  one artifact, the joiner and leaver roster.
- The content has four problems to fix before any device check runs (section 4): one device artifact is
  shared by 11 objectives with a single check as its only source, so a passing enrolment check would
  satisfy the encryption, agent, wipe and screen lock objectives, and a company without an MDM could never
  satisfy it at all.
- 11 new device and endpoint checks are defined here (section 5.3) and 4 new HR checks in
  [hr-systems.md](connectors/hr-systems.md#22-new-hr-checks).
- For customers without an MDM: **do not build an agent now.** Use Google Endpoint Verification where the
  customer runs Google Workspace (system generated, free on almost every edition), Intune where the
  customer already pays for Microsoft 365 Business Premium or E3, and a structured, reviewed device
  attestation everywhere else. Revisit an osquery based Go agent when there is demand (section 8).

## 2. Scope status

| Item | State today | Source |
|---|---|---|
| Signed catalogue (spec section 8) | no HR, MDM or EDR providers | `control-framework-requirements.md` Appendix A and open question 1 |
| Delivery plan | "endpoint or device agent" listed as out of scope | `delivery-plan.md` |
| `capabilities.json` | `hr_system` (Workday, BambooHR, Rippling, Gusto), `device_management` (Jamf, Kandji, Intune), `endpoint_protection` (CrowdStrike, SentinelOne): all `not_planned` | content |
| Missing from the catalogue | Microsoft Defender for Endpoint, Google Workspace as a device source, HiBob; Kandji's rename to Iru | this round |
| Checks | 5 `devices.*` and 1 `endpoint.*` exist, none implemented; 2 `people.*` need an HR source | `checks.json` |
| Open question 1 proposal | providers shown as "Not in plan, request it", controls stay manual, a people roster CSV import as the HR source | `control-framework-requirements.md` |

## 3. What the evidence serves, control by control

Coverage notation: SOC 2 criteria and ISO 27001:2022 references come from `template_requirements.json`.
Every mapping named here is partial unless marked full. "Check" means a key from section 5; "person"
means it stays with people or documents.

### EP-01 Endpoint EDR and anti-malware

SOC 2 CC6.8 (full); ISO A.8.1, A.8.7, A.8.16.

| Objective | What can evidence it | Why | Stays with people |
|---|---|---|---|
| EP-01.A standard approved | Documents module | a decision, not a state | all |
| EP-01.B every endpoint and server runs a current agent, checked against inventories, exemptions rechecked | `endpoint.protection_active`, `endpoint.coverage_complete` (EDR against MDM), `endpoint.servers_covered` (EDR against the Verity asset register) | the EDR console is the record of agent health; only a second inventory shows who has no agent | the reason and yearly recheck for each exempt system |
| EP-01.C each alert reviewed with reviewer, action and close date | `endpoint.detections_triaged` | the EDR holds status, owner, classification and close time | what action was taken and why |
| EP-01.D incidents entered in the incident register | NEED ticketing or incident register | a closed alert is not an incident record | the judgement that it was an incident |

### EP-02 Endpoint full disk encryption

SOC 2 CC6.1, CC6.5, CC6.7; ISO A.7.9, A.7.10, A.8.1, A.8.24.

| Objective | Evidence | Why | Stays with people |
|---|---|---|---|
| EP-02.A policy | document | | all |
| EP-02.B every device encrypted throughout the period, key held centrally | `devices.disk_encrypted`, `devices.recovery_key_escrowed` | MDMs report FileVault and BitLocker state; daily history shows "throughout" | |
| EP-02.C checked before issue and periodically, fixed | `devices.disk_encrypted` history from enrolment | the first observation after enrolment shows state at issue only for devices enrolled before hand over | interview on the issue process |
| EP-02.D exceptions approved and not expired | person (approved exceptions); later, waivers on failing results | an exception is a decision | all |

### EP-03 Device management enrolment

SOC 2 CC6.5, CC6.8; ISO A.6.7, A.7.9, A.8.1, A.8.19.

| Objective | Evidence | Why | Stays with people |
|---|---|---|---|
| EP-03.A policy | document | | all |
| EP-03.B every company device enrolled, before issue | `devices.enrolled`, completeness from `devices.staff_have_managed_device` and the asset register | an MDM cannot see devices that never enrolled, so a second population is needed | "before issue" for devices enrolled by hand |
| EP-03.C reconciled with the staff roster | `devices.staff_have_managed_device`, `devices.assigned_to_active_staff`, `hr.roster_exported` | the reconciliation is exactly a join of two system lists | follow up of each gap |
| EP-03.D baseline applied, drift fixed | `devices.disk_encrypted`, `devices.screen_lock`, `devices.os_current`, `devices.firewall_enabled`; fixes through `verity.tasks.remediation_in_sla` | each baseline setting is its own check | permitted software (A.8.19): no check proposed in this round |

### EP-04 Patch management

SOC 2 CC6.8, CC7.1; ISO A.8.8.

| Objective | Evidence | Stays with people |
|---|---|---|
| EP-04.A policy | document | all |
| EP-04.B deployed automatically | partial: an update policy exists in the MDM (not proposed as a check in this round) | interview |
| EP-04.C each device patched within the timeframe | `devices.os_current` (laptops); `scanner.scans_current` (servers, phase 3 research) | |
| EP-04.D laggards followed up | `verity.tasks.remediation_in_sla` | |
| EP-04.E out of cycle patches through emergency change | person | all |

### EP-05 Remote wipe on offboarding or loss

SOC 2 CC6.5; ISO A.5.11, A.7.9, A.7.14, A.8.1.

| Objective | Evidence | Stays with people |
|---|---|---|
| EP-05.A procedure | document | all |
| EP-05.B every managed device can be wiped | `devices.remote_wipe` | |
| EP-05.C lost devices and unreturned leaver devices were wiped | `devices.leaver_devices_recovered` (needs an HR source or the roster import) | lost device reports |
| EP-05.D wipes confirmed, not assumed | `devices.wipes_confirmed` | |
| EP-05.E credentials rotated for devices that never reconnected | person | all |

### EP-06 Screen lock

SOC 2 CC6.1; ISO A.7.7, A.8.1. Objective parameter `max_idle_lock_minutes` = 15.

| Objective | Evidence | Stays with people |
|---|---|---|
| EP-06.A standard | document | all |
| EP-06.B enforced by MDM, not user preference | `devices.screen_lock` (records whether the value came from an enforced policy) | |
| EP-06.C idle lock within the standard, password to unlock | `devices.screen_lock` | where the MDM reports no timeout (Google), all of it |
| EP-06.D fixes recorded | `verity.tasks.remediation_in_sla` | |

### EP-07 Harmful website blocking (ISO only)

ISO A.8.23 (full). No SOC 2 mapping.

| Objective | Evidence | Stays with people |
|---|---|---|
| EP-07.B filter covers every managed device | NEED network_edge + device_management: every managed device appears in the DNS or web filter's device list | |
| EP-07.C high value servers reach only named destinations | cloud egress rules (cloud research) | interview |
| EP-07.A, D, E standard, exceptions, quarterly review | person | all |

### LM-01 Asset and system inventory (devices part)

SOC 2 CC2.1, CC6.1; ISO A.5.9. LM-01.C asks that resources found in connected device sources appear in
the inventory. The natural key is the existing `assets.resources_registered` with MDM providers listed as
asset_discovery sources, but Verity's asset register has no device type (section 4, F5). Until that is
decided, `devices.assigned_to_active_staff` gives each device an accountable person (LM-01.B in spirit)
and the device inventory artifact stays separate from the asset inventory.

### HR-05 Offboarding and device return, HR-03 contractors

HR-05: SOC 2 CC6.2, CC6.3; ISO A.5.11, A.6.5. HR-03: CC6.2, CC9.2; A.5.11, A.8.30.

| Objective | Evidence | Stays with people |
|---|---|---|
| HR-05.C every leaver had a closed offboarding record | `hr.roster_exported` (population) + NEED verity_tasks | the checklist itself |
| HR-05.D access removed in time | `people.leavers_deprovisioned` (identity research) | |
| HR-05.E devices came back or were wiped | `devices.leaver_devices_recovered` | tokens, badges, handover, signed reminder of duties |
| HR-03.B register complete | `hr.contractors_have_end_dates`, `hr.roster_exported` | sponsor, systems reached |
| HR-03.D access ends at the end date, devices returned | NEED people (accounts off by end date), `devices.leaver_devices_recovered` | |

### IAM controls

- IAM-12 timely removal (CC6.2, CC6.3; A.5.16, A.5.18): HR gives the leaver list (IAM-12.B via
  `hr.roster_exported`); the identity research owns the removal checks.
- Device posture in sign in (IAM-03, IAM-11 neighbourhood, and NS-11.B): NEED identity_provider: sign ins
  to company applications, at least administrative and remote access, require a managed or compliant
  device (Entra conditional access, Okta device assurance, Google context aware access). Device data here
  is only the population behind that rule.
- IAM-02 access reviews: the HR manager field lets reviews be routed to managers (identity research).

### NS-11 Remote access

SOC 2 CC6.6; ISO A.6.7, A.8.21. NS-11.B device rules: `edge.zero_trust_access` (operations research)
plus the identity NEED above. NS-11.C members are current staff: NEED network_edge + hr_system.

### DM-16 Secure disposal, DM-19 data leaving by device

- DM-16 (C1.2 full, CC6.5, P4.3 full; A.7.10, A.7.14, A.8.10 full): `verity.assets.disposal_recorded`
  covers retired assets once devices can be assets. NEED device_management + verity_assets: every device
  removed from management in the period has a disposal or reassignment record (later round).
- DM-19.C (ISO A.5.14, A.7.10, A.8.12 full): `devices.removable_storage_restricted`.

### Malware and patching across families

EP-01 (malware), EP-04 (endpoint patching), LM-11 (vulnerability programme, CC7.1 full, A.8.8 full) and
NS-04 (hardening, A.8.9 full) meet on endpoints. Device checks cover the laptop half of EP-04 and part of
the OS hardening in NS-04 (firewall); servers and applications need the scanner and cloud sources.
Defender for Endpoint's vulnerability data could later feed LM-11 for endpoints (not proposed now).

## 4. Content findings to fix first

| # | Finding | Effect | Proposal (for control mapping research and the owner) |
|---|---|---|---|
| F1 | `inventory-of-company-devices` (AR-EP-06) is named by 11 objectives (DM-19.C, EP-01.B, EP-02.B, EP-02.C, EP-02.D, EP-03.B, EP-03.C, EP-03.D, EP-05.B, EP-06.B, EP-07.B). Its only source is `devices.enrolled`; it has no `person` source. All 338 artifacts use `combine: any` | Under rule B a passing enrolment check would satisfy the encryption, agent, wipe, screen lock and web filter objectives. Without an MDM the artifact can never be satisfied, against rule 1.3.1 of the evidence model | Split by what is tested: `inventory-of-company-devices` (enrolment and reconciliation: EP-03.B, EP-03.C), new `device-encryption-report` (EP-02.B, EP-02.C), new `device-protection-agent-report` (EP-01.B), new `device-wipe-capability-report` (EP-05.B); EP-06.B uses `screen-lock-setting-report`, EP-07.B uses `report-of-filter-coverage-and-blocked`, DM-19.C uses `leakage-prevention-and-sharing-settings-in`. Every one keeps a `person` source |
| F2 | `screen-lock-setting-report` lists only `person` although `devices.screen_lock` exists | the check would never reach its artifact | add `devices.screen_lock` |
| F3 | `roster-of-joiners-and-leavers-with` is filled by `people.leavers_deprovisioned`, a check about account removal | a passing removal check stands in for the roster itself | source it from `hr.roster_exported` (full) and keep `person` |
| F4 | `devices.enrolled` (EP-03), `devices.disk_encrypted` (EP-02), `devices.screen_lock` (EP-06) and `endpoint.protection_active` (EP-01) are mapped `full` | each control has a design objective and operating objectives no device check proves (AUTHORING rule 5) | change to `partial` with rationales naming what remains; none is implemented, so no workspace's readiness changes |
| F5 | `ASSET_TYPES` in `modules/assets/models.py` is application, infrastructure, data, cloud, third_party, business_service: no device | laptops cannot be registered as assets; LM-01.C and DM-16.B for laptops have no home | decision D-DEV-6: add a device type (schema change, migration, CHECK constraint) or keep devices outside the asset register. The correlation keys (`serial_number`, `primary_mac`, `hostname`, `os_normalized`) already exist |
| F6 | `assets.resources_registered` has `resource_type: cloud_resource` and says devices need their own source | | reuse it for devices once F5 is decided, with MDM providers added to `asset_discovery` |
| F7 | EP-07 has no automated source | | the network_edge NEED in section 3 |
| F8 | Catalogue gaps: Defender for Endpoint, Google devices, HiBob, Iru naming | | D-DEV-12, D-DEV-13, D-DEV-11 |

## 5. Check catalogue

### 5.1 Shared rules for devices.* and endpoint.*

- **Population.** Every device record the source holds for the scope (platforms, groups, blueprints,
  sites, org units), including unmanaged, missing, hidden or decommissioned records with their state.
  Personal devices follow the scope setting; excluding them needs a recorded reason (AU-9). A read that
  did not reach the end of paging gives `insufficient` for every check of the run.
- **Freshness.** A device whose last check in is older than `stale_after_days` (setting, default 14)
  gives `insufficient` for that device on every state check (encryption, lock, OS, firewall), because
  its present state is unknown, and `fail` on `devices.enrolled`, because being out of contact is itself
  the known fact.
- **Matching across sources.** Serial number first, then provider ids that link systems (Intune
  `azureADDeviceId` to Defender `aadDeviceId`), then hostname plus MAC. A match made on name alone is
  labelled weak in the evidence.
- **People.** Work email lowercased, and the identity provider's immutable user id once matched.
- **Outcomes.** As in `01-evidence-model.md` 1.2 and 1.3: missing permission or licence is `error`;
  partial visibility is `insufficient`; an empty population is `insufficient` unless the check says how
  it can prove emptiness.
- **Settings** (defaults are drafts for the owner, D-DEV-8): `max_idle_lock_minutes` 15 (objective
  parameter), `stale_after_days` 14, `os_minimums` per platform, `leaver_device_days` 7,
  `sensor_stale_after_days` 7, `alert_triage_hours` 24, `alert_close_days` critical 3, high 7, medium 30,
  `alert_min_severity` medium, `lookback_days` 90 for event checks.
- **Evidence.** One file per check per run as built for GitHub: scope and exclusions, per device results,
  and the part of the snapshot read.

### 5.2 Existing checks: refined predicates

| Check | Population | Predicate (refined) | Coverage change proposed |
|---|---|---|---|
| `devices.enrolled` | all device records in scope | under full MDM management (provider rule in each connector file) and checked in within `stale_after_days` | EP-03 full -> partial: "Shows each device the MDM knows is managed and in contact. Devices never enrolled, enrolment before issue and the policy are evidenced separately." |
| `devices.disk_encrypted` | managed computers and phones in scope | OS volume encryption on (FileVault, BitLocker OS volume, mobile data protection) | EP-02 full -> partial: "Shows each managed device is encrypted. Key escrow, checks before issue and approved exceptions are evidenced separately." |
| `devices.screen_lock` | managed computers and phones in scope | a lock that needs authentication starts after idle time at or under `max_idle_lock_minutes`, enforced by an MDM policy or profile; evidence records whether the value is the device's reported value or the policy's | EP-06 full -> partial: "Shows the lock is enforced at or under the limit. The standard and fixes are evidenced separately." |
| `devices.os_current` | managed computers and phones | OS version at or above the minimum for its platform | none (already partial) |
| `devices.remote_wipe` | managed devices | the management channel can erase the whole device (company owned) or remove company data (personal, if the policy accepts it) | none (already partial) |
| `endpoint.protection_active` | all sensors in scope, including hidden and inactive | reported within `sensor_stale_after_days`, healthy (not reduced functionality, not impaired), supported agent version, antivirus or prevention engine running and current | EP-01 full -> partial: "Shows each sensor is healthy and current. Devices without a sensor, prevention settings and alert handling are separate checks." |

### 5.3 New devices.* and endpoint.* checks

All are `daily`. Coverage is partial everywhere.

| Check key (NEW) | Capabilities | Resource | Population | Predicate | pass, fail, error, insufficient | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|---|
| `devices.recovery_key_escrowed` "Disk recovery keys are held centrally" | device_management | device | devices passing the encryption predicate | a recovery key for the OS volume is held by the MDM or directory; key material is never read | fail: no key held. insufficient: the provider does not report escrow for that platform | per device: escrow present, source, key created date | EP-02 partial: shows encrypted devices stay recoverable. Encryption itself, exceptions and the policy are separate |
| `devices.firewall_enabled` "Laptop firewalls are on" | device_management | device | managed macOS, Windows and Linux computers | the native firewall is on (Windows: every profile, or the provider's firewall health good) | fail: off. insufficient: not reported | per device firewall state and source | EP-03 partial: shows the firewall part of the baseline holds. Other baseline settings and the policy are separate |
| `devices.assigned_to_active_staff` "Every company device belongs to a current person" | device_management, identity_provider | device | company owned managed devices; shared or kiosk devices excluded with a reason | assigned user matches an active member account in the identity provider | fail: unassigned, or assigned to a suspended, deleted or unknown account. insufficient: identity list incomplete | per device: assigned email, account state | EP-03 partial: reconciles devices to the staff list from the device side. LM-01 partial: each device has an accountable person |
| `devices.staff_have_managed_device` "Every person works on a managed device" | device_management, identity_provider | person | active member accounts (not guests or service accounts), minus people excluded with a reason (for example no company device by role) | at least one managed device assigned and in contact | fail: none, or only out of contact devices. insufficient: device or identity read incomplete | per person: devices and their state | EP-03 partial: reconciles the staff list to managed devices, which is how unmanaged laptops are found |
| `devices.leaver_devices_recovered` "Leavers' devices come back or are wiped" | device_management, hr_system | device | devices assigned, on Verity's own record, to a person whose end date is in `lookback_days` and at least `leaver_device_days` ago (contractors at their end date count) | within `leaver_device_days` of the end date the device was wiped with confirmation, unenrolled with a recorded return, or reassigned to an active person | fail: still assigned to the leaver, or no recorded outcome. insufficient: Verity has no observation of the device at the end date (connected later), or the HR list is incomplete | per leaver: end date, devices, outcome and its date | EP-05 partial: shows unreturned devices were wiped. HR-05 partial: covers the device return item of offboarding. HR-03 partial: covers device return at a contractor's end date |
| `devices.wipes_confirmed` "Wipes are confirmed, not assumed" | device_management | device | every wipe command issued in `lookback_days` | the command reached a completed state, or the device later reported wiped | fail: failed, cancelled, or pending past 7 days (setting). insufficient: command history not readable or shorter than the window | per command: device, issued, completed, state | EP-05 partial: shows each wipe executed. Why it was issued and credential rotation stay with people |
| `devices.removable_storage_restricted` "USB storage is blocked or restricted" | device_management | device | managed Windows and macOS company devices | a policy or profile that blocks removable storage, or allows only encrypted media, is assigned and reported applied | fail: none applied. insufficient: the provider cannot report it | per device policy and state | DM-19 partial: covers the removable media route only. Other routes, alerts and reviews stay with people |
| `endpoint.coverage_complete` "Every managed laptop runs the protection agent" | endpoint_protection, device_management | device | managed company computers in contact | a matching sensor passes the `endpoint.protection_active` freshness rule | fail: no matching sensor, or a stale one. insufficient: either read incomplete | per device: match key, sensor id, last seen | EP-01 partial: shows the agent reaches every managed laptop, checked against the device inventory |
| `endpoint.servers_covered` "Every server runs the protection agent" | endpoint_protection, verity_assets | asset | active infrastructure and cloud assets with an operating system recorded, in production (setting), minus exemptions with a reason reviewed in the last 12 months | a matching sensor reported within the window | fail: none, or an exemption older than 12 months. insufficient: asset has no match keys | per asset: match key, sensor, exemption reason and date | EP-01 partial: shows servers in the asset register are covered, and that exemptions are rechecked yearly |
| `endpoint.prevention_enabled` "Protection blocks, not only detects" | endpoint_protection | device | active sensors | the effective policy blocks or quarantines malware (not detect only) and tamper or uninstall protection is on | fail: detect only, or tamper protection off. insufficient: policy not readable | per sensor: policy, prevention mode, tamper state | EP-01 partial: shows agents are set to prevent. Coverage and alert handling are separate |
| `endpoint.detections_triaged` "Endpoint alerts are handled in time" | endpoint_protection | alert | alerts at or above `alert_min_severity` created in `lookback_days` | none still new after `alert_triage_hours`; none open past `alert_close_days` for its severity; every closed alert has an owner and a classification or resolution | fail: any breach, each listed. insufficient: alert query incomplete or retention shorter than the window. Empty: pass with reason "no alerts in the window", only when the query covered the whole window | per alert: severity, status, owner, created, closed, classification | EP-01 partial: shows alerts were reviewed and closed. Whether one became an incident stays with people. LM-04 partial: shows endpoint events were assessed |

### 5.4 Needs for other prefixes (NEED entries)

- NEED identity_provider: administrative and remote access sign ins require a managed or compliant device
  (NS-11.B; partial).
- NEED network_edge + device_management: every managed device is enrolled in the DNS or web filter
  (EP-07.B; partial).
- NEED device_management + verity_assets: every device removed from management in the period has a
  disposal or reassignment record (DM-16.B; partial).
- NEED ticketing: high and critical true positive endpoint alerts link to an incident record (EP-01.D;
  partial).
- People and HR needs: [hr-systems.md section 2.4](connectors/hr-systems.md#24-needs-raised-for-the-identity-research-need-entries).

### 5.5 Feasibility by provider

| Check | Intune | Jamf Pro | Kandji | Google | Defender | CrowdStrike | SentinelOne |
|---|---|---|---|---|---|---|---|
| `devices.enrolled` | yes | yes | yes | partial | | | |
| `devices.disk_encrypted` | yes | yes | yes | yes | | | |
| `devices.screen_lock` | partial | partial | partial | no | | | |
| `devices.os_current` | yes | yes | yes | yes | | | |
| `devices.remote_wipe` | yes | yes | yes | partial | | | |
| `devices.recovery_key_escrowed` | Windows | yes | yes | no | | | |
| `devices.firewall_enabled` | partial (macOS only until the export permission is solved) | yes | yes | yes | | | |
| `devices.assigned_to_active_staff` | yes | yes | yes | yes | | | |
| `devices.staff_have_managed_device` | yes | yes | yes | partial | | | |
| `devices.leaver_devices_recovered` | partial | partial | partial | partial | | | |
| `devices.wipes_confirmed` | partial | yes | partial | partial | | | |
| `devices.removable_storage_restricted` | later | partial | partial | no | | | |
| `endpoint.protection_active` | | | | | yes | yes | yes (fields unverified: console login required) |
| `endpoint.coverage_complete` | | | | | yes | yes | yes |
| `endpoint.servers_covered` | | | | | yes | yes | yes |
| `endpoint.prevention_enabled` | | | | | partial | yes | likely |
| `endpoint.detections_triaged` | | | | | yes | yes | yes |

Verification round (2026-11-23, [verification/devices-hr.md](verification/devices-hr.md)): Kandji escrow
is read from Prism `key_escrowed` and Google firewall from `is_os_native_firewall_enabled`, so both moved
to yes. Intune's Windows firewall report needs an export job whose documented permissions are all
ReadWrite, so it stays out of a read only connector until a read permission is proven.

## 6. Observation contract additions

Extends the `device` and `person.record` types of [01-evidence-model.md 1.4](01-evidence-model.md).

| Observation | Fields to add |
|---|---|
| `device` | platform, OS build, management channel (full MDM, user enrolment, agent only, inventory only), supervised, wipe scope (device, company data only, none), enrolled at, assigned user email and provider user id, recovery key escrowed, screen lock idle seconds and its origin (device value or policy), firewall on, removable storage blocked, match keys (serial, provider device ids, hostname, MAC), state flags (missing, removed, hidden, decommissioned) |
| `device.action` | device, kind (wipe, lock, retire), issued at, completed at, state, source |
| `endpoint.sensor` (or protection fields on `device`) | sensor id, agent version, last seen, health, reduced functionality, prevention mode, tamper protection, policy id |
| `endpoint.alert` | id, device, severity, status, owner, created, updated, closed, classification |
| `person.event`, `person.training`, `person.screening` | see [hr-systems.md section 3](connectors/hr-systems.md#3-what-verity-collects-all-providers) |

## 7. Customers without an MDM

### 7.1 Who they are

Small companies whose laptops are bought by staff or issued without enrolment, often on Google Workspace
or on Microsoft 365 plans that include Intune but never set it up; contractors on their own laptops. For
them EP-02, EP-03, EP-05 and EP-06 are today satisfied only by people, and F1 means the device artifact
cannot be satisfied at all.

### 7.2 Reference agents

| Agent | What it checks | Platforms | Distribution | Built on | Verified |
|---|---|---|---|---|---|
| Drata Agent | screen lock, password manager, antivirus, automatic updates (the README does not mention disk encryption) | latest and previous major LTS of Ubuntu, Windows, macOS | the user installs it and registers with a token from a link emailed by the Drata portal | Electron and osquery (binaries not kept in the repository); Apache-2.0 licence, public on GitHub; unofficial builds unsupported and not code signed | yes [A1] |
| Vanta Device Monitor (formerly Vanta Agent) | antivirus, disk encryption, screen lock, password manager. Corrected: OS updates are not listed | macOS, Windows, Linux; on Linux only disk encryption is detected [A9] | each person installs it after a Vanta task; corrected: no MDM deployment is described, and choosing the MDM option instead blocks the download. Suggested for fewer than 75 devices | osquery (confirmed); open source status not stated | yes [A8][A9] |
| Secureframe Agent | screen lock (session timeout), built in antivirus, local firewall, disk encryption, password, device present [A10] | macOS, Windows, Linux; on Linux no screen lock or antivirus, firewall only UFW on Debian based systems [A10] | each person downloads a unique installer from Employee Onboarding; not meant for mass or scripted deployment [A11] | osquery run by Fleet's Orbit (Windows service named Fleet osquery) [A11]; open source status not stated | yes [A10][A11] |

### 7.3 Building blocks for a Verity agent

- **osquery** is dual licensed Apache-2.0 or GPL-2.0-only [A2]. Its `screenlock` table (macOS) reports
  whether a password is required after sleep or screen saver and the grace period, only for the logged in
  user who logged in recently [A3]: it does not report the idle time before the screen saver starts, so a
  full EP-06 answer needs the managed preference value as well. Confirmed: the `preferences` table reads
  macOS defaults with a `forced` flag for managed values [A12], and `managed_policies` lists MDM and other
  managed policy keys [A13].
  `windows_security_center` reports the health of the firewall, automatic updates and antivirus as Good,
  Poor, Snoozed, Not Monitored or Error [A4]. Disk encryption: `disk_encryption` (POSIX spec; macOS adds
  `filevault_status`) [A14] and `bitlocker_info` on Windows [A15].
- **Fleet** is MIT licensed outside its `ee/` directory; the `ee/` code needs a paid Fleet subscription for
  production use and its licence forbids selling or sublicensing it [A5][A6]. Verity could use the MIT
  parts (or osquery directly) but not resell Fleet's enterprise features. Running a Fleet server per
  tenant adds an operated system to Verity's stack. Secureframe's agent shows the pattern works: osquery
  managed by Fleet's Orbit runtime [A11].
- **Distribution.** macOS software shipped outside the App Store needs a Developer ID certificate, the
  hardened runtime and Apple notarization, uploaded with `notarytool` (Apple stopped accepting `altool`
  uploads on 1 November 2023) [A7]. Windows: corrected, Authenticode signing is needed but does not by
  itself stop SmartScreen warnings; reputation for the file and the certificate builds up over time, and
  EV certificates no longer skip that [A16]. Without an MDM, macOS privacy permissions cannot be pre
  approved: the privacy preferences payload can only be installed by a device management service [A17],
  so users see prompts. Updates, crash handling and uninstall are Verity's to run.

### 7.4 Options compared

| Criterion | A. Verity agent (Go + osquery) | B. MDM connectors only | C. Reviewed device attestation | D. Google Endpoint Verification |
|---|---|---|---|---|
| Evidence strength | system generated, continuous | system generated, continuous, and enforced | self reported with OS screenshots or command output; a reviewer approves | system generated, continuous, not enforced |
| Who it serves | anyone who installs it | only customers with an MDM | everyone | Google Workspace customers |
| Customer effort | each person installs and grants permissions | connect once | each person, every quarter | turn on, staff add the extension |
| Verity build | agent, installers, signing, notarization, updates, ingestion, support | connectors (this plan) | a form, a review queue, reminders | a few fields on the Workspace connector |
| Ongoing cost and risk | software on customer laptops: security patches, OS changes yearly, privacy review | API drift | reviewer time | API drift |
| Scope | explicitly out of scope today | extension | extension, smallest | extension, rides on a Phase 2 connector |
| What it cannot do | enforce or wipe | see unenrolled devices | prove continuity between attestations | report screen lock timeout, wipe laptops |

No authoritative source was found on whether auditors accept screenshots or self attestation for
endpoint controls (unverified: AICPA guidance is not public and was not researched in this round). The attestation path should be presented as people evidence, labelled
as such, sampled by the auditor like any other upload.

### 7.5 Attestation flow (option C) in outline

Per device: owner, serial number, OS and version, ownership. Each quarter (setting) the owner answers five
questions (encrypted, screen lock time, OS updated, firewall on, protection agent) and attaches the
evidence Verity names per OS (for example the FileVault status screen, the BitLocker status, the Lock
Screen settings page). A reviewer approves; approved rows fill the split device artifacts (F1) as
`person` evidence. Overdue attestations show on the control. No software is installed.

## 8. Recommendation

1. **Fix the content first** (F1 to F4). Cheap, no scope question, and it stops a future connector from
   over claiming.
2. **Ask the client for an extension** covering device management, endpoint protection and HR, in this
   order:
   - Intune with Defender for Endpoint, sharing the Entra ID app registration of the Phase 2 identity
     connector: one consent screen, and many small customers already hold the licences.
   - Google devices on the Phase 2 Google Workspace connector, including Endpoint Verification: the
     cheapest system generated path for customers without an MDM.
   - Jamf Pro and Kandji for Mac fleets; CrowdStrike, then SentinelOne once a partner console gives access
     to its API reference.
   - HR: the roster CSV import first (open question 1), then BambooHR, HiBob and Rippling (self service
     credentials), Gusto after Gusto's partner review, Workday on demand through a customer built report.
3. **Do not build an agent now.** The delivery plan excludes it, options B and D cover most customers,
   and C covers the rest. Re-decide when paying customers without an MDM or Google Workspace are a
   meaningful share. If built: Go plus osquery under its Apache-2.0 licence, a fixed set of read only
   queries, results posted to the ingestion API, signed and notarized installers; not Fleet's enterprise
   code.
4. **Offer the attestation flow** as the universal fallback, so every endpoint control can be completed
   without any connector.

## 9. Decisions for the owner

| # | Decision | Options | Recommended |
|---|---|---|---|
| D-DEV-1 | Bring device management, endpoint protection and HR into scope | keep manual (open question 1 reading); extension with the client; Phase 3 | extension, sequenced as in section 8 |
| D-DEV-2 | First device provider | Intune and Defender; Google; Jamf; Kandji | Intune and Defender, then Google |
| D-DEV-3 | Endpoint agent | build now; defer with a trigger; never | defer, with a demand trigger |
| D-DEV-4 | Change four `full` mappings to `partial` (F4) | yes; no | yes |
| D-DEV-5 | Split the device inventory artifact and add `person` sources (F1, F2) | split; keep and add objective level bindings | split |
| D-DEV-6 | Device type in the asset register (F5) | add a device type (migration); keep devices out of the asset register | add, so LM-01.C and DM-16.B work for laptops |
| D-DEV-7 | Personal devices | in scope; out with a reason; per tenant setting | per tenant setting, default in scope when they reach company data |
| D-DEV-8 | Default thresholds in 5.1 | as drafted; other | confirm or amend |
| D-DEV-9 | Google Endpoint Verification desktops: managed or only known | known only (fail `devices.enrolled`); count as managed | known only |
| D-DEV-10 | Attestation flow (option C) | build; rely on plain uploads | build, small |
| D-DEV-11 | Kandji or Iru in the catalogue | rename; show both | show "Iru (Kandji)" |
| D-DEV-12 | Add Defender for Endpoint to `endpoint_protection` | yes; no | yes |
| D-DEV-13 | Add Google Workspace to `device_management` | yes; no | yes |
| D-HR-1 | Roster CSV import as the interim HR source | yes; no | yes |
| D-HR-2 | Direct HR connectors or a unified HR API vendor | direct; aggregator | direct for the first three, revisit after |
| D-HR-3 | HR data held by Verity (privacy notice, DPA, retention) | minimal fields as in hr-systems.md 2.1; more | minimal |
| D-HR-4 | Screening and training sources | HR fields only; add `background_screening` and `security_training` capabilities | add the capabilities in a later round; HR fields meanwhile |

## 10. Sources

- [A1] Drata Agent repository: https://github.com/drata/drata-agent
- [A2] osquery licence: https://raw.githubusercontent.com/osquery/osquery/master/LICENSE
- [A3] osquery `screenlock` table spec: https://raw.githubusercontent.com/osquery/osquery/master/specs/darwin/screenlock.table
- [A4] osquery `windows_security_center` table spec: https://raw.githubusercontent.com/osquery/osquery/master/specs/windows/windows_security_center.table
- [A5] Fleet licence: https://raw.githubusercontent.com/fleetdm/fleet/main/LICENSE
- [A6] Fleet enterprise licence: https://raw.githubusercontent.com/fleetdm/fleet/main/ee/LICENSE
- [A7] Apple, notarizing macOS software: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution (read through its .md version)
- [A8] Vanta, device monitoring: https://help.vanta.com/en/articles/11345823-device-monitoring-in-vanta
- [A9] Vanta, Device Monitor on Linux (search summary): https://help.vanta.com/en/articles/11346064-troubleshooting-the-vanta-device-monitor-on-linux-machines
- [A10] Secureframe, supported MDMs and agent checks: https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
- [A11] Secureframe Agent FAQ (installation, osquery and Orbit): https://support.secureframe.com/en/articles/15111638-faqs-secureframe-agent-installation-coverage-and-troubleshooting
- [A12] osquery `preferences` table spec: https://raw.githubusercontent.com/osquery/osquery/master/specs/darwin/preferences.table
- [A13] osquery `managed_policies` table spec: https://github.com/osquery/osquery/blob/master/specs/darwin/managed_policies.table
- [A14] osquery `disk_encryption` table spec: https://raw.githubusercontent.com/osquery/osquery/master/specs/posix/disk_encryption.table
- [A15] osquery `bitlocker_info` table spec: https://github.com/osquery/osquery/blob/master/specs/windows/bitlocker_info.table
- [A16] Microsoft, SmartScreen reputation for app developers: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
- [A17] Apple, Privacy Preferences Policy Control payload: https://support.apple.com/guide/deployment/privacy-preferences-policy-control-payload-dep38df53c2a/web
- Google Endpoint Verification editions and attributes: see [google-endpoint-management.md](connectors/google-endpoint-management.md) S2, S3
- Internal: `backend/src/verity/seed/content/automation/checks.json`, `capabilities.json`, `objectives/objectives.json`, `objectives/artifacts.json`, `soc2/` and `iso27001/` `control_templates.json` and `template_requirements.json`, `backend/src/verity/modules/assets/models.py`, `docs/product/control-framework-requirements.md`, `docs/product/delivery-plan.md`
