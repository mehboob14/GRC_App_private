# Google Workspace

| | |
|---|---|
| Capabilities | `identity_provider` (Chrome and mobile device data belongs to devices research) |
| Delivery phase | Phase 2 for evidence (signed catalogue, section 8). Sign in through Keycloak is Phase 3 deliverable 3.2 |
| Auth model | Recommended: a Verity owned service account with domain wide delegation, authorised by the customer's super admin for read only scopes, acting as a named admin. Alternatives in section 2 |
| Shares setup with | Single sign on through Keycloak ([sso-providers.md](../../../runbooks/sso-providers.md) section 3) and the lifecycle gap there (section 6: Google pushes no SCIM). See [identity-providers-unified-setup.md](identity-providers-unified-setup.md) |
| Go library | `google.golang.org/api/admin/directory/v1`, `google.golang.org/api/admin/reports/v1` (maintenance mode), `google.golang.org/api/cloudidentity/v1`, auth through `google.golang.org/api/impersonate` or `golang.org/x/oauth2/google` [G1][G2][G3][G4][G5] |

Shared check definitions, artifacts and framework reach: [identity-checks.md](identity-checks.md).

## 1. What it proves

Read only, Google Workspace shows:

- every user: suspended or archived, super admin or delegated admin, created, deleted, last sign in, and
  whether 2 step verification is enrolled and enforced for them [W1];
- admin roles and who holds them [W2];
- the security settings Google exposes through the Policy API: password rules, 2 step verification
  enforcement and allowed factors, web session length, less secure apps, unconfigured third party app
  access [W3];
- 180 days of login, admin, SAML, OAuth token and account events [W4][W5];
- per user account facts with a few days' lag: security keys, passkeys, password length compliance,
  authorised app count [W6].

It cannot show app assignments for its own SAML apps (no endpoint found in the Directory, Reports or Cloud
Identity references; unverified), lockout settings
(not configurable), or any third party token without a scope that could also revoke it.

## 2. Connecting: method, credentials and permissions

### 2.1 The options

| Option | How | Customer does | Verity does once | Notes |
|---|---|---|---|---|
| **A. Verity service account, domain wide delegation (recommended)** | Verity's service account signs a JWT with `sub` set to a customer admin; Google issues a token for the authorised scopes [W7] | A super admin adds Verity's client ID and the scope list under API controls, Manage Domain Wide Delegation, and names the admin Verity acts as [W8] | A Google Cloud project and service account; a way to sign without a stored key (below) | No consent screen, so OAuth app verification does not apply (an inference: Google's verification pages do not mention service account delegation, while a Marketplace domain install with sensitive scopes does need verification [W13b]). Changes can take up to 24 hours [W8] |
| B. Customer service account, domain wide delegation | Same, with a service account in the customer's own project | Create a project and service account, a key, and the delegation; send the key to Verity | Nothing | One credential per customer (smaller blast radius), but a key file changes hands, and new organisations block key creation by default [W9] |
| C. Admin role on a service account (no delegation) | A role is assigned directly to the service account's email [W10] | Super admin assigns a role (any prebuilt or custom role except Super Admin; an optional expiry of up to one year) [W10]. Corrected 2026-11-23: Google states no one role limit | Same as A | Documented for the Groups API [W10][W11]; for users and Reports unverified (Google gives only the Groups example). Cannot reach the Policy API (super admin only [W12]) |
| D. OAuth by an admin (three legged) | An admin consents in Verity's external OAuth app; Verity keeps a refresh token | Sign in as an admin and approve | OAuth verification: brand (2 to 3 business days), sensitive scopes (about 10 business days, demo video, privacy policy); restricted scopes 6 weeks plus a yearly security assessment [W13][W14] | Google's restricted scope page names Gmail and Drive data as restricted and points to the verification FAQ for the current lists [W13b]; the FAQ gives only examples, so the class of each Admin SDK scope stays unverified until the scopes are added in the Cloud Console. An unverified app is capped at 100 users for the project's lifetime [W14]; Google lists admin trusted apps as an exception, which users can install whether verified or not [W14b]. The token dies with the admin's account. The Policy API setup guide documents only a service account with delegation [W26], so this route stays unverified |
| E. Marketplace app | Admin installs domain wide; required permissions are granted automatically [W7][W15] | Install from the Marketplace | OAuth verification first, then Marketplace review ("several days") [W16] | Use of Admin SDK admin scopes by Marketplace apps is not stated (unverified) |

**Recommendation: A**, with the key problem solved without a key. Google's guidance is to avoid service
account keys and sign with the `signJwt` API after authenticating through an attached service account or
workload identity federation, which accepts AWS, Azure, OIDC and SAML identities [W17][W18][W19]. Verity
runs outside Google Cloud, so it needs one of: Verity's own AWS identity (the AWS connector plan already
gives Verity one) federated into its Google Cloud project; an OIDC issuer Verity hosts; or a key, with the
`iam.managed.disableServiceAccountKeyCreation` default overridden for that one project (organisations
created on or after 3 May 2024 enforce it [W9]). Owner decision.

