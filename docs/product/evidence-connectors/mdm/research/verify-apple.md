# Verification log: Apple platforms and Apple focused MDMs (round 2)

Adversarial check of two round 2 research files written on 2026-11-26:
[apple-platforms.md](apple-platforms.md) (AP) and [apple-mdms.md](apple-mdms.md) (AM). Brief: [BRIEF.md](BRIEF.md).
Every source below was fetched by the checker in this session on 2026-11-26. Nothing in the two research files
was edited.

## 1. Scope

| Item | Covered |
|---|---|
| Claims checked | 79 load bearing claims: every row of both "Corrections to round 1" tables (AP section 7, 10 rows; AM section 11, 13 rows), every gotcha (AP G1 to G27; AM 4.7 items 1 to 10; AM 5.5 items 1 to 5), plus the named Apple Business, Jamf, Iru, Addigy and SimpleMDM claims |
| Apple sources | Apple's schema repository `apple/device-management`, `release` branch (README says it matches iOS, macOS, tvOS, visionOS and watchOS 27.2), read as raw YAML; developer.apple.com pages read through Apple's documentation JSON (same content as the rendered page); support.apple.com deployment, security and Apple Business guides |
| Vendor sources | developer.jamf.com reference and changelog pages (Jamf Pro API spec 11.34.0) and Platform API pages; Jamf Pro Documentation 11.34.0 topic "Remote Commands for Computers" (the AM file cites the 11.30.0 copy; the current copy was read); Jamf support FAQ; Iru OpenAPI file 1.0.0, Iru API overview and brand update pages; Addigy Swagger 2.0 file; SimpleMDM API v1 page |
| Method | Each claim was tested against the cited page. A claim that sounds right but is not on the page is marked unverified or corrected |
| Not checked | Mosyle rows (the AM file already marks them U or T); AP section 2 matrix cells other than those a gotcha or correction relies on; vendor field rows not tied to a correction or gotcha |

Verdicts: **confirmed** (the source says it), **corrected** (the source says something different or narrower),
**unverified** (the source does not say it either way).

## 2. Corrections (claims that were wrong or overstated)

| # | File and section | Claim as written | What the source supports | Effect on Verity |
|---|---|---|---|---|
| X1 | AP 3.7, G5, section 7 row 8 | an escrow payload installed after FileVault was already on is silently skipped, with no warning | Apple's escrow payload text says the key is wrapped and stored only if FileVault is turned on after the payload is installed. The "no warning or error when FileVault is already on" note is about the old `FDERecoveryRedirect` payload, not the current escrow payload. For an already encrypted Mac the documented route to an escrowed key is `RotateFileVaultKey` with a reply certificate, which returns the new key in the command result (`RotateResult`), not in SecurityInfo | `devices.recovery_key_escrowed` rule stands (read the vendor's escrow flag, never "has key"). Change the reason text and the remediation hint: a Mac encrypted before the escrow payload needs a key rotation to become escrowed. Do not cite "silently skipped" |
| X2 | AP G3 | second signal for a confirmed wipe can be Apple Business `deviceEraseStatus` | `deviceEraseStatus` is an attribute of `GET /v1/mdmDevices/{id}/details`, which covers only devices enrolled in Apple Business built in management; Apple publishes no meaning for its two values. Apple's erase page also says the `Default` fallback can reply `Error` or send no status at all | `devices.wipes_confirmed`: list `deviceEraseStatus` only for the Apple Business built in management connector, not for Jamf, Iru, Addigy or SimpleMDM. Treat a missing erase reply as "not confirmed", never as "failed" |
| X3 | AP G26 | the bypass code window of 15 days means leaver recovery can fail on user linked locks | Apple's Activation Lock page states the 15 day window for iPhone and iPad. The same page says an Apple Business user whose role can manage devices can turn off both organisation linked and user linked Activation Lock on devices the organisation owns, if the device was added to Apple Business before the lock and has not been released | Proposed `devices.activation_lock_org_controlled` and `devices.leaver_devices_recovered`: a USER lock on a device held in Apple Business is recoverable by the customer, so it is a finding to act on, not proof that recovery is impossible. A USER lock on a device not in Apple Business stays the hard case |
| X4 | AM 2 (erase row) | the device answers once and does not retry a failed erase | Apple's schema says the device sends its reply once and does not resend it if delivery fails. It says nothing about retrying the erase itself | none on checks (both readings already require a second signal); fix the wording |
| X5 | AM 4.7 item 6 | Jamf `passcodeCompliant` reads true without a policy (Apple [36]) | Apple states "true when no passcode policy exists" only for the DDM status item `passcode.is-compliant`. Jamf's mobile SECURITY fields (`passcodePresent`, `passcodeCompliant`, `passcodeCompliantWithProfile`) mirror the SecurityInfo keys, whose Apple description says nothing about the no policy case | keep the rule "compliance counts only with an assigned policy" as a Verity precaution, but cite it as Verity's rule, and add a fixture test (device with no passcode profile) before claiming Jamf behaves like DDM |
| X6 | AM 7.1 | read operations carry `x-mcp-readonly: true`, a usable allow list | In the Swagger file the marker is on 77 operations: 76 POST query routes and 1 GET. The other 126 GET routes, including the permissions route, the facts list, the per device compliance status and the MDM device detail, carry no marker. The marker is never set to false | build the Addigy collector allow list by hand (named GET routes plus marked POST query routes); do not derive it from the marker |

