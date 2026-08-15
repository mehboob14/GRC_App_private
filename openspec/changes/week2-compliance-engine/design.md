# Design — compliance engine

## Schema status

The column lists below are **derived**. The ER document describes this module in prose (Section
3.2) and names its relationships (Section 4), but does not give column lists in a form that can be
transposed directly. The derivation sources, in priority order:

1. The ER Design document §3.2 prose and §4 linkage table
2. The framework-engine deep-dive's "Recommended hardening to adopt now" (adopted per
   `week2-decisions.md` D7)
3. `docs/conventions/database.md` and `docs/architecture/data-model.md`
4. The shape of the content actually being seeded — `control_library.json` (114 templates) and
   `soc2_controls.json` (61 requirements)

**Sources 2 and 4 are not in this repository.** The framework-engine deep-dive and both JSON files
live in the earlier prototype repo at `C:/Users/HP/OneDrive/Desktop/Platform/grc-s` — see
`proposal.md`, "Provenance", for the exact paths and for the task that vendors the two JSON files
in with a recorded `sha256`. Until that task runs, no citation of them in this change resolves for
a reader of this repository, and the seed has no reproducible input.

Every derived column is marked `-- DERIVED`. Approving this design is approving these columns.

`created_at` / `updated_at` are on every table per convention and are not repeated. `id` is UUIDv7
throughout. No table in this change is append-only.

**Two recorded deviations from the ER diagrams**, both from `week2-decisions.md`:

- **D8** — the diagrams show `owner_id` / `user_id` against `users`. `CLAUDE.md` rule 9 and
  ADR-0011 win: `controls.owner_membership_id` is a foreign key to `tenant_memberships.id`, and so
  is every other person reference here. A foreign key to `users.id` on a tenant-owned table is a
  schema defect. The ER identity diagrams are already known stale (`week1-review-decisions.md`
  item 11); this is the same deviation one module later.
- **Engagement scope** is a join table, not the ER's free `jsonb` `categories_in_scope`. The
  deep-dive names the failure: a renamed or mistyped category silently changes the readiness
  denominator, and there is no way to defend a historical percentage. The join table is also less
  code than validating the `jsonb` would have been.

---

## Layers

The engine is three layers by ownership, plus an instantiation step and a derivation step.

| Layer | Tables | Ownership |
|---|---|---|
| **A — global content** | `frameworks`, `framework_versions`, `requirements`, `framework_version_requirements` | Shipped like code. No `tenant_id`, no RLS, `SELECT` only to the app role. |
| **B — the template library (also global)** | `control_templates`, `template_requirement_map` | The platform's compliance IP. The bridge between global knowledge and tenant reality. |
| **C — tenant reality** | `controls`, `control_requirement_map`, `engagements`, `engagement_frameworks`, `engagement_scope_categories` | `tenant_id` on every row, RLS enabled and forced. |

Evidence never attaches to a framework. It attaches to a control (Week 3). Coverage is always
derived by walking control → requirement → framework version, which is the single property that
makes a second framework an `INSERT` instead of a rebuild.

---

## Tables — Layer A, global content (no `tenant_id`, no RLS)

```
frameworks
  id           uuid PK, UUIDv7
  code         text NOT NULL UNIQUE           -- 'SOC2'
  name         text NOT NULL                  -- 'SOC 2'
  description  text NULL
  built_in     bool NOT NULL DEFAULT true
```

```
framework_versions                            -- DERIVED (deep-dive hardening (b); not in the ER)
  id            uuid PK, UUIDv7
  framework_id  uuid NOT NULL FK -> frameworks.id ON DELETE RESTRICT
  version       text NOT NULL                 -- '2017-rev-2022'
  published_at  timestamptz NOT NULL
  is_current    bool NOT NULL DEFAULT false
  UNIQUE (framework_id, version)
  partial UNIQUE (framework_id) WHERE is_current      -- exactly one current version per framework
```

```
requirements
  id               uuid PK, UUIDv7            -- NEVER re-minted for a given (framework_id, code)
  framework_id     uuid NOT NULL FK -> frameworks.id ON DELETE RESTRICT
  code             text NOT NULL              -- 'CC6.1'
  requirement_key  text NOT NULL UNIQUE       -- DERIVED: 'SOC2:CC6.1' = frameworks.code||':'||code
  category         text NOT NULL              -- 'Logical & Physical Access'
  name             text NOT NULL              -- the criterion text
  description      text NULL
  is_always_in_scope bool NOT NULL DEFAULT false  -- DERIVED: true for the 33 common criteria
  UNIQUE (framework_id, code)
```

`requirements.id` is the **stable identity**. It is minted once per `(framework_id, code)` and is
never re-minted — a typo fix or a wording change mutates this row. Everything that maps to a
requirement (both crosswalks, and `readiness_snapshots` in Week 3) foreign-keys to this `id`, so a
content update can never leave a dangling mapping. That is the deep-dive's requirement-key
stability point, achieved with a foreign key rather than with an unconstrained text key.