Google warns that delegation gives access to data of all users and can impersonate anyone, including super
admins, for the authorised scopes [W8][W20]. With A, every scope is read only, and the subject is one named
admin per customer.

### 2.2 Scopes and the admin Verity acts as

All scopes have the prefix `https://www.googleapis.com/auth/`.

| Scope | Read only | Needed for | Admin privilege of the subject |
|---|---|---|---|
| `admin.directory.user.readonly` | yes | users, 2SV fields, last sign in, suspension [W1]: `idp.mfa_enforced`, `idp.access_list_exported`, `idp.no_inactive_accounts`, `people.*` | Users: Read [W21] |
| `admin.directory.group.readonly` | yes | groups and members [W22]: `idp.access_list_exported`, role holding groups | Groups: Read [W21] |
| `admin.directory.rolemanagement.readonly` | yes | roles, privileges, assignments [W22]: `idp.admins_limited`, `idp.admin_mfa_phishing_resistant` | unverified which privilege (the privilege page names no read privilege for roles) |
| `admin.directory.orgunit.readonly` | yes | the organisational unit tree, to read per unit settings | Organizational Units: Read [W21] |
| `admin.directory.domain.readonly` | yes | domains, matched to Verity's proven domains | unverified (the privilege page names Domain Settings and Domain Management, no read only privilege) |
| `admin.reports.audit.readonly` | yes | `login`, `admin`, `token`, `saml`, `user_accounts` events [W4]: `idp.connected_apps_known`, `idp.sso_enforced`, `people.leavers_deprovisioned`, `tickets.access_requests_approved` | Reports [W21] |
| `admin.reports.usage.readonly` | yes | accounts usage parameters [W6]: `idp.admin_mfa_phishing_resistant`, `idp.password_policy`, `idp.no_inactive_accounts` | Reports [W21] |
| `cloud-identity.policies.readonly` | yes | password, 2SV, session, less secure apps, unconfigured apps settings [W3][W23]: `idp.password_policy`, `idp.session_timeout`, `idp.mfa_enforced` | **super admin only** [W12] |

Not requested: `admin.directory.user.security`. It is the only scope for listing a user's OAuth tokens and
app specific passwords, and it also allows deleting them [W24][W25]. Third party apps are read from the
token audit events and the authorised app count instead.

**The subject.** The Policy API needs a super admin [W12], and with delegation the scope must match exactly
what was authorised [W26]. So the customer chooses:

- a super admin as subject: every check can run; or
- a dedicated admin with a custom role holding only the Read privileges and Reports: the three policy
  based checks read error ("could not check: needs a super admin"), the rest run.

A dedicated admin account uses a Workspace licence; reusing a person's admin account breaks the connection
when they leave. The setup guide says both.

**Editions.** Cloud Identity Free and Premium include admin, user, SAML, OAuth and group log events, the
security and accounts reports, 2SV and API access [W27]. The Policy API is available to all Workspace
customers since 20 Feb 2025 [W28]. Reports API availability per Workspace edition is unverified (the
Reports API pages do not state it). The Policy API returns only values an admin set explicitly; an unset
setting means Google's default, which the checks must apply rather than read as missing [W12].

## 3. Customer setup guide (draft product text, option A)

1. In Verity, open Integrations, Google Workspace, **Connect evidence**. Verity shows its client ID and a
   list of scopes, each with a copy button.
2. Sign in to the Google Admin console as a super admin. Go to Security, Access and data control, API
   controls, **Manage Domain Wide Delegation**.
3. Press **Add new**. Paste Verity's client ID and the scope list exactly as shown. Press **Authorize**. If
   your organisation uses multi party approval, a second super admin approves it.
