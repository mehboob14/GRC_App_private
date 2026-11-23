# Connecting identity providers through Keycloak

How a customer's Entra ID, Google Workspace, Okta or SAML provider is connected to Verity, what each
side configures, how to test it, and how a developer adds a provider. Spec:
`openspec/changes/add-keycloak-sso/` (phase E is the work this guide drives). ADRs 0006 and 0015.
Local Keycloak: `docs/runbooks/keycloak-local.md`.

## 1. What the contract asks for

From the signed requirements specification:

| Where | What it says | What it means here |
|---|---|---|
| Deliverable 3.2 (Phase 3) | Single sign on with Azure AD and Entra ID and Google Workspace. | Entra ID and Google Workspace sign in are contract scope. |
| Section 8, connector catalogue (Phase 2) | Identity and directory: Okta, Google Workspace, Microsoft 365 and Entra ID, 1Password. | Read only **evidence** connectors, a separate piece of work. Okta **sign in** is not named in the contract; it is the owner's request. |
| Deliverable 3.2 | Access reviews pull who has access from connected systems. | Needs the directory data the lifecycle work below brings in. |
| Assumptions | The organisation provides test accounts per system and supports app registration (Google, Microsoft), with external verification lead times. | The owner (or the customer) creates the test tenants and app registrations. |

ADR-0006 also lists JIT provisioning, SCIM lifecycle sync and IdP managed MFA for this phase. JIT, sync
and MFA at the IdP are built (phases A to D). ADR-0006 said Verity would expose its own SCIM endpoint;
ADR-0015 changed that to "lifecycle comes from Keycloak, whatever feeds Keycloak". Section 6 shows what
that needs on this Keycloak build.

## 2. One pattern for every provider

```
Customer's provider  ──OIDC or SAML──>  Keycloak (identity provider "<org>-<provider>",
(Entra, Google, Okta, SAML)              linked to the customer's organization)
                                                │ OIDC, organization + identity_provider claims
                                                v
                                         Verity (its own session, roles, audit)
```

The admin of a Verity workspace does it all from **Settings, Security, SSO**:

1. Save the Keycloak organization alias and the email domains.
2. Prove each domain with the TXT record the page shows (`_verity.<domain>`).
3. **Connect**: pick the provider, copy the redirect URI shown in the popup into the provider, paste
   back the client ID and secret (or the metadata URL for SAML). Verity creates the identity provider in
   Keycloak, links it to the organization and routes the proven domains to it. The secret goes to
   Keycloak only.
4. Sign in with SSO once (this proves the setup), then optionally **Require SSO**, **Create accounts
   automatically**, and **Add group**.

The redirect URI is always `https://<keycloak>/realms/<realm>/broker/<org>-<provider>/endpoint`. For
SAML the same URL is the ACS URL, and the SP entity ID is `https://<keycloak>/realms/<realm>`.

What Verity sets on every Keycloak identity provider (`modules/iam/idp_templates.py`): signature checks,
PKCE (OIDC), `syncMode FORCE` (name and email follow the provider at each sign in), hidden from the
Keycloak login page, and `trustEmail`. Trusting the email is safe only because Verity confines a
workspace's provider to that workspace and its DNS proven domains (ADR-0015 decision 6). Never turn
that containment off.

## 3. Provider by provider

### Microsoft Entra ID (contract)

At the provider (Entra admin center):
1. App registrations, New registration. Supported account types: **this organizational directory only**
   (single tenant). Redirect URI: platform **Web**, the URI from the Connect popup.
2. Certificates and secrets: new client secret. Note its expiry (24 months at most); Keycloak does not
   warn before it lapses.
3. API permissions: Microsoft Graph delegated `openid`, `profile`, `email`; grant admin consent.
4. Token configuration: add the optional ID token claim `email`. Entra only sends an email for users with
   a mail address, and sends no `email_verified`.
5. Enterprise applications, the app, Properties: **Assignment required: Yes**, then assign the people or
   groups allowed in. MFA and device rules stay in Conditional Access.

In Verity: provider **Microsoft Entra ID**, the directory (tenant) ID, client ID, secret.

Watch for: users without a mail address (no email, refused as "no account"); an Entra admin can set any
address as a user's mail, which is why containment refuses emails outside the proven domains; the
`groups` claim carries group object IDs, not names, so prefer SCIM for groups (section 6).

### Google Workspace (contract)