Additions found while checking (the files did not state these; each affects a credential step or a privacy rule):

| # | File and section | Addition | Source |
|---|---|---|---|
| A1 | AM 5.1 | The Iru OpenAPI file lists two server hosts: `{subdomain}.api.kandji.io` (US) and `{subdomain}.api.eu.kandji.io` (EU). The connect form must accept the EU host as well as `api.iru.com` | Iru OpenAPI `servers` |
| A2 | AM 8 | SimpleMDM device reads also take `include_secret_custom_attributes` (default false), which returns custom attributes marked secret. Verity must never set it | SimpleMDM API v1 |
| A3 | AP 4.2 | Apple's own abstract for `GET /v1/orgDevices` describes it as the devices that enrol through Automated Device Enrollment. The "every device added" reading in AP 4.2 is close but the population is the ADE eligible set | Apple Business API, Get Organization Devices |
| A4 | AP G9 | Apple marks the passcode payload deprecated in 27 but does not name the DDM passcode configuration as its replacement. "Successor" is a sound reading, not an Apple statement | schema CHANGES and passcode payload YAML |

## 3. Full claims table

Source keys used in the URL column are defined in section 4.

### 3.1 apple-platforms.md, section 7 corrections

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V01 | Mac erase prerequisites; missing ones fall back to obliteration | AP 7 r1 | confirmed | Apple silicon needs a bootstrap token; Apple silicon and T2 need first partition start, a signed system volume and no external boot; T2 needs Full Security and no firmware password; otherwise the Mac obliterates and needs macOS reinstalled | S-erase |
| V02 | Erase reply does not settle the outcome; Default can reply Error and erase; DoNotObliterate can acknowledge and not erase | AP 7 r2 | confirmed | preflight decides the reply; Default replies Error then erases; DoNotObliterate does nothing if EACS fails after a passing preflight. Support page adds Default may send no status | Y-erase, S-erase |
| V03 | `EraseDevice` needs no supervision; only user enrolment forbids it | AP 7 r3 | confirmed | `supervised: false` on all five OSes; user enrolment forbidden on iOS, macOS, visionOS. Lost Mode is `supervised: true` | Y-erase, Y-lost |
| V04 | screen lock comes from passcode payload, DDM passcode settings and screen saver payload | AP 7 r4 | confirmed | `maxInactivity` (macOS converts to screen saver settings, max 60), `MaximumInactivityInMinutes`, `idleTime` all exist | Y-pass, Y-ddmpass, Y-ss |
| V05 | OS 27 removed `AvailableOSUpdates` and `OSUpdateStatus`; pending data only from DDM (macOS supervised; iOS supervised or device) | AP 7 r5 | confirmed | both deprecated 26, removed 27; `softwareupdate.pending-version` allows macOS supervised only, iOS supervised and device | Y-changes, Y-upd, D-removed |
| V06 | `IsActivationLockEnabled` deprecated iOS 16, macOS 13 | AP 7 r6 | confirmed | deprecated iOS 16, macOS 13 (and watchOS 10) | Y-dev, D-qr |
| V07 | data protection needs `HardwareEncryptionCaps` 3 and a passcode | AP 7 r7 | confirmed | Apple states both conditions are required | Y-sec |
| V08 | escrow payload after FileVault on is silently skipped | AP 7 r8 | corrected | see X1 | Y-escrow, Y-rotate |
| V09 | top level IMEI and MEID removed in iOS 26; `ServiceSubscriptions` iOS 12; Apple Business `imei`, `meid` | AP 7 r9 | confirmed | query and response keys deprecated 16, removed 26; `ServiceSubscriptions` iOS 12 needs the network information right; orgDevice has `imei`, `meid` | Y-dev, D-qr, D-orgattr |
| V10 | product renamed Apple Business; API 2.8 on 4 Nov 2026; old path 404 | AP 7 r10 | confirmed | changelog lists 2.8 dated 2026/11/04 with webhooks; old `applebusinessmanagerapi` JSON returned 404; roles page says ABM and ABE organisations move to Apple Business | D-change, D-abapi, S-roles |