4. Choose the admin account Verity will act as. A super admin lets every check run. A dedicated read only
   admin works too, but three checks about password, 2 step verification and session settings will say
   they need a super admin.
5. Back in Verity, enter that admin's email address and your primary domain. Press **Test**. Google can
   take up to 24 hours to apply a new delegation, so a first test may need a retry.
6. If you block unconfigured third party apps, Verity's test tells you whether its client is affected
   (behaviour for delegated clients is unverified: Google's app access control page does not address
   delegated service accounts).

## 4. What Verity collects

| Resource | API | Fields kept | Paging and quotas | Provider retention |
|---|---|---|---|---|
| Users | `users.list` (`customer=my_customer`) [W1] | id, primaryEmail, suspended, suspensionReason, archived, isAdmin, isDelegatedAdmin, isEnrolledIn2Sv, isEnforcedIn2Sv, lastLoginTime, creationTime, deletionTime, orgUnitPath, changePasswordAtNextLogin | max 500 a page [W29] | until deleted |
| Groups and members | `groups.list`, `members.list` [W22] | id, email, members (id, role, type) | max 200 a page [W29] | current |
| Roles | `roles.list`, `roleAssignments.list` [W2] | role id, name, isSuperAdminRole, privileges; assignee, scope, org unit | | current |
| Org units, domains | `orgunits.list`, `domains.list` | path, parent; domain name, verified | | current |
| Policies | `GET https://cloudidentity.googleapis.com/v1/policies` with a `setting.type` filter [W23] | `security.password` (minimumLength, maximumLength, enforceRequirementsAtLogin, allowedStrength, allowReuse, expirationDuration), `security.two_step_verification_enforcement` (enforcedFrom), `..._enrollment` (allowEnrollment), `..._enforcement_factor` (allowedSignInFactorSet), `..._grace_period`, `..._device_trust`, `security.session_controls` (webSessionDuration), `security.less_secure_apps`, `api_controls.unconfigured_third_party_apps` (access_level), each with the unit or group it applies to [W3] | `pageSize` default 50, max 100 [W23] | current; only explicitly set values [W12] |
| Audit events | `activities.list` for `login`, `admin`, `token`, `saml`, `user_accounts` [W4] | id.time, actor, eventName, parameters needed by a check | `maxResults` 1000; filtered calls 250 a minute [W30] | 180 days; a start older than 180 days returns only 180 [W4][W5] |
| Account facts | `userUsageReport.get` for `all` on a date [W31] | `accounts:is_2sv_enrolled`, `is_2sv_enforced`, `is_2sv_protected`, `num_security_keys`, `num_passkeys_enrolled`, `password_length_compliance`, `num_authorized_apps`, `timestamp_last_login`, `timestamp_last_sso` [W6] | date in Pacific time | 1 to 5 days lag, 6 months in the report, 15 months through the API [W5] |

Directory quota: 2,400 queries a minute per user per project, raisable; a 429 `rateLimitExceeded` per
Workspace account cannot be raised [W29]. Reports: 2,400 a minute; 503 means quota, back off [W30].

## 5. Checks

Controls, coverage and rationale: `checks.json` for existing keys, [identity-checks.md](identity-checks.md)
section 2 for new keys.

### 5.1 Existing checks on Google Workspace