`requirement_key` is the human-facing natural key — `SOC2:CC6.1` — carried as a real column so it
appears in exports, API responses, and log lines without a join, and so an operator can name a
requirement without knowing a uuid.

`is_always_in_scope` carries the rule "Security is always in scope" as data rather than as a string
prefix test on the code. True for the 33 common-criteria requirements (CC1-CC9, spanning 9
categories); false for the 28 in Availability, Confidentiality, Processing Integrity, and Privacy.
A second framework decides its own answer at seed time.

```
framework_version_requirements                -- DERIVED (deep-dive hardening (b))
  framework_version_id  uuid NOT NULL FK -> framework_versions.id ON DELETE RESTRICT
  requirement_id        uuid NOT NULL FK -> requirements.id ON DELETE RESTRICT
  PRIMARY KEY (framework_version_id, requirement_id)
```

Versioning lives here rather than on `requirements`, so a requirement's identity survives a version
bump. Publishing v1.1 that adds a requirement is: one `INSERT` into `requirements` (new row, new
key) plus `INSERT`s into this table **for the new version only**. A tenant pinned to v1 is
untouched — their denominator cannot grow mid-engagement. A version that drops a requirement simply
omits the row; the requirement and every historical mapping to it remain explainable.

This is a named refinement of the deep-dive's literal recommendation. The deep-dive suggests
hanging `requirements` off `framework_version_id` and referencing a stable text key from the
mappings. That form gets version pinning but gives up the foreign key, which is the exact integrity
the risk was about. Putting the version in a join table keeps both.

## Tables — Layer B, the template library (global)

```
control_templates
  id                       uuid PK, UUIDv7
  code                     text NOT NULL          -- the slug: 'code-of-conduct'
  canonical_key            text NOT NULL          -- DERIVED (deep-dive hardening (a))
  name                     text NOT NULL
  category                 text NOT NULL          -- one of the 11 library categories
  control_type             text NOT NULL          -- DERIVED (D1): seeded = category
  control_sub_type         text NULL              -- DERIVED (D1): NULL on all 114; NO CHECK
  importance               text NOT NULL
  description              text NOT NULL
  implementation_guidance  text NULL
  built_in                 bool NOT NULL DEFAULT true
  CONSTRAINT uq_control_templates__code            UNIQUE (code)
  CONSTRAINT ck_control_templates__control_type    CHECK (control_type IN <CONTROL_TYPE_VOCAB>)
  CONSTRAINT ck_control_templates__importance      CHECK (importance IN ('mandatory','preferred'))
  index ix_control_templates__canonical_key (canonical_key)
```

**`<CONTROL_TYPE_VOCAB>` is one list, used verbatim on both tables.** It is the 11 library
categories from `week2-decisions.md` D1 — Governance, Risk & Compliance; Data Management & Privacy;
Identity & Access Management; Secure Development & Code Management; Infrastructure & Network
Security; Logging, Monitoring & Incident Management; Human Resources & Personnel Security; Business
Continuity & Third-Party Management; Endpoint Security; Communications & Collaboration Security;
Physical & Environmental Security. `controls.control_type` and `control_templates.control_type`
carry the **same** constraint: a template whose type a control could not legally hold is a template
that cannot be instantiated, and the previous draft had the check on only one of the two.

**`control_sub_type` carries no `CHECK` on either table, deliberately.** D1 says no Sub-type
vocabulary exists yet. A `CHECK` against a vocabulary with no members rejects every non-null value,
which would ship a column no custom control could ever populate. The constraint arrives with the
client's list, as D1's one-line `ADD CONSTRAINT`.

`canonical_key` is **not unique** on this table, deliberately. Two content packs may legitimately
ship two templates for the same concept — the deep-dive's second reuse failure case — and the
shared canonical key is precisely what lets instantiation collapse them into one tenant control.
On the 114 seeded rows `canonical_key` equals `code`, so the column costs nothing today and is
load-bearing the day a second pack ships.

```
template_requirement_map                      -- the shipped crosswalk; the platform's IP
  id              uuid PK, UUIDv7
  template_id     uuid NOT NULL FK -> control_templates.id ON DELETE RESTRICT
  requirement_id  uuid NOT NULL FK -> requirements.id ON DELETE RESTRICT
  coverage        text NOT NULL DEFAULT 'full'                               -- DERIVED (D7c)
  weight          numeric(4,3) NOT NULL DEFAULT 1.000                        -- DERIVED (D7c)
  rationale       text NULL                                                  -- DERIVED (D7c)
  CONSTRAINT uq_template_requirement_map__template_requirement
             UNIQUE (template_id, requirement_id)
  CONSTRAINT ck_template_requirement_map__coverage CHECK (coverage IN ('full','partial'))
  CONSTRAINT ck_template_requirement_map__weight   CHECK (weight > 0 AND weight <= 1)
  index ix_template_requirement_map__requirement_id (requirement_id, template_id)
```

150 rows seeded, all `coverage='full'`, `weight=1.000`, `rationale` null. The reverse index is
covering so "which templates satisfy these requirements" is answered index-only.

## Tables — Layer C, tenant plane (`tenant_id`, RLS enabled and forced)

