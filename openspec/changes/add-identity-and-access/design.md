# Design — identity and access

## Schema status

The column lists below are **derived**, not copied from a diagram. The ER identity diagrams still
show the pre-ADR-0011 shape (`USERS.tenant_id`, email unique per tenant, `GROUP_MEMBERS.user_id`, no
`TENANT_MEMBERSHIPS`). The derivation sources, in priority order, are:

1. ADR-0011 (accepted) and ADR-0006 (accepted)
2. The ER Design document §3.1 prose (the identity-updated text)
3. `docs/architecture/data-model.md`
4. Column shapes from the stale diagrams, transposed onto the membership model (e.g. the credentials
   columns move from `user_id` to the same columns keyed on the global user)

Every derived column is marked. Approving this design is approving these columns; the ER document is
then updated to match, in the same change.

`created_at` / `updated_at` are on every table per convention and are not repeated.

## Tables — global identity (no `tenant_id`, no tenant RLS)

```
users                                          -- DERIVED (diagram still has tenant_id)
  id          uuid PK, UUIDv7
  email       text NOT NULL UNIQUE             -- unique globally, per ADR-0011
  full_name   text NOT NULL
  status      text NOT NULL  CHECK IN ('active','disabled')
  mfa_enabled bool NOT NULL DEFAULT false      -- from diagram; denormalised convenience flag
```

```
credentials                                    -- name per CLAUDE.md / data-model.md (diagram: USER_CREDENTIALS)
  user_id                   uuid PK, FK -> users.id ON DELETE CASCADE
  password_hash             text NOT NULL      -- argon2id, via core/security.py
  mfa_secret_encrypted      text NULL          -- envelope-encrypted TOTP secret
  recovery_codes_encrypted  jsonb NULL         -- argon2id hashes of single-use codes
  last_login_at             timestamptz NULL
  mfa_enrolled_at           timestamptz NULL   -- DERIVED (reference project; useful for "must enroll")
  last_totp_counter         bigint NULL        -- DERIVED (replay protection; not in any diagram)
```

`last_totp_counter` is the one column with no source in the ER prose. Without it, a TOTP code can be
replayed for up to 30 seconds. It is listed here rather than smuggled in during implementation.
Rejecting it means accepting that replay window; say so at review.

```
user_identities                                -- DERIVED shape; diagram lacks provider_type
  id                   uuid PK, UUIDv7
  user_id              uuid NOT NULL FK -> users.id ON DELETE CASCADE
  provider             text NOT NULL           -- e.g. 'entra', 'okta', 'keycloak'
  provider_type        text NOT NULL           -- CHECK IN ('oidc','saml')  -- required by ADR-0006 / prose
  external_subject_id  text NOT NULL
  UNIQUE (provider, external_subject_id)
  UNIQUE (user_id, provider)                   -- one link per provider per user
```

No route in this change reads or writes `user_identities`. The table exists so Phase 3 is an insert,
not a migration.

## Tables — tenant plane (carry `tenant_id`, RLS on)

```
tenant_memberships                             -- DERIVED; absent from every diagram
  id             uuid PK, UUIDv7
  tenant_id      uuid NOT NULL FK -> tenants.id
  user_id        uuid NOT NULL FK -> users.id
  status         text NOT NULL CHECK IN ('invited','active','disabled')
  invited_at     timestamptz NULL
  accepted_at    timestamptz NULL
  disabled_at    timestamptz NULL
  UNIQUE (tenant_id, user_id)
```

The auditor time-box is **not** on this table. It lives on `role_assignments` (below), matching the
ER diagram and the reference project. ADR-0011's wording that memberships "carry the auditor
time-box columns" is treated as describing the capability, not the column location, and is
clarified in the doc task.

```
groups
  id         uuid PK, UUIDv7
  tenant_id  uuid NOT NULL FK -> tenants.id
  name       text NOT NULL
  UNIQUE (tenant_id, name)
```

```
group_members                                  -- DERIVED: membership_id, not user_id
  id                     uuid PK, UUIDv7
  tenant_id              uuid NOT NULL FK -> tenants.id
  group_id               uuid NOT NULL FK -> groups.id
  tenant_membership_id   uuid NOT NULL FK -> tenant_memberships.id
  UNIQUE (group_id, tenant_membership_id)
```

`tenant_id` is denormalised onto the join so the RLS policy is a direct column comparison, and so a
cross-tenant `(group_in_A, membership_in_B)` pair fails the `WITH CHECK` even before the FKs are
considered. A check constraint that `group.tenant_id = membership.tenant_id` is enforced in the
service; enforcing it in the database would need a composite FK or a trigger, which is more
mechanism than this join warrants.