| Check | Verdict | Population | Predicate on Google | Outcomes and traps | API (scope) |
|---|---|---|---|---|---|
| `idp.mfa_enforced` | Supported | Users not suspended and not archived | Every user has `isEnforcedIn2Sv` and `isEnrolledIn2Sv` true [W1]; less secure apps off (policy or `accounts:is_less_secure_apps_access_allowed`) [W3][W6] | fail lists users; users who sign in through a third party SAML provider (seen in `timestamp_last_sso`) read insufficient, their second factor happens upstream | users, usage, policies |
| `idp.sso_enforced` | Partial | Vendor register applications | Each was signed into through Google in 180 days: a `saml` event (Google as the SAML provider) or a `token` authorise event (Sign in with Google) | no documented API lists Google's custom SAML apps or who is assigned (unverified), so an app nobody used in 180 days is invisible | audit (`admin.reports.audit.readonly`) |
| `idp.password_policy` | Partial | `security.password` per unit | `minimumLength`, strength, reuse, expiry and `enforceRequirementsAtLogin` meet the standard; `accounts:password_length_compliance` per user [W3][W6] | lockout is not a Google setting, so that item reads not applicable; error without a super admin subject | policies, usage |
| `idp.session_timeout` | Partial | `security.session_controls` per unit | `webSessionDuration` within the standard [W3] | no idle timeout exists, that item reads not applicable; error without a super admin | policies |
| `idp.admins_limited` | Supported | Users with `isAdmin` or `isDelegatedAdmin`, every role assignment (groups expanded, service accounts listed) | Each holder is an active person on Verity's approved list; super admin count within the customer's limit | `is_super_admin` and `is_delegated_admin` usage fields ended 15 Nov 2024 [W6]; use role assignments | users, roles |
| `idp.access_list_exported` | Supported | All users with groups and roles | Complete export | insufficient when truncated | users, groups, roles |
| `idp.groups_drive_access` | Not possible | | App access for Google's SAML apps is set per unit or group in the console; no read API found (unverified) | not applicable on Google, with that reason shown | |
| `idp.connected_apps_known` | Partial | OAuth clients authorised by users in 180 days (`token` events) | Each is approved in the vendor register or marked for removal; the unconfigured apps setting is recorded | tokens granted more than 180 days ago and never used since are invisible; the per user count `accounts:num_authorized_apps` flags users whose count exceeds the clients seen | audit, usage |
| `people.leavers_deprovisioned` | Partial | Leavers on the roster in the last 90 days | No user still active later than the allowed hours after the end date; time from admin audit events (`SUSPEND_USER`, `DELETE_USER`, `ARCHIVE_USER` [W35]) or Verity snapshots | insufficient without a roster; suspension is enough to stop sign in, deletion is not required | users, audit |
| `people.joiners_onboarded` | Partial | Users created in the period (`creationTime`) | Each matches a joiner whose onboarding started first | needs onboarding records | users |
| `tickets.access_requests_approved` | Partial (identity side) | Role and group change events | Supplies grants; approvals come from ticketing | 180 days of events | audit |

### 5.2 New checks on Google Workspace

| Check key (NEW) | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `idp.admin_mfa_phishing_resistant` | Holders of any admin role | `accounts:num_security_keys` or `num_passkeys_enrolled` above zero [W6], and the 2SV factor policy for their unit or group is PASSKEY_ONLY or a passkey combination [W3] | partial: usage data is 1 to 5 days late; a policy targets one unit or group through `policyQuery.orgUnit` or `policyQuery.group`, and `sortOrder` decides between policies of the same setting [W34]; error without a super admin for the policy part | daily | admin, key counts, policy | IAM-03, IAM-07 partial |
| `idp.no_inactive_accounts` | Active users older than `inactive_days` | The later of `lastLoginTime` and `accounts:timestamp_last_sso` within `inactive_days` | insufficient when truncated | daily | user, last sign in | IAM-12, IAM-02, HR-03 partial |
| `idp.machine_identities_owned` | | Not possible: service accounts and delegation clients live in Google Cloud, not the Workspace directory (no Admin SDK listing found, unverified) | not applicable | | | covered by `cloud.machine_credentials_rotated` |
| `idp.access_reviews_completed` | | Not possible: Workspace has no access review feature | not applicable | | | |
| `people.accounts_match_roster` | Active users | Matched to an active roster person, or a recorded shared or service mailbox | insufficient without a roster | daily | user, match | IAM-12, IAM-01, HR-03 partial |

## 6. Artifacts and objectives it fills

As [identity-checks.md](identity-checks.md) section 3, except: `group-and-role-membership-export` gets
`idp.access_list_exported` only (no `idp.groups_drive_access`), and no access review or machine identity
artifact changes.

## 7. Framework reach

As [identity-checks.md](identity-checks.md) section 4, without the IAM-10 and access review links.

## 8. Limits and false assurance traps

