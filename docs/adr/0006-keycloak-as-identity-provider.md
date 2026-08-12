# ADR-0006: Identity — native auth now, external Keycloak-based IdP later

**Status: Accepted**
**Date:** 2026-08-10 (revised: the identity provider is external and deferred)

## Context

The customer is building their own identity and access-management solution (Keycloak-based). It
is **external to this platform and arrives later**; SSO and federated login are a Phase 3 concern,
and the customer has explicitly asked to defer them. Phase 1 still needs working authentication
from day one, so the platform cannot wait on an identity provider that does not yet exist.

The ER design (Section 3.1) specifies a credentials table (password hash, encrypted MFA secret,
recovery codes) kept out of the hot `users` table, plus `USER_IDENTITIES` mapping platform users
to federated identities. An earlier draft of this ADR proposed running Keycloak *inside* the
platform and dropping the credentials table. That is now wrong: with the IdP external and
deferred, Phase 1 must authenticate users itself.

## Decision

1. **The identity provider is external and deferred.** The platform does not run its own Keycloak.
   When the customer's Keycloak-based solution is ready (Phase 3), the platform federates to it.

2. **Phase 1 ships native authentication.** Email/password plus TOTP MFA, with the credentials
   table exactly as the ER design specifies. The platform is its own authenticator until the
   external IdP exists. The credentials table stays; the ER design is **not** amended to remove it.

3. **All authentication goes through one seam.** `core/security` exposes a single
   `current_identity` abstraction (user id, tenant id, roles) that the entire application depends
   on. Auth is a **swappable provider** behind that seam: native auth is the first provider, an
   external OIDC/SAML IdP is the second. No module ever knows which provider is active. This is the
   load-bearing decision — it is what lets any IdP drop in later without a rewrite. That covers
   whichever provider the future holds: the customer's solution, a direct Entra, Okta, or Google
   connection, or an **in-house Keycloak we build ourselves later** — each is just another provider
   behind the seam, added additively (a `USER_IDENTITIES` row + an auth provider registration), not a
   schema change.

4. **Authorization always lives in the platform.** Roles, groups, per-module permissions, and
   object-scoped access (control owner sees assigned controls; auditor sees one engagement within
   its window) stay in the platform database, never in the IdP. The IdP answers *who is this*; the
   platform answers *what may they do*. GRC permissions are too granular and too per-tenant to model
   in an IdP, and splitting authorization across two systems is how privilege bugs happen. This
   holds identically for native auth and for the external IdP.

5. **`USER_IDENTITIES` is built now, used later.** It maps a platform user to a federated subject
   (`sub`). Empty under native auth; populated when the external IdP federates. Designing it now
   makes the federation drop-in additive, not a migration.

6. **When the external IdP arrives (Phase 3):** the platform becomes an OIDC/SAML *relying party*
   trusting the customer's solution; JIT provisioning on first federated login and SCIM for
   lifecycle sync populate users; MFA moves to the IdP for federated tenants; native credentials
   become a fallback, deprecated per tenant as it federates. One shared realm with tenant carried
   as a claim (not realm-per-tenant); the provider plane authenticates separately from tenant users.

7. **Vendors never get identity-provider accounts.** The questionnaire portal stays on signed,
   expiring tokens, under native auth or federation alike.

## What the platform builds itself (Phase 1, now)

Native auth is not "the cheap option" — it is real work, and it is all yours:

- Native authentication: email/password, TOTP MFA, the credentials table, session/token issuance
  and validation.
- Self-service signup that creates the tenant, the first admin, and triggers provisioning.
- Email invite flow with role assignment — the day-one way users arrive, needs no integration.
- Tenant provisioning: seed the control library and templates on tenant creation.
- The full authorization layer: five roles, groups, granular per-module permissions, object-scoped
  and time-boxed access.
- The `current_identity` seam and the `USER_IDENTITIES` table (empty for now).
- The append-only `audit_log`.

## What the external identity layer provides LATER (do NOT build in Phase 1)

These come from the customer's Keycloak-based solution; the platform integrates with them only when
Phase 3 arrives:

- SSO login: OIDC/SAML brokering to Entra ID, Okta, and Google Workspace.
- JIT provisioning (auto-create a user on first federated login).
- SCIM sync (bulk provisioning and offboarding lifecycle).
- IdP-managed MFA for federated tenants.

The platform's only obligations for that phase: be a relying party (accept and verify the IdP's
tokens through the seam) and expose a SCIM endpoint. **Do not build Keycloak, realm config, or IdP
brokering now.**

## Consequences

- The credentials table stays; MFA secrets are stored, encrypted at the app layer, and Rule 6 in
  the contract applies to them.
- **Keycloak is not a Phase 1 runtime dependency.** `infra/keycloak` and any realm config are for
  the later external-IdP phase or local experimentation only; Phase 1 runs and deploys without it.
- The seam in `core/security` is the one place auth strategy lives. Getting it right now is what
  makes federation later a provider swap, not surgery. When federating, the tenant claim is verified
  against the user's actual membership on every request — never trust the claim alone.
- Auditor time-boxing (`engagement_id`, `valid_from`, `valid_until`) stays in the platform
  regardless of provider; an IdP has no concept of an engagement window.

## Superseded reasoning

The earlier proposal (Keycloak owns authentication, drop the credentials table, the platform runs
its own realm) assumed the platform hosts the IdP. It does not — the customer does, later.
Native-first behind a seam gives Phase 1 a working login now and keeps the clean authN/authZ split
for when federation lands.
