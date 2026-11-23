# Connecting Verity to the client's Keycloak (production)

How Verity is pointed at Infowise's Keycloak, and how every customer is then brought into Verity
through it. Verity never hosts Keycloak in production (ADR-0006, ADR-0015). Spec:
`openspec/changes/add-keycloak-sso/` (design sections 1 to 10). Local rehearsal of all of this:
`docs/runbooks/keycloak-local.md`. Connecting each customer's Entra ID, Google or Okta:
`docs/runbooks/sso-providers.md`.

## 1. The shape

```
Customer A's Entra ID ─┐
Customer B's Google  ──┼─> Infowise Keycloak, one realm for Verity ──OIDC──> Verity
Customer C's Okta    ──┘   (one organization per Verity workspace)          (one workspace per customer)
```

- **One realm** serves every Verity customer. Each customer is a Keycloak **organization**; its email
  domains route sign in to its own identity provider.
- Verity trusts the realm through **one client** (`verity-web`, sign in) and reads or sets it up through
  **one service account** (`verity-admin`, Admin API).
- Keycloak answers *who is this*. Verity decides *what they may do*: workspace membership, roles and
  audit stay in Verity, and an organization claim never grants access by itself.

## 2. Who does what

| Step | Infowise (Keycloak admins) | Verity operator (us) | Customer's workspace admin |
|---|---|---|---|
| Realm and the two clients (section 3) | Once | Sends this page | |
| Verity settings and restart (section 4) | | Once per environment | |
| Smoke test (section 5) | Test organization and user | Runs it | |
| Each new customer (section 6) | Only in mode B | | Settings, Security, SSO |

**Mode A, Verity sets customers up (recommended).** The workspace admin connects their provider from
Verity's SSO page; Verity creates the organization, identity provider and domain routing in Keycloak
through `verity-admin`. Needs the management roles in section 3.2.
**Mode B, Infowise sets customers up.** Infowise creates each organization and identity provider by hand;
the workspace admin only types the organization alias and proves the domains. `verity-admin` keeps read
roles only. Infowise chooses; both work with the same Verity build.

## 3. What Infowise sets up once

### 3.1 Realm

- A realm for Verity (named, for example, `verity`), **Organizations enabled**.
- Signing keys RS256 (the default).
- Optional, for lifecycle feeds from customers' directories: the SCIM server. On the owner's build it
  does not place users in organizations (see `sso-providers.md`, section 6); ask how theirs behaves.

### 3.2 Clients

**`verity-web`** (sign in):

| Setting | Value |
|---|---|
| Client authentication | On (confidential) |
| Flows | Standard flow only. Direct access grants, implicit and service accounts off |
| PKCE | S256 (`pkce.code.challenge.method`) |
| Valid redirect URI | `https://<verity>/api/v1/auth/sso/callback` |
| Valid post logout redirect URI | `https://<verity>/sign-in` |
| Front-channel logout | Off |
| Back-channel logout URL | `https://<verity>/api/v1/auth/sso/backchannel-logout`, session required on |
| Client scopes | Default: `basic`, `profile`, `email`, `acr`. Optional: `organization` |
| Mapper | User session note `identity_provider` into the ID token as claim `identity_provider` |

`<verity>` is the public address of the web app (the API is served under `/api/v1` on the same host).

**`verity-admin`** (service account for the Admin API):

| Setting | Value |
|---|---|
| Client authentication | On; service accounts on; every browser flow off |
| Default client scope | `kc-admin-api` (recent builds refuse Admin API tokens without it) |
| Roles, mode B | realm-management `view-users`, `query-users`, `query-groups`, `view-realm` |
| Roles, mode A | the above plus `manage-realm`, `manage-users`, `manage-identity-providers` |

Infowise sends us the two client secrets over a secret channel, never in chat or email.

The file `infra/keycloak/realms/verity-realm.json` is the same configuration as an importable realm
(local URLs and throwaway secrets: they change URLs, then regenerate both secrets after import).

## 4. What we set on Verity's side

In `infra/docker/.env.production` on the host (git-ignored, read by the api, worker and beat
containers):

```bash
OIDC_ENABLED=true
OIDC_ISSUER_URL=https://<keycloak>/realms/<realm>
OIDC_CLIENT_ID=verity-web
OIDC_CLIENT_SECRET=<from Infowise>
OIDC_REDIRECT_URL=https://<verity>/api/v1/auth/sso/callback
OIDC_WEB_URL=https://<verity>
OIDC_ADMIN_CLIENT_ID=verity-admin
OIDC_ADMIN_CLIENT_SECRET=<from Infowise>
```

