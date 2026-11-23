# Design: sign in through Keycloak

Builds on ADR-0006 (native first, one seam, authorization stays in Verity, one shared realm with the
tenant carried as a claim) and records the new choices in ADR-0015.

## 1. Shape

```
Browser ── Verity web ── Verity API ──(OIDC, confidential client)── Keycloak realm "verity"
                                    └─(Admin API, service account, later)──┘   │
                                                                              ├─ organization per tenant
                                                                              │   (domains, linked IdPs)
                                                                              └─ brokered IdPs: Entra ID,
                                                                                 Okta, Google, any OIDC/SAML
```

Two integrations, as in the owner's brief: Verity to Keycloak (built here, once), and customer IdP to
Keycloak (configuration inside Keycloak, automated by Verity from phase C). Verity trusts one issuer.

## 2. Sign in (service provider initiated, email first)

1. The sign in page has "Sign in with SSO". The person types a work email.
2. `GET /auth/sso/start?email=` returns an authorization URL. The API generates `state`, `nonce` and a
   PKCE S256 verifier, keeps them in Redis under the state for ten minutes (single use), and adds
   `login_hint` and the scopes `openid email profile organization`. When the email's domain belongs to a
   tenant's SSO record (phase B), it requests `organization:<alias>` so Keycloak routes to that
   organization's identity provider without asking again.
3. Keycloak runs identity-first login: the domain picks the organization, the organization's linked IdP
   takes over, the user authenticates there, and Keycloak's first broker login adds them to the
   organization.
4. `GET /auth/sso/callback?code&state` (the API): pops the state, exchanges the code with the client
   secret, validates the ID token (signature against the cached JWKS, `iss`, `aud`, `azp`, `exp`, `nonce`),
   and reads `sub`, `email`, `email_verified`, `organization`, `acr`, `amr`.
5. It resolves the person (section 3) and stores a one time handoff in Redis for sixty seconds, then
   redirects the browser to the web app's `/sso/complete?handoff=`.
6. The web app posts the handoff to `POST /auth/sso/complete`, which returns the same shape as password
   sign in: a session, or a workspace choice. The handoff never carries a token in a URL.

Failures (bad state, expired state, IdP error, invalid token, unknown person) redirect to
`/sso/complete?error=<code>` with a fixed reader message per code; details go to the log only.

## 3. Who is this

1. `user_identities (provider='keycloak', external_subject_id=sub)` finds a linked user.
2. Otherwise, when `email_verified` is true and a Verity user has that email, link them (one audit row).
   Keycloak sets `email_verified` from the IdP only when the IdP link is configured to trust email, which
   the phase C setup does per organization.
3. Otherwise, phase D: when the organization maps to a tenant with just in time provisioning on, create
   the user and an active membership with the tenant's default role.
4. Otherwise refuse: "There is no Verity account for this email. Ask your workspace admin to invite you."

A disabled user, or a user with no active membership, is refused as with a password.

## 4. Which workspace

The `organization` claim names organizations the person belongs to in Keycloak. When exactly one maps to
a Verity tenant and the person holds an active membership there, that membership gets the session. When
none maps (local Keycloak users, phase A), the person's active memberships decide as with a password: one
gives a session, several give a workspace choice. The claim never grants a membership: a person must hold
one in Verity (ADR-0006, decision 4).

## 5. Session, MFA and sign out

- The session is Verity's own token, issued by `_grant_session(..., method="sso")`. The session audit row
  records the issuer, `acr`, `amr` and the organization.
- MFA for SSO sign ins is the identity provider's job (ADR-0006, decision 6): Verity's TOTP step is
  skipped. A tenant option to require a minimum `acr` is noted for phase F.
- The ID token is kept server side in Redis under the session's `jti` for the session's lifetime. Sign out
  returns Keycloak's end session URL with `id_token_hint` and `post_logout_redirect_uri`, and the web app
  goes there, so the Keycloak session ends too.
- The brief suggested HttpOnly cookies. Verity's session is a bearer token platform wide; changing that is
  its own change, and Keycloak's tokens stay on the server either way.

## 6. Configuration

