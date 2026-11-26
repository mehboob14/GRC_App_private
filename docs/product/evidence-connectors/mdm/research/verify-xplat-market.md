# Verification log: cross platform MDMs and market research (MDM round 2)

Adversarial check of three round 2 files written on 2026-11-26:

- [cross-platform-mdms-a.md](cross-platform-mdms-a.md) (Workspace ONE, JumpCloud, Hexnode, ManageEngine), ids `WS`, `JC`, `HX`, `ME`
- [cross-platform-mdms-b.md](cross-platform-mdms-b.md) (Fleet, NinjaOne, Rippling, Device Trust), ids `FL`, `NJ`, `RP`, `DT`
- [market-and-audit.md](market-and-audit.md) (competitors, audit practice, privacy), ids `MK`

## 1. Scope and method

- Date of every read: 2026-11-26.
- Target: load bearing claims only, meaning a claim that changes a Verity check, a permission, a credential step, the
  connector order or a privacy rule. Every gotcha and every "Corrections to round 1" row in the three files was
  included, plus the items named in the request.
- Method: each cited primary source was fetched again in this session. Machine readable specs were downloaded and
  searched field by field: Workspace ONE MDM v1 (2607) JSON, JumpCloud v1 and Directory Insights YAML, Fleet
  `rest-api.md`, licences, `handler.go`, `go.mod`, pricing YAML and policy library, NinjaOne v2 and authorization
  JSON, Device Trust OpenAPI 2026-04-07, Rippling `llms.txt` and changelog HTML. Help pages were read through a
  fetch tool. Omnissa docs refuse the fetch tool (403) and were read with a plain HTTP client instead.
- Verdicts: **confirmed** (the cited page says it), **corrected** (the page says something different, or the
  claim is wrong in a way that matters), **unverified** (the cited page does not say it, and no other primary
  source read here does). A claim that sounds right but is not on the cited page is not confirmed.
- One row can hold several closely linked atomic claims from the same source. Notes are in my own words.

## 2. Corrections

Claims found wrong or not supported, with the right statement and the effect on Verity.

