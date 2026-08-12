# Verity — SOC 2 / GRC Compliance Platform

Multi-tenant compliance platform. Takes an organisation from "we need SOC 2" to "we are
audit-ready, continuously." Sold one account per company; several customer companies run
isolated on one deployment.

**Read before writing any code:** [docs/architecture/overview.md](docs/architecture/overview.md),
[docs/architecture/multi-tenancy.md](docs/architecture/multi-tenancy.md),
[docs/conventions/database.md](docs/conventions/database.md), and
[docs/conventions/code-quality.md](docs/conventions/code-quality.md) — the cross-cutting quality bar
(SOLID, reuse, design discipline) that applies to every file.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Tailwind + Vite |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| Database | PostgreSQL 16 (row-level security enabled) |
| Migrations | Alembic |
| Identity | Native auth (Phase 1) behind an IdP-agnostic seam; the customer's external Keycloak-based OIDC/SAML IdP federates in later (Phase 3) — see [ADR-0006](docs/adr/0006-keycloak-as-identity-provider.md) |
| Queue / jobs | Redis + Celery (scheduler + workers) |
| Object storage | S3-compatible — evidence files never live in Postgres |

## The rules that are not negotiable

These are compliance and security properties the product is *selling*. Violating one is a bug
even if the tests pass.

1. **Every tenant-owned row carries `tenant_id`.** No exceptions in the tenant plane. Postgres
   RLS is the second wall; the app filter is the first. Never rely on only one.
2. **The provider plane has no `tenant_id`.** Platform admins, the tenants register, branding,
   provisioning, and all global content (frameworks, requirements, control templates, checks,
   questionnaire banks, document and risk templates) sit above the tenant boundary.
3. **Append-only tables are never updated or deleted from.** `audit_log`, `task_transitions`,
   `vuln_transitions`, `check_results`, `readiness_snapshots`, `kri_measurements`,
   `document_versions`. No `UPDATE`, no `DELETE`, ever.
4. **Compliance objects are disabled with a recorded justification, not deleted.** Controls,
   risks, documents, vendors. Hard delete exists only for drafts and tenant teardown.
5. **Every state-changing action writes to `audit_log`** with actor, timestamp, and before/after
   snapshots.
6. **Secrets are encrypted at the application layer before they reach the database** and are
   never written to logs: connector credentials, MFA secrets, portal tokens.
7. **`error` is a distinct state from `fail`.** A broken connector must never look like a failed
   control. This distinction is load-bearing for the whole product.
8. **AI never publishes and never decides.** It drafts. A human reviews and approves everything.
   AI-authored content is marked with its origin (`ai_draft`) and goes through the same approval
   gate as human content.
9. **A user is a global identity; membership in a tenant is `tenant_memberships`.** `users`,
   `credentials`, and `user_identities` carry no `tenant_id`. Every in-tenant reference to a person —
   asset owner, control owner, approver, assignee, group member — is a FK to `tenant_memberships`,
   never to `users` directly. Phase 1 defaults to one membership per user; global users (a person in
   several tenants) is the same schema with more rows — see
   [ADR-0011](docs/adr/0011-tenant-membership-model.md).

## Architecture shape

- **Backend is a modular monolith.** One deployable, hard module boundaries under
  `backend/src/verity/modules/`. Modules talk through service interfaces, never by importing
  another module's repository or reaching into its tables. Extract to services only when a real
  scaling or ownership reason appears — see [ADR-0008](docs/adr/0008-modular-monolith.md).
- **Vertical slices.** A module owns its router, schemas, models, service, and repository. Do not
  create global `models.py` / `services.py` layers.
- **Frontend features mirror backend modules** one-for-one under `frontend/src/features/`.
- **Configuration lives in tables, not code.** Risk matrix, evidence validity periods, SLA
  definitions, vendor tiering policy, scoring models. If a requirement says "configurable," it is
  a per-tenant row.

## Working agreement for AI tools

- **Specs before code.** This project runs spec-driven (OpenSpec). Do not implement a feature
  that has no spec. If asked to build something unspecified, write the spec first and stop for
  review.
- **Never invent schema.** The data model is defined in
  [docs/architecture/data-model.md](docs/architecture/data-model.md). If a table or column you
  need is not there, say so and stop — do not add it silently.
- **Never weaken a boundary to make a test pass.** No disabling RLS, no `SECURITY DEFINER` to
  dodge a policy, no bypassing the tenant filter in a fixture.
- **New dependencies need a reason.** Say what it replaces and why it is worth the supply-chain
  surface.
- **When a decision is genuinely open, stop and ask.** An unasked question costs a message. A
  wrong assumption baked into the schema costs a migration and a bug in production.
- **Every change updates its docs in the same commit.** A stale doc is worse than no doc, because
  future you and future agents will believe it.

## Layout

```
backend/src/verity/
  core/        config, db session, security, deps, errors, logging
  db/          declarative base, RLS helpers, alembic migrations
  modules/     one folder per bounded context (see list below)
  shared/      cross-module value objects and pure helpers — no business logic
  workers/     Celery tasks and the scheduled jobs
frontend/src/
  app/         routes and layouts
  features/    one folder per backend module
  components/  ui/ holds primitives only; feature components live in features/
  lib/         api client, auth, query config
docs/          architecture, ADRs, conventions, runbooks
infra/         docker compose, deploy scripts; keycloak/ realm config is for the later external-IdP phase, not Phase 1
openspec/      specs and change proposals (created by `openspec init`)
```

**Modules:** tenancy, iam, compliance, evidence, tasks, documents, risk, vendors, assets,
vulnerabilities, connectors, approvals, audit, ai, notifications.

## Delivery phases

Phase 1 is the complete core platform on manual data, no connectors. Phase 2 adds the connector
framework, the first 15 connectors, continuous monitoring, and AI drafting. Phase 3 adds ERM, the
remaining connectors, SSO, and access reviews. Tables for later phases are designed now so
nothing built earlier has to change — see
[docs/product/delivery-plan.md](docs/product/delivery-plan.md).

Do not build Phase 2 or 3 features during Phase 1. Do design the schema so they drop in.
