# Microsoft Defender for Endpoint

| | |
|---|---|
| Capabilities | endpoint_protection |
| Delivery phase | Not in the signed catalogue. Not in `capabilities.json` at all (the endpoint_protection providers listed are CrowdStrike and SentinelOne, both `not_planned`). Adding it is part of decision D-DEV-1 and D-DEV-12 |
| Auth model | OAuth 2.0 client credentials with application permissions on the WindowsDefenderATP API, admin consent |
| Shares setup with | The Entra ID and Intune connectors: the same app registration gains a second API's permissions ([intune.md](intune.md)) |
| Go library | No Go SDK found for the Defender for Endpoint API: plain REST with `azidentity` for the token. The Graph security route can use `msgraph-sdk-go` |

Check definitions: [mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue).

## 1. What it proves

Defender for Endpoint is the EDR many Microsoft 365 customers already pay for. It shows which machines
run the sensor and when each last reported, the machine's sensor health, the Defender Antivirus mode
(active, passive, disabled) and whether signatures and engine are current, and every alert with its
status, owner, classification and resolution time. That covers the agent half of EP-01 and the alert
handling half of EP-01.C and LM-04.

It does not prove that machines without the sensor exist or not (that needs the device or asset
inventory, `endpoint.coverage_complete` and `endpoint.servers_covered`), or that a true positive became an
incident (EP-01.D stays with people or a ticketing source).

## 2. Connecting: method, credentials and permissions

### 2.1 Method

Same app registration as Entra ID and Intune. The customer adds consent for the WindowsDefenderATP API.
Calls go to `https://api.security.microsoft.com` [S1].

For APIs other than Microsoft Graph, a Cloud Application Administrator or Application Administrator can
grant admin consent; Graph application permissions need Privileged Role Administrator or Global
Administrator [S2].

### 2.2 Permissions

| Permission (application, WindowsDefenderATP) | Read only | Needed for | Role that can grant it |
|---|---|---|---|
| `Machine.Read.All` | yes | `endpoint.protection_active`, `endpoint.coverage_complete`, `endpoint.servers_covered`; machines [S1] and the antivirus health export `GET /api/deviceavinfo` [S7] | Cloud Application Administrator, Application Administrator, Privileged Role Administrator, Global Administrator [S1][S2] |
| `Alert.Read.All` | yes | `endpoint.detections_triaged` | same. Note: the List alerts page lists only `Alert.ReadWrite.All`; `Alert.Read.All` appears on the user related alerts page [S3]. Test read only access before release; if it fails, use the Graph route below rather than accept a write permission |
| Graph `SecurityAlert.Read.All` (alternative) | yes | `endpoint.detections_triaged` through `GET /v1.0/security/alerts_v2`, the least privileged application permission for that call [S3] | Privileged Role Administrator or Global Administrator [S2] |

No permission for machine actions, live response, indicators or advanced hunting write.

### 2.3 Licences

Defender for Endpoint Plan 1, Plan 2 and Defender for Business all list APIs in Microsoft's comparison
table [S11] (corrected source: the service description [S4] does not list APIs). Plan 2 and Defender for
Business add EDR and automated investigation; Plan 1 has no EDR [S4][S11]. Which alert data a Plan 1
tenant gets through the alerts API was not confirmed (unverified: not stated). Data is kept 180 days [S12],
but the comparison table marks six month retention as a Plan 2 feature only [S11], so retention on Plan 1
and Defender for Business is unclear (unverified).
Device groups exist in Plan 1 and Plan 2 [S1].

## 3. Customer setup guide (draft product text)

