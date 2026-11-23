# ADR-0015: Keycloak organizations route SSO; Verity keeps its own session

**Status: Proposed**
**Date:** 2026-11-23

## Context

ADR-0006 deferred federation to an external, client run Keycloak and fixed the principles: one seam, one
shared realm with the tenant carried as a claim, authorization in Verity. The owner now wants it built,
tested locally first, then pointed at the client's Keycloak. The current Keycloak (the owner's source build
of November 2026) has organizations and a SCIM server enabled by default.

## Decision

1. **A Keycloak organization stands for a Verity tenant.** Its domains route sign in (identity-first
   login), its linked identity providers are the customer's Entra ID, Okta, Google or SAML, and the token's
   `organization` claim names it. Verity maps the organization to the tenant in a `tenant_sso` record and
   still requires a Verity membership: the claim never grants access.
2. **Verity issues its own session after the OIDC callback.** Keycloak tokens stay on the server; the ID
   token is kept only to end the Keycloak session at sign out. The rest of the platform keeps using the
   seam unchanged.
3. **MFA for SSO sign ins belongs to the identity provider.** Verity's TOTP step is skipped for them; a
   minimum `acr` per tenant can be required later.
4. **Lifecycle comes from Keycloak, whatever feeds Keycloak.** Verity reads organization members and
   groups through the Admin API, maps groups to its own roles, disables memberships that disappear, and
   honours back-channel logout. Whether customers push SCIM into Keycloak, federate LDAP or only sign in is
   the client's choice.
5. **A password sign in stays available.** A tenant may enforce SSO; members holding the built-in Admin
   role with TOTP enrolled keep password sign in as break glass.
6. **Workspace admins may set their own identity provider up, held to their workspace** (added with
   phase C). Domains route sign in only once a DNS TXT record proves ownership, and an identity provider
   a workspace set up may only sign people into that workspace, for its proven domains. Verity learns
   which provider signed a person in from the `identity_provider` claim.

## Consequences

- `user_identities` is used from now on (the unit test that kept it unused changes with this ADR).
- Moving from the local Keycloak to the client's is configuration, plus the access listed in the design.
- A second realm in `infra/keycloak` plays a customer IdP, so brokering is tested without outside accounts.
