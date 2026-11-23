# Verification log: identity providers and password manager

Round: 2026-11-23. Scope: the connector files [entra-id.md](../connectors/entra-id.md),
[okta.md](../connectors/okta.md), [google-workspace.md](../connectors/google-workspace.md),
[1password.md](../connectors/1password.md), [identity-checks.md](../connectors/identity-checks.md) and
[identity-providers-unified-setup.md](../connectors/identity-providers-unified-setup.md).

Method: every "unverified" mark and every permission, scope, admin role, licence, endpoint and field a
check depends on was read against the provider's official pages (Microsoft Learn, developer.okta.com and
help.okta.com, Okta's API spec as shipped in the official Go SDK, developers.google.com, docs.cloud.google.com,
support.google.com and knowledge.workspace.google.com, www.1password.dev and support.1password.com).
Source tags refer to the Sources section of the file named in the row. "Confirmed" means an official page
states it, including facts that replaced an "unverified" mark. "Corrected" means the file said something
else or less, now fixed in place. "Still unverified" keeps the mark, with the reason in the file.
Claims about Vanta, Drata, Secureframe and Sprinto were not checked in this round (not provider
documentation); their "unverified" marks stay as they were.

## Corrections that change a check, a decision or a recommendation

| File | Correction | Effect |
|---|---|---|
| entra-id.md, identity-checks.md | The registration report (`userRegistrationDetails`) needs Entra ID P1 or P2: its Graph resource page points to the licence section that requires P1 or P2 [4][5] | `idp.mfa_enforced` on a Free tenant: the per user half reads error with reason `licence`, so the check is insufficient even with security defaults on. Feasibility matrix cell changed |
| okta.md, identity-checks.md | Identity Engine role comparison lists "View Global Session Policies" for Super and Org Administrator only, not Read-only Administrator [O6b] | `idp.session_timeout` and the session half of `idp.mfa_enforced` may read error with Read-only Administrator. Decision 1 (and unified decision 6) gain an option: a custom admin role with `okta.iam.read` and `okta.policies.read` [O7] |
| okta.md, identity-checks.md | Access certification campaigns and reviews need the Access Certifications Administrator role (`ACCESS_CERTIFICATIONS_ADMIN`) as well as the scope [O15][O6b] | `idp.access_reviews_completed` on Okta needs an extra admin role on the service app; without it the check reads error |
| okta.md | Read-only Administrator is not listed for viewing administrators in either edition [O6][O6b] | Confirms the open point is likely a refusal; `idp.admins_limited` stays "role read to test"; custom role with `okta.iam.read` is the documented narrow route (API acceptance still to test) |
| entra-id.md, identity-providers-unified-setup.md | The v2 admin consent endpoint requires `redirect_uri` matching a URI registered on the app [34][M2] | Option A / (c) for Entra needs one registered Verity callback URL. No change to the recommendation |
| entra-id.md | `passwordPolicies` can hold `DisableStrongPassword`, which allows weaker passwords than the default [2] | `idp.password_policy` predicate now lists such users as a gap (key and mappings unchanged) |
| google-workspace.md | The Policy API returns only values an admin set explicitly [W12] | `idp.password_policy`, `idp.session_timeout`, `idp.mfa_enforced`: an absent setting must be read as Google's default, never as missing data |
| okta.md | System Log polling orders events by storage time and always returns a `next` link [O19] | Collector cursor is the `next` link, not the last `published` plus uuid (implementation only) |
| okta.md | API tokens are listed by `GET /api/v1/api-tokens` with `okta.apiTokens.read` [O26] | `idp.machine_identities_owned` on Okta can read tokens; new optional scope row added |
| 1password.md | The Events API reaches only the last 120 days; the console audit log keeps 365 [1P18][1P16] | `vault.leavers_removed` (90 days) fits; a first run cannot backfill beyond 120 days |

