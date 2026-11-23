# Microsoft Entra ID and Microsoft 365

| | |
|---|---|
| Capabilities | `identity_provider` (this document); `device_management` through Intune on the same app (devices research) |
| Delivery phase | Phase 2 for evidence (signed catalogue, section 8: "Microsoft 365 and Entra ID"). Sign in through Keycloak is Phase 3 deliverable 3.2 |
| Auth model | OAuth 2.0 client credentials (app only) to Microsoft Graph, certificate credential, admin consent to application permissions |
| Shares setup with | Single sign on through Keycloak ([sso-providers.md](../../../runbooks/sso-providers.md) section 3). Kept as a separate app, see [identity-providers-unified-setup.md](identity-providers-unified-setup.md) |
| Go library | `github.com/microsoftgraph/msgraph-sdk-go` (v1.107.0, 2026-11-20) with `github.com/Azure/azure-sdk-for-go/sdk/azidentity` [39][40] |

Shared check definitions, artifacts and framework reach: [identity-checks.md](identity-checks.md).

## 1. What it proves

Entra ID is the workforce directory for Microsoft 365 customers. Read only, it can show:

- who has an account (members, guests, disabled, deleted), when each last signed in successfully;
- whether a second factor is required (security defaults or Conditional Access) and who has registered one;
- who holds administrator roles, standing or eligible through PIM;
- which enterprise apps sign in through Entra, whether access to them comes from groups, and which third
  party apps hold consented permissions;
- the configurable parts of the password, lockout and session rules;
- dated admin and lifecycle events (disable, delete, role and group changes) for up to 30 days.

It cannot show anything about systems that do not sign in through Entra, whether an approval existed,
or anything older than its log retention unless Verity kept it.

## 2. Connecting: method, credentials and permissions

**Method.** An app registration with Microsoft Graph **application** permissions (no user signs in to
collect). Two ways to own it, compared in the unified setup document: the customer registers it in their
own tenant (single tenant), or Verity publishes one multi tenant app and the customer's admin consents.
Either way the credential is a **certificate**: Microsoft recommends certificates and says secrets should
not be used in production; a secret lasts 24 months at most and Microsoft advises under 12 [35]. Verity
generates the key pair and keeps the private key; the customer uploads only the public certificate.

**Who can grant it.** Admin consent to Microsoft Graph application permissions needs Privileged Role
Administrator or Global Administrator. Cloud Application Administrator and Application Administrator can
consent to other permissions but not to Microsoft Graph app roles [33][V1].

| Permission (application) | Read only | Needed for | Licence |
|---|---|---|---|
| `User.Read.All` | yes | users and deleted users: `idp.access_list_exported`, `idp.no_inactive_accounts`, `people.*`, populations for every user check [1][47] | Free |
| `AuditLog.Read.All` | yes | `signInActivity` [2], `userRegistrationDetails` [4], directory audits [22]: `idp.mfa_enforced`, `idp.admin_mfa_phishing_resistant`, `idp.no_inactive_accounts`, `people.leavers_deprovisioned`, `tickets.access_requests_approved` | `signInActivity` and sign in logs need P1 or P2 [2][21]. The registration report also needs P1 or P2: its Graph resource page points to the activity page's licence section, which requires P1 or P2 [4][5] (verified 2026-11-23; the exact error a Free tenant gets is untested) |
| `Policy.Read.All` | yes | Conditional Access policies and named locations [6][49], security defaults [7], authentication methods policy and strengths [9][10], idle timeout policy [30]: `idp.mfa_enforced`, `idp.admin_mfa_phishing_resistant`, `idp.session_timeout` | Conditional Access needs P1; risk based policies P2 [8] |
| `RoleManagement.Read.Directory` | yes | role definitions and assignments, PIM eligible and active schedules (it is listed as a higher permission on the PIM endpoints, so one permission covers both) [11][12]: `idp.admins_limited`, `idp.admin_mfa_phishing_resistant` | PIM needs P2 or Entra ID Governance [13] |
| `GroupMember.Read.All` | yes | groups and transitive members [14]: `idp.access_list_exported`, `idp.groups_drive_access`, role assignable groups | Free. `GroupMember.ReadBasic.All` is named least privileged on the transitive members page, but it is not listed for listing groups and is missing from the permissions reference; `GroupMember.Read.All` is listed for both [14][50][19], so ask for `GroupMember.Read.All` |
| `Application.Read.All` | yes | service principals, single sign on mode, app role assignments, app registrations, credentials and owners [15][16][17][20]: `idp.sso_enforced`, `idp.groups_drive_access`, `idp.connected_apps_known`, `idp.machine_identities_owned` | Free |
| `DelegatedPermissionGrant.Read.All` | yes | delegated consent grants: `idp.connected_apps_known` | The list page names `Directory.Read.All` as least privileged and does not name `DelegatedPermissionGrant.Read.All`, which exists in the permissions reference [18][19]. Test the narrow one first (unverified that the list call accepts it); fall back to `Directory.Read.All` only if it fails |
| `GroupSettings.Read.All` | yes | "Password Rule Settings" (banned passwords, lockout) [28]: `idp.password_policy` | Custom lockout and banned lists need P1 [26][27] |
| `Domain.Read.All` | yes | password expiry per domain, federation [25]: `idp.password_policy`, `idp.mfa_enforced` (federated domains) | Free |
| `AccessReview.Read.All` (optional) | yes | `idp.access_reviews_completed` [32] | Entra ID Governance, or P2 for features that were GA in P2 [32][13] |
| `User-LifeCycleInfo.Read.All` (optional) | yes | `employeeLeaveDateTime` as a leaver date when HR writes it [2]: `people.leavers_deprovisioned` | licence unverified: the user resource names the permission but no licence [2] |

