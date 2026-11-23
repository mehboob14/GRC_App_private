# SentinelOne Singularity

| | |
|---|---|
| Capabilities | endpoint_protection |
| Delivery phase | Not in the signed catalogue. `capabilities.json` lists `sentinelone` as `not_planned` (decision D-DEV-1) |
| Auth model | API token of a console user or service user, sent on every call as `Authorization: ApiToken <token>` [S2] |
| Shares setup with | Nothing |
| Go library | No official Go SDK found. Plain REST |

Check definitions: [mdm-and-endpoint-strategy.md section 5](../mdm-and-endpoint-strategy.md#5-check-catalogue).

**Verification status.** SentinelOne's API reference is served inside the customer's management console
and needs a login. This round could not read it. SentinelOne's own (archived, unsupported) integration
examples on GitHub confirm the header and the `/web/api/v2.1/` base path [S2]. Everything else not marked
as read from a source comes from the Cortex XSOAR integration documentation (Palo Alto Networks, a third
party that calls the API) [S1] or Vanta's setup guide [S3], or is marked unverified. Confirm every endpoint, field and role against the console's
API documentation before building.

## 1. What it proves

SentinelOne lists every agent with its computer name, OS, machine type, site and group, whether it is
active, its network status, last active date, agent version, whether it is decommissioned, and how many
threats it holds [S1]. Policies set whether the agent protects (mitigates) or only detects, and whether
anti tamper is on (unverified: login required). Threats carry mitigation status, classification, confidence, created
date, and incident status and analyst verdict, which XSOAR uses as filters and update fields [S1].

## 2. Connecting: method, credentials and permissions

### 2.1 Method

The customer creates a service user (preferred over a person's token, which ends when the person leaves)
with a read only role, scoped to the account or the sites in scope, and generates its API token. Verity
stores the management URL (for example `https://usea1.sentinelone.net`, format seen in [S1]) and the
token. API version 2.1: SentinelOne's example code calls `<console>/web/api/v2.1/` [S2] (XSOAR tested 2.0
and 2.1 [S1]). The service user's expiry date is chosen when it is created and its token is shown only
once (Vanta's guide [S3]); the console's own token rules need a login (unverified).

### 2.2 Permissions

| Role or permission | Read only | Needed for | Who can grant |
|---|---|---|---|
| Service user with a view only role at account or site scope: Vanta uses a custom role with view rights on endpoints, applications, console users and endpoint policy, set up by an Admin [S3]; whether a built in Viewer role fits needs the console (unverified) | yes | every endpoint.* check: agents, policies, threats | an account or site Admin |

Not requested: any role that can mitigate threats, disconnect agents or change policies.

### 2.3 Plans

Which Singularity tiers expose the API: unverified (no public page; console or sales).

## 3. Customer setup guide (draft product text)

1. In the SentinelOne console, open Settings, Users, Service Users and create a service user named "Verity"
   with a view only role for your account (or for each site in scope), and an expiry date [S3].
2. Copy its API token now: it is shown once.
3. In Verity, paste your console address and the token. Pick the sites and groups in scope.
4. Set a reminder: Verity warns you before the token expires.

## 4. What Verity collects

| Resource | API (unverified unless cited) | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Agents | `GET /web/api/v2.1/agents` (path unverified: login required) | computer name, OS name and revision, machine type (laptop, desktop, server), site, group, is active, network status, last active date, agent version, is decommissioned, threat count, encrypted applications, serial number, up to date flag, mitigation mode, infected. Corrected: XSOAR's output [S1] shows computer name, OS name, machine type, site, active, network status, last active date, agent version, decommissioned, threat count and encrypted applications; group, OS revision, serial number, up to date, mitigation mode and infected are not in it, and no raw field names are confirmed by SentinelOne (unverified: login required) | cursor paging (unverified: a third party reports `pagination.nextCursor` sent back as `cursor`) | unverified |
| Policies | account, site and group policy endpoints | mitigation mode (protect or detect) for malicious and suspicious, anti tamper (unverified: login required) | | current |
| Threats | `GET /web/api/v2.1/threats` (path unverified: login required) | id, agent id, created date, mitigation status, classification, confidence level [S1]; incident status (XSOAR uses unresolved, in_progress, resolved) and analyst verdict (XSOAR uses undefined, true_positive, false_positive, suspicious) [S1] (values unverified from SentinelOne) | cursor paging | unverified |

## 5. Checks

| Check | Feasible | How | Gaps |
|---|---|---|---|
| `endpoint.protection_active` (existing) | yes | active, last active within the window, not decommissioned, agent version supported, up to date | field names to confirm |
| `endpoint.coverage_complete` (NEW) | yes, with an MDM | match on serial number (if the agent reports it), then computer name | serial availability unverified (login required) |
| `endpoint.servers_covered` (NEW) | yes, with Verity assets | machine type server, match by name or IP | |
| `endpoint.prevention_enabled` (NEW) | likely | effective policy mitigation mode protect, anti tamper on | policy inheritance (account, site, group) must be resolved per agent |
| `endpoint.detections_triaged` (NEW) | yes | threats in the window by incident status and analyst verdict | no status history |

## 6. Artifacts and objectives it fills

As CrowdStrike: device protection coverage (EP-01.B), server coverage through the asset inventory
(EP-01.B), reviewed alerts (EP-01.C, partial for EP-01.D).

## 7. Framework reach

EP-01: SOC 2 CC6.8; ISO 27001:2022 A.8.1, A.8.7, A.8.16. LM-04: CC7.3; A.5.25, A.8.16. All partial.

## 8. Limits and false assurance traps

- **Detect mode** agents protect nothing; the policy decides.
- **Decommissioned agents** disappear from the default view; include them with their state.
- **A person's token** stops working when that person leaves or their role changes; insist on a service
  user.
- **Unverified fields** are the main risk here: the first build must start from recorded console
  responses, not from this table.

## 9. Product and UI

Connect form: console URL, API token. Settings: sites and groups in scope, servers in or out, alert age
limits, token expiry date. Health: token expired (`error` with renewal hint), role too narrow (missing
sites: `insufficient`), throttled. In product guide: yes.

## 10. Implementation notes

REST client with the shared limiter, cursor paging to the end, fixtures recorded from a partner console.
Test account: a SentinelOne partner or trial console (availability unverified: not checked).

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | Service user with a custom view only role; reads hosts, prevention policies, users and vulnerabilities [S3] | groups have a secure prevention policy, alerts handled, vulnerabilities handled |
| Drata, Secureframe, Sprinto | No public guide found in this round (unverified) | |

## 12. Sources

- [S1] Cortex XSOAR SentinelOne v2 integration (third party, Palo Alto Networks): https://xsoar.pan.dev/docs/reference/integrations/sentinel-one-v2
- [S2] SentinelOne integration examples (archived, marked not officially supported): https://github.com/Sentinel-One/s1-integration-examples
- [S3] Vanta, connecting SentinelOne: https://help.vanta.com/en/articles/11345695-connecting-vanta-sentinelone
- SentinelOne API reference: inside each customer console (login required, not read).