```
controls
  id                        uuid PK, UUIDv7
  tenant_id                 uuid NOT NULL FK -> tenants.id
  code                      text NOT NULL              -- human code, unique in the tenant
  canonical_key             text NULL                  -- DERIVED (D7a); NULL allowed for custom
  template_id               uuid NULL FK -> control_templates.id ON DELETE RESTRICT  -- provenance
  name                      text NOT NULL
  description               text NULL
  control_type              text NOT NULL              -- D1; CHECK, same vocab as templates
  control_sub_type          text NULL                  -- D1; NO CHECK — no vocabulary exists yet
  owner_membership_id       uuid NULL FK -> tenant_memberships.id   -- D8: membership, NOT users
  status                    text NOT NULL DEFAULT 'not_started'
  implementation_guidance   text NULL                  -- inherited from template, editable
  is_disabled               bool NOT NULL DEFAULT false
  disabled_justification    text NULL
  disabled_at               timestamptz NULL
  disabled_by_membership_id uuid NULL FK -> tenant_memberships.id   -- D8
  instantiated_content_hash text NULL                  -- DERIVED (D7d); written once, read never
  source                    text NOT NULL DEFAULT 'manual'
  external_id               text NULL
  synced_at                 timestamptz NULL
  CONSTRAINT uq_controls__tenant_id_code UNIQUE (tenant_id, code)
  CONSTRAINT uq_controls__tenant_id_id   UNIQUE (tenant_id, id)   -- composite-FK target; see below
  partial UNIQUE (tenant_id, canonical_key) WHERE canonical_key IS NOT NULL     -- D7a, load-bearing
  partial UNIQUE (tenant_id, source, external_id) WHERE external_id IS NOT NULL -- convention
  CONSTRAINT ck_controls__control_type CHECK (control_type IN <CONTROL_TYPE_VOCAB>)
  CONSTRAINT ck_controls__status
             CHECK (status IN ('not_started','in_progress','implemented','not_applicable'))
  CONSTRAINT ck_controls__disabled_justification
             CHECK (is_disabled = false OR disabled_justification IS NOT NULL)
  CONSTRAINT ck_controls__disabled_at
             CHECK (is_disabled = false OR disabled_at IS NOT NULL)
```

`UNIQUE (tenant_id, id)` is redundant as a uniqueness claim — `id` is already the primary key — and
exists solely so a child table can foreign-key the **pair**. See "Composite foreign keys" below.

**`template_id` is provenance, `canonical_key` is identity.** A custom control has no
`template_id`; it may still carry a `canonical_key`, which is what stops the first ISO pack from
duplicating a hand-built MFA control. `ON DELETE RESTRICT` on `template_id` means a content pack
cannot be retracted out from under a tenant's provenance.

The disable columns implement `CLAUDE.md` rule 4: a compliance object is disabled with a recorded
justification, never deleted. **There is no `DELETE` route for a control**, and the CHECK
constraints mean a row cannot reach the disabled state without a reason and a timestamp — the
justification is enforced by the database, not by remembering to validate it.

`source` / `external_id` / `synced_at` are present from the first migration per
`docs/conventions/database.md`, even though every Week 2 control is manual. The unique index is
partial so the 114 instantiated controls (all `source='manual'`, `external_id` null) do not collide.

`instantiated_content_hash` is written by the instantiator and read by nothing in this change. It
exists because provenance drift that has already happened cannot be reconstructed: without it we
can never afterwards distinguish a control the tenant customised from a pristine copy of a template
whose guidance has since improved (`week2-decisions.md` D7d).

```
control_requirement_map                       -- the tenant's own crosswalk
  id                        uuid PK, UUIDv7
  tenant_id                 uuid NOT NULL FK -> tenants.id
  control_id                uuid NOT NULL                                              -- see FK below
  requirement_id            uuid NOT NULL FK -> requirements.id ON DELETE RESTRICT
  coverage                  text NOT NULL DEFAULT 'full'                               -- D7c
  weight                    numeric(4,3) NOT NULL DEFAULT 1.000                        -- D7c
  rationale                 text NULL                                                  -- D7c
  review_status             text NOT NULL DEFAULT 'accepted'                           -- D7c
  reviewed_by_membership_id uuid NULL FK -> tenant_memberships.id                      -- D8
  reviewed_at               timestamptz NULL
  CONSTRAINT uq_control_requirement_map__tenant_control_requirement
             UNIQUE (tenant_id, control_id, requirement_id)
  CONSTRAINT fk_control_requirement_map__control
             FOREIGN KEY (tenant_id, control_id)
             REFERENCES controls (tenant_id, id) ON DELETE RESTRICT      -- composite; see below
  CONSTRAINT ck_control_requirement_map__coverage CHECK (coverage IN ('full','partial'))
  CONSTRAINT ck_control_requirement_map__weight   CHECK (weight > 0 AND weight <= 1)
  CONSTRAINT ck_control_requirement_map__review_status
             CHECK (review_status IN ('suggested','accepted','rejected'))
  CONSTRAINT ck_control_requirement_map__rejected_reviewed_at
             CHECK (review_status <> 'rejected' OR reviewed_at IS NOT NULL)
```

