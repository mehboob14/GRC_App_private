# Compliance

> **This spec is written against `openspec/changes/week2-decisions.md` D1-D10, which are PROPOSED
> and have not been confirmed by the client.** It is not yet the agreed contract. Where a
> requirement or scenario below depends on an unconfirmed decision it is tagged with that decision
> — **(D1)**, **(D4)**, **(D7a)** and so on — and it changes if the decision is overridden. The
> decisions most load-bearing here are **D1** (Type derived from the library's 11 categories,
> Sub-type left empty), **D4** (exactly one active engagement per tenant), **D7a** (instantiation
> upserts on canonical key), **D7b** (framework versions with never-re-minted requirement ids, and
> engagements pinned to a version), **D7c** (`coverage` / `weight` / `review_status` on the
> crosswalk, shipped mappings seeded as `accepted`), **D8** (person references are
> `tenant_memberships` foreign keys, contradicting the ER diagrams), **D9** (the five permission
> keys) and **D10** (which tables are global content and which are tenant-owned). An untagged
> requirement rests on the signed requirements document, not on a proposal.

## ADDED Requirements

### Requirement: Framework content is global, versioned, and read-only to every tenant (D7b, D10)

Frameworks, their versions, their requirements, the prebuilt control template library, and the
shipped crosswalk between them carry no `tenant_id` and no row-level security **(D10)**. Every
tenant reads the same content. No tenant can write it: the application role holds `SELECT` and
nothing else, and content is loaded by the migration running as the schema owner.

A requirement's identity is minted once per framework and code and is **never re-minted** **(D7b)**.
A content correction mutates that row. A new framework version is a new set of version-to-requirement
links, never a new set of requirements, so no mapping anywhere can be orphaned by a content update.
Framework versioning itself exists only because D7b was adopted; without it there is no version to
pin and no stable requirement identity.

**Permission key:** `frameworks:read` **(D9)**.

**Object scope:** none — global content is not tenant-scoped.

**Audit trail written:** none. No route in this change writes global content.

#### Scenario: The SOC 2 pack is present after migration

- **WHEN** the platform has migrated to head
- **THEN** exactly one framework `SOC2` exists with one current version
- **AND** it has 61 requirements across 13 categories, 33 of them marked always in scope
- **AND** 114 control templates exist across 11 categories
- **AND** 150 template-to-requirement crosswalk rows exist
- **AND** no requirement is left with zero mapped templates

#### Scenario: A tenant reads global content

- **GIVEN** a session bound to tenant A
- **WHEN** the frameworks and requirements are listed
- **THEN** every framework and every requirement is returned
- **AND** the result does not depend on which tenant is bound

#### Scenario: A tenant attempts to write global content

- **GIVEN** a session bound to any tenant
- **WHEN** an insert, update, or delete is attempted against `frameworks`, `framework_versions`,
  `requirements`, `framework_version_requirements`, `control_templates`, or
  `template_requirement_map`
- **THEN** the database refuses it for lack of privilege
- **AND** no route exists that would attempt it

#### Scenario: A content correction does not orphan a mapping (D7b)

- **GIVEN** a requirement mapped by a tenant's crosswalk
- **WHEN** the platform corrects that requirement's wording
- **THEN** the same requirement row is updated
- **AND** every mapping that pointed at it still points at it

#### Scenario: A new framework version does not move a tenant's denominator (D7b)

- **GIVEN** an engagement pinned to framework version v1
- **WHEN** version v1.1 is published with an additional requirement
- **THEN** the pinned engagement's in-scope requirement set is unchanged
- **AND** the new requirement appears only for an engagement pinned to v1.1

### Requirement: A tenant's control library is instantiated from the templates by canonical identity (D7a)

Creating a tenant, or enabling a framework version for an existing tenant, materialises the
template library into that tenant's own controls and projects the shipped crosswalk into the
tenant's own crosswalk. The tenant then owns a private, editable copy; the global tables stay
pristine.

Instantiation is an **upsert on canonical identity**, not a copy **(D7a)**. A template whose
canonical key already exists as a control in that tenant reuses that control and adds only the new
requirement edges. It never mints a second control for the same concept, and it never overwrites a
field the tenant owns. If D7a is overridden, instantiation becomes a plain copy keyed on
`template_id` and every reuse scenario below is void.

