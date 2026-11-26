# 4. Checks, and how device evidence reaches objectives and controls

The chain for device evidence, using Verity's model (AUTHORING 1):

```
device fields (02)  ->  check (this file, 4.2 and 4.3)  ->  artifact (4.4)  ->  objective (4.5)
                    ->  control EP-01..EP-08, DM-19, HR-05, HR-03, LM-01, NS-11  ->  SOC 2 and ISO 27001 (4.6)
```

A check is written once per capability (`device_management`, `endpoint_protection`), evaluated per device with
the platform rules of [01](01-device-landscape.md) 1.5, and fills one or more artifacts. An objective is met
when every artifact its methods name is satisfied; a person source always stays on every artifact (evidence
model rule 1.3.1). Every mapping below is **partial**: no device check proves a design objective, and the
operating objectives also need a person's follow up. The machine readable form is
[device-evidence-map.csv](device-evidence-map.csv).

## 4.1 Shared rules (extend round 1 section 5.1)

| Rule | Detail |
|---|---|
| Population | every device record in scope from every connected source, merged ([05](05-process.md) 5.3), including missing, hidden and removed records with their state; personal devices per `personal_devices`; exclusions only with a reason |
| Completeness | a source read that did not page to the end, or a `reporting_gaps` section the check needs, gives `insufficient` for every affected device |
| Freshness | state checks use `inventory_reported_at` (falling back to `last_check_in_at` only where the source has no separate inventory time); older than `stale_after_days` gives `insufficient` for state checks and `fail` for `devices.enrolled` |
| Platform rules | per platform predicate from 01 1.5; a platform the source cannot answer for is `insufficient` with the reason; `not_applicable` only where 01 says so (for example encryption on a Cloud PC) |
| Policy evidence | a value whose `idle_lock_origin` or source is a policy counts only when the policy is reported installed or active on that device (`device.policy.applied_state`) |
| Provider verdict | `provider_compliance_state` is printed beside Verity's result and never decides it |
| Exceptions | a failing device with an exception in force is listed as "failing, exception in force" and does not fail the run (engine change D-MDM-6) |
| Weak matches | a device matched on name only, or a person linked with `assignment_confidence` weak, never satisfies a completeness check |
| Evidence file | per check per run: scope, population and its sources, per device values with their source and time, exceptions, weak matches, completeness, Verity check version, query and filters (the auditor's information produced by the entity questions [market 6.1]) |

## 4.2 Catalogue

28 checks: 6 shipped (content only, none implemented), 11 proposed in round 1, 11 new in round 2. Round 1
section 5 holds the full predicates of the first 17; this table updates them where round 2 changed them.

| Check | Status | Population | Predicate (short) | Round 2 change |
|---|---|---|---|---|
| `devices.enrolled` | shipped | all device records in scope | managed (provider rule) and in contact within `stale_after_days`; `legacy_device_admin` fails with that reason | channel and `managed_by` from 02; no double count across sources |
| `devices.disk_encrypted` | shipped | managed computers and phones | encrypted per the platform rule (01 1.5) | in_progress and paused are not on; Android default key fails; iOS needs a passcode; Cloud PC `not_applicable` |
| `devices.screen_lock` | shipped | managed computers and phones | an installed or active policy sets idle lock at or under the limit (computers `max_idle_lock_minutes`, mobile `max_idle_lock_minutes_mobile`) and requires authentication; mobile also `passcode_present` with a policy assigned | policy evidence on every platform; separate mobile limit (D-MDM-9); Apple `passcode_compliant` alone never passes |
| `devices.os_current` | shipped | managed computers and phones | at or above the platform minimum, the major still supported, supplemental version read; Android complete patch level within `android_patch_max_age_days` and version in the latest bulletin; ChromeOS before `autoUpdateThrough` | Android and Apple rules from research |
| `devices.remote_wipe` | shipped | managed devices | the channel allows a full erase (company) or removal of company data (personal, if the policy accepts it); record `erase_method` | Apple: no supervision or bootstrap token needed; User Enrolment cannot erase |
| `endpoint.protection_active` | shipped | sensors in scope | healthy, current, reported within `sensor_stale_after_days` | none |
| `devices.recovery_key_escrowed` | round 1 | devices passing encryption, macOS and Windows (Linux where reported) | the vendor's escrow record shows a key held; "has a key" alone is `fail` for escrow | Intune macOS `insufficient` (no metadata route); Google `not_applicable` for ChromeOS; fix hint for a Mac encrypted before escrow: rotate the key in the MDM [verify-apple] |
| `devices.firewall_enabled` | round 1 | managed macOS, Windows, Linux | firewall on (Windows every profile) | Intune via per setting state when a policy evaluates it; Android `not_applicable` |
| `devices.assigned_to_active_staff` | round 1 | company devices, shared and dedicated excluded with reason | assigned person is an active member; strong assignment only | `assignment_confidence` |
| `devices.staff_have_managed_device` | round 1 | active members minus "no company device" | at least one managed device in contact | JumpCloud and Rippling can answer without a separate identity provider |
| `devices.leaver_devices_recovered` | round 1 | devices assigned to leavers in the window | within `leaver_device_days`: wipe confirmed, return recorded, or reassigned | wipe must be confirmed by a later signal; Rippling device orders as return evidence |
| `devices.wipes_confirmed` | round 1 | wipe commands in `lookback_days` | `confirmed_by` later_signal, or a provider erase status that is not an Apple reply alone | partial on every Apple vendor [apple G3] |
| `devices.removable_storage_restricted` | round 1 | managed Windows and macOS company devices | a policy blocking or limiting removable storage is applied | macOS DDM `ExternalStorage` (macOS 15) as a policy source |
| `endpoint.coverage_complete` | round 1 | managed company computers in contact | a matching healthy sensor | none |
| `endpoint.servers_covered` | round 1 | server assets in production | a matching sensor | none |
| `endpoint.prevention_enabled` | round 1 | active sensors | blocking mode and tamper protection | none |
| `endpoint.detections_triaged` | round 1 | alerts at or above severity in the window | triaged and closed in time | none |
| `devices.purchased_devices_enrolled` | **new** | every device in a purchase list (`device.purchase`), minus released and retired with a record | a managed device matches on serial or IMEI and checked in within `stale_after_days`, at most `enrol_grace_days` after being added | finds bought devices that never enrolled [apple 4.2][ms 2.3][google 9] |
| `devices.directory_devices_managed` | **new** | `device.directory` records of active members signed in within `directory_active_days` (default 30, at least 21 [ms G17]), company or unknown ownership | the device is managed (matched to a managed record) or excepted | finds unmanaged laptops reaching company sign in |
| `devices.enrolled_before_issue` | **new** | company devices first assigned in the period | enrolment observed on or before the first assignment, or before the person's HR start date | `insufficient` for devices enrolled before Verity connected; Autopilot registration time is never used [ms G10] |
| `devices.drift_fixed_in_time` | **new** | per device failures of the baseline checks (encryption, lock, OS, firewall, integrity) found in the period | each returned to passing within `drift_fix_days` (default 14) or had an exception in force | reads Verity's own daily history, so it works for every provider |
| `devices.updates_automatic` | **new** | managed company computers and phones | an OS update policy (DDM software update, Windows Update ring, Android `systemUpdate`, ChromeOS auto update) is applied | EP-04.B; policy evidence only |
| `devices.browsers_current` | **new** | managed company computers | every installed managed browser within `browser_max_age_days` of the latest stable release | EP-04 names browsers; inventory lag noted [ms G15] |
| `devices.software_permitted` | **new** | company devices with an app inventory | no installed app outside the permitted list or catalogue, or each one removed within `software_fix_days` | EP-03.E (ISO A.8.19); needs the customer's list (D-MDM-16) |
| `devices.os_integrity` | **new** | managed devices | integrity on: SIP and secure boot (Mac), Secure Boot and code integrity (Windows), not jailbroken or rooted and Play Integrity at least device level (mobile), verified boot (ChromeOS) | each sub key `not_collected` gives `insufficient` |
| `devices.activation_lock_org_controlled` | **new** | company Apple devices | no device has a user linked Activation Lock (`lockType` USER) | a personal lock blocks reuse of a leaver device until cleared; the fix hint names Apple Business, which can clear it for company owned devices [apple G26, verify-apple] |
| `devices.removed_have_disposal_record` | **new** (was a NEED) | devices that left management in the period | a disposal, return to stock or reissue record in Verity Assets within `disposal_record_days` | needs the device type in Assets (D-DEV-6) |
| `devices.byod_apps_protected` | **new** | personal phones and tablets reaching company data (`device.app_protection`, `device.directory`) | each runs company apps under app protection, or is enrolled on a personal channel | evidences the personal device rule; needs objective EP-03.F (4.7) |

Deferred, no objective tests it yet: `devices.unlock_attempts_limited` (CIS 4.10), `devices.local_admin_limited`.

## 4.3 Outcome cases per new check

| Check | fail | insufficient | empty population |
|---|---|---|---|
| `devices.purchased_devices_enrolled` | a purchased device with no managed match after the grace period | a purchase list read incomplete; Apple Business holds only some purchases (retail buys missing): stated in evidence, never a pass on what was not seen | pass with reason only when the purchase source shows zero devices for the organisation |
| `devices.directory_devices_managed` | an active staff device not managed and not excepted | directory read incomplete; device with no owner | pass with reason "no staff devices registered in the directory" |
| `devices.enrolled_before_issue` | enrolled after first assignment or after the start date | no observation of the device before assignment (connected later) | pass with reason "no devices first issued in the period" |
| `devices.drift_fixed_in_time` | a failure open past `drift_fix_days` with no exception | history gap longer than `history_gap_days` | pass with reason "no baseline failures found", only when the period's daily runs are complete |
| `devices.updates_automatic` | no update policy applied | policy not readable for the platform | insufficient |
| `devices.browsers_current` | a browser older than allowed | inventory older than `stale_after_days` | insufficient |
| `devices.software_permitted` | an app outside the list, not removed in time | no permitted list set; inventory missing | insufficient |
| `devices.os_integrity` | any sub key off | sub key `not_collected` | insufficient |
| `devices.activation_lock_org_controlled` | a company device locked to a personal account | lock type unknown | pass with reason "no Apple devices", only when the population source covers Apple |
| `devices.removed_have_disposal_record` | removed with no record in time | removal date unknown | pass with reason "no devices left management in the period" |
| `devices.byod_apps_protected` | a personal device reaching company data without protection or enrolment | app protection or directory read incomplete | pass with reason "no personal devices reached company data", only when sign in data covers the period |

## 4.4 Artifacts: which checks fill what

Round 1 finding F1 (one inventory artifact named by 11 objectives) is resolved by the split below. Every
artifact keeps `{"kind": "person"}`. "Fill" follows evidence model rule 1.3.2: `full` only when the check
collects the artifact itself for the whole population; under refinement G1 only a `full` fill can satisfy the
artifact alone.

| Artifact | State | Objectives | Checks (fill) | Person fallback |
|---|---|---|---|---|
| `inventory-of-company-devices` | exists, narrowed | EP-03.B, EP-03.C, EP-01.B, EP-06.B, EP-07.B | `devices.enrolled` (full), `devices.purchased_devices_enrolled` (partial), `devices.directory_devices_managed` (partial), `devices.staff_have_managed_device` (partial), `devices.assigned_to_active_staff` (partial) | MDM export or sheet; attestation |
| `device-encryption-report` | new (F1) | EP-02.B, EP-02.C | `devices.disk_encrypted` (full), `devices.recovery_key_escrowed` (partial), `devices.drift_fixed_in_time` (partial) | encryption export; attestation with the OS status screen |
| `device-protection-agent-report` | new (F1) | EP-01.B | `endpoint.protection_active` (full), `endpoint.coverage_complete` (partial), `endpoint.prevention_enabled` (partial) | EDR console export |
| `device-wipe-capability-report` | new (F1) | EP-05.B | `devices.remote_wipe` (full), `devices.activation_lock_org_controlled` (partial) | MDM export |
| `device-baseline-report` | **new (round 2)** | EP-03.D | `devices.firewall_enabled` (partial), `devices.os_integrity` (partial), `devices.drift_fixed_in_time` (partial) | baseline report from the MDM |
| `permitted-software-report` | **new (round 2)** | EP-03.E | `devices.software_permitted` (full) | software inventory export reviewed against the list |
| `personal-device-access-report` | **new (round 2)** | EP-03.F (proposed) | `devices.byod_apps_protected` (partial); NEED identity_provider: company apps require a compliant or protected device | conditional access export |
| `screen-lock-setting-report` | exists | EP-03.D, EP-06.B, EP-06.C, EP-06.D | `devices.screen_lock` (full; add as source, round 1 F2), `devices.drift_fixed_in_time` (partial) | profile export; attestation |
| `patch-compliance-report` | exists | EP-03.D, EP-04.B, EP-04.C, EP-04.D | `devices.os_current` (partial: browsers and apps remain), `devices.browsers_current` (partial), `devices.updates_automatic` (partial, EP-04.B), `devices.drift_fixed_in_time` (partial) | monthly report from the device tool |
| `wipe-confirmations-for-recovered-or-lost` | exists | EP-05.C, EP-05.D, EP-05.E | `devices.wipes_confirmed` (partial), `devices.leaver_devices_recovered` (partial) | recycler certificate, task records |
| `completed-offboarding-records-for-leavers-in` | exists | HR-05.C, HR-05.E, EP-05.C, EP-05.E | `devices.leaver_devices_recovered` (partial) | closed checklist |
| `leakage-prevention-and-sharing-settings-in` | exists | DM-19.C (and DM-19.A, B) | `devices.removable_storage_restricted` (partial) | settings export |
| `disposal-records-or-certificates` | exists | EP-08.B, EP-08.C | `devices.removed_have_disposal_record` (partial), `verity.assets.disposal_recorded` | contractor certificates |
| `asset-inventory` | exists | LM-01.B, LM-01.C, EP-01.B | `assets.resources_registered` with MDMs and purchase sources as `asset_discovery` (partial), `endpoint.servers_covered` (partial) | asset register export |
| `approved-exceptions` | exists | EP-02.D | `verity.exceptions.in_force` (full) | approved exception records |
| `log-of-control-deficiencies-with-owner` | exists | EP-04.D, EP-06.D | `devices.drift_fixed_in_time` (partial), `verity.tasks.remediation_in_sla` | remediation log |

## 4.5 Objective by objective

What device evidence proves for each objective, which platforms it reaches, and what stays with people.
"All MDM platforms" means macOS, Windows, iOS, iPadOS, Android and ChromeOS through a supporting provider
(03 3.2); Linux only through agents.

| Objective | Device evidence proves | Checks | Platforms automatable | Stays with people |
|---|---|---|---|---|
| EP-01.A standard | nothing | none | none | the standard |
| EP-01.B agent on every endpoint and server | each managed laptop and each server asset has a healthy, preventing sensor | `endpoint.protection_active`, `endpoint.coverage_complete`, `endpoint.servers_covered`, `endpoint.prevention_enabled` | computers via EDR; phones out of scope | exemption reasons and their yearly recheck |
| EP-01.C alerts reviewed | each alert triaged and closed in time | `endpoint.detections_triaged` | EDR | the action taken and why |
| EP-01.D incidents registered | none from devices | NEED ticketing | none | the incident judgement |
| EP-02.A policy | nothing | none | none | the policy |
| EP-02.B encrypted throughout, keys central | each device encrypted on every day of the period, keys escrowed | `devices.disk_encrypted`, `devices.recovery_key_escrowed` (daily history) | all; escrow on macOS and Windows | the period before Verity connected |
| EP-02.C checked before issue and fixed | encrypted at first observation before assignment; failures fixed in time | `devices.enrolled_before_issue`, `devices.drift_fixed_in_time` | all | the issue process interview |
| EP-02.D exceptions | each unencrypted device has an exception in force | `verity.exceptions.in_force` | n/a | the safeguard is real |
| EP-03.A policy | nothing | none | none | the policy, including the personal device rule |
| EP-03.B every company device enrolled before issue | every purchased and known company device is managed; enrolment preceded issue | `devices.enrolled`, `devices.purchased_devices_enrolled`, `devices.enrolled_before_issue` | all with a purchase source (Apple Business, Autopilot, Knox, ChromeOS); otherwise the MDM's own list only, stated in evidence | devices bought outside purchase programs |
| EP-03.C reconciled with the staff roster | every person has a managed device; every device has a current person; staff devices seen at sign in are managed | `devices.staff_have_managed_device`, `devices.assigned_to_active_staff`, `devices.directory_devices_managed`, `hr.roster_exported` | all | follow up of each gap |
| EP-03.D baseline applied, drift fixed | encryption, lock, OS, firewall and integrity hold, and failures were fixed in time | `devices.disk_encrypted`, `devices.screen_lock`, `devices.os_current`, `devices.firewall_enabled`, `devices.os_integrity`, `devices.drift_fixed_in_time` | all (firewall: computers) | that the baseline is sensible |
| EP-03.E permitted software (proposed add) | no unapproved software on company devices, or removed in time | `devices.software_permitted` | company computers and phones with inventory | the permitted list itself |
| EP-03.F personal devices (proposed add, 4.7) | personal devices reaching company data were enrolled on a personal channel or used protected apps | `devices.byod_apps_protected` + NEED identity_provider | phones; laptops through agents or conditional access | the decision to allow BYOD |
| EP-04.A policy | nothing | none | none | the policy |
| EP-04.B deployed automatically | an update policy is applied on every device | `devices.updates_automatic` | all MDM platforms | interview |
| EP-04.C patched in time | OS and browsers within the timeframes on every day | `devices.os_current`, `devices.browsers_current` | all; browsers on computers | third party apps beyond browsers (later, `known_vulnerabilities`) |
| EP-04.D laggards followed up | failures returned to passing or excepted in time | `devices.drift_fixed_in_time`, `verity.tasks.remediation_in_sla` | all | |
| EP-05.A procedure | nothing | none | none | the procedure |
| EP-05.B every managed device can be wiped | the channel allows erase; no personal Activation Lock blocks recovery | `devices.remote_wipe`, `devices.activation_lock_org_controlled` | all except Apple User Enrolment and Android personal work profile (company data only) | |
| EP-05.C lost and unreturned devices wiped | each leaver device recovered or confirmed wiped | `devices.leaver_devices_recovered` | all | lost device reports (Tasks) |
| EP-05.D wipes confirmed | each wipe confirmed by a later signal | `devices.wipes_confirmed` | all; Apple always needs the later signal | |
| EP-05.E credentials rotated | none | none | none | all |
| EP-06.A standard | nothing | none | none | the standard |
| EP-06.B enforced by device management | a lock policy is installed on every device | `devices.screen_lock` | all; Linux through agents | |
| EP-06.C within the standard | idle limit at or under the standard; authentication required | `devices.screen_lock` | all, policy values (device reported only on Shared iPad) | Apple User Enrolment idle time |
| EP-06.D fixes recorded | failures fixed in time | `devices.drift_fixed_in_time` | all | |
| EP-07.B filter covers every managed device | NEED network_edge: every managed device runs the filter client | NEED | computers | |
| EP-08.B disposal records | every device that left management has a record | `devices.removed_have_disposal_record` | all | contractor certificates (EP-08.C) |
| DM-19.C removable storage | a restricting policy is applied | `devices.removable_storage_restricted` | macOS, Windows | the exceptions for encrypted media |
| HR-05.E devices returned or wiped | each leaver device returned, reassigned or confirmed wiped | `devices.leaver_devices_recovered` | all | tokens, badges, handover |
| HR-03.D contractor devices returned | same, at the contractor's end date | `devices.leaver_devices_recovered` | all | artifact home to decide (removal records are about access) |
| LM-01.C inventory complete | devices from device and purchase sources appear in the asset register | `assets.resources_registered` with device sources | all, once Assets has a device type (D-DEV-6) | vendor systems |
| NS-11.B device rules on remote access | NEED identity_provider: remote and admin access require a managed or compliant device | NEED | n/a | |

## 4.6 Controls and frameworks

Mappings from `template_requirements.json`; device checks are partial against each.

| Control | SOC 2 | ISO 27001:2022 | Device checks that map (partial) |
|---|---|---|---|
| EP-01 EDR and anti-malware | CC6.8 (full) | A.8.1, A.8.7, A.8.16 | `endpoint.*` |
| EP-02 Full disk encryption | CC6.1, CC6.5, CC6.7 | A.7.9, A.7.10, A.8.1, A.8.24 | `devices.disk_encrypted`, `devices.recovery_key_escrowed`, `devices.enrolled_before_issue`, `devices.drift_fixed_in_time` |
| EP-03 Device management enrolment | CC6.5, CC6.8 | A.6.7, A.7.9, A.8.1, A.8.19 | `devices.enrolled`, `devices.purchased_devices_enrolled`, `devices.directory_devices_managed`, `devices.enrolled_before_issue`, `devices.assigned_to_active_staff`, `devices.staff_have_managed_device`, `devices.firewall_enabled`, `devices.os_integrity`, `devices.software_permitted`, `devices.byod_apps_protected`, `devices.drift_fixed_in_time` |
| EP-04 Patch management (devices, after the split) | CC6.8, CC7.1 | A.8.8 | `devices.os_current`, `devices.browsers_current`, `devices.updates_automatic`, `devices.drift_fixed_in_time` |
| EP-05 Remote wipe | CC6.5 | A.5.11, A.7.9, A.7.14, A.8.1 | `devices.remote_wipe`, `devices.activation_lock_org_controlled`, `devices.wipes_confirmed`, `devices.leaver_devices_recovered` |
| EP-06 Screen lock | CC6.1 | A.7.7, A.8.1 | `devices.screen_lock`, `devices.drift_fixed_in_time` |
| EP-07 Web filtering (ISO only) | none | A.8.23 | NEED network_edge |
| EP-08 Equipment wiping and disposal (proposed) | C1.2, CC6.5 | A.7.10, A.7.14 | `devices.removed_have_disposal_record` |
| DM-19 Data leakage prevention | none | A.5.14, A.7.10, A.8.12 (full) | `devices.removable_storage_restricted` |
| HR-05 Offboarding | CC6.2, CC6.3 | A.5.11, A.6.5 | `devices.leaver_devices_recovered` |
| HR-03 Contractors | CC6.2, CC9.2 | A.5.11, A.8.30 | `devices.leaver_devices_recovered` |
| LM-01 Asset inventory | CC2.1, CC6.1 | A.5.9 | `assets.resources_registered` (device sources), `devices.assigned_to_active_staff` |
| NS-11 Remote access | CC6.6 | A.6.7, A.8.21 | NEED identity_provider |

## 4.7 Content changes this file proposes (for D2 review)

| # | Change | Why |
|---|---|---|
| CC1 | Apply round 1 F1 split and add `device-baseline-report`, `permitted-software-report`, `personal-device-access-report` | every device check reaches an artifact that tests what it proves |
| CC2 | EP-03.E (already proposed in 06-control-changes) uses `permitted-software-report` instead of `inventory-of-company-devices` | keeps the inventory artifact about enrolment only |
| CC3 | Add objective EP-03.F: "Personal devices that reached company data met the personal device rules: enrolled on a personal channel, or company data reached only through protected apps, checked against sign in records." (operating; test; `personal-device-access-report`) | ISO A.6.7 and A.8.1 cover personal devices and no objective tests the rule |
| CC4 | Add parameter `max_idle_lock_minutes_mobile` (default 2) to EP-06.C | CIS 4.3 sets a stricter mobile limit [market 6.3] |
| CC5 | HR-03.D gains `completed-offboarding-records-for-leavers-in` or a contractor return record as an artifact | the device return part has no artifact a device check can fill |
| CC6 | Register the 11 new checks in `checks.json` with the mappings above, `implementations` per 03 3.2, and the 11 round 1 checks with their mappings | checks with no artifact cannot move an objective (round 1 finding) |
| CC7 | `capabilities.json`: `device_management` gains Google, JumpCloud, Workspace ONE, ManageEngine, Addigy, SimpleMDM, Fleet, NinjaOne, Rippling, Device Trust, Apple Business (as a purchase source); show Kandji as Iru (Kandji) | catalogue matches the plan |

None of these changes is applied by this plan. They go through D2 and land in work package MDM-1 ([06](06-build-plan.md)).
