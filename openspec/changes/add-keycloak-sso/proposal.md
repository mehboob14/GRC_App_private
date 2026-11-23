# Sign in through Keycloak (SSO), then lifecycle sync

Status: proposed 2026-11-23. The owner asked to build and test the Keycloak integration locally first,
then connect to the client's in-house Keycloak, then bring Entra ID, Okta and Google Workspace in through
it, then synchronisation, user lifecycle and groups. Evidence collection from the same providers comes
after, as a separate change (see design section 12).

## Why

ADR-0006 shipped native sign in for Phase 1 and kept one seam for an external identity provider. The client
(Infowise) is building its own Keycloak and wants every product, Verity included, to trust it. Their
customers' Entra ID, Okta and Google Workspace connect to that Keycloak, not to each Verity tenant
separately. Verity integrates once, with Keycloak, and never needs to know which provider sits behind it.

## What changes

- Verity becomes an OpenID Connect client of a Keycloak realm (authorization code with PKCE, confidential
  client, server side token handling). Native sign in stays and is unchanged unless a tenant enforces SSO.
- A Keycloak organization stands for a Verity tenant. Its email domains route a sign in to the right
  identity provider (Keycloak's identity-first login); the token's `organization` claim names it.
- After the callback Verity issues its own session exactly as today. Keycloak tokens never reach the
  browser. MFA for SSO sign ins happens at the identity provider.
- A per tenant SSO record maps the tenant to its Keycloak organization, with enforcement, just in time
  provisioning and a default role.
- Later phases: Verity sets up organizations and identity providers in Keycloak through its Admin API,
  pulls members and groups from Keycloak to create, update and disable memberships, maps groups to Verity
  roles, and honours Keycloak's back-channel logout.
- Local development runs the owner's own Keycloak build (`C:\Development\Key_cloak`, a source build from
  November 2026) with realm files in `infra/keycloak/`, including a second realm that plays a customer's
  identity provider, so the whole chain is tested without outside accounts.

## Phases

| Phase | What | Needs |
|---|---|---|
| A | Local Keycloak, realm as code, Verity sign in through Keycloak, sign out | nothing outside |
| B | Tenant mapping by organization, a fake customer IdP realm brokered in, SSO enforcement | nothing outside |
| C | SSO settings in Verity, organizations and IdPs set up through the Admin API, test login | nothing outside |
| D | Just in time provisioning, directory sync from Keycloak, group to role mapping, back-channel logout | nothing outside |
| E | Real Entra ID, Okta and Google Workspace through Keycloak | the owner's test tenants |
| F | The client's Keycloak (Infowise), production hardening | Infowise details (design section 10) |

## Out of scope

- Running Keycloak as part of Verity's production deployment (ADR-0006: the client hosts it).
- SAML or OIDC between Verity and a customer directly: every protocol difference stays inside Keycloak.
- Evidence collection and monitoring through the same providers (next change, design section 12).
- Moving Verity's own session from a bearer token to cookies (a platform wide change of its own).

## Impact

- Backend: `modules/iam` (new `sso` service and routes, the `user_identities` seam starts being used),
  settings `OIDC_*`, Redis for one time state, new tables in later phases (`tenant_sso`, group role maps,
  a per user session epoch for back-channel logout).
- Frontend: "Sign in with SSO" on the sign in page, a completion route, sign out through Keycloak, later an
  SSO settings page.
- Infra and docs: `infra/keycloak/` realm files and a start script, `docs/runbooks/keycloak-local.md`,
  ADR-0015.
- Signed plan: SSO, JIT and SCIM are Phase 3 items of the signed delivery plan; the owner asked for them
  now.
