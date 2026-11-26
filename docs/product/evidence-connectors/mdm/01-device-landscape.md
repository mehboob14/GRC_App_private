# 1. The device landscape: types, ownership, enrolment channels and what each can prove

What Verity can know about a device depends less on the MDM vendor than on three facts about the device:
its **platform**, its **ownership**, and the **channel** it was enrolled through. Apple, Microsoft and Google
cap what any MDM can see per channel, by design. This file sets those caps once, so every connector and every
check is judged against them. Facts come from the round 2 research files in [research/](research/), cited as
`[apple]`, `[ms]`, `[google]`, `[apple-mdms]`, `[xplat-a]`, `[xplat-b]`, `[market]` with the section, and
from the verification logs as `[verify-apple]`, `[verify-ms]` (Microsoft and Google) and `[verify-xplat]`.

## 1.1 Device classes

| Class | Examples | Evidence posture | Checks that apply |
|---|---|---|---|
| Computer, company owned | MacBook from Apple Business, Autopilot laptop, Linux workstation | the core population for every EP control | all device checks |
| Computer, personal | contractor's own laptop, staff BYOD laptop | limited by channel; often agent only or not managed | per the personal device policy (1.6); privacy rules in [02](02-what-verity-collects.md) 2.5 |
| Phone or tablet, company owned | supervised iPhone, fully managed Android, company iPad | full posture on supervised or fully managed channels | encryption, passcode, OS current, wipe, assignment. Competitors mostly list phones without checks (Sprinto's Jamf page lists iOS and iPadOS; which checks run there is unclear) [market 2, 4.2; verify-xplat X8], so this is a Verity lead |
| Phone or tablet, personal | own iPhone with mail, Android work profile | the platform hides hardware ids and personal apps | access rule evidence first (identity provider or app protection), device checks only for what the channel shows |
| Shared or dedicated | Shared iPad, Android kiosk, meeting room PC | no single person | excluded from person reconciliation with a reason; encryption and OS checks still apply; lock checks use the device value where reported (Shared iPad) |
| Virtual desktop | Windows 365 Cloud PC, AVD single or multi session | encryption and lock are the platform's, not the device's | encryption `not_applicable` with reason [ms G5, G6]; OS current and protection apply |
| Server | EC2, VM, on premises server | not an MDM matter | EDR and asset register (`endpoint.servers_covered`, NS-13); out of the device population |

## 1.2 The channel model across platforms

One vocabulary for every platform. The right column is the value Verity stores as `enrolment_channel`
([02](02-what-verity-collects.md)).

| Platform | Channel | Ownership signal | Supervision or owner rights | `enrolment_channel` |
|---|---|---|---|---|
| macOS, iOS, iPadOS | Automated Device Enrolment (serial in Apple Business) | company (purchase record) | supervised | `automated_company` |
| macOS, iOS, iPadOS | Device enrolment, profile based | unknown | Mac supervised from macOS 11; iPhone and iPad not | `user_initiated_device` |
| macOS, iOS, iPadOS | Device enrolment, account driven (Managed Apple Account) | unknown, meant for company | Mac supervised; iPhone and iPad not | `account_driven_device` (new value, [apple 9 P7]) |
| macOS, iOS, iPadOS | User Enrolment, account driven (BYOD) | personal | never | `byod_account_driven` |
| iPadOS | Shared iPad (ADE) | company | supervised | `automated_company`, class shared |
| Windows | Autopilot or Entra join | company | n/a | `automated_company` when Autopilot, else `user_initiated_device` [ms 3.1] |
| Windows | Hybrid join, co-management with Configuration Manager | company | n/a | `user_initiated_device` or `automated_company` [ms 3.1] |
| Windows | Personal device with a work account added | personal | n/a | `user_initiated_device`, ownership personal |
| Windows, any | Entra registered or joined but not managed | unknown | none | `registered_only` |
| Android | Fully managed, dedicated (device owner) | company | device owner | `automated_company` (zero touch or KME) or `user_initiated_device` |
| Android | Work profile on a company owned device (11 and later) | company | profile owner, company owned | `work_profile_company` |
| Android | Work profile on a personal device | personal | profile owner | `work_profile_personal` |
| Android | Legacy device admin | unknown | weak: password policies stop working for apps targeting API 29 [google G22] | `legacy_device_admin` (new value; fails enrolment) |
| ChromeOS | Enterprise enrolment | company | n/a | `automated_company` when pre provisioned, else `user_initiated_device` |
| Linux | Intune Linux, JumpCloud, Fleet agent | company in practice | agent | `agent_only` (Fleet with MDM: by platform) |
| macOS, Windows, Linux | Agent without MDM (Google Endpoint Verification, 1Password Device Trust, an RMM agent) | per source | none | `agent_only` |
| Phones | App protection only (Intune MAM), no enrolment | unknown | none | no device record: evidenced as an access rule (1.6) |
| Any | Purchase list only, never enrolled (Apple Business, Autopilot `notContacted`, zero touch, KME, ChromeOS `PRE_PROVISIONED`) | company | none | `inventory_only` |

## 1.3 What each channel lets any MDM see and do

The caps below hold for every vendor; a vendor can only expose less. Detail per key is in the research
matrices: Apple [apple 2.2, 2.3], Microsoft [ms 2.1, 2.2, 2.3], Android and ChromeOS [google 2.1, 2.2].

### 1.3.1 Apple

| Ability | ADE (supervised) | Device enrolment | User Enrolment (personal) |
|---|---|---|---|
| Serial number, UDID | yes | yes | no: an enrolment id instead, which changes on re-enrolment |
| FileVault state (Mac) | yes | yes | readable, but FileVault cannot be enforced; escrow forbidden |
| Recovery key escrow (Mac) | when the escrow payload was installed before FileVault was turned on; a Mac encrypted earlier needs a key rotation (`RotateFileVaultKey`) before its key is escrowed [apple G5, verify-apple] | same | no |
| Passcode present and compliant (iPhone, iPad) | yes | yes | through DDM status only |
| Idle lock time | policy value only, on every Apple platform [apple 3.6] | policy only | not provable |
| Firewall, SIP, Secure Boot (Mac) | yes | yes | yes |
| Full app list | yes | yes | managed apps only |
| Software update state | DDM status (OS 27 removed the old MDM update commands [apple G8]) | DDM | no |
| Wipe | yes, no supervision needed | yes | no: unenrolment removes managed data only |
| Lost Mode | supervised iPhone and iPad only; no Mac lost mode | no | no |
| Location | never collected by Verity, whatever the vendor offers |

Apple specifics that change checks:
- iPhone and iPad encryption is not a setting: data protection is on when the hardware supports it and a
  passcode is set. A device with no passcode is not encrypted in the sense of the control [apple G7].
- `passcode.is-compliant` reads true when no passcode policy exists [apple G1]. Compliance counts only with
  a policy assigned (`passcode_policy_assigned`).
- macOS has no passcode present or compliant keys at all. Mac screen lock is always policy evidence [apple G2].
- A supervised Mac is not proof of company ownership: Mac device enrolment also supervises [apple G15].
  Ownership comes from Apple Business or the customer's classification.
- Erase replies do not prove the outcome: the Mac can answer Error and still erase, or Acknowledged and not
  erase, depending on the fallback setting, and a Default erase may send no reply at all; the reply is not
  resent [apple G3, verify-apple].
- A user linked Activation Lock blocks reuse of a returned device; Apple Business can clear it for devices
  the company owns [verify-apple].

### 1.3.2 Windows

| Ability | Entra joined or Autopilot | Hybrid or co-managed | Personal with work account | Cloud PC | AVD multi session |
|---|---|---|---|---|---|
| Serial number | yes | yes | yes | unverified | unverified |
| BitLocker state | yes (OS drive; attestation needs a reboot [ms G4]) | yes | yes | not applicable | not supported |
| Recovery key escrow | yes, metadata without the key | partial: keys kept only in on premises AD are not visible | yes | n/a | n/a |
| Idle lock, firewall, password | per setting state, only where a compliance policy evaluates the setting [ms G1] | same | same | partial | firewall and some password settings; no idle lock [verify-ms K3] |
| Antivirus state | yes (`windowsProtectionState`) | yes | yes | yes | yes |
| App inventory | yes, refreshed every 7 days [ms G15] | yes | managed apps only | yes | yes |
| Wipe | yes | yes | yes | partial | no (wipe and remote lock disabled [verify-ms K3]) |

Windows specifics: retiring an Entra joined laptop suspends BitLocker, so a retired leaver laptop can read
unencrypted on its last report [ms G12]. Devices set up with Autopilot device preparation appear in the
Autopilot list only when they were also registered; unregistered ones are missed by "registered but never
enrolled" [ms G11, narrowed by verify-ms K5]. Intune enrolment type values above 12 (Android corporate modes,
Azure VM, account driven user enrolment) are documented only in the beta API: read the field from beta, or map
those devices to `unknown` [verify-ms K1].

