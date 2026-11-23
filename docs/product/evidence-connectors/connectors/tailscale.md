# Tailscale

| | |
|---|---|
| Capabilities | network_edge |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | OAuth client ("trust credential") with explicit read scopes, client credentials flow, one hour access tokens [T3] [T2] |
| Shares setup with | The identity provider: Tailscale signs people in through it and enforces no second factor of its own [T14] [T15] |
| Go library | `tailscale.com/client/tailscale/v2` (official client for the Tailscale API; supports API keys, OAuth and identity federation) [T26] |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

Tailscale is the private network many small companies use instead of a VPN. Its policy file, device
list, user list and settings show:

- internal systems sit on the tailnet (NS-11, partly);
- no rule lets everyone reach everything, and production is reached by named groups or tags (NS-11,
  IAM-08);
- the policy tests the paths into production that must stay closed, and refuses any change that opens
  them (NS-07);
- new devices need approval, and device keys expire so people sign in again through the identity
  provider (NS-11, IAM-11);
- only current staff are members (NS-11.C, IAM-12).

It does **not** prove that a system has no route in outside the tailnet (a public IP or a security group
open to the internet), that sign in used a second factor (that is the identity provider: Tailscale's API
does not expose it [T27]), or that remote sessions were reviewed. New tailnets start with an allow all
policy [T9], so a connected Tailscale account proves nothing until its policy is read.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

| Option | Fit | Notes |
|---|---|---|
| **OAuth client (trust credential)** (recommended) | yes | Client credentials at `POST https://api.tailscale.com/api/v2/oauth/token`; the access token lasts one hour and cannot be changed [T3]. The credential does not expire, is not tied to a person and keeps working if its creator leaves; it is revoked by hand [T2] [T3]. Created by an Owner, Admin, Network admin or IT admin; only Owners and Admins can grant every scope [T3] |
| API access token | fallback | Has the same rights as its owner, expires after 1 to 90 days [T4] [T1]. Sprinto uses this and asks customers to reconnect every 90 days [T28] |
| Workload identity federation | later | Exchanges a token from a cloud or CI identity at `https://api.tailscale.com/api/v2/oauth/token-exchange` with `client_id` and `jwt` [T6]. Generally available on all plans since 19 February 2026 [T31]. The customer's admin must trust the issuer and claims, and the issuer must be publicly reachable [T6]. Which admin roles can create a federated identity is not stated (still unverified) [T6] [T31] |

Tailnet id: `-` means the default tailnet of the credential [T1]. Tailnets created before October 2025
may still use a legacy id; the tailnet id is preferred [T1] [T7].

### 2.2 Scopes

Read scope names from the trust credentials reference [T2]. `all:read` is **not** used: it also grants
read access to APIs Tailscale adds later [T2], which breaks least privilege.

| Scope | Read only | Needed for (check keys) | Who can grant |
|---|---|---|---|
| `policy_file:read` (requires `devices:core:read` and `devices:posture_attributes:read` alongside it [T2]) | yes | `edge.access_policies_least_privilege`, `edge.policy_tests_defined`, `edge.devices_verified` (posture rules) | Owner or Admin |
| `devices:core:read` | yes | `edge.device_keys_expire`, `edge.zero_trust_access`, `edge.devices_verified` | Owner or Admin |
| `devices:posture_attributes:read` | yes | with `policy_file:read`; posture attributes on devices | Owner or Admin |
| `users:read` | yes | `edge.members_current`; admin role list for IAM-07 | Owner or Admin. Other admin roles can grant only scopes within their own rights (a Network admin cannot grant `devices:core`, an IT admin can) [T3]; no per scope list is published, so the setup guide asks for an Owner or Admin |
| `feature_settings:read` | yes | `edge.devices_verified` (device approval), `edge.device_keys_expire` (key duration), user approval, admin console session timeout | Owner, Admin |
| `logs:configuration:read` | yes | configuration audit log kept as change evidence | Owner, Admin |
| `logs:network:read` | yes | network flow logs (Premium and Enterprise), and the flow logging setting [T1] | Owner, Admin |
| `log_streaming:read` | yes | whether logs stream to the customer's SIEM | Owner, Admin |
| `auth_keys:read` | yes | optional: reusable and preauthorized auth keys (devices that join without a person) | Owner, Admin |
| `networking_settings:read` | yes | optional: HTTPS setting | Owner, Admin |

