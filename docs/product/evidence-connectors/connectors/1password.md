# 1Password

| | |
|---|---|
| Capabilities | `password_manager` |
| Delivery phase | Phase 2 (signed catalogue, section 8: "Identity and directory ... 1Password") |
| Auth model | Two read only credentials: a Users API OAuth client (client credentials, scope `users.view` only) and an Events Reporting bearer token limited to audit events |
| Shares setup with | Nothing in Verity. Where the customer provisions 1Password from Entra, Okta or Google, the identity provider's app assignment is the provisioning source |
| Go library | None official for these APIs. Plain REST over `net/http`. The official `github.com/1password/onepassword-sdk-go` covers items and vaults through service accounts, which this connector does not need [1P9] |

Shared check definitions: [identity-checks.md](identity-checks.md). Note: 1Password's developer site moved
to `www.1password.dev`; older `developer.1password.com` links redirect there.

## 1. What it proves

- Who has a company 1Password account, and whether it is active or suspended, from the account itself
  (Users API) [1P1].
- When people joined, were suspended, reactivated or deleted, and when vault access was granted or revoked,
  group membership changed, two factor was turned on or off, or unlock with SSO was set up (audit events)
  [1P4].

Joined to a staff roster, that answers IAM-05.B and IAM-05.D: every current person has an account, and no
leaver kept one.

It cannot show, through any documented API: whether each member has two factor on (only the console's
team report holds it), the account's policies, Watchtower or Insights results, who can read which shared
vault as a complete snapshot, or whether people actually keep credentials there [1P5][1P6][1P9]. See
section 8.

## 2. Connecting: method, credentials and permissions

| Credential and scope | Read only | Needed for | Who can create it | Plan |
|---|---|---|---|---|
| Users API OAuth application, scope `users.view` [1P2] | yes (the other scopes, `users.suspend` and `users.reactivate`, are not requested; scopes are fixed when the app is created [1P2]) | member list and state: `vault.everyone_enrolled`, `vault.leavers_removed` | owner, administrator or a member of the Security group; Integrations (then Directory if other integrations exist), **OAuth Application** [1P2][1P3] | Business or Enterprise; not Teams; **not supported when the account uses 1Password's own automated provisioning** [1P3] |
| Events Reporting token, feature `auditevents` only [1P7][1P8] | yes (reporting only) | lifecycle and access events: `vault.leavers_removed` (removal time), evidence for IAM-05.D | owner or administrator, Integrations, Events Reporting, choose a SIEM or **Other**, Add Integration, Issue Token; expiry Never (default), 30, 90 or 180 days [1P7] | Business [1P7]; the setup pages name only Business, so Teams stays unverified |

Not used:

- **SCIM bridge token.** The self hosted bridge's bearer token provisions users and groups; 1Password
  offers no reduced token [1P10]. Vanta and Drata use it for "read only calls", but read only is then the
  vendor's discipline, not something 1Password enforces [V1][D1]. Verity's rule is a read only credential.
- **1Password CLI.** Lists users, groups and vault access, but authenticates as a person's account [1P11].
- **Service accounts, Connect, SDKs.** They reach items and vaults granted to them; listing users is
  "supported, but not recommended" through the CLI, groups and user operations are only planned in the SDKs
  [1P9][1P12][1P13].

**Customers on automated provisioning** (1Password hosted, from Entra, Okta, Google, JumpCloud or OneLogin
[1P10]) cannot use the Users API [1P3]. For them, membership comes from the identity provider's assignment
of the 1Password app plus audit events. The check names that source on the evidence.

**Vendor side prerequisites.** None.

## 3. Customer setup guide (draft product text)

1. In Verity, open Integrations, 1Password, **Connect evidence**. Pick where your account lives:
   1password.com, 1password.ca, 1password.eu, or the Enterprise address.
2. Sign in to your 1Password account on the web as an owner or administrator.
3. Go to Integrations (then Directory, if you already have integrations) and select **OAuth Application**
   for the Users API. Give it only the view users scope. Copy the client ID and client secret into Verity.
4. Go to Integrations, **Events Reporting**, choose **Other**, name the integration "Verity" and add it.
   Issue a token, leave only **Audit events** ticked, and choose an expiry (Verity reminds you before it
   ends). Copy the token into Verity.
5. Press **Test**. Verity confirms each credential can do only what it needs.

