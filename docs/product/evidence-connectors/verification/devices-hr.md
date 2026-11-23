# Verification log: devices, endpoint protection and HR

Round: 2026-11-23. Scope: [mdm-and-endpoint-strategy.md](../mdm-and-endpoint-strategy.md) and the connector files
[intune.md](../connectors/intune.md), [microsoft-defender-endpoint.md](../connectors/microsoft-defender-endpoint.md),
[jamf-pro.md](../connectors/jamf-pro.md), [kandji.md](../connectors/kandji.md),
[google-endpoint-management.md](../connectors/google-endpoint-management.md),
[crowdstrike-falcon.md](../connectors/crowdstrike-falcon.md), [sentinelone.md](../connectors/sentinelone.md),
[hr-systems.md](../connectors/hr-systems.md).

Method: every "unverified" mark and every permission, scope, role, licence, endpoint and field a check
depends on was read against the provider's official pages. Source tags (S1, A7, B2 ...) refer to the
Sources section of the file named in the row, where the full URL is listed. "Confirmed" means an official
page states it (including facts that replaced an "unverified" mark). "Corrected" means the file said
something else, now fixed in place. "Still unverified" keeps the mark, with the reason. Third party pages
(Palo Alto XSOAR for SentinelOne, Vanta, Drata, Secureframe) count as confirmed only for claims about
those third parties themselves.

## Corrections that change a check, a decision or a recommendation

| File | Correction | Effect |
|---|---|---|
| intune.md | Intune report export jobs document only ReadWrite permissions (v1.0 and beta) | `devices.firewall_enabled` on Windows cannot use the FirewallStatus report under the read only rule: Windows gives `insufficient` until a read permission is proven. macOS is unaffected. The `Devices` report cross read for encryption is held back too. Strategy 5.5 Intune firewall stays partial, now explained |
| hr-systems.md | Gusto contractors have only `dismissal_date`, no planned contract end date | `hr.contractors_have_end_dates` cannot pass from Gusto alone: noted in the check's row (2.2) and in 7.3. Recommendation order (Gusto after partner review) unchanged |
| kandji.md | Prism `filevault` has a documented `key_escrowed` column | `devices.recovery_key_escrowed` on Kandji moves from likely to yes (kandji.md 5.2, strategy 5.5) |
| google-endpoint-management.md | `additionalSignals` has `is_os_native_firewall_enabled`; it has no screen lock key | `devices.firewall_enabled` on Google moves from likely to yes (strategy 5.5). `devices.screen_lock` stays no |
| jamf-pro.md | Configuration profiles are only on the Classic API; only Classic computer endpoints are deprecated | Section 8 rule narrowed: never the deprecated Classic computer endpoints, Classic profile reads allowed |
| jamf-pro.md | The FileVault inventory endpoint needs View Disk Encryption Recovery Key and returns personal recovery keys | Verity never calls it; noted under privileges |
| mdm-and-endpoint-strategy.md | Secureframe's agent runs osquery under Fleet's Orbit; Vanta's Device Monitor is osquery based and self installed only | Supports option A as feasible; recommendation (defer the agent) unchanged |

No check key or control mapping was changed.

## Claims checked