| # | File and section | Claim as written | What the source says | Effect on Verity |
|---|---|---|---|---|
| X1 | xplat-a A.4 (rows `disk_encryption`, `recovery_key_escrowed`, `passcode_present`, `passcode_compliant`), A.8 | Escrow flags (`HasPersonalRecoveryKey`, `HasInstitutionalRecoveryKey`), `IsPasscodePresent`, `IsPasscodeCompliant` and `IsEncrypted` come from the bulk `GET /api/mdm/devices/securityinfosearch` | The bulk endpoint returns a slim `SecurityInfo` object: `DeviceId`, `CompromisedStatus`, `EncryptionStatus`, `PasscodeStatus`, `PasscodeComplianceStatus` and two grace period numbers. It also marks `organizationgroupid` and `user` as required. The escrow flags, `IsPasscodePresent`, `IsEncrypted`, SIP and Secure Boot fields live only in `DeviceSecurityInfo`, returned per device by `GET /api/mdm/devices/{id}/security`, the same schema that holds `PersonalRecoveryKey`, `StaticRecoveryKey`, `UnlockPin` and the others | `devices.recovery_key_escrowed` on Workspace ONE needs one call per device to the endpoint whose response schema carries key material. Decide: accept that call with a strict struct that never decodes key fields (and test that a Read Only role returns them empty or not), or drop escrow for Workspace ONE. Encryption and passcode can use the bulk status strings, whose value sets are undocumented (fixtures needed). Budget: one call per device per day against the default 50,000 daily quota. Test whether the required `user` parameter blocks a fleet wide bulk read |
| X2 | xplat-a A.5, A.6 | Throttling is a tenant setting and the daily quota covers every integration on the tenant | The page shows throttling (default 5,000 calls a minute) and daily quota (default 50,000) as an organization group setting with inherit or override, plus a usage counter. It does not say the quota is shared by all integrations | Keep the conservative budget, but mark sharing as unverified. Onboarding should read the setting on the organization group the OAuth client is attached to |
| X3 | xplat-b 3.1 `device.action`, 7 `devices.wipes_confirmed` | Fleet wipe evidence from activities `wiped_host` plus commands and device status | `wiped_host` is logged when a user sends the wipe request, not when the device finishes. `failed_wipe` exists only for Windows | `devices.wipes_confirmed` on Fleet must use `mdm.device_status` = `wiped` or the command result, never `wiped_host` alone. A `wiped_host` without a matching completed state is `insufficient` |
| X4 | xplat-a C.6 | Hexnode device details carry `location_history` | The device details sample carries `latitude`, `longitude`, `last_location`, `last_location_time`, `locations`, `location_tracking_*`, and phone fields `user.phoneno`, `device.phoneno_1`, `device.phoneno_2`, `network.phoneno_1`, `network.phoneno_2`, `network.win_phone_no_1`, `network.win_phone_no_2`. No `location_history` key appears there | The privacy drop list for the Hexnode normaliser must name these real keys, and the personal device fixture test must include them |
| X5 | xplat-a C.2 | One Hexnode API key per portal | None of the three cited pages states a count. The help page says the key goes raw in the `Authorization` header; the developer authentication page says HTTP Basic | The read only conclusion still holds (custom roles have API disabled, no scope or read only option documented). Credential text must not promise "one key"; the connector must test both header styles |
| X6 | xplat-a B.1, B.2 fallback | Every JumpCloud admin, including a Read Only admin, can hold an API key once a Billing admin enables API access | The API page says only Billing admins can enable API access and gives the 90 day default and `jca_` prefix. It does not say which roles can hold a key | Make the service account (confirmed for Read Only) the only documented path; keep the Read Only admin key as "unverified, test first" |
| X7 | xplat-b 3.2 | NinjaOne operations all list `monitoring`, `management` and `control` together | The spec sets all three as the global default; 310 of 315 operations inherit it, 5 declare their own (4 `management`, 1 `monitoring`). Separately, NinjaOne's own OAuth page is self contradictory: its intro says only authorization code and implicit grants are supported, while its list includes client credentials. The token schema does accept `client_credentials` | Credential step risk. Onboarding must run a test token request with `client_credentials` and `scope=monitoring` and show a clear error if the tenant's app type rejects it |
| X8 | market 2 item 2, 8, 9 item 6 | Nobody checks phones: every competitor either skips iOS and Android or keeps them as inventory | Confirmed for Vanta (Intune, Jamf, Rippling), Drata (multi device, JumpCloud), Secureframe (checks never apply to mobile) and Scrut (phones go to asset management). Sprinto's Jamf page lists macOS, iOS and iPadOS as supported with OS, encryption and antivirus checks and does not split checks by platform | "Nobody" is not proven. Say "no competitor documents phone checks; Sprinto's Jamf integration may" in buyer material. D-MKT-2 (company owned phones only) is unchanged |
| X9 | market 3 table, JumpCloud row, Vanta cell | Vanta JumpCloud: yes, including Linux [6][14] | Vanta's JumpCloud page names no platforms and no checks; the device monitoring page does not mention Linux for JumpCloud | Cell is unverified. The Linux conclusion (9 item 13) still stands on Drata [23] and Secureframe [40], both confirmed |
| X10 | market 5, device to person, Drata | Drata matches Intune devices by serial plus primary user email or UPN | Drata requires a unique serial but matches the person by the primary user's email or UPN (email by default, UPN as fallback); serial is not a matching key | Wording only |
| X11 | market 6.1, Linford [64] | An unsupported hand made list can be refused in favour of a system generated population | Linford says a manual list may be insufficient and the auditor may ask for another source or format, but a manual list can still be used if it is tested for completeness and accuracy. It never says refuse | Wording only. The IPE metadata plan (9 item 3) is unchanged |
| X12 | market 6.1, Schneider Downs [65] | Provide the query so it can be rerun; cropped screenshots cause rework | The article asks for screenshots of the script or query and that someone else can rerun the report; it lists partial screens as a pitfall, without the word rework | Wording only |
| X13 | market 2 item 5, 7.2 | Apple User Enrolment withholds serial, UDID, IMEI and MEID [87][88] | Current Apple pages confirm serial and UDID only [87]. IMEI and MEID rest on a 2019 WWDC session [88]. The User Enrolment pages [85][86] list no identifiers | Rule P1 is unchanged (Verity drops all four anyway). Cite [87] for serial and UDID and mark IMEI and MEID as 2019 behaviour |

Additions found while checking (not errors in the files, but they bear on a decision):

| # | Finding | Source | Bears on |
|---|---|---|---|
| A1 | Drata's BYOD article suggests a phone screen timeout of one minute or less, next to 15 minutes for workstations | Drata [33] | D-MKT-5 (mobile default): CIS says at most 2 minutes, Drata suggests 1. The 2 minute default stays defensible |
| A2 | JumpCloud Directory Insights also has an EU host, `api.eu.jumpcloud.com`, listed in the spec's servers | JumpCloud DI spec [26] | xplat-a B.2 said the EU host was unverified |
| A3 | Rippling device order endpoints were added on 2026-06-24, a week before device endpoints | Rippling changelog [R6] | none |
| A4 | Fleet's multi tenancy feature is listed under Premium, but its documentation link points to a GitHub issue | Fleet pricing YAML [F7] | xplat-b 8 "Verity hosts Fleet Premium as a partner": shipped status unverified |
| A5 | JumpCloud's role page calls Read Only read only in its summary but grants Edit on Insights in its table | JumpCloud roles [18] | xplat-a B.6 gotcha holds; the page itself is inconsistent |
| A6 | Fleet's policy library also has a CIS tagged macOS policy for lock within 20 minutes (not tagged built in) | Fleet policy library [F14] | xplat-b 6.1: a reviewed SQL pattern for the screen lock report can start from it |

## 3. Claims table

Legend: C confirmed, X corrected, U unverified.

