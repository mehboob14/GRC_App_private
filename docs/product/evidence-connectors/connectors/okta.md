# Okta

| | |
|---|---|
| Capabilities | `identity_provider` |
| Delivery phase | Phase 2 for evidence (signed catalogue, section 8). Okta sign in is the owner's request, not named in the contract's SSO line |
| Auth model | OAuth 2.0 client credentials on an API Services app, `private_key_jwt`, optional DPoP; read scopes `okta.*.read` and a read only admin role on the app |
| Shares setup with | Single sign on through Keycloak ([sso-providers.md](../../../runbooks/sso-providers.md) section 3). Always a separate app, see [identity-providers-unified-setup.md](identity-providers-unified-setup.md) |
| Go library | `github.com/okta/okta-sdk-golang/v9/okta` (v9.0.0, released 19 Nov 2026; supports private key auth and DPoP) [G1] |

Shared check definitions, artifacts and framework reach: [identity-checks.md](identity-checks.md).

## 1. What it proves

Okta Workforce Identity holds the people, groups, app assignments and sign in rules. Read only, it shows:

- every user and their lifecycle status (active, suspended, deprovisioned and the states between), with
  creation, activation, last sign in and status change times;
- which factors each user has enrolled, and which policies require a second factor for which apps;
- password, lockout and session rules, by policy and rule priority;
- who holds which admin role, directly, through a group, or as an app (client);
- which apps sign in through Okta (SAML, OIDC) versus password vaulting, and whether users reach them
  through groups;
- 90 days of System Log events: lifecycle, privilege grants, policy changes, membership changes.

It cannot show apps that never touched Okta, approvals, or anything older than 90 days that Verity did not
keep.

## 2. Connecting: method, credentials and permissions

**Method.** The customer creates an **API Services** app integration. Verity authenticates with client
credentials and a signed client assertion (`private_key_jwt`). Okta documents `private_key_jwt` (or
`spiffe_jwt`) for service apps that request Okta scoped tokens, and says the client ID and secret method
isn't allowed there [O1][O25]. Tokens last one hour, fixed [O1]. Okta supports
DPoP for its management APIs (GA in 2024.02.0); the app setting is "Require Demonstrating Proof of
Possession (DPoP) header in token requests" [O2][O3]. Verity supports DPoP and asks for it on.

**Why not an API token.** An SSWS token carries the privileges of the admin who made it, changes when
theirs change, dies 30 days after its last use and when that admin is deactivated, and Okta strongly
recommends OAuth instead [O4]. Verity accepts one only as a fallback for orgs that cannot create a service
app, and says so on the connection.

**Admin role on the app.** Okta requires an admin role on every OAuth service app [O1]. Okta support
recommends **Read-only Administrator** for read access [O5]. Okta's role comparison (Classic and Identity
Engine) lists viewing the System Log and apps for Read-only Administrator, but lists "add, remove, and
view administrators" under Super Administrator only [O6][O6b]; the API reference for the role endpoints
names only the `okta.roles.read` scope [O13]. So reading role assignments with Read-only Administrator is
likely refused. Two more gaps found on 2026-11-23: on Identity Engine the comparison lists "View Global
Session Policies" for Super and Org Administrator only [O6b], and access certification campaigns and
reviews need the Access Certifications Administrator role [O6b][O15]. **To test on a developer org before
launch.** The narrow alternative is a custom admin role: `okta.iam.read` is described as viewing roles,
resources and admin assignments, and `okta.policies.read` as viewing any policy [O7] (whether the role
endpoints accept a custom role is unverified until tested). The wide one is Super Administrator, which is
what Vanta asks for [V1]. Only a Super Administrator can grant scopes to the app, and only one can rotate
the app's keys once it has Okta scoped grants, so setup and key rotation need one [O1].

