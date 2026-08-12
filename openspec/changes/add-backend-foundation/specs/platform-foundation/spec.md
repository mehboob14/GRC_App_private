# Platform foundation

## ADDED Requirements

### Requirement: Configuration is read from the environment once

The backend reads all deployment configuration from environment variables into a single validated
settings object, constructed once per process. Nothing in the codebase reads `os.environ` for
configuration.

Secret-bearing settings are held in a type that does not render its value when printed, logged, or
included in a traceback.

#### Scenario: Required settings are absent

- **GIVEN** `DATABASE_URL` is not set in the environment
- **WHEN** the settings object is constructed
- **THEN** construction fails with a message naming the missing variable
- **AND** the process does not start

#### Scenario: A secret is rendered

- **GIVEN** a settings object holding a secret
- **WHEN** it is formatted into a string or a log line
- **THEN** the secret's value does not appear in the output

#### Scenario: A development default reaches production

- **GIVEN** `ENV` is `production`
- **AND** `SECRET_KEY` or `APP_ENCRYPTION_KEY` still holds its development default
- **WHEN** the settings object is constructed
- **THEN** construction fails
- **AND** the message names the variable that must be set

#### Scenario: The database URL uses a blocking driver

- **GIVEN** `DATABASE_URL` names a synchronous driver such as `postgresql+psycopg`
- **WHEN** the settings object is constructed
- **THEN** construction fails, because a blocking driver on the event loop is a defect that would
  otherwise surface only under load

### Requirement: Tenant context is bound to a transaction, never to a connection

The system provides one primitive for binding the current tenant, and every tenant-scoped unit of
work goes through it. The bound value is transaction-local, so it cannot outlive its transaction and
cannot be observed by the next user of a pooled connection.

The tenant identifier is passed to the database as a bound parameter. It is never interpolated into
SQL text.

#### Scenario: Tenant context is bound and read back

- **GIVEN** an open transaction on a session
- **WHEN** tenant context is bound to a tenant id
- **THEN** reading the tenant setting inside that transaction returns that id

#### Scenario: The transaction ends

- **GIVEN** tenant context was bound inside a transaction
- **WHEN** that transaction commits or rolls back
- **THEN** the tenant setting is empty for any subsequent transaction on the same connection

#### Scenario: A pooled connection is reused

- **GIVEN** a unit of work bound tenant A and returned its connection to the pool
- **WHEN** a later unit of work acquires a connection from that pool and reads the tenant setting
  without binding it
- **THEN** the setting is empty

#### Scenario: Binding is attempted with no transaction open

- **GIVEN** a session with no transaction in progress
- **WHEN** tenant context binding is attempted
- **THEN** it fails with an error naming the missing transaction, rather than silently binding a
  value that would be discarded

#### Scenario: Tenant-scoped work runs with no tenant bound

- **GIVEN** a tenant-scoped table with its RLS policy applied
- **WHEN** it is queried with no tenant bound
- **THEN** no rows are returned and no error is raised, because the policy fails closed

### Requirement: The application connects with a role that cannot bypass RLS

The role the application and the workers authenticate as is not a superuser, does not hold
`BYPASSRLS`, and does not own the tables it reads. Migrations run as a separate role. Tests connect
as the application role.

#### Scenario: The application role is inspected

- **GIVEN** a connection opened with the application's own credentials
- **WHEN** the role's attributes are read from the catalog
- **THEN** `rolsuper` is false and `rolbypassrls` is false

#### Scenario: A test fixture connects

- **GIVEN** the integration or isolation test suite
- **WHEN** it opens a database connection
- **THEN** it connects as the application role
- **AND** no fixture disables row-level security or elevates to a bypassing role

### Requirement: Migrations that create a tenant-owned table enable RLS in the same migration

The system provides migration helpers that enable row-level security, force it for the table owner,
and add the tenant policy for a named table, so that doing it correctly is one call and forgetting it
is visible in review. A separate helper revokes `UPDATE` and `DELETE` for append-only tables.