### 3.2 apple-platforms.md, gotchas G1 to G27

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V11 | G1: DDM `passcode.is-compliant` true with no policy | AP 6 | confirmed | the item reports true when the device has no passcode policies | Y-st-comp |
| V12 | G2: macOS has no passcode present or compliant keys | AP 6 | confirmed | SecurityInfo passcode keys and both DDM passcode items are n/a on macOS | Y-sec, Y-st-comp |
| V13 | G3: erase reply semantics, plus `deviceEraseStatus` as second signal | AP 6 | corrected | reply semantics confirmed; `deviceEraseStatus` is built in management only (X2) | Y-erase, S-erase, D-mdmdetail |
| V14 | G4: `CheckOut` is single attempt, only if asked | AP 6 | confirmed | sent only when `CheckOutWhenRemoved` is true; the device tries once; Apple suggests a timeout | Y-mdm, D-inactive |
| V15 | G5: "has key" is not escrow; late escrow silently skipped | AP 6 | corrected | first half confirmed; second half is X1 | Y-sec, Y-escrow |
| V16 | G6: Apple silicon encrypts user data with a volume key without FileVault | AP 6 | confirmed | Data Protection on Apple silicon Macs uses a volume key; FileVault on by default from macOS 26.4 | S-dp |
| V17 | G7: iOS encryption inferred; SecurityInfo passcode key withheld on UE | AP 6 | confirmed | `PasscodePresent` forbidden on UE; DDM `passcode.is-present` allows `user` | Y-sec, Y-st-pres |
| V18 | G8: OS 27 removed MDM update commands and update queries | AP 6 | confirmed | four update commands removed; `OSUpdateSettings`, `SoftwareUpdateSettings`, `SoftwareUpdateDeviceID` queries removed | Y-changes |
| V19 | G9: passcode payload deprecated 27; DDM takes the smallest value, max 15 | AP 6 | confirmed | deprecated on iOS, macOS, visionOS, watchOS 27; `combinetype: number-min`, range 0 to 15; successor not named (A4) | Y-pass, Y-ddmpass |
| V20 | G10: `ProfileList` gives types, not settings; encrypted profiles omit payloads | AP 6 | confirmed | payload items carry type, identifier, UUID, names; `PayloadContent` absent when `IsEncrypted` | Y-plist |
| V21 | G11: schema and deployment page disagree on UE `maxInactivity` | AP 6 | confirmed | schema marks it ignored on UE yet says it removes "never"; deployment page says UE devices honour it | Y-pass, S-passpay |
| V22 | G12: top level IMEI and MEID gone in iOS 26 | AP 6 | confirmed | as V09 | Y-dev |
| V23 | G13: `IsActivationLockEnabled` deprecated; Apple Business status is the live source | AP 6 | confirmed | deprecation confirmed; Apple Business returns `isLocked`, `lockType`, and 404 when the org does not hold the serial | Y-dev, D-al |
| V24 | G14: `EnrolledViaDEP` macOS only; `mdm.enrollment-type` from 27 merges ADE and manual supervision | AP 6 | confirmed | `EnrolledViaDEP` n/a on iOS, tvOS, visionOS, watchOS; status item values none, supervised, device, user, from 27.0 | Y-sec, Y-st-enr |
| V25 | G15: both Mac Device Enrollment forms supervise | AP 6 | confirmed | enrolment table: profile based and account driven Device Enrollment both "Yes (Mac)" | S-enrol |
| V26 | G16: purchase list misses retail; release date only on single reads | AP 6 | confirmed | `releasedFromOrgDateTime` supported only on single device queries; sources are APPLE, RESELLER or MANUALLY_ADDED | D-orgattr, D-orgdev |
| V27 | G17: ASSIGNED is not enrolled; assignment does not change a current enrolment | AP 6 | confirmed | Apple Business says assigning a service does not affect a current enrolment | S-dms, D-orgattr |
| V28 | G18: OS version string omits the improvement letter | AP 6 | confirmed | Apple exposes the letter as a separate key and query; it does not say the plain string contains it | Y-dev, S-osq |
| V29 | G19: older majors do not get every fix | AP 6 | confirmed | Apple says not all known issues are fixed in previous versions | S-upd |
| V30 | G20: Lost Mode only supervised iPhone and iPad; Mac uses PIN lock | AP 6 | confirmed | `EnableLostMode` iOS 9.3 supervised; macOS, tvOS, visionOS, watchOS n/a | Y-lost |
| V31 | G21: DDM status per channel on macOS and Shared iPad | AP 6 | confirmed | Apple says each channel reports DDM status separately on macOS and Shared iPad | D-ddmint |
| V32 | G22: app list differs by channel and OS | AP 6 | confirmed | system apps on macOS and 26+; DDM managed apps excluded on UE; costly values omitted from 26 unless requested | Y-apps |
| V33 | G23: error codes may change between releases | AP 6 | confirmed | Apple says not to rely on `ErrorCode` and `ErrorDomain` | D-send |
| V34 | G24: Shared iPad has no passcode policies; idle lock device reported | AP 6 | confirmed | passcode payload forbidden on Shared iPad; DDM passcode settings has no allowed scope there; `AutoLockTime` required on Shared iPad (iOS 17) | Y-pass, Y-ddmpass, Y-sec |
| V35 | G25: missing token or T2 settings still wipe, by obliteration | AP 6 | confirmed | true under the default fallback; with `DoNotObliterate` nothing is erased | S-erase, Y-erase |
| V36 | G26: 15 day bypass window means leaver recovery can fail on user locks | AP 6 | corrected | window is stated for iPhone and iPad; Apple Business can clear user linked locks on owned devices (X3) | S-al |
| V37 | G27: passcode keys are SecurityInfo, not DeviceInformation | AP 6 | confirmed | `PasscodePresent` absent from DeviceInformation; present in SecurityInfo | Y-dev, Y-sec |

