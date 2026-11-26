# Market and audit practice for device evidence (MDM research, round 2)

Brief: [BRIEF.md](BRIEF.md). Round 1: [mdm-and-endpoint-strategy.md](../../mdm-and-endpoint-strategy.md) and
[03-market-research.md](../../03-market-research.md). This file covers what competitors do with device
data, what auditors ask for, what privacy law allows on personal devices, and what that means for Verity.
It does not map provider API fields (the per provider files do that).

Marks: every claim carries a source id in square brackets. A source id means the page was fetched and
read on 26 November 2026. "Unverified" means the point came from a search snippet, from a page whose
content was placeholder text, or from my own reading, and must be checked before anyone builds on it.
Round 1 ids such as [P4] or [D6] point to section 3.13 of `03-market-research.md`.

## 1. Scope

| Area | Covered | Not covered |
|---|---|---|
| Competitors | Vanta, Drata, Secureframe, Sprinto, Scrut, Hyperproof, Thoropass (help centres and integration pages); ServiceNow (Service Graph Connector list only) | private docs behind logins; pricing; Vanta's full directory (only page 1 of 21 of the MDM filter was readable) |
| MDM and device sources | Intune, Jamf, Kandji or Iru, Workspace ONE, JumpCloud, Rippling, Mosyle, Hexnode, Addigy, NinjaOne, Fleet, Google, Kolide, plus others each vendor lists | API fields of each source |
| Audit practice | SOC 2 (public audit firm and platform guidance), ISO 27001 certification (consultancy and certification body blogs), ISO/IEC 27002:2022 control 8.1 from public summaries, CIS Controls v8.1, NIST SP 800-124 Rev. 2 | AICPA guides (not public), the ISO standard text itself (not read) |
| Privacy | GDPR Articles 5 and 88, Article 29 Working Party Opinion 2/2017 (WP249), ICO monitoring workers guidance (4 October 2023, v1.0.0), Germany's Works Constitution Act section 87; Apple User Enrollment; Android work profile on personal devices; Intune's user facing visibility page | national law of other member states; ICO's 2013 BYOD guidance (not read) |

The ICO site returned HTTP 403 to every fetch. The ICO guidance was read from the Internet Archive's copy
of the official PDF [84]; the content is the ICO's own document, version 1.0.0 of 4 October 2023.

## 2. Summary

1. **Intune, Jamf Pro, Kandji or Iru and JumpCloud are table stakes.** Each is integrated by all six SaaS
   competitors that have device features (Vanta, Drata, Secureframe, Sprinto, Scrut, Hyperproof).
   JumpCloud is also the main MDM route to Linux. Round 1 did not have JumpCloud in Verity's order.
2. **Nobody checks phones.** Every competitor either does not sync iOS and Android, or syncs them as
   inventory with no checks. Drata's own guidance (vendor opinion) is that email only phones are usually
   covered by policy [33].
3. **Nobody reads Google endpoint data for desktops.** Sprinto reads Chromebooks only [52], Hyperproof
   lists Chrome devices as proof [59], Drata asks for uploads for Chromebooks [29]. Google Endpoint
   Verification for Mac and Windows is an open gap Verity can fill.
4. **Auditors want a population and a sample, and prefer timestamped system exports with the query
   shown.** Screenshots are accepted when dated, full screen and identifying the device (audit firm
   guidance [65][67]). A current dashboard does not prove the whole period (MDM vendor opinion [68]).
5. **Personal devices: the platforms already hide hardware ids, personal apps and location.** Apple
   User Enrollment withholds serial, UDID, IMEI and MEID [87][88]; Android 12 removes IMEI, MEID and
   serial from personal work profiles [89]. EU and UK guidance says do not capture private use and do a
   DPIA before MDM [83][84]. Verity must drop those fields before storage, for any provider that still
   exposes them.

## 3. MDM and device sources by competitor

Cell legend: **yes** (integration confirmed, with what it supplies), **inv** (devices listed, no posture
checks), **list** (proof lists only, the customer writes tests), **no** (looked, not found), **u**
(unverified: directory page exists but its content is placeholder or a snippet).

| Source | Vanta | Drata | Secureframe | Sprinto | Scrut | Hyperproof | Thoropass | ServiceNow |
|---|---|---|---|---|---|---|---|---|
| Intune | yes: macOS, Windows; no iOS or Android [2] | yes: macOS, Windows, follows Intune compliance verdict [19] | yes: all six checks, macOS, Windows [40] | yes: screen lock, antivirus (Windows) [46][48] | yes [53][54] | list [59][61] | no [35][37] | CMDB only [63] |
| Jamf Pro | yes: macOS only, cloud only [1] | yes: no Jamf Now [21] | yes: all six checks [40] | yes, pages conflict on checks [48][49] | yes [54] | list: computers and mobile devices [60] | no | CMDB only [63] |
| Kandji or Iru | yes: macOS and Windows [4] | yes: macOS computers [22] | yes: macOS, no "device exists" [40] | yes (Iru) [46][48] | yes [54] | list [62] | no | no [63] |
| Workspace ONE | yes: no screen lock through the API [5] | yes: Windows, macOS desktops [24] | yes (AirWatch): antivirus, firewall [40] | yes [46] | no [53] | no [59] | no | CMDB only [63] |
| JumpCloud | yes, including Linux [6][14] | yes: macOS, Windows, Linux [23] | yes: all six checks, macOS, Windows, Linux [40] | yes [46][48] | yes [54] | list [59] | no | no [63] |
| Rippling | yes: computers with a serial only [8] | yes: add on to the HRIS connection [26] | yes: lock, antivirus, exists [40] | no (unverified: may sit under "others" [46]) | no [53] | no [59] | no | no |
| Mosyle | partial: the API gives no posture, Vanta's agent is deployed through Mosyle [11] | no | inv [40] | no | no | no | no | no |
| Hexnode | yes: macOS (documented by Hexnode) [10] | yes: macOS guide read; a Windows guide exists, not read [25] | inv [40] | yes: lock, antivirus, encryption [48] | yes: no encryption or lock through the API [54] | no | no | no |
| Addigy | yes: macOS [9] | no | yes: macOS [40] | no | no | no | no | no |
| NinjaOne | u [12] | no | yes: antivirus, encryption [40] | yes [46] | yes: no encryption or lock [54] | no | no | no |
| Fleet | u [12] | no | no as a source; its agent runs on Fleet's Orbit [A11] and cannot coexist with a self hosted Fleet [43] | no | yes [54] | no | no | no |
| Google (Workspace devices, Endpoint Verification) | no | no; Chromebooks by upload [29] | no [40] | Chromebooks only [52] | no [53] | list: Chrome devices [59] | no | CMDB: Google Console [63] |
| Kolide | u [12] | no | yes: all six checks [40] | no | yes [54][C6] | no | no | no |
| Others named | 1Password Device Trust, Agency [12] | Custom Device Connections (JSON, five booleans) [27] | CrowdStrike, Datto RMM, Scalefusion, SentinelOne, SimpleMDM, Sophos, WatchGuard [40] | Sophos, Atera, ManageEngine [46][48] | Endpoint Central, Island Browser, Kitecyber, Sophos [53] | Okta devices, CrowdStrike, SentinelOne, Defender (vulnerabilities only) [59] | XFA and Swif as partners [38][39] | SCCM, Tanium, Defender for Endpoint, Qualys [63] |
| Own agent | yes [14] | yes [28] | yes [41] | yes [P4] | yes [55] | no | no | no |