### 3.1 Workspace ONE (cross-platform-mdms-a.md, section A)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| WS-1 | OAuth clients and the token service exist only on SaaS; on premises uses basic, certificate or directory auth; regional token URLs and country mapping as listed | A.1, A.2 | C | The token service and OAuth client creation are stated as SaaS only; uat, na (US, Canada), emea (UK, Germany), apac (India, Japan, Singapore, Australia, Hong Kong) match; the settings page lists basic, certificate and directory | https://docs.omnissa.com/WorkspaceONE-UEM-Console-Basics-VSaaS/UsingUEMFunctionalityWithRESTAPI , https://docs.omnissa.com/SystemSettings-VSaaS/RestAPIforWorkspaceONEUEM |
| WS-2 | Read Only REST permissions exist per collection; `REST API MDM Devices` and `REST API MDM Profiles` are Edit and send lock or unlock | A.2 | C | The permission table marks the Read entries as Read Only and both MDM entries as Edit with lock and unlock commands | same Omnissa REST page |
| WS-3 | Throttling 5,000 calls a minute and daily quota 50,000 by default; over the minute limit new requests get no answer | A.5 | C | Both defaults stated; over the limit the server offloads new calls without responding | Omnissa REST settings page |
| WS-4 | Throttling is a tenant setting; the daily quota is shared by every integration | A.5, A.6 | X | Organization group setting with inherit or override; sharing not stated (see X2) | Omnissa REST settings page |
| WS-5 | `DeviceSecurityInfo` defines `PersonalRecoveryKey`, `StaticRecoveryKey`, `GracePeriodRecoveryKey`, `OldPersonalRecoveryKeyValue`, `UnlockPin`; a BitLocker recovery key path exists | A.6 | C | All five properties are in the schema; `GET /devices/{deviceUuid}/bitlocker/recoveryKey/{recoveryKeyID}` and `/devices/{uuid}/security/recovery-lock-password` exist | https://raw.githubusercontent.com/euc-dev/ws1-uem-apis/main/docs/versions/2607/mdmv1.json |
| WS-6 | Escrow flags, `IsPasscodePresent`, `IsPasscodeCompliant`, `IsEncrypted` read from bulk `securityinfosearch` | A.4, A.8 | X | Bulk endpoint returns slim `SecurityInfo`; the flags are on per device `GET /devices/{id}/security` (see X1) | mdmv1.json |
| WS-7 | Device audit start date at most 30 days back | A.4, A.5 | C | `startdate` must be within 30 days of today on `GET /ogs/{og_id}/devices/audit` | mdmv1.json |
| WS-8 | Ownership filter values C, E, S, Undefined; `pagesize` default 500, `page` 0 based; `lgid` defaults to the caller's group; `/gps` exists | A.4, A.5, A.2, A.6 | C | All stated in the search parameters; `/devices/{id}/gps` present | mdmv1.json |
| WS-9 | Last Seen inactivity indicator defaults to 480 minutes | A.5 | C | 480 minutes (8 hours), editable under Devices & Users advanced settings | https://docs.omnissa.com/WorkspaceONE-UEM-Managing-Devices-VSaaS/DeviceListView |
| WS-10 | Deleting a device sends an enterprise wipe and keeps it on the allowlist; Wipe Protection holds bulk wipes | A.6 | C | All three stated | same Device List View page |
| WS-11 | Firewall Status and Antivirus Status exist only as compliance rules, Windows desktop | A.6, A.8 | C | Both rules read the Windows Action Center; firewall is for OMA-DM managed Windows desktops | https://docs.omnissa.com/WorkspaceONE-UEM-Managing-Devices-VSaaS/CompliancePolicyRulesAndActions |