- **Enforced is per user, set by unit.** `isEnforcedIn2Sv` reflects the unit's policy. A unit with a long grace period shows enrolled users who are not yet forced.
- **Federated sign in.** When Workspace trusts another provider for sign in, Google's 2SV does not apply to that path by default; an admin can turn on 2SV and risk challenges after SSO, and super admins never sign in through SSO [W32]. Those users read insufficient until that provider is connected.
- **Tokens need a write capable scope.** Reading third party tokens directly would need `admin.directory.user.security`, which can delete them [W24]. Verity does not ask for it, so token evidence is event based and limited to 180 days.
- **Lag.** Account facts arrive 1 to 5 days late; OAuth token events a couple of hours late [W5]. A check never treats "not yet reported" as pass.
- **The subject leaves.** If the admin Verity acts as is suspended or loses a privilege, every call fails. That is a connection error, never a control failure.
- **Delegation power.** The authorised scopes apply to every user in the domain [W8]. Scopes stay read only, and the list in the console is the full list.
- **Several domains or Workspace accounts.** One delegation covers one customer account; secondary domains in it are covered, a second account is a second connection.

## 9. Product and UI

- **Connect form.** Client ID and scope list (copy buttons), the subject's email, primary domain, Test. A note that delegation can take 24 hours.
- **Scope.** The whole account; per user exclusions with a reason. Optional limit to organisational units, recorded on the evidence like GitHub's repository scope.
- **Health states.** Connected; delegation missing or scope mismatch (named); subject is not a super admin (names the three checks); subject suspended; throttled.
- **In product guide.** Yes: the delegation screen is easy to get slightly wrong (one missing scope fails the whole token request).

## 10. Implementation notes

- **Auth, keyless.** `impersonate.CredentialsConfig{TargetPrincipal, Scopes, Subject}` from `google.golang.org/api/impersonate`, which needs `roles/iam.serviceAccountTokenCreator` on the service account [G5]; the base identity comes from workload identity federation [W19]. With a key: `google.JWTConfigFromJSON(key, scopes...)` and `Subject` [G4]; Google marks the JSON credential helpers as a security risk [G4].
- **One token per scope set.** A token request for scopes that were not all authorised fails, so the probe requests each scope alone once per run to name the missing one (behaviour inferred from [W26]).
- **Paging.** `pageToken` loops. Reports date parameters are Pacific time [W31].
- **Error mapping.** `unauthorized_client` on token: delegation missing (connection error). 403 on a call: privilege missing for those checks. 429 per account or 503 on Reports: back off, then `truncated`.
- **Deletion semantics.** Suspended and archived users stay listed; deleted users disappear from the list; a deleted user can be restored for 20 days [W33], but how long `showDeleted` returns them is not stated (unverified); Verity snapshots keep the trail.
- **Fixtures.** Record from a test Workspace or Cloud Identity Free account. Seed: a user without 2SV, a unit with enforcement and a grace period, a super admin with a security key, a delegated admin through a group, a suspended user, a third party OAuth grant, a custom SAML app.

## 11. How comparable platforms do it

| Platform | Connection | Scopes | Tests named |
|---|---|---|---|
| Vanta | OAuth consent by a super admin; publishes its client IDs for customers to trust [V1] | three read only directory scopes, names not published [V1] | MFA on Google Workspace, deprovisioning, account linkage [V1] |
| Drata | OAuth by a User Management, Groups or Directory Sync admin, or a service account with domain wide delegation set by a super admin [D1] | `admin.directory.user.readonly`, `.group.readonly`, `.orgunit.readonly`, `.domain.readonly` [D1] | not listed |
| Secureframe | super admin [S1] | includes `admin.directory.user.security` and `admin.directory.rolemanagement.readonly` [S1] | not listed |
| Sprinto | OAuth by a super admin; Admin SDK, Reports, Cloud Identity and Alert Center APIs [P1] | not listed | MFA enabled [P1] |

Secureframe's list includes the write capable security scope Verity avoids. Whether any of these apps is
verified by Google is not stated (unverified).

## 12. Sources

Several Google pages now redirect to `knowledge.workspace.google.com` and `docs.cloud.google.com`.

