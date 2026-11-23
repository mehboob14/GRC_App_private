# CrowdStrike Falcon

| | |
|---|---|
| Capabilities | endpoint_protection |
| Delivery phase | Not in the signed catalogue. `capabilities.json` lists `crowdstrike` as `not_planned` (decision D-DEV-1) |
| Auth model | OAuth 2.0 client credentials for an API client created in the Falcon console, with per area read scopes |
| Shares setup with | Nothing |
| Go library | `github.com/crowdstrike/gofalcon/falcon`, maintained by CrowdStrike with the open source community; its README says it is not a formal CrowdStrike product [S1] |

Check definitions: [mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue).

## 1. What it proves

Falcon lists every host with a sensor: hostname, serial number, platform, OS version, agent version,
first and last seen, status, whether the sensor runs in reduced functionality mode, whether the host is a
workstation or server, and which prevention and sensor update policies apply [S2]. Its policies say
whether the sensor blocks or only detects. Its alerts carry status, severity, owner and times. That
covers the agent, prevention and alert handling parts of EP-01 for laptops and servers.

It does not show hosts without a sensor (needs the MDM or asset inventory), nor that a confirmed
detection became an incident (EP-01.D stays with people or a ticketing source).

## 2. Connecting: method, credentials and permissions

### 2.1 Method

A Falcon administrator creates an API client with read scopes and gives Verity the client id, secret
and cloud. Verity exchanges them for a bearer token at `POST /oauth2/token`; the token lasts 30 minutes
and can be revoked with `POST /oauth2/revoke` [S7]. Cloud base URLs: US-1 `api.crowdstrike.com`, US-2
`api.us-2.crowdstrike.com`, EU-1 `api.eu-1.crowdstrike.com`, US-GOV-1 `api.laggar.gcw.crowdstrike.com`;
gofalcon also maps US-GOV-2 to `api.us-gov-2.crowdstrike.mil` [S5][S6]. gofalcon handles cloud selection.

### 2.2 Scopes

| API scope | Read only | Needed for | Who can grant |
|---|---|---|---|
| Hosts: READ | yes | `endpoint.protection_active`, `endpoint.coverage_complete`, `endpoint.servers_covered` (`/devices/combined/devices/v1`, `/devices/entities/devices/v2`, hidden hosts) [S2] | Falcon Administrator (named by Vanta's guide [S8]; CrowdStrike's role reference needs a Falcon login: unverified) |
| Prevention policies: READ | yes | `endpoint.prevention_enabled` (`/policy/combined/prevention/v1`, members) [S3] | same |
| Sensor update policies: READ | yes | `endpoint.prevention_enabled` (uninstall protection), `endpoint.protection_active` (sensor version policy): `GET /policy/combined/sensor-update/v2` carries `uninstall_protection` (ENABLED or DISABLED); members at `/policy/combined/sensor-update-members/v1` [S9] | same |
| Alerts: READ | yes | `endpoint.detections_triaged` (`/alerts/queries/alerts/v2` and entity fetch) [S4] | same |
| Host groups: READ | yes | scope selection by host group (`/devices/combined/host-groups/v1`, `/devices/combined/host-group-members/v1`) [S10] | same |

Not requested: any WRITE scope, Real time response, Hosts containment.

### 2.3 Plans

Which Falcon subscriptions include API access was not confirmed: no public CrowdStrike page states it (unverified; Falcon docs need a login).

## 3. Customer setup guide (draft product text)

1. In the Falcon console, open Support and resources (Support in some consoles), then API clients and keys [S5].
2. Add a client named "Verity" with read scopes only: Hosts, Host groups, Prevention policies, Sensor
   update policies, Alerts.
3. Copy the client id, the secret (shown once) and your cloud (for example US-1).
4. Paste them into Verity. Choose host groups in scope; servers count too.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Hosts | `GET /devices/combined/devices/v1` (FQL `filter`, `limit` 1 to 10,000, `offset` cursor from the previous `next`, `sort`, `fields`) [S2] | `device_id`, `hostname`, `serial_number`, `platform_name`, `os_version`, `agent_version`, `first_seen`, `last_seen`, `status`, `reduced_functionality_mode`, `product_type_desc`, `provision_status`, `device_policies` (prevention and sensor update policy ids and applied state), `host_hidden_status`, MAC and instance ids where present [S2] | read the limit from the `X-Ratelimit-Limit` and `X-Ratelimit-Remaining` response headers [S11]; the window and whether it is per customer are not on a public page (unverified). gofalcon can retry 429 and 5xx with backoff, off until `RetryConfig` is set [S1] | set by the customer's host retention policy (`host-retention` in `device_policies`) [S2]; its default needs a Falcon login (unverified) |
| Hidden hosts | `GET /devices/combined/devices-hidden/v1` [S2] | as above | | |
| Prevention policies | `GET /policy/combined/prevention/v1`, `GET /policy/combined/prevention-members/v1` [S3] | policy id, name, platform, enabled, `prevention_settings` (structure not shown in the examples: read from fixtures), `groups` | | current |
| Alerts | `GET /alerts/queries/alerts/v2` (FQL `filter`, `sort`, numeric `offset`, `limit` default 100 and up to 10,000, `include_hidden`) then `POST /alerts/entities/alerts/v2` [S4] | composite id, device id, severity, status, created and updated times, assignee, tactic and technique | | by subscription (unverified: no public page) |

The v1 alert query, entity and aggregate routes are deprecated in favour of v2; v3 exists only for
updates [S4]. The legacy Detects API was deprecated and decommissioned on 30 September 2025, with Alerts
as its replacement [S12].

## 5. Checks

### 5.1 Existing checks

