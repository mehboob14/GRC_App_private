# How Verity is built

Written 2026-10-11. This is the map, not the law: the repo's `docs/architecture/*`, `docs/conventions/*` and
the ADRs are the source, and the code beats both. Where this file adds something the repo does not say, it
says so. Rules live in START-HERE.md.

## Runtime shape

```
Browser -> React SPA -> FastAPI (modular monolith, /api/v1) -> PostgreSQL 16 (row level security)
                              |                                 Redis (rate limits, Celery broker)
                              |                                 object storage (evidence files)
                              +-> Celery worker and beat (same codebase, schedules in workers/celery_app.py)
```

- One deployable backend, one database, one shared schema. Customer companies are tenants inside it.
- Production is a single host running `infra/docker/docker-compose.prod.yml`: postgres, redis, minio,
  minio-init, api, web (nginx serving the built SPA), worker, beat. The host's edge nginx and TLS belong to
  someone else's stack on a shared box. The evidence volume is `evidence-data` (local disk driver); MinIO is
  not where evidence lives today.
- Configuration comes from `<repo>/.env` and `backend/.env` (the latter wins). Both are git ignored and hold
  real secrets (SMTP, keys). `.env.example` lists the keys.
- API docs exist at `/api/v1/docs` in local and test only. Probes: `/healthz` (touches nothing), `/readyz`
  (database and Redis).

## Two planes

- **Provider plane**, above the tenant boundary: `platform_admins`, `tenants`, `tenant_branding`,
  `tenant_provisioning`, `demo_requests`, and all shipped content (frameworks, requirements, control templates,
  checks, questionnaire banks, document and risk templates). Platform admins are a separate population with their
  own sign in (TOTP) and a provider console in the SPA (`features/provider`).
- **Tenant plane**: everything a customer owns. Every row has `tenant_id`.
- Identity is global: `users`, `credentials`, `user_identities` have no `tenant_id`. A person belongs to a
  tenant through `tenant_memberships`, and every in-tenant reference to a person points at a membership.

## Tenancy mechanics (read `core/db.py`, `core/rls.py`, `core/deps.py`, `db/rls.py`)

- A transaction binds the tenant with a transaction local setting, `app.tenant_id` (and `app.provider_plane`
  for provider work). Policies read `NULLIF(current_setting('app.tenant_id', true), '')::uuid`, so an unbound
  session sees no rows (fails closed). Older notes say `app.current_tenant`: the code says `app.tenant_id`.
- Three entry points: `get_tenant_session` (request dependency, tenant taken from the authenticated membership),
  `session_scope(tenant_id)` (workers, scripts, tests), `provider_session_scope()` (platform admin work, identity
  resolution, the leads public route). The last one checks nobody, which is why nothing else may use it.
- Roles: `verity_owner` runs migrations and seeds; `verity_app` serves requests and has no BYPASSRLS. Tenant tables
  are `ENABLE` and `FORCE ROW LEVEL SECURITY`. FORCE applies to the owner too, so a data migration that reads or
  writes tenant rows must lift FORCE around both its reads and writes.
- Services never commit. The scope commits on a clean exit.

## Auth and permissions

- Native auth now: password plus TOTP, verify first signup with an emailed link, invitations, recovery codes.
  Bearer tokens live in `sessionStorage` (`verity.session.token`, `verity.session.principal`; see
  `frontend/src/lib/auth/session.ts`). The Keycloak based external provider is deferred (ADR-0006) behind a seam.
- Permissions are `module:action` strings (`controls:manage`, `frameworks:read`, `evidence:manage`,
  `documents:approve`, `members:read`, `security:manage`). They come from roles and groups with assignment
  windows. A route declares `Depends(require("x:y"))`. Object scope (an owner sees what is assigned) is applied in
  the service on top. Reading a control's automation (`/controls/{id}/automation`) needs `frameworks:read`, not
  `controls:read`: check the router before assuming a key.
- Rate limits (`core/ratelimit.py`) cover sign in, MFA, signup, reset and mail sending; Redis down means they fail closed.
  The client address is read from `X-Forwarded-For` through two proxy hops.

## Audit, errors, secrets

- `audit_service.record(session, action, object_type, object_id, actor, tenant_id, before, after)` in the same
  transaction as the change. The action vocabulary is fixed: `create`, `update`, `delete`, `transition`, `approve`
  (a typed `Literal`; invented strings fail mypy). Snapshot with `fields=` after a flush on rows with server side
  `onupdate` columns.
- `audit_log` and the other history tables (`task_transitions`, `vuln_transitions`, `check_results`,
  `document_versions`, readiness and KRI series) are append only: a database trigger refuses `UPDATE` and `DELETE`.
- Errors are typed `VerityError` subclasses in `core/errors.py`. `message` goes to the reader, `detail` goes to the
  log. One handler maps them to a stable `code` and a correlation id. Some auth errors are uniform on purpose
  (an invite token is a bearer credential, per reason copy would leak): do not "improve" them.