```
permissions                                    -- global content: no tenant_id
  key     text PK                              -- 'module:action'
  module  text NOT NULL
  action  text NOT NULL
```

Permissions are global content, like frameworks. A tenant does not invent `controls:approve`; it
receives the key set the platform ships. Custom *roles* compose those keys; custom *permissions* are
a platform concern and out of scope.

```
roles
  id         uuid PK, UUIDv7
  tenant_id  uuid NOT NULL FK -> tenants.id
  name       text NOT NULL
  built_in   bool NOT NULL DEFAULT false
  UNIQUE (tenant_id, name)
```

```
role_permissions
  role_id         uuid NOT NULL FK -> roles.id ON DELETE CASCADE
  permission_key  text NOT NULL FK -> permissions.key
  PRIMARY KEY (role_id, permission_key)
```

`role_permissions` carries no `tenant_id`. It is reachable only through `roles`, which is
tenant-scoped and RLS-protected; a direct select on this table without joining through a visible
role returns nothing useful, and writes go through the service. Adding `tenant_id` would denormalise
a fact already on `roles` for no policy gain.

```
role_assignments
  id                     uuid PK, UUIDv7
  tenant_id              uuid NOT NULL FK -> tenants.id
  role_id                uuid NOT NULL FK -> roles.id
  assignee_type          text NOT NULL CHECK IN ('membership','group')
  assignee_id            uuid NOT NULL         -- tenant_memberships.id OR groups.id; no FK (polymorphic)
  engagement_id          uuid NULL             -- NO FK in this migration; added when engagements lands
  valid_from             date NULL
  valid_until            date NULL
  CHECK (valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until)
```

`assignee_id` is polymorphic, same reasoning as `audit_log.actor_id`. The service validates that a
`membership` assignee is a membership in this tenant and a `group` assignee is a group in this
tenant; the RLS policy on this table still bounds every row by `tenant_id`.

## Built-in roles and their keys

Seeded per tenant at creation, `built_in = true`, not deletable.

| Role | Keys |
|---|---|
| Admin | every key the platform ships, including `members:*`, `groups:*`, `roles:*`, `tenant:read`, `audit:read` |
| Compliance Manager | `members:read`, `groups:read`, `roles:read`, `tenant:read`, `audit:read`, plus the compliance / evidence / task keys that land with those modules |
| Control Owner | `tenant:read`, plus the control and evidence keys that land with those modules |
| Employee | `tenant:read`, plus acknowledgement keys that land with documents |
| Auditor | `tenant:read`, `audit:read`, plus read keys across compliance modules; always time-boxed via `role_assignments` |

Keys for modules that do not yet exist are **not** inserted now. The `permissions` table grows as
modules land; Admin's "every key" is resolved at check time as "every key that exists," so a new
module's keys are granted to Admin without a data migration. The other built-ins receive their keys
in the module change that introduces them.

Week 1 therefore ships this permission set for real:

```
tenant:read
members:read   members:invite   members:disable
groups:read    groups:manage
roles:read     roles:manage
audit:read
```

## Row-level security

| Table | Policy |
|---|---|
| `users`, `credentials`, `user_identities`, `permissions` | none — global / identity plane |
| `tenant_memberships`, `groups`, `group_members`, `roles`, `role_assignments` | standard tenant policy on `tenant_id` |
| `role_permissions` | none directly; reachable through `roles` |

Standard tenant policy, same helper as every other tenant-owned table:

```sql
USING  (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
```

`ENABLE` + `FORCE` in the same migration that creates each table.

Identity-plane lookups (login by email) run with **no tenant bound** and **no provider-plane flag
set**. That is safe because those tables have no RLS; it is also the reason a bug that leaves
`app.tenant_id` set from a previous request on a pooled connection would not hide a user — and the
reason the foundation's "context dies on commit" isolation test matters here specifically.

## Indexes

`tenant_id` leads every composite index on tenant-owned tables.