Legacy scope names (`acl`, `devices`, `logs:read`, ...) still work on credentials made before
14 November 2024 and map to the current ones [T2]. Verity asks only for current names.

### 2.3 Plan requirements

Current plans: Personal (free, up to 6 users), Standard, Premium, Enterprise [T5]. On 8 April 2026
Starter became Standard and Personal Plus was retired [T19].

| Feature | Plans | Source |
|---|---|---|
| Device approval, user approval | all | [T20] [T18] |
| Node key expiry (1 to 180 days, default 180, can be turned off per device; tagged devices have it off by default) | all | [T21] |
| Configuration audit log, last 90 days | all | [T12] |
| Network flow logs, last 30 days, off by default | Premium, Enterprise | [T22] |
| Log streaming | Premium, Enterprise | [T23] |
| Device posture: default attributes all plans; integrations Standard and up; custom attributes Premium and up | as stated | [T24] |
| Roles beyond Owner, Admin and Member (IT admin, Network admin, Billing admin, Auditor) | Standard and up | [T25] |
| User and group provisioning (SCIM) for Google Workspace, Entra ID, Okta | Standard and up | [T17] |

## 3. Customer setup guide (draft)

1. In the Tailscale admin console, as an Owner or Admin, open **Settings**, then **Trust credentials**,
   and create an OAuth client named "Verity (read only)".
2. Tick only the read scopes Verity lists on the connect screen. Do not tick **All** read.
3. Copy the client id and secret; the secret is shown once.
4. In Verity, open **Connections**, choose **Tailscale**, and paste the client id and secret. Leave the
   tailnet as `-` unless you manage more than one.
5. Tell Verity which tags mean production, and which internal systems should only be reachable through
   the tailnet (or let Verity take them from the asset inventory).
6. Connect your identity provider to Verity too, so it can check that members are current staff and
   that sign in needs a second factor.

Verity never changes the policy file, devices, users or settings.

## 4. What Verity collects

Base `https://api.tailscale.com/api/v2` [T1]. The API has no paging: each call returns everything [T1].

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Policy file | `GET /tailnet/{tailnet}/acl` with `Accept: application/json` [T1] | `grants`, `acls`, `groups`, `tagOwners`, `postures`, `autoApprovers`, `tests`, `sshTests`, ETag; whether the file is managed externally (from settings) | none | current version only; history from the audit log |
| Devices | `GET /tailnet/{tailnet}/devices?fields=all` [T1] | id, name, user, tags, OS, client version, update available, created, last seen, authorized, key expiry disabled, expires, external, posture identity, advertised and enabled routes | none | |
| Users | `GET /tailnet/{tailnet}/users?type=all` [T1] | id, login name, type, role (owner, admin, it-admin, network-admin, billing-admin, auditor, member), status (active, idle, suspended, needs approval, over billing limit), last seen, device count | none | |
| Settings | `GET /tailnet/{tailnet}/settings` [T1] | device approval, user approval, key duration days, network flow logging, posture collection, admin console session timeout, external policy management | none | |
| Configuration audit log | `GET /tailnet/{tailnet}/logging/configuration` with `start`, `end` [T1] | event time, actor, target, action, old and new values | no paging and no page size limit [T12]; query one day at a time | 90 days [T12] |
| Network flow logs (optional) | `GET /tailnet/{tailnet}/logging/network` with `start`, `end` [T1] | node, start, end, traffic counts | none | 30 days, Premium and Enterprise [T22] |
| Log streaming | `GET /tailnet/{tailnet}/logging/{logType}/stream` and `/stream/status` [T1] | destination type, status | | |
| Keys (optional) | `GET /tailnet/{tailnet}/keys?all=true` [T1] | type, created, expires, revoked, reusable, ephemeral, preauthorized, tags | | auth keys expire after 1 to 90 days [T13] |

Rate limits: confirmed 2026-11-23 that no numbers are published. The OpenAPI spec defines a 429 answer
(used on the device attribute calls) and states only one limit, one invite resend per minute [T1]; the
API overview and OAuth client pages say nothing on rate limits [T4] [T3].

Settings scopes: `feature_settings:read` shows most settings; `networkFlowLoggingOn` also needs
`logs:network:read`, `httpsEnabled` needs `networking_settings:read`, and the external policy management
fields need `policy_file:read` [T1].

## 5. Checks

Period: daily state checks; each daily result is the record for that day. Production means the tags
the customer marks.