**Permission key:** none for the provisioning path (system-run); `controls:manage` **(D9)** for an
explicit enable-framework call.

**Object scope:** none.

**Audit trail written:** `create` on `control` and on `control_requirement_map` for every row
created, in the tenant's own stream, in the same transaction as the inserts.

#### Scenario: A new tenant is provisioned

- **GIVEN** a newly registered tenant
- **WHEN** provisioning runs its content-seeding step
- **THEN** 114 controls exist in that tenant, each carrying its template as provenance and its
  canonical key as identity **(D7a)**
- **AND** 150 crosswalk rows exist in that tenant's own crosswalk
- **AND** every control's status is `not_started` and its owner is unset
- **AND** the provisioning step reports the real count rather than completing as a no-op

#### Scenario: Instantiation runs twice (D7a)

- **GIVEN** a tenant whose library is already instantiated
- **WHEN** instantiation runs again for the same framework version
- **THEN** no control and no crosswalk row is created
- **AND** the result reports every control as reused

#### Scenario: A second framework reuses controls instead of duplicating them (D7a)

- **GIVEN** a tenant instantiated from SOC 2, with an owner and a status set on a control
- **WHEN** a second framework whose templates share canonical keys with that library is enabled
- **THEN** no second control is created for any shared concept
- **AND** only new crosswalk rows are created, linking the existing controls to the new
  framework's requirements
- **AND** the existing control's owner, status, implementation guidance, and disabled state are
  unchanged

#### Scenario: A custom control participates in reuse (D7a)

- **GIVEN** a hand-authored control with no template and a canonical key set
- **WHEN** a framework is enabled whose template carries that same canonical key
- **THEN** the existing custom control is reused and mapped
- **AND** no control is created from that template

#### Scenario: Instantiation fails part way

- **GIVEN** an instantiation that raises after creating some controls
- **WHEN** the transaction rolls back
- **THEN** no control, no crosswalk row, and no audit row survives
- **AND** the provisioning step remains pending and is safe to retry

#### Scenario: Two tenants are independent after instantiation

- **GIVEN** tenants A and B both instantiated from the same framework version
- **WHEN** A renames a control, assigns an owner, and sets a status
- **THEN** B's corresponding control is unchanged
- **AND** neither tenant can see the other's controls or crosswalk rows

### Requirement: A control carries Type, Sub-type, owner, status, implementation guidance, and its mapped criteria (D1, D8)

Every control in a tenant's library is one row carrying a unique code, a title, a description, a
Type, an optional Sub-type, an owner, a status, implementation guidance inherited from its template
and editable per tenant, and its mapped framework criteria through the tenant's own crosswalk.

**(D1)** Type is derived from the 11 categories the shipped library already carries, and Sub-type
ships **empty on all 114 rows** because no client vocabulary exists for it. If the client supplies
either vocabulary, the permitted values and the seeded Type of every shipped control change; the
column, the filter, and the API do not.

**(D8)** The owner is a foreign key to `tenant_memberships`, never to `users` — a control cannot be
assigned to somebody who is not a member of the tenant that owns it. This contradicts the ER
diagrams, which show `owner_id` against `users`, and follows `CLAUDE.md` rule 9 instead.

One control satisfying criteria in several frameworks is one control row and several crosswalk
rows. That is the property that makes evidence collected once count everywhere in Week 3.

**Permission keys (D9):** `controls:read` to list and read; `controls:manage` to create, edit, and
map.

**Object scope:** `ControlOwnerScope` on `owner_membership_id`. A caller whose compliance access
comes only from the Control Owner role sees only the controls they own; another owner's control
returns **404**, not 403, when requested by id. A caller holding `controls:read` without an
ownership scope sees every control in the tenant, bounded by RLS rather than by ownership.

**Audit trail written:** `create` and `update` on `control` and `control_requirement_map`, with
before and after snapshots, in the tenant's stream.

#### Scenario: The library is filtered by Type and Sub-type (D1)

- **GIVEN** an instantiated library
- **WHEN** the caller filters by Type
- **THEN** only controls of that Type are returned, the Type values being the library's 11
  categories **(D1)**
