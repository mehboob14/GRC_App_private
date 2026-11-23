# Cloudflare

| | |
|---|---|
| Capabilities | network_edge |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | Account owned API token with read permission groups only, restricted to Verity's egress addresses, with an expiry [C1] [C2] |
| Shares setup with | Nothing. Cloudflare Access may sit behind the same identity provider Verity reads (identity research) |
| Go library | `github.com/cloudflare/cloudflare-go/v7` (official; needs Go 1.26 or later) [C41]. Minor releases have changed response shapes (v7.14.0 changed rulesets and zone setting values), so pin the exact version [C41] |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

Cloudflare sits in front of public web applications and, with Zero Trust Access, in front of internal
ones. Its settings are the evidence for:

- a web application firewall with managed rules, and DDoS protection, in front of each public hostname
  (NS-10, SD-05);
- TLS 1.2 or later at the edge, HTTPS forced, HSTS sent, and the edge to origin hop encrypted with a
  verified certificate (NS-02);
- signed DNS answers (DNSSEC, NS-02);
- the origin set up to accept only edge traffic (NS-10.C, partly);
- internal applications reachable only after an identity and, where set, device check, with rules for
  named groups (NS-11, IAM-08).

It does **not** prove that every public service uses Cloudflare (a hostname not proxied, or a service on
another domain, is invisible to the edge), that the origin actually refuses traffic that bypasses the
edge, that the WAF rules were reviewed (NS-10.D), or that internal systems have no other route in. The
first and the last need the asset inventory and the cloud connector.

## 2. Connecting: method, credentials and permissions

### 2.1 Method

| Option | Fit | Notes |
|---|---|---|
| **Account owned API token** (recommended) | yes | Acts as a service principal and keeps working after the person who made it leaves; prefix `cfat_` [C1]. Up to 500 per account [C9]. Not supported for a few products, including the Zero Trust client platform [C1]. The same matrix marks "Zero Trust Devices and Services" as supported, but does not say which of the two covers the posture rules endpoint (still unverified: the connect test probes it) [C1] |
| User API token | fallback | Inherits a subset of one user's rights; stops with that user [C1] |
| Global API key | no | Full rights of the user, no expiry or address limit, labelled legacy [C8] |

Token options: client IP address filtering and an expiry date [C2] [C3]. Verify with
`GET /accounts/{account_id}/tokens/verify`, which returns status (active, disabled, expired) and expiry
[C7].

### 2.2 Permission groups

All read level. Names as on Cloudflare's permissions page [C4].

| Permission group | Read only | Needed for (check keys) | Who can grant |
|---|---|---|---|
| Zone Read | yes | all zone checks (zones, plan, status) | an account member allowed to create account API tokens ("Account API Tokens Write" for the API route [C3]). In the dashboard: a Super Administrator, or since 1 October 2026 a member with the API Token Provisioning role; either can grant only permissions they already hold [C1] [C45] |
| Zone Settings Read | yes | `edge.minimum_tls`, `edge.hsts_enabled`, `edge.origin_tls_verified` | same |
| DNS Read | yes | `edge.dnssec_enabled`, `edge.waf_enabled` (proxied records), `edge.origin_locked` | same |
| SSL and Certificates Read | yes | `edge.origin_locked` (authenticated origin pulls) [C25] | same |
| Zone WAF Read | yes | `edge.waf_enabled` (managed rules entrypoint). Accepted by the zone ruleset list and get calls [C46]; the entry point reference page lists only account level groups [C47], so the connect test still probes the entry point call and falls back to list then get by id | same |
| HTTP DDoS Managed Ruleset Read | yes | `edge.waf_enabled` (DDoS overrides). Accepted by the zone ruleset list and get calls [C46]; entry point call as for Zone WAF Read | same |
| Account Rulesets Read, Account WAF Read | yes | `edge.waf_enabled` where rules are deployed at account level | same |
| Access: Apps and Policies Read | yes | `edge.zero_trust_access`, `edge.access_policies_least_privilege`, `edge.devices_verified` | same |
| Access: Organizations, Identity Providers, and Groups Read | yes | `edge.access_policies_least_privilege` (identity providers, groups) | same |
| Access: Device Posture Read | yes | `edge.devices_verified`. The group exists and is described as read access to device posture checks [C4]; the posture rules endpoint page lists no accepted permission (confirmed 2026-11-23) [C31], so the connect test probes it | same |
| Access: Audit Logs Read | yes | Access sign in logs kept as NS-11.D evidence | same |
| Cloudflare Tunnel Read | yes | `edge.origin_locked` | same |
| Account Settings Read | yes | account audit logs (accepted by the audit log endpoints [C5] [C33]) | same |

