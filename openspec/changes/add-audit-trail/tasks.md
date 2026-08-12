# Tasks — platform-wide audit trail

Each task is at most two hours. The migration enables RLS and adds every policy in the same
migration. The isolation test ships in this change.

## 1. Append-only DDL helper

- [ ] 1.1 Extend `verity.db.rls.make_append_only` to emit the shared `CREATE OR REPLACE FUNCTION`
      trigger function alongside the existing `REVOKE`, and to attach a `BEFORE UPDATE OR DELETE`
      trigger to the named table. Add the matching `drop_append_only` for downgrades.
- [ ] 1.2 Unit-test the generated DDL text: the function is created idempotently, the trigger names
      follow the convention, and the revoke targets the application role and not the owner.

## 2. Model and migration

- [ ] 2.1 Add `modules/audit/models.py`: the `AuditLog` model, UUIDv7 primary key, nullable
      `tenant_id` with **no** foreign key, `actor_type`/`actor_id` with the paired `CHECK`, and the
      `action` and `actor_type` status checks as `CHECK` constraints rather than enums.
- [ ] 2.2 Add the ORM `before_update` and `before_delete` listeners that raise on any attempted
      mutation, and unit-test both with no database.
- [ ] 2.3 Write the migration: create the table, the three `tenant_id`-leading indexes, `ENABLE` and
      `FORCE ROW LEVEL SECURITY`, all four policies, the revoked grant, and the trigger — in this one
      migration. Grant `SELECT, INSERT` to the application role.
- [ ] 2.4 Verify `alembic upgrade head` then `downgrade -1` then `upgrade head` runs clean against a
      real Postgres, and that the downgrade docstring states that it destroys the audit trail.

## 3. Provider-plane session scope

- [ ] 3.1 Add `bind_provider_plane()` to `core/rls.py` next to `bind_tenant_context`, using the same
      `set_config(..., true)` primitive and the same "must be inside a transaction" guard.
- [ ] 3.2 Add `provider_session_scope` to `core/db.py`, and a placeholder dependency in `core/deps.py`
      that will be completed when platform-admin authentication lands in `add-provider-plane`.
- [ ] 3.3 Unit-test that the provider setting is transaction-local, does not survive commit or
      rollback, and does not leak across a pooled connection — mirroring the existing tenant-context
      tests.

## 4. Repository and service

- [ ] 4.1 Add `modules/audit/repository.py`: insert, and the cursor-paginated list keyed on
      `(occurred_at, id)`.
- [ ] 4.2 Add `modules/audit/service.py`: `AuditService.record(...)` taking the caller's session, and
      the `Actor` value objects for membership, platform admin, and system.
- [ ] 4.3 Add `AuditService.snapshot(...)`, importing the secret deny-list from `core/logging.py`
      rather than restating it. Unit-test that a password hash and an encrypted MFA secret are
      redacted while the fact of the change survives.
- [ ] 4.4 Unit-test the three actor kinds, including that a `system` actor with an actor id and a
      `membership` actor without one are both rejected before reaching the database.

## 5. Route

- [ ] 5.1 Add `modules/audit/schemas.py` and `router.py`: `GET /api/v1/audit-log`, cursor-paginated,
      declaring permission key `audit:read`. Reject any client-supplied tenant parameter.
- [ ] 5.2 Mount the router in `main.py` behind the `/api/v1` prefix.
- [ ] 5.3 Integration-test 200 for a permitted caller, 403 for a caller without `audit:read`, 401
      unauthenticated, and 404 — never 403 — for a record belonging to another tenant.

## 6. Isolation and append-only tests — ship in this change

- [ ] 6.1 `tests/isolation/test_audit_isolation.py`: seed tenants A and B plus provider-plane rows.
      Assert A sees only A, an unbound session sees nothing, and no tenant session sees a
      provider-plane row in a list or a count.
- [ ] 6.2 Assert a session bound to A cannot insert a record carrying B, and that a provider-plane
      session can insert both a tenant-stream row and a no-tenant row.
- [ ] 6.3 `tests/integration/test_append_only.py`: `UPDATE` and `DELETE` are refused for the
      application role **and** for the owner role, and the ORM listeners fire before a flush reaches
      the database.
- [ ] 6.4 Integration-test transactional atomicity: a unit of work that raises leaves neither the
      change nor the audit record.

## 7. Docs — a change that makes a doc wrong is not done

- [ ] 7.1 `docs/architecture/multi-tenancy.md`: document `app.provider_plane`, what sets it, and the
      four-policy pattern on a table that serves both planes.
- [ ] 7.2 `docs/conventions/database.md`: name append-only tables as the documented exception to
      `created_at`/`updated_at`, and record that append-only is enforced by revoke **and** trigger.
- [ ] 7.3 `docs/architecture/data-model.md`: record the `audit_log` actor model and the deliberate
      absence of foreign keys on `tenant_id` and `actor_id`, with the teardown reasoning.
- [ ] 7.4 Raise the four ER-document deviations in `proposal.md` as a correction list for the ER
      Design document, so the source of truth stops disagreeing with the schema.