- **AND** filtering by Sub-type is accepted and returns nothing while no control carries one
  **(D1 — Sub-type ships empty pending a client vocabulary)**

#### Scenario: A control's mapped criteria are visible from the control (D7c)

- **GIVEN** a control mapped to more than one requirement
- **WHEN** the control is read by id
- **THEN** every mapped criterion is returned with its code, its framework, its coverage, and its
  weight **(D7c — `coverage` and `weight` exist only because D7c was adopted)**

#### Scenario: A control is assigned an owner

- **GIVEN** an active membership in the same tenant
- **WHEN** that membership is set as the control's owner
- **THEN** the assignment succeeds and is audited with before and after snapshots

#### Scenario: A control is assigned an owner from another tenant

- **GIVEN** a membership belonging to a different tenant
- **WHEN** it is set as the control's owner
- **THEN** the write is refused
- **AND** the response does not reveal that the membership exists

#### Scenario: A user id is supplied where a membership id is required (D8)

- **WHEN** an owner is set using a `users.id`
- **THEN** the request is rejected at validation
- **AND** the column references `tenant_memberships.id`, so no such row could be written

#### Scenario: A control owner sees only their own controls

- **GIVEN** a member whose compliance access comes only from the Control Owner role
- **WHEN** they list controls
- **THEN** only controls they own are returned
- **AND** requesting another owner's control by id returns 404

#### Scenario: A member without the key is refused

- **GIVEN** a member holding no compliance permission
- **WHEN** they list or read controls
- **THEN** the response is 403 with a stable error code, regardless of ownership

### Requirement: A control is added, edited, or disabled with a justification — never deleted

A tenant can add a custom control, edit any control including a shipped one, edit its crosswalk,
and disable a control with a recorded justification. A control is never hard-deleted: there is no
delete route, and the database refuses to remove a control that any crosswalk row references.

A disabled control is excluded from coverage, but the crosswalk row survives so the coverage view
can say which control was covering the criterion before it was disabled.

**Permission key:** `controls:manage`.

**Object scope:** `ControlOwnerScope`, as above.

**Audit trail written:** `create` on `control` for a custom control; `update` on `control` for an
edit, a disable, or an enable, with before and after snapshots including the justification.

#### Scenario: A custom control is added

- **GIVEN** a member holding `controls:manage`
- **WHEN** they create a control with a code, name, Type, and no template
- **THEN** the control is created with no template provenance
- **AND** it may carry a canonical key so a later framework reuses it **(D7a)**
- **AND** the creation is audited

#### Scenario: A custom control reuses an existing code

- **WHEN** a control is created with a code another control in the tenant already holds
- **THEN** the response is 409
- **AND** no second row is created

#### Scenario: A shipped control is edited

- **GIVEN** a control instantiated from a template
- **WHEN** its name, description, or implementation guidance is edited
- **THEN** the edit succeeds and is audited
- **AND** the global template is unchanged

#### Scenario: A control is disabled

- **GIVEN** a control
- **WHEN** it is disabled with a justification
- **THEN** the control is marked disabled, with the justification, the time, and the acting
  membership recorded
- **AND** the change is audited with before and after snapshots

#### Scenario: A control is disabled without a justification

- **WHEN** a disable is attempted with no justification
- **THEN** the request is rejected
- **AND** the database constraint would refuse the row even if validation were bypassed

#### Scenario: A disabled control is disabled again

- **WHEN** an already-disabled control is disabled a second time
- **THEN** the response returns the existing row unchanged
- **AND** no second audit row is written and the original justification is not overwritten

#### Scenario: A control cannot be deleted

- **WHEN** a delete of a control is attempted by any route or any direct statement
- **THEN** no route exists to perform it
- **AND** the database refuses the statement while any crosswalk row references the control

#### Scenario: The tenant edits its own crosswalk (D7c)

- **GIVEN** a control mapped to a requirement by the shipped crosswalk
- **WHEN** the tenant removes that mapping and adds a different one
- **THEN** the tenant's crosswalk changes and the shipped crosswalk does not
- **AND** the hand-added mapping records the acting membership as its reviewer **(D7c, D8 — the
  review lifecycle and the membership reference both rest on unconfirmed decisions)**
