# Design — platform-wide audit trail

## What `tenant_id` means on this table

`audit_log.tenant_id` is **the tenant stream the event belongs to, not the actor's tenant.** A
platform admin provisioning tenant X writes `tenant_id = X` with `actor_type = 'platform_admin'`, so
the event appears in X's own history where an auditor will look for it. Events that belong to no
tenant — a platform admin logging in, a global-content edit — carry no tenant.

This is the decision that makes one table serve both planes, and it is why the actor and the stream
are two independent facts rather than one.

## Table

```
audit_log
  id           uuid        PK, UUIDv7
  tenant_id    uuid        NULL          -- the stream, not the actor. NULL = provider plane.
  actor_type   text        NOT NULL      -- CHECK IN ('membership','platform_admin','system')
  actor_id     uuid        NULL          -- NULL when actor_type = 'system'
  action       text        NOT NULL      -- CHECK IN ('create','update','delete','transition','approve')
  object_type  text        NOT NULL
  object_id    uuid        NOT NULL
  before       jsonb       NULL          -- NULL on create
  after        jsonb       NULL          -- NULL on delete
  occurred_at  timestamptz NOT NULL DEFAULT now()
```

`CHECK (actor_type = 'system') = (actor_id IS NULL)` — a system row cannot name an actor and a
person row cannot omit one. Without this the discriminator is decoration.

### Why there are no foreign keys

Neither `tenant_id` nor `actor_id` is a foreign key, and both are deviations from the ER diagram that
need explicit approval.

**`actor_id`** cannot be one: it points at `tenant_memberships`, `platform_admins`, or nothing,
depending on `actor_type`. That is a polymorphic reference and Postgres has no constraint for it.
This is what makes the audit slice shippable before identity exists.

**`tenant_id`** is the more interesting one. Hard deletion is permitted for tenant teardown
(`docs/conventions/database.md`). With `ON DELETE CASCADE`, teardown issues a `DELETE` against an
append-only table, which the trigger below refuses, so teardown fails. With `ON DELETE RESTRICT`,
teardown fails for the same reason from the other direction. With `ON DELETE SET NULL`, Postgres
issues an `UPDATE`, which the trigger also refuses.

Every foreign-key action is incompatible with append-only. And the compliance answer agrees with the
mechanical one: the record of a tenant being torn down is precisely the record you must not lose with
the tenant. So the trail outlives the objects it describes, and `tenant_id` is an unconstrained uuid.

### Why `occurred_at` and no `updated_at`

`docs/conventions/database.md` puts `created_at` and `updated_at` on every table. An `updated_at` on
a table that refuses `UPDATE` is a column that can only ever repeat `occurred_at`. The ER diagram
shows `occurred_at` alone and that is what ships. The convention doc gets a sentence naming
append-only tables as the exception.

### Why `login` is not an action value

The ER enumerates five actions. Authentication is recorded as `create` on `object_type = 'session'`
with the session identifier as `object_id`, and sign-out as `delete` on the same pair, rather than
adding a sixth value that is not in the data model. If you would rather have `login` and `logout`
outright, that is a one-line change to the `CHECK` constraint and a line in the ER document — say so
at review and it goes in now rather than as a constraint migration later.

## Row-level security

Four policies. Postgres combines permissive policies with `OR`, which is what lets the provider plane
read across streams without weakening the tenant predicate.

```sql
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

CREATE POLICY audit_log_tenant_select ON audit_log FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY audit_log_tenant_insert ON audit_log FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY audit_log_provider_select ON audit_log FOR SELECT
  USING (NULLIF(current_setting('app.provider_plane', true), '') = 'on');

CREATE POLICY audit_log_provider_insert ON audit_log FOR INSERT
  WITH CHECK (NULLIF(current_setting('app.provider_plane', true), '') = 'on');
```

No `UPDATE` or `DELETE` policy exists. With RLS enabled and no policy for a command, the command
matches nothing — a third wall behind the revoked grant and the trigger.

`tenant_id IS NULL` never satisfies the tenant predicate, because `NULL = anything` is `NULL` and a
policy admits a row only on `true`. Provider-plane rows are therefore invisible to every tenant-plane
session by construction rather than by filtering, and an unbound session sees nothing at all. The
isolation test asserts this directly rather than trusting the reasoning.

### The `app.provider_plane` GUC, and what it costs

This is the security-sensitive part of the change and should be reviewed as such.

`app.provider_plane` is a transaction-local setting, bound exactly like `app.tenant_id` and through
the same `set_config(..., true)` primitive, by one dependency: the provider-plane session scope,
which runs only after a platform admin has been authenticated. It is never derived from a request
parameter, a header, or a token claim that a tenant user can influence.

It is, honestly, a switch that widens visibility, and it is only as strong as the code that sets it.
That is the same property `app.tenant_id` already has — a bug that binds the wrong tenant is a
cross-tenant read regardless of RLS — so this does not introduce a new class of risk, but it does add
a second place where that class applies.