At the provider (Google Cloud console, a project owned by the customer's Workspace):
1. OAuth consent screen: user type **Internal** (only the Workspace's users; no Google verification
   needed for `openid email profile`).
2. Credentials, Create credentials, OAuth client ID, **Web application**. Authorized redirect URI: the
   URI from the Connect popup.

In Verity: provider **Google Workspace**, client ID, secret. Verity sets Keycloak's hosted domain to the
first proven domain, so only accounts of that Workspace domain get through.

Watch for: a customer with several Workspace domains (only the first is enforced as hosted domain; the
others still pass containment); Google does not push SCIM to custom apps, so lifecycle needs another
route (section 6).

### Okta (owner's request, not named in the contract's SSO line)

At the provider (Okta Admin Console):
1. Applications, Create App Integration, **OIDC**, **Web Application**. Grant type Authorization Code.
   Sign in redirect URI: the URI from the Connect popup.
2. Assignments: the people or groups allowed in (only assigned users can sign in).
3. Optional: Sign On tab, groups claim filter, if groups should travel in the token.

In Verity: provider **Okta**, the Okta domain (`acme.okta.com`), client ID, secret. Verity uses the org
authorization server (`https://<domain>`).

Watch for: a customer that uses a custom authorization server (`/oauth2/default`) needs the "Other
OpenID Connect provider" option with that discovery URL instead.

### Any other OpenID Connect provider

Provider **Other OpenID Connect provider** with its discovery URL (HTTPS), client ID, secret. Used today
for the local stand-in IdP. Works for Auth0, Ping, JumpCloud, Keycloak and others.

### SAML (not in the contract; only when a customer has no OIDC)

At the provider: ACS URL and SP entity ID from the popup, NameID format **email address**, signed
assertions. In Verity: provider **SAML**, the provider's metadata URL (HTTPS). Certificate rollover is
the customer's; a rolled certificate needs Connect again.

## 4. What every connection is tested for

Run these on each provider's test tenant before calling it supported:

1. Email first sign in routes straight to the provider (no Keycloak page in between).
2. A member signs in and lands in the right workspace; the session audit row names the provider
   (`identity_provider`), `acr` and `amr`.
3. MFA happens at the provider (Conditional Access, Okta policy, Google 2SV), and Verity asks for no TOTP.
4. A user not assigned to the app is stopped by the provider.
5. An address outside the proven domains is refused by Verity (`wrong_domain`).
6. With **Create accounts automatically** on, a new person joins with the default role.
7. **Require SSO** blocks password sign in; an Admin with TOTP still gets in (break glass).
8. Sign out ends the provider session in Keycloak, and back-channel logout ends Verity sessions.
9. A person disabled at the provider cannot sign in again.
10. With a lifecycle feed (section 6): a leaver is disabled at the next sync, group changes move roles.

## 5. Adding a provider (developers)

1. `modules/iam/idp_templates.py`: add the key to `PROVIDERS` and `LABELS`, where Keycloak imports its
   configuration from (`import_source`, HTTPS only outside local), and any provider specific settings in
   `representation`.
2. A migration that widens `ck_tenant_sso__provider_valid` (hand written, with downgrade), and the
   `provider` pattern in `schemas.SsoProviderPut`.
3. The Connect popup (`features/iam/components/sso-settings-page.tsx`): the fields the provider needs.
4. Tests: the template in `tests/unit/test_sso_setup.py` against the fake Keycloak, the flow in
   `tests/integration/test_sso_setup_flow.py`.
5. The live checklist (section 4) on a real tenant, then a section here.

Rules that do not bend: the client secret never reaches Verity's database, logs or audit rows; routing
and trust only for proven domains; a provider set up by a workspace stays held to that workspace.

## 6. Lifecycle: how leavers and groups reach Verity

Verity's sync reads the Keycloak **organization**: its members, and each member's organization groups.
Brokered sign in alone never tells Keycloak someone left, so a feed is needed:

| Provider | Feed into Keycloak | Status |
|---|---|---|
| Entra ID | Enterprise application provisioning (SCIM 2.0) to Keycloak's SCIM server | Planned, E.3 |
| Okta | SCIM provisioning (set on a provisioning app integration; confirm the app type on the test tenant) | Planned, E.4 |
| Google Workspace | No SCIM push. Directory API through the Phase 2 Google Workspace connector, or Keycloak LDAP on editions with Secure LDAP | Decision needed |
| SAML / other | Whatever the provider offers (SCIM, LDAP) | Per customer |

**Gap found on this Keycloak build:** its SCIM server (`/realms/<realm>/scim/v2`) has no notion of
organizations. SCIM users and groups land in the realm, not in the customer's organization. Effect today:
deactivating or deleting a user who has signed in once works (the sync sees them disabled or gone), but
pre-created users and SCIM groups do not reach Verity until it reads them. Fix planned in E.3: the sync
also reads a member's realm groups, and finds realm users by proven domain. Confirm with Infowise how
their build behaves before building it.

SCIM from Entra or Okta calls Keycloak from the internet, so it needs Keycloak on a public HTTPS address
(a staging Keycloak or a tunnel). Sign in alone works with Keycloak on localhost.

## 7. Evidence from the same providers (later)

The Phase 2 connectors read Entra, Google Workspace and Okta for evidence (MFA coverage, admin roles,
users). Keep two credentials per provider: the sign in app (`openid email profile`, nothing more) and a
separate read only API app for evidence. One "integration" card per provider in the interface can show
both (design section 12: `tenant_sso` gains a `connection_id`), but merging the two credentials would
give the sign in app directory read rights it does not need.