- **AND** both changes are audited

### Requirement: An engagement pins the audit type, the observation window, the framework version, and the categories in scope (D4, D7b)

An engagement records what audit the tenant is preparing for: Type I or Type II, an observation
window, one or more framework versions, and which categories of each are in scope. **(D4)** A
tenant has at most one **active** engagement at a time; drafts and closed engagements are
unlimited. The requirements document never says whether a second concurrent engagement is legal;
if D4 is overridden the partial unique index is dropped and the one-active scenario below is void.

**(D7b)** Pinning a framework **version** is what makes a historical number defensible: readiness
always computes against the version the engagement named, so publishing new content cannot move a
tenant's score mid-audit. Version pinning exists only because D7b was adopted; without it an
engagement names a framework and the denominator moves with the content.

Security's common criteria are always in scope and cannot be removed. Availability,
Confidentiality, Processing Integrity, and Privacy are opt-in per engagement.

**Permission keys (D9):** `engagements:read`, `engagements:manage`.

**Object scope:** none in this change. Time-boxed auditor scoping rides `role_assignments`
(`engagement_id`, `valid_from`, `valid_until`), whose foreign key to `engagements` is added here.

**Audit trail written:** `create` / `update` / `delete` on `engagement`,
`engagement_framework`, and `engagement_scope_category`, with before and after snapshots.

#### Scenario: A Type II engagement is created

- **WHEN** an engagement is created as Type II with a start and end date
- **THEN** it is created in `draft` status with that observation window
- **AND** a start date after the end date is refused

#### Scenario: A Type I engagement is created

- **WHEN** an engagement is created as Type I with an as-of date
- **THEN** the observation window start and end are both that date
- **AND** a Type I engagement with a differing start and end is refused

#### Scenario: A framework version is added to an engagement (D7b)

- **WHEN** a framework version is added
- **THEN** the engagement is pinned to that version
- **AND** every category containing an always-in-scope requirement is added automatically

#### Scenario: An always-in-scope category is removed

- **WHEN** a caller attempts to remove Security's common criteria from scope
- **THEN** the request is refused with a typed error
- **AND** the scope is unchanged

#### Scenario: An optional category is toggled

- **WHEN** Privacy is added to and then removed from scope
- **THEN** the in-scope requirement set grows and shrinks accordingly
- **AND** both changes are audited

#### Scenario: An unknown category is added to scope

- **WHEN** a category that no requirement of the pinned version carries is submitted
- **THEN** the request is rejected
- **AND** the scope is unchanged, so the denominator cannot be changed by a typo

#### Scenario: A second engagement is activated (D4)

- **GIVEN** a tenant with one active engagement
- **WHEN** a second engagement is activated
- **THEN** the response is 409
- **AND** the refusal comes from a database constraint, not from a check the service could lose a
  race against

#### Scenario: A draft engagement is deleted

- **GIVEN** an engagement in `draft`
- **WHEN** it is deleted
- **THEN** it is removed along with its framework pins and scope rows
- **AND** deleting an active or closed engagement returns 409

#### Scenario: A pinned framework version cannot be withdrawn (D7b)

- **WHEN** a framework version referenced by any engagement is deleted from global content
- **THEN** the database refuses it

#### Scenario: Cross-tenant engagement access

- **GIVEN** an engagement belonging to tenant B
- **WHEN** a session bound to tenant A requests it by id
- **THEN** the response is 404, not 403

### Requirement: The coverage view lists every in-scope criterion with no mapped control (D7b, D7c)

For the engagement's pinned framework version **(D7b)** and categories in scope, the coverage view
returns every requirement that has no **accepted** **(D7c)**, enabled, mapped control, grouped by
category, with a count per category and a total. The word *accepted* is D7c's review lifecycle; if
D7c is overridden the filter is simply "mapped and enabled", and shipped mappings seeding as
`accepted` rather than `suggested` (open in D7) is what makes a new tenant's coverage read from its
library at all rather than from nothing.

A requirement whose only control has been disabled appears as a gap **and** names the disabled
control, so the loss of coverage is explained rather than silently reflected in a lower number.

The complementary half of the coverage view — every control with no evidence — depends on the
evidence table and lands in Week 3. It is named here as absent, not omitted.

