# Tasks: sign in through Keycloak

## A. Verity to Keycloak, locally: built and verified 2026-11-23

- [x] A.1 `infra/keycloak/`: realm files (`verity`, `northwind-corp`), `run-local.sh` that unpacks the
      owner's build and starts it on 8180 with the realms imported; `docs/runbooks/keycloak-local.md`.
- [x] A.2 `OIDC_*` settings, off by default; discovery and JWKS cache.
- [x] A.3 `GET /auth/sso/start`, `GET /auth/sso/callback`, `POST /auth/sso/complete`; state and handoff
      in Redis, single use; ID token validation; identity resolution (link by subject, then verified
      email); session through `_grant_session(method="sso")`, TOTP skipped, issuer and `acr` audited.
- [x] A.4 Sign out through Keycloak: ID token kept per session, end session URL returned on logout.
- [x] A.5 Web: "Sign in with SSO" (email first), `/sso/complete`, error messages, sign out redirect.
- [x] A.6 Tests: unit (token validation, state single use, resolution rules) with a fake issuer;
      integration of the routes with the IdP mocked; isolation unaffected.
- [x] A.7 End to end on the local Keycloak: a Keycloak user signs in to Verity, signs out.

## B. Tenant routing and the customer IdP, locally: built and verified 2026-11-23

- [x] B.1 Migration `tenant_sso` (4b8e1d6a9c27) with forced RLS plus a provider plane SELECT policy;
      `GET` and `PUT /tenant/security/sso` (`security:manage`); alias and domains unique across
      workspaces; audited. Settings, Security, SSO page.
- [x] B.2 Start: the email's domain finds an enabled record and the request asks for
      `organization:<alias>`.
- [x] B.3 The `organization` claim picks the workspace; a workspace with SSO on admits an SSO sign in
      only through its organization; an SSO workspace choice is limited server side to what the sign in
      allowed. The first sign in through the organization stamps `verified_at`.
- [x] B.4 Enforcement needs a proven sign in (CHECK and service); password sign in, password workspace
      choice and switching refuse an enforcing workspace except Admins with TOTP enrolled, who always
      get the TOTP step.
- [x] B.5 End to end on the demo stack: Northwind's SSO set in the page, signed in through Keycloak and
      the stand-in customer IdP, proof stamped, Require SSO switched on.

## C. Setting customers up from Verity: built and verified 2026-11-23

- [x] C.1 `modules/iam/keycloak_admin.py`: client credentials token (reused), organizations, domain routing,
      identity provider create or update and enable, import from discovery or metadata; refusals become
      `UpstreamUnavailable` with Keycloak's words in the log only.
- [x] C.2 `modules/iam/idp_templates.py`: Entra ID, Okta, Google Workspace (hosted domain), OIDC, SAML;
      `modules/iam/sso_setup.py`: DNS TXT domain proof, connect, keep Keycloak in step with the switches.
      Migration 9c3e5a7b2d14 (`provider`, `idp_alias`, `verified_domains`, `domain_token`).
- [x] C.3 Settings page: domains with their record and Check, Connect popup per provider with the URI to
      register, the switches. Containment of workspace providers through the `identity_provider` claim,
      and relinking a re-created account, came with it.

## D. Lifecycle: built and verified 2026-11-23

- [x] D.1 Just in time provisioning with the tenant's default role (required, never Admin).
- [x] D.2 Directory sync job from the organization's members and groups; disable, never delete; last
      Admin kept; fail closed. Hourly worker job and Sync now.
- [x] D.3 `sso_group_roles` and the mapping on the SSO page (Add group popup).
- [x] D.4 Session epoch per user (`users.sessions_revoked_at`) and back-channel logout.

## E. Real providers (guide: `docs/runbooks/sso-providers.md`)

Contract scope (spec deliverable 3.2): Entra ID and Google Workspace sign in. Okta and SAML are extra.

- [ ] E.0 From the owner: an Entra ID test tenant, a Google Workspace trial on a domain he controls, an
      Okta developer org; a Keycloak on a public HTTPS address for SCIM (staging or a tunnel).
