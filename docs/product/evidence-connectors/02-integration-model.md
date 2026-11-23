# 2. The integration model: connecting once, credentials, screens and setup guides

How a customer connects a system, what Verity asks for, what the screens look like, and how one
connection can serve several purposes (sign in, evidence, people lifecycle). Per provider details are
in [connectors/](connectors/); identity providers in particular in
[connectors/identity-providers-unified-setup.md](connectors/identity-providers-unified-setup.md).

## 2.1 One integration per provider, several capabilities

The owner's direction: a customer connects a provider once, and that one connection serves every
capability the provider has. Microsoft is the clearest case:

| Purpose | What it needs from Microsoft | Verity capability |
|---|---|---|
| Sign in to Verity through Keycloak | OIDC sign in (`openid`, `profile`, `email`) | single sign on (phases A to D, built) |
| Identity evidence | Graph read of users, MFA registration, Conditional Access, roles, sign in logs | `identity_provider` |
| Device evidence | Graph read of Intune managed devices and compliance | `device_management` |
| People lifecycle | Provisioning into Keycloak (SCIM) or Graph read of users | directory sync (phase D, built) |

In the product this is **one integration card per provider** with a switch per capability, and **one
guided setup** behind it. Underneath there are **always two credentials** for identity providers: the
sign in app, held by Keycloak, and the evidence credential, held by Verity's core. One shared app is
rejected for every provider: for Entra ID it would put a directory read credential in Keycloak, which
Infowise runs; Okta does not offer it; for Google it gains nothing
([identity-providers-unified-setup.md](connectors/identity-providers-unified-setup.md) section 6).
Recommended sequence: launch with customer owned evidence apps created in the same wizard, where Verity
generates the key pair so no evidence secret is ever typed (Entra certificate, Okta private key JWT,
Google domain wide delegation to Verity's service account); after the first Entra pilot, add Verity's
own multi tenant Entra evidence app with one click admin consent, signed by a key that cannot be
exported. Lifecycle provisioning (SCIM into Keycloak) stays a separate, optional step.

Data model consequence (design section 12 of `openspec/changes/add-keycloak-sso/design.md`):
`tenant_sso` gains a `connection_id`, so the sign in setup and the evidence connection of the same
provider are one integration in the interface and can be switched on and off independently.

## 2.2 Credential types

Every provider uses one of six patterns. The connect screen is generated from the pattern and the
provider's content, so a new provider needs content, not a new dialog.

| Pattern | How it works | Providers (examples) | What the customer does |
|---|---|---|---|
| **Vendor app, admin consent** | Verity publishes one app (multi tenant or marketplace); the customer's admin approves the listed permissions; Verity stores the customer's tenant or install id and gets tokens with its own vendor credential | Entra ID and Intune (multi tenant app), Google Workspace (marketplace or verified OAuth app), Slack app, Atlassian (Jira) OAuth 2.0 app, GitHub App | Click Connect, sign in as an admin, approve |
| **Customer app registration** | The customer creates an app in their own tenant with listed permissions and gives Verity its id and a secret or key | Entra ID single tenant, Okta API service app (private key JWT), Google service account with domain wide delegation | Follow the in product guide, paste ids and secret |
| **API token or key** | A read only token the customer creates | PagerDuty, Datadog (API key and application key), Sentry, Cloudflare, Tailscale, 1Password, Kandji, Jamf API client, CrowdStrike API client, SentinelOne, HR systems | Create the token with the listed scopes, paste it |
| **Cloud role** | Verity's own cloud identity assumes a role the customer creates, bound to an external id unique to the workspace | AWS (IAM role and external id, CloudFormation one click), GCP (service account impersonation or workload identity federation), Azure (service principal with Reader) | Run the template or create the role, paste the role id |
| **Personal or project token** | A token tied to a person or a project | GitHub fine grained token (built), GitLab group access token, Bitbucket access token | Create, paste; Verity shows when it expires |
| **Agent** | A small program on each device reports device facts | a possible Verity endpoint agent ([mdm-and-endpoint-strategy.md](mdm-and-endpoint-strategy.md)) | Distribute through MDM or install by hand |

Rules for all of them:

- **Read only, least privilege.** The permission list shown before connecting is the full list
  requested; nothing is added silently later. A new permission after an upgrade is a reconnect the
  customer approves.
- **Secrets stay in the core.** Envelope encrypted at rest (existing), never shown back (only a hint
  and an expiry date), never logged, never in an audit row.
- **Expiry and rotation.** `credential_expires_at` (exists) drives reminders to the workspace's Admins 30
  days and 7 days before, and a connection health warning. For customer app registrations the customer
  types the secret's expiry date when the provider does not expose it.
- **Permission drift.** Each run probes the permissions it needs. A removed permission turns only the
  checks that need it into `error`, and the connection shows "missing permission: X" with the fix.

## 2.3 The connect flow, screen by screen

1. **Catalogue.** Integrations grouped by category, each card showing the capabilities it serves and
   its state (available, planned with its phase, not in the plan). Today the list is hard coded in
   `frontend/src/features/connectors/connector-catalogue.ts`; it moves to content (2.5) so it cannot
   drift from what the backend supports.
2. **Before you connect.** One screen per provider, from content: what Verity reads, the exact
   permissions and why each is needed (mapped to the checks it enables), what Verity never does (write,
   read message content, read secrets), plan or licence requirements (for example Entra ID P1 for sign
   in logs), and which controls and frameworks it helps.
3. **Connect.** The form for the provider's pattern:
   - vendor app: one button, then the provider's consent page, then back;
   - customer app or token: the fields the provider needs (ids, secret, region or domain), each with a
     one line hint and a link into the setup guide side panel;
   - cloud role: the external id to copy, the one click template link, then the role id field.
4. **Test.** Verity calls the provider once and shows, per check, whether it can run: ready, missing
   permission, not available on your plan. The customer can save with missing permissions; those checks
   stay in `error` until fixed.
5. **Scope.** The discovered resources (repositories, accounts, subscriptions, device groups, user
   groups) with system defaults and reasons, as the GitHub scope dialog does today
   (`scope-dialog.tsx`). Scope changes are audited.
6. **Health.** On the integration page: last run, next run, per capability status, completeness per
   resource type, errors in plain words with the fix, credential expiry, and a Run now button.
7. **Disconnect.** Keeps history (results and evidence already filed stay, marked as from a
   disconnected source); stops runs; asks for a reason (audited).

## 2.4 In product setup guides

| Pattern | Guide needed? | Why |
|---|---|---|
| Vendor app, admin consent | Short (what the admin will see, who can approve) | The provider's own consent page does the work |
| Customer app registration | Yes, full and illustrated | Several screens in the provider's console; easy to grant too much or too little |
| API token or key | Yes, short | Where to create it, which scopes to tick, expiry choice |
| Cloud role | Yes, with the template | The template does most; manual path for teams without CloudFormation or Terraform |
| Personal or project token | Yes, short | Fine grained choices |
| Agent | Yes | Distribution through each MDM, and by hand |

Guides are **content**, not code: one file per provider (proposed `seed/content/integrations/
guides/<provider>.md`), shown in a side panel of the connect dialog, versioned and reviewed like other
content, written in Verity's own words with screenshots taken by Verity. Each connector document's
section 3 is the draft of its guide. A guide names the date it was last checked against the provider's
console, because consoles change.

## 2.5 Provider content (proposed schema)

The catalogue, permissions, form fields and guides move into content next to the capabilities:

```json
{
  "key": "entra",
  "name": "Microsoft Entra ID",
  "category": "Identity",
  "status": "planned",
  "phase": "Phase 2",
  "capabilities": ["identity_provider", "device_management", "single_sign_on"],
  "auth": {
    "pattern": "vendor_app_consent",
    "alternatives": ["customer_app_registration"],
    "fields": [
      {"key": "tenant_id", "label": "Directory (tenant) ID", "kind": "text", "pattern": "..."},
      {"key": "client_secret", "label": "Client secret", "kind": "secret"}
    ],
    "permissions": [
      {"name": "User.Read.All", "type": "application", "purpose": "List users and their state", "checks": ["idp.access_list_exported"]}
    ],
    "requirements": [{"text": "Sign in logs need Entra ID P1 or P2", "checks": ["idp.stale_accounts"]}]
  },
  "guide": "guides/entra.md",
  "collector": {"language": "go", "observation_types": ["identity.user", "identity.policy", "device"]},
  "docs": ["https://learn.microsoft.com/..."]
}
```

`capabilities.json` keeps its list of provider keys per capability; this file holds everything about a
provider. The connect dialog, the before you connect screen and the catalogue are generated from it.

## 2.6 Security notes specific to integrations

- A vendor app means Verity holds one credential that can read every consenting customer's directory.
  It lives in a secret store with restricted access, is rotated, and its use is logged per tenant. The
  identity providers document weighs this against customer registered apps.
- Keycloak (run by the client, Infowise, in production) should not hold a credential that can read a
  customer's directory: sign in and evidence use different credentials even when the customer sees one
  setup.
- Tokens are requested per run with the narrowest scope the provider allows.
- Evidence that contains personal data (user lists, device owners) follows the workspace's retention
  setting and is never sent to an AI model as instructions (rule 11): evidence is untrusted input.
