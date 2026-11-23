---
name: verity-keycloak-sso
description: "Verity SSO through Keycloak: phases A to D built and verified locally 2026-11-23 (uncommitted); local Keycloak setup, design choices, what comes next"
metadata:
  node_type: memory
  type: project
  originSessionId: f8c069aa-a1f0-440a-b6ef-dec216cfaf5a
  modified: 2026-11-23T07:42:48.932Z
---

Owner's goal (2026-11-23): Verity integrates once with Keycloak; locally first, then the client's
(Infowise) in-house Keycloak; Entra ID, Okta and Google Workspace come in through Keycloak; then sync,
lifecycle, groups and roles; evidence collection from the same providers is a later, separate change
(one integration per provider with capabilities).

Built (uncommitted): OpenSpec `openspec/changes/add-keycloak-sso/` (phases A to F, A done), ADR-0015,
runbook `docs/runbooks/keycloak-local.md`, `infra/keycloak/` (realms, run-local.sh, setup_local.py),
`modules/iam/sso.py` + `IamAuthService.sso_sign_in`, routes `/auth/sso/*`, web SSO button and
`/sso/complete`. Verified in the browser: domain routing to a stand-in customer IdP realm, link by
verified email, sign out ends the Keycloak session, unknown person refused.

Local Keycloak: the owner's source build (`C:\Development\Key_cloak`, a Keycloak repo clone built to
`quarkus/dist/target/keycloak-999.0.0-SNAPSHOT.zip`) unpacked to `C:\Development\keycloak-local`, port
8180, mgmt 9180, H2 dev store. That build differs from released Keycloak: no
`/clients/{id}/service-account-user` endpoint (use `serviceAccountUserId` on the client), org domain
routing lives on the domain (`identityProviderAlias`, `autoRedirect`), realm import rejects unknown
fields like `_comment` and does not import organizations.

**Why:** ADR-0006 always planned federation through the client's Keycloak; the owner now wants it.

Phase B (same day): `tenant_sso` (migration 4b8e1d6a9c27; another session chained 3f6a8c2d7e91 after
it), domain to `organization:<alias>`, claim picks the workspace, proof stamp, enforcement with Admin +
TOTP break glass, Settings > Security > SSO page.

Phase C (same day): migration 9c3e5a7b2d14; Verity sets the IdP up in Keycloak from Settings > Security >
SSO after DNS TXT domain proof; workspace IdPs held to their workspace via the `identity_provider` claim;
routing uses proven domains only. That Keycloak build also needs `kc-admin-api` as a default scope on the
service account client, or the Admin API answers 401.

Phase D (same day): migration 5d2f8a1c7b63 (another session chained 6a1f9d3c8e25 after it). Accounts on
first SSO sign in (default role required, never Admin), Keycloak organization groups give roles
(`role_assignments.source='sso_group'`, the sync only takes back its own), `modules/iam/sso_sync.py`
(hourly worker + Sync now; disables leavers, keeps last Admin, fails closed on empty org), back-channel
logout moves `users.sessions_revoked_at`. This Keycloak build has organization groups
(`/organizations/{id}/members/{mid}/groups`). Brokered-only sign in never tells Keycloak about leavers:
that needs SCIM/LDAP into Keycloak (E.2).

Phase E plan (2026-11-23): guide `docs/runbooks/sso-providers.md`, tasks E.0 to E.8. Signed spec 3.2
names SSO for Entra ID and Google Workspace only; Okta is only an evidence connector there. The owner's
Keycloak SCIM server (`/realms/<realm>/scim/v2`) has no organizations: SCIM users and groups land in the
realm, so the sync must also read realm groups (E.3).

**How to apply:** A to D done. Phase E needs the owner's Entra/Okta/Google test tenants; phase F needs Infowise's answers
(design section 10). Bash heredocs with apostrophes break here: write edit scripts with the Write tool.
Related: [[verity-guided-onboarding-plan]], [[feedback-no-long-test-runs]].
