# Identity providers: one setup for sign in and evidence

The owner wants each customer to set up Entra ID, Okta or Google Workspace once, and have that one setup
cover both **sign in to Verity through Keycloak** and **evidence collection**. This document compares three
ways to do it per provider, then recommends one. Provider details: [entra-id.md](entra-id.md),
[okta.md](okta.md), [google-workspace.md](google-workspace.md). Researched 2026-11-23.

## 1. Where we start

| Fact | Source |
|---|---|
| Sign in: the customer registers an app at their provider and pastes its client ID and secret into Verity; Verity creates the identity provider in Keycloak and the secret goes to Keycloak only, never to Verity's database, logs or audit rows | [sso-providers.md](../../../runbooks/sso-providers.md) sections 2, 5 |
| In production Keycloak is run by Infowise, not Verity. One realm serves every customer; each customer is a Keycloak organization | [keycloak-production.md](../../../runbooks/keycloak-production.md) sections 1, 2 |
| Each customer's provider in Keycloak has its own redirect URI: `https://<keycloak>/realms/<realm>/broker/<org>-<provider>/endpoint` | sso-providers.md section 2 |
| The runbook already says: keep two credentials per provider, show one integration card | sso-providers.md section 7; [02-integration-model.md](../02-integration-model.md) section 2.1 (`tenant_sso.connection_id`) |
| Evidence needs app only access: Microsoft Graph application permissions, an Okta API Services app, a Google service account with delegation | the three provider documents, section 2 |

So "one setup" is a product question (one guided flow, one card) and a security question (one credential
or two). They have different answers.

## 2. Can one app do both?

| Provider | One app technically possible? | What it would mean |
|---|---|---|
| Entra ID | Yes. An app registration can hold the delegated sign in permissions and Graph application permissions; application permissions are used by whoever holds the app's credential, through client credentials [M1] | Keycloak would hold a credential that reads the customer's whole directory |
| Okta | No, in practice. Client credentials with `okta.*` scopes are documented for API Services apps. A Web app shows the client credentials grant only when the org bought an NHI Authentication Token subscription [K1][K2] | Two apps are required |
| Google Workspace | Not meaningfully. Sign in uses an OAuth web client; evidence uses a service account with delegation. Using the sign in client for admin consent too (three legged OAuth) would need the client secret in both Keycloak and Verity, and ties evidence to one admin's refresh token | Two credentials either way |

## 3. The three options per provider

(a) one app registration for both; (b) two apps created in one guided flow; (c) a Verity owned
multi tenant app or marketplace listing with one click consent.

### 3.1 Microsoft Entra ID