A broader "Zero Trust Read" group is also accepted by the Access endpoints [C28] [C32]; the narrower
groups above are preferred. Narrower still, and also on the permissions page: "Access: Apps Read",
"Access: Policies Read" and "Access: Identity Providers Read" are each accepted by the matching list
endpoint [C4] [C28] [C29] [C30] (checked 2026-11-23). All names in this table were confirmed on the
permissions page [C4] that day.

### 2.3 Plan requirements

| Feature | Plans | Source |
|---|---|---|
| Free Managed Ruleset, unmetered DDoS | all zone plans; the Free Managed Ruleset is on by default on Free | [C37] [C38] |
| Cloudflare Managed Ruleset, OWASP Core Ruleset | Pro and above | [C20] |
| HTTP DDoS managed ruleset | always on, cannot be turned off; only action and sensitivity change | [C21] |
| Network layer DDoS | always on, all plans | [C22] |
| HSTS, minimum TLS, Always Use HTTPS | all plans | [C13] [C16] |
| Authenticated origin pulls | all plans | [C26] |
| Per hostname minimum TLS | Advanced Certificate Manager | [C13] |
| Zero Trust | Free up to 50 users; pay as you go; contract | [C39] |
| Access log retention | Free up to 24 hours, pay as you go up to 30 days, contract up to 6 months; admin logs 18 months | [C39] [C40] |
| Account audit logs | 18 months (the dashboard shows 90 days) | [C35] |

## 3. Customer setup guide (draft)

1. In the Cloudflare dashboard, open **Manage Account**, then **API Tokens**, and create a custom token
   named "Verity (read only)".
2. Add the permission groups Verity lists on the connect screen, each at **Read**. Limit zone
   permissions to the zones in scope, or all zones in the account.
3. Under **Client IP Address Filtering**, add Verity's outbound addresses shown on the connect screen.
4. Set an expiry date, up to one year, and create the token. Copy it; it is shown once.
5. In Verity, open **Connections**, choose **Cloudflare**, and paste the token, the account id and the
   expiry date.
6. Choose the zones in scope. List your internal applications (or let Verity take them from the asset
   inventory) and mark the administrative ones.

