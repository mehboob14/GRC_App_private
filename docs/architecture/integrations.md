# Connector framework

Phase 1 ships the framework with one live connector, GitHub (build plan week 7: "connect GitHub and
watch controls marked pass or fail from real repository data"). Phase 2 adds the rest of the first
fifteen and continuous monitoring (findings, alerts, waivers). Phase 3 delivers the rest of the
catalogue.

## How it works today

- **Checks are content** (`backend/src/verity/seed/content/automation/`): each names the
  capabilities it needs (`version_control`, `identity_provider`), the providers whose collector
  implements it, and the control templates it maps to. One connected provider per capability is
  enough. `seed-content` loads them into `integration_capabilities`, `checks` and
  `control_template_checks`.
- **A connection** holds one provider account and an envelope encrypted, read only token.
  Disconnecting destroys the token; the row and its history stay.
- **A run** collects once (outside any transaction), evaluates every implemented check as a pure
  function of the snapshot, and then writes in one transaction: one `check_results` row per check and
  resource, one evidence file per check holding that check's results and the part of the snapshot
  it read, linked only to the controls that check supports (at most one a day per check unless its
  results change), and the connection's health. Runs are daily from the worker
  (`run_connector_checks`, hourly beat, due after 20 hours) and on demand.
- **The control page** reads `GET /controls/{id}/automation`: tests, the capability and providers
  ("connect any one of"), per resource results, and a 30 day history. A system Verity does not
  support is requested through `integration_requests`.
- Not built yet (Phase 2): findings with auto resolve, alerts, waivers, scoping and exclusions.
  Until then the latest run's failing rows are the open issues.

## Non-negotiables

- **Least-privilege, read-only credentials.** A connector that needs write access needs an ADR.
- **Credentials encrypted at the application layer** before reaching the database, never written to
  logs, never in an exception message, never in a `__repr__`.
- **`error` is not `fail`.** A collection failure is recorded as `error`. A broken integration must
  never be presented as a failed control. This single distinction is what separates a compliance
  product people trust from one they stop reading.
- **Idempotent sync.** Every connector upserts on `(tenant_id, source, external_id)`. Re-running a
  sync must not duplicate rows or reopen closed findings.
- **Health is visible per connection**: last successful sync, error streak, credential expiry.

## Shared behaviour

Every connector implements the same interface and inherits consistent authentication, paging, rate
limiting, retry with exponential backoff **and jitter**, and error classification. A connector that
implements its own retry loop is a bug — retry storms against a rate-limited provider get your
customer's account throttled.

## Evidence and checks

Connectors write evidence rows (`kind = connector_result`) attached to the controls they satisfy,
marked pass or fail **against the named resource** — a specific bucket, repository, or account.
Checks are global content mapped to the stable control template identity, so a check arrives already
mapped to controls in every tenant. A check activates only when its provider is connected and reads
`not_applicable` otherwise.

A check says which capability it needs, which providers can supply it, which of them have a
collector today (`implementations`), and which artifacts it collects. One provider per capability is
enough; a check that needs two (version control and ticketing) says so. A check that reads only
Verity's own modules (provider `verity`, capabilities `verity_*`) is a platform check: listed and
mapped, planned until its runner ships. The control page derives from this, per workspace, whether
each check is running, ready to connect, planned, or needs a system outside the plan, and says
what evidences the control as a whole (spec section 3A). The full map, criterion by criterion and
connector by connector, is generated into `check-catalogue.md` from the same content the product loads.

## Phase 2 — the first fifteen

AWS (core cloud), GitHub, GitLab, Bitbucket, Okta, Google Workspace, Microsoft 365 / Entra ID,
1Password, Jira, Slack, PagerDuty, Datadog, Sentry, Cloudflare, Tailscale.

## Phase 3 — the remainder

Azure, GCP; Grafana, SigNoz, Better Stack; Linear, Asana, ClickUp, Monday, Notion; DigitalOcean,
Heroku, Render, Vercel, Netlify, Supabase, Neon, Qovery; Tenable Nessus, Rapid7 Nexpose, Qualys;
BMC; HubSpot, Intercom, Zendesk, PostHog; SendGrid, Resend; OpenAI, Anthropic; on-premises and
bespoke systems.

## Adding a connector

1. Write the spec first: which controls it satisfies, which checks it ships, what it reads, the
   least-privilege scope required.
2. Implement against the shared interface. No bespoke auth, paging, or retry.
3. Map checks to control templates as content, not code.
4. Integration test against recorded fixtures; never against a live customer account in CI.
5. Document the required scopes in the connector's README — customers must be able to review exactly
   what access they are granting.