Notes on the table:

- Secureframe's "six checks" are its table columns: session timeout, native antivirus, local firewall,
  encryption, password, device exists. It has no OS update or password manager column [40]. Its table
  lists Jamf Pro under Windows too, which Jamf Pro does not manage (likely a page error, unverified).
  Intune's antivirus and firewall cells carry an asterisk the page does not explain [40].
- Sprinto's extended checks page gives Jamf screen lock only [48]; its Jamf integration page gives OS
  version, encryption and antivirus, on macOS, iOS and iPadOS [49]. The two conflict.
- Hexnode encryption: Sprinto claims it [48], Scrut says Hexnode's API has none [54], Secureframe lists
  no checks [40]. Treat Hexnode encryption as unverified until the Hexnode API is read.
- ServiceNow's Service Graph Connectors fill the CMDB; they are not posture tests [63].

**Count of SaaS competitors integrating each source** (of the seven SaaS vendors; confirmed only):
Intune 6, Jamf Pro 6, JumpCloud 6, Kandji or Iru 6, Hexnode 4 with posture (plus 1 inventory),
Workspace ONE 4, Rippling 3, NinjaOne 3, Addigy 2, Kolide 2, Google 2 (Chromebooks or Chrome lists
only), Fleet 1, Mosyle 0 with posture.

## 4. Device tests by competitor and platform

### 4.1 Own agents

| Agent | Encryption | Screen lock | OS updates | Antivirus | Password manager | Firewall | Platforms | Lock threshold | Cadence |
|---|---|---|---|---|---|---|---|---|---|
| Vanta Device Monitor | mac, win, linux | mac, win | not listed | mac, win | mac, win (browser extension counts only here or via JumpCloud) | not listed | macOS, Windows, Linux (Linux: encryption only, Debian variants) [14][15] | passes at 60 minutes idle or less [14] | stale after more than 1 day [16] |
| Drata Agent | yes | yes | yes (automatic updates) | yes | yes | no test found (unverified that none exists) | macOS, Windows, Ubuntu [28][A1] | not found on the test page; its BYOD article recommends 15 minutes [33] | every 24 hours, fixed [28] |
| Secureframe Agent | mac, win, linux | mac, win | no | mac, win | no (it checks a password policy instead) | mac, win, linux (UFW on Debian only) | macOS, Windows, Linux [40][41] | 15 minutes, fixed [42] | daily [42] |
| Dr. Sprinto | yes | yes | yes | yes (supported list) | not listed | yes | macOS, Windows, Linux [46][50] | 15 minutes [P5][47] | 24 hours [46] |
| Scrut Endpoint Agent | yes | yes | not listed | yes | yes (system or browser) | diagnostic only, not a check | Windows 10 and 11, macOS 13 to 26, several Linux distributions [56][57] | not found | every 3 hours [58] |

Per platform detail for Dr. Sprinto and Scrut's agent was not stated beyond the platform list
(unverified per check).

### 4.2 Tests supplied through an MDM

| Competitor | Where the verdict comes from | Mobile |
|---|---|---|
| Vanta | Jamf: FileVault, lock from profiles, antivirus and password manager from app names [1]. Intune: lock, antivirus and encryption from compliance policy state, apps refreshed by Intune every 7 days, no app list on non corporate devices [2]. Iru: FileVault, enrolment, agent status, Activation Lock [4]. Workspace ONE: lock only if a passcode profile is applied [5]. Hexnode: lock only if password and screensaver policies are enforced [10] | not synced from Jamf or Intune [1][2] |
| Drata | Intune: tests 61, 64, 65, 66 follow Intune's own compliance verdict; test 63 (password manager) through a managed app or extension policy [19]. Jamf: lock and updates from extension attribute scripts [21]. Kandji: library items must carry keyword names [22]. Workspace ONE: exactly named policies on Windows [24]. Rippling: no update data, screenshot per device [26] | mobile not supported [30] |
| Secureframe | when an API cannot give a value, the test becomes an upload test [40] | phones may appear in inventory from Intune and Kandji; checks never apply [40] |
| Sprinto | standard checks: OS current, encryption, antivirus, lock, firewall, device mapped to a person; optional DLP, web filtering, inventory [50] | Jamf page lists iOS and iPadOS; which checks run on them is unverified [49] |
| Scrut | common fields per MDM: OS version, serial, antivirus, encryption, lock, all yes or no; daily sync [54] | Hexnode phones go to asset management, not to employees [54] |
| Hyperproof | no built in posture tests; customer writes automated tests over proof lists [59][H2] | Jamf mobile device lists [60] |

**Pattern:** the strongest competitors take the MDM's own compliance verdict (Vanta and Drata on Intune)
or a named policy's presence. Their test is then only as strict as the customer's own MDM policy.

## 5. How competitors handle devices