Seeded from the shipped crosswalk at instantiation, tenant-editable thereafter. Mappings created by
instantiation are `review_status='accepted'` with `reviewed_by_membership_id` **null**, meaning
"accepted as shipped platform content, not reviewed by a person in this tenant". A mapping a person
adds by hand is `accepted` with the reviewer set. `suggested` is reserved for automated suggestion
in Phase 2 and is never written in Week 2. This is a compliance semantic, not an implementation
detail, and it is flagged as open in `week2-decisions.md` D7.

`ON DELETE RESTRICT` on `control_id` is not defensive clutter: it is what makes a hard delete of a
control impossible even from a psql session, which is the same rule the disable columns encode at
the service layer.

```
engagements
  id                    uuid PK, UUIDv7
  tenant_id             uuid NOT NULL FK -> tenants.id
  name                  text NOT NULL
  audit_type            text NOT NULL
  observation_start_on  date NOT NULL
  observation_end_on    date NOT NULL
  status                text NOT NULL DEFAULT 'draft'
  closed_at             timestamptz NULL
  closed_reason         text NULL
  CONSTRAINT uq_engagements__tenant_id_name UNIQUE (tenant_id, name)
  CONSTRAINT uq_engagements__tenant_id_id   UNIQUE (tenant_id, id)  -- composite-FK target
  partial UNIQUE (tenant_id) WHERE status = 'active'          -- D4: one active engagement
  CONSTRAINT ck_engagements__audit_type CHECK (audit_type IN ('type_1','type_2'))
  CONSTRAINT ck_engagements__status     CHECK (status IN ('draft','active','closed'))
  CONSTRAINT ck_engagements__observation_window
             CHECK (observation_start_on <= observation_end_on)
  CONSTRAINT ck_engagements__type_1_point_in_time
             CHECK (audit_type <> 'type_1' OR observation_start_on = observation_end_on)
  CONSTRAINT ck_engagements__closed_fields
             CHECK (status <> 'closed' OR (closed_at IS NOT NULL AND closed_reason IS NOT NULL))
```

A **Type I** report is a point in time; a **Type II** covers a window. Rather than making the end
date nullable and branching every downstream query, a Type I engagement stores the as-of date in
both columns and the CHECK enforces it. Every consumer — the coverage view now, evidence
effective-date filtering in Week 3 — sees one window shape and never has to ask which audit type
it is looking at.

`status='draft'` is the one state where a hard `DELETE` is permitted, per
`docs/conventions/database.md` ("hard deletion exists only for drafts and tenant teardown").

```
engagement_frameworks
  id                    uuid PK, UUIDv7
  tenant_id             uuid NOT NULL FK -> tenants.id
  engagement_id         uuid NOT NULL                                                  -- see FK below
  framework_version_id  uuid NOT NULL FK -> framework_versions.id ON DELETE RESTRICT   -- D7b pin
  CONSTRAINT uq_engagement_frameworks__tenant_engagement_version
             UNIQUE (tenant_id, engagement_id, framework_version_id)
  CONSTRAINT uq_engagement_frameworks__tenant_id_id UNIQUE (tenant_id, id)  -- composite-FK target
  CONSTRAINT fk_engagement_frameworks__engagement
             FOREIGN KEY (tenant_id, engagement_id)
             REFERENCES engagements (tenant_id, id) ON DELETE CASCADE       -- composite
```

**This is the version pin.** Readiness always computes against the version named here, so a content
update published mid-engagement cannot move the number. `ON DELETE RESTRICT` on the version means
a published version can never be withdrawn while an engagement points at it. `ON DELETE CASCADE`
on the engagement is safe because the only deletable engagement is a draft.

```
engagement_scope_categories                   -- DERIVED: replaces the ER's jsonb categories_in_scope
  id                       uuid PK, UUIDv7
  tenant_id                uuid NOT NULL FK -> tenants.id
  engagement_framework_id  uuid NOT NULL                                    -- see FK below
  category                 text NOT NULL
  CONSTRAINT uq_engagement_scope_categories__tenant_ef_category
             UNIQUE (tenant_id, engagement_framework_id, category)
  CONSTRAINT fk_engagement_scope_categories__engagement_framework
             FOREIGN KEY (tenant_id, engagement_framework_id)
             REFERENCES engagement_frameworks (tenant_id, id) ON DELETE CASCADE   -- composite
```

`category` is validated in the service against the distinct categories of the pinned version's
requirements, so a typo is a 422 rather than a silently smaller denominator. It is a text column
rather than a foreign key because categories are an attribute of requirements, not an entity —
promoting them to a table would buy a constraint we get from a one-line validation and a test.

**Security is always in scope.** Every category containing an `is_always_in_scope` requirement is
inserted automatically when the framework is added to the engagement and cannot be removed; the
API rejects the attempt with a typed error rather than silently ignoring it. The other four SOC 2
categories (Availability, Confidentiality, Processing Integrity, Privacy) are opt-in.

## Composite foreign keys — why every parent reference carries `tenant_id`