| Scope | Read only | Needed for | Admin role and licence notes |
|---|---|---|---|
| `okta.users.read` | yes | users, factors (`/users/{id}/factors` uses this scope), authenticator enrollments [O8][O9]: `idp.mfa_enforced`, `idp.admin_mfa_phishing_resistant`, `idp.access_list_exported`, `idp.no_inactive_accounts`, `people.*` | Read-only Administrator |
| `okta.groups.read` | yes | groups and members: `idp.access_list_exported`, `idp.groups_drive_access` | Read-only Administrator |
| `okta.apps.read` | yes | apps, app users, app groups [O10]: `idp.sso_enforced`, `idp.groups_drive_access`, `idp.connected_apps_known`, `idp.machine_identities_owned` | Read-only Administrator |
| `okta.policies.read` | yes | password, global session, authentication and enrolment policies and rules [O11]: `idp.mfa_enforced`, `idp.password_policy`, `idp.session_timeout`, `idp.admin_mfa_phishing_resistant` | Classic: Read-only Administrator views Okta sign on policies [O6]. Identity Engine: it views app sign-in (authentication) policies, but global session policies are listed for Super and Org Administrator only [O6b] (corrected 2026-11-23); password policies are not listed (unverified). A custom role with `okta.policies.read` covers every policy [O7] |
| `okta.authenticators.read` | yes | authenticators (Identity Engine) [O12]: `idp.mfa_enforced`, `idp.admin_mfa_phishing_resistant` | unverified for Read-only Administrator (the comparison does not list viewing authenticators) |
| `okta.roles.read` | yes | role assignments for users, groups and clients [O13]: `idp.admins_limited`, `idp.admin_mfa_phishing_resistant` | viewing administrators is listed for Super Administrator only [O6][O6b]; custom role with `okta.iam.read` [O7]; test |
| `okta.apiTokens.read` (optional) | yes | API token metadata (`GET /api/v1/api-tokens`: id, name, userId, created, expiresAt) [O26]: `idp.machine_identities_owned` | admin role unverified |
| `okta.logs.read` | yes | System Log [O14]: `people.leavers_deprovisioned`, `tickets.access_requests_approved`, `idp.admins_limited` history | Read-only Administrator [O6] |
| `okta.governance.accessCertifications.read` (optional) | yes | campaigns and reviews [O15]: `idp.access_reviews_completed` | Okta Identity Governance subscription, and the Access Certifications Administrator role on the app (the API names `ACCESS_CERTIFICATIONS_ADMIN`) [O15] (added 2026-11-23) |

`okta.factors.read` does not exist; factor reads use `okta.users.read` [O16]. Every scope above exists in
Okta's scope list [O16]. Not requested: any `.manage` scope.

**Vendor side prerequisites.** None for a customer created service app. An Okta Integration Network (OIN)
listing is optional and changes the auth model (unified setup document, section 3.2).

## 3. Customer setup guide (draft product text)

Screen labels as documented on 2026-11-23; check them on a developer org before publishing.

1. In Verity, open Integrations, Okta, **Connect evidence**. Verity shows a public key and the list of
   scopes. The public key is not a secret.
2. Sign in to the Okta Admin Console as a Super Administrator. Go to Applications, **Create App
   Integration**, choose **API Services**, name it "Verity evidence (read only)" and save.
3. On the General tab, under Client Credentials, press **Edit**. Choose **Public key / Private key**, add a
   key, paste the key from Verity and save. Turn on **Require Demonstrating Proof of Possession (DPoP)
   header in token requests**.
4. On the **Okta API Scopes** tab, grant each scope Verity listed and nothing else.
5. Assign the app the **Read-only Administrator** role (and any extra role Verity names for reading
   administrators).
6. In Settings, Account, make sure **Public client app admins** is off. When it is on, Okta gives service
   apps the Super Administrator role automatically once scopes are granted [O1]. (Location corrected
   2026-11-23: it is not under Security, General.)
7. Copy your Okta domain (for example `acme.okta.com`) and the app's **Client ID** into Verity. Press
   **Test**.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Users | `GET /api/v1/users`, then `filter=status eq "DEPROVISIONED"` (the default list leaves deprovisioned users out) [O8] | id, status, created, activated, statusChanged, lastLogin, passwordChanged, lastUpdated, type, profile login and email | `limit` default 200; Link header `rel="next"` [O17]; 600 a minute [O18] | until the user is deleted |