1. Connect Microsoft 365 first. Open it and choose **Add endpoint protection (Defender)**.
2. Accept the extra read permissions: machines and alerts. Verity cannot isolate machines or close alerts.
3. Choose which device groups are in scope. Servers count too.
4. Set how old an alert may be before it must be closed (defaults: critical 3 days, high 7, medium 30).

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Machines | `GET /api/machines` [S1] | `id`, `computerDnsName`, `aadDeviceId`, `osPlatform`, `version`, `osBuild`, `healthStatus` (Active, Inactive, ImpairedCommunication, NoSensorData, NoSensorDataImpairedCommunication, Unknown), `onboardingStatus` (onboarded, CanBeOnboarded, Unsupported, InsufficientInfo), `firstSeen`, `lastSeen` (last full device report, sent about every 24 hours), `rbacGroupName`, `machineTags`, `lastIpAddress` [S6] | `$top` up to 10,000, `$skip`; 100 calls a minute and 1,500 an hour [S1] | devices last seen within the tenant's retention period [S1]; inactive device data kept up to 180 days [S12] |
| Antivirus health | `GET /api/deviceavinfo` [S7] | `avMode` (a string: `0` Active, `1` Passive, `2` Disabled, `3` or empty Other, `4` EDRBlocked, `5` PassiveAudit), `avIsSignatureUpToDate`, `avIsEngineUpToDate`, `avIsPlatformUpToDate` (each `True`, `False` or `Unknown`), quick scan time, `lastSeenTime` [S13] | `$top` up to 10,000 (default page 20), `@odata.nextLink`; 30 calls a minute and 1,000 an hour [S7]. Snapshot only, no history [S7] | current state |
| Alerts | `GET /api/alerts` [S3] | `id`, `machineId`, `severity` (UnSpecified, Informational, Low, Medium, High), `status` (Unknown, New, InProgress, Resolved), `classification` (TruePositive, InformationalExpectedActivity, FalsePositive), `determination`, `assignedTo`, `alertCreationTime`, `lastUpdateTime`, `resolvedTime`, `incidentId` (all names confirmed [S3]) | `$top` up to 10,000, `$skip`; 100 calls a minute and 1,500 an hour [S3] | alerts last updated within the retention period [S3]; Defender for Endpoint keeps data 180 days [S12] |
| Alternative: Graph alerts | `GET /v1.0/security/alerts_v2` | `status`, `classification`, `determination`, `assignedTo`, `createdDateTime`, `resolvedDateTime`, `serviceSource`, device evidence [S3] | `@odata.nextLink` | as above |

Fallback for a tenant with Defender Antivirus but no Defender for Endpoint licence: the Intune
`DefenderAgents` report (DeviceId, RealTimeProtectionEnabled, MalwareProtectionEnabled,
SignatureUpdateOverdue, TamperProtectionEnabled, ProductStatus, LastReportedDateTime) [S8] or the
`windowsProtectionState` relationship on each managed device [S9]. That is antivirus state, not EDR.

## 5. Checks

### 5.1 Existing checks

| Check | Feasible | How | Gaps |
|---|---|---|---|
| `endpoint.protection_active` | yes | `onboardingStatus` onboarded, `healthStatus` Active, `lastSeen` within the window, and from AV health: `avMode` active (or passive only where a third party AV is the protection, per setting), signatures and engine up to date | `lastSeen` is the last full report, not the UI's last seen [S6]; the window must allow at least 24 hours plus margin (default 7 days) |

### 5.2 New checks

| Check (NEW) | Feasible | How | Gaps |
|---|---|---|---|
| `endpoint.coverage_complete` | yes, with an MDM | Every MDM device in contact matches a machine by `aadDeviceId` (Intune) or by hostname and serial (other MDMs; serial is not in the machine resource as read: match on hostname then MAC, weaker) | Non Entra joined devices match on name only: results say so |
| `endpoint.servers_covered` | yes, with Verity assets | Server assets matched by hostname or IP to machines | Cloud instances need the cloud resource id, not on the machine resource |
| `endpoint.prevention_enabled` | partial | `avMode` active (`0`) means blocking; `4` shows EDR in block mode [S13]; tamper protection from Intune `windowsProtectionState.tamperProtectionEnabled` [S9] or the Intune report [S8] | Attack surface reduction settings live in policies not read here (unverified: not researched) |
| `endpoint.detections_triaged` | yes | Alerts in the window with status, assignee, classification and resolved time | No status history: time to triage cannot be measured, only that nothing stays New past the limit |

## 6. Artifacts and objectives it fills

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `inventory-of-company-devices` (protection coverage part, strategy section 4 split) | EP-01.B | EP-01 | check only today -> person + `endpoint.protection_active`, `endpoint.coverage_complete` |
| `asset-inventory` | EP-01.B | EP-01 | adds `endpoint.servers_covered` |
| `alerts-that-were-reviewed-and-acted` | EP-01.C, EP-01.D | EP-01 | person -> person + `endpoint.detections_triaged` (partial: D needs the incident register) |

## 7. Framework reach

