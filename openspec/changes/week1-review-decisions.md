# Week 1 review decisions — approval record

Review outcome for `add-audit-trail`, `add-provider-plane`, `add-identity-and-access`.
Every decision those changes flagged is settled here; implementation follows this record.
Recorded 2026-08-12 by the project owner (via review). This file is the "explicit approval"
the proposals asked for and is removed when the changes archive.

## add-audit-trail

1. **ER deviations — APPROVED as designed:** `tenant_id` nullable with no FK (stream semantics,
   NULL = provider plane); polymorphic `actor_type`/`actor_id` pair with no FK; `occurred_at`
   only (append-only exception to created_at/updated_at); five-verb action CHECK.
2. **Action taxonomy — five verbs stay.** Login = `create` on `object_type='session'`
   (object_id = the token's `jti`); sign-out = `delete` on the same. Workspace switch = `create`
   on `session` in the target tenant's stream (a switch issues a new session; no extra verb).
3. **Failed attempts (gap resolved):** failed password, failed TOTP, and completed MFA enrollment
   are events, not state changes, and get `action='create'` on `object_type='auth_attempt'`
   (failures) / `'mfa_enrollment'` (completed enrollment), `object_id` = minted UUIDv7,
   `after` = a minimal outcome map (e.g. `{"outcome": "failed_password"}`). Actor = the matched
   membership/platform_admin when the identity resolved; `system` with `after.reason='unknown_email'`
   when it did not. Never an email address or any credential material in snapshots.
4. **`app.provider_plane` GUC policy — APPROVED** (over the dedicated-role alternative).
   Revisit when the provider admin panel grows real tenant-data reads.

## add-provider-plane

5. **Platform-admin credentials — APPROVED on `platform_admins`** (`password_hash`,
   `mfa_secret_encrypted`, `recovery_codes_encrypted` columns; no separate table). Platform
   admins remain a separate population from tenant `credentials`.
6. **Rule-2 rewording — APPROVED:** `tenant_branding` / `tenant_provisioning` keep `tenant_id`
   per the ER and get RLS; CLAUDE.md rule 2 is reworded to cover `platform_admins` + `tenants`
   only (doc task in the change).
7. **`tenants.created_by` nullable — APPROVED** (self-service signup has no admin).
8. **No `failed` provisioning status — APPROVED** (failing step stays `pending`, retried).
9. **RLS on `tenants` keyed on its own PK — APPROVED** (strengthening of ADR-0007).
10. **Provisioning dead-end (gap resolved) — Week 1 step semantics:**
    - `create_tenant`: done at registration.
    - `seed_content`: completes as an honest no-op ("0 templates instantiated" — the global
      content library does not exist yet). Does real work when the library lands.
    - `invite_admin`: done when the tenant has ≥1 Admin membership recorded (self-signup:
      immediately; provider path: when the admin invitation is recorded).
    - `verify`: completes only when the other three are done AND ≥1 **active** Admin membership
      exists. Tenant → `active` in the same transaction as the last step.
    So a self-signup tenant reaches `active` inside the signup transaction; a provider-created
    tenant reaches `active` when its invited admin accepts. Tenant-plane login requires
    `tenants.status='active'` (provisioning/suspended/terminated → 401, no session, audited).

## add-identity-and-access

11. **Derived schema — APPROVED as written in design.md,** including `credentials.last_totp_counter`
    (TOTP replay protection) and `user_identities.provider_type`. ER document correction is the
    change's doc task.
12. **Auditor time-box on `role_assignments` — APPROVED.** ADR-0011 amended 2026-08-12 (done).
13. **Admin "every key" resolved at check time — APPROVED.**
14. **Permission seed mechanism:** the Week 1 permission keys are seeded in the same migration
    that creates `permissions` (INSERT … ON CONFLICT DO NOTHING). Built-in roles are seeded
    per tenant by the iam service at tenant creation (both signup and provider registration),
    idempotently.
15. **Membership accept (gap resolved — required by the Week 1 demo):** invites carry a signed
    single-use invite token (`typ='invite'`, 7-day TTL, subject = membership id). Because email
    delivery is a notifications-module concern, Week 1 returns the invite token/link **once, in
    the invite response**, for the inviter to hand over; this is recorded as a deliberate Week 1
    affordance, removed when notifications land. `POST /api/v1/auth/invitations/accept`
    (unauthenticated; token + full_name + password for new users, token alone for existing
    users) activates the membership, consumes the token, writes the audit rows. Accepting is
    what flips an `invited` membership to `active`.
16. **Password change / password reset — OUT of Week 1.** The proposal mentioned them; no task,
    route, or spec scenario exists. Deferred to the notifications change (reset needs delivery).
    Flagged, not silently dropped.

## Cross-cutting

17. **Session tokens (gap resolved):** PyJWT HS256 with `SECRET_KEY`. Claims: `sub`, `plane`
    (`tenant`|`provider`), `typ` (`session`|`challenge`|`selection`|`invite`), `iat`, `exp`,
    `jti` (UUIDv7 — the audit `session` object_id). TTLs: session **12h** (configurable,
    `AUTH_SESSION_TTL_HOURS`), MFA challenge **5m**, workspace-selection token **5m**, invite
    **7d**. No token revocation store in Week 1: enforcement is per-request DB state (disabled
    membership/admin or non-active tenant → 401 regardless of token validity). Sign-out is
    client-side discard + `delete` on `session` audit row.
18. **Multi-membership login:** password (+ TOTP where required) verified → if the user has >1
    active membership, the response is `select_workspace` with a short-lived selection token;
    the session is issued by `POST /auth/workspaces/select`. Matches the already-built frontend
    contract.
19. **MFA policy:** platform admins — TOTP always, no exceptions. Tenant plane — TOTP required
    for memberships holding the Admin role; others password-only in Week 1.
20. **Tenant "security policy" endpoint:** does NOT exist (no table in the data model; the
    frontend mock invented a toggle). The Settings → Security screen renders the platform's
    enforced policy read-only from `GET /api/v1/tenant` + fixed facts; no invented schema.
21. **API port on this machine:** 8001 (8000 is occupied by an unrelated app). Frontend dev
    proxy targets `http://127.0.0.1:8001`.
