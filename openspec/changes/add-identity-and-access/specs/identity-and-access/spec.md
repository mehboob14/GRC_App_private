# Identity and access

## ADDED Requirements

### Requirement: A user is a global identity; membership in a tenant is a separate row

A person is one `users` row. Their place in a tenant is one `tenant_memberships` row. Email is unique
globally. A second membership for the same user needs no schema change.

Every in-tenant reference to a person — group member, role assignee, and every owner / approver /
assignee column later modules add — is a foreign key to `tenant_memberships`, never to `users`.

#### Scenario: Self-service trial signup

- **GIVEN** no existing user with the submitted email
- **WHEN** a trial signup is submitted with company profile and the first admin's email and password
- **THEN** a tenant is created in `provisioning` status through the tenancy registration service
- **AND** a user, a credentials row, and one membership are created in the same transaction
- **AND** the membership holds the built-in Admin role
- **AND** the audit trail records the tenant creation and the membership creation in that tenant's
  stream

#### Scenario: The email is already registered

- **WHEN** signup uses an email that already exists
- **THEN** the response is 409
- **AND** no partial tenant, user, or membership is left behind

#### Scenario: A user is added to a second tenant

- **GIVEN** a user with a membership in tenant A
- **WHEN** they are invited into tenant B and accept
- **THEN** a second `tenant_memberships` row is created
- **AND** no column of `users` changes
- **AND** a session in tenant A still cannot see anything belonging to tenant B

#### Scenario: An in-tenant reference points at a user

- **WHEN** any tenant-owned table is defined with a person-reference column
- **THEN** that column is a foreign key to `tenant_memberships.id`
- **AND** a foreign key to `users.id` on a tenant-owned table is a schema defect

### Requirement: Native login verifies a password and, for admins, a TOTP code

Login resolves the user by email, verifies the password against the credentials row, selects the
active membership, and issues a session. For a membership holding the Admin role, a valid TOTP code
is required; without it, only a short-lived challenge is issued.

Password verification takes the same time whether or not the email exists.

**Permission key:** none — unauthenticated / partially-authenticated routes.

**Audit trail written:** `create` on `session` for a completed login, with `actor_type =
'membership'` and `tenant_id` of the active membership. Failed password and failed TOTP attempts are
recorded without issuing a session.

#### Scenario: Correct password, non-admin membership

- **GIVEN** a user with an active non-admin membership in tenant A
- **WHEN** they submit the correct password
- **THEN** a session token is issued bound to that membership
- **AND** the audit trail records the login in tenant A's stream

#### Scenario: Correct password, admin membership, no code

- **GIVEN** a user whose active membership holds the Admin role and has TOTP enrolled
- **WHEN** they submit the correct password alone
- **THEN** no session token is issued
- **AND** the response carries only a short-lived challenge that permits the TOTP step

#### Scenario: Correct password and valid code, admin membership

- **GIVEN** an admin holding a valid challenge
- **WHEN** they submit a valid, unused TOTP code
- **THEN** a session token is issued
- **AND** the audit trail records the login

#### Scenario: The admin has not enrolled

- **GIVEN** an admin membership with no TOTP secret
- **WHEN** they submit the correct password
- **THEN** the response directs them to enrollment
- **AND** no session token is issued until enrollment is confirmed with a valid code

#### Scenario: A user has memberships in two tenants

- **GIVEN** a user with active memberships in tenants A and B
- **WHEN** they log in
- **THEN** the response lists both memberships
- **AND** the session is issued only after they select one
- **AND** switching later is an explicit, audited action, not a request parameter

#### Scenario: The email does not exist

- **WHEN** login is attempted with an unregistered email
- **THEN** the response is 401 and is indistinguishable in content and in timing from a wrong
  password

#### Scenario: The membership is disabled or outside its window

- **GIVEN** a user whose only membership is disabled, or whose role assignment's `valid_until` has
  passed
- **WHEN** they submit correct credentials
- **THEN** the response is 401 and no session is issued

#### Scenario: Secrets never leave the server

- **WHEN** any route returns a user, a membership, or a credentials-related status
- **THEN** the response contains no password hash, no MFA secret, and no recovery code, in neither
  plaintext nor ciphertext

### Requirement: The federation seam exists and is unused

`user_identities` maps a platform user to an external identity by provider name, provider type
(OIDC or SAML), and external subject. No route in this change reads or writes it. Adding an identity
provider later is additive — new rows and a new provider behind the seam — and never a schema
rewrite.

#### Scenario: The table is empty after signup and login

- **GIVEN** a completed trial signup and a completed login
- **WHEN** `user_identities` is queried for that user
- **THEN** no rows exist

#### Scenario: The unique key is provider-scoped

- **WHEN** two rows would share the same `(provider, external_subject_id)`
- **THEN** the database refuses the second insert

### Requirement: Permissions are flat module:action keys; roles are named bundles of them

A permission is a key of the form `module:action`. A role is a named bundle of keys, tenant-scoped,
and may be built-in or custom. Roles are assigned to a membership or to a group. The flat model
does not provide row-level scoping.

**Permission keys used by routes in this change:**

| Route | Key |
|---|---|
| List / invite / disable memberships | `members:read` / `members:invite` / `members:disable` |
| Manage groups | `groups:read` / `groups:manage` |
| Manage roles and assignments | `roles:read` / `roles:manage` |
| Read the caller's own profile and permissions | (authenticated; no key) |