The recommendation in identity-providers-unified-setup.md (two credentials, one guided setup, launch
with customer apps, then Verity's Entra multi tenant app) is unchanged.

## All claims checked

| File | Claim | Result | Source |
|---|---|---|---|
| entra-id.md | Go SDK `msgraph-sdk-go` v1.107.0 released 2026-11-20 | confirmed | [39] (GitHub release, Go module proxy) |
| entra-id.md | `NewClientCertificateCredential`, `NewGraphServiceClientWithCredentials`, `msgraphcore.NewPageIterator` | confirmed | [39][40] |
| entra-id.md | Certificates recommended; secrets not for production; secret lifetime 24 months at most, under 12 advised | confirmed | [35] |
| entra-id.md | Graph application permission consent needs Privileged Role Administrator or Global Administrator; Cloud Application Administrator and Application Administrator cannot | confirmed | [33] |
| entra-id.md | `User.Read.All` lists users and deleted users | confirmed | [1][47] |
| entra-id.md | `AuditLog.Read.All` for signInActivity, registration report, directory audits, sign ins | confirmed | [2][4][22][21] |
| entra-id.md | signInActivity needs P1 or P2 | confirmed | [2] |
| entra-id.md | Registration report licence (open point) | confirmed: P1 or P2 (was unverified) | [4][5] |
| entra-id.md | Registration report permission (open point) | confirmed: `AuditLog.Read.All`, application | [4] |
| entra-id.md | `Policy.Read.All` reads CA policies, named locations, security defaults, auth methods policy, strengths, idle timeout | confirmed (least privileged for the two auth methods APIs is `Policy.Read.AuthenticationMethod`; `Policy.Read.All` is listed) | [6][49][7][9][10][30] |
| entra-id.md | Conditional Access needs P1; risk based policies P2 | confirmed | [8] |
| entra-id.md | `RoleManagement.Read.Directory` covers role definitions, assignments and PIM schedule instances | confirmed | [11][12] |
| entra-id.md | PIM needs P2 or ID Governance | confirmed | [13] |
| entra-id.md | `GroupMember.ReadBasic.All` versus `GroupMember.Read.All` | confirmed: ask for `GroupMember.Read.All` (ReadBasic is not listed for listing groups and is missing from the permissions reference) | [14][50][19] |
| entra-id.md | `Application.Read.All` for service principals, appRoleAssignedTo, applications, owners | confirmed | [15][17][20] |
| entra-id.md | `DelegatedPermissionGrant.Read.All` works for the grants list | still unverified (exists in the reference, not named on the list page) | [18][19] |
| entra-id.md | `GroupSettings.Read.All` lists tenant settings | confirmed | [28] |
| entra-id.md | Custom lockout and custom banned list need P1 | confirmed | [26][27] |
| entra-id.md | `Domain.Read.All` for domains; domain fields | confirmed | [25] |
| entra-id.md | `AccessReview.Read.All`; access reviews need ID Governance, some capabilities P2 | confirmed | [32][13] |
| entra-id.md | `User-LifeCycleInfo.Read.All` reads `employeeLeaveDateTime` | confirmed | [2] |
| entra-id.md | Licence for `employeeLeaveDateTime` | still unverified (not stated) | [2] |
| entra-id.md | Intune permissions and active Intune licence | confirmed | [42][43] |
| entra-id.md | Microsoft discourages per user method reads for the whole population | confirmed | [48] |
| entra-id.md | Publisher verification requirements | corrected: verified partner global account, Application Administrator or Cloud Application Administrator plus CPP Partner Admin or Account Admin, MFA, minutes once ready | [37] |
| entra-id.md | Unverified multi tenant apps still get admin consent (risk based step up) | confirmed | [38] |
| entra-id.md | Users page max 999, 500 with signInActivity; signInActivity 10 requests a minute | confirmed | [1][41] |
| entra-id.md | `lastSuccessfulSignInDateTime` only from Dec 2023 | confirmed (1 Dec 2023, not backfilled) | [3] |
| entra-id.md | signInActivity absent for users who never signed in or not since April 2020 | confirmed (added) | [2] |
| entra-id.md | `createdDateTime` null for some accounts before June 2018 | confirmed | [2] |
| entra-id.md | Deleted users kept 30 days | confirmed | [46] |
| entra-id.md | Registration report fields | confirmed | [4] |
| entra-id.md | Report up to 36 hours late; disabled users not listed | confirmed (soft deleted users also left out) | [4][5] |
| entra-id.md | Reports throttling 5 requests per 10 seconds per app per tenant | confirmed for the reports service; the page does not name this report | [41] |
| entra-id.md | Conditional Access 1 request a second per tenant, 429 without Retry-After | confirmed | [41] |
| entra-id.md | Directory token bucket 3,500 to 8,000 units per 10 seconds by tenant size | confirmed | [41] |
| entra-id.md | `preferredSingleSignOnMode` values; may be null | confirmed | [16] |
| entra-id.md | Credential fields kept, never secret values | corrected: `hint` (first three characters) added to never keep | [20] |
| entra-id.md | Directory audits 7 days Free, 30 days P1 and P2 | confirmed | [23] |
| entra-id.md | Sign in log retention by licence (open point) | confirmed: 7 days Free, 30 days P1 and P2; Graph needs P1 or P2; upgrade is not retroactive | [23][21] |
| entra-id.md | Access review field names | confirmed (was unverified) | [32][51] |
| entra-id.md | Access review history retention | still unverified (not stated) | [32] |
| entra-id.md | Security defaults block legacy authentication | confirmed (was unverified) | [52] |
| entra-id.md | Minimum password length (open point) | confirmed: fixed 8 to 256, not configurable (page updated September 2026) | [24] |
| entra-id.md | Lockout defaults 10 attempts, one minute | confirmed | [24][26] |
| entra-id.md | `DisableStrongPassword` user flag | corrected (added to the predicate) | [2] |
| entra-id.md | Password expiry defaults by tenant age | confirmed (added) | [24] |
| entra-id.md | Idle session timeout covers Microsoft 365 web apps only | confirmed | [31] |
| entra-id.md | Group based app assignment needs P1 or P2; nested groups do not cascade | confirmed | [44] |
| entra-id.md | Microsoft first party apps by owner tenant id | partly confirmed: Microsoft Services tenant id documented; completeness still unverified | [54] |
| entra-id.md | Phishing resistant strength combinations | confirmed: `fido2`, `windowsHelloForBusiness`, `x509CertificateMultiFactor` | [53] |
| entra-id.md | `methodsRegistered` value strings | still unverified (only examples published) | [4] |
| entra-id.md | `signInSessionsValidFromDateTime` readable with `User.Read.All` | still unverified (no extra permission named; needs a test) | [2] |
| entra-id.md | Per user MFA only in beta | confirmed (`/users/{id}/authentication/requirements`, `perUserMfaState`) | [55] |
| entra-id.md | GDAP partner admins absent from users or role list | still unverified (GDAP pages do not say) | Partner Center GDAP FAQ |
| entra-id.md | Admin consent URL | corrected: `redirect_uri` required | [34] |
| entra-id.md | Read the token's `roles` claim for scope drift | corrected: Microsoft says clients treat access tokens as opaque | [56] |
| entra-id.md | Test tenant with P1 and P2 | partly confirmed: E5 developer sandbox eligibility; P2 trial length still unverified | [57] |
| okta.md | Go SDK v9.0.0, 19 Nov 2026, import path `.../v9/okta` | confirmed | [G1] |
| okta.md | SDK options `WithAuthorizationMode("PrivateKey")`, `WithScopes`, `WithPrivateKey`, `WithPrivateKeyId`; DPoP support | confirmed | [G1] |
| okta.md | Service apps use `private_key_jwt` or `spiffe_jwt`; client secret not allowed | confirmed (was unverified) | [O1][O25] |
| okta.md | Token lifetime fixed at one hour; assertion `exp` at most one hour ahead | confirmed | [O1] |
| okta.md | DPoP GA for management APIs in 2024.02.0 | confirmed | [O2] |
| okta.md | DPoP setting label | corrected to the full label in the setup guide | [O3] |
| okta.md | DPoP nonce flow, `ath`, separate DPoP key | confirmed | [O3] |
| okta.md | SSWS token inherits admin privileges, 30 day idle expiry, dies with the admin, OAuth recommended | confirmed | [O4] |
| okta.md | Admin role required on every service app | confirmed | [O1] |
| okta.md | Read-only Administrator can list admin role assignments (open point) | still unverified: both comparisons list viewing administrators for Super Administrator only, so refusal is likely; test on a developer org | [O6][O6b][O13] |
| okta.md | Read-only Administrator can read global session policies (Identity Engine) | corrected: listed for Super and Org Administrator only | [O6b] |
| okta.md | Read-only Administrator can read password policies and authenticators | still unverified (not listed in the comparison) | [O6b] |
| okta.md | Custom role permission `okta.iam.read` exists | confirmed (views roles, resources and admin assignments) | [O7] |
| okta.md | Custom role accepted by the role endpoints | still unverified (test) | [O7] |
| okta.md | Custom permission `okta.policies.read` (view any policy) | confirmed (added) | [O7] |
| okta.md | Only Super Administrator grants scopes | confirmed; also only one can rotate keys once grants exist (added) | [O1] |
| okta.md | Scopes `okta.users/groups/apps/policies/authenticators/roles/logs.read` exist | confirmed | [O16] |
| okta.md | `okta.factors.read` does not exist; factor reads use `okta.users.read` | confirmed | [O16][G1] |
| okta.md | `okta.governance.accessCertifications.read` | confirmed; corrected: also needs Access Certifications Administrator | [O15] |
| okta.md | "Public client app admins" setting location | corrected: Settings, Account | [O1] |
| okta.md | Default user list omits DEPROVISIONED; `limit` default 200 | confirmed | [O8] |
| okta.md | Factors and authenticator enrolment endpoints | confirmed | [O9][G1] |
| okta.md | Per user call limits | still unverified (limits table loads by script) | [O18] |
| okta.md | Authenticator keys (`okta_password`, `okta_verify`, `security_key`) | confirmed | [G1] |
| okta.md | Policy types PASSWORD, OKTA_SIGN_ON, ACCESS_POLICY, MFA_ENROLL | confirmed | [G1] |
| okta.md | Apps `limit` max 200; app users max 500 | confirmed | [G1] |
| okta.md | Per minute rate limits (600 users, 100 apps, 120 or 50 logs) | still unverified (table loads by script) | [O18] |
| okta.md | Role endpoints and paging (default 100) | confirmed; client role endpoint added; max 200 | [O13][G1] |
| okta.md | System Log `limit` max 1000; 90 day retention | confirmed | [O14][O19] |
| okta.md | System Log event types listed | confirmed (all present in the catalogue) | [O20] |
| okta.md | Service apps get 50 percent of a rate limit bucket by default | confirmed | [O1] |
| okta.md | Rate limit headers and 429 | confirmed | [O21] |
| okta.md | `signOnMode` values | confirmed | [G1] |
| okta.md | Password policy JSON paths and defaults | confirmed (was unverified) | [G1] |
| okta.md | Session defaults (idle 120, lifetime 0) and `usePersistentCookie` | confirmed | [G1] |
| okta.md | App user `scope` USER or GROUP | confirmed (was unverified) | [G1] |
| okta.md | Phishing resistant constraint field | confirmed: `possession.phishingResistant` = `REQUIRED` (was unverified) | [G1] |
| okta.md | Whether Okta Verify counts as phishing resistant | confirmed: FastPass and passkeys do; push and codes are not named (was unverified) | [O27] |
| okta.md | Okta apps have no owner field | still unverified | [G1] |
| okta.md | API token listing endpoint and scope | confirmed: `GET /api/v1/api-tokens`, `okta.apiTokens.read` (was unverified) | [O26] |
| okta.md | `/credentials/secrets` returns `client_secret` | confirmed (added: never call it) | [G1] |
| okta.md | IGA campaigns and reviews endpoints | confirmed | [O15] |
| okta.md | IGA data retention | still unverified (not stated) | [O15] |
| okta.md | Token URL `/oauth2/v1/token` | confirmed | [O22] |
| okta.md | Response to a partly granted scope list | still unverified (not stated; test) | [O1] |
| okta.md | System Log polling cursor | corrected: store the `next` link | [O19] |
| okta.md | Upstream identity provider factors | confirmed: "Trust AMR claims" and claims sharing (was unverified) | [O28] |
| okta.md | Vanta and Drata listed as OIN API service integrations | still unverified (OIN pages do not expose the type as text) | [O24] |
| google-workspace.md | `impersonate` needs `roles/iam.serviceAccountTokenCreator` | confirmed | [G5] |
| google-workspace.md | Admin role on a service account: any role except Super Admin, optional expiry up to a year | confirmed | [W10] |
| google-workspace.md | One role per service account | corrected: not stated by Google, removed | [W10] |
| google-workspace.md | Service account admin role documented for the Groups API only | confirmed; users and Reports still unverified | [W10][W11] |
| google-workspace.md | Policy API only for a super administrator | confirmed | [W12] |
| google-workspace.md | Policy API by admin OAuth (open point) | still unverified: setup guide documents only a service account with delegation | [W26] |
| google-workspace.md | Admin SDK Directory and Reports scopes sensitive or restricted (open point) | still unverified: restricted list covers Gmail and Drive data; the FAQ gives only examples | [W13b][W14] |
| google-workspace.md | Verification timelines: brand 2 to 3 business days, sensitive 10, restricted 6 weeks, yearly assessment | confirmed | [W14][W13b] |
| google-workspace.md | Unverified app capped at 100 users for the project lifetime | confirmed | [W14] |
| google-workspace.md | Admin trusted apps exception | confirmed (added) | [W14b] |
| google-workspace.md | Option A needs no OAuth verification | still unverified (inference; pages do not mention delegation) | [W13b] |
| google-workspace.md | Marketplace review "several days"; domain install with sensitive scopes needs verification | confirmed | [W16][W13b] |
| google-workspace.md | Marketplace apps using Admin SDK admin scopes | still unverified | [W16] |
| google-workspace.md | Delegation: super admin, Client ID and scopes, multi party approval, up to 24 hours | confirmed | [W8] |
| google-workspace.md | Use `signJwt` instead of service account keys for delegation | confirmed | [W17] |
| google-workspace.md | Workload identity federation accepts AWS, Azure, OIDC and SAML | confirmed | [W19] |
| google-workspace.md | Key creation blocked for organisations created on or after 3 May 2024 | confirmed | [W9] |
| google-workspace.md | Scope names and meanings | confirmed | [W22][W23][W4] |
| google-workspace.md | Admin privilege for `rolemanagement.readonly` and `domain.readonly` | still unverified (privilege page names none) | [W21] |
| google-workspace.md | `admin.directory.user.security` is the only scope for tokens.list | confirmed | [W24] |
| google-workspace.md | Cloud Identity editions include admin, user, SAML, OAuth and group log events and reports | confirmed | [W27] |
| google-workspace.md | Policy API GA 20 Feb 2025 for all Workspace customers | confirmed | [W28] |
| google-workspace.md | Reports API availability per Workspace edition | still unverified (not stated) | [W30] |
| google-workspace.md | Policy API returns only explicitly set values | corrected (added; checks apply defaults) | [W12] |
| google-workspace.md | Users resource fields | confirmed | [W1] |
| google-workspace.md | Users max 500 a page; groups and members max 200 | confirmed | [W29] |
| google-workspace.md | Policy setting types and field names | confirmed; `pageSize` default 50, max 100 added | [W3][W23] |
| google-workspace.md | activities.list `maxResults` 1000; 180 day window; 250 filtered calls a minute | confirmed | [W4][W30] |
| google-workspace.md | Accounts usage parameter names; `is_super_admin` and `is_delegated_admin` ended 15 Nov 2024 | confirmed | [W6] |
| google-workspace.md | Lag 1 to 5 days (accounts), a couple of hours (token); 6 months report, 15 months API | confirmed | [W5] |
| google-workspace.md | Directory 2,400 queries a minute per user per project; 429 per account cannot be raised | confirmed | [W29] |
| google-workspace.md | Reports 2,400 a minute; 503 on quota | confirmed | [W30] |
| google-workspace.md | No API lists custom SAML apps or their assignments | still unverified (no endpoint found) | [W1][W22] |
| google-workspace.md | Unconfigured apps setting and delegated clients | still unverified (page does not address it) | Google app access control help |
| google-workspace.md | Google 2SV with a third party IdP | confirmed: off by default, can be turned on after SSO; super admins never use SSO (was unverified) | [W32] |
| google-workspace.md | How long `showDeleted` lists deleted users | still unverified; 20 day restore window confirmed | [W33] |
| google-workspace.md | How a policy targets a group | confirmed: `policyQuery.orgUnit` or `policyQuery.group`, `sortOrder` (was unverified) | [W34] |
| google-workspace.md | Leaver admin event names | confirmed: `SUSPEND_USER`, `DELETE_USER`, `ARCHIVE_USER` (was "to confirm") | [W35] |
| google-workspace.md | Service accounts and delegation clients not listed by the Admin SDK | still unverified | [W22] |
| google-workspace.md | Source W2 link | corrected (pointed at the scopes page) | [W2] |
| 1password.md | Users API needs Business or Enterprise, not Teams; unsupported with automated provisioning | confirmed | [1P3] |
| 1password.md | Scopes `users.view`, `users.suspend`, `users.reactivate`; fixed at creation | confirmed | [1P2] |
| 1password.md | Who creates the OAuth application and the screen labels | corrected: owner, administrator or Security group; Integrations, Directory, OAuth Application (labels were unverified) | [1P2][1P3] |
| 1password.md | Token endpoint, regional hosts, 900 second tokens, no refresh token | confirmed | [1P2][1P14] |
| 1password.md | List users filter, fields, other states excluded, page size | confirmed (default 100 added) | [1P1] |
| 1password.md | Users API 100 a minute, 6,000 an hour | confirmed | [1P14] |
| 1password.md | Events token: owner or administrator, expiry options, events to report | confirmed | [1P7] |
| 1password.md | Events Reporting plan | confirmed Business; Teams still unverified | [1P7] |
| 1password.md | Introspect endpoint | confirmed | [1P8] |
| 1password.md | Audit events endpoint, cursor, `limit` 1 to 1000, 600 a minute, 30,000 an hour | confirmed | [1P15] |
| 1password.md | Audit event codes and the inconsistencies on the page | confirmed | [1P4] |
| 1password.md | How far back the Events API reads | confirmed: 120 days (was unverified); audit log 365 days | [1P18][1P16] |
| 1password.md | Owners cannot unlock with SSO | confirmed | [1P17] |
| 1password.md | SCIM bridge uses one bearer token, no reduced token | confirmed (none documented) | [1P10] |
| 1password.md | Service accounts list users "supported, but not recommended"; SDK user management planned | confirmed | [1P12][1P9] |
| 1password.md | Developer site moved to www.1password.dev | confirmed (redirect) | [1P1] |
| identity-checks.md | Entra `idp.mfa_enforced` feasibility | corrected (Free tenant reads insufficient) | entra-id.md [5] |
| identity-checks.md | Okta `idp.session_timeout` and `idp.admins_limited` feasibility notes | corrected (role caveats) | okta.md [O6b] |
| identity-checks.md | Okta `idp.access_reviews_completed` needs an extra role | corrected | okta.md [O15] |
| identity-checks.md | Identity providers keep sign in logs 7 to 180 days | confirmed (Entra 7 or 30, Okta 90, Google 6 months) | entra-id.md [23], okta.md [O19], google-workspace.md [W5] |
| identity-providers-unified-setup.md | Okta Web app client credentials only with an NHI Authentication Token subscription | confirmed (bought or renewed on or after 14 Aug 2026) | [K2] |
| identity-providers-unified-setup.md | Entra 256 redirect URIs, cannot be raised | confirmed | [M6] |
| identity-providers-unified-setup.md | Keycloak build can sign a JWT for Entra | still unverified (depends on Infowise's build) | none |
| identity-providers-unified-setup.md | Partner Center and publisher verification lead time | corrected: publisher verification minutes; Partner Center time still unverified | [M4] |
| identity-providers-unified-setup.md | Option (c) Entra needs a redirect URI | corrected (added) | [M2] |
| identity-providers-unified-setup.md | OIN Wizard submitter must be a super admin | corrected: super admin, or app and org admin roles | [K4] |
| identity-providers-unified-setup.md | OIN API service integrations: client secret only | corrected wording (secret generated per install; no other method offered) | [K3][K4] |
| identity-providers-unified-setup.md | Admin role given to an installed OIN integration | still unverified (role assignment possible since 2024.02.0) | [K6] |
| identity-providers-unified-setup.md | OIN OIDC per customer redirect URI | confirmed: up to eight tenant variables in redirect URIs (was unverified) | [K7] |
| identity-providers-unified-setup.md | `azidentity` can sign the assertion through a callback | confirmed: `NewClientAssertionCredential` (was unverified) | [M7] |
| identity-providers-unified-setup.md | Google Internal apps skip verification and the user cap | confirmed | [G1] |
| identity-providers-unified-setup.md | Google verification timelines; Marketplace review several days | confirmed | [G3][G4] |

## Counts

| Result | Rows |
|---|---|
| confirmed (2 of them partly, with the open part noted) | 130 |
| corrected | 21 |
| still unverified | 27 |
| total | 178 |