### 3.2 JumpCloud (cross-platform-mdms-a.md, section B)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| JC-1 | Read Only role: read on Users, Groups, Devices and Commands; Edit on Insights | B.2, B.6 | C | The table grants Read Only on those areas and Edit on Directory and System Insights; the role summary says read only (inconsistent page, see A5) | https://jumpcloud.com/support/admin-portal-roles |
| JC-2 | Service accounts: only Administrator with Billing creates them; Read Only can be assigned; secret life 30 to 365 days; two secrets; email 7 days before expiry; not for MSPs; token URL `admin-oauth.id.jumpcloud.com/oauth2/token`, `scope=api`, about one hour | B.2 | C | All stated; example `expires_in` is 3599 seconds | https://jumpcloud.com/support/service-account-for-apis |
| JC-3 | API key fallback: default expiry 90 days, prefix `jca_`, only Billing admins enable API access | B.2 | C | All three stated | https://jumpcloud.com/support/jumpcloud-apis |
| JC-4 | Any admin, including Read Only, can hold an API key once enabled | B.1, B.2 | U | Not stated on either page (see X6) | jumpcloud-apis, admin-portal-roles |
| JC-5 | System Insights kept 90 days effective 6 April 2026; before that kept until the device was deleted; silent devices lose data | B.5 | C | All stated on the dated notice and the System Insights page | https://jumpcloud.com/?p=145210 , https://jumpcloud.com/support/system-insights |
| JC-6 | System Insights collects hourly; must be enabled for the org and per device | B.1, B.5 | C | One collection every 60 minutes; org toggle plus per device enablement for older devices | System Insights page |
| JC-7 | `GET /api/v2/systems/{id}/fdekey` returns the key; never call it | B.4 | C | The SDK doc says it returns the latest saved FDE key for the system | https://github.com/TheJumpCloud/jcapi-powershell/blob/master/SDKs/PowerShell/JumpCloud.SDK.V2/docs/exports/Get-JcSdkSystemFdeKey.md |
| JC-8 | `fde.keyPresent` has no description, so "key held" is an inference | B.4 | C | Only the parent object is described (FDE active); `keyPresent` is a bare boolean | https://docs.jumpcloud.com/api/1.0/index.yaml |
| JC-9 | Directory Insights is not in the Device Management package | B.1, B.6 | C | Pricing table marks MDM and System Insights but not Directory Insights for Device Management; the page flattens columns, so the mapping follows mark order | https://jumpcloud.com/pricing |
| JC-10 | Erase event confirms receipt only (`mdm_command_result`, `EraseDevice`); user enrolled iOS cannot be erased; lock state not visible after the command | B.6 | C | All stated across the two pages | https://jumpcloud.com/support/understand-the-erase-device-mdm-command , https://jumpcloud.com/support/mdm-commands |
| JC-11 | v1 built in erase is for Linux and Windows only; Macs use Apple MDM commands | B.6 | C | Stated on `/systems/{system_id}/command/builtin/erase` | JumpCloud v1 spec |
| JC-12 | Directory Insights keeps events 90 days; `limit` up to 10,000; paging with `X-Search_after` | B.5 | C | All stated; spec also lists `api.eu.jumpcloud.com` (see A2) | https://docs.jumpcloud.com/new/api/insights/directory/index.yaml |
| JC-13 | macOS Tahoe 26 ignores lock screen policy settings except Timeout and Ask for Password Delay | B.6 | C | Only those two remain; Ask for Password, screen saver path and name are unsupported on Tahoe 26 | https://jumpcloud.com/support/create-a-mac-lock-screen-policy |
| JC-14 | v1 `limit` default 10, maximum 100 | B.5 | C | Shared `limit` trait: default 10, limited to 100 | JumpCloud v1 spec |
| JC-15 | `networkInfo.simInfo.phoneNumber` on the system object; `systemInsights.state` enabled, disabled, deferred; `mdm.enrollmentType` values | B.4, B.6 | C | All present; IMEI, MEID, MAC, phone number, ICCID and carrier are each marked PII | JumpCloud v1 spec |

### 3.3 Hexnode (cross-platform-mdms-a.md, section C)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| HX-1 | Custom technician roles have API access fully disabled; custom roles need Ultimate or Ultra | C.1, C.2 | C | Both stated in the Admin tab restrictions and plan note | https://www.hexnode.com/mobile-device-management/help/configuring-custom-technician-roles-using-hexnode-mdm/ |
| HX-2 | Read Only Technician exists for the console only | C.2 | C | Described as view only console access; no API mention | https://www.hexnode.com/mobile-device-management/help/configuring-technicians-and-roles-in-hexnode/ |
| HX-3 | One API key per portal | 0, C.2 | U | No page states a count (see X5) | help: does-hexnode-have-apis; developers: authentication, retrieve-api-key |
| HX-4 | No read only API credential; the same API reaches lock, wipe, delete and disenroll | 0, C.2, C.6 | C | No scope or read only option documented; the developer site has Lock, Wipe, Delete and Disenroll actions beside the device reads | https://www.hexnode.com/mobile-device-management/developers/devices/ , https://www.hexnode.com/mobile-device-management/help/does-hexnode-have-apis/ |
| HX-5 | Key from Admin > API (view, revoke, reset), sent raw in `Authorization`; `/api-token-auth/` returns it from an admin username and password | C.2 | C | All stated; the authentication page instead describes HTTP Basic (see X5) | does-hexnode-have-apis; https://www.hexnode.com/mobile-device-management/developers/setting-up-an-api/retrieve-api-key/ |
| HX-6 | Documented API returns no encryption, passcode or firewall fields | 0, C.4 | C | The device details sample has none; `device.storage` is null | https://www.hexnode.com/mobile-device-management/developers/devices/retrieve-device-details/ |
| HX-7 | Location (`location_history`) and phone numbers arrive in device details | C.6 | X | Location and phone fields are there but under other names (see X4) | retrieve-device-details |
| HX-8 | `per_page` default 100, maximum 250; list uses `last_reported`, details `lastreported` | C.5, C.6 | C | Both stated or shown in samples | https://www.hexnode.com/mobile-device-management/developers/devices/list-all-devices/ |