| Check | Population | Predicate | Pass, fail, error, insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `edge.zero_trust_access` (existing) | Internal systems the customer lists, or asset inventory systems marked as reached through the tailnet | Each is a tailnet device or sits inside an enabled subnet route | pass (tailnet side only; the result names the cloud checks for other routes); fail: list; insufficient: no systems listed | daily | systems matched to devices or routes | NS-11 (propose partial) |
| NEW `edge.access_policies_least_privilege` | The policy file | No ACL rule from `*` to `*:*` and no grant from `*` to `*` on all ports; every rule whose destination includes a production tag names groups, tags or users, not `*` and not all members (configurable) | pass; fail: list of rules; error: scope missing; insufficient: policy unparsable | daily | policy file version (ETag), flagged rules | NS-11 partial, IAM-08 partial |
| NEW `edge.policy_tests_defined` | The policy file and the production tags | For each production tag, at least one test expects traffic to it to be denied from a source that should not reach it. Tailscale rejects a policy change that makes a test fail [T30] | pass; fail: tags without a deny test; insufficient: no production tag marked | daily | tests per tag | NS-07 partial |
| NEW `edge.devices_verified` | Tailnet settings, and rules into production when the standard asks for posture | Device approval is on; where the workspace standard requires a device check, rules into production carry a posture condition | pass; fail; error | daily | settings, posture conditions | NS-11 partial |
| NEW `edge.device_keys_expire` | Devices of people (untagged) and the tailnet key duration | Key duration at most the workspace standard (default 180 days, the maximum [T21]); no person's device has expiry turned off unless left out with a reason. Tagged server devices are listed, not judged | pass; fail: list; error | daily | key duration, devices with expiry off | NS-11 partial, IAM-11 partial |
| NEW `edge.members_current` | Users of type member with status active or idle | Each login name is an active user in the connected identity provider | pass; fail: members unknown to or suspended in the identity provider; insufficient: no identity provider connected | daily | members and their identity provider status | NS-11 partial, IAM-12 partial |

Full definitions: [operations-checks.md](operations-checks.md) section 3.4.