**Object scope:** none of the routes above are object-scoped. Object-scope filtering — control owner
seeing only assigned controls, auditor seeing only their engagement — is a service-layer filter on
top of the flat check, and is exercised in this change only through the hook and its unit tests.
Later modules plug their ownership columns into that hook; this change does not invent those
columns.

**Audit trail written:** `create` / `update` / `delete` on `tenant_membership`, `group`,
`group_member`, `role`, `role_assignment` for every corresponding state change, with before and after
snapshots, in the active tenant's stream.

#### Scenario: A route declares and enforces its permission

- **GIVEN** a member whose roles do not grant `members:invite`
- **WHEN** they call the invite route
- **THEN** the response is 403 with a stable error code

#### Scenario: Permissions are the union of every active assignment

- **GIVEN** a membership holding role R1 directly and belonging to a group that holds role R2
- **WHEN** their effective permissions are resolved
- **THEN** the result is the union of R1's and R2's keys
- **AND** an assignment whose `valid_until` has passed contributes nothing

#### Scenario: A built-in role cannot be deleted

- **GIVEN** a built-in role
- **WHEN** a caller attempts to delete it
- **THEN** the response is 409
- **AND** the role is unchanged

#### Scenario: A custom role is created and assigned

- **GIVEN** a member holding `roles:manage`
- **WHEN** they create a role with a set of permission keys and assign it to a membership
- **THEN** that membership's subsequent requests are authorised for those keys
- **AND** both the role creation and the assignment are in the audit trail

#### Scenario: An auditor assignment is time-boxed and engagement-scoped

- **GIVEN** a role assignment with `engagement_id`, `valid_from`, and `valid_until`
- **WHEN** the current time is outside that window
- **THEN** the assignment contributes no permissions
- **AND** when inside the window, object-scope filtering further restricts the member to that
  engagement's objects — the flat permission alone does not

### Requirement: Groups contain memberships, not users

A group is tenant-scoped. Its members are `tenant_memberships` rows. Adding a global user to a group
directly is impossible at the schema level.

#### Scenario: A membership is added to a group

- **GIVEN** a membership in tenant A and a group in tenant A
- **WHEN** the membership is added to the group
- **THEN** the member inherits the group's role assignments
- **AND** the audit trail records the addition

#### Scenario: A membership from another tenant is added

- **GIVEN** a membership in tenant B and a group in tenant A
- **WHEN** an insert of that pair is attempted
- **THEN** the database refuses the write — either by foreign key, by RLS, or by both

#### Scenario: A user id is supplied where a membership id is required

- **WHEN** any group-member or role-assignment write is attempted with a `users.id`
- **THEN** the write is refused; those columns reference `tenant_memberships.id`

### Requirement: `require(permission)` resolves from the active membership, then applies object scope

The dependency declared on every tenant-plane route loads the active membership from the session,
computes its effective permissions, and rejects the request if the required key is absent. A second
hook accepts an ownership or assignment filter so a caller with the flat permission still only sees
the rows they are scoped to.

#### Scenario: The flat check passes and no object scope applies

- **GIVEN** a membership holding `controls:read` and no ownership filter on the route
- **WHEN** they list controls
- **THEN** every control in their tenant is returned (bounded by RLS, not by ownership)

#### Scenario: The flat check passes and object scope applies

- **GIVEN** a membership holding `controls:read` whose object-scope filter is "owned by me"
- **WHEN** they list controls
- **THEN** only controls they own are returned
- **AND** a control owned by someone else in the same tenant returns 404, not 403, when requested
  by id

#### Scenario: The flat check fails

- **GIVEN** a membership that does not hold `controls:read`
- **WHEN** they list or read controls
- **THEN** the response is 403, regardless of ownership

#### Scenario: The session's tenant does not match the membership

- **GIVEN** a token whose subject is a membership in tenant A
- **WHEN** anything attempts to bind tenant B for that request
- **THEN** the request is rejected; the tenant is taken from the membership and never from the
  client

### Requirement: Cross-tenant access fails at the database, not only in the application

Every tenant-owned table in this change has RLS enabled and forced, with the standard tenant policy,
in the same migration that creates it. A session bound to tenant A cannot read, update, or delete
tenant B's rows, and cannot insert a row carrying tenant B.

#### Scenario: A list in tenant A

- **GIVEN** memberships, groups, roles, and assignments in tenants A and B
- **WHEN** a session bound to A lists any of them
- **THEN** only A's rows are returned

#### Scenario: A direct read of a B row by id

- **GIVEN** the identifier of a membership, group, or role belonging to tenant B
- **WHEN** a session bound to A requests it
- **THEN** the response is 404, not 403

#### Scenario: A write carrying the wrong tenant

- **GIVEN** a session bound to A
- **WHEN** it attempts to insert a group, role, or membership carrying tenant B
- **THEN** the database refuses the write

#### Scenario: A user with memberships in A and B

- **GIVEN** one user with a membership in A and a membership in B
- **WHEN** a session bound to the A membership runs
- **THEN** nothing belonging to B is visible, including the user's own B membership
- **AND** switching to B is a new session, not a parameter on the A session

#### Scenario: Global identity tables are not tenant-filtered by mistake

- **GIVEN** a session bound to tenant A
- **WHEN** authentication looks up a user by email
- **THEN** the lookup succeeds regardless of which tenant the user has memberships in, because
  `users`, `credentials`, and `user_identities` carry no `tenant_id` and are not subject to the
  tenant policy