### 3.4 ManageEngine (cross-platform-mdms-a.md, section D)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| ME-1 | READ scopes per module: `Common.READ`, `PatchMgmt.READ`, `DataEncryption.READ`, MDM `MDMInventory.READ` | 0, D.2 | C | Each endpoint page names its scope; MDM scope families listed per module with READ variants | https://www.manageengine.com/products/desktop-central/help/api/cloud/computers-getcomputers.html , .../system-report-get-system-health-report.html , https://www.manageengine.com/mobile-device-management/api/oauth/ |
| ME-2 | `DataEncryption.READ` returns BitLocker recovery keys | D.6 | C | `GET /api/1.4/bitlocker/recoverykeydetails` under that scope returns a `recovery_key` value | https://www.manageengine.com/products/desktop-central/help/api/cloud/recovery-key-details-report.html |
| ME-3 | `MDMInventory.READ` returns Mac firmware passwords and locations | D.6 | C | `/firmware/password` returns `firmware_password`; several location endpoints return latitude and longitude | https://www.manageengine.com/mobile-device-management/api/devices/ |
| ME-4 | Rate limits 120 a minute (systemHealth 50), 5 minute lock, HTTP 429 | D.5, D.6 | C | Get Computers: 120 a minute with a 5 minute wait period; systemHealth: 50 a minute, 429 with lockout. Get Computers does not state the status code | Get Computers and System Health pages |
| ME-5 | Zoho: 10 access tokens per refresh token per 10 minutes; access token 1 hour; refresh token no expiry; Self Client code 3 minutes | D.2, D.5 | C | All stated; MDM grant codes default to 2 minutes | MDM OAuth page; https://www.manageengine.com/products/desktop-central/api/cloud_index.html |
| ME-6 | Guest role reads Inventory, Patch, Configurations, MDM, Reports; BitLocker and Device Control unstated; on premises key has per module Read toggles, never expires by default, shown once | D.2 | C | All stated | https://www.manageengine.com/products/desktop-central/help/access-management/user_role_and_permission.html , https://www.manageengine.com/products/desktop-central/api-key-generation.html |
| ME-7 | Agent refresh every 90 minutes; MDM `security.passcode_complaint` spelling; `owned_by` 1 corporate, 2 personal; FileVault flags; command history filters | D.4, D.5 | C | All stated | agent communication guide; MDM devices API |

### 3.5 Fleet (cross-platform-mdms-b.md)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| FL-1 | Observer can read disk encryption keys, Recovery Lock passwords and managed account passwords | 4.1, 6.1 | C | All three endpoints list Observer and Observer+ among allowed roles | https://raw.githubusercontent.com/fleetdm/fleet/main/docs/API/rest-api.md |
| FL-2 | Premium `api_endpoints` allowlist for API only users; it never adds rights beyond the role | 4.1 | C | Marked Premium; stated that the list cannot grant what the role forbids | rest-api.md |
| FL-3 | Managed cloud only for 700 or more hosts (Premium); self hosting Free; Premium $7 a host a month | 4.1, 8, 10 | C | Pricing YAML and pricing page | https://raw.githubusercontent.com/fleetdm/fleet/main/handbook/company/pricing-features-table.yml , https://fleetdm.com/pricing |
| FL-4 | Licence: MIT outside `ee/`; `docs/` CC BY-SA 4.0; EE code only in production with a subscription, free to copy for development and testing | 8, 10 | C | Root LICENSE and `ee/LICENSE` say this; client side JavaScript is also MIT | https://raw.githubusercontent.com/fleetdm/fleet/main/LICENSE , https://raw.githubusercontent.com/fleetdm/fleet/main/ee/LICENSE |
| FL-5 | `server/service/handler.go` imports `ee/server/service/scep`; module needs Go 1.27.4, about 400 lines; latest release v4.96.0 on 2026-11-24 | 9, 1 | C | Import present; `go 1.27.4`, 413 lines; release published 2026-11-24 | handler.go, go.mod, GitHub releases API |
| FL-6 | API only tokens do not expire | 4.1 | C | Expiry is not enforced for API only users even though a date is returned | rest-api.md |
| FL-7 | `disk_encryption_enabled` omitted when unknown and for Linux hosts reporting unencrypted root | 6.1 | C | Stated in each host note | rest-api.md |
| FL-8 | Built in screen lock policies: macOS checks only that a password is required; Windows allows up to 1,800 seconds | 6.1 | C | macOS SQL tests `askForPassword` = 1 only; Windows SQL tests `InactivityTimeoutSecs` at most 1800 (see A6) | https://raw.githubusercontent.com/fleetdm/fleet/main/docs/01-Using-Fleet/standard-query-library/standard-query-library.yml |
| FL-9 | Moving a host to a fleet with disk encryption off deletes its key; Linux LUKS2 on four distros; escrow is Premium | 6.1, 2.1 | C | Ubuntu, Kubuntu, Fedora and Omarchy listed; key deleted on move; section marked Premium | https://fleetdm.com/guides/enforce-disk-encryption |
| FL-10 | `failed_wipe` exists only for Windows | 6.1 | C | Generated when a Windows host reports a failed wipe | https://fleetdm.com/docs/api/global-audit-logs |
| FL-11 | `wiped_host` activity is wipe evidence | 3.1, 7 | X | Logged when a user sends the request (see X3) | global audit logs |
| FL-12 | `preserve_host_activities_on_reenrollment` defaults to false on new servers; `is_personal_enrollment` sticky after mobile unenrolment; `mia` means unseen over 30 days | 6.1, 3.1 | C | All stated; upgraded servers get true, and the sticky flag resets on macOS and Windows | rest-api.md |
| FL-13 | Observer sees profile names and status only; profile contents need Technician or above | 3.1 | C | Profile list and download list Admin, Maintainer, GitOps, Technician only | rest-api.md |
| FL-14 | Command retention: Apple wipe and lock kept; other Apple 24 hours or 30 days; Windows 30 days | 5 | C | Stated as defaults | https://fleetdm.com/guides/mdm-commands |
| FL-15 | Fleet lists Premium multi tenancy for service providers | 8 | C | Listed under Premium; its documentation link is a GitHub issue (see A4) | pricing YAML |