| Topic | Vanta | Drata | Secureframe | Sprinto | Scrut |
|---|---|---|---|---|---|
| Personal devices | no guidance found | BYOD written into policy; evidence from MDM, agent or screenshots; ask for deletion of company data at exit [33]. Personnel exclusion for a contractor on an unmanaged personal device [32] | screenshot accepted for BYOD, auditor decides [42]; contractors without production or sensitive access are out of MDM scope [40] | owner picks company or personal when submitting a device [51]; manual workflows for BYOD and contractors [50] | not found |
| Phones | not synced [1][2] | unsupported [30] | inventory only [40] | unverified [49] | asset records only [54] |
| Servers | not found | not found | through an endpoint security integration or by hand [44] | not found | not found |
| Device to person | Intune primary user through Entra [2]; Iru assigned user email [4]; owner set or changed by hand [13] | serial plus primary user email or UPN (Intune) [19]; email then username (Jamf) [21]; one owner per device [30] | owners not taken from the MDM; set by hand or a default owner [44] | assigned user email from Jamf [49]; "mapped to a staff member" is a check [50] | email match (Hexnode, JumpCloud, Kolide); NinjaOne syncs only assigned devices [54] |
| Excluding | per device scope toggle [3]; Jamf site or a named group [1]; Iru blueprint by id [4]; Addigy policy filter [9]; contractors by assigning the task to a full time group [14] | per person, with reason and optional date range, shown in audit exports; the person stays in audit scope [32]; manual unlink for retired, lost or stolen [30] | device out of scope; retired devices out of scope [43]; MDM devices cannot be deleted in Secureframe [44] | In Scope or Not in Scope toggle [51] | Kolide out of scope marks pass through [54]; removed Intune devices stay as records [54] |
| Stale | agent: suspect after more than 1 day; MDM: no threshold, Last Check moves only on change [16]; new MDM devices get a 3 hour grace [2][5] | not found; a separation date stops a person's devices syncing [31] | "Last check in" column, no threshold [44]; uninstalled agent drops after about 30 days [43] | Inactive after 90 days without a report or when the owner leaves; a failed sync marks devices Inactive [46][50][51] | not found |
| Several sources | not documented | many MDMs, one per device; the agent wins over any MDM [18] | the agent wins over an MDM [43] | several MDMs scoped by staff group [46]; another page says pick one [47] | not found |

Hyperproof and Thoropass have none of these built in. Thoropass's partner XFA finds devices at sign in,
runs a daily encryption monitor and is pitched for BYOD [38].

## 6. Audit practice

### 6.1 SOC 2

| Point | Source type | Source |
|---|---|---|
| Inventories and reports are "information produced by the entity"; the auditor tests completeness and accuracy, directly or through controls over the report; an unsupported hand made list can be refused in favour of a system generated population | audit firm | Linford [64] |
| For each report: name, source system, filters, period, run time, the query so it can be rerun, the same parameters across periods, record counts tied back. Screenshots are fine if they show date and time, the system address and the whole screen; cropped ones cause rework. Prefer exports and keep originals | audit firm | Schneider Downs [65] |
| If a report cannot be checked, the auditor widens testing or records an exception; management owns the report logic | audit firm | Forvis Mazars [66] |
| Remote laptops: MDM walkthroughs by screen share, a random sample of people checked against policy, HR leavers compared with a serial number ledger, timestamped wipe records, lock at 10 to 15 minutes | audit firm | Linford [67] |
| MDM evidence pack: export of in scope devices with status and collection date, assigned policies with status, proof settings are enforced; a policy alone does not prove management; unenrolled devices need approved exceptions; personal devices only if the audit scope includes them | vendor opinion | Drata [34] |
| No MDM: screenshots per person of encryption, password manager, antivirus and lock | vendor opinion | Vanta [17] |
| Type 2: auditors sample from populations; owner, encryption, password policy and antivirus required per endpoint; updates, firewall and lock recommended | vendor opinion | Secureframe [45] |
| A current dashboard does not prove the period; auditors may ask for state on chosen dates; history usually cannot be rebuilt later; reconcile MDM with identity and HR; timestamped exports beat screenshots | vendor opinion (an MDM vendor) | Hexnode [68] |
| No AICPA table sets sample sizes; each firm's method does; the population must be shown complete first; a system enforced setting may be tested once if change and access controls are reliable | consultancy (says it does not attest) | TCSA [69] |
| Auditors sample device ids and ask for proof of encryption; 25 to 60 samples for frequent controls | vendor and directory site, unverified | [70][71] |

**Reading:** a timestamped system export with its query, filters and record count is preferred over
screenshots; dated full screen screenshots remain acceptable. This rests on audit firm guidance [65][67]
plus vendor opinion [34][68]. No AICPA text on screenshots was found (unverified).

### 6.2 ISO 27001 certification

- A consultancy's A.8.1 checklist: an asset register of all endpoints with owners, including personal
  devices that reach in scope services; evidence of the controls claimed in the Statement of
  Applicability (antivirus, encryption) with records of periodic checks and of what happened when one
  failed; possible screen share walkthroughs and samples; MDM compliance dashboards; proof a leaver's
  device was wiped or returned; signed BYOD acknowledgements [72].
- A certification body (DQS) asks for a communicated policy, every device on the A.5.9 register, user
  duties and BYOD rules; it does not describe evidence formats and does not name MDM [73].
- Advisera lists no artifacts [75]; Sensiba describes Stage 2 only generally [76].
- No certification body text was found on exports compared with screenshots for A.7.9, A.8.7, A.8.8 or
  A.6.7 (unverified).

**ISO/IEC 27002:2022 control 8.1, in my own words**, from public summaries [73][74] (the standard was
not read):

- A topic specific policy on configuring and handling endpoints, communicated to staff.
- It should cover: what classification of information a device may hold; registering devices; physical
  protection; limits on installing software and on updates; use on public networks and off site; access
  control; storage encryption; malware protection; remote disable, lock and erase; backups; web service
  use; analysis of user behaviour; removable media and port control; separating business data and
  blocking local storage of sensitive data; configuration management through control 8.9.
- Users: log off or lock, protect unattended devices, take care in public, guard against theft, follow
  a lost device procedure.
