# Tenancy — the provider plane

## ADDED Requirements

### Requirement: A platform admin authenticates with a password and a TOTP code, always

Provider-plane access requires two factors. There is no configuration setting, environment variable,
or account flag that reduces it to one. An admin who has not enrolled a TOTP secret can complete
enrollment and nothing else.

Password verification takes the same time whether or not the email exists, so the login route does
not disclose which addresses are registered.

**Permission key:** none — these are the unauthenticated and partially-authenticated routes.

**Audit trail written:** `create` on `session` for a completed login. A failed password attempt, a
failed TOTP attempt, and a completed enrollment are each recorded with `actor_type =
'platform_admin'` and no tenant.

#### Scenario: Correct password and correct code

- **GIVEN** an active platform admin with TOTP enrolled
- **WHEN** they submit the correct password and then a valid code
- **THEN** a session token is issued
- **AND** an audit record is written for the login

#### Scenario: Correct password, no code

- **GIVEN** an active platform admin with TOTP enrolled
- **WHEN** they submit the correct password alone
- **THEN** no session token is issued
- **AND** the response carries only a short-lived challenge that permits the TOTP step and nothing
  else

#### Scenario: Correct password, wrong code

- **GIVEN** a platform admin holding a valid challenge
- **WHEN** they submit an incorrect code
- **THEN** the response is 401, no session token is issued, and the attempt is recorded

#### Scenario: A code is replayed

- **GIVEN** a TOTP code that was already accepted
- **WHEN** it is submitted again within its validity window
- **THEN** it is rejected

#### Scenario: The admin has not enrolled

- **GIVEN** an active platform admin with no TOTP secret
- **WHEN** they submit the correct password
- **THEN** the response directs them to enrollment
- **AND** no session token is issued until enrollment is confirmed with a valid code

#### Scenario: The email does not exist

- **WHEN** a login is attempted with an unregistered email
- **THEN** the response is 401 and is indistinguishable in content and in timing from a wrong
  password

#### Scenario: The admin is not active

- **GIVEN** a platform admin whose status is not active
- **WHEN** they submit correct credentials and a valid code
- **THEN** the response is 401 and no session token is issued

#### Scenario: The stored secret is never disclosed

- **WHEN** any provider route returns a platform admin
- **THEN** the response contains no password hash, no MFA secret, and no recovery code, in neither
  plaintext nor ciphertext

### Requirement: A platform admin registers a tenant, capturing the profile that documents will reuse

Registration creates the tenant with its company profile, sets its status to provisioning, and
creates its provisioning steps. The tenant's slug is unique across the platform.

**Permission key:** `tenants:create`.

**Object scope:** none. Provider-plane authorization resolves from `platform_admins.role`; the
`permissions` and `roles` tables are tenant-scoped and hold no provider-plane grant.

**Audit trail written:** `create` on `tenant`, `tenant_id` = the new tenant, `actor_type =
'platform_admin'`, `before` empty, `after` the profile. One `create` on `tenant_provisioning` per
step.

#### Scenario: A tenant is registered

- **GIVEN** an authenticated platform admin holding `tenants:create`
- **WHEN** they register a tenant with a legal name, a slug, and the contact and address profile
- **THEN** the response is 201 with the tenant
- **AND** its status is `provisioning`
- **AND** its four provisioning steps exist, each `pending`
- **AND** `created_by` names the registering admin
- **AND** the audit trail carries the creation in the new tenant's own stream

#### Scenario: The slug is taken

- **WHEN** registration uses a slug that already exists
- **THEN** the response is 409 with a stable error code
- **AND** no partial tenant, branding, or provisioning row is left behind

#### Scenario: The request is retried

- **GIVEN** a registration that was submitted with an idempotency key
- **WHEN** the identical request is submitted again with the same key
- **THEN** the original tenant is returned
- **AND** no second tenant, and no second set of provisioning steps, is created

#### Scenario: A caller without the permission

- **GIVEN** a platform admin whose role does not grant `tenants:create`
- **WHEN** they attempt to register a tenant
- **THEN** the response is 403

#### Scenario: A tenant user reaches a provider route

- **GIVEN** an authenticated member of a tenant, with any roles
- **WHEN** they call any route under the provider prefix
- **THEN** the response is 403 and no provider-plane data is disclosed

#### Scenario: The status is not a permitted value

- **WHEN** a tenant is written with a status outside provisioning, active, suspended, and terminated
- **THEN** the database refuses the write

### Requirement: A platform admin sets a tenant's branding, and its mail credentials are encrypted

Branding is one record per tenant, created empty at registration and updated thereafter. The tenant's
SMTP credentials are encrypted at the application layer before they reach the database.

**Permission key:** `tenants:brand`.