### 3.6 NinjaOne (cross-platform-mdms-b.md)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| NJ-1 | Monitoring scope is read only; only system administrators configure OAuth; menu Administration > Apps > API | 4.2 | C | All stated | https://www.ninjaone.com/docs/application-programming-interface-api/oauth-token-configuration/ |
| NJ-2 | Spec states no per operation scope; all operations list the three scopes together | 3.2 | X | Global default lists all three; 5 operations override (see X7). Spec is OpenAPI 3.0.1, version 2.0.9-draft, 254 paths, as stated | https://app.ninjarmm.com/apidocs/NinjaRMM-API-v2.json |
| NJ-3 | Encryption only for Windows BitLocker volumes; macOS only FileVault on and off activity codes; no macOS or Linux state | 3.2, 6.2 | C | `bitLockerStatus` on volumes; `FILEVAULT_ENABLED` and `FILEVAULT_DISABLED` codes; only other field is `selfEncrypted` on physical disks. Secureframe says the same | NinjaOne v2 spec; https://support.secureframe.com/en/articles/15111587-ninjaone |
| NJ-4 | Mobile ownership, supervised, passcode and encryption are console only; MDM network carries `phoneNumber` and `iccId` | 3.2, 6.2 | C | Console page lists them per enrolment type; spec MDM schemas lack them and have the phone fields | https://www.ninjaone.com/docs/mdm/mdm-data-details-enrollment-type/ , v2 spec |
| NJ-5 | Client credentials grant at `/ws/oauth/token`; regions app, us2, eu, ca, oc | 4.2 | C | Token schema enum includes `client_credentials`; Secureframe lists the five regions and machine to machine app type. NinjaOne's own page is self contradictory (see X7) | https://app.ninjarmm.com/apidocs/authorization.json , Secureframe NinjaOne page |

### 3.7 Rippling (cross-platform-mdms-b.md)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| RP-1 | Device endpoints added 2026-07-01; `SOLD` added 2026-11-05 as a breaking change; `limit` documented 2026-08-25 | 1, 3.3, 6.3, 10 | C | All three dates match; device orders came on 2026-06-24 (see A3) | https://developer.rippling.com/documentation/rest-api/essentials/changelog |
| RP-2 | Scope `devices.read`; platforms only MACOS, WINDOWS, IOS, IPADOS; enums for enrolment, lifecycle, MDM provider; `is_encrypted`; agent and MDM sync times; `worker_id`; `pending_actions`; no hostname, ownership or build | 2.3, 3.3 | C | All match the reference | https://developer.rippling.com/documentation/rest-api/reference/list-devices |
| RP-3 | 600 requests per 10 seconds per token per path; `limit` 1 to 100, default 50; expand depth 2; filter 64 nodes | 5 | C | All stated | https://developer.rippling.com/documentation/rest-api/essentials/api-limits |
| RP-4 | Token sees the intersection of owner profile and scopes; revoked after 30 days unused or when the owner leaves; shown once; some APIs need an entitlement; creation notifies owner and admins | 4.3, 6.3 | C | All stated | https://developer.rippling.com/documentation/rest-api/essentials/api-tokens |
| RP-5 | A null can mean redacted; check `__meta.redacted_fields` | 4.3, 6.3 | C | Stated in the agent rules | https://developer.rippling.com/llms.txt |

### 3.8 1Password Device Trust (cross-platform-mdms-b.md)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| DT-1 | Keys are read only by default; write is a premium feature missing on some legacy plans; only Full Access admins create keys; `k2sk_v1_` format; per_page 1 to 100, default 25 | 3.4, 4.4, 5 | C | All stated | https://support.1password.com/device-trust-api/ |
| DT-2 | 270 requests a minute; the sample 429 shows a limit of 15 | 5 | C | Both stated; the conflict is on the page | Device Trust API page |
| DT-3 | Header `X-Kolide-Api-Version: 2026-04-07` | 3.4, 9 | C | Header is optional and defaults to latest; current version 2026-04-07. The OpenAPI file itself does not declare the header | Device Trust API page; https://support.1password.com/files/device-trust/openapi-2026-04-07.json |
| DT-4 | Check status has eight values; `stale` means options changed since the last run | 6.4 | C | Spec enum: unknown, passing, failing, errored, inapplicable, stale, pending, out_of_scope; overview defines stale that way | spec; https://support.1password.com/device-trust-checks-overview/ |
| DT-5 | Sold as Device Trust Core and Connect within Unified Access; no Extended Access Management on the page | 4.4, 10 | C | All stated; the page mentions "Extended Device Compliance" instead | https://1password.com/product/device-trust |