- [ ] E.1 Entra ID sign in on the test tenant: app registration, Connect, the ten checks (guide section 4).
- [ ] E.2 Google Workspace sign in: Internal consent screen, Connect, the ten checks; hosted domain holds.
- [ ] E.3 Entra SCIM provisioning into Keycloak's SCIM server. This build's SCIM has no organizations, so
      the sync also reads members' realm groups and finds realm users by proven domain; leavers and
      group moves reach Verity. Confirm Infowise's build first.
- [ ] E.4 Okta sign in, then Okta SCIM (provisioning app type confirmed on the tenant).
- [ ] E.5 Client secret expiry: an optional expiry date at Connect, reminder to the workspace's Admins
      30 days before (Entra secrets lapse at 24 months at most).
- [ ] E.6 Google Workspace lifecycle: decide between the Phase 2 Directory API connector and Keycloak
      LDAP (Secure LDAP editions only).
- [ ] E.7 SAML on a real IdP, only when a customer asks.
- [ ] E.8 User guide chapter per provider, with screenshots, for customer admins.

## F. The client's Keycloak and hardening

- [ ] F.1 Questions to Infowise (design section 10); configuration for their realm.
- [ ] F.2 Minimum `acr` per tenant, rate limits on the SSO routes, monitoring, lockout recovery runbook.

## Verified 2026-11-23

- Local Keycloak from the owner's build, both realms imported, `setup_local.py` idempotent (organization
  `northwind`, domain routed to `northwind-corp`, `verity-admin` roles, client URLs re-applied).
- Browser, end to end: Verity sign in with `demo-iso@northwind.example`, Keycloak routed the domain
  straight to the customer IdP, sign in there, back into the Northwind workspace; the user was added to
  the organization and linked to the IdP in Keycloak, and linked by verified email in Verity. Sign out
  ended the Keycloak session too (Keycloak reports no sessions). `alice@northwind.example`, known only to
  the IdP, is refused with "There is no Verity account for this email. Ask your admin to invite you."
- Tests: `tests/unit/test_sso.py` (11: token checks, PKCE, single use state and handoff, sign out URL),
  `tests/integration/test_sso_sign_in.py` (6: link once then by subject, audited refusals, workspace
  choice without TOTP, routes off until configured), iam and security unit tests (59), ruff, mypy,
  import contracts (21 kept), tsc, eslint.
- Deviation: the seam guard test now allows `user_identities` in the repository only (ADR-0015).

Phase B, 2026-11-23: `tests/integration/test_tenant_sso.py` (settings validation and uniqueness,
organization picks the workspace and stamps the proof, the choice cannot reach a disallowed workspace,
enforcement with break glass), `tests/isolation/test_sso_isolation.py` (owner only, provider plane reads
but cannot write, WITH CHECK), phase A tests rerun, the existing sign in suite `test_iam_auth.py` (20); ruff, mypy, import contracts (22 kept), tsc,
eslint, migration up, down and up, no drift on `tenant_sso`.

Phase C, 2026-11-23: `tests/unit/test_sso_setup.py` (4: templates, Admin API client against a fake
Keycloak, refusals typed), `tests/integration/test_sso_setup_flow.py` (2: prove, connect, follow the
switches, no secret in audit; a workspace provider held to its workspace and domains), relink test in
`test_sso_sign_in.py`. Browser on the demo stack: proved `northwind.example`, connected the stand-in IdP
as an OpenID Connect provider from the page, Keycloak then held `northwind-oidc` (imported issuer, PKCE)
linked and routed, and the next sign in went through it (`identity_provider: northwind-oidc` on the
session audit row) and recorded the proof.

Phase D, 2026-11-23: `tests/unit/test_sso.py` (logout token: good once, replay, no event, other event,
nonce, stale, audience, no subject), `tests/integration/test_sso_lifecycle.py` (3: account on first sign in
and its refusals, sync with group roles, empty organization and last Admin, back-channel logout ends the
session). Browser and worker on the demo stack with the local Keycloak: turned on automatic accounts (role
popup leaves Admin out) and mapped `engineering`; signing out made Keycloak call the back-channel URL (200,
epoch moved, audited); Alice, unknown to Verity, signed in and became an Engineering Lead; in the
`engineering` organization group the worker job gave her Security Officer; removed from the organization,
the next run disabled her ("left the organization in Keycloak") and her open session went to sign in.