If your account uses 1Password's automated provisioning, skip step 3. Verity reads members through your
identity provider instead and says so.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Access token | `POST https://api.1password.com/v1/oauth/token` (regional hosts `.ca`, `.eu`, `api.ent.1password.com`) [1P2][1P14] | none kept | token lasts 900 seconds, no refresh token [1P2] | |
| Members | `GET /v1/accounts/{account}/users`, `filter=user.isActive()` or `user.isSuspended()` [1P1] | id, email, display_name, state (ACTIVE or SUSPENDED; users in any other state, such as pending, are left out), create_time [1P1] | `max_page_size` 100 by default, up to 1000, `page_token` with the same `filter`; 100 a minute, 6,000 an hour [1P1][1P14] | current |
| Token check | `GET /api/v2/auth/introspect` [1P8] | features granted (to confirm `auditevents` only) | | |
| Audit events | `POST /api/v2/auditevents` on `events.1password.com` (or `.ca`, `.eu`, `events.ent.1password.com`) [1P8][1P15] | uuid, timestamp, actor_uuid, actor_type, action, object_type, object_uuid, aux_uuid, aux_info, for user, invite, uva, gva, gm, account and sso events [1P4] | first call with a reset cursor (`limit` 1 to 1000, default 100; `start_time`, default one hour back), then the returned `cursor`; `has_more`; 600 a minute, 30,000 an hour [1P15] | the audit log in the console keeps 365 days [1P16]; the Events API reads only the last 120 days [1P18] (resolved 2026-11-23). The 90 day leaver window fits; a first run cannot backfill past 120 days |

Not collected: sign in attempts and item usage (possible later for LM-02, not needed for these checks).

## 5. Checks

### 5.1 Existing checks against 1Password