### 3.9 Market and audit (market-and-audit.md)

| Id | Claim (short) | Section | Verdict | What the source says | Source |
|---|---|---|---|---|---|
| MK-1 | Vanta's lock test passes at 60 minutes idle or less | 4.1, 9.5, C4 | C | Stated; no other threshold | https://help.vanta.com/en/articles/11345823-device-monitoring-in-vanta |
| MK-2 | Secureframe lock fixed at 15 minutes; password at least 8 with complexity; daily sync; BYOD screenshot is the auditor's call | 4.1, 5, C10 | C | All stated | https://support.secureframe.com/en/articles/15877671-faqs-secureframe-agent-macos-profiles-password-policy-and-endpoint-checks |
| MK-3 | CIS 4.3: at most 15 minutes on general purpose OSs, at most 2 minutes on mobile; metric is locked over lockable | 6.3, 9.5, D-MKT-5 | C | Both thresholds and the M1 to M6 metric stated | https://controls-assessment-specification.readthedocs.io/en/latest/control-4/control-4.3.html |
| MK-4 | Schneider Downs: report name, source, filters, period, run time, query, same parameters, counts; dated full screen screenshots; prefer exports | 6.1 | X | Mostly right; query shown as a screenshot, not as text; no rework wording (see X12) | https://schneiderdowns.com/our-thoughts-on/soc-audit-ipe-explained-how-to-avoid-delays-rework-exceptions/ |
| MK-5 | Linford: inventories are IPE; auditor tests completeness and accuracy directly or via controls; a hand made list can be refused | 6.1 | X | First two confirmed; refusal overstated (see X11) | https://linfordco.com/blog/iuc-ipe-audit-procedures-for-soc-audits/ |
| MK-6 | Linford remote: screen share walkthroughs, random sample, leavers against a serial inventory, timestamped wipe records, lock at 10 to 15 minutes | 6.1, 9.4 | C | All present; the wipe point asks for a timestamped workflow showing wipe ability, not logs of completed wipes | https://linfordco.com/blog/soc-2-physical-security-remote-considerations/ |
| MK-7 | Android 12 removes IMEI, MEID and serial on personal work profiles; enrolment specific id stable across resets | 2.5, 7.2 | C | Both stated | https://developer.android.com/work/versions/android-12 |
| MK-8 | Apple User Enrolment hides serial and UDID (and IMEI, MEID) | 2.5, 7.2 | X | Serial and UDID confirmed; IMEI and MEID only from 2019 (see X13) | https://support.apple.com/guide/deployment/managed-device-attestation-dep28afbde6a/web |
| MK-9 | Nobody checks phones | 2.2, 8, 9.6 | U | Four of five confirmed; Sprinto Jamf open (see X8) | sources in MK-10 to MK-22 |
| MK-10 | Vanta Intune: macOS and Windows, no iOS or Android; lock, antivirus, encryption from compliance policy; apps weekly; none on non corporate; 3 hour grace; owner via Entra | 3, 4.2, 5 | C | All stated | https://help.vanta.com/en/articles/11345786-connecting-vanta-microsoft-endpoint-manager-intune-mdm |
| MK-11 | Vanta Jamf: macOS only, cloud only, no mobile sync; lock from profile payloads; site or group scoping | 3, 4.2, 5 | C | All stated | https://help.vanta.com/en/articles/11345770-connecting-vanta-jamf-pro |
| MK-12 | Vanta Iru: macOS and Windows; FileVault, enrolment, agent status, Activation Lock | 3, 4.2 | C | All stated | https://help.vanta.com/en/articles/11345787-connecting-vanta-iru |
| MK-13 | Vanta Workspace ONE: no lock data through the API; lock only with a passcode profile | 3, 4.2 | C | Stated | https://help.vanta.com/en/articles/11345780-connecting-vanta-vmware-workspace-one-mdm |
| MK-14 | Vanta Rippling: only computers with a serial; mobile not synced | 3, 5 | C | Stated | https://help.vanta.com/en/articles/11345682-connecting-vanta-rippling |
| MK-15 | Vanta JumpCloud: yes, including Linux | 3 | U | Platforms not named (see X9) | https://help.vanta.com/en/articles/11345785-integrating-vanta-jumpcloud-mdm |
| MK-16 | Vanta agent: Last Checked over one day suggests trouble; MDM devices have no threshold and update only on change | 5 | C | Stated | https://help.vanta.com/en/articles/11345936-understanding-the-last-checked-column-on-the-computers-page |
| MK-17 | Drata Intune: tests 61, 64, 65, 66 follow Intune's verdict; macOS and Windows only; matched by serial plus user email or UPN | 3, 4.2, 5, C2 | X | Verdict and platforms confirmed (64 can use a managed app instead); matching corrected (see X10); "since 27 May" has no year on the page | https://help.drata.com/en/articles/16190016-microsoft-intune-integration-guide |
| MK-18 | Drata JumpCloud: macOS, Windows, Linux; mobile not supported | 3 | C | Computers only on those three; phones and tablets unsupported | https://help.drata.com/en/articles/5872265-jumpcloud-mdm-connection |
| MK-19 | Drata: mobile unsupported; one owner per device; manual unlink; exclusions per person only, with reason and dates, shown in audit exports | 4.2, 5, C5 | C | All stated | https://help.drata.com/en/articles/13613390-multi-device-support , https://help.drata.com/en/articles/13521706-personnel-exclusions |
| MK-20 | Drata BYOD: 15 minute workstation lock; email only phones usually covered by policy; deletion request at exit | 2.2, 4.1, 8 | C | All stated; also suggests 1 minute on phones (see A1) | https://help.drata.com/en/articles/6297649-how-do-bring-your-own-device-byod-devices-affect-my-audit |
| MK-21 | Drata agent checks encryption, lock, antivirus, password manager, updates, every 24 hours fixed; no firewall test | 4.1, C3 | C | All stated; the page names no operating systems, so the platform list rests on round 1 | https://help.drata.com/en/articles/4742932-how-does-the-drata-agent-work |
| MK-22 | Secureframe table: Intune 6 checks macOS and Windows; Jamf Pro 6 with Windows listed; JumpCloud and Kolide 6 on macOS, Windows, Linux; Kandji 5 macOS; Addigy 4 macOS; Hexnode and Mosyle 0 (inventory); 19 sources; mobile checks never apply; contractors without production access out of scope | 3, 4.2, 5, C9 | C | Counts, platforms and the two policy statements match. Which named checks the 2 marks for AirWatch and NinjaOne and the 3 for Rippling stand for could not be read from the page text (unverified per check) | https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities |
| MK-23 | Sprinto: Hexnode lock, antivirus, encryption; Jamf lock only; Intune lock plus Windows antivirus; Jamf page OS, encryption, antivirus on macOS, iOS, iPadOS | 3, C7, C8 | C | All stated; the two Jamf pages do conflict | https://docs.sprinto.com/monitors/extended-checks-in-mdm-tool-comms , https://docs.sprinto.com/integrations/overview/jamf-integration |
| MK-24 | Sprinto: Inactive after 90 days without a report, when the owner is offboarded, or on a failed sync; checks every 24 hours; owner picks company or employee; scope toggle | 5, 9.9, C7 | C | All stated across the FAQ and how it works pages | https://docs.sprinto.com/data-library/staff-devices/frequently-asked-questions , https://docs.sprinto.com/data-library/staff-devices/how-it-works |
| MK-25 | Scrut: Hexnode API lacks encryption and lock; Hexnode phones go to asset management; NinjaOne cannot verify encryption or lock and syncs only assigned devices; agent syncs every 3 hours | 3, 4.1, 5, C6 | C | All stated; MDM syncs are daily | https://help.scrut.io/docs/integrating-hexnode , https://help.scrut.io/docs/integrating-ninjaone , https://help.scrut.io/docs/scrut-agent-faqs-troubleshooting |
| MK-26 | Hyperproof offers proof lists, no posture tests: Jamf computers and mobile devices, JumpCloud, Kandji, Google Chrome devices, CrowdStrike | 3, C11 | C | Those proof types confirmed with a Testable column; Intune, SentinelOne, Okta and Defender sat in the unread part of a long page (unverified) | https://intercom.help/hyperproofio/en/articles/14303912-supported-apps-and-proof-types-for-hypersyncs |

## 4. Totals

| File | Rows | Confirmed | Corrected | Unverified |
|---|---|---|---|---|
| cross-platform-mdms-a.md (WS, JC, HX, ME) | 41 | 36 | 3 | 2 |
| cross-platform-mdms-b.md (FL, NJ, RP, DT) | 30 | 28 | 2 | 0 |
| market-and-audit.md (MK) | 26 | 20 | 4 | 2 |
| **All** | **97** | **84** | **9** | **4** |

Rows group linked atomic claims from one source; more than 150 atomic claims were checked in total. Corrections that
change a check or a credential step: X1 (Workspace ONE escrow and passcode come from a per device endpoint whose
schema holds key material), X3 (Fleet `wiped_host` is a request, not a completed wipe), X4 (Hexnode privacy drop
keys), X6 and X7 (JumpCloud fallback key and NinjaOne grant type need an onboarding test). No correction changes
the proposed connector order: the five "table stakes" sources and their competitor counts survive, and the Linux
argument for JumpCloud rests on confirmed Drata and Secureframe pages.
