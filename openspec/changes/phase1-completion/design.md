# Design: Phase 1 completion

Each item reuses what is already in the codebase. Nothing here adds a dependency.

## 1. Login rate limit

- Reuse `core/ratelimit.check` (Redis fixed window, fails closed). New named limits next to the
  portal ones: login per account, login per address, MFA verify, signup, password reset, provider
  login. The account key is the sha256 of the lowercased email, never the email (the key reaches
  Redis and logs).
- Every attempt counts, successful or not. At ten per fifteen minutes no real user notices, and it
  avoids a second "failures only" counter.
- The address is read from `X-Real-IP` (nginx overwrites it) only when the immediate peer is a private
  address, so behind the proxy every user is not one bucket and a direct caller cannot pick theirs.
- The stored tenant lockout setting stays unenforced. A rate limit bounds guessing; a lockout
  would let anyone lock a colleague out, which is a different decision.
- `RateLimited` already maps to 429; add `Retry-After`.

## 2. Tasks

Columns already exist (`severity*`, `recurrence_rule`, `next_occurrence_at`, `requires_approval`,
`approval_status`, `task_attachments`). The work is the API, the jobs and the UI.

- **Severity.** Create and edit accept severity; impact and urgency resolve it through the existing
  matrix (`_resolve_severity`); a manual override needs a reason (the CHECK is there).
- **Recurrence.** A restricted RRULE (FREQ daily, weekly, monthly, quarterly as monthly with
  interval 3, yearly, plus INTERVAL and UNTIL or COUNT) computed with stdlib date math. A daily beat
  job spawns the next occurrence as a fresh task pointing at the series head, moves
  `next_occurrence_at`, audits as the system actor and notifies the owner. A repeating task can
  require approval, using the existing `decide_approval`.
- **Attachments.** A transition and the task itself can carry attached evidence: pick an existing
  evidence item (links primitive) or upload a file (stored through `core.storage` with its sha256,
  becomes an evidence item mapped to the task's linked controls). Add and read only, no delete:
  the history stays whole.
- **Renewal task.** A daily beat job finds evidence past its validity with no open renewal task,
  honours the `evidence_stale` automation (its config sets owner, priority and due), creates the
  task idempotently (one open renewal per evidence item), links evidence and controls, notifies the
  owner. System actor in the audit row.

## 3. Type and Sub-type

Decision D1 (week 2) proposed Type from the 11 categories and left Sub-type blank until the client
answered. The client has not, and the register shows neither, so both are populated now from our own
taxonomy and are one content file away from changing.

- **Type** is the existing `category` (the 11 domains), shown and labelled **Type**.
- **Sub-type** is `sub_category`. `controls.sub_category` already exists (migration 20260823_1100, API,
  filter, form); `control_templates` had no such column, so migration `d5c2e8a41f07` adds it. Values
  are authored for all 116 shipped controls (3 to 7 per Type, from each control's own name and description; the spec's
  own words such as CI/CD, Cloud, Endpoint Devices are used where they fit).
- `control_type` (Preventive, Detective ...) and `control_sub_type` (Manual, Automated, Hybrid) are
  kept as they are and relabelled **Design** and **Automation** so the spec's two words mean the
  spec's thing. No existing data or constraint changes.
- Content sealed with `scripts/seal_content.py`; a data migration backfills existing tenant
  controls (same FORCE RLS handling as the earlier content migrations); adoption copies the field.
- Register: Type and Sub-type columns, facets, group by. Status must stay on screen at 1440px.

## 4. Provider plane UI and branding

- Same SPA, route tree `/provider/*`, its own shell and its own session (never mixed with a tenant
  session). Sign in with password then TOTP, enrolling on first use.
- Screens: tenants register (search, status), register tenant (popup), tenant detail with Profile,
  Branding and Provisioning, invite first admin (popup). Only what the existing `/provider/*` API
  supports; missing API is added in `modules/tenancy` (logo upload is the likely one).
- Branding applied after sign-in from `GET /tenant/branding`: workspace name and logo in the shell,
  the primary colour into the accent token (guarded for contrast), the document footer on exports.
  Pre-login branding needs custom domain routing and is not Phase 1.

## 5. Dashboard live

Compose the endpoints that already exist; no new backend. Admin view: the workspace's real posture
(adopted frameworks only, no ISO or HIPAA unless adopted), per category coverage, and tiles from the
live summaries of risks, vendors, vulnerabilities, assets, tasks, evidence and documents. My Day:
the caller's own tasks, approvals, acknowledgements and owned controls. A tile with no source is
removed, not mocked.

## Parallel work rules

Separate databases per stream, migrations chained in a fixed order (`d5c2e8a41f07` column first, then
the sub-type backfill, then tasks if it needs one), disjoint files per stream, no commits.