### 3.3 apple-platforms.md, Apple Business API

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V38 | read endpoints and fields: orgDevices, assignedServer, activationLockStatus (404 if not held), mdmServers, mdmDevices details, auditEvents with start and end required | AP 4.2 | confirmed | all routes, fields and enums as listed; audit start and end filters marked required; orgDevices abstract scopes to ADE devices (A3) | D-orgdev, D-orgattr, D-al, D-servers, D-mdmdetail, D-audit |
| V39 | Org Admin creates up to 50 API accounts with a role; custom roles up to 15 and granular; permission names for device reads and Activation Lock status | AP 4.2 | confirmed | permission names and limits as stated; webhook, assign, release, migration and Blueprint rights are separate | S-apiacct, S-roles |
| V40 | token flow: ES256 assertion, `kid`, `sub`, fixed `aud`, `exp` within 180 days, `jti`; client credentials POST with `scope=business.api`; 3600 s token; renew on 401 | AP 4.2 | confirmed | as stated. Apple's sample script also sets an `iss` claim equal to the client id, which the table omits | D-oauth |
| V41 | paging: cursor, `limit` max 1000, keep filters identical; 429 with no number | AP 5 | confirmed | max 1000 on orgDevices, mdmServers, server devices, mdmDevices, auditEvents; Apple warns not to change filters mid paging; 429 listed, no number | D-orgdev |