| Check | Feasible | How | Gaps |
|---|---|---|---|
| `endpoint.protection_active` | yes | `last_seen` within the window, `status` normal (not contained or similar), `reduced_functionality_mode` not on, `agent_version` within the supported range (from the sensor update policy or a content list), `provision_status` provisioned | Supported sensor versions per platform need a source (sensor update policy tags or CrowdStrike's support matrix): decision on how Verity keeps it |

### 5.2 New checks

| Check (NEW) | Feasible | How | Gaps |
|---|---|---|---|
| `endpoint.coverage_complete` | yes, with an MDM | MDM devices matched to hosts by `serial_number`, then hostname and MAC | |
| `endpoint.servers_covered` | yes, with Verity assets | server assets matched by hostname, cloud instance id or MAC; `product_type_desc` Server | |
| `endpoint.prevention_enabled` | yes | host's applied prevention policy has machine learning prevention and quarantine on (setting ids from fixtures), and its sensor update policy has uninstall protection on | Setting ids differ per platform and change over time: version the evaluation rule |
| `endpoint.detections_triaged` | yes | alerts in the window: none still `new` after the triage limit, none open past the close limit, closed ones with an assignee | Status values are `new`, `in_progress`, `reopened` and `closed` [S13]. No status history: time to triage is bounded, not measured |

## 6. Artifacts and objectives it fills

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `inventory-of-company-devices` (protection coverage part) | EP-01.B | EP-01 | check only today -> person + `endpoint.protection_active`, `endpoint.coverage_complete` |
| `asset-inventory` | EP-01.B | EP-01 | adds `endpoint.servers_covered` |
| `alerts-that-were-reviewed-and-acted` | EP-01.C, EP-01.D | EP-01 | person -> person + `endpoint.detections_triaged` |

## 7. Framework reach

EP-01: SOC 2 CC6.8; ISO 27001:2022 A.8.1, A.8.7, A.8.16. LM-04: CC7.3; A.5.25, A.8.16. All partial.

## 8. Limits and false assurance traps

- **Detect only policies.** A healthy sensor in a policy with prevention off blocks nothing.
- **Reduced functionality mode** happens after kernel or OS updates; the host looks present but protects
  less. It fails `endpoint.protection_active`.
- **Hidden hosts** are removed from the main view by an administrator; include them in the population
  with their hidden state, never silently drop them.
- **Duplicate host ids** after reimaging: match on serial number before counting missing coverage.
- **Closed is not reviewed.** Alerts closed in bulk without an assignee are listed as such.

## 9. Product and UI

Connect form: cloud (select: US-1, US-2, EU-1, US-GOV-1, US-GOV-2), client id, secret. Settings: host groups in scope, servers in or out, alert
age limits by severity, minimum sensor version source. Health: secret invalid (`error`), scope missing
(its checks `error`), throttled (`truncated`). In product guide: yes (scopes).

## 10. Implementation notes

Use gofalcon with retries enabled for 429 and 5xx [S1]. One hosts call with `limit=10000` pages the
fleet. Fixtures: a workstation, a server, an RFM host, a hidden host, a detect only policy, alerts in each
status. Test account: a CrowdStrike partner or trial tenant (availability unverified: not checked).

## 11. How comparable platforms do it

| Platform | Auth and scopes | What they test |
|---|---|---|
| Vanta | API client with read on User Management, Hosts and Prevention Policies, optional Vulnerabilities, Alerts and Cloud Security; created by a Falcon Administrator; secret shown once [S8] | hosts have a prevention policy that is not empty, the agent runs on every workstation (with an MDM in scope) and cloud instance, detections handled within the SLA, leavers' Falcon accounts removed |
| Drata | Hosts: Read for the EDR link; Vulnerabilities: Read for Spotlight [S14] | agent presence per device |
| Secureframe, Sprinto | No public guide found in this round (unverified) | |

## 12. Sources

- [S1] gofalcon: https://github.com/CrowdStrike/gofalcon
- [S2] Hosts API collection: https://developer.crowdstrike.com/api-reference/collections/hosts/
- [S3] Prevention Policy API collection: https://developer.crowdstrike.com/api-reference/collections/prevention-policy/
- [S4] Alerts API collection: https://developer.crowdstrike.com/api-reference/collections/alerts/
- [S5] Falcon API credentials and clouds: https://developer.crowdstrike.com/falcon-mcp/getting-started/credentials/
- [S6] gofalcon cloud constants: https://github.com/CrowdStrike/gofalcon/blob/main/falcon/cloud.go
- [S7] OAuth2 API collection: https://developer.crowdstrike.com/api-reference/collections/oauth2/
- [S8] Vanta, integrating CrowdStrike: https://help.vanta.com/en/articles/11345781-integrating-vanta-crowdstrike
- [S9] Sensor Update Policy API collection: https://developer.crowdstrike.com/api-reference/collections/sensor-update-policy/ and falconpy endpoint map https://github.com/CrowdStrike/falconpy/blob/main/src/falconpy/_endpoint/_sensor_update_policies.py
- [S10] Host Group API collection: https://developer.crowdstrike.com/api-reference/collections/host-group/
- [S11] CrowdStrike SDK response headers: https://developer.crowdstrike.com/sdks/python/responses/
- [S12] Detects API collection (deprecation notice): https://developer.crowdstrike.com/api-reference/collections/detects/
- [S13] falconpy alerts endpoint map (status values): https://github.com/CrowdStrike/falconpy/blob/main/src/falconpy/_endpoint/_alerts.py
- [S14] Drata, connecting CrowdStrike: https://help.drata.com/en/articles/9175449-connecting-crowdstrike