Intune on the same app registration (devices research owns the checks) would add
`DeviceManagementManagedDevices.Read.All` (managed devices), `DeviceManagementConfiguration.Read.All`
(configuration and compliance policies) and `Device.Read.All` (Entra device objects, `isCompliant`,
`isManaged`, `approximateLastSignInDateTime`), and needs an active Intune licence [42][43].

Not requested: anything with `ReadWrite`, `Directory.Read.All` (unless the grant fallback above is
needed), `UserAuthenticationMethod.Read.All` (per user method lists; Microsoft points large reads to the
registration report instead [48]).

**Vendor side prerequisites.** For a customer owned app: none. For a Verity multi tenant app: publisher
verification (a verified Microsoft AI Cloud Partner Program account, using the Partner One ID of the partner
global account rather than a location ID; a publisher domain that is not `onmicrosoft.com`; started by
someone who holds Application Administrator or Cloud Application Administrator in Entra and CPP Partner
Admin or Account Admin in Partner Center, signed in with MFA; free, and done in minutes once those exist)
[37]. Corrected 2026-11-23: the Entra roles and the partner account type were incomplete. Unverified multi tenant apps can still receive admin consent, because risk based step up sends
user consent to an admin instead [38], but the consent screen shows the app as unverified.

## 3. Customer setup guide (draft product text)

**Option A, Verity's app (once Verity is publisher verified).**

1. In Verity, open Integrations, Microsoft, and press **Connect evidence**.
2. Sign in as a Global Administrator or Privileged Role Administrator of your Microsoft tenant.
3. Read the permissions Verity asks for. All of them read; none can change anything. Press **Accept**.
4. You return to Verity. It runs a first collection and shows which checks your licence allows.

**Option B, your own app registration.**

1. In Verity, open Integrations, Microsoft, **Connect evidence**, and choose **Use my own app**. Download
   the certificate Verity shows. It holds no secret.
2. In the Microsoft Entra admin center, go to App registrations, **New registration**. Name it
   "Verity evidence (read only)". Choose **Accounts in this organizational directory only**. Leave the
   redirect URI empty. Register.
3. Open **Certificates and secrets**, **Certificates**, **Upload certificate**, and pick the file from step 1.
4. Open **API permissions**, **Add a permission**, **Microsoft Graph**, **Application permissions**. Add
   each permission Verity lists. Press **Grant admin consent** (you need Global Administrator or Privileged
   Role Administrator).
5. Copy the **Directory (tenant) ID** and **Application (client) ID** from Overview into Verity. Press
   **Test**.
6. Verity names any permission it could not use and any check your licence does not support.

## 4. What Verity collects