### 3.4 apple-mdms.md, section 11 corrections

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V42 | v4 arrived 11.30.0; v1 deprecated 11.20.0, v2 11.23.0, v3 11.30.0 | AM 11 r1, 4.1 | confirmed | 11.20.0 adds v2 and deprecates v1; 11.23.0 adds v3 and deprecates v2; 11.30.0 adds v4 and deprecates v3. The version ladder in 4.1 matches | J-1120, J-1123, J-1130 |
| V43 | `lastCheckIn` is a new v4 general field; `lastContact` replaced `lastContactTime` | AM 11 r2 | confirmed | rename, removal of `lastReportedIp` and new `lastCheckIn` stated; v4 schema has `lastContact`, `lastCheckIn`, no `lastContactTime` | J-1130, J-v4 |
| V44 | v1 and v2 deprecated; inventory dates `general.reportDate` and `lastInventoryUpdateDate` | AM 11 r3 | confirmed | as V42; both date fields present in v4 and mobile detail schemas | J-v4, J-mob |
| V45 | erase needs neither supervision, ADE nor bootstrap token; UE forbidden | AM 11 r4 | confirmed | as V03; a missing token changes the method (obliteration), not whether the command runs | Y-erase, S-erase |
| V46 | `devices.wipes_confirmed` on Jamf is partial; inventory unchanged after wipe | AM 11 r5 | confirmed | Jamf: wiping does not remove the computer or change its inventory | L-remote |
| V47 | add Read Mobile Device Configuration Profiles; DDM needs Read Computers and Read Mobile Devices | AM 11 r6 | confirmed | Classic mapping lists the mobile profile read privilege; the DDM status route lists both privileges as required | J-classic, J-ddm |
| V48 | mobile fields: `lastContactDate`; `hardwareEncryption` undefined integer; lost mode location in SECURITY; LENIENT mode | AM 11 r7 | confirmed | all present in the 11.34.0 schema; Jamf does not define the integer (its example is 3, which matches Apple's caps value 3, mapping unverified) | J-mob |
| V49 | Platform API tenant path was beta; GA uses `X-Tenant-Id` header | AM 11 r8 | confirmed | Jamf says this changed at GA and production accepts only the header | J-pfund |
| V50 | Iru `activation_lock` example shows only shared device columns | AM 11 r9 | confirmed | the example repeats device information columns (host name, model, OS) | I-oas |
| V51 | Iru token steps: Enable MCP toggle, then Configure or Skip | AM 11 r10 | confirmed | both steps on the overview page; token and MCP block shown once | I-ov |
| V52 | Iru device list has no success example; fields come from Update Device; `user` is a string | AM 11 r11 | confirmed | Get Device and list have empty 200 bodies; Update Device example shows `user` as a string | I-oas |
| V53 | Prism has 16 categories incl. `startup_settings`, `local_users`, `apps`, `cellular` | AM 11 r12 | confirmed | 16 category routes plus export, export by id and count | I-oas |
| V54 | strategy 5.5 lacked Addigy, SimpleMDM, Mosyle columns | AM 11 r13 | confirmed | structural row; the three vendor sources exist and were read | X-swag, SM-api |

### 3.5 apple-mdms.md, Apple rule in section 2

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V55 | the device does not retry a failed erase | AM 2 | corrected | the reply is not resent; erase retry is not mentioned (X4) | Y-erase |

### 3.6 apple-mdms.md, Jamf gotchas 4.7

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V56 | 1: version drift loses the contact field | AM 4.7 | confirmed | rename between v3 and v4 is stated | J-1130 |
| V57 | 2: contact can be fresh while inventory is old | AM 4.7 | confirmed | Mac inventory runs on a customer policy; extra policies refresh the report date; mobile cadence is daily or longer | J-scal |
| V58 | 3: inventory unchanged after wipe | AM 4.7 | confirmed | as V46; Jamf also says a failed preflight runs the chosen fallback, which by default erases | L-remote |
| V59 | 4: `fileVault2Enabled` can be true while ENCRYPTING or paused | AM 4.7 | unverified | the enums ENCRYPTING, ENCRYPTING_PAUSED and the boolean exist; Jamf does not describe how they relate. The pass rule stays (it is stricter) | J-v4 |
| V60 | 5: NOT_COLLECTED and UNKNOWN values exist | AM 4.7 | confirmed | `sipStatus` and `individualRecoveryKeyValidityStatus` enums as listed | J-v4 |
| V61 | 6: Jamf `passcodeCompliant` true without policy | AM 4.7 | corrected | Apple's statement covers only the DDM item (X5) | Y-st-comp, Y-sec |
| V62 | 7: mobile SECURITY carries lost mode location | AM 4.7 | confirmed | `lostModeLocation` sits in the SECURITY schema with coordinates and accuracy | J-mob |
| V63 | 8: STRICT default returns 500; LENIENT returns 200 with null sections | AM 4.7 | confirmed | as stated | J-mob |
| V64 | 9: read installed profiles, not scope | AM 4.7 | confirmed | `configurationProfiles[]` has `profileIdentifier`, `uuid`, `lastInstalled` | J-v4 |
| V65 | 10: Platform integrations expire after six months | AM 4.7, 4.2 | confirmed | Jamf says integrations are valid for six months; tokens last 900 s; 200 requests a second per client | J-pstart, J-pfund |

### 3.7 apple-mdms.md, Iru gotchas 5.5

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V66 | 1: `activation_lock` and `desktop_and_screensaver` examples are copies | AM 5.5 | confirmed | both examples show device information columns only | I-oas |
| V67 | 2: command `status` and ADE `enrollment_status` are unexplained integers | AM 5.5 | confirmed | examples show 3 and 4; no meanings given | I-oas |
| V68 | 3: Iru Compliance shares the hourly budget | AM 5.5 | confirmed | its evidence collection counts toward the same limit | I-ov |
| V69 | 4: `is_missing` is lost contact, not retired | AM 5.5 | unverified | `is_missing` and `is_removed` appear only in examples, with no description | I-oas |
| V70 | 5: lost mode details and Prism `cellular` hold location and phone data | AM 5.5, 5.2 | confirmed | lost mode returns `last_location` latitude and longitude; cellular has `imei_slot_*` and `phone_number_slot_*` | I-oas |

### 3.8 apple-mdms.md, other named vendor claims

| # | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| V71 | Jamf role privileges: Read Computers, Read Mobile Devices, View MDM command information, Read macOS and Mobile Device Configuration Profiles | AM 4.2 | confirmed | each route's required privilege matches; Classic commands and history need Read Computers or Read Mobile Devices | J-v4, J-mob, J-cmd, J-classic |
| V72 | Iru hosts: `api.kandji.io` or `api.iru.com` for migrated tenants; old scripts keep working | AM 5.1 | confirmed | as stated; EU host omitted (A1) | I-brand, I-oas |
| V73 | Iru limit 10,000 requests an hour per customer, all tokens share it | AM 5.4 | confirmed | stated in the OpenAPI introduction and the overview; body says the limit was exceeded | I-oas, I-ov |
| V74 | Iru Prism `filevault.key_escrowed` | AM 5.3 | confirmed | example row has `status`, `key_type`, `key_escrowed`, `regeneration_needed`, `scheduled_key_rotation` | I-oas |
| V75 | Iru routes never to call: secrets, lost mode details, cellular, actions | AM 5.2 | confirmed | `/secrets/filevaultkey`, `bypasscode`, `unlockpin`, `recoverypassword`, `/details/lostmode`, `/action/*` all exist | I-oas |
| V76 | Addigy `GET /configuration/permissions` lists the key's permission identifiers | AM 7.1 | confirmed | returns strings such as `com.addigy.devices.view` | X-swag |
| V77 | Addigy auth is `x-api-key` header | AM 7.1 | confirmed | the only security definition is an API key named `x-api-key` in the header | X-swag |
| V78 | Addigy reads carry `x-mcp-readonly: true` | AM 7.1 | corrected | marker on 77 operations, only one GET (X6) | X-swag |
| V79 | SimpleMDM `show_secrets` false for new keys, true for existing keys | AM 8 | confirmed | needs the Device Secrets permission; returns FileVault key, firmware and recovery lock passwords, bypass codes, admin passwords and PINs | SM-api |

## 4. Sources

All fetched 2026-11-26.

| Key | URL |
|---|---|
| Y-changes | https://github.com/apple/device-management/blob/release/CHANGES.md |
| Y-erase | https://github.com/apple/device-management/blob/release/mdm/commands/device.erase.yaml |
| Y-dev | https://github.com/apple/device-management/blob/release/mdm/commands/information.device.yaml |
| Y-sec | https://github.com/apple/device-management/blob/release/mdm/commands/information.security.yaml |
| Y-pass | https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.mobiledevice.passwordpolicy.yaml |
| Y-ddmpass | https://github.com/apple/device-management/blob/release/declarative/declarations/configurations/passcode.settings.yaml |
| Y-escrow | https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.security.FDERecoveryKeyEscrow.yaml |
| Y-rotate | https://github.com/apple/device-management/blob/release/mdm/commands/rotate.file.vault.key.yaml |
| Y-upd | https://github.com/apple/device-management/blob/release/declarative/status/softwareupdate.pending-version.yaml and .../mdm/commands/system.update.available.yaml |
| Y-st-comp | https://github.com/apple/device-management/blob/release/declarative/status/passcode.is-compliant.yaml |
| Y-st-pres | https://github.com/apple/device-management/blob/release/declarative/status/passcode.is-present.yaml |
| Y-st-enr | https://github.com/apple/device-management/blob/release/declarative/status/mdm.enrollment-type.yaml |
| Y-plist | https://github.com/apple/device-management/blob/release/mdm/commands/profile.list.yaml |
| Y-apps | https://github.com/apple/device-management/blob/release/mdm/commands/application.installed.list.yaml |
| Y-lost | https://github.com/apple/device-management/blob/release/mdm/commands/device.lostmode.enable.yaml |
| Y-mdm | https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.mdm.yaml |
| Y-ss | https://github.com/apple/device-management/blob/release/mdm/profiles/com.apple.screensaver.yaml |
| D-removed | https://developer.apple.com/documentation/devicemanagement/removed-commands-and-profiles |
| D-qr | https://developer.apple.com/documentation/devicemanagement/deviceinformationresponse/queryresponses-data.dictionary |
| D-inactive | https://developer.apple.com/documentation/devicemanagement/dealing-with-inactive-managed-devices-and-invalid-push-tokens |
| D-send | https://developer.apple.com/documentation/devicemanagement/sending-mdm-commands-to-a-device |
| D-ddmint | https://developer.apple.com/documentation/devicemanagement/integrating-declarative-management |
| D-abapi | https://developer.apple.com/documentation/applebusinessapi (old path `.../applebusinessmanagerapi` returned 404) |
| D-orgdev | https://developer.apple.com/documentation/applebusinessapi/get-org-devices |
| D-orgattr | https://developer.apple.com/documentation/applebusinessapi/orgdevice/attributes-data.dictionary |
| D-al | https://developer.apple.com/documentation/applebusinessapi/get-the-activation-lock-status-information-for-an-orgdevice and .../activationlocktype |
| D-servers | https://developer.apple.com/documentation/applebusinessapi/get-mdm-servers and .../mdmserver/attributes-data.dictionary |
| D-mdmdetail | https://developer.apple.com/documentation/applebusinessapi/get-apple-mdm-enrolled-devices, .../mdmdevicedetail/attributes-data.dictionary, .../deviceerasestatus |
| D-audit | https://developer.apple.com/documentation/applebusinessapi/get-audit-events |
| D-oauth | https://developer.apple.com/documentation/apple-school-and-business-manager-api/implementing-oauth-for-the-apple-school-manager-and-apple-business-api |
| D-change | https://developer.apple.com/documentation/apple-school-and-business-manager-api/apple-school-manager-and-apple-business-api-changelog |
| S-erase | https://support.apple.com/guide/deployment/erase-devices-dep0a819891e/web |
| S-al | https://support.apple.com/guide/deployment/activation-lock-depf4ab94ef1/web |
| S-enrol | https://support.apple.com/guide/deployment/enrollment-methods-for-apple-devices-dep08f54fcf6/web (published 28 January 2025) |
| S-passpay | https://support.apple.com/guide/deployment/passcode-payload-settings-dep4d6a472a/web |
| S-upd | https://support.apple.com/guide/deployment/about-software-updates-depc4c80847a/web |
| S-osq | https://support.apple.com/guide/deployment/operating-system-queries-dep8b8b23369/web |
| S-dp | https://support.apple.com/guide/security/data-protection-overview-secf6276da8a/web |
| S-dms | https://support.apple.com/guide/business/intro-to-device-management-services-axm659f6bd48/web |
| S-apiacct | https://support.apple.com/guide/business/create-an-apple-business-api-account-axm33189f66a/web |
| S-roles | https://support.apple.com/guide/business/intro-to-roles-and-permissions-axm97dd59159/web |
| J-1120, J-1123, J-1130 | https://developer.jamf.com/jamf-pro/changelog/11200-deprecations (and 11200-additions), .../11230-deprecations (and 11230-additions), .../11300-additions and .../11300-deprecations |
| J-v4 | https://developer.jamf.com/jamf-pro/reference/get_v4-computers-inventory-id |
| J-mob | https://developer.jamf.com/jamf-pro/reference/get_v2-mobile-devices-detail |
| J-cmd | https://developer.jamf.com/jamf-pro/reference/get_v2-mdm-commands |
| J-ddm | https://developer.jamf.com/jamf-pro/reference/get_v1-ddm-clientmanagementid-status-items |
| J-classic | https://developer.jamf.com/jamf-pro/docs/classic-api-minimum-required-privileges-and-endpoint-mapping |
| J-scal | https://developer.jamf.com/jamf-pro/docs/jamf-pro-api-scalability-best-practices |
| J-pstart | https://developer.jamf.com/platform-api/reference/getting-started-with-platform-api.md |
| J-pfund | https://developer.jamf.com/platform-api/reference/platform-api-fundamentals.md |
| L-remote | https://learn.jamf.com/r/en-US/jamf-pro-documentation-current/Remote_Commands_for_Computers (Jamf Pro Documentation 11.34.0) |
| I-oas | https://docs.iru.com/openapi/iru-endpoint-openapi.json |
| I-ov | https://docs.iru.com/en/endpoint/api/iru-api-overview |
| I-brand | https://docs.iru.com/en/iru/platform-overview/iru-brand-update |
| X-swag | https://api.addigy.com/api/v2/documentation/godoc_swagger.json |
| SM-api | https://api.simplemdm.com/v1 |

## 5. Totals

| Verdict | Count | Claims |
|---|---|---|
| confirmed | 70 | all others |
| corrected | 7 | V08, V13, V15, V36, V55, V61, V78 (six distinct findings, X1 to X6; V08 and V15 are the same finding) |
| unverified | 2 | V59, V69 |
| total | 79 | |

Corrections that change a check or a credential step: X1 (`devices.recovery_key_escrowed` remediation and reason text),
X2 (`devices.wipes_confirmed` signal list), X3 (proposed Activation Lock and leaver checks), X6 (Addigy collector
allow list), plus additions A1 (Iru EU host in the connect step) and A2 (SimpleMDM secret custom attributes stay off).
X4 and X5 change wording and test fixtures only.