Verity never changes a setting, rule or policy in Cloudflare.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Zones | `GET /zones` [C10] | id, name, status, paused, type, plan (marked deprecated in favour of the subscription endpoint) | `page`, `per_page` 5 to 50 | while it exists |
| Zone settings | `GET /zones/{zone_id}/settings/{setting_id}` for `min_tls_version`, `ssl`, `ssl_automatic_mode`, `always_use_https`, `security_header`, `tls_1_3` [C11] [C14] | value, editable, modified on | one call per setting; the all settings call ends on 31 March 2027 [C12] | config |
| Per hostname TLS | `/zones/{zone_id}/hostnames/settings/min_tls_version/{hostname}` [C13] | hostname, value | where Advanced Certificate Manager is used | config |
| DNSSEC | `GET /zones/{zone_id}/dnssec` [C17] | status (active, pending, disabled, pending disabled, error), modified on | | config |
| DNS records | `GET /zones/{zone_id}/dns_records` [C24] | name, type, content, `proxied`, `proxiable` | paged; the reference states `per_page` minimum 1 and maximum 5,000,000 (confirmed as written 2026-11-23, still implausible, so Verity uses a modest page size and follows `result_info`) [C24] | config |
| WAF managed rules | `GET /zones/{zone_id}/rulesets/phases/http_request_firewall_managed/entrypoint` [C18] | rules that execute a managed ruleset (Cloudflare Managed Ruleset id `efb7b8c949ac4650a09736fc376e9aee` [C19]), enabled, overrides (action, sensitivity) | | config |
| Custom WAF rules | phase `http_request_firewall_custom` [C44] | expression, action, enabled | | config |
| DDoS overrides | `GET /zones/{zone_id}/rulesets/phases/ddos_l7/entrypoint` [C21] | overrides of action and sensitivity | | config |
| Origin pulls | `GET /zones/{zone_id}/origin_tls_client_auth/settings` [C25] | enabled (zone level; global and per hostname levels also exist [C26]) | | config |
| Tunnels | `GET /accounts/{account_id}/tunnels` [C27] | id, name, status (healthy, degraded, down, inactive), deleted | the `connections` field ended 5 October 2026 [C12] | |
| Access applications | `GET /accounts/{account_id}/access/apps` [C28] | type, domain, destinations, allowed identity providers, session duration, policies (precedence, decision, include, require, exclude) | up to 1,000 per page | config |
| Access policies | `GET /accounts/{account_id}/access/policies` [C29] | decision (allow, deny, non identity, bypass), include, require, exclude, reusable, app count | | config |
| Identity providers | `GET /accounts/{account_id}/access/identity_providers` [C30] | type (for example one time PIN, Entra ID, Okta, SAML, OIDC), SCIM config presence | | config |
| Device posture rules | `GET /accounts/{account_id}/devices/posture` [C31] | type, input, schedule | | config |
| Access sign in logs | `GET /accounts/{account_id}/access/logs/access_requests` with `since`, `until` [C32] | time, user email, app, allowed, action, IP, ray id | `page`, `per_page`, `limit` | 24 hours on Free; pull at least daily |
| Account audit logs | `GET /accounts/{account_id}/logs/audit` with `since`, `before` (generally available 10 March 2026) [C5] [C35] | time, actor (email, token), action, result, resource, zone | cursor, `limit` up to 1,000 | 18 months [C35] |

Rate limits: 1,200 requests per 5 minutes per user or account token across dashboard and API, and
200 requests per second per IP; over the limit, 429 and calls blocked for 5 minutes; headers
`Ratelimit`, `Ratelimit-Policy` and `retry-after` [C9].

Legacy WAF managed rules, firewall rules and filters APIs were deprecated on 15 June 2025; use rulesets
only [C12].

## 5. Checks

In scope: active zones the customer selects; in each, proxiable records for hostnames that serve web
traffic. Period: daily state checks; each daily result is the record for that day.