| Check | Verdict | Population | Predicate on 1Password | Outcomes and traps | API |
|---|---|---|---|---|---|
| `vault.everyone_enrolled` | Supported (needs a roster) | Active people on the staff roster (contractors as the customer's policy says) | Each has an ACTIVE 1Password member, matched by email | invited but not joined counts as not enrolled (the API leaves pending users out); insufficient without a roster; with automated provisioning, the identity provider's assignment is read instead and the evidence says so | Users API |
| `idp.mfa_enforced` | Not applicable | | Member two factor is not exposed; audit events show only changes (`enblmfa`, `disblmfa`, account wide `disblmfa`) [1P4] | 1Password owners and admins are administrators under IAM-03.C; their two factor needs the console team report uploaded by a person [1P5] | |
| `idp.sso_enforced` | Partial | 1Password as an application | The identity provider's connector shows 1Password signs in through it; audit events show unlock with SSO set up per user (`sdvcsso`) and account SSO changes [1P4] | owners cannot unlock with SSO [1P17], so they always keep a password | Events API |
| `idp.access_list_exported` | Partial | 1Password as an in scope system for access reviews | The member list is complete and dated | no vault or group access in the Users API [1P3], so the review covers accounts, not entitlements | Users API |
| `people.leavers_deprovisioned` | Not applicable | | Covered for the vault by `vault.leavers_removed` | | |

### 5.2 New checks on 1Password

| Check key (NEW) | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `vault.leavers_removed` | Leavers on the roster with an end date in the last 90 days | No ACTIVE member for the leaver later than `removal_hours` after the end date. The removal time is the `suspend` or `delete` audit event; without one, the first daily snapshot that shows the member gone or suspended | fail lists leavers and hours late; insufficient without a roster, or when neither events nor snapshots cover the end date; error on a credential problem | daily | leaver, member state, removal time, source | IAM-05 partial, IAM-12 partial |

Considered and not proposed: a check that each shared vault has an owner and team scoped members
(IAM-05.C). No read only, population complete API lists vault access for every vault [1P3][1P9]. It stays a
person's evidence, and a `NEED password_manager: every shared vault has a named owner and members that
match its team` for the reconciliation step.

## 6. Artifacts and objectives it fills

| Artifact key | Objectives | Control | Change |
|---|---|---|---|
| `password-manager-members-against-staff-list` | IAM-05.B, IAM-05.D | IAM-05 | person -> person + `vault.everyone_enrolled` + `vault.leavers_removed`. IAM-05.C stays a person |
| `removal-records-for-a-sample-of` | IAM-12.D | IAM-12 | check `people.leavers_deprovisioned` + person -> + `vault.leavers_removed` |
| `completed-offboarding-records-for-leavers-in` | IAM-05.D | HR-05 | unchanged: rotation of shared credentials after a leaver is a person's record; audit events can show the leaver's vault access was revoked |
| `second-factor-enforcement-and-enrolled-users` | IAM-03.C | IAM-03 | unchanged for 1Password: owners' two factor is a person's upload |

## 7. Framework reach

Through IAM-05: SOC 2 CC6.1, ISO 27001:2022 A.5.17. Through IAM-12: CC6.2, CC6.3, A.5.16, A.5.18. All
partial.

## 8. Limits and false assurance traps

- **An account is not use.** Membership does not show that shared or non SSO credentials live in the vault rather than in chat or spreadsheets. IAM-05.A and C stay with people.
- **Two factor is invisible** to the API. A clean membership check says nothing about it.
- **Pending invites** are not in the member list, so they read as not enrolled. Correct, but the remedy text says "accept the invite".
- **Automated provisioning** removes the Users API [1P3]. Without the identity provider connected, the vault checks read insufficient, never pass.
- **Event codes** on 1Password's audit events page are partly inconsistent (`enblmfa` and `enablmfa`; two SSO codes with swapped descriptions) [1P4]. The collector maps codes from recorded fixtures, not from the page alone.
- **Token expiry.** An Events token set to expire stops silently; health shows the date.

## 9. Product and UI

- **Connect form.** Region; Users API client ID and secret; Events token. Each tested separately, each optional with the checks it unlocks named.
- **Scope.** The whole account. Exclusions per member (service or shared accounts) with a reason.
- **Health states.** Connected; Users API unavailable (automated provisioning, falls back to the identity provider); token missing a feature or carrying extra ones (introspect); token expires on; throttled.
- **In product guide.** Yes, short: two credentials in two places of the 1Password admin console.

## 10. Implementation notes

- **Auth.** Users API: client credentials at `/v1/oauth/token`, a new token every 15 minutes [1P2]. Events API: static bearer token; call introspect at the start of each run and refuse a token whose features include more than `auditevents` (Verity asks for least privilege, and says why) [1P8].
- **Cursor.** Store the Events cursor per connection; cursors persist across sessions [1P15]. A lost cursor restarts from the last stored event time.
- **Rate limits.** Users 100 a minute; Events 600 a minute [1P14][1P15]; 429 means back off.
- **Matching.** Members match roster people by email, lower cased. A renamed email breaks the match; the evidence lists unmatched members for a person to resolve.
- **Deletion semantics.** A deleted member disappears from the list; the `delete` event and Verity's snapshot keep the date.
- **Fixtures.** Record from a 1Password Business test account: an active member, a suspended one, a deleted one, a pending invite, a vault access grant and revoke, MFA turned off and on.

## 11. How comparable platforms do it

| Platform | Connection | Reads | Tests named |
|---|---|---|---|
| Vanta | Self hosted SCIM bridge URL and bearer token, "read only calls"; Business; not possible when the bridge is tied to Google Workspace [V1] | members | not listed |
| Drata | SCIM bridge URL and token; with Google Workspace a second bridge on the same `scimsession` [D1] | users, groups, roles for access reviews [D1] | not listed |
| Sprinto | An OAuth application's client ID and secret created in 1Password Integrations [P1] (matches the Users API, an inference) | members | not listed |
| Secureframe | listed as an integration, method not documented [S1] | unverified | unverified |

No platform documents a 1Password two factor test. Verity's choice of the Users API plus an audit only
Events token is stricter than the SCIM token route Vanta and Drata use.

## 12. Sources

- 1P1 List users: https://www.1password.dev/users-api/list-users.md
- 1P2 Users API authorisation: https://www.1password.dev/users-api/authorization.md
- 1P3 Users API overview (plans, automated provisioning, not supported items): https://www.1password.dev/users-api.md
- 1P4 Audit events: https://www.1password.dev/events-api/audit-events.md
- 1P5 Two factor management: https://support.1password.com/manage-two-factor-authentication/ and reports https://support.1password.com/reports/
- 1P6 Manage organisation (what each tool does): https://www.1password.dev/get-started/manage-organization.md
- 1P7 Events API get started: https://www.1password.dev/events-api/get-started.md and https://support.1password.com/events-reporting/
- 1P8 Events API reference: https://www.1password.dev/events-api/reference/
- 1P9 SDK functionality: https://www.1password.dev/sdks/functionality.md and https://www.1password.dev/sdks.md
- 1P10 Provisioning and SCIM endpoints: https://support.1password.com/provisioning/ and https://support.1password.com/scim-endpoints/
- 1P11 CLI user commands: https://www.1password.dev/cli/reference/management-commands/user.md
- 1P12 Service accounts with the CLI: https://www.1password.dev/service-accounts/use-with-1password-cli.md
- 1P13 Connect API: https://www.1password.dev/connect/api-reference.md
- 1P14 Users API conventions: https://www.1password.dev/users-api/conventions.md
- 1P15 Events API conventions: https://www.1password.dev/events-api/conventions.md
- 1P16 Audit log (formerly activity log; keeps 365 days): https://support.1password.com/activity-log/
- 1P17 Unlock with SSO: https://support.1password.com/sso/
- 1P18 About the Events API (120 day reach): https://www.1password.dev/events-api/introduction.md
- V1 Vanta: https://help.vanta.com/en/articles/11345741-connecting-vanta-1password
- D1 Drata: https://help.drata.com/en/articles/9868870-1password-integration-guide
- P1 Sprinto: https://docs.sprinto.com/integrations/remove-integration-access/1password.md
- S1 Secureframe: https://support.secureframe.com/en/articles/15111633-supported-password-manager-integrations

## Decisions for the owner

1. Accept a SCIM bridge token (as Vanta and Drata do) for customers who want it, or keep the read only rule (recommended: keep it; offer the identity provider route instead).
2. Teams plan customers: no Users API. Support them through the identity provider route only, or not at all.