**Audit trail written:** `update` on `tenant_branding` in that tenant's stream, with before and after
snapshots from which the SMTP credential is excluded.

#### Scenario: Branding is set

- **GIVEN** an authenticated platform admin holding `tenants:brand`
- **WHEN** they set the logo reference, colours, custom domain, sending identity, and footer
- **THEN** the response is 200 and the branding is stored
- **AND** the audit trail records the change with both snapshots

#### Scenario: Mail credentials are supplied

- **WHEN** branding is set with SMTP credentials
- **THEN** what reaches the database is ciphertext
- **AND** the value appears in no log line, no error message, and neither audit snapshot

#### Scenario: Branding is read back

- **WHEN** the branding is read through any route
- **THEN** the SMTP credential is absent from the response

#### Scenario: The tenant does not exist

- **WHEN** branding is set for an unknown tenant
- **THEN** the response is 404

### Requirement: Provisioning is a sequence of recorded steps that is safe to re-run

A tenant has one row per provisioning step. Running provisioning executes the steps that are still
pending and leaves completed steps untouched. When every step is done, the tenant becomes active.

**Permission key:** `tenants:provision` to run, `tenants:read` to inspect.

**Audit trail written:** `transition` on `tenant_provisioning` for each step completed, and
`transition` on `tenant` when the tenant becomes active, both in that tenant's stream.

#### Scenario: Provisioning runs

- **GIVEN** a tenant with pending steps
- **WHEN** provisioning is run
- **THEN** each step it completes is marked done with a completion time
- **AND** each completion is recorded in the audit trail

#### Scenario: Provisioning runs twice

- **GIVEN** a tenant whose steps are already done
- **WHEN** provisioning is run again
- **THEN** no step is repeated, no completion time is overwritten, and no duplicate audit record is
  written

#### Scenario: A step cannot complete yet

- **GIVEN** the `seed_content` step, whose content library does not exist in this phase
- **WHEN** provisioning is run
- **THEN** the step remains pending and the tenant does not become active
- **AND** the response reports which steps remain

#### Scenario: Every step completes

- **GIVEN** a tenant whose last pending step completes
- **WHEN** provisioning finishes
- **THEN** the tenant's status becomes active
- **AND** the transition is in the audit trail

### Requirement: A tenant reads its own profile and branding, and nothing about any other tenant

The tenant plane has read access to its own registration profile and branding. The tenant is resolved
from the session. There is no route, parameter, or filter by which a tenant addresses another tenant.

**Permission key:** `tenant:read`.

**Object scope:** none; the row set is bounded by tenant context, not by ownership.

**Audit trail written:** none. These are reads.

#### Scenario: A tenant reads its profile

- **GIVEN** an authenticated member of tenant A holding `tenant:read`
- **WHEN** they call the tenant profile route
- **THEN** the response is tenant A's profile

#### Scenario: A tenant is not bound

- **GIVEN** a session with no tenant context bound
- **WHEN** the tenant profile route is called
- **THEN** the response is 401 and no profile is returned

#### Scenario: Another tenant's row is reachable at the database level

- **GIVEN** a session bound to tenant A
- **WHEN** it queries the tenants table without a filter
- **THEN** only tenant A's row is returned, because the policy and not the query is what bounds it

#### Scenario: Another tenant's branding is requested by identifier

- **GIVEN** a session bound to tenant A and the identifier of tenant B's branding
- **WHEN** it is requested
- **THEN** the response is 404, not 403

#### Scenario: A tenant attempts to change its own status or plan

- **GIVEN** an authenticated member of tenant A
- **WHEN** they attempt to write status, plan, or slug through any tenant-plane route
- **THEN** the write is refused, because lifecycle is managed from the provider plane

### Requirement: Provider-plane tables are unreachable from a tenant session

Row-level security is enabled on all four provider-plane tables. A tenant-plane session sees its own
tenant's row where that is meaningful and nothing else, and sees no platform admin at all.

#### Scenario: A tenant session reads the platform admins table

- **GIVEN** a session bound to tenant A
- **WHEN** it queries the platform admins table directly
- **THEN** no rows are returned

#### Scenario: A tenant session reads another tenant's provisioning

- **GIVEN** provisioning rows for tenants A and B
- **WHEN** a session bound to tenant A queries them
- **THEN** only tenant A's rows are returned

#### Scenario: A tenant session writes another tenant's branding

- **GIVEN** a session bound to tenant A
- **WHEN** it attempts to insert or update a branding row carrying tenant B
- **THEN** the database refuses the write

#### Scenario: No context of either kind is bound

- **GIVEN** a session with neither tenant context nor provider context bound
- **WHEN** it queries any of the four tables
- **THEN** no rows are returned and no error is raised