| Index | Columns |
|---|---|
| `uq_users__email` | `(email)` |
| `uq_user_identities__provider_subject` | `(provider, external_subject_id)` |
| `uq_tenant_memberships__tenant_id_user_id` | `(tenant_id, user_id)` |
| `ix_tenant_memberships__tenant_id_status` | `(tenant_id, status)` |
| `uq_groups__tenant_id_name` | `(tenant_id, name)` |
| `uq_group_members__group_id_membership` | `(group_id, tenant_membership_id)` |
| `ix_group_members__tenant_id_membership` | `(tenant_id, tenant_membership_id)` |
| `uq_roles__tenant_id_name` | `(tenant_id, name)` |
| `ix_role_assignments__tenant_id_assignee` | `(tenant_id, assignee_type, assignee_id)` |
| `ix_role_assignments__tenant_id_engagement` | `(tenant_id, engagement_id)` partial, `WHERE engagement_id IS NOT NULL` |

## Authentication flow

Reuses `core/security.py` from `add-provider-plane` unchanged — same argon2id parameters, same TOTP
window, same replay counter, same token shape. The only difference is the subject: a tenant session
names a `tenant_memberships.id`, a provider session names a `platform_admins.id`, and the plane
claim distinguishes them so one cannot be presented to the other.

```
POST /api/v1/auth/signup          -- trial: tenant + user + credentials + membership(Admin)
POST /api/v1/auth/login           -- password -> session OR challenge OR enrollment
POST /api/v1/auth/mfa/verify      -- challenge + TOTP -> session
POST /api/v1/auth/mfa/enroll      -- begin enrollment (authenticated via challenge)
POST /api/v1/auth/mfa/confirm     -- confirm enrollment with a valid code
POST /api/v1/auth/workspaces      -- list memberships for the current user
POST /api/v1/auth/workspaces/switch -- issue a new session for another membership (audited)
```

Self-service signup calls the tenancy registration service (no platform admin, so
`tenants.created_by` is null) and then, in the **same transaction**, creates the user, credentials,
membership, and the Admin role assignment. If any step fails, nothing is committed — including the
tenant. That is stricter than "create the tenant and clean up on failure," and it is what keeps a
partial signup from leaving an orphan company in the register.

## `require(permission)` and the object-scope hook

```python
def require(permission: str, *, scope: ObjectScope | None = None): ...

class ObjectScope(Protocol):
    async def filter(
        self,
        session: AsyncSession,
        membership: TenantMembership,
        query: Select[Any],
    ) -> Select[Any]: ...

    async def allows(
        self,
        session: AsyncSession,
        membership: TenantMembership,
        object_id: UUID,
    ) -> bool: ...
```

Resolution order, always:

1. Authenticate the session token; reject if invalid or expired (401).
2. Load the membership named by the token; reject if missing, disabled, or its tenant does not
   match the bound tenant context (401).
3. Compute effective permissions: union of keys from direct role assignments and from the
   membership's groups' role assignments, excluding any assignment outside its
   `valid_from`/`valid_until` window.
4. Flat check: required key present? If not, 403.
5. Object scope, if the route declared one: apply `filter` to list queries; apply `allows` to
   by-id reads and writes. Denial is **404**, not 403 — a 403 would confirm the object exists.

The flat model stops at step 4. Steps 5 exists so implementers cannot assume the flat model gave
them row scoping — which is the failure mode the ER prose and `openspec/config.yaml` both warn
about.

Week 1 ships one concrete scope used by the auditor path:

```python
class EngagementScope:
    """Restricts to objects linked to the caller's active engagement_id assignments."""
```

Control-owner scope lands with the compliance module, against `controls.owner_id` →
`tenant_memberships.id`.

## Idempotency — what happens if this runs twice?

**Signup** accepts an `Idempotency-Key` and is additionally protected by `users.email` uniqueness
and `tenants.slug` uniqueness. A retry with the same key returns the original result; a retry with
the same email and no key is a 409 with no partial rows.

**Invite** is idempotent on `(tenant_id, user_id)`: inviting an existing active membership is a
no-op returning the existing row; inviting a disabled membership is a reactivation that is audited
as an update, not a create.

**Role assignment** is idempotent on `(role_id, assignee_type, assignee_id, engagement_id)`: a
duplicate insert is a 409 rather than a second row that would double-count in the union.

**Login** is not idempotent and should not be — two successful logins are two sessions, and each is
an audit event.

## Dependencies, timeouts, and failure

Postgres only. Password hashing cost and rate-limit posture are as stated in
`add-provider-plane/design.md`. Mail delivery for invites and password reset is out of scope; the
tokens are issued and stored, delivery is a notifications-module concern that must not hold this
transaction open when it arrives.

## Reversibility

The migration is reversible. The downgrade drops every identity and access table, which destroys
every user, membership, and role on the deployment. The docstring says so.