| | (a) One app | (b) Two customer apps, one flow | (c) Verity multi tenant app |
|---|---|---|---|
| Customer does | One registration with a redirect URI, sign in and Graph application permissions, admin consent, one secret pasted | App 1 for sign in exactly as today; app 2 for evidence: no redirect URI, application permissions, upload the certificate Verity generated, admin consent. About 10 steps in one sitting | Evidence: press Connect, sign in as Global Administrator or Privileged Role Administrator, Accept [M2][M3]. Sign in: app 1 as today (see below) |
| Verity does once | Nothing | The wizard and certificate generation | Partner Center account in the Microsoft AI Cloud Partner Program, Partner One ID, publisher domain, publisher verification (free) [M4]; one registered redirect URI for the admin consent response, which the endpoint requires [M2]; a signing key in a store it cannot be exported from; rotation and leak procedures |
| Credential | A secret (Keycloak needs one; whether this Keycloak build can use a signed JWT with Entra instead is unverified: it depends on Infowise's build, decision 8); 24 months at most [M5] | Sign in: secret in Keycloak. Evidence: Verity's private key, per customer | One Verity certificate for every consenting customer |
| Main risk | Keycloak, run by a third party, holds a directory read credential; one expiry breaks sign in and evidence together | More steps for the customer | One stolen key reads every consenting tenant's directory |
| Lead time | none | none | Microsoft says publisher verification takes minutes once the partner account is verified [M4]; how long Partner Center takes to verify the account is not stated (unverified) |

A Verity owned multi tenant app for **sign in** as well is possible but has two costs: every customer's
Keycloak broker URI must be registered on it, and Entra allows at most 256 redirect URIs per app, a limit
that cannot be raised [M6]; and Keycloak would hold one Verity secret used for every customer's sign in.
Sign in stays customer owned.

### 3.2 Okta

| | (a) One app | (b) Two customer apps, one flow | (c) OIN listing |
|---|---|---|---|
| Customer does | Not available without the NHI subscription [K2] | OIDC Web app for sign in (as today); API Services app for evidence: paste Verity's public key, grant scopes, assign Read-only Administrator. A Super Administrator once [K1] | Install Verity's API service integration from the catalogue, grant its scopes; Okta shows a client ID and secret once, which the admin pastes into Verity [K3] |
| Verity does once | | The wizard and key generation | An Integrator Free Plan org, submission through the OIN Wizard by a super admin (or an admin holding both the app and org admin roles) signed in with a company domain email, initial review then QA; Okta emails dates, no fixed lead time [K4][K5]. Corrected 2026-11-23: a super admin is not the only role allowed |
| Credential | | Private key JWT, per customer, key never leaves Verity | Client secret only: Okta generates a client ID and secret per install, and the submission offers no other client authentication [K3][K4] (reworded: the page does not say "not supported" in those words) |
| Main risk | | More steps | A copyable secret crosses a person; Okta lets orgs assign admin roles to API service integrations since 2024.02.0 [K6], but which role an install gets by default is not stated (unverified) |

An OIN OIDC listing for sign in would need each customer's own Keycloak broker URI. OIN OIDC integrations
allow up to eight tenant setting variables that admins fill in at install, usable inside redirect URIs
[K7], so a per customer broker URI is possible (resolved 2026-11-23).

### 3.3 Google Workspace

| | (a) One OAuth client | (b) Sign in client plus delegation, one flow | (c) Verified OAuth app or Marketplace app |
|---|---|---|---|
| Customer does | Sign in client as today, then an admin consents to admin scopes on the same client | Sign in client as today (Internal, no verification [G1]); in the Admin console, paste Verity's service account client ID and scopes into domain wide delegation [G2] | Sign in as an admin and approve, or install from the Marketplace |
| Verity does once | Nothing | A Google Cloud project and service account, signing without a stored key (google-workspace.md 2.1) | OAuth verification: brand 2 to 3 business days, sensitive scopes about 10 business days, restricted scopes 6 weeks plus a yearly security assessment [G3]; Marketplace review "several days" after that [G4] |
| Credential | Client secret in Keycloak and in Verity, plus an admin's refresh token | Sign in: secret in Keycloak. Evidence: Verity's service account, delegation per customer | Verity's OAuth client and each admin's refresh token |
| Main risk | Secret in two places; evidence dies when that admin leaves; Policy API by this route unverified (its setup guide documents only a service account with delegation, google-workspace.md W26) | One Verity service account serves all customers (delegation is still per customer, read only) | Verification work and the 100 user cap until verified [G3] |

Domain wide delegation already behaves like a Verity owned app with one consent step, without Google's
app verification, so (c) buys nothing for evidence.

## 4. Security trade offs

| Question | (a) | (b) | (c) |
|---|---|---|---|
| Does Keycloak (run by Infowise) hold a credential that can read the customer's directory? | Yes (Entra; Google variant) | No | No |
| Can one stolen Verity credential read many customers? | No | Entra, Okta: no, keys are per customer. Google: the service account is shared, delegation is per customer | Entra: yes, one certificate. Okta OIN: no, secrets are per install |
| Does a secret pass through a person? | Yes | Only the sign in secret, as today | Okta OIN: yes. Entra, Google: no |
| Does one expiry break both sign in and evidence? | Yes | No | No |
| Can the customer revoke evidence alone? | No, it breaks sign in | Yes: delete app 2, or remove the delegation | Yes: remove the enterprise app or uninstall |

In every option Verity's core holds every customer's evidence credential, encrypted
(01-evidence-model.md 1.5). The Entra multi tenant certificate adds a single key outside the database that
needs no per customer record to use. If option (c) is built for Entra, the key must sign through a key
service that never exports it. `azidentity.NewClientAssertionCredential(tenantID, clientID, getAssertion,
options)` takes a callback that returns the signed assertion, so the key service can sign it [M7]
(resolved 2026-11-23).

## 5. How Vanta and Drata connect these providers

| Provider | Vanta | Drata |
|---|---|---|
| Entra ID | Admin consent to Vanta's app by Global Administrator or Privileged Role Administrator; sync by client credentials [V1] | Global Administrator consent creates an enterprise application [D1] |
| Okta | Customer API Services app with private key JWT, assigned Super Administrator; API token as fallback [V2] | API token from a Read-only Administrator service account; a separate OIN OIDC app serves sign in to Drata only [D2] |
| Google Workspace | OAuth consent by a super admin; publishes its client IDs for customers to trust [V3] | OAuth by an admin, or a service account with domain wide delegation [D3] |

Both keep sign in to their own product separate from evidence (Drata documents it for Okta; for Vanta it
is unverified). Neither merges them into one credential, as far as their pages show.

## 6. Recommendation

1. **Two credentials, one guided setup, one card.** Reject (a) for all three providers. For Entra it puts a
   directory read credential in a system Verity does not run; for Okta it is not available; for Google it
   gains nothing. The card is the `tenant_sso.connection_id` design already planned.
2. **Launch with (b).** One wizard per provider: step 1 sign in (as today), step 2 evidence, step 3 test
   both (one SSO sign in, one evidence run). Verity generates the evidence key pair for Entra (certificate)
   and Okta (public key), so no evidence secret is ever typed. Google evidence uses domain wide delegation to
   Verity's own service account.
3. **Then (c) for Entra evidence only**, after the first Entra pilot: publisher verification and an admin
   consent button cut step 2 to one click. Build it only with a non exportable signing key. Sign in stays a
   customer app.
4. **Skip the Okta OIN API listing** until a sales need appears. It costs a review cycle and downgrades the
   credential to a client secret.
5. **Skip Google OAuth verification and the Marketplace.** Delegation covers evidence; the sign in client
   is the customer's Internal app.
6. **Lifecycle stays separate.** SCIM from Entra and Okta into Keycloak (sso-providers.md section 6) is a
   third piece. The wizard can offer it as an optional step 4 later, but it writes into Keycloak, so it is not
   an evidence permission.

## 7. Decisions for the owner

1. Approve the two credential rule for every provider, including Entra (recommended yes).
2. Entra: launch with customer owned evidence apps (b) and add Verity's multi tenant app (c) after the pilot, or invest in (c) now. Either way, join the Microsoft AI Cloud Partner Program for publisher verification.
3. Accept the concentration risk of one Verity certificate for all Entra customers, conditional on a non exportable signing key (needs an ADR, AUTHORING and integrations.md non negotiables).
4. Google: how Verity's service account signs without a stored key (AWS federation, an OIDC issuer Verity hosts, or a key with the default policy overridden for one project).
5. Google: ask customers for a super admin as the delegated subject, or accept a read only admin and three checks that say "needs a super admin".
6. Okta: Read-only Administrator plus whatever a developer org test shows, a custom admin role with `okta.iam.read` and `okta.policies.read` (okta.md section 2), or Super Administrator as Vanta asks.
7. Which provider goes first (the pilot customer's, per continuous-compliance-plan.md section 7).
8. Who confirms with Infowise that their Keycloak build can (or cannot) authenticate to Entra with a signed JWT instead of a secret, which would remove the 24 month secret expiry from sign in.

## 8. Sources

- M1 Admin consent and application permissions: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent
- M2 Admin consent endpoint: https://learn.microsoft.com/en-us/entra/identity-platform/v2-admin-consent
- M3 Vanta's required Entra roles (also V1)
- M4 Publisher verification: https://learn.microsoft.com/en-us/entra/identity-platform/publisher-verification-overview
- M5 App credentials: https://learn.microsoft.com/en-us/entra/identity-platform/how-to-add-credentials
- M6 Redirect URI limits (256, cannot be raised): https://learn.microsoft.com/en-us/entra/identity-platform/reply-url
- M7 azidentity client assertion credential: https://pkg.go.dev/github.com/Azure/azure-sdk-for-go/sdk/azidentity#NewClientAssertionCredential
- K1 Okta service app OAuth: https://developer.okta.com/docs/guides/implement-oauth-for-okta-serviceapp/main/
- K2 Okta OIDC app wizard (client credentials on Web apps needs NHI subscription): https://help.okta.com/oie/en-us/content/topics/apps/apps_app_integration_wizard_oidc.htm
- K3 Okta API service integrations: https://developer.okta.com/docs/guides/build-api-integration/main/
- K4 Submit an API service integration (client secret only): https://developer.okta.com/docs/guides/submit-apiservice-app/main/
- K5 OIN submission overview and wizard: https://developer.okta.com/docs/guides/submit-app-overview/ and https://developer.okta.com/docs/guides/submit-oin-app/openidconnect/main/
- K6 Okta release notes 2024 (admin roles for API service integrations, 2024.02.0): https://developer.okta.com/docs/release-notes/2024-okta-identity-engine/
- K7 OIN OIDC tenant settings and dynamic redirect URIs: https://developer.okta.com/docs/guides/submit-oin-app/openidconnect/main/
- G1 Google verification exceptions (Internal apps): https://support.google.com/cloud/answer/13464323
- G2 Domain wide delegation: https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation
- G3 Verification timelines and user cap: https://support.google.com/cloud/answer/13463817
- G4 Marketplace review: https://developers.google.com/workspace/marketplace/about-app-review
- V1 https://help.vanta.com/en/articles/11345655-connecting-vanta-microsoft-entra
- V2 https://help.vanta.com/en/articles/15062074-okta-quickstart
- V3 https://help.vanta.com/en/articles/14977969-google-workspace-integration-guide.md
- D1 https://help.drata.com/en/articles/4797766-microsoft-365-integration-guide
- D2 https://help.drata.com/en/articles/5608136-okta-integration-guide-identity-management-provider
- D3 https://help.drata.com/en/articles/4663303-google-workspace-integration-guide