| Check | Population | Predicate | Pass, fail, error, insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `edge.waf_enabled` (existing) | In scope zones and their public hostnames | Zone active and not paused; each hostname proxied; the managed WAF phase executes the Cloudflare Managed Ruleset, enabled, not overridden to log only; no DDoS override sets every rule to log only | pass; fail: unproxied hostname, no managed ruleset, detect only; fail with reason `plan` on Free zones running only the Free Managed Ruleset (owner decision 9); error: permission; insufficient: a ruleset unreadable | daily | zone, proxied records, managed rules entrypoint, DDoS overrides | NS-10 (propose partial), SD-05 partial |
| `edge.minimum_tls` (existing) | In scope zones, and per hostname overrides where present | Minimum TLS 1.2 or higher on the zone and on every hostname override; Always Use HTTPS on | pass; fail: list; error; insufficient: per hostname settings unreadable | daily | settings per zone and hostname | NS-02 partial |
| NEW `edge.hsts_enabled` | In scope zones serving web traffic | HSTS enabled with max age at least 180 days (default), and include subdomains where the workspace standard asks | pass; fail; a zone whose origin sends the header can be left out with that reason | daily | HSTS setting per zone | NS-02 partial |
| NEW `edge.origin_tls_verified` | In scope zones | Encryption mode is Full (strict), or `origin_pull`, which is Strict (SSL-Only Origin Pull), an Enterprise mode that validates the origin certificate as Full (strict) does and always uses TLS to the origin [C48] | pass; fail: off, Flexible or Full; insufficient: automatic mode on (`ssl_automatic_mode` is `auto`, not `custom` [C49]) where the reported value may not be the effective one. (Corrected 2026-11-23: was insufficient on `origin_pull` because its meaning was unverified; it now counts as pass. Check key and mapping unchanged) | daily | `ssl` and `ssl_automatic_mode` per zone | NS-02 partial |
| NEW `edge.dnssec_enabled` | In scope zones using Cloudflare as their DNS | DNSSEC status active | pass; fail: disabled, pending (DS record not at the registrar), error | daily | status per zone | NS-02 partial |
| NEW `edge.origin_locked` | Proxied hostnames in scope | Served through a healthy tunnel (hostname to tunnel mapping via the DNS record target: a CNAME to `<tunnel id>.cfargotunnel.com` [C50]; a tunnel reached through a load balancer endpoint does not show in the record and reads insufficient), or authenticated origin pulls on at zone or hostname level (the global level uses a certificate shared by all Cloudflare accounts, so it does not count [C26]) | pass (edge side only); fail: neither; insufficient: a tunnel's health unreadable. The result says the origin side needs the cloud check | daily | tunnels, origin pull settings | NS-10 partial |
| `edge.zero_trust_access` (existing) | Internal applications the customer lists, or asset inventory systems marked internal with a hostname | Each hostname is a destination of an Access application with at least one allow policy that requires an identity | pass; fail: list; insufficient: no internal applications listed | daily | applications, destinations, policies | NS-11 (propose partial) |
| NEW `edge.access_policies_least_privilege` | Access applications of type self hosted, SSH, RDP and VNC | No allow policy includes everyone without a require rule naming a group, the company email domain or an identity provider group; no bypass on the whole application unless marked public with a reason; allowed identity providers exclude one time PIN unless a reason is recorded | pass; fail: list of rules; error | daily | policies flagged | NS-11 partial, IAM-08 partial |
| NEW `edge.devices_verified` | Access applications the customer marks administrative | At least one allow policy requires a device posture rule | pass; fail; error: posture permission; insufficient: no application marked | daily | policies and posture rules | NS-11 partial |

Full definitions: [operations-checks.md](operations-checks.md) section 3.4.

Additional evidence kept, not judged: Access sign in logs (who reached which internal application,
daily, for NS-11.D) and account audit log entries for any setting a check reads, attached to the result
when that check changes outcome, so a regression shows who made it and when (LM-03.C).

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `public-endpoint-tls-scan` | NS-02.B, NS-02.C, NS-02.E | NS-02 | person + `edge.minimum_tls`, `edge.hsts_enabled`, `edge.origin_tls_verified` (partial: settings, not a scan; NS-02.E certificate expiry not covered, the edge certificate endpoints were not researched) |
| `review-of-web-application-firewall-rules` | NS-10.B, NS-10.C, NS-10.D | NS-10 | person + `edge.waf_enabled`, `edge.origin_locked` (partial; NS-10.D review stays with people) |
| `remote-access-settings-and-members` | NS-11.B, C, D, NS-08.D | NS-11 | person + `edge.zero_trust_access`, `edge.access_policies_least_privilege`, `edge.devices_verified` (partial) |
| `evidence-validation-was-tested` | SD-05.B | SD-05 | unchanged; a firewall setting is not a validation test |

## 7. Framework reach

SOC 2: CC6.7 (NS-02), CC6.6 (NS-10, NS-11), PI1.2 (SD-05), CC6.1, CC6.3 and CC5.2 (IAM-08). ISO
27001:2022: A.8.21, A.8.24 and A.5.14 (NS-02), A.8.21 (NS-10), A.8.26 and A.8.28 (SD-05), A.6.7 and
A.8.21 (NS-11), A.5.15, A.8.3 and A.8.4 (IAM-08). All partial except where the requirement mapping is
full; see [operations-checks.md](operations-checks.md) section 7.

## 8. Limits and false assurance traps

- **The edge only knows what is proxied.** A hostname with proxying off, or a service on a domain not in
  Cloudflare, has no WAF. The check fails unproxied in scope hostnames, and the asset inventory must list
  the rest.