- Secrets are encrypted in the application (`core/crypto.py`, `APP_ENCRYPTION_KEY`) before they reach Postgres, and
  logging redacts by key name.

## Content packs and the control library

- Shipped content lives in `backend/src/verity/seed/content/<pack>/` as JSON plus a `MANIFEST.json` that seals each
  file with a SHA256 over LF normalised bytes. `python -m verity.manage seed-content` (`seed/loader.py`) upserts
  global tables, prunes per pack, and refuses a pack whose files differ from its manifest or whose mappings lack
  `coverage` and a `rationale`. `scripts/seal_content.py` (with `--check`) writes and verifies the seals; a unit test
  enforces it. Packs that contain checks load last.
- A control template has a `canonical_key` (the same concept in two packs collapses into one tenant control), a
  `pack` (the lowercase framework code), a code like `IAM-01` (prefixes BC, CS, DM, EP, GOV, HR, IAM, LM, NS, PE, SD),
  a statement, four guidance steps, a Type, a Sub-type, a Design and an Automation value.
- Tenants hold **copies**. `control_service.instantiate_library` copies templates into `controls`
  (idempotent on tenant and template). Nothing resyncs them afterwards, so changed shipped text needs a data
  migration. Custom controls are `origin=custom`, coded `IC-NN`.

## One library, many frameworks (built 2026-10-10)

- `frameworks.scope_model` is `categories` (SOC 2: the workspace elects Trust Services Categories through its
  engagement) or `applicability` (ISO 27001: everything is in scope unless excluded in the Statement of
  Applicability with a written reason; clauses, `is_always_in_scope`, can never be excluded). `frameworks.position`
  orders them (SOC 2 first); consumers order by `(position, code)`, so never assume `frameworks[0]` is SOC 2 without it.
- `tenant_frameworks` records which frameworks a workspace runs (SOC 2 for every existing tenant, by migration).
  Adoption is per pack: `framework_service.add` calls `instantiate_library` for the framework's pack, then
  `control_service.link_framework`, which links controls the workspace already runs to the new framework's
  requirements, in one audited transaction. Signup and `backfill_adopt_soc2` adopt the SOC 2 pack only.
- Mappings: `template_requirement_map` (global, coverage `full` or `partial`, rationale) is copied to
  `control_requirements` (tenant). One control can serve requirements of several frameworks and is worked,
  owned and evidenced once.
- `engagements` are one per tenant and framework version. ISO audit types: initial certification, surveillance,
  recertification, plus scope statement, certification body, audit date. Every `/engagement*` endpoint takes
  `?framework=CODE` (default `SOC2`).
- Per framework dashboards and coverage count only controls relevant to that framework (mapped to it, or custom and
  unmapped, which count everywhere). `controls_shared` counts controls serving more than one framework.
- `requirement_applicability` holds Statement of Applicability decisions: applicable, justification (a CHECK
  requires one to exclude), operated by (`organization` or `supplier`), owner membership, reviewed at. Implementation
  state is derived, never stored: `met` (every applicable mapped control is ready), `partly` (some ready or started),
  `not_started`, `no_controls`, `excluded`. Exclusion is per requirement, never per control.
- Endpoints (`compliance/tenant_framework_router.py`): `GET/POST /tenant-frameworks`, `GET /frameworks/{id}/overlap`,
  `GET /frameworks/{id}/applicability`, `PUT /frameworks/{id}/applicability/{requirement_id}`,
  `GET /frameworks/{id}/soa.xlsx`. Reads need `frameworks:read`, writes need `controls:manage`.
- ISO text is licensed: the pack carries identifiers and Verity's own wording (`text_policy: id_only`). Probo (MIT)
  gave identifiers and a cross check, never the mappings. Notices are in `THIRD_PARTY_NOTICES.md`.

## Readiness, evidence, connectors

- `compliance/readiness.py` is the one definition: a control is ready when it is `implemented`, has evidence that
  still counts (not rejected, not past renewal) and automation is not `failing`, `error` or `stale`; a requirement is
  met only when every applicable mapped control is ready. Automation can only take readiness away, never grant it.
  Dashboards and exports both use it.
- Evidence anchors to controls (`evidence_controls`), never to requirements, so collect once, satisfy many. Files go
  through `core/storage.py` (local driver by default, S3 by config) with content sniffing; metadata and hashes live in
  Postgres. Evidence from outside carries `source`, `external_id`, `synced_at`, unique on those with the tenant.