EP-01: SOC 2 CC6.8; ISO 27001:2022 A.8.1, A.8.7, A.8.16. LM-04 (through `endpoint.detections_triaged`):
CC7.3; A.5.25, A.8.16. All partial.

## 8. Limits and false assurance traps

- **Passive mode.** Defender Antivirus in passive mode does not block. A machine can be onboarded and
  healthy while nothing prevents malware. `avMode` decides, not onboarding.
- **Inactive is not gone.** An Inactive machine may be a laptop on holiday or a reimaged one with a new
  id. Match on `aadDeviceId` and hostname before calling it missing.
- **Resolved is not handled.** An alert auto resolved by automated investigation has a resolved time
  but maybe no person. The check records `assignedTo` and classification and says when they are empty.
- **Retention.** Alerts older than the retention window cannot be read; a Type 2 period longer than
  retention relies on Verity's own stored results.

## 9. Product and UI

Same connection as Microsoft 365; an **Endpoint protection** toggle with device group scope and the alert
age settings. Health: consent missing (checks `error`), licence missing (`error`), throttled (run
`truncated`, `insufficient`). In product guide: yes, short, because of the consent role and the passive
mode trap.

## 10. Implementation notes

Token for resource `https://api.securitycenter.microsoft.com/.default`: Microsoft says some Defender for
Endpoint APIs still need tokens for that legacy resource and return 403 otherwise, even though the calls
go to `api.security.microsoft.com` [S7][S1]. Respect 100 calls a minute: one machines call with
`$top=10000` and paging covers most tenants. Fixtures: an onboarded active machine, a passive mode
machine, an inactive one, alerts in New, InProgress and Resolved. Error mapping as for Intune. A 404 on
List machines means no recent machines [S1]: record as an empty population with that reason, which is
`insufficient` unless the MDM also shows no Windows or Mac devices.

## 11. How comparable platforms do it

Vanta has a Defender for Endpoint integration: read only, consent by a Global Administrator or
Privileged Role Administrator; it reads onboarded devices with health status, risk score and exposure
level, and vulnerability findings (search summary of Vanta's page; exact permissions are on the app's API
permissions tab: unverified) [S14]. Vanta's Intune page says it reads antivirus settings through Intune
[S10]. Drata, Secureframe and Sprinto Defender integrations were not researched (unverified).

## 12. Sources

- [S1] List machines API: https://learn.microsoft.com/en-us/defender-endpoint/api/get-machines
- [S2] Grant tenant wide admin consent: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent
- [S3] Alerts: https://learn.microsoft.com/en-us/defender-endpoint/api/alerts, https://learn.microsoft.com/en-us/defender-endpoint/api/get-alerts, https://learn.microsoft.com/en-us/defender-endpoint/api/get-user-related-alerts, https://learn.microsoft.com/en-us/graph/api/security-list-alerts_v2?view=graph-rest-1.0
- [S4] Microsoft Defender service description: https://learn.microsoft.com/en-us/office365/servicedescriptions/microsoft-365-service-descriptions/microsoft-365-tenantlevel-services-licensing-guidance/microsoft-defender-service-description
- [S5] Defender for Business FAQ: https://learn.microsoft.com/en-us/defender-business/mdb-faq
- [S6] Machine resource type: https://learn.microsoft.com/en-us/defender-endpoint/api/machine
- [S7] Export device antivirus health: https://learn.microsoft.com/en-us/defender-endpoint/api/device-health-export-antivirus-health-report-api
- [S8] Intune reports (DefenderAgents): https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/reports-export-graph-available-reports
- [S9] windowsProtectionState: https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-windowsprotectionstate?view=graph-rest-1.0
- [S10] Vanta, connecting Intune: https://help.vanta.com/en/articles/11345786-connecting-vanta-microsoft-endpoint-manager-intune-mdm
- [S11] What is Defender for Business (comparison with Defender for Endpoint plans): https://learn.microsoft.com/en-us/defender-business/mdb-overview
- [S12] Defender for Endpoint data storage and privacy (retention): https://learn.microsoft.com/en-us/defender-endpoint/data-storage-privacy
- [S13] Device antivirus health properties (avMode codes): https://learn.microsoft.com/en-us/defender-endpoint/api/device-health-api-methods-properties
- [S14] Vanta, connecting Defender for Endpoint: https://help.vanta.com/en/articles/16988266-connecting-vanta-microsoft-defender-for-endpoint