- **DDoS is always on.** There is no off switch to check [C21] [C22]; the evidence is that hostnames
  are proxied and no override weakens the rules.
- **Origin lock is half visible.** Cloudflare can present a client certificate or use a tunnel; only
  the origin or its firewall can refuse other traffic.
- **Free plan WAF is narrower.** The Free Managed Ruleset is not the full managed ruleset [C20].
- **Zero Trust Free keeps sign in logs for 24 hours** [C39]. A missed daily run loses that day.
- **Setting values change shape.** The Go library changed zone setting value types in a minor release
  [C41]; parse defensively and fail closed to insufficient information, never pass.
- **Automatic SSL/TLS mode** may report a value that is not the effective mode (still unverified: the
  docs say an upgrade rolls out to a growing share of traffic and never lowers the mode, but not what
  the `ssl` setting reports during the rollout) [C14] [C49].

## 9. Product and UI

- **Connect form:** account id, account API token, expiry date; Verity's egress addresses shown for the
  IP filter.
- **Scope:** zones in or out with a reason; internal applications (list or from the asset inventory);
  administrative applications; hostnames left out (for example HSTS set at the origin) with a reason.
- **Health:** token expired or disabled (verify endpoint), missing permission per check, plan limits
  (Free zone WAF), Access log retention warning on Zero Trust Free.
- **In product guide:** yes. Thirteen permission groups at read level are easy to get wrong.

## 10. Implementation notes

- **Auth.** Bearer token. Verify first; a disabled or expired token ends the run as `error` on every
  check.
- **Settings one by one.** The batch settings endpoint was deprecated on 23 April 2025 and ends on
  31 March 2027 [C12].
- **Rate limits.** At most about 4 requests per second per token to stay under 1,200 per 5 minutes,
  which also covers dashboard use by the customer's own staff on a user token [C9]. A 429 blocks for
  5 minutes; stop the run as truncated rather than retrying in a loop.
- **Ruleset ids.** Resolve managed ruleset ids by name from `GET /zones/{zone_id}/rulesets`, not by
  hard coded ids, except the documented Cloudflare Managed Ruleset id [C19] [C6].
- **Deprecations to watch.** Zone `plan` field (use the subscription endpoint), Access
  `self_hosted_domains` (use `destinations`), old device list endpoints ended 11 November 2025 [C10]
  [C28] [C12].
- **Fixtures.** One Free and one Pro zone, a proxied and an unproxied record, HSTS off, Flexible SSL,
  DNSSEC pending, an Access application with an everyone policy, a tunnel.

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | User owned API token from the "Read all resources" template | Traffic and security rule monitoring, Workers ownership, staff access; no named WAF or TLS tests published [C42] |
| Drata | Custom API token, all read: account firewall access rules, account settings, Access identity providers and groups, zone, zone settings, firewall services, Access apps and policies, zone WAF, memberships, user details | Infrastructure and user access review; no named WAF, TLS or DDoS tests published [C43] |
| Secureframe | Scoped account or user API token with Account Settings Read; Global API Key refused [C51] | Collects resources for its tests; no named tests on the public page [C51] |
| Sprinto | API key with admin access for access review; a "Read all resources" template token for infrastructure [C52] | Users, roles and two factor status for access reviews; zone and firewall configuration [C52] |

Verity's design uses an account owned token (not tied to a person), an IP filter and named checks for
each setting.

## 12. Sources