- Personal devices: separate work and personal use technically; the user agrees before use to protect
  and update the device, to claim no ownership of business data, and to accept deletion of work data
  within what privacy law allows. The policy also covers intellectual property, the employer's right of
  access as far as law allows, and software licences.
- Wireless: configuration procedures and the backup risk of weak links.

### 6.3 CIS Controls v8.1 safeguards that define checks

Read from a mirror of the CIS v8.1 guide (August 2024) [77], checked against v8 sources [78][79]. CIS
text is licensed CC BY-NC-ND 4.0 [77]: cite safeguard numbers, never ship the text.

| Safeguard | IG | In my words | Verity check it supports |
|---|---|---|---|
| 1.1 | 1 | detailed inventory of every asset that can hold data, with owner and whether it may connect; includes remote assets and devices that connect often; reviewed twice a year | `devices.assigned_to_active_staff`, inventory completeness |
| 1.2 | 1 | deal with unauthorised assets weekly | `devices.staff_have_managed_device` (finds unmanaged) |
| 1.3, 1.4 | 2 | active discovery daily; DHCP or IPAM logs feed the inventory weekly | none (network sources) |
| 3.6 | 1 | encrypt end user devices holding sensitive data | `devices.disk_encrypted` |
| 4.1 | 1 | documented secure configuration process, yearly review | document |
| 4.3 | 1 | automatic lock at most 15 minutes on general purpose OSs, at most 2 minutes on mobile; CIS metric is locked assets over assets able to lock [78] | `devices.screen_lock`, with a separate mobile threshold |
| 4.5 | 1 | host firewall on end user devices, default deny | `devices.firewall_enabled` (CIS asks more than "on") |
| 4.10 | 2 | lock out after failed local logins: at most 20 on laptops, 10 on phones and tablets | new key proposed in section 10 |
| 4.11 | 2 | remote wipe of enterprise data on company owned portable devices when lost, stolen or the person leaves | `devices.remote_wipe`, `devices.leaver_devices_recovered` |
| 4.12 | 3 | separate work and personal space on mobile | ownership and enrolment channel |
| 7.3 | 1 | automated OS patching monthly or faster | `devices.os_current` |
| 10.1, 10.2 | 1 | anti-malware on all assets; automatic signature updates | `endpoint.protection_active`, `av_signatures_current` |

### 6.4 NIST SP 800-124 Rev. 2 (May 2023), for phone and tablet checks only

Laptops are out of its scope [80]. Points that define checks: the EMM can deny access by OS version,
rooted or jailbroken state, model or MDM client version (4.2.1.1); unlock authenticator with a retry
limit, idle lock, remote lock, wipe after failed attempts or after a period without check in (4.2.1.2);
encryption of storage (4.2.1.3); full wipe for company devices, enterprise only wipe for personal ones,
and the console updates status after a wipe so it can be confirmed (4.3.3); fast update deployment with
blocking of non compliant devices (4.3.6); containers and mobile threat defence (4.3.7, 4.2.3). On
privacy, it notes EMM and threat defence tools can collect location and contacts, that location needs
notice and consent, and that app management instead of full MDM eases privacy on personal devices
(3.1.11, 4.2.2, 4.3.13, 5.1.3) [80].

## 7. BYOD and privacy

### 7.1 What the law and regulators say (EU and UK)

| Point | Source |
|---|---|
| Collect only what the purpose needs; do not reuse it for an incompatible purpose; keep it only as long as needed | GDPR Art. 5(1)(b), (c), (e) [81] |
| Member states may set specific rules for employee data, which must include safeguards on monitoring systems at work | GDPR Art. 88 [82] |
| Consent is very unlikely to be a valid basis at work because of the employment relationship | WP249 sections 3.1.1 and 6.2 [83]; ICO, power imbalance [84] |
| On personal devices, identifiers such as MAC addresses and security scans are named privacy risks; areas presumed private (for example the photo folder) should in principle not be accessed; measures must separate private and business use | WP249 section 5.4.2 [83] |
| MDM: do a DPIA before deploying; location must serve a stated purpose and never become ongoing monitoring; location can be held without showing it to the employer until a device is reported lost; employees must be told what tracking happens | WP249 section 5.4.3 [83] |
| Before device monitoring: document the purpose and why less intrusive means will not do; identify a lawful basis; do a DPIA where high risk (and the ICO advises one anyway); consider consulting workers; tell workers | ICO, device activity section [84] |
| When workers use their own devices for work, do not capture their private use of the device | ICO [84] |
| Set and justify a retention schedule for monitoring data; do not keep it in case it becomes useful | ICO [84] |
| Covert monitoring is unlikely to be justified in normal circumstances | ICO [84] |
| Germany: the works council co-determines the introduction and use of technical devices that monitor behaviour or performance | Works Constitution Act s. 87(1) no. 6 [93]. Whether a compliance tool reading MDM data falls under it is a legal question for the customer (unverified) |

### 7.2 What the platforms were built to hide

| Platform and channel | Hidden from the organisation | Still visible | Source |
|---|---|---|---|
| Apple User Enrollment (personal iPhone, iPad, Mac) | serial number, UDID, IMEI, MEID and any persistent hardware id; a temporary enrolment id is used instead and changes on re-enrolment; user installed App Store apps; personal accounts | managed apps, profiles, certificates, general device and security information; iOS and iPadOS lock command | [86][87][88] |
| Apple User Enrollment, actions | erase device, passcode clearing; lost mode and Activation Lock are not in the command lists | removal of managed data when enrolment ends | [86][88][92] |
| Apple User Enrollment, passcode | the server can require only a six digit, non simple passcode, nothing stronger | | [88] (2019 session, current behaviour unverified) |
| Android work profile on a personal device (Android 12 and later) | IMEI, MEID and serial; personal apps, data and usage; personal profile network traffic | an enrolment specific id stable across resets; work profile apps and data; work profile network logs | [89][90] |
| Android work profile, Google's user page | personal apps, data and usage | the same page lists model, serial, device id, phone number, carrier, MAC and location from work apps; this conflicts with [89] for Android 12 and later on serial (unverified which applies per OS version) | [90] |
| Intune, any personal device | call and browsing history, email and texts, contacts, calendar, passwords, photos, document contents; location of a personal device | owner, name, serial, model, manufacturer, OS version, IMEI; last four digits of the phone number; managed apps only | [91] |

