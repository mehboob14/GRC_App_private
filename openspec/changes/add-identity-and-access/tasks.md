# Tasks — identity and access

Each task is at most two hours. Every migration enables RLS and adds its policies in the same
migration. The isolation test ships in this change.

## 1. Models and migration

- [ ] 1.1 Add `modules/iam/models.py` for all ten tables, with every `CHECK` constraint from
      `design.md`, and with person-reference columns pointing at `tenant_memberships.id`.
- [ ] 1.2 Write the migration: create the tables, every unique and leading-`tenant_id` index,
      `ENABLE` + `FORCE ROW LEVEL SECURITY` and the tenant policy on every tenant-owned table, and
      the grants — in this one migration. `engagement_id` is a bare nullable uuid; no FK.
- [ ] 1.3 Seed migration or startup seed for the Week 1 `permissions` rows listed in `design.md`.
- [ ] 1.4 Verify `alembic upgrade head` / `downgrade -1` / `upgrade head`, and that the downgrade
      docstring states that it destroys every user and membership.

## 2. Permission resolution and `require`

- [ ] 2.1 Implement effective-permission resolution: direct assignments ∪ group assignments, honouring
      `valid_from` / `valid_until`, for a membership.
- [ ] 2.2 Complete `core/deps.py`: `get_current_principal`, `get_tenant_context` (tenant from the
      membership, never from the request), and `require(permission, scope=...)`.
- [ ] 2.3 Implement the `ObjectScope` protocol and the `EngagementScope` concrete scope; unit-test
      that flat denial is 403 and scope denial is 404.
- [ ] 2.4 Unit-test that a token for membership-in-A cannot bind tenant B, and that a provider-plane
      token is refused by every tenant-plane dependency.

## 3. Native auth and MFA

- [ ] 3.1 `POST /api/v1/auth/signup` — trial signup in one transaction via the tenancy registration
      service; create user, credentials (argon2id), membership (Admin), and the built-in roles for
      the new tenant. Honour `Idempotency-Key`. Audit the creations.
- [ ] 3.2 `POST /api/v1/auth/login`, `/mfa/verify`, `/mfa/enroll`, `/mfa/confirm` — same challenge /
      session split as the provider plane; Admin memberships require TOTP; replay counter enforced.
- [ ] 3.3 `POST /api/v1/auth/workspaces` and `/workspaces/switch` — list memberships, issue a new
      session for another membership, audit the switch.
- [ ] 3.4 Integration-test the authentication scenarios, including timing-indistinguishable misses
      and that secrets never appear in any response.

## 4. Memberships, groups, roles

- [ ] 4.1 Membership routes: list, invite, accept, disable. Permissions `members:read` /
      `members:invite` / `members:disable`. Inviting an existing membership is idempotent.
      Cross-tenant membership ids are 404.
- [ ] 4.2 Group routes: CRUD and member add/remove. Permissions `groups:read` / `groups:manage`.
      Members are membership ids; a user id is rejected at validation.
- [ ] 4.3 Role routes: list, create custom, assign / unassign to membership or group, set the
      time-box columns. Permissions `roles:read` / `roles:manage`. Built-in roles refuse delete with
      409.
- [ ] 4.4 On tenant creation (signup and provider registration), seed the five built-in roles and
      attach Admin to the first membership. Seed is idempotent.
- [ ] 4.5 Every state-changing path above writes the audit trail in the same transaction; integration-
      test that a rolled-back invite leaves no audit row.

## 5. Federation seam

- [ ] 5.1 Confirm `user_identities` is created by the migration with the unique constraints from
      `design.md`, and that no router, service, or repository in this change imports it for read or
      write.
- [ ] 5.2 Unit-test that the unique constraint on `(provider, external_subject_id)` holds, so Phase 3
      has a real seam to hang off rather than a table-shaped hope.

## 6. Isolation tests — ship in this change

- [ ] 6.1 `tests/isolation/test_iam_isolation.py`: seed tenants A and B with memberships, groups,
      roles, and assignments in each. Assert every list, read, update, and delete from an A session
      touches nothing of B, and that cross-tenant reads are 404.
- [ ] 6.2 Seed one user with memberships in both A and B. Assert an A-bound session cannot see the
      B membership, B's groups, or B's role assignments, including the user's own.
- [ ] 6.3 Assert a write carrying the wrong `tenant_id` is refused by `WITH CHECK`.
- [ ] 6.4 Assert Admin login without TOTP cannot obtain a session, and that a non-admin login can.

## 7. Week 1 demo script

- [ ] 7.1 A documented, runnable sequence of API calls that: creates an organisation (provider),
      self-signups a trial, puts users into groups and roles, adds one user across two organisations,
      and lists the audit log showing every action. Lives in `docs/runbooks/week1-demo.md`.
- [ ] 7.2 The sequence is also an integration test, so the demo cannot rot silently.

## 8. Docs — including the ER correction

- [ ] 8.1 Update the ER Design document: regenerate the identity diagrams so they show
      `tenant_memberships`, global `users` / `credentials` / `user_identities`, groups-of-memberships,
      and `role_assignments` with the time-box. The working summary in
      `docs/architecture/data-model.md` is updated in the same commit.
- [ ] 8.2 Clarify ADR-0011: the auditor time-box columns live on `role_assignments`, not on
      `tenant_memberships`. The capability is per-membership; the columns are per-assignment.
- [ ] 8.3 Finish the ADR-0007 cleanup begun in `add-provider-plane` if any stale wording remains.
- [ ] 8.4 `docs/architecture/multi-tenancy.md`: document that identity-plane lookups run with no
      tenant bound, and why that is safe.
- [ ] 8.5 Record the derived columns that were approved — especially `credentials.last_totp_counter`
      and `user_identities.provider_type` — so a future reader does not treat them as drift.
