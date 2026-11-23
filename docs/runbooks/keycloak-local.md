# Running Keycloak locally for SSO work

Local development only. Verity never runs Keycloak in production: the client hosts it (ADR-0006,
ADR-0015). Spec: `openspec/changes/add-keycloak-sso/`.

## What runs

| Piece | Where | Port |
|---|---|---|
| Keycloak (the owner's source build, `keycloak-999.0.0-SNAPSHOT`) | `C:\Development\keycloak-local` | 8180, management 9180 |
| Realm `verity`: client `verity-web`, service account `verity-admin`, organization `northwind` | imported from `infra/keycloak/realms/` | |
| Realm `northwind-corp`: a stand-in for a customer's Entra ID, Okta or Google Workspace | same | |

Every password and client secret in these files is a throwaway for localhost. The client's Keycloak
issues the real values, and they go in environment variables, never in a file.

## First time

```bash
unzip C:/Development/Key_cloak/quarkus/dist/target/keycloak-999.0.0-SNAPSHOT.zip -d C:/Development/keycloak-local
bash infra/keycloak/run-local.sh          # leave running; imports both realms on first start
python infra/keycloak/setup_local.py      # once it is up: organization, domain routing, roles
```

The admin console is `http://localhost:8180/admin` (user `admin`, password `admin`, both overridable
with `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD`). Java 21 is required.

Realm files are imported only on the first start. After editing one, either run `setup_local.py`
again (it re-applies the `verity-web` URLs) or delete `C:\Development\keycloak-local\
keycloak-999.0.0-SNAPSHOT\data\h2` to start clean.

## Point Verity at it

```bash
export OIDC_ENABLED=true
export OIDC_CLIENT_SECRET=verity-web-local-dev-only
export OIDC_WEB_URL=http://localhost:5175                          # the web app's address
export OIDC_REDIRECT_URL=http://localhost:5175/api/v1/auth/sso/callback
```

The defaults already name `http://localhost:8180/realms/verity` and the client `verity-web`. Redis must
be running: the sign in keeps its one time values there.

## Try it

1. Open the sign in page, type `demo-iso@northwind.example`, press **SSO**.
2. Keycloak sees the `northwind.example` domain, picks the `northwind` organization and sends you to
   `northwind-corp`'s own sign in. Use password `Northwind-local-1`.
3. You land back in Verity, in the Northwind workspace. The first time, the Keycloak subject is linked
   to the Verity user with that verified email (an audit row `user_identity`).
4. Sign out: Verity ends its session and sends the browser to Keycloak's sign out, then back.

`alice@northwind.example` exists only at the identity provider, so Verity refuses her with "There is no
Verity account for this email" until she is invited, or until the workspace turns on automatic accounts
(phase D).

## Tie the workspace to its organization (phase B)

As the workspace's admin, open **Settings, Security, SSO**: Keycloak organization `northwind`, email
domain `northwind.example`, Save, then switch on **Sign in with SSO**. Sign out and sign in with SSO once:
that proves the setup (the page then shows when it worked) and unlocks **Require SSO**. With it on,
members can no longer sign in with a password; Admins with MFA keep password sign in, always with the
TOTP step, so a broken identity provider cannot lock the workspace out.

## Set a customer up from Verity (phase C)

Add `OIDC_ADMIN_CLIENT_SECRET=verity-admin-local-dev-only` to the API's environment. On Settings,
Security, SSO: **Check** each domain (reserved test domains such as `northwind.example` pass locally
without DNS; a real one needs the TXT record shown), then **Connect**. To try it without outside accounts,
pick "Other OpenID Connect provider" with discovery URL
`http://localhost:8180/realms/northwind-corp/.well-known/openid-configuration`, client `keycloak-broker`
and secret `northwind-broker-local-dev-only`: Verity creates `northwind-oidc` in Keycloak and routes the
domain to it. If Keycloak then offers to link an existing account, delete the earlier brokered copy of
that user in realm `verity` (Users) and sign in again.

## Lifecycle (phase D)

On Settings, Security, SSO: **Create accounts automatically** asks for the role new people get; then
`alice@northwind.example` joins on her first SSO sign in. **Add group** maps a Keycloak organization group
to a role. Create the group in the admin console (Organizations, northwind, Groups) and add members
there; **Sync now** (or the hourly worker job) applies it. Removing someone from the organization
disables their membership at the next sync.

Back-channel logout: the realm file sets `verity-web`'s back-channel URL to
`http://localhost:5175/api/v1/auth/sso/backchannel-logout` (the demo web app's proxy). Keycloak calls it
when it ends a sign in, so it must reach the API; change it to the web app's address in use.

## Moving to the client's Keycloak

Only configuration changes. The whole procedure, what Infowise sets up and how each customer is brought
in: `docs/runbooks/keycloak-production.md`.