### 1.3.3 Android

| Ability | Fully managed or dedicated | Work profile, company owned | Work profile, personal |
|---|---|---|---|
| Serial, IMEI | yes | yes | no on Android 12 and later: an enterprise specific id instead [google G2]; Intune documents the serial as possibly missing on any personal work profile, and never shows IMEI or MEID there [verify-ms K2] |
| Encryption | yes (`encryptionStatus`); "active with default key" means no user credential protects it [google G6] | yes | yes (device level) |
| Screen lock timeout | policy only (`maximumTimeToLock`; 0 means none) [google G8] | policy only | policy only, applicability unverified |
| Patch level | yes, judged on the complete level (the 5th of the month) [google G12] | yes | yes |
| Integrity | Play Integrity posture | yes | yes |
| Wipe | factory reset | wipe or remove work profile | removes the work profile only |
| Apps | full | work profile only | work profile only; never collect personal apps |

Android data reaches Verity only through the customer's MDM. The Android Management API cannot be used by
Verity: it has one full control scope and is limited to EMMs and partners [google G1].

### 1.3.4 ChromeOS

Encryption is always on by design and not reported per device; screen lock delay is a policy read through the
Chrome Policy API; `bootMode` Dev means verified boot is off; `autoUpdateThrough` gives the support end date
per device [google 2.2]. A true read only admin privilege exists for ChromeOS devices [google 4].

