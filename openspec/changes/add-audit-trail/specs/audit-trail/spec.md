# Audit trail

## ADDED Requirements

### Requirement: Every state-changing action is recorded with its actor and its before/after state

The system records a row in the audit trail for every action that changes persisted state. The row
carries who acted, when, which object changed, and the state of that object before and after the
change.

An actor is one of three kinds, and the row says which: a **membership** (a person acting inside a
tenant), a **platform admin** (an operator acting on the provider plane), or the **system** (a
scheduled job or an internal process, which has no actor identifier).

#### Scenario: A tenant user changes an object

- **GIVEN** an authenticated member of tenant A
- **WHEN** they perform an action that changes persisted state
- **THEN** an audit record is written with `tenant_id` = A, `actor_type` = `membership`, and
  `actor_id` = that person's membership id
- **AND** the record carries the object's type, its identifier, the state before, and the state after

#### Scenario: A platform admin acts on a tenant

- **GIVEN** an authenticated platform admin
- **WHEN** they perform an action that changes state belonging to tenant X
- **THEN** an audit record is written with `tenant_id` = X, because the event belongs to X's history
- **AND** `actor_type` = `platform_admin` and `actor_id` = the platform admin's id

#### Scenario: A platform admin acts on the provider plane itself

- **GIVEN** an authenticated platform admin
- **WHEN** they perform an action that belongs to no tenant
- **THEN** an audit record is written with `tenant_id` empty
- **AND** `actor_type` = `platform_admin`

#### Scenario: A scheduled job changes state

- **GIVEN** a background job running with no authenticated person
- **WHEN** it performs an action that changes persisted state
- **THEN** an audit record is written with `actor_type` = `system` and no actor identifier

### Requirement: The audit record and the change it describes succeed or fail together

The audit record is written on the same session and inside the same transaction as the change it
describes. There is no path that commits a change without its audit record, and no path that leaves
an audit record describing a change that did not happen.

#### Scenario: The change is rolled back

- **GIVEN** a unit of work that changes an object and records the change
- **WHEN** the unit of work raises before committing
- **THEN** neither the change nor the audit record is persisted

#### Scenario: The audit write fails

- **GIVEN** a unit of work that changes an object
- **WHEN** writing the audit record fails
- **THEN** the whole unit of work fails and the change is not persisted

#### Scenario: The unit of work runs twice

- **GIVEN** a unit of work that was retried after its transaction rolled back
- **WHEN** it runs again and commits
- **THEN** exactly one audit record exists for the committed change

### Requirement: The audit trail is insert-only

No audit record is ever updated or deleted, by anybody, through any path. The database refuses both
operations rather than relying on the application not to attempt them.

#### Scenario: An update is attempted by the application role

- **GIVEN** an existing audit record
- **WHEN** the application role attempts to update any column of it
- **THEN** the database refuses the statement
- **AND** the record is unchanged

#### Scenario: A delete is attempted by the application role

- **GIVEN** an existing audit record
- **WHEN** the application role attempts to delete it
- **THEN** the database refuses the statement

#### Scenario: An update is attempted by the owning role

- **GIVEN** an existing audit record
- **WHEN** the role that owns the table — the role migrations run as — attempts to update or delete it
- **THEN** the database refuses the statement, because a revoked grant does not bind a table's owner

#### Scenario: The application attempts a mutation through the ORM

- **GIVEN** an audit record loaded into a session
- **WHEN** application code modifies it and flushes
- **THEN** the operation fails and the failure names the append-only rule

### Requirement: Audit records are visible only within the tenant stream they belong to

A tenant-plane session reads audit records belonging to its own tenant and no others. Records
belonging to no tenant are provider-plane records and are invisible to every tenant-plane session.

#### Scenario: A tenant reads its own trail

- **GIVEN** audit records exist for tenant A and for tenant B
- **WHEN** a session bound to tenant A lists the audit trail
- **THEN** only tenant A's records are returned

#### Scenario: A tenant asks for another tenant's record directly

- **GIVEN** an audit record belonging to tenant B, and its identifier
- **WHEN** a session bound to tenant A requests that record by identifier
- **THEN** the response is 404, not 403

#### Scenario: Provider-plane records are requested from inside a tenant

- **GIVEN** audit records with no tenant
- **WHEN** a session bound to any tenant lists or counts the audit trail
- **THEN** none of those records are returned, and none are counted

#### Scenario: No tenant is bound

- **GIVEN** a session that has not bound a tenant and is not a provider-plane session
- **WHEN** it queries the audit trail
- **THEN** no records are returned and no error is raised

#### Scenario: A record is written for the wrong tenant

- **GIVEN** a session bound to tenant A
- **WHEN** it attempts to insert an audit record carrying tenant B
- **THEN** the database refuses the write

### Requirement: Secrets never enter the audit trail

The before and after snapshots exclude every secret-bearing column. A password hash, an encrypted
MFA secret, a recovery code, a portal token, and a connector credential are absent from the audit
trail whether or not the column that holds them changed.

#### Scenario: A credential record changes

- **GIVEN** a change to an object holding a password hash and an encrypted MFA secret
- **WHEN** the change is recorded
- **THEN** the before and after snapshots contain neither value, in neither plaintext nor ciphertext
- **AND** the snapshots still record that those fields changed, so the event is not silent

#### Scenario: A new secret-bearing column is added later

- **GIVEN** a column whose name matches the secret deny-list
- **WHEN** a snapshot is taken of a row containing it
- **THEN** the column is excluded without any change to the calling service

### Requirement: The audit trail is readable through one permission-gated route

`GET /api/v1/audit-log` returns the calling tenant's audit records, newest first, cursor-paginated.

**Permission key:** `audit:read`.

**Object scope:** none in this change. The flat permission grants the whole tenant's trail. Row-level
scoping — a time-boxed auditor seeing only their engagement's window — is an object-scope filter that
lands with the engagement, in the compliance module; the flat permission key does not provide it and
must not be assumed to.

**Audit trail written:** none. Reading the audit trail is not a state change.

#### Scenario: A permitted caller lists the trail

- **GIVEN** a member of tenant A whose roles grant `audit:read`
- **WHEN** they call `GET /api/v1/audit-log`
- **THEN** the response is 200 and contains tenant A's records, newest first, with a cursor

#### Scenario: A caller without the permission

- **GIVEN** a member of tenant A whose roles do not grant `audit:read`
- **WHEN** they call `GET /api/v1/audit-log`
- **THEN** the response is 403 with a stable error code and a correlation id

#### Scenario: An unauthenticated caller

- **GIVEN** no session
- **WHEN** `GET /api/v1/audit-log` is called
- **THEN** the response is 401

#### Scenario: The caller supplies a tenant

- **GIVEN** an authenticated member of tenant A
- **WHEN** they call `GET /api/v1/audit-log?tenant_id=<tenant B>`
- **THEN** the parameter is rejected as unknown and the response contains only tenant A's records,
  because the tenant is resolved from the session and never from the request