| # | File | Claim | Result | Source or reason |
|---|---|---|---|---|
| 1 | strategy | Drata Agent: checks, platforms, emailed token registration, Electron and osquery, Apache-2.0, unofficial builds unsupported | confirmed | A1 |
| 2 | strategy | Vanta agent checks include OS updates | corrected | A8: antivirus, disk encryption, screen lock, password manager only; now named Device Monitor |
| 3 | strategy | Vanta agent built on osquery | confirmed | A8 |
| 4 | strategy | Vanta agent distributed by direct install or MDM | corrected | A8: people install it after a Vanta task; choosing MDM blocks the download |
| 5 | strategy | Vanta agent platforms (Linux coverage) | confirmed | A9 (search summary): Linux detects disk encryption only |
| 6 | strategy | Secureframe Agent checks ("similar", not read) | confirmed | A10: screen lock, antivirus, firewall, encryption, password, device present |
| 7 | strategy | Secureframe Agent platforms | confirmed | A10: macOS, Windows, Linux with Linux gaps |
| 8 | strategy | Secureframe Agent distribution | confirmed | A11: per person installer, not for mass deployment |
| 9 | strategy | Secureframe Agent basis | confirmed | A11: osquery managed by Orbit |
| 10 | strategy | Vanta and Secureframe agents open source | still unverified | neither page says |
| 11 | strategy | osquery dual licence Apache-2.0 or GPL-2.0-only | confirmed | A2 |
| 12 | strategy | osquery `screenlock` columns and user scope | confirmed | A3 |
| 13 | strategy | osquery preference tables | confirmed | A12, A13 |
| 14 | strategy | `windows_security_center` health values | confirmed | A4 |
| 15 | strategy | osquery disk encryption tables | confirmed | A14, A15 |
| 16 | strategy | Fleet MIT outside `ee/`; `ee/` needs a subscription, no selling or sublicensing | confirmed | A5, A6 |
| 17 | strategy | macOS: Developer ID, hardened runtime, notarization with `notarytool` | confirmed | A7 (.md version of Apple's page) |
| 18 | strategy | Windows Authenticode signing avoids reputation warnings | corrected | A16: signing helps, reputation still builds over time |
| 19 | strategy | Without an MDM, macOS privacy permissions cannot be pre approved | confirmed | A17 |
| 20 | strategy | Auditors accept screenshots or self attestation | still unverified | AICPA guidance not public; not researched |
| 21 | strategy | Endpoint Verification on almost every Workspace edition | confirmed | google S3 |
| 22 | strategy | 5.5: Kandji escrow "likely" | corrected | kandji S1: yes |
| 23 | strategy | 5.5: Google firewall "likely" | corrected | google S1: yes |
| 24 | strategy | 5.5: Intune firewall partial | corrected | reason added: export job needs ReadWrite (intune S15) |
| 25 | strategy | 5.5: SentinelOne fields | still unverified | console login required |
| 26 | intune | Go module paths for Graph v1.0, beta and azidentity | confirmed | S14 (go.mod files) |
| 27 | intune | Active Intune licence required for Intune Graph calls | confirmed | S1 |
| 28 | intune | Graph application consent needs Privileged Role Administrator; app admins cannot | confirmed | S2 |
| 29 | intune | `DeviceManagementManagedDevices.Read.All` for the device list | confirmed | S3 |
| 30 | intune | `BitlockerKey.ReadBasic.All` application permission; key not returned | confirmed | S4 |
| 31 | intune | Permission for the reports export API | corrected | S15: only ReadWrite permissions documented |
| 32 | intune | Intune Plan 1 in Microsoft 365 E3, E5, EMS E3, E5 | confirmed | S16 |
| 33 | intune | Intune in Microsoft 365 Business Premium | confirmed | S5 |
| 34 | intune | Graph throttling numbers | corrected | S7: 130,000 per 10 s per app globally; Intune devices 2,000 per 20 s per app per tenant |
| 35 | intune | Cleanup rules 30 to 270 days, hide only | confirmed | S8 |
| 36 | intune | BitLocker keys kept while the Entra device exists | confirmed | S18 |
| 37 | intune | Export jobs only on beta | corrected | S19: v1.0 and beta |
| 38 | intune | Report columns FirewallStatus, NoncompliantDevicesAndSettings, Devices EncryptionStatus | confirmed | S10 |
| 39 | intune | managedDevice fields kept | confirmed | S6 |
| 40 | intune | `managementAgent` values | confirmed | S6 |
| 41 | intune | `deviceEnrollmentType` values | confirmed | S6 |
| 42 | intune | `managementState` only in the example | confirmed | S3, S6 |
| 43 | intune | macOS `isEncrypted` maps to FileVault | still unverified | Microsoft does not say; test on fixture |
| 44 | intune | macOS compliance names for password and idle lock | confirmed | S17 |
| 45 | intune | macOS firewall compliance property | confirmed | S17: `firewallEnabled` |
| 46 | intune | FileVault escrow metadata in Graph v1.0 | still unverified | not found |
| 47 | intune | `actionState` values | confirmed | S20 |
| 48 | intune | How long action results stay on the record | still unverified | not stated |
| 49 | intune | Intune audit events permission | confirmed | S21: `DeviceManagementApps.Read.All` |
| 50 | intune | Removable storage per device status route | still unverified | not researched |
| 51 | intune | Device with no policy counts as compliant | confirmed | S22: default setting is Compliant |
| 52 | intune | Test tenant availability | confirmed | S1 (Intune trial), S23 (sandbox limits) |
| 53 | intune | `windowsProtectionState` protection fields | confirmed | S11 |
| 54 | intune | Vanta Intune permissions | corrected | S12: adds `DeviceManagementConfiguration.Read.All` |
| 55 | intune | Drata Intune permissions and platforms | corrected | S13: two permissions now, macOS and Windows |
| 56 | intune | Secureframe Intune | confirmed | S24 |
| 57 | intune | Sprinto Intune | still unverified | not researched |
| 58 | defender | Calls go to `api.security.microsoft.com` | confirmed | S1 |
| 59 | defender | Non Graph consent by Cloud Application or Application Administrator | confirmed | S2 |
| 60 | defender | `Machine.Read.All` for machines | confirmed | S1 |
| 61 | defender | `Machine.Read.All` for the antivirus health export | confirmed | S7 |
| 62 | defender | List alerts page lists only `Alert.ReadWrite.All` | confirmed | S3 |
| 63 | defender | Graph `SecurityAlert.Read.All` | confirmed | S3 |
| 64 | defender | API access in Plan 1, Plan 2, Defender for Business | corrected | source changed to S11; S4 does not list APIs |
| 65 | defender | Alert data available to Plan 1 tenants | still unverified | not stated |
| 66 | defender | Retention 180 days | confirmed | S12; Plan 1 and Business retention unclear (S11) |
| 67 | defender | Device groups in Plan 1 and Plan 2 | confirmed | S1 |
| 68 | defender | Machine `healthStatus`, `onboardingStatus`, `lastSeen` meaning | confirmed | S6 |
| 69 | defender | Machines `$top` 10,000; 100 a minute, 1,500 an hour; 404 when none | confirmed | S1 |
| 70 | defender | `avMode` code table ambiguous | corrected | S13: 0 to 5 listed |
| 71 | defender | `avIs*UpToDate` fields | confirmed | S13 |
| 72 | defender | Antivirus health is a snapshot; 30 calls a minute | confirmed | S7 |
| 73 | defender | Alert field names | confirmed | S3 |
| 74 | defender | Alert retention 180 days by default | confirmed | S3, S12 |
| 75 | defender | EDR block mode not readable | corrected | S13: `avMode` 4 |
| 76 | defender | Attack surface reduction settings | still unverified | not researched |
| 77 | defender | Token resource `api.securitycenter.microsoft.com` | confirmed | S7 |
| 78 | defender | Intune tamper protection field and DefenderAgents columns | confirmed | S8, S9 |
| 79 | defender | Vanta Defender integration | confirmed | S14 (search summary); exact permissions still unverified |
| 80 | defender | Drata, Secureframe, Sprinto Defender | still unverified | not researched |
| 81 | jamf | Token from `/api/v1/oauth/token`, client credentials | confirmed | S9 |
| 82 | jamf | Token lives 599 seconds | corrected | S1, S9: lifetime set per client, read `expires_in` |
| 83 | jamf | Client access is the sum of its roles | confirmed | S1 |
| 84 | jamf | Role changes and secret rotation | confirmed | S1 |
| 85 | jamf | Minimum version for API Roles and Clients | confirmed | S1, S11: 10.49.0 |
| 86 | jamf | Settings path | corrected | S11: Settings, System, API Roles and Clients |
| 87 | jamf | Read Computers for v4 inventory | confirmed | S2 |
| 88 | jamf | Read macOS Configuration Profiles | confirmed | S13 |
| 89 | jamf | Read Mobile Devices | confirmed | S10 |
| 90 | jamf | MDM command history privilege | confirmed | S4: View MDM command information in Jamf Pro API |
| 91 | jamf | Platform API permission names | corrected | removed from the row: not needed; not fetched |
| 92 | jamf | Default page size cited to the FileVault variant | corrected | S2 for paging |
| 93 | jamf | FileVault inventory endpoint privilege and payload | confirmed | S6 |
| 94 | jamf | Inventory section names | confirmed | S2 |
| 95 | jamf | General section fields | confirmed | S2 |
| 96 | jamf | Last contact and check in field names | corrected | S2: `lastContact`, `lastCheckIn`, `reportDate` |
| 97 | jamf | Disk encryption fields and state values | confirmed | S2 |
| 98 | jamf | Recovery key validity values | confirmed | S2 |
| 99 | jamf | Security section fields | confirmed | S2 |
| 100 | jamf | OS, user and hardware fields | confirmed | S2 |
| 101 | jamf | Inventory from 10.39.0; Classic computer endpoints deprecated from 11.15.0 | confirmed | S5 |
| 102 | jamf | First version with v4 inventory | still unverified | not stated |
| 103 | jamf | macOS configuration profile endpoint | corrected | S12: Classic API list route; by id route not read |
| 104 | jamf | "Never the Classic API" | corrected | S5, S12 |
| 105 | jamf | Scalability guidance | confirmed | S7 |
| 106 | jamf | MDM command filter fields | confirmed | S4 |
| 107 | jamf | A filter is required | confirmed | S4 |
| 108 | jamf | MDM command response field names | corrected | S4: `commandType`, `commandState` |
| 109 | jamf | Erase command and state values | confirmed | S4 |
| 110 | jamf | MDM command retention | still unverified | not stated |
| 111 | jamf | Mobile device path and fields | confirmed | S10 |
| 112 | jamf | Apple erase prerequisites per Mac | still unverified | Apple deployment guide not read |
| 113 | jamf | Community Go SDK status | still unverified | not checked |
| 114 | jamf | Sandbox availability | still unverified | not checked |
| 115 | jamf | Vanta Jamf privileges and tests | confirmed | S3 |
| 116 | jamf | Drata Jamf tests include encryption | corrected | S8: not mentioned |
| 117 | jamf | Secureframe Jamf | confirmed | S14 |
| 118 | kandji | Renamed Iru in October 2025 | confirmed | S3, S6: 22 October 2025 |
| 119 | kandji | `subdomain.api.iru.com` for migrated tenants | confirmed | S3 |
| 120 | kandji | US and EU API URL formats | confirmed | S1 |
| 121 | kandji | Token shown once | confirmed | S2 |
| 122 | kandji | Token created in Settings, Access | corrected | S2: account menu, Access |
| 123 | kandji | Labels Device list, Device details | confirmed | S7 |
| 124 | kandji | Labels for commands, Prism, Users | still unverified | not shown on the pages read |
| 125 | kandji | 10,000 requests an hour | confirmed | S1, S2 |
| 126 | kandji | Device list `limit` maximum 300 | confirmed | S1 |
| 127 | kandji | API platform values Apple only | confirmed | S1 |
| 128 | kandji | No Windows or Android | corrected | S3: product now covers them |
| 129 | kandji | Device list returns Windows or Android | still unverified | not stated |
| 130 | kandji | Device list fields | confirmed | S1 (example, no schema) |
| 131 | kandji | `filevault_enabled` filter | confirmed | S1 |
| 132 | kandji | `is_removed` retention | still unverified | not documented |
| 133 | kandji | Device details FileVault fields | still unverified | no success schema in the specification |
| 134 | kandji | Supervision field | still unverified | not in the specification |
| 135 | kandji | iOS data protection from details | still unverified | no documented schema |
| 136 | kandji | Prism categories | confirmed | S1 |
| 137 | kandji | application_firewall columns | confirmed | S1 |
| 138 | kandji | desktop_and_screensaver columns | still unverified | no idle time column documented |
| 139 | kandji | Prism filevault `key_escrowed` | confirmed | S1 |
| 140 | kandji | Prism parameters and export | confirmed | S1 |
| 141 | kandji | Command fields | confirmed | S1 |
| 142 | kandji | Command status code meanings | still unverified | not documented |
| 143 | kandji | Users endpoint paging | corrected | S1: cursor paging |
| 144 | kandji | Plans that include the API | still unverified | not stated |
| 145 | kandji | Secrets and action endpoints exist (never granted) | confirmed | S1 |
| 146 | kandji | Drata Kandji permissions and tests | confirmed | S5 |
| 147 | kandji | Vanta and Secureframe Kandji permissions | confirmed | S7, S8 |
| 148 | kandji | What Vanta tests on Kandji | still unverified | not read |
| 149 | kandji | Scrut and Scytale guides | still unverified | not read |
| 150 | google | Go import paths | confirmed | S11 |
| 151 | google | Devices API needs domain wide delegation for a service account | confirmed | S12 |
| 152 | google | Admin privileges for the impersonated user | still unverified | not named by Google |
| 153 | google | `cloud-identity.devices.readonly` for devices.list | confirmed | S4 |
| 154 | google | ChromeOS read only scope | confirmed | S13 |
| 155 | google | Wipe events in the audit log | confirmed | S14, S15 |
| 156 | google | Basic and advanced management editions and wipe scope | confirmed | S7, S8 |
| 157 | google | Endpoint Verification editions | confirmed | S3 |
| 158 | google | Device fields and enums | confirmed | S1 |
| 159 | google | `additionalSignals` content | corrected | S1: named keys, no screen lock |
| 160 | google | `pageSize` up to 100 | confirmed | S4: default 20 |
| 161 | google | List views COMPANY_INVENTORY and USER_ASSIGNED_DEVICES | confirmed | S4 |
| 162 | google | API quotas | still unverified | not checked |
| 163 | google | How long inactive devices stay listed | still unverified | not stated |
| 164 | google | deviceUsers enums | confirmed | S9 |
| 165 | google | Field that carries desktop screen lock | still unverified | only `passwordState`, meaning not stated (S9) |
| 166 | google | Signals per platform, helper runs as the user | confirmed | S2 |
| 167 | google | Firewall value | corrected | S1: `is_os_native_firewall_enabled` |
| 168 | google | ChromeOS page size | confirmed | S13: 300 |
| 169 | google | Comparable platforms reading Google devices | still unverified | not checked |
| 170 | crowdstrike | gofalcon not a formal product | confirmed | S1 |
| 171 | crowdstrike | gofalcon retries off by default | confirmed | S1 |
| 172 | crowdstrike | Cloud base URLs | confirmed | S5, S6 (US-GOV-2 added) |
| 173 | crowdstrike | Token lifetime | confirmed | S7: 30 minutes |
| 174 | crowdstrike | Hosts: READ on hosts routes | confirmed | S2 |
| 175 | crowdstrike | Hosts paging parameters | confirmed | S2 |
| 176 | crowdstrike | Host fields | confirmed | S2 |
| 177 | crowdstrike | Prevention policies: READ and routes | confirmed | S3 |
| 178 | crowdstrike | `prevention_settings` structure | still unverified | examples are empty; read from fixtures |
| 179 | crowdstrike | Sensor update policies scope, v2 route, uninstall protection | confirmed | S9 |
| 180 | crowdstrike | Host groups: READ and routes | confirmed | S10 |
| 181 | crowdstrike | Alerts: READ, v2 query and entity fetch | confirmed | S4 |
| 182 | crowdstrike | v1 alerts deprecated for v2 and v3 | corrected | S4: v3 only for updates |
| 183 | crowdstrike | Alert status values | confirmed | S13 |
| 184 | crowdstrike | Detects API deprecation date | confirmed | S12: 30 September 2025, decommissioned |
| 185 | crowdstrike | Rate limits | still unverified | only response headers are documented (S11) |
| 186 | crowdstrike | Console menu path | confirmed | S5 (label differs between consoles) |
| 187 | crowdstrike | Falcon Administrator creates API clients | still unverified | third party only (S8); role docs need a login |
| 188 | crowdstrike | Inactive host retention | still unverified | Falcon login required |
| 189 | crowdstrike | Subscriptions with API access | still unverified | no public page |
| 190 | crowdstrike | Alert retention by subscription | still unverified | no public page |
| 191 | crowdstrike | Test tenant availability | still unverified | not checked |
| 192 | crowdstrike | Vanta CrowdStrike | confirmed | S8 |
| 193 | crowdstrike | Drata CrowdStrike | confirmed | S14 |
| 194 | crowdstrike | Secureframe, Sprinto CrowdStrike | still unverified | no public guide found |
| 195 | sentinelone | Header `Authorization: ApiToken` | confirmed | S2 (SentinelOne example code) |
| 196 | sentinelone | API version 2.1 base path | confirmed | S2 |
| 197 | sentinelone | `/agents` and `/threats` paths | still unverified | login required |
| 198 | sentinelone | Cursor paging | still unverified | login required (third party only) |
| 199 | sentinelone | Agent fields seen in XSOAR | corrected | S1: group and OS revision not shown; encrypted applications shown |
| 200 | sentinelone | Threat fields | still unverified | third party only (S1) |
| 201 | sentinelone | Incident status and analyst verdict values | still unverified | third party only (S1) |
| 202 | sentinelone | Policy mitigation mode and anti tamper fields | still unverified | login required |
| 203 | sentinelone | Viewer role | corrected | S3: Vanta uses a custom view only role; built in Viewer unverified |
| 204 | sentinelone | Token expiry rules | still unverified | console rules need a login; S3 shows expiry chosen at creation |
| 205 | sentinelone | Console URL format | still unverified | third party only (S1) |
| 206 | sentinelone | No official Go SDK | confirmed | S2 |
| 207 | sentinelone | Tiers with API access | still unverified | no public page |
| 208 | sentinelone | Serial number on agents | still unverified | login required |
| 209 | sentinelone | Test console availability | still unverified | not checked |
| 210 | sentinelone | Vanta SentinelOne | confirmed | S3 |
| 211 | sentinelone | Drata, Secureframe, Sprinto SentinelOne | still unverified | no public guide found |
| 212 | hr | BambooHR Basic auth, base URL, OAuth | confirmed | B1 |
| 213 | hr | BambooHR key inherits the user's permissions | confirmed | B1 |
| 214 | hr | BambooHR lockout with 403 | confirmed | B1 |
| 215 | hr | BambooHR API by plan | still unverified | help page did not render |
| 216 | hr | BambooHR field level access levels | still unverified | search summary only; former employee limit untested |
| 217 | hr | BambooHR scopes `employee`, `employee:job`, `employee:name` | confirmed | B2 |
| 218 | hr | BambooHR `training` scope | confirmed | B3 |
| 219 | hr | BambooHR paging and status filter | confirmed | B2 |
| 220 | hr | BambooHR `_restrictedFields` and filter drop | confirmed | B2 |
| 221 | hr | BambooHR default status set | still unverified | not stated |
| 222 | hr | BambooHR employee field names | confirmed | B2 |
| 223 | hr | BambooHR employment type field | confirmed | B2: `employmentStatusName` |
| 224 | hr | BambooHR job history tables | confirmed | B5, B6 |
| 225 | hr | BambooHR training endpoint and fields | confirmed | B3 |
| 226 | hr | BambooHR directory excludes former employees | confirmed | B4 |
| 227 | hr | BambooHR change feed not found | corrected | B7: `employees/changed` exists |
| 228 | hr | BambooHR no screening module | confirmed | B6 |
| 229 | hr | Rippling token creation and permission profile | confirmed | R1 |
| 230 | hr | Rippling token revoked after 30 unused days or owner termination | confirmed | R1 |
| 231 | hr | Rippling service accounts | confirmed | R1: none documented |
| 232 | hr | Rippling separate entitlement | confirmed | R1 |
| 233 | hr | Rippling base URL | confirmed | R1, R7 |
| 234 | hr | Rippling `workers.read` | confirmed | R3 |
| 235 | hr | Rippling scopes for expanded fields | still unverified | no page ties expand to scope |
| 236 | hr | Rippling worker status values | confirmed | R3 |
| 237 | hr | Rippling termination types | corrected | R3: eight values |
| 238 | hr | Rippling employment type field | corrected | R3: `employment_type_id` with expand |
| 239 | hr | Rippling paging and filters | confirmed | R3 |
| 240 | hr | Rippling default list includes terminated | still unverified | not stated |
| 241 | hr | Rippling worker changes | confirmed | R4 |
| 242 | hr | Rippling partner review process | confirmed | R5; lead time not given |
| 243 | hr | Rippling termination webhook | confirmed | R2 |
| 244 | hr | Rippling screening and training not in API | confirmed | R2 |
| 245 | hr | Workday: all docs behind login | corrected | W1 is public |
| 246 | hr | Workday `Get_Workers` | confirmed | W1 |
| 247 | hr | Workday background check data | confirmed | W1 |
| 248 | hr | Workday security domains | still unverified | only one domain named on W1 |
| 249 | hr | Workday RaaS through an Integration System User | still unverified | Workday Community login required |
| 250 | hr | Workday contract end date field | still unverified | not found in the part read |
| 251 | hr | Workday REST client and Learning | still unverified | login required |
| 252 | hr | Gusto scopes assigned in review | confirmed | G1 |
| 253 | hr | Gusto partner approval first | confirmed | G4 |
| 254 | hr | Gusto partner lead time | still unverified | not published |
| 255 | hr | Gusto `employees:read`, avoid `compensations:read` | confirmed | G2 |
| 256 | hr | Gusto bearer header | confirmed | G2 (version header added) |
| 257 | hr | Gusto employees endpoint and fields | confirmed | G2 |
| 258 | hr | Gusto `per` default 25 | still unverified | only a general default is stated |
| 259 | hr | Gusto `terminated` filter | confirmed | G2 |
| 260 | hr | Gusto contractors endpoint, scope and fields | confirmed | G3 |
| 261 | hr | Gusto contractor end dates | corrected | G3: only `dismissal_date`; check not feasible on Gusto |
| 262 | hr | Gusto screening and training | still unverified | not checked |
| 263 | hr | HiBob service user, no default access | confirmed | H1 |
| 264 | hr | HiBob auth header scheme | confirmed | H3: HTTP Basic |
| 265 | hr | HiBob default access covers active employees | confirmed | H1, H2 (page states it two ways) |
| 266 | hr | HiBob base and sandbox URLs | confirmed | H2 |
| 267 | hr | HiBob people search, `showInactive`, 400 fields | confirmed | H2 |
| 268 | hr | HiBob field paths | confirmed | H2 |
| 269 | hr | HiBob `payroll.employment.type` | still unverified | seen only in an example |
| 270 | hr | HiBob termination date read field | still unverified | not found |
| 271 | hr | HiBob rate limit numbers not stated | corrected | H4: 50 a minute |
| 272 | hr | HiBob history endpoints | confirmed | H6 |
| 273 | hr | HiBob training read | confirmed | H5: no read documented |
| 274 | hr | HiBob screening | still unverified | not checked |
| 275 | hr | Test accounts (Gusto demo, HiBob sandbox, Rippling test company) | confirmed | G1, H2, R5 |
| 276 | hr | Vanta HR auth and Merge use | confirmed | C1 (Merge); BambooHR auth from search summary only |
| 277 | hr | Drata HR connections and fields | confirmed | C2 |
| 278 | hr | Secureframe HR integrations | still unverified | search summaries only |
| 279 | hr | Finch use by Vanta, Drata, Secureframe | still unverified | no mention found |
| 280 | hr | Sprinto HR | still unverified | not checked |

## Totals

Confirmed 174, corrected 37, still unverified 69 (280 claims).