### 1.3.5 Linux

No platform MDM channel. Sources are agents: Intune for Ubuntu and RHEL (compliance settings for encryption,
password complexity and distribution version only; no idle lock) [ms 2.1], JumpCloud System Insights
[xplat-a], Fleet and osquery [xplat-b], 1Password Device Trust [xplat-b]. Drata and Secureframe read Linux
posture through JumpCloud [market 3; verify-xplat X9]. Wipe is `not_applicable` with a reason.

## 1.4 Purchase programs: the population an MDM cannot give

An MDM cannot see a laptop that never enrolled. Purchase programs list what the company bought, whether or not
it enrolled. Joining them to the MDM inventory finds company devices that were never enrolled, enrolled in the
wrong service, or released.

| Program | Platforms | Read only access | What it gives | Limits |
|---|---|---|---|---|
| Apple Business API (formerly Apple Business Manager) | Apple | yes: API account with a custom role limited to viewing devices and services and reading Activation Lock status; ES256 client assertion, one hour token [apple 4.2] | every device linked to the organisation: serial, order, purchase source, assigned MDM service, Activation Lock type (MDM, user, none) | retail purchases without the organisation's customer number are missing [apple G16]; "assigned" means assigned to a service, not enrolled [apple G17]; webhooks need a write, so Verity polls |
| Windows Autopilot device identities | Windows | yes: DeviceManagementServiceConfig.Read.All [ms 4] | serial, `enrollmentState` (`notContacted` is never enrolled), last contact | device preparation devices appear only if also registered [verify-ms K5]; never select `productKey` |
| Android zero touch | Android | **no read only path**: one scope for the whole API, Owner and Admin have equal API access [google 4] | devices claimed to the customer | owner decision D-MDM-11: recommended no; ask for a CSV export instead |
| Samsung Knox Mobile Enrolment | Samsung Android | yes: scope `kme.devices:view` [google 4] | reseller uploaded devices and their enrolment state | Samsung only |
| ChromeOS pre provisioned | ChromeOS | yes: Directory read only scope with a read only role [google 4] | devices registered by the reseller (`PRE_PROVISIONED`) | ChromeOS only |
| Verity Assets (device type) | any | Verity's own record | devices the customer registered by hand or import | as complete as the customer keeps it |