| Factors | `GET /api/v1/users/{id}/factors` (Classic), `GET /api/v1/users/{id}/authenticator-enrollments` (Identity Engine) [O9] | factor or authenticator type, status, created | one call per user; budget it (per user limits unverified: Okta's limits table loads by script) | current |
| Authenticators | `GET /api/v1/authenticators` [O12] | key (okta_password, okta_verify, security_key...), status, type | | current |
| Policies and rules | `GET /api/v1/policies?type=` PASSWORD, OKTA_SIGN_ON, ACCESS_POLICY, MFA_ENROLL; `GET /api/v1/policies/{id}/rules` [O11] | priority, status, conditions (groups, people, network zones), password complexity, age and lockout, session idle and lifetime, persistent cookie, factor mode, re-authentication interval | | current |
| Apps | `GET /api/v1/apps`, `/apps/{id}/users`, `/apps/{id}/groups` [O10] | id, label, status, signOnMode, created; assignments | apps limit max 200, app users max 500; 100 a minute on `/apps` [O18] | current |
| Groups | `GET /api/v1/groups`, `/groups/{id}/users` | id, name, type, members | | current |
| Admin roles | `GET /api/v1/iam/assignees/users`, `/users/{id}/roles`, `/groups/{id}/roles`, `/oauth2/v1/clients/{clientId}/roles` for apps [O13] | role type (SUPER_ADMIN, READ_ONLY_ADMIN, CUSTOM...), assignmentType (USER, GROUP, CLIENT), targets | default 100, max 200 | current |
| System Log | `GET /api/v1/logs?since=...&sortOrder=ASCENDING`, follow `next` [O19] | uuid, published, eventType, actor, target, outcome, for the event types below | limit max 1000; 120 a minute (50 on some plans) [O18] | 90 days [O19] |
| Access certifications (optional) | `GET /governance/api/v1/campaigns`, `GET /governance/api/v1/reviews` [O15] | campaign status and dates, review decisions and reviewers (reviews exist only for ACTIVE or COMPLETED campaigns [O15]) | | unverified (not stated on the API pages) |

System Log event types kept (all exist in Okta's event catalogue [O20]): `user.lifecycle.create`,
`user.lifecycle.activate`, `user.lifecycle.suspend`, `user.lifecycle.deactivate`,
`user.account.privilege.grant` and `.revoke`, `group.privilege.grant` and `.revoke`,
`app.oauth2.client.privilege.grant`, `policy.lifecycle.*`, `policy.rule.*`,
`application.user_membership.add`, `user.mfa.factor.activate` and `.deactivate`, `system.api_token.create`
and `.revoke`.

Every service app gets 50 percent of a rate limit bucket by default [O1]. Headers `X-Rate-Limit-Limit`,
`X-Rate-Limit-Remaining`, `X-Rate-Limit-Reset`; 429 when over [O21]. The per minute figures come from
Okta's limits page, whose table loads by script; confirm them in the org's rate limit dashboard.

## 5. Checks

Controls, coverage and rationale: `checks.json` for existing keys, [identity-checks.md](identity-checks.md)
section 2 for new keys.

### 5.1 Existing checks on Okta

| Check | Verdict | Population | Predicate on Okta | Outcomes and traps | API (scope) |
|---|---|---|---|---|---|
| `idp.mfa_enforced` | Supported | Users in ACTIVE, LOCKED_OUT, PASSWORD_EXPIRED, RECOVERY (they can sign in again) | Identity Engine: for every active app, every authentication policy rule that allows access requires two factors, and the global session policy does not let a password alone open a session. Classic: sign on policy rules require a factor. Rules are read in priority order; a higher rule that allows password only for a network zone or group is a gap unless recorded as an exception. **And** each user has an active factor that is not the password or email | fail lists users and rules; error on scope or role refusal. On Identity Engine, Read-only Administrator may be refused the global session policy [O6b]: error "role too narrow", never pass | policies, rules, enrollments (`okta.policies.read`, `okta.users.read`, `okta.authenticators.read`) |
| `idp.sso_enforced` | Partial | Vendor register applications matched to Okta apps | `signOnMode` SAML_2_0, SAML_1_1, OPENID_CONNECT or WS_FEDERATION. AUTO_LOGIN, BROWSER_PLUGIN, BASIC_AUTH and SECURE_PASSWORD_STORE store passwords; BOOKMARK is only a link [O10] | apps missing from Okta are listed as outside it; Okta cannot see local passwords left on the app | apps (`okta.apps.read`) |
| `idp.password_policy` | Supported | Every active PASSWORD policy and the groups it applies to | `minLength`, complexity, `historyCount`, `maxAgeDays`, lockout `maxAttempts` and `autoUnlockMinutes`, common password check meet the customer's standard. Fields confirmed in the SDK models generated from Okta's API spec, under the policy's password settings: `complexity.minLength` (default 8), `age.historyCount`, `age.maxAgeDays`, `lockout.maxAttempts` (default 10), `lockout.autoUnlockMinutes`, `complexity.dictionary.common.exclude` (default false) [G1] | users who sign in through an upstream provider do not use the Okta password; say so | policies (`okta.policies.read`) |
| `idp.session_timeout` | Supported | Global session policy rules; authentication policy rules | `maxSessionIdleMinutes` and `maxSessionLifetimeMinutes` within the standard, `usePersistentCookie` false; app re-authentication interval within the standard | the default idle is 120 minutes and the default lifetime 0, meaning no limit [G1]; per rule, so the weakest rule decides; on Identity Engine, Read-only Administrator may be refused the global session policy [O6b], which reads error, never pass | policies (`okta.policies.read`) |
| `idp.admins_limited` | Supported (role read to test) | Users, groups and clients holding any admin role | Each holder is an active person on Verity's approved list; Super Administrator count within the customer's limit; apps holding SUPER_ADMIN are listed | error (never pass) when the role read is refused | roles (`okta.roles.read`) |
| `idp.access_list_exported` | Supported | All users with groups, apps and roles | Complete export | insufficient when truncated | users, groups, apps |
| `idp.groups_drive_access` | Supported | In scope apps | Every assignment comes through a group: the app user `scope` field is `USER` (direct) or `GROUP` [G1] | fail lists direct assignments | apps (`okta.apps.read`) |
| `idp.connected_apps_known` | Partial | Apps in Okta | Each is approved in the vendor register or marked for removal | Okta does not see OAuth consents staff give inside other platforms | apps |
| `people.leavers_deprovisioned` | Partial | Leavers on the roster in the last 90 days | No user still ACTIVE (or able to sign in) later than the allowed hours after the end date; time from `statusChanged` and `user.lifecycle.deactivate` or `.suspend` | insufficient without a roster | users, System Log |
| `people.joiners_onboarded` | Partial | Users created or activated in the period | Each matches a joiner whose onboarding started first | needs onboarding records | users |
| `tickets.access_requests_approved` | Partial (identity side) | Membership, app assignment and privilege grant events | Supplies grants; approvals come from ticketing | 90 days of log | System Log |

### 5.2 New checks on Okta

| Check key (NEW) | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `idp.admin_mfa_phishing_resistant` | Admin role holders | The Okta Admin Console app's authentication policy requires a phishing resistant possession factor (rule constraint `possession.phishingResistant` = `REQUIRED` [G1]), and each admin has a security key or another phishing resistant authenticator enrolled | partial: Okta names passkeys (FIDO2 WebAuthn) and Okta FastPass as phishing resistant, not Okta Verify push or codes [O27]; an `okta_verify` enrolment does not show which, so those admins read insufficient | daily | policy rule, admin enrollments | IAM-03, IAM-07 partial |
| `idp.no_inactive_accounts` | Users older than `inactive_days` that can sign in | `lastLogin` within `inactive_days`; null means never | insufficient when truncated | daily | user, status, lastLogin | IAM-12, IAM-02, HR-03 partial |
| `idp.machine_identities_owned` | Service apps and API tokens | Credential age within `max_credential_days`; API tokens tied to an active admin | partial: Okta apps have no owner field (unverified), so only age is judged. API tokens come from `GET /api/v1/api-tokens` with `okta.apiTokens.read` (userId, created, expiresAt) [O26]; app keys from `GET /api/v1/apps/{appId}/credentials/jwks`. Never call `/credentials/secrets`, whose response carries `client_secret` [G1] | daily | app, key dates, token creator | IAM-10 partial |
| `idp.access_reviews_completed` | Campaigns that ended in the last 90 days | Every review decided, none by the person reviewed, removals applied | not applicable without Okta Identity Governance; error when the app lacks the Access Certifications Administrator role [O15] | daily | campaign, reviews | IAM-02, IAM-07 partial |
| `people.accounts_match_roster` | Users that can sign in | Matched to an active roster person, or a recorded service account | insufficient without a roster | daily | user, match | IAM-12, IAM-01, HR-03 partial |

## 6. Artifacts and objectives it fills

As [identity-checks.md](identity-checks.md) section 3. Okta specific: `session-limit-settings-export`
(IAM-11.B, partly IAM-11.C through the re-authentication interval on the Admin Console's policy) moves from
person to person + `idp.session_timeout`, and Okta is the strongest of the three for `idp.password_policy`.

## 7. Framework reach

As [identity-checks.md](identity-checks.md) section 4.

## 8. Limits and false assurance traps

- **Deprovisioned users are hidden** from the default user list [O8]. A leaver check that reads only the default list misses them; query them explicitly.
- **Rule order.** Policies and rules apply by priority and conditions. A "require MFA" rule below a "password only from the office" rule does not cover the office. Evaluate the order, not the presence.
- **Classic and Identity Engine differ** in policy types and events; `user.authentication.auth_via_mfa` fires only for the second factor in Classic [O20].
- **Role read refused** must read error, never "no admins".
- **Public client app admins** gives apps Super Administrator silently [O1]. The setup guide checks it.
- **Upstream identity providers.** When an identity provider in Okta has "Trust AMR claims from this identity provider" (or Okta to Okta claims sharing) on, Okta counts the upstream factors toward its policies [O28]. Reading that setting needs `okta.idps.read` [O16], which the first version does not request, so those users read insufficient unless the policy demands an Okta factor.
- **90 day log** [O19]. Leaver times older than that come only from Verity's snapshots.
- **Rate limits are shared** with the customer's other integrations. A full factor read for a large org is slow; record `truncated` rather than retry forever.

## 9. Product and UI

- **Connect form.** Okta domain, client ID, the public key Verity generated (copy button), the scope list (copy button). SSWS token as a fallback field, with a warning.
- **Scope.** The whole org. Per user exclusions with a reason.
- **Health states.** Connected; scope not granted (named); role too narrow (named checks); DPoP required but failing; throttled; key due for rotation (yearly by default, a Verity setting since the key has no provider expiry; rotating needs a Super Administrator once the app has Okta scoped grants [O1]).
- **In product guide.** Yes: seven steps, a Super Administrator, and the "Public client app admins" trap.

## 10. Implementation notes

- **Auth.** SDK `WithAuthorizationMode("PrivateKey")`, `WithClientId`, `WithScopes`, `WithPrivateKey`, `WithPrivateKeyId` [G1]. Client assertion `exp` at most one hour ahead [O1]. DPoP: first token call returns `use_dpop_nonce` and a `dpop-nonce` header; resend with the nonce; resource calls send `Authorization: DPoP <token>` plus a proof with `ath` [O3]. The DPoP key is separate from the client key [O3].
- **Token URL.** `https://{oktaDomain}/oauth2/v1/token` (org authorization server) [O22].
- **Scope drift.** Request the full scope list; if Okta refuses it, request scopes one at a time to name the missing one (refusal behaviour for a partly granted list is unverified: the service app guide says only that each requested scope is checked against the app's grants [O1]; test).
- **Paging.** Link header `next` until absent [O17]. System Log polling: no `until`, ascending order, follow `next` until a page is empty (the `next` link is always present when polling). Polling orders events by when Okta stored them, which can differ from `published`, so store the last `next` link as the cursor, not the last `published` and uuid [O19] (corrected 2026-11-23).
- **Error mapping.** 401: credential or key problem (connection error). 403: scope or role (checks error). 429: wait until `X-Rate-Limit-Reset`. `invalid_dpop_proof`: DPoP setting mismatch, health message [O23].
- **Deletion semantics.** DEPROVISIONED keeps the user; a deleted user disappears; Verity's snapshots keep the trail.
- **Fixtures.** Record from an Okta developer or Integrator Free Plan org (both Classic and Identity Engine where possible). Seed: a deprovisioned user, a suspended user, a user with only a password, an admin with a security key, a group assigned app, a direct assignment, an SWA app, a rule allowing password only from a zone.

## 11. How comparable platforms do it

| Platform | Connection | Scopes or role | Tests named |
|---|---|---|---|
| Vanta | Customer API Services app with private key JWT, assigned **Super Administrator**; SSWS token as fallback [V1] | `okta.appGrants.read`, `okta.apps.read`, `okta.groups.read`, `okta.policies.read`, `okta.roles.read`, `okta.users.read` [V1] | MFA on Okta (an active factor), deprovisioning of terminated users; password policies kept as evidence [V2] |
| Drata | API token from a Read-only Administrator service account; its OIN OIDC app is for sign in only (`okta.users.read.self`) [D1] | role as above | MFA on identity provider, unique emails [D1] |
| Sprinto | API token from Super, Org, Group, Group Membership or Read-only Administrator [P1] | `okta.apps.read`, `okta.users.read` [P1] | MFA disabled, offboarded user [P1] |
| Secureframe | unverified | unverified | unverified |

Vanta's choice of Super Administrator suggests Read-only Administrator does not read everything it needs
(an inference). Whether Vanta or Drata are listed as OIN API service integrations is unverified: their OIN
pages show the capability list only as a site wide filter, so the integration type is not readable [O24].

## 12. Sources

- O1 Service app OAuth: https://developer.okta.com/docs/guides/implement-oauth-for-okta-serviceapp/main/
- O2 Release notes 2024 (DPoP GA, service integration roles): https://developer.okta.com/docs/release-notes/2024-okta-identity-engine/
- O3 DPoP: https://developer.okta.com/docs/guides/dpop/oktaresourceserver/main/
- O4 API tokens: https://developer.okta.com/docs/guides/create-an-api-token/main/
- O5 Role for a service app: https://support.okta.com/help/s/article/how-to-assign-the-correct-admin-role-to-a-service-application
- O6 Admin role comparison (Classic): https://help.okta.com/en-us/content/topics/security/administrators-admin-comparison.htm
- O6b Admin role comparison (Identity Engine): https://help.okta.com/oie/en-us/content/topics/security/administrators-admin-comparison.htm
- O7 Custom role permissions: https://developer.okta.com/docs/api/openapi/okta-management/guides/permissions/
- O8 List users: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/user/other/listusers
- O9 Factors and authenticator enrollments: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/userfactor/other/listfactors and https://developer.okta.com/docs/api/openapi/okta-management/management/tags/userauthenticatorenrollments
- O10 Apps: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/application/other/listapplications, https://developer.okta.com/docs/api/openapi/okta-management/management/tags/applicationusers/other/listapplicationusers, https://developer.okta.com/docs/api/openapi/okta-management/management/tags/applicationgroups/other/listapplicationgroupassignments
- O11 Policies and rules: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/policy/other/listpolicies and https://developer.okta.com/docs/api/openapi/okta-management/management/tags/policy/other/listpolicyrules
- O12 Authenticators: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/authenticator/other/listauthenticators
- O13 Role assignments: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/roleassignmentauser/other/listuserswithroleassignments, https://developer.okta.com/docs/api/openapi/okta-management/management/tags/roleassignmentauser/other/listassignedrolesforuser, https://developer.okta.com/docs/api/openapi/okta-management/management/tags/roleassignmentbgroup/other/listgroupassignedroles, and client roles (`listRolesForClient`) in the management API spec mirrored at https://github.com/okta/okta-sdk-golang/blob/v9.0.0/okta/api/openapi.yaml
- O14 System Log API: https://developer.okta.com/docs/api/openapi/okta-management/management/tags/systemlog/other/listlogevents
- O15 Identity Governance: https://developer.okta.com/docs/api/iga/, https://developer.okta.com/docs/api/iga/oauth2, https://developer.okta.com/docs/api/iga/openapi/governance.api/tags/campaigns/ and https://developer.okta.com/docs/api/iga/openapi/governance.api/tags/reviews/ (each operation names its admin role)
- O16 Scope list: https://developer.okta.com/docs/api/oauth2/
- O17 Pagination: https://developer.okta.com/docs/api/
- O18 Rate limits: https://developer.okta.com/docs/reference/rl-global-mgmt/
- O19 System Log query and retention: https://developer.okta.com/docs/reference/system-log-query/
- O20 Event types: https://developer.okta.com/docs/okta-event-types.csv
- O21 Rate limit headers: https://developer.okta.com/docs/reference/rl2-monitor/
- O22 API service integrations: https://developer.okta.com/docs/guides/build-api-integration/main/
- O23 DPoP header missing: https://support.okta.com/help/s/article/the-dpop-proof-jwt-header-is-missing
- O24 OIN pages: https://www.okta.com/integrations/vanta/ and https://www.okta.com/integrations/drata/
- O25 Set up OAuth API access (client ID and secret not allowed for service apps): https://developer.okta.com/docs/guides/set-up-oauth-api/main/
- O26 API tokens (`listApiTokens`, `okta.apiTokens.read`): https://developer.okta.com/docs/api/openapi/okta-management/management/tags/apitoken/, the scope list O16, and the API spec in G1 (which assigns `okta.apiTokens.read` to `listApiTokens`)
- O27 Phishing resistant authentication: https://help.okta.com/oie/en-us/content/topics/identity-engine/authenticators/phishing-resistant-auth.htm
- O28 AMR claims mapping and claims sharing: https://developer.okta.com/docs/guides/configure-amr-claims-mapping/main/ and https://developer.okta.com/docs/guides/configure-claims-sharing/oktaoidc/main/
- G1 Go SDK and models: https://github.com/okta/okta-sdk-golang and https://github.com/okta/okta-sdk-golang/tree/master/okta/docs (v9.0.0 models: `PasswordPolicyPasswordSettings*`, `OktaSignOnPolicyRuleSignonSessionActions`, `AppUser`; API spec `okta/api/openapi.yaml`)
- V1 Vanta quickstart: https://help.vanta.com/en/articles/15062074-okta-quickstart
- V2 Vanta guide: https://help.vanta.com/en/articles/15082003-okta-integration-guide.md
- D1 Drata: https://help.drata.com/en/articles/5608136-okta-integration-guide-identity-management-provider
- P1 Sprinto: https://docs.sprinto.com/integrations/overview/okta-integration.md

## Decisions for the owner

1. Admin role for the service app: Read-only Administrator plus whatever the developer org test shows, or Super Administrator as Vanta does. Recommended: test first, never ask for Super Administrator by default. New option from the 2026-11-23 check: a custom admin role with `okta.iam.read` and `okta.policies.read` (plus the read permissions for users, groups and apps), since Okta lists viewing administrators and Identity Engine global session policies outside Read-only Administrator; Access Certifications Administrator only if access reviews are collected.
2. Allow the SSWS token fallback or not (recommended: allow, marked weaker on the connection).
3. Customer created service app (private key JWT) versus an OIN API service integration (client secret only). See the unified setup document.
