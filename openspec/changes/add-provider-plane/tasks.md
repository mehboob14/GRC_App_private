# Tasks — provider plane

Each task is at most two hours. Every migration enables RLS and adds its policies in the same
migration. The isolation test ships in this change.

## 1. Shared authentication primitives

- [ ] 1.1 Add `core/security.py`: argon2id hash and verify at the pinned parameters in `design.md`,
      with a rehash-needed signal on verify.
- [ ] 1.2 Add TOTP: enroll (generate secret + provisioning URI), verify with a one-step window, and
      store the last accepted counter so a code cannot be replayed inside its window.
- [ ] 1.3 Add recovery-code generation: single-use codes returned once in plaintext and stored as
      argon2id hashes; verifying a code consumes it.
- [ ] 1.4 Add signed session tokens and the short-lived MFA challenge token, as distinct types that
      cannot be substituted for each other. Tokens carry subject and plane and nothing
      authorization-bearing.
- [ ] 1.5 Unit-test hashing (including the timing-safe miss path), TOTP enrollment and replay
      rejection, recovery-code consumption, and that a challenge token is refused by every
      session-consuming dependency.

## 2. Models and migration

- [ ] 2.1 Add `modules/tenancy/models.py` for all four tables, with status and role `CHECK`
      constraints rather than enums, and with the platform-admin credential columns pending the
      review decision in `proposal.md`.
- [ ] 2.2 Write the migration: create the four tables, every unique and leading-`tenant_id` index,
      `ENABLE` and `FORCE ROW LEVEL SECURITY` on each, and every policy from `design.md` — in this
      one migration. Grant the application role `SELECT, INSERT, UPDATE, DELETE` as appropriate per
      table.
- [ ] 2.3 Verify `alembic upgrade head` / `downgrade -1` / `upgrade head` against a real Postgres,
      and that the downgrade docstring states that it destroys every tenant.

## 3. Platform-admin authentication

- [ ] 3.1 Seed path for the first platform admin (a management command or a migration-time insert
      gated on emptiness), with MFA enrollment forced on first login. Document how the operator
      boots the first admin.
- [ ] 3.2 Implement `POST /api/v1/provider/login` (password → challenge), `POST .../mfa/verify`, and
      `POST .../mfa/enroll` + `.../mfa/confirm`. No session is issued until TOTP succeeds.
- [ ] 3.3 Wire `get_current_platform_admin` and `require_provider(permission)` in `core/deps.py`,
      binding `app.provider_plane` for the request's transaction and never binding a tenant.
- [ ] 3.4 Every state-changing path in this section calls `AuditService` in the same transaction:
      login, failed login, enrollment, failed TOTP.
- [ ] 3.5 Integration-test the scenarios in the authentication requirement, including that the
      response and the wall time are the same for a missing email and a wrong password.

## 4. Registration, branding, provisioning

- [ ] 4.1 `POST /api/v1/provider/tenants` — register a tenant, create its branding row empty, create
      its four provisioning steps, write the audit records, honour `Idempotency-Key`. Permission:
      `tenants:create`.
- [ ] 4.2 `GET /api/v1/provider/tenants` (cursor-paginated) and `GET .../tenants/{tenant_id}`.
      Permission: `tenants:read`. Unknown id is 404.
- [ ] 4.3 `PATCH /api/v1/provider/tenants/{tenant_id}` for the profile fields. Permission:
      `tenants:update`. Status transitions are a separate, audited action, not a free field write.
- [ ] 4.4 `PUT /api/v1/provider/tenants/{tenant_id}/branding` — encrypt SMTP credentials through
      `core/crypto.py` with AAD bound to the tenant, exclude them from the response and from both
      audit snapshots. Permission: `tenants:brand`.
- [ ] 4.5 `POST /api/v1/provider/tenants/{tenant_id}/provision` and `GET .../provisioning`. Running
      is idempotent; completed steps are not re-run; `seed_content` and `invite_admin` stay pending
      and are reported as such. Permission: `tenants:provision` / `tenants:read`.
- [ ] 4.6 Integration-test registration idempotency, the slug conflict as 409 with no partial
      rows, branding encryption, and that a second provisioning run writes nothing.

## 5. Tenant-plane reads

- [ ] 5.1 `GET /api/v1/tenant` and `GET /api/v1/tenant/branding`, resolving the tenant from the
      session. Permission: `tenant:read`. Refuse any write of status, plan, or slug through these
      routes.
- [ ] 5.2 These routes cannot be exercised end-to-end until a tenant session exists in
      `add-identity-and-access`. Ship them now behind a fixture that mints a session for the
      isolation suite, and leave the production wiring for that change.

## 6. Isolation tests — ship in this change

- [ ] 6.1 `tests/isolation/test_tenancy_isolation.py`: seed two tenants and one platform admin.
      Assert a session bound to A sees only A's tenant, branding, and provisioning rows; sees no
      platform admin; and cannot write B's branding or provisioning.
- [ ] 6.2 Assert an unbound session sees nothing on any of the four tables.
- [ ] 6.3 Assert a provider-plane session sees both tenants and that a tenant-plane token is refused
      by every provider route with 403.
- [ ] 6.4 Assert that a platform-admin login is impossible without a valid TOTP code, including
      after a correct password.

## 7. Docs

- [ ] 7.1 `docs/architecture/multi-tenancy.md`: document the provider-plane session, the two-plane
      policy table, and that `tenants` is itself RLS-protected on its primary key.
- [ ] 7.2 `docs/architecture/data-model.md` and the ER Design document: apply the approved resolution
      of deviation 1 (credential columns or a credentials table), and correct rule 2's wording so it
      stops claiming branding and provisioning carry no `tenant_id`.
- [ ] 7.3 `docs/runbooks/local-setup.md`: the command that creates the first platform admin and how
      to enroll its TOTP.
- [ ] 7.4 Resolve ADR-0007's stale Alternatives and Consequences sections that still reject global
      users and claim "two accounts" — those contradict ADR-0011 and are corrected in this change's
      doc task rather than left for later.