- [C1] https://developers.cloudflare.com/fundamentals/api/get-started/account-owned-tokens/
- [C2] https://developers.cloudflare.com/fundamentals/api/get-started/create-token/
- [C3] https://developers.cloudflare.com/api/resources/accounts/subresources/tokens/methods/create/
- [C4] https://developers.cloudflare.com/fundamentals/api/reference/permissions/
- [C5] https://developers.cloudflare.com/api/resources/accounts/subresources/logs/subresources/audit/methods/list/
- [C6] https://developers.cloudflare.com/api/resources/rulesets/methods/list/
- [C7] https://developers.cloudflare.com/api/resources/accounts/subresources/tokens/methods/verify/
- [C8] https://developers.cloudflare.com/fundamentals/api/get-started/keys/
- [C9] https://developers.cloudflare.com/fundamentals/api/reference/limits/
- [C10] https://developers.cloudflare.com/api/resources/zones/methods/list/
- [C11] https://developers.cloudflare.com/api/resources/zones/subresources/settings/methods/get/
- [C12] https://developers.cloudflare.com/fundamentals/api/reference/deprecations/
- [C13] https://developers.cloudflare.com/ssl/edge-certificates/additional-options/minimum-tls/
- [C14] https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/
- [C15] https://developers.cloudflare.com/ssl/edge-certificates/additional-options/always-use-https/
- [C16] https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/
- [C17] https://developers.cloudflare.com/api/resources/dns/subresources/dnssec/methods/get/
- [C18] https://developers.cloudflare.com/waf/managed-rules/deploy-api/
- [C19] https://developers.cloudflare.com/waf/managed-rules/reference/cloudflare-managed-ruleset/
- [C20] https://developers.cloudflare.com/waf/managed-rules/
- [C21] https://developers.cloudflare.com/ddos-protection/managed-rulesets/http/, https://developers.cloudflare.com/ddos-protection/managed-rulesets/http/configure-api/
- [C22] https://developers.cloudflare.com/ddos-protection/managed-rulesets/network/
- [C23] https://developers.cloudflare.com/ruleset-engine/reference/phases-list/
- [C24] https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/list/
- [C25] https://developers.cloudflare.com/api/resources/origin_tls_client_auth/subresources/settings/methods/get/
- [C26] https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/
- [C27] https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/methods/list/
- [C28] https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/applications/methods/list/
- [C29] https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/policies/methods/list/
- [C30] https://developers.cloudflare.com/api/resources/zero_trust/subresources/identity_providers/methods/list/
- [C31] https://developers.cloudflare.com/api/resources/zero_trust/subresources/devices/subresources/posture/methods/list/
- [C32] https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/logs/subresources/access_requests/methods/list/
- [C33] https://developers.cloudflare.com/api/resources/audit_logs/methods/list/
- [C34] https://developers.cloudflare.com/fundamentals/account/account-security/review-audit-logs/
- [C35] https://developers.cloudflare.com/fundamentals/account/account-security/audit-logs/, https://developers.cloudflare.com/changelog/post/2026-03-10-audit-logs-v2-ga/
- [C36] https://developers.cloudflare.com/changelog/post/2026-09-30-logpush-usage-based-pricing/
- [C37] https://www.cloudflare.com/plans/network-cdn.md
- [C38] https://developers.cloudflare.com/waf/get-started/
- [C39] https://www.cloudflare.com/plans/sase-zero-trust.md
- [C40] https://developers.cloudflare.com/cloudflare-one/insights/logs/
- [C41] https://raw.githubusercontent.com/cloudflare/cloudflare-go/main/go.mod, https://github.com/cloudflare/cloudflare-go, https://github.com/cloudflare/cloudflare-go/releases
- [C42] https://help.vanta.com/hc/en-us/articles/14452242757780-Connecting-Vanta-Cloudflare, https://www.vanta.com/integrations/cloudflare
- [C43] https://help.drata.com/en/articles/5455086-cloudflare-integration-guide-infrastructure-and-uar
- [C44] https://developers.cloudflare.com/waf/custom-rules/
- [C45] https://developers.cloudflare.com/changelog/post/2026-10-01-account-api-token-provisioning/, https://developers.cloudflare.com/fundamentals/manage-members/roles/
- [C46] https://developers.cloudflare.com/ruleset-engine/rulesets-api/view/
- [C47] https://developers.cloudflare.com/api/resources/rulesets/subresources/phases/methods/get/
- [C48] https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/ssl-only-origin-pull/
- [C49] https://developers.cloudflare.com/api/resources/ssl/subresources/automatic_upgrader/methods/get/
- [C50] https://developers.cloudflare.com/cloudflare-one/faq/cloudflare-tunnels-faq/
- [C51] https://support.secureframe.com/en/articles/15111526-cloudflare
- [C52] https://docs.sprinto.com/integrations/overview/cloudflare-integration