Intune's user page is generic: it says serial and IMEI are always visible, while Apple and Android
withhold them on the personal channels [87][89]. A connector must expect those fields to be absent, and
must not treat absence as an error.

### 7.3 Rules for Verity on personal devices

These apply when `ownership` is `personal`, or the channel is `byod_account_driven` or
`work_profile_personal`, or ownership is `unknown` (treat unknown as personal until the customer
classifies it). The normaliser drops the field before anything is persisted, even if the provider sends
it.

**Never store for personal devices**

| # | Field | Why |
|---|---|---|
| P1 | `serial_number`, `hardware_ids` (UDID, IMEI, MEID), MAC addresses | the platforms withhold them on purpose [87][89]; WP249 names MAC identifiers as a BYOD risk [83]. Matching uses `provider_device_id` (the enrolment id). Whether a tenant keyed hash of the serial may be kept for cross source matching is an owner decision (D-MKT-3) |
| P2 | phone number, including partial digits | not needed for any check; Intune exposes the last four [91] |
| P3 | location, network details (SSID, IP, carrier) | WP249 and ICO [83][84]; never needed |
| P4 | `installed_apps` (full inventory) | personal apps are hidden by design [86][90][91]; keep only `managed_apps`, and only the derived booleans (`av_present`, password manager present) where a check needs them |
| P5 | `device_name` and `hostname` | often carry a person's or family member's name; not needed when the device is linked to a membership. Keep `model` and `platform` |
| P6 | local account names, file paths, processes, registry or event log entries, browser history, messages, photos, contacts, calendar | Intune's Device Query exposes some of these on corporate Windows devices [91]; Verity never calls device query or live query features on any device |
| P7 | anything from a personal profile or personal account | WP249 and ICO: do not capture private use [83][84] |

**Also, for every device**

| # | Rule | Source |
|---|---|---|
| G1 | Device data is used only as control evidence. Never compute per person activity, productivity or usage scores | ICO purpose and transparency [84]; GDPR Art. 5(1)(b) [81] |
| G2 | A retention period per observation type, set by the tenant within a Verity maximum, and enforced by a job | ICO retention [84]; GDPR Art. 5(1)(e) [81] |
| G3 | Publish the exact field list per provider and per ownership, so the customer can tell workers and complete a DPIA; offer it as a download | ICO and WP249 [83][84] |
| G4 | Never present employee consent as the lawful basis in Verity's screens or templates | WP249, ICO [83][84] |
| G5 | Actions on personal devices are recorded as kind, state and time only; full wipe is not an expected kind on a personal channel | Apple, NIST [88][80] |

## 8. Customer patterns

| Pattern | What competitors do | Verity proposal |
|---|---|---|
| Small company, Macs and Windows laptops, two MDMs (for example Jamf for Macs, Intune for Windows) | Drata: many MDMs, one per device, its agent wins [18]. Sprinto: several, each scoped to staff groups [46], though another page says pick one [47]. Secureframe and Drata: agent wins over MDM [18][43]. Vanta: precedence not documented. No one documents merging the same device from two MDMs | Population is the union. Match by serial (company devices), then provider ids. Per key authority: the MDM that manages the device's platform supplies its state; a second source fills only gaps, and a disagreement is shown in the evidence, not silently resolved. A device is counted once |
| Google Workspace only, no MDM | No competitor reads Endpoint Verification for Mac or Windows. Sprinto reads Chromebooks [52]; Hyperproof lists Chrome devices [59]; Drata wants uploads [29] | Google device connector (round 1 D-DEV-13) as a differentiator, labelled "known, not managed" (D-DEV-9). Screen lock timeout and wipe stay with the attestation flow (round 1 section 7.4) |
| Contractors on their own laptops | Drata: personnel exclusion with reason, person stays in audit scope [32][33]. Secureframe: out of MDM scope without production or sensitive access [40]. Vanta: give the device task to a full time group only [14]. Sprinto: manual workflow or group scope [46][50] | `ownership: personal` with the rules in 7.3. Scope set per tenant (D-DEV-7). Exclusion per person or per device with reason, approver and review date, printed in the evidence. Attestation where the contractor reaches company data |
| Phones with email only | No competitor checks phones (sections 4 and 5). Drata: policy is often enough for email only phones (vendor opinion) [33]. Secureframe: mark out of scope [40] | Phones are a separate population with their own thresholds (lock 2 minutes per CIS 4.3 [77]). Personal phones with email only: evidence is the identity or app protection rule that limits mail to compliant or managed apps (a NEED for the identity research), not a device check |

## 9. Implications for Verity

1. **Connector order.** Intune, Jamf Pro, Kandji or Iru and JumpCloud are what every competitor has
   (section 3). Google devices are what no one has. Proposed order: Intune (with Defender, as round 1),
   Google devices, Jamf Pro, Kandji or Iru, JumpCloud; then Workspace ONE and Hexnode; then Rippling,
   NinjaOne, Kolide, Addigy. Mosyle only after its API is shown to give posture (Vanta found it does not
   [11]).
2. **Read settings, not only the MDM verdict.** Vanta and Drata pass Intune devices on Intune's own
   compliance state [2][19], so their test is as weak as the customer's policy. Verity keeps the verdict
   as secondary evidence (BRIEF) and judges the setting against its own threshold where the API exposes
   the setting.
3. **Every evidence file carries IPE metadata**: source system and API, filters and scope, run time,
   record count, paging completed, Verity check version. This answers the completeness and accuracy
   questions auditors ask [64][65][66].
4. **Daily state kept per device for the whole audit period**, so an auditor's sample on any date can
   be answered [67][68]. This confirms round 1's "history from enrolment" approach.
5. **Thresholds.** Default screen lock 15 minutes for computers (CIS 4.3, Secureframe, Sprinto, Linford
   [77][42][P5][67]) and a separate 2 minute mobile default (CIS 4.3). Vanta passes at 60 minutes [14];
   Verity's stricter default with the CIS reference is a point to make to buyers.
6. **Phones are a real gap.** Since no competitor checks phones, Verity can lead, but only for company
   owned phones (supervised or fully managed). Personal phones follow section 7.3 and are evidenced
   through access rules.