- Connectors: global `integration_capabilities`, `checks`, `control_template_checks`; tenant `connections`,
  `check_runs`, `check_results` (partitioned by month to 2028-12, append only), `connection_resources`,
  `integration_requests`. GitHub is the only provider (hard wired plus a database CHECK). `connectors/github.py` is
  pure `collect` and `evaluate`; `service.py` runs start (row lock), collect outside the transaction, finish.
  Results are `pass`, `fail`, `error`, `not_applicable` or `stale`; `error` is never shown as `fail`.
  One evidence file per check, linked only to the controls that check supports. Rules for how a control's checks
  and manual evidence combine are in `connectors/composition.py`.
- The control Checks tab, the criterion chain dialog and the register's "Evidenced by" marks are built on that composition.

## Cross-module primitives

- `links` (polymorphic edge table) and `linkage` (routes and trace, up to four hops, filtered by what the caller may
  read) implement the hybrid linkage model (ADR-0003): explicit join tables for hot pairs, `links` for the long tail.
- `customfields`: tenant defined fields on assets, vulnerabilities and risks (`FIELD_OBJECT_TYPES`), values in a JSONB
  column, definitions archived never deleted. A primitive: models and service, no router (each module exposes its own routes).
- `notifications` (the bell merges pending approvals and campaigns), `ai` (client plus mapping suggestions; output is
  always a draft, evidence is untrusted input to a prompt), `approvals` (placeholder; each module keeps its own).

## Frontend (`frontend/src`)

- React 18, TypeScript, Tailwind, Vite. TanStack Query owns server state (retries only retryable errors, mutations
  never retry). React Router v6 with `BrowserRouter`. react-hook-form with zod. TipTap v3 for documents.
- `features/<module>` mirrors backend modules: `api.ts`, `types.ts`, `hooks.ts`, `components/`. API types are
  maintained by hand in `lib/api/types.ts` and per feature `types.ts`: check them against FastAPI schemas whenever
  a contract changes. `lib/api/client.ts` is the `/api/v1` bearer client (`ApiError` also covers network and timeout).
  `lib/api/describe-error.ts` is the single source for what a person reads when something fails.
- `components/ui` holds primitives only: `PageHeader` (no subtitle slot by design), `TabStrip`, `Toolbar`, `Table`,
  `DetailHeader`, `SegmentedControl`, `CodeChip`, `useTableSort` (pass `null` to keep server order). Module roots follow
  one header pattern (icon, live subtitle, top bar buttons, bar tabs) and share dialogs through typed outlet contexts.
  Copy a recent module, `risks-layout.tsx` or `assets/`, when adding one.
- `lib/nav` keeps filters, search, page and tab per history entry, restores scroll on Back, and builds Back labels.
- The design system (the client's Verity design) lives in `src/index.css`, `styles/ds-tokens.json` and
  `docs/design-system.md`: accent #0284C7, Sora and Inter, semantic status colors that never stand alone. Light mode is
  pinned in `lib/theme.tsx`. Tenant accent is runtime data.
- Frameworks screens read the selected framework from the URL (`?framework=CODE`, default `SOC2`) through
  `features/compliance/use-frameworks.ts`. Routes: `/frameworks/{dashboard,list,scope,soa,coverage}` and
  `/frameworks/:id`. A workspace with one framework shows no switcher.
- Mocks: MSW (`src/mocks`, `VITE_USE_MOCKS`) exists for credential free UI work and is off by default. A host
  environment variable can force it on; a real backend is what the preview normally hits.

## Tests

- `backend/tests/unit` (no database), `tests/integration` (real routes, real database), `tests/isolation` (tenant
  walls, a merge blocker). Helpers in `tests/support` (`signup_workspace`, `tenant_session_headers`, document helpers).
  `VERITY_REQUIRE_DB=1` makes the database suites fail instead of skip. Integration tests take 25 seconds or more
  each because signup is real. Rules for running them are in WORKFLOW.md.

## Where things live

| Looking for | Path |
|---|---|
| Routers mounted | `backend/src/verity/main.py` |
| A module | `backend/src/verity/modules/<name>/` (`assets/` is the reference shape; `compliance/` is the hub) |
| Migrations | `backend/src/verity/db/migrations/versions/` (head `c5d8a2f7e91b`) |
| Import boundary contracts | `[tool.importlinter]` in `backend/pyproject.toml` |
| Scheduled jobs | `backend/src/verity/workers/celery_app.py`, `tasks.py` |
| Management commands | `python -m verity.manage` (`seed-platform-admin`, `reset-password`, `seed-content`) |
| One off scripts | `backend/scripts/` (`seal_content.py`, `backfill_adopt_soc2.py`, `retire_legacy_connector_evidence.py`) |
| Specs and plans | `openspec/changes/*`, `docs/product/*` (the `.docx` files are the signed spec: never edit) |
| Decisions | `docs/adr/` (0001 to 0014) |
| Deploy and backup | `infra/scripts/deploy.sh`, `backup.sh`; runbooks in `docs/runbooks/` |
| User guide (source for the website docs) | `docs/user-guide/` |