`OIDC_*` settings: `enabled` (false by default), `issuer_url`, `client_id`, `client_secret`,
`redirect_url` (the API callback), `web_url` (for `/sso/complete` and post logout), `scopes`,
`provider_key` (`keycloak`), `timeout_seconds`. Discovery reads `/.well-known/openid-configuration`
once; the JWKS is cached and refreshed on an unknown `kid`. Moving from the local Keycloak to the client's
is a configuration change only.

## 7. Tenant SSO record (phase B, built 2026-11-23)

`tenant_sso` (migration 4b8e1d6a9c27): `organization_alias` (unique across tenants: one Keycloak
organization is one workspace), `domains`, `enabled`, `enforce`, `jit_enabled`, `default_role_id`,
`verified_at`. Forced RLS, plus a read only policy for the provider plane because sign in reads it
before any tenant is known (the `tenant_settings` pattern); no DELETE grant. Settings in Verity under
Settings, Security, SSO (`GET` and `PUT /tenant/security/sso`, `security:manage`).

- **Routing.** `/auth/sso/start` looks the email's domain up among enabled records and asks Keycloak for
  `organization:<alias>`, so the token carries that organization (Keycloak refuses a person who is not a
  member).
- **Which workspace.** A workspace with SSO on accepts an SSO sign in only when the token names its
  organization. When the token names the organization of one of the person's workspaces, that workspace
  gets the session directly; otherwise the workspaces that admit the sign in are offered as a choice,
  and the choice is held server side under the choice token so no other workspace can be picked.
- **Proof.** The first SSO sign in that lands in a workspace through its organization stamps
  `verified_at`. Changing the organization clears it.
- **Enforcement.** Needs `enabled` and `verified_at` (a database CHECK as well as the service). Password
  sign in, workspace choice and switching by password then refuse that workspace, except for members
  holding the built-in Admin role with TOTP enrolled, who always get the TOTP step (break glass).

Deviations from the first draft: `enabled` replaces a status column (draft and testing added nothing a
person could act on), and `connection_id` waits for the evidence change (section 12) to add it.

## 8. Setting up a customer in Keycloak (phase C, built 2026-11-23)

Settings, Security, SSO walks the admin through three steps; Verity drives Keycloak's Admin API with
its service account (`OIDC_ADMIN_CLIENT_ID` and `OIDC_ADMIN_CLIENT_SECRET`, client credentials).

1. **Prove each domain.** The page shows a TXT record, `_verity.<domain>` with
   `verity-domain-verification=<token>`; "Check" reads it over DNS over HTTPS (`OIDC_DNS_RESOLVER_URL`,
   Cloudflare by default; no new dependency). Only proven domains route sign in and reach Keycloak, and a
   domain proven by one workspace cannot be claimed or proven by another. A domain only typed in blocks
   nobody, so a company's domain cannot be squatted. Reserved test domains (`.example`, `.test`,
   `.localhost`, `.invalid`) pass without DNS outside a deployed environment.
2. **Connect the identity provider** (a popup): Microsoft Entra ID (directory id), Okta (domain), Google
   Workspace (limited to the first proven domain), any OpenID Connect provider (discovery URL), or SAML
   (metadata URL), plus client id and secret. Keycloak imports the discovery document or metadata
   itself. Verity creates or updates the identity provider `<organization>-<provider>` (PKCE, signature
   checks, email trusted), the organization, the link with auto membership, and the routing of every
   proven domain to it. The popup shows the redirect URI (and for SAML the entity id) to register at
   the provider. The secret goes to Keycloak and is never stored, logged or audited by Verity.
3. **Prove a sign in**, as in phase B; connecting or changing the provider clears the proof and
   turns enforcement off.

Afterwards Keycloak follows the page: switching SSO off disables the identity provider there, and a
removed domain stops routing.

**Containment.** Identity providers set up by workspace admins live in a realm every customer shares, so
Verity holds each one to its workspace: the `identity_provider` claim (a session note mapper on
`verity-web`) names the provider that signed a person in, and when it belongs to a workspace, that sign
in may only open that workspace and only for an email in its proven domains. Providers the realm's own
administrators set up (or Keycloak accounts) are not limited this way.

**Relinking.** A person whose account is re-created at the provider arrives with a new subject; a sign
in with the same verified email moves the link (one link per person and issuer), audited with the old
subject.