Additional evidence kept, not judged: the configuration audit log (each policy, settings and device
approval change, pulled daily because only 90 days are kept), attached to an edge check result when it
changes outcome; the admin console session timeout (IAM-11.B for the admin tool); whether network flow
logging and log streaming are on (NS-11.D, LM-02); holders of admin roles for the privileged access list
([operations-checks.md](operations-checks.md) section 6). Where the policy file is managed in git
(external management on), its changes are reviewed through the version control checks, and the
evidence says so.

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `remote-access-settings-and-members` | NS-11.B, NS-11.C, NS-11.D, NS-08.D | NS-11 | person + `edge.zero_trust_access`, `edge.access_policies_least_privilege`, `edge.devices_verified`, `edge.device_keys_expire`, `edge.members_current` (partial each; the second factor comes from `idp.mfa_enforced`) |
| `segmentation-test-results` | NS-07.B, NS-07.D | NS-07 | person + `edge.policy_tests_defined` (partial: tests inside the tailnet) |
| `session-limit-settings-export` | IAM-11.B | IAM-11 | person + `edge.device_keys_expire` (partial: remote access only) |
| `group-and-role-membership-export` | IAM-08.B | IAM-08 | person + `edge.access_policies_least_privilege` (partial: shows grants go to groups; the membership export itself is the identity provider's) |

## 7. Framework reach

SOC 2: CC6.6 (NS-11), CC6.1 and CC6.6 (NS-07), CC6.1, CC6.3 and CC5.2 (IAM-08), CC6.1 (IAM-11), CC6.2
and CC6.3 (IAM-12). ISO 27001:2022: A.6.7 and A.8.21 (NS-11), A.8.20 and A.8.22 (NS-07), A.5.15, A.8.3
and A.8.4 (IAM-08), A.8.5 (IAM-11), A.5.16 and A.5.18 (IAM-12). See
[operations-checks.md](operations-checks.md) section 7.

## 8. Limits and false assurance traps

- **Second factor is not here.** Tailscale uses whatever the identity provider enforces [T15]. A pass on
  every edge check with an identity provider that allows password only sign in is still weak; NS-11.B
  needs `idp.mfa_enforced` for the same members.
- **A suspended user can stay connected.** With provisioning from the identity provider, a user
  suspended there stays signed in to Tailscale until their device keys expire [T17]. That is why key
  expiry matters for leavers, and why `edge.members_current` compares against the identity provider.
- **Tagged devices do not expire by default** [T21]. A tagged laptop escapes key expiry; the check lists
  tagged devices that look like personal machines (by OS) for review.
- **Reusable, preauthorized auth keys** let devices join without approval [T13]. They are listed with the
  device approval result.
- **The tailnet is one route among many.** Passing here says nothing about a public IP on the same
  server.
- **Docs are inconsistent** on whether user approval and provisioning can both be on [T18] [T17]; the
  checks do not depend on it.

## 9. Product and UI

- **Connect form:** OAuth client id and secret, tailnet (default `-`).
- **Scope:** production tags; internal systems (list or asset inventory); devices left out of key
  expiry with a reason.
- **Health:** credential revoked, missing scope per check, flow logs not on plan, no identity provider
  connected (for `edge.members_current`).
- **In product guide:** yes, short: where trust credentials live, which scopes, and why not All read.

## 10. Implementation notes

- **Auth.** Exchange the client id and secret for a one hour token at each run [T3]; request only the
  scopes stored for the connection.
- **No paging.** Each list returns in full [T1]; record the counts as the population.
- **Policy parsing.** Ask for JSON, not HuJSON [T1]. Both `acls` and `grants` may be present; ACLs are
  now called legacy and can coexist with grants [T11]. Evaluate both.
- **Audit log windows.** No paging or page size limit [T12], so query day by day to keep answers small.
- **Rate limits.** Unpublished; serial calls, back off on 429.
- **Fixtures.** A Personal plan test tailnet with the default allow all policy, a grants policy with
  tests, a tagged server, a device with expiry off, and a member not in the test identity provider.

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | OAuth trust credential with Users read only (write if automated removal is on) | Users only: access reviews and leaver checks [T27] |
| Sprinto | API access token (90 days) and tailnet name, created by an Admin | Users and roles: identified users, leaver access removed, access valid [T28] |
| Oneleet | OAuth with `users:read` and `devices:core:read` | Dormant users, outdated clients, unauthorized devices [T29] |
| Drata, Secureframe | still unverified (searched their help centres again 2026-11-23: no Tailscale page; both offer custom integrations instead) | unverified |

None of the public material reads the policy file or the settings. Verity's checks on allow all rules,
policy tests, device approval and key expiry are new ground.

## 12. Sources

- [T1] https://api.tailscale.com/api/v2?outputOpenapiSchema=true (official OpenAPI spec behind https://tailscale.com/api)
- [T2] https://tailscale.com/docs/reference/trust-credentials
- [T3] https://tailscale.com/kb/1215/oauth-clients
- [T4] https://tailscale.com/kb/1101/api
- [T5] https://tailscale.com/pricing
- [T6] https://tailscale.com/docs/features/workload-identity-federation
- [T7] https://tailscale.com/docs/concepts/tailnet-name
- [T8] https://tailscale.com/docs/reference/syntax/policy-file
- [T9] https://tailscale.com/docs/reference/examples/acls
- [T10] https://tailscale.com/docs/reference/examples/grants
- [T11] https://tailscale.com/kb/1324/grants
- [T12] https://tailscale.com/kb/1203/audit-logging
- [T13] https://tailscale.com/kb/1085/auth-keys
- [T14] https://tailscale.com/kb/1013/sso-providers
- [T15] https://tailscale.com/docs/multifactor-auth
- [T16] https://tailscale.com/kb/1240/sso-custom-oidc
- [T17] https://tailscale.com/docs/features/user-group-provisioning
- [T18] https://tailscale.com/kb/1239/user-approval
- [T19] https://tailscale.com/blog/pricing-v4
- [T20] https://tailscale.com/kb/1099/device-approval
- [T21] https://tailscale.com/kb/1028/key-expiry
- [T22] https://tailscale.com/kb/1219/network-flow-logs
- [T23] https://tailscale.com/kb/1255/log-streaming
- [T24] https://tailscale.com/kb/1288/device-posture
- [T25] https://tailscale.com/kb/1138/user-roles
- [T26] https://github.com/tailscale/tailscale-client-go-v2, https://pkg.go.dev/tailscale.com/client/tailscale/v2
- [T27] https://help.vanta.com/en/articles/11707697-connect-vanta-tailscale
- [T28] https://docs.sprinto.com/integrations/overview/tailscale-integration
- [T29] https://docs.oneleet.com/integrations/tailscale/
- [T30] https://tailscale.com/kb/1337/policy-syntax
- [T31] https://tailscale.com/blog/workload-identity-ga