7. **Several sources per device.** Competitors pick one source per device or let an agent win. Verity
   should merge per key with recorded authority and show conflicts (section 8).
8. **Exclusions with reason, approver, expiry, at both person and device level, printed in the
   evidence.** Drata does person level [32]; Secureframe and Sprinto device level [43][51].
9. **Staleness.** Competitors range from 1 day (Vanta agent) to 90 days (Sprinto) [16][50]. Round 1's
   14 day `stale_after_days` default with `insufficient` per device is reasonable and stricter than
   most.
10. **People link through the MDM's assigned user email to a tenant membership** (CLAUDE rule 3), with
    `assignment_source` recorded. Secureframe does not trust the MDM's owner at all [44]; a manual
    override must therefore exist and be audited.
11. **Privacy rules are enforced in code.** The never store list in 7.3 runs in the normaliser before
    persistence, with a test per provider that feeds a personal device fixture and asserts the fields
    are absent.
12. **Customer privacy pack**: field list per provider and ownership, a worker notice template, DPIA
    inputs, and a note that German customers may need works council agreement [93] (legal reading
    unverified).
13. **Linux.** Agents cover Linux poorly (Vanta: encryption only [15]; Secureframe: no lock or antivirus
    [40]). JumpCloud is the one MDM with Linux posture across competitors [23][40].

## 10. Proposed dictionary keys

| Key | Meaning | Check that would use it | Source |
|---|---|---|---|
| `failed_unlock_limit` | number of failed unlock attempts before lockout or wipe, and its origin (policy or device) | new `devices.unlock_attempts_limited` (CIS 4.10: at most 20 on computers, 10 on mobile) | [77][80] |
| `firewall_default_deny` | the host firewall blocks unsolicited inbound connections, not only "on" | stricter predicate for `devices.firewall_enabled` | [77] |

For personal devices, `provider_device_id` must hold the per enrolment id (Apple enrolment id, Android
enrolment specific id), since no hardware id is available [88][89]. No new key is needed for that.

## 11. Corrections to round 1