All calls are `GET https://graph.microsoft.com/v1.0/...`. Verity keeps the fields listed, never secrets,
and never sign in log bodies in the first version.

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Users | `/users?$select=...` [1] | id, userPrincipalName, mail, displayName, accountEnabled, userType, externalUserState, createdDateTime, employeeHireDate, onPremisesSyncEnabled, lastPasswordChangeDateTime, passwordPolicies, signInActivity (lastSuccessfulSignInDateTime, lastSignInDateTime, lastNonInteractiveSignInDateTime) [2][3] | page max 999, or 500 with signInActivity; `$select=signInActivity` limited to 10 requests a minute [1][41] | user object lifetime; lastSuccessfulSignInDateTime only from 1 Dec 2023, not backfilled [3]; signInActivity is absent for users who never signed in or last signed in before April 2020 [2] |
| Deleted users | `/directory/deletedItems/microsoft.graph.user` [47] | id, userPrincipalName, deletedDateTime | max 999 | 30 days, then purged [46] |
| MFA registration | `/reports/authenticationMethods/userRegistrationDetails` [4] | id, userPrincipalName, isAdmin, userType, isMfaRegistered, isMfaCapable, isPasswordlessCapable, methodsRegistered, lastUpdatedDateTime | reports: 5 requests per 10 seconds per app per tenant (the throttling page does not name this report) [41] | current; up to 36 hours late; disabled and soft deleted users not listed [4][5] |
| Security defaults | `/policies/identitySecurityDefaultsEnforcementPolicy` [7] | isEnabled | | current |
| Conditional Access | `/identity/conditionalAccess/policies`, `/namedLocations` [6][49] | id, displayName, state, conditions (users, applications, clientAppTypes), grantControls (builtInControls, authenticationStrength with allowedCombinations), sessionControls (signInFrequency, persistentBrowser), modifiedDateTime | 1 request a second per tenant across all apps, 429 without Retry-After [41] | current only |
| Authentication methods | `/policies/authenticationMethodsPolicy`, `/policies/authenticationStrengthPolicies` [9][10] | method states, strengths and combinations | | current |
| Roles | `/roleManagement/directory/roleDefinitions`, `/roleAssignments?$expand=principal` [11] | role id and name, isBuiltIn, principal id and type, directoryScopeId | directory token bucket [41] | current |
| PIM | `/roleManagement/directory/roleEligibilityScheduleInstances`, `/roleAssignmentScheduleInstances` [12] | principal, role, start, end, assignment type | | current |
| Groups | `/groups`, `/groups/{id}/transitiveMembers` [14] | id, displayName, isAssignableToRole, members (id, type) | max 999 | current |
| Enterprise apps | `/servicePrincipals`, `/servicePrincipals/{id}/appRoleAssignedTo` [15][17] | id, appId, displayName, appOwnerOrganizationId, preferredSingleSignOnMode (password, saml, oidc, notSupported, may be null) [16], appRoleAssignmentRequired, accountEnabled; assignments with principalType, principalId, createdDateTime | | current |
| App registrations | `/applications`, `/applications/{id}/owners` [20] | id, appId, displayName, passwordCredentials and keyCredentials (keyId, displayName, startDateTime, endDateTime; never secretText or hint, which holds a secret's first three characters) [20], owner ids | | current |
| Consent grants | `/oauth2PermissionGrants` [18] | clientId, consentType, principalId, resourceId, scope | | current |
| Domains | `/domains` [25] | id, isVerified, authenticationType, passwordValidityPeriodInDays | | current |
| Password rules | `/groupSettings` (template "Password Rule Settings") [28] | the settings values, only present when an admin changed a default | | current |
| Idle timeout | `/policies/activityBasedTimeoutPolicies` [30] | definition | | current |
| Directory audits | `/auditLogs/directoryAudits?$filter=activityDateTime ge {last run}` [22] | activityDateTime, activityDisplayName, category, initiatedBy, targetResources, result | reports limit [41] | 7 days Free, 30 days P1 and P2 [23] |
| Access reviews (optional) | `/identityGovernance/accessReviews/definitions/{id}/instances/{id}/decisions` [32] | instance `status`, `startDateTime`, `endDateTime`; each decision's `decision`, `reviewedBy`, `reviewedDateTime`, `principal`, `appliedBy`, `applyResult` [32][51] | | how long review history is kept is unverified (not stated on the pages read) |

Verity keeps a daily snapshot of each user's state, so a disable or delete stays provable after the
provider forgets it (30 days for audits and deleted users).

## 5. Checks

Controls, coverage and rationale per check: `checks.json` for existing keys, [identity-checks.md](identity-checks.md)
section 2 for new keys. Every check below runs daily except `idp.access_list_exported` and
`idp.groups_drive_access` (weekly). Evidence kept is the normalised observation set each check read.

### 5.1 Existing checks on Entra

| Check | Verdict | Population | Predicate on Entra | Outcomes and traps | API (permission) |
|---|---|---|---|---|---|
| `idp.mfa_enforced` | Supported | Enabled members; guests listed separately | Security defaults on, **or** at least one Conditional Access policy with state `enabled` (report only does not count), all users, all apps, grant `mfa` or an authentication strength; every excluded user or group is a recorded exception; legacy authentication blocked (security defaults block it [52]). **And** every enabled member has `isMfaCapable` true | fail lists users and gaps; error when a permission or the 1 per second Conditional Access read fails; insufficient when the registration report is incomplete; users in a federated domain are insufficient (their second factor happens at the other provider). Fact change 2026-11-23: the registration report needs P1 or P2 [5], so on a Free tenant the per user half reads error with reason `licence` and the check reads insufficient, even with security defaults on | security defaults, CA, registration report (`Policy.Read.All`, `AuditLog.Read.All`) |
| `idp.sso_enforced` | Partial | Applications in Verity's vendor register marked as applications, matched to service principals | Each matched app has `preferredSingleSignOnMode` saml or oidc, or is a multi tenant app that signs in through Entra (mode null); `password` mode is vaulted passwords, not single sign on | fail lists apps; apps not found in Entra are listed as "outside Entra", which needs an exception or a fix; Entra cannot see whether the app still allows local passwords | service principals (`Application.Read.All`) |
| `idp.password_policy` | Partial | Tenant settings; users with `passwordPolicies` | Configurable items meet the customer's standard: expiry (domain and `DisablePasswordExpiration`), banned password check and custom list, lockout threshold and duration (defaults 10 attempts and one minute when unchanged; custom values need P1 [26]). Length (8 to 256) and complexity are fixed by Microsoft [24] and reported as such (still fixed on the page updated September 2026). A user whose `passwordPolicies` holds `DisableStrongPassword` may set a weaker password than the default and is listed as a gap [2] | users synced from on premises AD follow AD's policy and read insufficient; a 12 character rule cannot be met on Entra (owner decision); expiry defaults to none for tenants created from 2021 and 90 days before that [24] | domains, group settings (`Domain.Read.All`, `GroupSettings.Read.All`) |
| `idp.session_timeout` | Partial | Conditional Access policies; idle timeout policy | A policy covering all users and apps sets `signInFrequency` within the standard and `persistentBrowser` never; the Microsoft 365 idle timeout policy exists and is within the standard | Entra has no tenant wide idle timeout for its own session; the idle policy covers Microsoft 365 web apps only [31]; P1 needed for sign in frequency | CA, `activityBasedTimeoutPolicies` (`Policy.Read.All`) |
| `idp.admins_limited` | Supported | Active and eligible holders of every directory role, groups expanded | Each holder is an enabled member (not a guest or shared account) on Verity's approved administrator list; Global Administrator count within the customer's limit | service principals holding roles are listed; error if PIM cannot be read on a P2 tenant | roles, PIM (`RoleManagement.Read.Directory`) |
| `idp.access_list_exported` | Supported | All users with groups and roles | Complete export read | pass when complete, insufficient when truncated | users, groups, roles |
| `idp.groups_drive_access` | Supported (P1) | In scope apps with `appRoleAssignmentRequired` true | Every assignment has `principalType` Group, or is a recorded exception | Free tenants cannot assign groups [44]: fail with reason `plan`, like GitHub's plan results; nested groups do not cascade [44] | `appRoleAssignedTo` (`Application.Read.All`) |
| `idp.connected_apps_known` | Supported | Service principals owned by another organisation that hold delegated grants or application permissions | Each is approved in the vendor register, or marked for removal | Microsoft's own first party apps are left out by owner tenant: Microsoft documents `f8cdef31-a31e-4b4a-93e4-5f571e91255a` as the Microsoft Services tenant id [54]; whether every first party app uses it is not stated (unverified), so other unknown owners are listed for review | service principals, grants (`Application.Read.All`, `DelegatedPermissionGrant.Read.All`) |
| `people.leavers_deprovisioned` | Partial | Leavers on the roster in the last 90 days (or `employeeLeaveDateTime` when HR writes it) | No enabled account later than the allowed hours after the end date; the time comes from the audit event, else from Verity's daily snapshot | insufficient without a roster; disabling Entra does not prove other systems were removed | users, deleted users, audits |
| `people.joiners_onboarded` | Partial | Accounts created in the period (`createdDateTime`) | Each matches a joiner whose onboarding started on or before the creation date | needs onboarding records; `createdDateTime` is null for some accounts made before June 2018 [2] | users |
| `tickets.access_requests_approved` | Partial (identity side) | Group, role and app assignment events in the period | Supplies the grants; the ticketing source supplies approvals | audits are kept 30 days (7 Free), so Verity must collect daily | audits (`AuditLog.Read.All`) |

### 5.2 New checks on Entra

| Check key (NEW) | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `idp.admin_mfa_phishing_resistant` | Active and eligible role holders | An enabled Conditional Access policy that targets their roles or them, for all apps, requires an authentication strength whose `allowedCombinations` hold only phishing resistant methods (`fido2`, `windowsHelloForBusiness`, `x509CertificateMultiFactor` [53]); and their `methodsRegistered` includes one such method (Graph publishes only example values such as `passKeyDeviceBound` [4], so the exact strings stay unverified until recorded from a test tenant) | fail lists admins and policy gaps; security defaults alone fail (not phishing resistant); no P1 fails with reason `plan`; error on permission | daily | policy, strength, admin methods | IAM-03 partial, IAM-07 partial |
| `idp.no_inactive_accounts` | Enabled members and guests older than `inactive_days` | `lastSuccessfulSignInDateTime` within `inactive_days`; before Dec 2023 fall back to the later of the interactive and non interactive times [3]; no signInActivity means never signed in or not since April 2020, so inactive [2]; a guest still `PendingAcceptance` counts as inactive | error with reason `licence` without P1 (signInActivity unavailable) [2]; insufficient when the user list is truncated | daily | account, kind, last sign in | IAM-12, IAM-02, HR-03 partial |
| `idp.machine_identities_owned` | App registrations in the tenant with a secret or certificate | At least one owner; each credential's `endDateTime` minus `startDateTime` at most `max_credential_days` | fail lists apps; pass with note when none exist | daily | app, owners, credential dates (no values) | IAM-10 partial |
| `idp.access_reviews_completed` | Review instances that ended in the last 90 days | Every decision recorded, none by the person reviewed, every deny applied | not applicable when the tenant has no reviews; error with reason `licence` without Governance or P2 | daily | instance, decisions, reviewers | IAM-02, IAM-07 partial |
| `people.accounts_match_roster` | Enabled member accounts | Matched by employee id or UPN to an active roster person, or a recorded service or shared account | insufficient without a current roster | daily | account, match, reason | IAM-12, IAM-01, HR-03 partial |

## 6. Artifacts and objectives it fills

As [identity-checks.md](identity-checks.md) section 3. Entra specific additions:

| Artifact key | Objectives | Control | Change |
|---|---|---|---|
| `privileged-elevation-and-break-glass-log` | IAM-07.B | IAM-07 | person -> person + `idp.admins_limited` (PIM eligible versus active, P2 only) |
| `removal-records-for-a-sample-of` | IAM-11.D | IAM-11 | the user's `signInSessionsValidFromDateTime` after the end date would show sessions were revoked (the user resource names no extra permission for it and it needs `$select` [2]; that `User.Read.All` returns it is still unverified until tested) |
| `session-limit-settings-export` | IAM-11.B | IAM-11 | person -> person + `idp.session_timeout` (P1 for sign in frequency) |

## 7. Framework reach

As [identity-checks.md](identity-checks.md) section 4. Intune adds the endpoint controls (devices research).

## 8. Limits and false assurance traps

- **Report only policies.** A Conditional Access policy in `enabledForReportingButNotEnforced` state lists like an enforced one. Never count it.
- **Exclusions.** Every Conditional Access policy can exclude users, groups and roles. A policy "for all users" with a large excluded group proves little. The check lists each exclusion.
- **Registered is not required.** `isMfaRegistered` without an enforcing policy is a fail. `isMfaCapable` is the stronger field. The report can be 36 hours late [5].
- **Federated domains.** When a domain is federated to another provider (Okta, AD FS), the second factor happens there. Those users read insufficient until that provider is connected.
- **Synced accounts.** Users from on premises AD follow AD's password and lockout rules, which Graph does not show.
- **Free tenants.** No `signInActivity`, no sign in logs through the API, no Conditional Access, no registration report, 7 days of audits [2][21][23][5]. Several checks read error with reason licence. That is correct, never a pass.
- **Sign in log retention.** Sign in and audit logs are kept 7 days on Free and 30 days on P1 and P2; reading sign ins through Graph needs P1 or P2 [21][23]. Upgrading does not bring back older data [23].
- **Short memory.** Audits and deleted users go after 30 days [23][46]. A collector that misses a month loses the leaver trail unless Verity's snapshots cover it.
- **Single sign on mode can be null** for older SAML and OIDC apps [16], and "password" mode is a stored password, not federation.
- **Per user MFA (legacy)** is not read in the first version: only the beta `/users/{id}/authentication/requirements` exposes `perUserMfaState`, one call per user [55]. A tenant relying on it reads as not enforced. The guide tells customers to move to Conditional Access or security defaults.
- **Partner admins.** Administrators acting through a Microsoft partner relationship (GDAP) may not appear as tenant users or role holders (unverified: Microsoft's GDAP pages do not say; test with a partner managed tenant). The admin list says so.
- **One vendor credential.** With Verity's multi tenant app, one certificate can read every consenting customer's directory. See the unified setup document.

## 9. Product and UI

- **Connect form.** Option A: one button, then the admin consent redirect (`https://login.microsoftonline.com/{tenant}/v2.0/adminconsent?client_id=...&scope=https://graph.microsoft.com/.default&redirect_uri=...&state=...`) [34]. Corrected 2026-11-23: `redirect_uri` is required and must match a redirect URI registered on Verity's app, so option A's app needs one Verity callback URL. Option B: certificate download, tenant ID, client ID, Test.
- **Scope.** The whole tenant. Per account exclusions (break glass, service accounts) need a reason, stored and printed on the evidence, as for GitHub repositories.
- **Health states.** Connected; missing permission (named); licence limits (named checks that cannot run without P1, P2 or Governance, detected from the provider's premium licence error [21], not from an extra permission); certificate expires on (date); throttled (run truncated).
- **In product guide.** Yes. Option B has six steps and two common mistakes (delegated instead of application permissions, forgetting **Grant admin consent**).

## 10. Implementation notes

- **Auth.** `azidentity.NewClientCertificateCredential(tenantID, clientID, certs, key, nil)` then `msgraphsdk.NewGraphServiceClientWithCredentials(cred, []string{"https://graph.microsoft.com/.default"})` [40]. The private key is held by the core and handed to the collector only as a short lived token (01-evidence-model.md 1.5).
- **Paging.** `msgraphcore.NewPageIterator` from `github.com/microsoftgraph/msgraph-sdk-go-core` [39]. Users through `/users/delta` would cut daily cost later (not needed for the first version).
- **Rate limits.** Directory token bucket per app and tenant (3,500 to 8,000 units per 10 seconds by tenant size), reports 5 requests per 10 seconds, Conditional Access 1 per second with no Retry-After, `signInActivity` 10 a minute [41]. Honour Retry-After; a run that runs out of time records `truncated`.
- **Error mapping.** 401 or invalid client: connection error. 403 `Authorization_RequestDenied`: the checks needing that permission read error "missing permission". 403 premium licence message: error with reason `licence` for those checks. 429: back off.
- **Scope drift.** Probe each permission once per run (a `$top=1` read). Do not read the token's `roles` claim: Microsoft says clients must treat access tokens as opaque [56] (corrected 2026-11-23).
- **Deletion semantics.** Missing from `/users` and present in deleted items: deleted, with its date. Missing from both: purged. Disabled: `accountEnabled` false. Verity records each transition.
- **Fixtures and test tenant.** Record with go-vcr against a test tenant with P1 and P2. The Microsoft 365 E5 developer sandbox needs an eligible Visual Studio Professional or Enterprise subscription or a partner programme path [57]; the length of a standalone P2 trial is unverified. Seed: a break glass account in an exclusion, a pending guest, a disabled and a deleted user, a user without MFA, an admin with a security key, an eligible PIM admin, an app with a secret older than a year, a third party app with consent.

## 11. How comparable platforms do it

| Platform | Connection | Permissions published | Tests named |
|---|---|---|---|
| Vanta | OAuth consent to Vanta's app by Global Administrator or Privileged Role Administrator; background sync by client credentials [V1] | `User.Read.All`, `Directory.Read.All`, optional `AuditLog.Read.All`; sign in and MFA data need P1 or P2 [V1] | not listed on the page |
| Drata | Global Administrator consent creates an enterprise application [D1] | `User.Read.All`, `Reports.Read.All`, `Directory.Read.All`, `Policy.Read.All`, `AuditLog.Read.All` [D1] | identity, MFA, unique email [D1] |
| Secureframe | Its own OAuth app or the customer's app registration; Global Reader and P1 [S1] | `Application.Read.All`, `AuditLog.Read.All`, `Directory.Read.All`, `User.Read.All`, `User.ReadBasic.All` [S1] | MFA counts Conditional Access and per user MFA [S1] |
| Sprinto | Admin consent by a Global Administrator; client credentials also offered [P1][P2] | `User.Read.All`, `Organization.Read.All`, `Reports.Read.All`, `Directory.Read.All`, `AuditLog.Read.All` [P1] | offboarded users [P2] |

All four ask for `Directory.Read.All`. Verity's list avoids it. Whether their apps are publisher verified
is not stated on these pages (unverified).

## 12. Sources

Microsoft Graph pages are `https://learn.microsoft.com/en-us/graph/api/<page>?view=graph-rest-1.0`.

1. user-list: https://learn.microsoft.com/en-us/graph/api/user-list?view=graph-rest-1.0
2. user resource: https://learn.microsoft.com/en-us/graph/api/resources/user?view=graph-rest-1.0
3. signInActivity: https://learn.microsoft.com/en-us/graph/api/resources/signinactivity?view=graph-rest-1.0
4. userRegistrationDetails: https://learn.microsoft.com/en-us/graph/api/authenticationmethodsroot-list-userregistrationdetails?view=graph-rest-1.0
5. Authentication methods activity: https://learn.microsoft.com/en-us/entra/identity/authentication/howto-authentication-methods-activity
6. Conditional Access policies: https://learn.microsoft.com/en-us/graph/api/conditionalaccessroot-list-policies?view=graph-rest-1.0
7. Security defaults: https://learn.microsoft.com/en-us/graph/api/identitysecuritydefaultsenforcementpolicy-get?view=graph-rest-1.0
8. Conditional Access overview and licensing: https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview
9. Authentication methods policy: https://learn.microsoft.com/en-us/graph/api/authenticationmethodspolicy-get?view=graph-rest-1.0
10. Authentication strengths: https://learn.microsoft.com/en-us/graph/api/authenticationstrengthroot-list-policies?view=graph-rest-1.0
11. Role assignments: https://learn.microsoft.com/en-us/graph/api/rbacapplication-list-roleassignments?view=graph-rest-1.0
12. PIM schedules: https://learn.microsoft.com/en-us/graph/api/rbacapplication-list-roleeligibilityscheduleinstances?view=graph-rest-1.0 and https://learn.microsoft.com/en-us/graph/api/rbacapplication-list-roleassignmentscheduleinstances?view=graph-rest-1.0
13. Governance licensing: https://learn.microsoft.com/en-us/entra/id-governance/licensing-fundamentals
14. Transitive members: https://learn.microsoft.com/en-us/graph/api/group-list-transitivemembers?view=graph-rest-1.0
15. Service principals: https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list?view=graph-rest-1.0
16. servicePrincipal resource: https://learn.microsoft.com/en-us/graph/api/resources/serviceprincipal?view=graph-rest-1.0
17. appRoleAssignedTo: https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list-approleassignedto?view=graph-rest-1.0
18. oauth2PermissionGrants: https://learn.microsoft.com/en-us/graph/api/oauth2permissiongrant-list?view=graph-rest-1.0
19. Permissions reference: https://learn.microsoft.com/en-us/graph/permissions-reference
20. Applications and credentials: https://learn.microsoft.com/en-us/graph/api/application-list?view=graph-rest-1.0 and https://learn.microsoft.com/en-us/graph/api/resources/passwordcredential?view=graph-rest-1.0
21. Sign ins: https://learn.microsoft.com/en-us/graph/api/resources/signin?view=graph-rest-1.0
22. Directory audits: https://learn.microsoft.com/en-us/graph/api/directoryaudit-list?view=graph-rest-1.0
23. Data retention: https://learn.microsoft.com/en-us/entra/identity/monitoring-health/reference-reports-data-retention
24. Password policy: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-sspr-policy
25. Domain resource: https://learn.microsoft.com/en-us/graph/api/resources/domain?view=graph-rest-1.0
26. Smart lockout: https://learn.microsoft.com/en-us/entra/identity/authentication/howto-password-smart-lockout
27. Banned passwords: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-password-ban-bad
28. Directory settings: https://learn.microsoft.com/en-us/graph/group-directory-settings and https://learn.microsoft.com/en-us/graph/api/group-list-settings?view=graph-rest-1.0
30. Idle timeout policy: https://learn.microsoft.com/en-us/graph/api/activitybasedtimeoutpolicy-list?view=graph-rest-1.0
31. Microsoft 365 idle session timeout: https://learn.microsoft.com/en-us/microsoft-365/admin/manage/idle-session-timeout-web-apps
32. Access reviews: https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview and https://learn.microsoft.com/en-us/graph/api/accessreviewinstance-list-decisions?view=graph-rest-1.0
33. Grant admin consent: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent
34. Admin consent endpoint: https://learn.microsoft.com/en-us/entra/identity-platform/v2-admin-consent
35. App credentials: https://learn.microsoft.com/en-us/entra/identity-platform/how-to-add-credentials
37. Publisher verification: https://learn.microsoft.com/en-us/entra/identity-platform/publisher-verification-overview
38. Risk based step up consent: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-risk-based-step-up-consent
39. Go SDK: https://github.com/microsoftgraph/msgraph-sdk-go
40. Go authentication: https://learn.microsoft.com/en-us/graph/sdks/choose-authentication-providers?tabs=go
41. Throttling limits: https://learn.microsoft.com/en-us/graph/throttling-limits
42. Intune managed devices: https://learn.microsoft.com/en-us/graph/api/intune-devices-manageddevice-list?view=graph-rest-1.0
43. Devices: https://learn.microsoft.com/en-us/graph/api/device-list?view=graph-rest-1.0
44. App assignment (group assignment needs P1 or P2): https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/assign-user-or-group-access-portal
46. Restore deleted users: https://learn.microsoft.com/en-us/entra/fundamentals/users-restore
47. Deleted items: https://learn.microsoft.com/en-us/graph/api/directory-deleteditems-list?view=graph-rest-1.0
48. Authentication methods per user: https://learn.microsoft.com/en-us/graph/api/authentication-list-methods?view=graph-rest-1.0
49. Named locations: https://learn.microsoft.com/en-us/graph/api/conditionalaccessroot-list-namedlocations?view=graph-rest-1.0
50. List groups: https://learn.microsoft.com/en-us/graph/api/group-list?view=graph-rest-1.0
51. Access review decision item: https://learn.microsoft.com/en-us/graph/api/resources/accessreviewinstancedecisionitem?view=graph-rest-1.0 and https://learn.microsoft.com/en-us/graph/api/resources/accessreviewinstance?view=graph-rest-1.0
52. Security defaults: https://learn.microsoft.com/en-us/entra/fundamentals/security-defaults
53. Authentication method modes: https://learn.microsoft.com/en-us/graph/api/resources/authenticationmethodmodes?view=graph-rest-1.0 and https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-strengths
54. First party Microsoft apps: https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/governance/verify-first-party-apps-sign-in
55. Per user MFA state (beta): https://learn.microsoft.com/en-us/entra/identity/authentication/howto-mfa-userstates and https://learn.microsoft.com/en-us/graph/api/resources/strongauthenticationrequirements?view=graph-rest-beta
56. Access tokens are opaque to clients: https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
57. Microsoft 365 Developer Program: https://learn.microsoft.com/en-us/office/developer-program/microsoft-365-developer-program
- V1 Vanta: https://help.vanta.com/en/articles/11345655-connecting-vanta-microsoft-entra
- D1 Drata: https://help.drata.com/en/articles/4797766-microsoft-365-integration-guide
- S1 Secureframe: https://support.secureframe.com/en/articles/15111601-microsoft-entra-id
- P1 Sprinto Office 365: https://docs.sprinto.com/integrations/overview/office365-integration.md
- P2 Sprinto Azure AD: https://docs.sprinto.com/integrations/overview/azure-active-directory-integration.md

## Decisions for the owner

1. Option A (Verity multi tenant app, publisher verification) or option B (customer app) first. See the unified setup document.
2. Entra's fixed 8 character minimum against IAM-06.A's 12: judge the configurable items only, or accept a compensating rule (MFA or passwordless). A compliance meaning, so the owner and an auditor decide.
3. Free tenants: show the checks that need P1 as "could not check, licence" (proposed), or hide them.
