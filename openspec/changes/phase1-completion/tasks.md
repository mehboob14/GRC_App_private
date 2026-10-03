# Tasks: Phase 1 completion

Integration and isolation tests run against a scratch database, never `verity` and never two
streams on one database. Gates per stream: ruff, mypy, import-linter, its tests, `tsc -p
tsconfig.app.json`, eslint on touched files. Whole-tree gates and `vite build` run once at the end.

## 0. Plan

- [x] 0.1 Audit against the signed spec and the build plan (Phase 1 only).
- [x] 0.2 Proposal, design, tasks.
- [x] 0.3 Scratch databases `verity_t_tasks`, `verity_t_ctl`, `verity_t_prov` from `verity_test`.

## 1. Login rate limit (core, iam)

- [x] 1.1 Named limits in `core/ratelimit.py`; `Retry-After` on 429.
- [x] 1.2 Apply to login, MFA verify and confirm, signup, password reset, verification resend, provider login.
- [x] 1.3 Client address from `X-Real-IP` behind the proxy (no compose change); documented in `docs/conventions/api.md`.
- [x] 1.4 Tests: helpers (unit), eleventh attempt, other account, address, MFA, reset, provider (integration). Sign in message shows the wait from `Retry-After`.

## 2. Tasks

- [x] 2.1 Severity on create and edit; matrix resolve; override with reason. API and form.
- [x] 2.2 Recurrence: validate and store the rule, compute `next_occurrence_at`, create and edit.
- [x] 2.3 Beat job spawning the next occurrence; audit, notify, series head.
- [x] 2.4 Recurring tasks can require approval; the form toggle; closing waits for the decision.
- [x] 2.5 Attachments: upload, attach existing evidence, list, download; transition carries them (an attachment is an evidence item plus the evidence to task link; `task_attachments` stays unused).
- [x] 2.6 Beat job for stale evidence renewal tasks; idempotent; honours the automation toggle.
- [x] 2.7 Frontend: form (severity, repeat, approval), transition popup (attach), detail (attachments).
- [x] 2.8 Tests: unit (recurrence maths, severity), integration (create with rule, spawn, approval
      gate, attach, renewal task once, none after close and renew).

## 3. Type and Sub-type

- [x] 3.0 Column `control_templates.sub_category` (migration `d5c2e8a41f07`, applied to the scratch databases).
- [x] 3.1 Template side: loader, adoption copy, schemas and service expose it; vocabulary for the form.
- [x] 3.2 Author Sub-type for all 116 controls; reseal manifests; loader and adoption copy it.
- [x] 3.3 Backfill migration (after `d5c2e8a41f07`): set `controls.sub_category` from the template where it is empty.
- [x] 3.4 Relabel `control_type` Design and `control_sub_type` Automation in the UI.
- [x] 3.5 Register: Type and Sub-type columns, facets, group by; detail; form for custom controls.
- [x] 3.6 Tests: content integrity, every control has both, adoption copies, filters, migration round trip.

## 4. Provider plane UI and branding

- [ ] 4.1 Provider session, sign in with TOTP and enrolment.
- [ ] 4.2 Tenants register and register popup.
- [ ] 4.3 Tenant detail: profile, branding, provisioning, invite first admin.
- [ ] 4.4 Logo upload and serve (backend if missing).
- [ ] 4.5 Branding applied in the tenant shell, accent token with contrast guard, export footer.
- [ ] 4.6 Tests: provider routes the UI needs, branding read by a tenant, logo upload limits.

## 5. Dashboard live

- [x] 5.1 Admin dashboard on live data; remove fabricated frameworks and tiles.
- [x] 5.2 My Day on live data.
- [x] 5.3 Loading, empty and error states; deep links.

## 6. Close out

- [x] 6.1 Single head `a3b9c7e15d68` (tasks needed no schema change); upgrade, downgrade, upgrade verified on a scratch database.
- [ ] 6.2 Whole-tree gates, full unit and integration run on `verity_test`, `vite build`.
- [ ] 6.3 Look at every changed screen in a browser at 1440px.
- [ ] 6.4 Update the user guide pages and the deployment runbook where they changed.