**Postgres foreign-key checks bypass row-level security by design.** The referential-integrity
trigger runs as the constraint owner and does not see the `USING` clause. So a bare
`control_id uuid REFERENCES controls (id)` is satisfied by *any* control in the table, including
tenant B's. An A-bound session inserting a crosswalk row with its own `tenant_id = A` and
`control_id = <B's control>` passes the RLS `WITH CHECK` (the row's `tenant_id` is A) **and** passes
the foreign key (B's control exists). Both walls hold and the row is still wrong: A now owns a
mapping hanging off B's control, and every join through it crosses tenants.

The fix is to make the pair the key. Each parent declares `UNIQUE (tenant_id, id)` and each child
references the pair:

| Child | Foreign key | Parent |
|---|---|---|
| `control_requirement_map` | `(tenant_id, control_id)` | `controls (tenant_id, id)` `ON DELETE RESTRICT` |
| `engagement_frameworks` | `(tenant_id, engagement_id)` | `engagements (tenant_id, id)` `ON DELETE CASCADE` |
| `engagement_scope_categories` | `(tenant_id, engagement_framework_id)` | `engagement_frameworks (tenant_id, id)` `ON DELETE CASCADE` |
| `role_assignments` | `(tenant_id, engagement_id)` | `engagements (tenant_id, id)` `ON DELETE RESTRICT` |

The mismatched pair `(A, B's control)` does not exist in the parent, so the database refuses the
insert without consulting RLS at all. This costs three redundant unique indexes and buys a class of
cross-tenant corruption no application-layer check can be trusted to catch — exactly `CLAUDE.md`
rule 2's "the database is the wall, the query filter is the convenience".

`role_assignments.engagement_id` stays nullable, and a composite foreign key with a NULL member is
not checked (MATCH SIMPLE, the default). That is the behaviour we want: an assignment with no
engagement is unconstrained, and one with an engagement must name one in its own tenant.

## Cross-module change

```
ALTER TABLE role_assignments
  ADD CONSTRAINT fk_role_assignments__tenant_id_engagement_id
  FOREIGN KEY (tenant_id, engagement_id)
  REFERENCES engagements (tenant_id, id) ON DELETE RESTRICT;
```

`add-identity-and-access/design.md` created this column as "a nullable uuid with **no foreign
key** in this migration. The constraint is added when the compliance module creates
`engagements`." This is that migration. `RESTRICT` because an auditor's time-boxed access record
must outlive nothing — you cannot delete the engagement an auditor was scoped to. The key is
composite for the reason above: a bare `engagement_id` would let a tenant-A role assignment
time-box an auditor against tenant B's engagement, and neither RLS nor the foreign key would object.

## Row-level security

| Table | Policy |
|---|---|
| `frameworks`, `framework_versions`, `requirements`, `framework_version_requirements`, `control_templates`, `template_requirement_map` | **None.** Global content. `GRANT SELECT` to `verity_app` and nothing else. |
| `controls`, `control_requirement_map`, `engagements`, `engagement_frameworks`, `engagement_scope_categories` | Standard tenant policy on `tenant_id`, `ENABLE` + `FORCE`, in the same migration that creates the table. `grant_crud()`. |

Standard tenant policy, the same `verity.db.rls.enable_rls` helper every other tenant-owned table
uses:

```sql
USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
```

**Global content is granted `SELECT` only — `grant_crud()` is deliberately not called on it.** The
content loader runs as the migration (owner) role, which is already configured to be a different
role from `verity_app` (`DATABASE_MIGRATION_URL` must differ from `DATABASE_URL`, enforced in
`core/config.py`). A service cannot write a framework or a requirement even by mistake: the grant
is not there. This is the deep-dive's global-boundary risk, closed by privilege rather than by
convention.

**`control_requirement_map` carries its own `tenant_id`** even though it is reachable only through
`controls`. The deep-dive names the exact query that breaks without it: a coverage-gap
`NOT EXISTS` written against the map without joining through `controls` leaks the fact that some
other tenant mapped a requirement. A direct policy closes that by construction rather than by
remembering to write the join every time. Same reasoning as `group_members` in Week 1.

**Every readiness and coverage join crosses the RLS boundary** — tenant-scoped `controls` joined to
unscoped `requirements`. That is intended; it is what makes multi-framework cheap. The two failure
modes are (i) RLS naively applied to a global table, which makes every tenant's compliance read
empty, and (ii) an unqualified map query leaking across tenants. Both get an explicit isolation
test.

### Isolation tests this design requires

Beyond the standard two-tenant read/write matrix, this change owes three tests that exist because
of the specific hazards above. Each asserts the refusal comes from the **database**, in raw SQL
against a tenant-bound session, not from a service-layer check that a future refactor could delete.

1. **Global content stays readable and unwritable.** With tenant A bound, `frameworks`,
   `requirements`, and `control_templates` return 1 / 61 / 114; `INSERT` / `UPDATE` / `DELETE` on
   all six global tables are refused for lack of privilege.
2. **The unqualified crosswalk query cannot leak.** A coverage-gap `NOT EXISTS` written against
   `control_requirement_map` without joining through `controls` still sees only A's rows.
3. **Cross-tenant parent references are refused by the foreign key.** With tenant A bound, each of
   these four inserts must raise `foreign_key_violation` — carrying A's own `tenant_id` every time,
   so RLS is satisfied and the foreign key is the only thing left to refuse it:

   | Table | Row that must be refused |
   |---|---|
   | `control_requirement_map` | `tenant_id = A`, `control_id` = a control owned by tenant B |
   | `engagement_frameworks` | `tenant_id = A`, `engagement_id` = an engagement owned by B |
   | `engagement_scope_categories` | `tenant_id = A`, `engagement_framework_id` = a row owned by B |
   | `role_assignments` | `tenant_id = A`, `engagement_id` = an engagement owned by B |

   The test must assert `foreign_key_violation` specifically. A row rejected for some other reason
   would pass a naive "it raised" assertion while leaving the actual hole open, and this is exactly
   the pairing a bare `id` reference accepts.

## Indexes

`tenant_id` leads every composite index on a tenant-owned table, so the RLS predicate is an index
range bound rather than a post-filter and one tenant's rows are physically contiguous.

| Index | Columns |
|---|---|
| `uq_frameworks__code` | `(code)` |
| `uq_framework_versions__framework_id_version` | `(framework_id, version)` |
| `uq_framework_versions__framework_id_current` | `(framework_id)` partial, `WHERE is_current` |
| `uq_requirements__requirement_key` | `(requirement_key)` |
| `uq_requirements__framework_id_code` | `(framework_id, code)` |
| `uq_control_templates__code` | `(code)` |
| `ix_control_templates__canonical_key` | `(canonical_key)` |
| `uq_template_requirement_map__template_requirement` | `(template_id, requirement_id)` |
| `ix_template_requirement_map__requirement_template` | `(requirement_id, template_id)` — covering, reverse direction |
| `uq_controls__tenant_id_code` | `(tenant_id, code)` |
| `uq_controls__tenant_id_id` | `(tenant_id, id)` — composite-FK target, not a uniqueness claim |
| `uq_controls__tenant_id_canonical_key` | `(tenant_id, canonical_key)` partial, `WHERE canonical_key IS NOT NULL` |
| `uq_controls__tenant_id_source_external_id` | `(tenant_id, source, external_id)` partial, `WHERE external_id IS NOT NULL` |
| `ix_controls__tenant_id_status` | `(tenant_id, status)` — the library list's default filter |
| `ix_controls__tenant_id_control_type` | `(tenant_id, control_type, control_sub_type)` — the Type/Sub-type filter |
| `ix_controls__tenant_id_owner` | `(tenant_id, owner_membership_id)` — `ControlOwnerScope` |
| `uq_control_requirement_map__tenant_control_requirement` | `(tenant_id, control_id, requirement_id)` |
| `ix_control_requirement_map__tenant_requirement_control` | `(tenant_id, requirement_id, control_id)` — covering, the coverage view's direction |
| `uq_engagements__tenant_id_name` | `(tenant_id, name)` |
| `uq_engagements__tenant_id_id` | `(tenant_id, id)` — composite-FK target |
| `uq_engagements__tenant_active` | `(tenant_id)` partial, `WHERE status = 'active'` |
| `uq_engagement_frameworks__tenant_engagement_version` | `(tenant_id, engagement_id, framework_version_id)` |
| `uq_engagement_frameworks__tenant_id_id` | `(tenant_id, id)` — composite-FK target |
| `uq_engagement_scope_categories__tenant_ef_category` | `(tenant_id, engagement_framework_id, category)` |

The crosswalk is traversed in **both** directions — requirement→control for the coverage view,
control→requirement for the control detail page — which is why it carries two indexes rather than
one. Both are covering, so neither drill-down touches the heap.

## The instantiation algorithm

Materialises the template library into tenant reality. Runs at tenant creation (via
`tenant_provisioning`'s `seed_content` step) and again whenever a framework version is added to a
tenant.

```
instantiate(tenant_id, framework_version_id) -> InstantiationResult:

  templates = SELECT DISTINCT t.*
              FROM control_templates t
              JOIN template_requirement_map m ON m.template_id = t.id
              JOIN framework_version_requirements fvr ON fvr.requirement_id = m.requirement_id
              WHERE fvr.framework_version_id = :framework_version_id

  for t in templates:
      # 1. Upsert the control on canonical identity — D7a. Never a twin.
      #    The arbiter is the PARTIAL index uq_controls__tenant_id_canonical_key, so the
      #    conflict target MUST repeat its predicate. Without `WHERE canonical_key IS NOT NULL`
      #    Postgres cannot infer a partial index and raises 42P10 at runtime, on every row.
      INSERT INTO controls (tenant_id, code, canonical_key, template_id, name, description,
                            control_type, control_sub_type, implementation_guidance,
                            status, instantiated_content_hash)
      VALUES (:tenant_id, next_free_code(t.code), t.canonical_key, t.id, t.name, t.description,
              t.control_type, t.control_sub_type, t.implementation_guidance,
              'not_started', sha256(t.name || t.description || t.implementation_guidance))
      ON CONFLICT (tenant_id, canonical_key) WHERE canonical_key IS NOT NULL DO NOTHING
      RETURNING id
      # If no row came back, the tenant already has this concept. Re-select it and reuse it.
      # An existing control's tenant-owned fields — owner, status, guidance, disabled — are
      # NEVER overwritten. Instantiation adds; it does not edit.
      #
      # `uq_controls__tenant_id_code` is a SECOND arbiter and ON CONFLICT can only infer one.
      # A code collision therefore raises unique_violation rather than doing nothing. The
      # statement is wrapped in a SAVEPOINT and retried with the next free code, up to a small
      # bound, then gives up with a typed error. See next_free_code() below.

      # 2. Project the shipped crosswalk into the tenant's own, for this version only.
      for (requirement_id, coverage, weight, rationale) in shipped_map(t, framework_version_id):
          INSERT INTO control_requirement_map (tenant_id, control_id, requirement_id,
                                               coverage, weight, rationale, review_status)
          VALUES (:tenant_id, control.id, requirement_id, coverage, weight, rationale, 'accepted')
          ON CONFLICT (tenant_id, control_id, requirement_id) DO NOTHING

  return InstantiationResult(controls_created, controls_reused, mappings_created)
```

**Properties this buys, each of which is a named risk in the deep-dive:**

- **Idempotent.** Running it twice creates nothing the second time. Both `ON CONFLICT` clauses name
  real unique indexes, so a re-run is a no-op rather than a duplicate. This is **not** the same as
  being race-free: see the concurrency note below.
- **Reuse over duplication.** Enabling a second framework whose templates share canonical keys with
  the tenant's existing controls adds **only crosswalk edges**. No twin, no split evidence, no two
  owners for one operational reality. This is the property the whole hardening exists for, and the
  isolation suite proves it with a synthetic second framework.
- **Custom controls participate.** A hand-built control that has opted into a canonical key is
  found by the upsert and reused, which is the case `template_id` alone cannot cover.
- **Non-destructive.** A tenant's edits are never clobbered by a later instantiation.

**Concurrency — stated plainly rather than claimed away.** `next_free_code(slug)` resolves a
`(tenant_id, code)` collision — possible when a custom control has already taken the slug — by
appending `-2`, `-3`, and so on, and it does that by **reading the tenant's existing codes and then
writing**. That is a read-then-write, and two concurrent instantiations into the same tenant can
both pick the same free code. The database is what catches it: the loser gets a
`unique_violation` on `uq_controls__tenant_id_code`, and the path **retries** inside a `SAVEPOINT`
with the next free code, bounded at a handful of attempts before raising a typed domain error.

So: the canonical-key arbiter is handled by the database, and the code collision is handled by
retrying on `unique_violation`. There is no claim here that concurrency is fully handled by the
database — it is not, and writing that down is cheaper than someone discovering it under a
provisioning storm. The canonical key, not the code, is the identity; the code is a label, which is
why re-labelling on retry is safe.

**Audit.** One `create` audit row per control and per mapping, in the same transaction as the
inserts, actor `system` when run by provisioning and the acting membership when run by an explicit
"enable framework" call. A rolled-back instantiation leaves no audit rows — integration-tested.

**Cost.** For SOC 2 v1 into an empty tenant: 114 control inserts and 150 mapping inserts, one
transaction, well inside a request. It is synchronous. Moving it to Celery would add a job, a
status-polling contract, and a partial-failure story to save a few hundred milliseconds — not
worth it until a content pack is an order of magnitude larger.

## Readiness — decided here, computed in Week 3

Nothing in this change computes a percentage. The formula is settled in `week2-decisions.md` D2 and
recorded here so the Week 2 columns are not questioned later:

```
requirement_score = min(1, Σ over accepted, enabled, mapped controls of
                            weight × control_score)

control_score = 1.0   implemented AND has current evidence
                0.5   exactly one of those
                0.0   neither

# A requirement with no mapped control scores 0.0 and STAYS in the denominator.
# A disabled control leaves the numerator; the requirement stays in the denominator.
# Framework readiness = mean of requirement_score over requirements in scope. Never over controls.
```

It will live in **one pure function**, `verity.modules.compliance.readiness.score()` — plain data
in, numbers out, no session, no HTTP. **That function is written in the Week 3 change, not this
one**; writing it here would contradict this change's Non-goals and D2, which defers the
implementation to Week 3. Because every seeded mapping is `coverage='full', weight=1.000`, the
weighted form reduces exactly to 1.0 / 0.5 / 0.0 for every tenant on day one.

The Week 2 coverage view is the part of this that needs no evidence: **which in-scope requirements
have no accepted, enabled, mapped control**. The other half — controls with no evidence — is one
anti-join added in Week 3 against a table that does not exist yet, and is named in the proposal's
Non-goals rather than quietly dropped.

## Routes, permissions, and object scope

| Route | Key | Object scope |
|---|---|---|
| `GET /api/v1/frameworks` | `frameworks:read` | none |
| `GET /api/v1/frameworks/{id}/requirements` | `frameworks:read` | none (global content) |
| `GET /api/v1/controls` | `controls:read` | `ControlOwnerScope` when the caller holds only Control Owner |
| `POST /api/v1/controls` | `controls:manage` | none |
| `GET /api/v1/controls/{id}` | `controls:read` | `ControlOwnerScope` → **404**, never 403 |
| `PATCH /api/v1/controls/{id}` | `controls:manage` | `ControlOwnerScope` |
| `PUT /api/v1/controls/{id}/requirements` | `controls:manage` | `ControlOwnerScope` |
| `POST /api/v1/controls/{id}/disable` | `controls:manage` | `ControlOwnerScope` |
| `POST /api/v1/controls/{id}/enable` | `controls:manage` | `ControlOwnerScope` |
| `GET /api/v1/engagements` | `engagements:read` | none |
| `POST /api/v1/engagements` | `engagements:manage` | none |
| `GET /api/v1/engagements/{id}` | `engagements:read` | none |
| `PATCH /api/v1/engagements/{id}` | `engagements:manage` | none |
| `POST /api/v1/engagements/{id}/frameworks` | `engagements:manage` | none |
| `PUT /api/v1/engagements/{id}/frameworks/{efid}/categories` | `engagements:manage` | none |
| `POST /api/v1/engagements/{id}/activate` | `engagements:manage` | none |
| `DELETE /api/v1/engagements/{id}` | `engagements:manage` | draft only; 409 otherwise |
| `GET /api/v1/engagements/{id}/coverage` | `engagements:read` | none |

**There is no `DELETE /controls/{id}`.** Not a missing route — an absent one, by rule 4.

`ControlOwnerScope` is the concrete object scope `add-identity-and-access/design.md` said would
land with this module, filtering on `controls.owner_membership_id`. Week 1 review finding #17 —
`EngagementScope.allows(...)` treats its argument as an engagement id rather than the
object-under-access id the `ObjectScope` protocol defines — is reconciled in this change, because
this is the first module that actually uses the protocol.

The five permission keys are seeded by this migration with `ON CONFLICT (key) DO NOTHING`
(`week2-decisions.md` D9). The built-in **Compliance Manager** role receives all five; **Control
Owner** receives `frameworks:read`, `controls:read`, `controls:manage` (scoped to owned controls by
`ControlOwnerScope`) and `engagements:read`; **Auditor** receives the three read keys; **Employee**
receives none. **Admin** needs no change — its grant is "every key that exists", resolved at check
time (`week1-review-decisions.md` item 13).

## Idempotency — what happens if this runs twice?

**Instantiation** is idempotent by construction, on two unique indexes — the partial
`(tenant_id, canonical_key)` (conflict target written **with** its predicate) and
`(tenant_id, control_id, requirement_id)`. Second run: zero rows,
`InstantiationResult(0, 114, 0)`. Concurrent runs additionally lean on the `unique_violation` retry
described above for `(tenant_id, code)`.

**The content seed** is idempotent: `ON CONFLICT DO NOTHING` on every natural key
(`frameworks.code`, `(framework_id, version)`, `(framework_id, code)`, `control_templates.code`,
`(template_id, requirement_id)`). Re-running the migration's seed after a partial failure completes
it rather than duplicating it.

**Custom control creation** is guarded by `UNIQUE (tenant_id, code)` — a repeat is a 409, not a
second row. It accepts no `Idempotency-Key`; it is a human-driven form submission, not a
connector path.

**Disable** is idempotent: disabling an already-disabled control is a no-op returning the existing
row, and does **not** write a second audit row or overwrite the original justification.

**Engagement activation** is guarded by the partial unique index. Activating a second engagement
while one is active is a 409 from the constraint, not a race the service has to win.

## Dependencies, timeouts, and failure

Postgres only. No external calls, no object storage (Week 3), no queue, no LLM. There is nothing
in this change that can be slow or down except the database, and every path is a single
transaction opened by `core.db.session_scope`, which binds the tenant with `SET LOCAL` inside the
`BEGIN` — the pooling discipline the deep-dive names as the highest-severity operational risk.

The one path with real cost is instantiation (264 inserts). It runs inside the provisioning
transaction. If it fails, the tenant's `seed_content` step stays `pending` and is retried, which is
exactly the Week 1 provisioning semantics (`week1-review-decisions.md` item 8) and needs no new
mechanism.

Coverage is computed live in Week 2 — 61 requirements against a few hundred mapping rows, on
covering indexes. The deep-dive is right that live derivation stops scaling at roughly 50-100
tenants, and the answer is `readiness_snapshots`, which is Week 3. Computing live now is correct
now and is not a decision that has to be unwound: the snapshot writer will call the same pure
function.

## Reversibility

The migration is reversible. The downgrade drops every compliance table, which destroys every
tenant control, every crosswalk edit, and every engagement on the deployment — the tenant's own
compliance work, not just shipped content. It also drops the foreign key added to
`role_assignments.engagement_id`, returning that column to the bare nullable uuid Week 1 created.
The docstring says all of this in as many words.