Then recreate the three containers so they read it (the owner runs this on the server; we hand over the
command, never run it ourselves):

```bash
dc up -d --force-recreate api worker beat
```

Network paths that must be open:

| From | To | Why |
|---|---|---|
| Users' browsers | Keycloak | sign in pages |
| Verity API and worker | Keycloak, HTTPS | discovery, token exchange, signing keys, Admin API, hourly sync |
| Keycloak | Verity, HTTPS | back-channel logout |
| Verity API | `cloudflare-dns.com` (or `OIDC_DNS_RESOLVER_URL`) | DNS TXT proof of a customer's domain |

Redis must be up: sign in keeps its one time values there.

## 5. Smoke test before the first customer

1. `https://<verity>/api/v1/auth/sso/status` answers `{"enabled": true}`.
2. Infowise creates a test organization (`verity-smoke`) with a domain they control, and a Keycloak user
   in it (or links a test identity provider).
3. In a test Verity workspace: Settings, Security, SSO: alias `verity-smoke`, the domain, prove it, turn
   on **Sign in with SSO**.
4. Sign out, type the test user's email on the sign in page, press **SSO**: Keycloak, then back into the
   test workspace. The page now shows when SSO worked.
5. Sign out: Keycloak's session ends too, and the API log shows the back-channel call answered 200.
6. Mode A only: **Connect** an "Other OpenID Connect provider" (any test IdP) and check it appears in
   Keycloak as `verity-smoke-oidc`, linked and routed.
7. **Sync now** on the SSO page: no error, "Last synced" filled in.

## 6. Bringing a customer in

1. **Workspace.** The customer signs up (or we create the workspace); their first admin signs in with a
   password and TOTP. That admin stays the break glass account.
2. **Organization and domains.** Settings, Security, SSO: the organization alias (the workspace's slug
   is suggested) and the company's email domains. Publish the TXT record shown, press **Check**. Only
   proven domains route sign in, and no other workspace can claim them.
3. **Identity provider.** Mode A: **Connect**, following `sso-providers.md` for their provider (they
   register an app at Entra, Google or Okta with the redirect URI the popup shows). Mode B: Infowise
   creates the organization, identity provider and domain routing in Keycloak.
4. **Prove it.** The admin signs out and signs in with **SSO** once.
5. **Choose the policy.** **Require SSO** (password sign in off; Admins with TOTP keep it for
   emergencies), **Create accounts automatically** with the role new people get (never Admin), and
   **Add group** for Keycloak groups that give roles.
6. **Lifecycle.** For leavers to be disabled without an admin, the customer's directory feeds Keycloak
   (SCIM from Entra or Okta, or LDAP); Verity's hourly sync then disables leavers and moves roles.
   Without a feed, an admin disables leavers in Verity.

What the customer's people then see: type their work email, press **SSO**, sign in at their own
company's page, land in Verity. MFA is their provider's.

## 7. Moving between Keycloaks

Each person is linked to their Keycloak user id. When Verity is pointed at a different Keycloak (local to
staging to production), the first sign in through the new one re-links the person by verified email,
audited with the old id; nothing else moves. Organization aliases and domains stay in Verity; Keycloak
needs its organizations and identity providers again (mode A: press **Connect** again).

## 8. Security notes

- Secrets live only in `.env.production` on the host and in Keycloak. Customers' provider secrets go to
  Keycloak and are never stored, logged or audited by Verity.
- Never enable direct access grants on `verity-web`; Verity never sees a password that belongs to SSO.
- Rotate `verity-web` and `verity-admin` secrets on Infowise's schedule: update `.env.production`, then
  recreate the three containers.
- If Keycloak is down: password sign in still works for workspaces that do not require SSO, and for their
  Admins with TOTP where SSO is required. The hourly sync changes nothing while Keycloak cannot be read.

## 9. Still to agree with Infowise

1. Mode A or mode B (section 2).
2. Realm name, Keycloak version, and whether that realm serves their other products too.
3. Whether their SCIM server places users in organizations.
4. Secret rotation schedule and how secrets reach us.
5. Their policy on minimum sign in strength (`acr`) per customer, and the monitoring they give us
   (phase F).
