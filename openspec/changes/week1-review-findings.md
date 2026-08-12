# Week 1 adversarial review — findings and disposition

An adversarial review (six dimensions — isolation, auth, audit, secrets, spec-divergence,
contract — each finding independently verified by a refutation pass) ran against the Week 1
build. 26 findings raised, 2 refuted, 24 confirmed. This file records the disposition of every
confirmed finding so none is lost.

## Fixed in this cycle

| # | Sev | Finding | Fix |
|---|-----|---------|-----|
| 20 | critical | Audit-log page white-screens: backend omits `actor_label`/`object_label` the UI renders | Backend emits both (best-effort humanized labels); UI renders null-safe |
| 21 | high | Invite dialog defaulted `role_id` to a mock fixture id → 422 on real backend | UI defaults the role from `GET /roles` by name; never sends a non-UUID |
| 22 | high | Workspace switch dead-ends when the target org requires MFA | UI handles the full login union from `/workspaces/switch` (mfa_required → challenge) |
| 9 | high | Login issues a session to a membership whose only role assignment is out of window | Login excludes memberships with no in-window role; expired sole guest → 401 (the time-box guarantee) |
| 24 | med | Signed-in users couldn't accept an invitation (PublicOnly bounced `/accept-invite`) | Route ungated; existing-user accept offers to switch into the new workspace |
| 1 | med | Provider-internal `notes`/`created_by` leaked into the tenant's own audit stream | Tenant audit snapshots exclude those fields |
| 2, 3 | med/low | TOTP counter and recovery-code consumption were non-atomic (concurrent replay) | `SELECT … FOR UPDATE` on the credential row serialises the guard-then-write |
| 11 | med | Promised sign-out `delete on session` audit row was never written | `POST /auth/logout` writes it; UI calls it on sign-out |
| 4 | med | `accept_invitation` set `user.full_name` without an audit row | Audited as `update` on `user` |
| 7 | low | Validation-error logs echoed raw field input (a TOTP code could reach logs) | Handler strips `input` from logged validation errors |
| 23 | med | MFA recovery codes generated once but never shown; no recovery-code sign-in | UI shows codes once post-enrollment; sign-in offers "use a recovery code" |

## Deferred — tracked, not blocking Week 1

Genuine but low-impact; scheduled for the hardening pass after the Week 1 demo.

- **#12 (med)** — no route to remove a member from a group, and no group rename/delete. `tasks.md`
  4.2 listed member add/remove; only add shipped. Add `DELETE /groups/{id}/members/{mid}`, group
  rename, and group delete (disable-style) next.
- **#10 (med)** — signup `Idempotency-Key` replay returns 409 instead of the original result when
  the *first* attempt used the fallback (suffixed) slug because the base slug was taken. Narrow
  edge (two companies, same name, same key, retried). Fix: record the resolved slug with the
  idempotency key and replay against it.
- **#5 / #14 / #15 (low)** — invite idempotency edges: re-inviting a still-`invited` member mints a
  fresh token with no audit trace (#5) and ignores a changed role/window (#15); provider
  `admin-invite` does not reactivate a disabled membership (#14). Tighten invite idempotency to
  audit re-issues and honour role/window changes.
- **#6 (low)** — failed-attempt attribution falls back to `system`/no-tenant for disabled members
  and non-active tenants, losing the tenant stream. Attribute to the matched membership when the
  identity resolved, per decision 3.
- **#8 (low)** — the MFA-enrollment challenge JWT rides in the URL query (`/mfa/enroll?challenge=`)
  and is not stripped from history. 5-minute TTL; move it to navigation state / strip on mount.

## Spec to amend (code is right; the document lags)

- **#13 (low)** — inviting an already-active member returns 409 `already_member`; `design.md` said
  "no-op returning the existing row". The 409 is the better contract and matches the frontend and
  its mock. Amend `add-identity-and-access/design.md`.
- **#16 (low)** — identity-plane lookups run inside `provider_session_scope` (sets
  `app.provider_plane`) rather than "no flag set" as `design.md` states. Safe (those tables have no
  RLS; the new provider SELECT policies on the identity tables admit nothing a tenant could reach),
  but record the deviation in `design.md`.
- **#17 (low)** — `EngagementScope.allows(…, object_id)` treats its argument as an engagement id,
  not the object-under-access id the `ObjectScope` protocol defines. No caller in Week 1 (the scope
  is exercised only by unit tests); reconcile the signature when the compliance module first uses it.
- **#18 (low)** — the spec's "read own profile and permissions" route was not built; the frontend
  reads the principal from the login/session response instead, so nothing needs it in Week 1. Drop
  it from the spec or add it when a settings/profile screen needs a refresh endpoint.
- **#19 (low)** — built-in roles are seeded at first-admin-invite for provider-registered tenants
  rather than at registration. Benign (no one can reach the tenant before its admin exists), but
  decision 14 says "at tenant creation"; seed at registration for exactness.

## Refuted (raised, did not hold)

Two findings were dropped by the verification pass as not reproducible against the actual code.