**This Keycloak build** requires Admin API tokens to carry the `kc-admin-api` scope and audience; it is
a default scope of the `verity-admin` client locally. The client's Keycloak needs the same if it is this
recent.

## 9. Lifecycle (phase D, built 2026-11-23)

Migration 5d2f8a1c7b63: `users.sessions_revoked_at`, `role_assignments.source`, `tenant_sso.synced_at`,
table `sso_group_roles` (tenant owned, forced RLS).

- **Accounts on first sign in.** With "Create accounts automatically" on, a person arriving through the
  workspace's organization, with a verified email in a proven domain, becomes an active member with the
  workspace's default role (user created if new, Keycloak subject linked). The default role is required
  and can never be Admin. A membership that exists in any state is left alone: one an admin disabled
  stays disabled until an admin restores it.
- **Group to role map** (`sso_group_roles`): a Keycloak organization group (by name, or by path when it
  starts with a slash) gives a Verity role. Roles the sync gives carry `source = 'sso_group'`; the sync
  takes back only those, never a role an admin gave.
- **Directory sync** (`modules/iam/sso_sync.py`): hourly worker job `sync_sso_directories`, and Sync now
  on the page. Reads the organization's members and each member's organization groups through the Admin
  API, outside any transaction, then applies them in the workspace's transaction. It governs members
  linked to Keycloak whose email is in a proven domain: one who left the organization or is disabled
  there is disabled (reason in the audit row, never deleted); roles follow the map; with automatic
  accounts on, organization members with a verified email and no membership yet are added. The last
  active Admin is never disabled nor stripped of Admin. Fail closed: Keycloak unreachable, or an empty
  organization while governed members exist, changes nothing.
- **Back-channel logout**: Keycloak calls `POST /auth/sso/backchannel-logout` with a logout token
  (signed for `verity-web`, logout event, no nonce, at most 5 minutes old, `jti` used once in Redis,
  `sub` required). Verity moves the person's `sessions_revoked_at` forward, audited; the session check
  refuses any older session. One epoch per person: a sign out at Keycloak ends their Verity sessions on
  every device.
- How people reach Keycloak stays the client's choice: brokered sign in, SCIM pushed into Keycloak, or
  LDAP. With brokered sign in only, Keycloak learns nothing when someone leaves the customer's directory,
  so leavers need SCIM or LDAP into Keycloak (phase E.2) or an admin.

## 10. The client's Keycloak (phase F)

Procedure: `docs/runbooks/keycloak-production.md` (realm, clients, Verity settings, smoke
test, bringing a customer in, mode A or B). In short:

Ask Infowise for: the realm, a confidential client for Verity with our redirect and post logout URIs, the
`organization` scope with organization ids in the claim, the `identity_provider` claim (a user session
note mapper), back-channel logout to our URL, a service account limited to `view-users`, `query-groups`
and organization reads (plus organization and IdP management, `manage-realm` and
`manage-identity-providers`, only if they want Verity to set customers up, with `kc-admin-api` as a default
scope on recent builds), and their policy on organizations per customer.

## 11. Local development

- Keycloak: the owner's build (`keycloak-999.0.0-SNAPSHOT.zip`), unpacked to `C:\Development\
  keycloak-local`, run in dev mode on port 8180 with the H2 file store (Verity never runs Keycloak in
  production, so its local database does not matter), importing `infra/keycloak/realms/*.json`.
- Realm `verity`: client `verity-web`, organization `northwind` (domain `northwind.example`) linked to the
  IdP `northwind-corp`.
- Realm `northwind-corp` plays the customer's IdP (it stands in for Entra ID): its users sign in there and
  arrive in `verity` brokered, exactly as an Entra user would.

## 12. Later: one integration per provider

The owner's brief puts SSO, provisioning, evidence collection and monitoring for one provider behind one
integration the customer connects once. The connectors module already holds per tenant connections with
encrypted credentials and a provider catalogue (Entra, Okta, Google Workspace are listed as planned).
When evidence collection arrives, `tenant_sso` gains a `connection_id`, so an Entra connection can carry
both capabilities without moving the SSO record.