#### Scenario: A tenant table is created

- **GIVEN** a migration that creates a tenant-owned table
- **WHEN** it calls the RLS helper for that table
- **THEN** row-level security is enabled and forced on the table
- **AND** a policy restricting every command to the bound tenant is created

#### Scenario: An append-only table is created

- **GIVEN** a migration that creates an append-only table
- **WHEN** it calls the append-only helper for that table
- **THEN** `UPDATE` and `DELETE` are revoked from the application role
- **AND** an attempted update by the application role is refused by the database, not by convention

### Requirement: Every table declaration inherits the mandated columns

The system provides the declarative base and mixins that give a table its UUIDv7 primary key, its
`created_at` and `updated_at` timestamps in UTC, its `tenant_id`, and its `source` / `external_id` /
`synced_at` integration columns, so that a module cannot get them subtly different.

Primary keys are UUID version 7. Index and constraint names follow the documented convention. A
helper builds composite indexes with `tenant_id` as the leading column and refuses to build one
without it.

#### Scenario: An identifier is generated

- **WHEN** a primary key is generated
- **THEN** its version field is 7 and its variant field is RFC 9562 compliant
- **AND** two identifiers generated in sequence sort in generation order

#### Scenario: A composite index is declared for a tenant table

- **WHEN** the tenant index helper is called with one or more columns
- **THEN** the resulting index lists `tenant_id` first
- **AND** its name follows `ix_<table>__<cols>`

#### Scenario: A status column is declared

- **WHEN** a status column's allowed values are declared
- **THEN** a `CHECK` constraint is produced rather than a database enum type

### Requirement: Errors return a stable code and a correlation id, never internals

Every error response the API produces uses one envelope containing a stable machine-readable `code`,
a message safe to show a user, and a `correlation_id`. The detail needed to diagnose the failure is
written to the log against that same correlation id.

A resource belonging to another tenant is reported as absent, not as forbidden.

#### Scenario: A domain error is raised

- **GIVEN** a service raises a domain exception
- **WHEN** the response is produced
- **THEN** the body is `{"error": {"code", "message", "correlation_id"}}`
- **AND** the status code is the one the exception declares

#### Scenario: An unexpected exception escapes

- **GIVEN** a request handler raises an exception that is not a domain exception
- **WHEN** the response is produced
- **THEN** the status is 500 and the code is a generic internal-error code
- **AND** the body contains no exception type, no message from the exception, no stack trace, and no
  SQL
- **AND** the full exception is logged with the correlation id that the response returned

#### Scenario: A request carries a correlation id

- **GIVEN** a request arriving with a correlation id header
- **WHEN** any response is produced
- **THEN** that id is echoed in the response header and used in any error body and log line

#### Scenario: A resource in another tenant is requested

- **WHEN** a resource belonging to a different tenant is requested by id
- **THEN** the response is 404, never 403

### Requirement: Logs never contain secrets

Log output is structured. Any event field whose key names a credential, token, secret, password, key,
or MFA seed is replaced with a redaction marker before the event is rendered, at any depth of nesting.

#### Scenario: A secret is passed to a log call

- **WHEN** an event is logged with a field named `password`, `token`, `api_key`, `secret`,
  `authorization`, `credential`, or `mfa_secret`
- **THEN** the rendered line contains a redaction marker in place of the value
- **AND** the value does not appear anywhere in the line

#### Scenario: A secret is nested

- **WHEN** a logged field is a mapping or a list containing a secret-named key at any depth
- **THEN** that value is redacted too

### Requirement: Secrets are encrypted before they reach the database

The system provides envelope encryption for values that must be stored but never read by the
database: a per-value data key encrypts the value, and the application master key encrypts the data
key. Ciphertext records which master key encrypted it, so a master key can be rotated without
re-encrypting existing rows.

