# Connector framework

Phase 1 models connectors and shows placeholders. Phase 2 builds the framework and the first
fifteen. Phase 3 delivers the rest of the catalogue.

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