- W1 Users resource: https://developers.google.com/workspace/admin/directory/reference/rest/v1/users
- W2 Roles and role assignments: https://developers.google.com/workspace/admin/directory/reference/rest/v1/roles and https://developers.google.com/workspace/admin/directory/reference/rest/v1/roleAssignments (link corrected 2026-11-23; it pointed at the scopes page)
- W3 Supported Policy API settings: https://docs.cloud.google.com/identity/docs/concepts/supported-policy-api-settings
- W4 activities.list: https://developers.google.com/workspace/admin/reports/reference/rest/v1/activities/list
- W5 Retention and lag: https://knowledge.workspace.google.com/admin/reports/data-retention-and-lag-times
- W6 Accounts usage parameters: https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user/accounts
- W7 Service accounts and delegation: https://developers.google.com/identity/protocols/oauth2/service-account
- W8 Domain wide delegation: https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation
- W9 Secure by default organisations: https://docs.cloud.google.com/resource-manager/docs/secure-by-default-organizations
- W10 Assign admin roles (service accounts): https://knowledge.workspace.google.com/admin/users/assign-specific-admin-roles
- W11 Groups API setup: https://docs.cloud.google.com/identity/docs/how-to/setup
- W12 Policy API overview: https://docs.cloud.google.com/identity/docs/concepts/overview-policies
- W13 Verification requirements: https://support.google.com/cloud/answer/13464321
- W13b Restricted scope verification: https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- W14 Verification timelines and user cap: https://support.google.com/cloud/answer/13463817 and https://support.google.com/cloud/answer/7454865
- W14b Verification exceptions (internal, admin trusted, service owned data): https://support.google.com/cloud/answer/13464323
- W15 Marketplace install: https://knowledge.workspace.google.com/admin/apps/install-marketplace-apps-for-your-organization
- W16 Marketplace review: https://developers.google.com/workspace/marketplace/about-app-review
- W17 Delegation best practices: https://knowledge.workspace.google.com/admin/apps/domain-wide-delegation-best-practices
- W18 Service account key practices: https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys
- W19 Workload identity federation: https://docs.cloud.google.com/iam/docs/workload-identity-federation
- W20 Service account practices: https://docs.cloud.google.com/iam/docs/best-practices-service-accounts
- W21 Admin privileges: https://knowledge.workspace.google.com/admin/users/administrator-privilege-definitions
- W22 Directory scopes: https://developers.google.com/workspace/admin/directory/v1/guides/authorizing
- W23 policies.list: https://docs.cloud.google.com/identity/docs/reference/rest/v1/policies/list
- W24 tokens.list: https://developers.google.com/workspace/admin/directory/reference/rest/v1/tokens/list
- W25 asps.list: https://developers.google.com/workspace/admin/directory/reference/rest/v1/asps/list
- W26 Policy API setup: https://docs.cloud.google.com/identity/docs/how-to/setup-policies
- W27 Cloud Identity editions: https://docs.cloud.google.com/identity/docs/editions
- W28 Policy API GA: https://workspaceupdates.googleblog.com/2025/02/policy-api-general-availability.html
- W29 Directory limits: https://developers.google.com/workspace/admin/directory/v1/limits
- W30 Reports limits: https://developers.google.com/workspace/admin/reports/v1/limits
- W31 userUsageReport.get: https://developers.google.com/workspace/admin/reports/reference/rest/v1/userUsageReport/get
- W32 2SV with third party identity providers: https://knowledge.workspace.google.com/admin/security/how-2-step-verification-works-with-third-party-idps
- W33 Restore a deleted user: https://support.google.com/a/answer/1397578
- W34 Policy resource (`policyQuery`): https://docs.cloud.google.com/identity/docs/reference/rest/v1/policies
- W35 Admin audit user settings events: https://developers.google.com/workspace/admin/reports/v1/appendix/activity/admin-user-settings
- G1 https://pkg.go.dev/google.golang.org/api/admin/directory/v1
- G2 https://pkg.go.dev/google.golang.org/api/admin/reports/v1
- G3 https://pkg.go.dev/google.golang.org/api/cloudidentity/v1
- G4 https://pkg.go.dev/golang.org/x/oauth2/google
- G5 https://pkg.go.dev/google.golang.org/api/impersonate
- V1 Vanta: https://help.vanta.com/en/articles/14977969-google-workspace-integration-guide.md
- D1 Drata: https://help.drata.com/en/articles/4663303-google-workspace-integration-guide
- S1 Secureframe: https://support.secureframe.com/en/articles/15111500-permissions-google-workspace
- P1 Sprinto: https://docs.sprinto.com/integrations/overview/google-workspace-integration.md

## Decisions for the owner

1. Option A (Verity service account) versus D (verified OAuth app). Recommended A: no Google verification, no 100 user cap, all scopes read only.
2. How Verity's service account signs without a stored key: federate from Verity's AWS identity, host an OIDC issuer, or keep a key with the default policy overridden for one project.
3. Subject: ask for a super admin (all checks) or accept a read only admin (three policy checks read "needs a super admin").