Ciphertext is bound to a caller-supplied context, so a ciphertext moved to a different row or a
different tenant fails to decrypt rather than decrypting into the wrong place.

#### Scenario: A value round-trips

- **WHEN** a value is encrypted and then decrypted with the same context
- **THEN** the original value is returned

#### Scenario: Ciphertext is modified

- **WHEN** any byte of a ciphertext is altered and decryption is attempted
- **THEN** decryption fails and no plaintext is returned

#### Scenario: Ciphertext is moved

- **GIVEN** a ciphertext encrypted under one context
- **WHEN** decryption is attempted under a different context
- **THEN** decryption fails

#### Scenario: The master key is rotated

- **GIVEN** a value encrypted under the previous master key
- **AND** a new active master key with the previous key retained for decryption
- **WHEN** the value is decrypted
- **THEN** it decrypts successfully
- **AND** newly encrypted values record the new key's id

#### Scenario: The encryption helper is logged or repr'd

- **WHEN** the encryption helper is formatted into a string
- **THEN** no key material appears

### Requirement: The service reports liveness and readiness separately

The service exposes an endpoint that reports whether the process is running, and a separate endpoint
that reports whether its dependencies are usable. A dependency failure makes the service unready
without making it dead, so an orchestrator restarts a hung process but waits out a slow database.

#### Scenario: The process is running

- **WHEN** the liveness endpoint is requested
- **THEN** it returns 200 without contacting any dependency

#### Scenario: Dependencies are reachable

- **WHEN** the readiness endpoint is requested and the database and Redis both answer
- **THEN** it returns 200 and names each dependency as reachable

#### Scenario: A dependency is unreachable

- **WHEN** the readiness endpoint is requested and the database does not answer within its timeout
- **THEN** it returns 503 naming which dependency failed
- **AND** the response contains no connection string, host, credential, or driver error text

### Requirement: Background jobs bind tenant context per unit of work

A Celery worker or scheduled job that touches tenant data binds tenant context inside the
transaction for each unit of work. A job that iterates tenants binds it once per tenant, not once per
job.

#### Scenario: A scheduled job processes several tenants

- **WHEN** a job iterates tenants
- **THEN** each tenant's work runs in its own transaction with that tenant bound
- **AND** no tenant's work observes another tenant's rows

#### Scenario: A worker starts

- **WHEN** a Celery worker starts against the configured broker
- **THEN** it registers its tasks and reports ready
- **AND** the scheduler has at least one entry

### Requirement: Module boundaries are enforced by the build

The layering in `backend/CLAUDE.md` is checked mechanically, not by review alone. A router may reach
a service, a service a repository, a repository the models. No module imports another module's
repository or models.

#### Scenario: A router imports a repository directly

- **WHEN** a module's `router.py` imports its own `repository.py`, skipping the service
- **THEN** the boundary check fails the build

#### Scenario: A module reaches into another module's data

- **WHEN** any module imports another module's `repository.py` or `models.py`
- **THEN** the boundary check fails the build

#### Scenario: A module calls another module's service

- **WHEN** a module imports another module's `service.py`
- **THEN** the boundary check passes

### Requirement: The foundation is verifiable from documented commands

A developer with a clean checkout brings the stack up, applies migrations, and runs the checks and
tests from documented commands. Continuous integration runs the same checks, including the isolation
suite, on every change.

#### Scenario: A clean checkout is set up

- **WHEN** the documented setup, up, and migrate commands are run in order
- **THEN** dependencies install, Postgres, Redis, and object storage start, and migrations apply
  without error

#### Scenario: The checks are run

- **WHEN** the documented check command is run
- **THEN** formatting, linting, type checking, and the module boundary contracts all pass

#### Scenario: Continuous integration runs without a database

- **GIVEN** the integration and isolation suites require Postgres
- **WHEN** they run in continuous integration
- **THEN** an unreachable database fails the build rather than skipping the suite