**Permission key:** `engagements:read` **(D9)**.

**Object scope:** none. The view is a tenant-wide posture read, not an ownership view.

**Audit trail written:** none — it is a read.

#### Scenario: A criterion with no control

- **GIVEN** an in-scope requirement with no mapped control
- **WHEN** the coverage view is read
- **THEN** that requirement is listed as a gap

#### Scenario: A criterion covered by a control

- **GIVEN** an in-scope requirement with an accepted **(D7c)** mapping to an enabled control
- **WHEN** the coverage view is read
- **THEN** that requirement is not listed as a gap, regardless of the control's status

#### Scenario: The only covering control is disabled

- **GIVEN** an in-scope requirement whose only mapped control is disabled
- **WHEN** the coverage view is read
- **THEN** that requirement is listed as a gap
- **AND** the disabled control is named as the coverage that was lost

#### Scenario: Out-of-scope criteria are absent

- **GIVEN** a framework version with categories both in and out of scope
- **WHEN** the coverage view is read
- **THEN** only requirements in the in-scope categories appear, covered or not

#### Scenario: Another tenant's mapping does not close a gap

- **GIVEN** tenants A and B, where B has mapped a control to requirement R and A has not
- **WHEN** A reads the coverage view
- **THEN** R is listed as a gap for A
- **AND** nothing in the response reveals that any other tenant mapped it

### Requirement: Cross-tenant access to controls, crosswalks, and engagements fails at the database (D10)

Every tenant-owned table in this change has row-level security enabled and forced, with the
standard tenant policy, in the same migration that creates it. **(D10)** `control_requirement_map`
carries its own `tenant_id` and its own policy rather than relying on reaching it through
`controls`, and the six global-content tables carry neither. Which tables fall on which side of
that line is D10 and is unconfirmed.

Every parent/child reference between two tenant-owned tables here is a **composite** foreign key on
`(tenant_id, <parent>_id)`. Postgres foreign-key checks run with row security bypassed, so a bare
`id` reference lets an A-bound session point a child row at tenant B's parent and have both the FK
and the RLS `WITH CHECK` accept it. The composite key is what makes that pairing impossible.

A session bound to tenant A cannot read, update, or disable tenant B's rows, and cannot insert a
row carrying tenant B.

#### Scenario: A list in tenant A

- **GIVEN** controls, crosswalk rows, and engagements in tenants A and B
- **WHEN** a session bound to A lists any of them
- **THEN** only A's rows are returned

#### Scenario: A direct read of a B row by id

- **GIVEN** the identifier of a control, crosswalk row, or engagement belonging to tenant B
- **WHEN** a session bound to A requests it
- **THEN** the response is 404, not 403

#### Scenario: A write carrying the wrong tenant

- **GIVEN** a session bound to A
- **WHEN** it attempts to insert a control, crosswalk row, engagement, framework pin, or scope
  category carrying tenant B
- **THEN** the database refuses the write

#### Scenario: A child row cannot reference another tenant's parent

- **GIVEN** a session bound to tenant A
- **WHEN** it inserts a crosswalk row carrying A's `tenant_id` but tenant B's `control_id`, or an
  engagement-framework row carrying A's `tenant_id` but B's `engagement_id`, or a scope-category row
  carrying A's `tenant_id` but B's `engagement_framework_id`, or a role assignment carrying A's
  `tenant_id` but B's `engagement_id`
- **THEN** the database refuses each one, because the foreign key is composite on
  `(tenant_id, <parent>_id)` and no such pair exists
- **AND** the refusal comes from the foreign key, not from a service-layer check

#### Scenario: Global content is not tenant-filtered by mistake

- **GIVEN** a session bound to tenant A
- **WHEN** frameworks, requirements, and control templates are read
- **THEN** every row is returned
- **AND** binding a different tenant returns the same rows, because global content carries no
  `tenant_id` and no policy

#### Scenario: An unqualified crosswalk query cannot leak

- **GIVEN** a coverage-gap query written against `control_requirement_map` without joining through
  `controls`
- **WHEN** it runs in a session bound to tenant A
- **THEN** it still sees only tenant A's mapping rows, because the map carries its own policy