The identity provider is a third source: Entra devices with `isManaged` false and `trustType` Workplace are
devices reaching company sign in that no MDM manages [ms 2.3]. The Entra activity timestamp moves in steps of
about 14 days, so a staleness rule on it needs at least 21 days [ms G17].

## 1.5 Judging each platform fairly

The predicate per platform, used by the checks in [04](04-checks-and-control-mapping.md). A platform the
source cannot answer for gives `insufficient` for that device with the reason, never `pass`.

| Check | macOS | Windows | iOS, iPadOS | Android | ChromeOS | Linux |
|---|---|---|---|---|---|---|
| Encrypted | FileVault on and fully encrypted (not encrypting or paused) [apple-mdms 4.7 item 4]; hardware volume keys without FileVault do not count [apple G6] | BitLocker on for the OS volume, protection not suspended | hardware encryption capability plus a passcode present | `encryptionStatus` active with a user credential; "default key" fails | managed and not in developer mode: pass with the reason "encrypted by design" | LUKS on the root volume where the agent reports it |
| Key escrowed | the vendor's escrow record (never the "has key" flag) | BitLocker recovery key metadata for the OS volume | n/a | n/a | n/a | LUKS escrow where the source reports it (Fleet Premium) |
| Locked | a policy (passcode payload, DDM passcode configuration, or screen saver payload) installed and active with idle at or under the limit and a password required | inactivity lock policy evaluated compliant at or under the limit | passcode present, policy assigned, auto lock at or under the mobile limit | screen lock required, `maximumTimeToLock` set and at or under the mobile limit | screen lock delay policy at or under the limit | where the agent reports it, else `insufficient` |
| OS current | at or above the minimum, the major still receiving Apple security releases, the supplemental (Background Security Improvement) version read [apple G18, G19] | supported build at or above the minimum; end of support from Defender where connected | same as macOS, with the model in the release's supported list | complete patch level within `android_patch_max_age_days`, Android version still in the latest bulletin, model in its vendor support window when known [google 2.3] | before `autoUpdateThrough`, at or above the minimum | supported distribution release |
| Firewall | on (stealth and block all recorded) | on for every profile, read from the compliance setting state | n/a | n/a | via Endpoint Verification | on (UFW, firewalld) where reported |
| Wipe possible | any channel except User Enrolment; record the method (erase all content or obliteration) [apple G25] | wipe available | any channel except User Enrolment | factory reset on fully managed; work profile removal on personal | wipe or powerwash | `not_applicable` |

Mobile thresholds differ from computers: CIS 4.3 sets at most 15 minutes for computers and 2 minutes for
phones and tablets [market 6.3]. Verity proposes a separate `max_idle_lock_minutes_mobile` default of 2
(D-MDM-9). EP-06.A's parameter stays 15 for computers.

## 1.6 Personal devices and phones: what Verity evidences instead

| Situation | Device evidence | Access rule evidence (stronger here) |
|---|---|---|
| Personal phone with company mail | none needed beyond the channel's flags | the identity provider or app protection limits mail and files to compliant or managed apps (NEED identity_provider; Intune `managedAppRegistrations` [ms 3]) |
| Personal phone on User Enrolment or a work profile | passcode present and compliant, OS current, managed apps; no serial, no full wipe | the same access rule |
| Contractor laptop, not managed | none, unless an agent (Device Trust, Endpoint Verification) is installed | access only through VDI or app protection, or exclusion with reason, approver and expiry |
| Personal laptop with an agent | encryption, lock, OS, firewall from the agent | sign in rules requiring a known or compliant device |

The per tenant setting `personal_devices` (D-DEV-7) decides whether personal devices are in the device
population. Default: in scope when they reach company data, with the privacy rules of
[02](02-what-verity-collects.md) 2.5 always applied.