| # | File and place | Round 1 claim | Correction | Source |
|---|---|---|---|---|
| C1 | 03-market-research.md 3.3, Vanta | MDMs: Jamf Pro, Kandji, Intune | add Workspace ONE, JumpCloud, Rippling, Addigy (macOS), Hexnode (macOS), Mosyle (agent deployment only); Iru covers macOS and Windows | [4][5][6][8][9][10][11] |
| C2 | 03 3.3, Drata | Jamf, Kandji, Intune, JumpCloud; "the agent wins over Jamf" | add Workspace ONE, Hexnode, Rippling (add on), Custom Device Connections. Since 27 May 2026 Intune has one macOS and Windows guide using Intune's compliance verdict; [D10] is the legacy guide. The agent wins over any MDM | [18][19][24][25][26][27] |
| C3 | mdm-and-endpoint-strategy.md 7.2, Drata Agent | "the README does not mention disk encryption" | the help article lists encryption among the agent's checks | [28] |
| C4 | strategy 7.2, Vanta | no lock threshold | the lock test passes at 60 minutes or less; Linux "encryption only" now confirmed on the page, not from a snippet | [14][15] |
| C5 | 03 3.3, personal devices | "a personnel exclusion for device checks" | Drata's exclusions are per person and cover all that person's devices; a single device cannot be excluded alone | [32] |
| C6 | 03 3.3, Scrut | built on "not stated", macOS page, "Sync Now" | built on osquery, runs on Windows, macOS and Linux, syncs every 3 hours, adds a password manager check | [55][56][57][58] |
| C7 | 03 3.3, Sprinto | MDMs: Hexnode, Intune, Jamf; cadence conflicting | list adds Iru, Sophos, JumpCloud, Atera, Google (Chromebook), Workspace ONE, NinjaOne, ManageEngine; cadence 24 hours; Inactive after 90 days; its two Jamf pages conflict | [46][48][49][50] |
| C8 | 03 3.3, Sprinto | "Hexnode (all three checks)" | conflicts with Scrut (no encryption or lock in Hexnode's API) and Secureframe (no checks); mark unverified | [48][54][40] |
| C9 | 03 3.3, Secureframe | cadence "Not stated" | daily; 19 sources in the capability table | [40][42] |
| C10 | strategy 7.2, Secureframe Agent | no threshold | fixed 15 minute lock; password at least 8 characters with complexity; the agent's result wins over an MDM; no OS update and no password manager check | [41][42][43] |
| C11 | 03 3.3, Hyperproof | MDM integrations "Not checked" | Jamf, Intune, Kandji, JumpCloud, Google Chrome devices, CrowdStrike, SentinelOne proof types; no posture tests | [59] |
| C12 | 03 3.3, ServiceNow | Intune and Jamf connectors | the list also has Google Console, SCCM, Workspace ONE, Tanium, Defender for Endpoint, Qualys | [63] |
| C13 | 03 3.3, Thoropass | "None found; MDM coming soon" | still no native MDM; device posture through partners XFA and Swif | [35][38][39] |
| C14 | strategy 7.4 | "No authoritative source was found on whether auditors accept screenshots" | audit firm guidance accepts dated, full screen screenshots and prefers exports with parameters; AICPA text still not found | [65][67] |

## 12. Decisions for the owner

| # | Decision | Options | Recommended |
|---|---|---|---|
| D-MKT-1 | Connector order | as round 1; as section 9 item 1 | section 9 item 1 (adds JumpCloud to the first wave) |
| D-MKT-2 | Phone checks | none; company owned phones only; all phones | company owned phones only |
| D-MKT-3 | Serial on personal devices | never stored; tenant keyed hash for matching | never stored, until a matching need is shown |
| D-MKT-4 | Unknown ownership | treat as personal; treat as company | treat as personal until classified |
| D-MKT-5 | Mobile screen lock default | 2 minutes (CIS); 5 minutes; same as computers | 2 minutes, editable |

## 13. Sources

All read on 26 November 2026 unless marked unverified.

Vanta
1. Connecting Jamf Pro: https://help.vanta.com/en/articles/11345770-connecting-vanta-jamf-pro
2. Connecting Intune: https://help.vanta.com/en/articles/11345786-connecting-vanta-microsoft-endpoint-manager-intune-mdm
3. Removing Intune devices: https://help.vanta.com/en/articles/11345965-how-to-remove-devices-from-vanta-for-microsoft-endpoint-manager-intune
4. Connecting Iru: https://help.vanta.com/en/articles/11345787-connecting-vanta-iru
5. Connecting Workspace ONE: https://help.vanta.com/en/articles/11345780-connecting-vanta-vmware-workspace-one-mdm
6. JumpCloud MDM: https://help.vanta.com/en/articles/11345785-integrating-vanta-jumpcloud-mdm
7. JumpCloud directory page (partly placeholder): https://www.vanta.com/integrations/jumpcloud
8. Connecting Rippling: https://help.vanta.com/en/articles/11345682-connecting-vanta-rippling
9. Connecting Addigy: https://help.vanta.com/en/articles/11345686-connecting-vanta-addigy
10. Hexnode's guide to the Vanta integration: https://www.hexnode.com/mobile-device-management/help/how-to-integrate-vanta-with-hexnode-uem.md
11. Device Monitor through Mosyle: https://help.vanta.com/en/articles/12489802-deploying-the-vanta-device-monitor-with-mosyle-mdm
12. Directory pages, placeholder content (unverified): https://www.vanta.com/integrations/kolide, https://www.vanta.com/integrations/fleet, https://www.vanta.com/integrations/ninjaone, filter page https://www.vanta.com/integrations?filters=MDM
13. Computers page: https://help.vanta.com/en/articles/11345380-computers-page
14. Device monitoring in Vanta: https://help.vanta.com/en/articles/11345823-device-monitoring-in-vanta
15. Device Monitor on Linux: https://help.vanta.com/en/articles/11346064-troubleshooting-the-vanta-device-monitor-on-linux-machines
16. Last Checked column: https://help.vanta.com/en/articles/11345936-understanding-the-last-checked-column-on-the-computers-page
17. Evidence for unmonitored laptops: https://help.vanta.com/en/articles/11345596-evidence-collection-for-unmonitored-laptops

Drata
18. Multiple MDM support (new experience): https://help.drata.com/en/articles/13613980-multiple-mdm-support-new-experience
19. Intune guide (current): https://help.drata.com/en/articles/16190016-microsoft-intune-integration-guide
20. Intune for Mac guide (legacy): https://help.drata.com/en/articles/5899473-microsoft-intune-integration-guide-mac-devices
21. Jamf guide: https://help.drata.com/en/articles/5456409-jamf-integration-guide
22. Kandji (Iru) guide: https://help.drata.com/en/articles/5831405-kandji-now-iru-integration-guide-mdm
23. JumpCloud MDM: https://help.drata.com/en/articles/5872265-jumpcloud-mdm-connection
24. Workspace ONE: https://help.drata.com/en/articles/7068294-workspace-one-mdm-connection
25. Hexnode macOS: https://help.drata.com/en/articles/6063710-hexnode-uem-macos-connection
26. Rippling: https://help.drata.com/en/articles/5014534-rippling-integration-guide-hris-mdm-uar
27. Custom Device Connections: https://help.drata.com/en/articles/12014143-custom-device-connections
28. How the Drata Agent works: https://help.drata.com/en/articles/4742932-how-does-the-drata-agent-work
29. Chromebooks: https://help.drata.com/en/articles/6297654-how-to-handle-device-compliance-for-chromebooks
30. Multi device support: https://help.drata.com/en/articles/13613390-multi-device-support
31. Device linking and removal: https://help.drata.com/en/articles/12401019-understanding-device-linking-removal-and-visibility-in-drata
32. Personnel exclusions: https://help.drata.com/en/articles/13521706-personnel-exclusions
33. BYOD and audits: https://help.drata.com/en/articles/6297649-how-do-bring-your-own-device-byod-devices-affect-my-audit
34. Evidence for MDM software (DCF-574): https://help.drata.com/en/articles/16402161-how-to-collect-evidence-for-dcf-574-mobile-device-management-software

Thoropass
35. Asset intelligence: https://help.thoropass.com/en/articles/11887300-asset-intelligence
36. Asset inventory collection: https://help.thoropass.com/en/collections/14300359-asset-inventory
37. Integrations page: https://www.thoropass.com/platform/integrations
38. XFA partnership: https://www.thoropass.com/blog/streamlining-compliance-thoropass-and-xfa-solve-compliance-challenges
39. Partner programme: https://www.thoropass.com/blog/thoropass-integration-partner-program

Secureframe
40. Supported MDMs and capabilities (table parsed from the page HTML): https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
41. Agent fields pulled: https://support.secureframe.com/en/articles/15111648-secureframe-agent-fields-pulled
42. Agent macOS profiles and password policy FAQ: https://support.secureframe.com/en/articles/15877671-faqs-secureframe-agent-macos-profiles-password-policy-and-endpoint-checks
43. Agent overview FAQ: https://support.secureframe.com/en/articles/15111652-faqs-secureframe-agent-overview-and-common-questions
44. Asset inventory page: https://support.secureframe.com/en/articles/15111079-asset-inventory-page-details
45. Preparing for a SOC 2 Type 2 audit: https://support.secureframe.com/en/articles/15111418-preparing-for-a-soc-2-type-2-audit

Sprinto
46. Device health through MDM: https://docs.sprinto.com/data-library/staff-devices/dashboard-actions/set-up-device-health-reporting-via-mdm
47. Getting staff devices compliant: https://docs.sprinto.com/data-library/staff-devices/how-sprinto-helps-in-getting-staff-devices-compliant-ready
48. Extended checks in MDM tools: https://docs.sprinto.com/monitors/extended-checks-in-mdm-tool-comms
49. Jamf integration: https://docs.sprinto.com/integrations/overview/jamf-integration
50. Staff devices, how it works: https://docs.sprinto.com/data-library/staff-devices/how-it-works
51. Staff devices FAQ: https://docs.sprinto.com/data-library/staff-devices/frequently-asked-questions
52. Google Workspace Chromebook: https://docs.sprinto.com/integrations/overview/google-workspace-chromebook-staff-device-management-integration

Scrut
53. Integrations overview: https://help.scrut.io/docs/integrations-overview
54. Per MDM pages (read as .md): https://help.scrut.io/docs/integrating-jamf-pro, https://help.scrut.io/docs/microsoft-intune, https://help.scrut.io/docs/integrating-kandji, https://help.scrut.io/docs/integrating-jumpcloud, https://help.scrut.io/docs/integrating-hexnode, https://help.scrut.io/docs/integrating-fleet, https://help.scrut.io/docs/integrating-ninjaone, https://help.scrut.io/docs/integrating-sophos, https://help.scrut.io/docs/integrating-kolide
55. Agent walkthrough: https://help.scrut.io/docs/scrut-agent-walkthrough
56. Agent supported OSs: https://help.scrut.io/docs/scrut-agent-supported-operating-systems
57. Agent collected data: https://help.scrut.io/docs/viewing-collected-agent-data
58. Agent FAQ: https://help.scrut.io/docs/scrut-agent-faqs-troubleshooting

Hyperproof
59. Supported apps and proof types: https://intercom.help/hyperproofio/en/articles/14303912-supported-apps-and-proof-types-for-hypersyncs
60. Jamf proof types: https://intercom.help/hyperproofio/en/articles/14303947-jamf-proof-types-and-permissions
61. Intune proof types: https://intercom.help/hyperproofio/en/articles/14303946-microsoft-intune-proof-types-and-permissions
62. Kandji proof types: https://intercom.help/hyperproofio/en/articles/14303954-kandji-proof-types-and-permissions

ServiceNow
63. Available Service Graph Connectors: https://www.servicenow.com/docs/r/servicenow-platform/service-graph-connectors/cmdb-sgc-available.html

Audit practice
64. Linford, IPE in SOC audits: https://linfordco.com/blog/iuc-ipe-audit-procedures-for-soc-audits/
65. Schneider Downs, SOC audit IPE: https://schneiderdowns.com/our-thoughts-on/soc-audit-ipe-explained-how-to-avoid-delays-rework-exceptions/
66. Forvis Mazars, IPE readiness: https://www.forvismazars.us/forsights/2026/04/ipe-readiness-in-soc-examinations
67. Linford, remote physical security: https://linfordco.com/blog/soc-2-physical-security-remote-considerations/
68. Hexnode, UEM data as SOC 2 evidence: https://www.hexnode.com/blogs/uem-data-soc-2-audit-evidence/
69. TCSA, SOC 2 sampling: https://www.tcsa.in/learn/soc-2-sampling-and-sample-sizes
70. Sprinto blog on device gaps (unverified, snippet): https://sprinto.com/blog/fix-top-device-security-gaps-that-delay-soc-2-audits/
71. soc2auditors.org sample sizes (unverified, snippet): https://soc2auditors.org/insights/soc-2-sample-size/
72. HT Black (High Table), A.8.1 audit checklist: https://hightable.io/iso-27001-annex-a-8-1-audit-checklist/
73. DQS, control A.8.1: https://www.dqsglobal.com/en/explore/blog/strengthening-user-device-security-with-control-a801
74. ISMS.online, ISO 27002 control 8.1: https://www.isms.online/iso-27002/control-8-1-user-endpoint-devices
75. Advisera, control 8.1: https://advisera.com/iso27001/control-8-1-user-endpoint-devices/
76. Sensiba, Stage 2 preparation: https://knowledge.sensiba.com/preparing-for-your-iso-27001-stage-2-audit
77. CIS Controls v8.1 guide (mirror): https://researchsoc.iu.edu/resources/crosswalks/cis_controls__v8.1_guide__2024_0801.pdf
78. CIS assessment specification, safeguard 4.3: https://controls-assessment-specification.readthedocs.io/en/latest/control-4/control-4.3.html
79. Tenable, CIS v8 references: https://tenable.com/audits/references/CSCv8
80. NIST SP 800-124 Rev. 2: https://csrc.nist.gov/pubs/sp/800/124/r2/final and https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-124r2.pdf

Privacy and platforms
81. GDPR Article 5: https://gdpr-info.eu/art-5-gdpr/
82. GDPR Article 88: https://gdpr-info.eu/art-88-gdpr/
83. Article 29 Working Party, Opinion 2/2017 on data processing at work (WP249), sections 5.4.2 and 5.4.3: https://ec.europa.eu/newsroom/article29/items/610169 (PDF https://ec.europa.eu/newsroom/article29/redirection/document/45631)
84. ICO, Employment practices and data protection: monitoring workers, v1.0.0, 4 October 2023 (ico.org.uk returned 403; read from the archived official PDF): https://ico.org.uk/media/for-organisations/uk-gdpr-guidance-and-resources/employment-information/employment-practices-and-data-protection-monitoring-workers-1-0.pdf via https://web.archive.org/web/2024/
85. Apple, User Enrollment and device management (published 17 September 2026): https://support.apple.com/guide/deployment/user-enrollment-and-mdm-dep23db2037d/web
86. Apple, Device management service User Enrollment information (31 March 2025): https://support.apple.com/guide/deployment/device-management-service-user-enrollment-dep6ae3f1d5a/web
87. Apple, Managed Device Attestation (29 July 2024): https://support.apple.com/guide/deployment/managed-device-attestation-dep28afbde6a/web
88. Apple, WWDC19 session 303, What's new in managing Apple devices (2019): https://developer.apple.com/videos/play/wwdc2019/303/
89. Android 12 enterprise features: https://developer.android.com/work/versions/android-12
90. Google, What policies is my organization enforcing on my device (Pixel for Business help, undated): https://support.google.com/pixel-enterprise/answer/7502354?hl=en
91. Microsoft, What info can your organization see when you enroll your device (30 October 2026): https://learn.microsoft.com/en-us/intune/user-help/enrollment/data-visibility
92. Hexnode, Apple User Enrollment for iOS devices: https://www.hexnode.com/mobile-device-management/help/apple-user-enrollment-for-ios-devices.md
93. Germany, Works Constitution Act (English translation), section 87: https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html

Round 1 ids used here: [A1] [A11] from `mdm-and-endpoint-strategy.md` section 10; [C6] [H2] [P4] [P5] [D10]
from `03-market-research.md` section 3.13.