**The stronger alternative, not taken:** give the provider plane its own database role with its own
policy (`TO verity_provider USING (true)`), and a second connection pool. That cannot be reached by
executing a statement, only by holding a different connection. It was rejected for this change
because the rest of the provider plane does not need it: `tenants`, `tenant_branding`,
`tenant_provisioning`, and `platform_admins` have no `tenant_id` and therefore no RLS at all, so
their protection is already application-level permission checks. Adding a second role to defend one
table, while four others sit behind application checks alone, buys less than it looks like it does.
If provider-plane reads later grow into a real admin panel over tenant data, that is the point to
revisit it, and the policy above is replaced rather than extended.

## Append-only enforcement

Three layers, because each covers what the others miss.

1. **Revoked grant** — `REVOKE UPDATE, DELETE ON audit_log FROM verity_app`. Stops the application
   role. Does not bind the table's owner.
2. **Trigger** — `BEFORE UPDATE OR DELETE ... FOR EACH ROW EXECUTE FUNCTION audit_log_append_only()`,
   raising an exception naming the rule. Binds the owner too, which is what migrations run as.
3. **ORM event listeners** — `before_update` and `before_delete` on the model, raising immediately.
   Catches the mistake in a unit test with no database, where the developer is still looking at it.

`verity.db.rls.make_append_only` today only revokes. It grows the trigger half in this change, so
`task_transitions`, `vuln_transitions`, `check_results`, `readiness_snapshots`, `kri_measurements`,
and `document_versions` inherit all of it when they arrive.

The trigger function is created idempotently (`CREATE OR REPLACE`) and is shared by every append-only
table.

## Indexes

Every composite index leads with `tenant_id`.

| Index | Columns | Serves |
|---|---|---|
| `ix_audit_log__tenant_id_occurred_at` | `(tenant_id, occurred_at DESC)` | The default list, newest first, and the cursor |
| `ix_audit_log__tenant_id_object_type_object_id` | `(tenant_id, object_type, object_id)` | "What happened to this object" |
| `ix_audit_log__tenant_id_actor_id` | `(tenant_id, actor_id)` | "What did this person do" |

Postgres indexes `NULL`s in B-trees, so provider-plane rows are covered by the same indexes and no
separate partial index is needed.

## The service

```python
class AuditService:
    async def record(
        self,
        session: AsyncSession,          # the caller's session, deliberately
        *,
        action: AuditAction,
        object_type: str,
        object_id: UUID,
        actor: Actor,                   # Membership | PlatformAdmin | System
        tenant_id: UUID | None,
        before: Mapping[str, object] | None,
        after: Mapping[str, object] | None,
    ) -> None: ...

    @staticmethod
    def snapshot(instance: DeclarativeBase, *, fields: Sequence[str] | None = None) -> dict: ...
```

The session is a parameter rather than an injected dependency. That is the whole point: the audit
write has to join the caller's transaction, and a service that opened its own session would produce
exactly the failure mode this table exists to prevent — a committed audit row describing a change
that rolled back.

`snapshot` reads mapped columns and drops any whose name matches the secret deny-list
(`password`, `hash`, `secret`, `token`, `credential`, `key`, `recovery_code`, `_enc`, `_encrypted`),
substituting a redaction marker so the change is still visible as having happened. The deny-list is
the same one `core/logging.py` already uses for log redaction, imported rather than restated, so a
new secret column is covered in both places at once.

## Idempotency — what happens if this runs twice?

Audit rows are insert-only and carry no natural key, so there is nothing to deduplicate on and
nothing that could be overwritten.

Re-running a *unit of work* is safe because the audit write shares its transaction: a retried
transaction that rolled back left no audit row, and a retried transaction that committed is not
retried. A caller that deliberately records the same logical event twice gets two rows, which is
correct — the event happened twice as far as the system is concerned. Deduplicating at this layer
would mean deciding that two identical actions a second apart were really one, which is not a
decision the audit trail is entitled to make.

## Dependencies, timeouts, and failure

The audit trail has one dependency, Postgres, and it is the same connection the change is already
using. There is no external call, no queue, and no timeout of its own — the statement timeout
configured on the engine in `core/db.py` covers it.

If Postgres is slow, the whole unit of work is slow and fails on the existing timeout. If Postgres is
down, the change fails and no audit row is written, which is the correct outcome: the change did not
happen either.

There is deliberately **no** asynchronous or best-effort audit path. Writing the trail through a
queue would decouple it from the transaction and reintroduce "the change committed but the audit row
did not," which is the one failure this table cannot have.

## Reversibility

The migration downgrade drops the trigger, the policies, and the table. It is reversible in the
mechanical sense, and destroys the audit trail in the real one. The docstring says so.
