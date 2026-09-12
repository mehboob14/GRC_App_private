# Design — third-party vendor risk

Every decision tagged **(Vn)** rests on an unconfirmed answer in `vendor-decisions.md` and
changes if that answer changes. Untagged design rests on the signed documents or on an existing
Verity convention.

---

## 1. Data model

**This section is the build reference.** Every migration in this change is written from here and
from nowhere else — not from the ten ER diagram images, not from the tables that used to summarise
them. Columns below are transcribed verbatim from the ER's section-3.7 diagrams, with the ER's own
vocabulary annotations kept because those become the `Final` tuples and the `CHECK` constraints.

**Twenty-seven tables: twenty-five tenant-owned and two global.** Twenty-four of the tenant-owned
ones and both global ones are the ER's twenty-six **(V14)**. The twenty-fifth, `vendor_transitions`,
is not drawn by the ER and is required by rule 5 and by every other module in this codebase.

### How to read a block

Each block lists only the table's **defining** columns. ER ¶17 states that shared columns appear
once in its section 6 and are omitted from each box, so a column's absence from a diagram is never
permission to omit it. Applied to Verity, every block below silently also carries:

| Always present | From |
|---|---|
| `id uuid` PK, UUIDv7 | `UUIDPrimaryKey` |
| `tenant_id uuid` NOT NULL, first column of every composite index | `TenantScoped` (rule 1) |
| `created_at`, `updated_at` | `Timestamped` |

Append-only tables are the documented exception and carry their event timestamp alone. Line
prefixes: `+` is a Verity addition the ER does not draw, `~` is a Verity change to what it draws.
Every addition and change is in the deviation register below — nothing is altered silently.

**Four rules bind every block, and the first one is the one most likely to be got wrong.**

1. **Every person column is an FK to `tenant_memberships`, never to `users`** (rule 3). The ER
   writes `uuid user_id FK` and `uuid ..._by FK` throughout, and the reference GRC-Tenant product
   pointed those at `users` — that is one of the weaknesses this change explicitly does not adopt,
   because it lets you attach a person to a tenant they are not a member of. This applies to
   `business_owner_id`, `security_owner_id`, `relationship_owner_id`, `internal_owner_id`,
   `requested_by`, `decided_by`, `assessed_by`, `reviewed_by`, `owner_id`, `acknowledged_by`,
   `revoked_by`, and `vendor_team_roster.user_id`.
2. **Status and type columns are text with a `CHECK`, never a Postgres enum** (`docs/conventions/
   database.md`). The vocabularies below are the constraint's contents.
3. **Vocabularies are written three times** — a module-level `Final[tuple[str, ...]]`, again
   literally in the migration, and again in the frontend types. Deliberately: Alembic must not
   import a model, and TypeScript cannot import Python.
4. **Every tenant-owned table gets `enable_rls` + `grant_crud` in the migration that creates it**
   (rule 12), and an isolation test in this change.

### Deviation register

The ER wins on any disagreement (`docs/architecture/data-model.md`), so every departure is listed
rather than absorbed. Seven are renames; the structural list grew to twenty-three as sections 2
through 4 landed and each appended what it had to change.

**Renames.** The rule applied: keep the ER's table name; prefix only where the bare name is too
generic to sit in a shared schema, and pluralise where the ER is inconsistent with itself.

| ER name | Ships as | Why |
|---|---|---|
| `QUESTIONS` | `questionnaire_questions` | A global table named `questions` is too generic for a shared schema. |
| `TIERING_POLICIES` | `vendor_tiering_policies` | Tenant-owned and vendor-specific; sits beside `vendor_tiering_assessments`. |
| `ASSESSMENT_RESPONSES` | `vendor_assessment_responses` | Prefix; `assessments` is a word three other modules also use. |
| `ASSESSMENT_COMMENTS` | `vendor_assessment_comments` | Same. |
| `SOC_REPORT_REVIEWS` | `vendor_soc_report_reviews` | Same. |
| `DISCOVERED_APPS` | `vendor_discovered_apps` | Unprefixed it reads as a platform-wide inventory, which it is not. |
| `VENDOR_OFFBOARDING` | `vendor_offboardings` | The ER's own singular; every other table here is plural. |

`QUESTIONNAIRE_TEMPLATES` keeps its ER name. It is global content, and `*_templates` is already
CLAUDE.md rule 1's naming for exactly that plane — an earlier draft of this design called it
`questionnaire_banks`, which invented a word for a convention that already existed. **"Bank" stays
as the UI word for a published set of questions; the table is `questionnaire_templates`.**

**Structural.**

| Deviation | Why |
|---|---|
| `+ vendor_transitions` — a table the ER does not draw | Rule 5 and the pattern `task_transitions` / `asset_transitions` / `vuln_transitions` already set: two records per state change, one columnar and one in `audit_log`. |
| `− vendor_reviewers` — a table an earlier draft of this design proposed, now **cut** | Spec ¶82's "required reviewers" needs no table. `vendor_tiering_policies.required_reviewer_roles_by_tier` says which roles a tier demands; `vendor_team_roster` already maps role → person. The diligence exit criterion is satisfied by intersecting the two. |
| `~ vendor_assessments.portal_token` → `portal_token_hash` + `portal_token_expires_at` + `portal_token_revoked_at` | **(V11)** A bearer token that reaches an unauthenticated endpoint is a credential, and rule 8 keeps credentials out of the database in a readable form. |
| `~ vendor_stages.entered_at` is kept as the ER writes it | An earlier draft of this design said `started_at` in the gate-freshness rule. Same column, ER's name. The rule reads `approval.decided_at >= stage.entered_at`. |
| `− vendor_stages.exit_blockers` — proposed, now **cut** | §2 states exit criteria are computed and never stored. A stored blocker list is a cache that goes stale the moment the record that clears it changes. |
| `+ id` on `vendor_assessment_responses` | The ER diagram marks no PK on that box. It gets a UUIDv7 `id` like every other table, plus `UNIQUE (tenant_id, assessment_id, question_id)` which is the real identity. |
| `+ vendor_tiering_assessments.policy_snapshot` — a JSONB column the ER does not draw | The weights and thresholds are a tenant-editable row. Without freezing the ones a run used, *"why is this vendor critical"* stops being answerable the moment somebody retunes the policy — and spec ¶82 requires the arithmetic be visible. One column, and it is what lets the defaults live in code. |
| `vendor_tiering_policies` ships with **no seeded rows** | The defaults live in `vendors/scoring.py` and `vendors/lifecycle.py`; a row here is the override a tenant writes when they retune, merged field by field. That keeps a new tenant free of a provisioning step and keeps the migration from inserting a tenant-owned row it cannot see through that row's own policy — `FORCE` binds the owner too. |
| `+ vendor_tiering_policies.stage_skip_matrix_by_tier` and `.required_reviewer_roles_by_tier` | Spec ¶82 promises the tier right-sizes assessment depth, **required reviewers** and cadence. The ER draws the depth and the cadence, and leaves the other two nowhere to live. |
| `~ vendor_transitions` carries `occurred_at` alone | `docs/conventions/database.md`: an `updated_at` on a table that refuses `UPDATE` could only ever lie. This diverges from `vuln_transitions`, which composes `Timestamped` — that is the sibling drifting from the convention, not this one. |
| `+ vendor_stages.cycle`, `is_required`, `skipped_by_membership_id`, `skipped_reason`, `skipped_by_policy` | `cycle` replaces a `vendor_cycles` table. `is_required` is V2's third flag. The three skip columns are why a skipped row is defensible and not merely recorded. |

---

### 1.1 The register

```
vendors                                       -- ER VENDORS
  name                        string
  vendor_type                 string   ∈ vendor | supplier | contractor | partner
| `+ vendor_portal_tokens` — a table the ER does not draw, on the **global plane** | A portal request presents a token and nothing else, so the tenant must be resolved before it can be bound — and `vendor_assessments` is tenant-owned with FORCE RLS, so it cannot answer that. This is the same job `users` and `user_identities` already do on that plane. It holds a hash and the pair it resolves to: no secret, no personal data. The three token columns V11 put on `vendor_assessments` move here, so revocation and rotation are rows rather than an overwritten column. |
| `+ questionnaire_templates.code` / `questionnaire_questions.code` | The stable identity a re-seed and a version bump key on, matching `frameworks.code` and `control_templates.canonical_key`. A response points at the question it answered, so rewording in a later pack must move the same row. |
| `+ questionnaire_templates.is_current`, `.description` | Which version an issue picks by default. An assessment in flight keeps the `template_id` it was dispatched with. |
| `+ vendor_assessments.score_snapshot`, `.cycle`, `.submitted_at`, `.portal_contact_id` | `score_snapshot` freezes the ceiling and domain weights a score used, for the same reason `policy_snapshot` freezes the tiering weights. |
| `+ vendor_findings.title`, `.detail`, `.engagement_id`, `.accepted_rationale`, `.accepted_by_membership_id`, `.closed_at` | The ER draws a finding with no words in it. A finding a reader cannot understand without opening the question it came from is not a finding. |
| `~ vendor_findings.promoted_risk_id` and `.task_id` and `vendor_assessment_responses.evidence_id` carry **no ORM relationship** | Declaring one makes the vendors mapper resolve another module's table at configuration time, which means importing another module's models — exactly what the boundary contract forbids. The migration owns the constraint; `audit_log.actor_id` already carries a column this way. |
| `+ audit_log.actor_type` gains `vendor_contact` | The portal is the first path where a state change is made by somebody who is neither a member nor the system. The polymorphic pair was built for precisely this; a fourth case costs one CHECK. Recording answers as `system` would make *"who answered this question"* unanswerable. |
| `− vendor_assessments.decision` — **dropped** in section 4 | V3. The ER draws two decision enums that disagree: four-valued verbs on `vendor_approvals`, three-valued participles on the assessment. The approval row is the record of who decided what, when and why; the assessment is the work product and keeps its `status`. Section 3 shipped the column by transcribing the ER before this was settled. |
| `+ vendor_approvals.excluded_membership_ids`, `.engagement_id`, `.cycle` | Who was barred from deciding, frozen at decision time. The business owner can change afterwards, so "was segregation of duties applied here" would otherwise stop being answerable from the row. |
| `+ vendor_documents.title`, `.reviewed_at`; `+ vendor_contracts.title`, `.evidence_id`; `+ vendor_slas.vendor_id`, `.measured_at`; `+ vendor_soc_report_reviews.vendor_id`, `.cuec_notes` | The ER draws several of these tables with no human-readable label and no denormalised vendor, which makes every list query a join and every row unnameable on screen. |
| `+ vendor_intake_requests.vendor_name`, `.decision_reason`, `.decided_at` | The ER's intake row has no name for the thing being requested. |
| `+ vendor_offboardings.reason`, `.completed_at` | Completion is a state, not the absence of one, and the reason is the first thing anyone reviewing an exit asks for. |
| `+ vendor_signals.title`, `.detail`, `.acknowledged_at`; `+ vendor_alert_rules.name`, `.is_enabled` | Same reason: a signal with no words in it cannot be triaged. |
  industry                    string
  website                     string
  business_unit               string
  services_provided           text
  stores_pii                  bool
  data_location               string
  data_types_in_scope         jsonb
  data_classification         string
  lifecycle_status            string   ∈ requested | under_review | approved | active
                                         | flagged | on_hold | offboarding | terminated
                                         | archived
  tier                        string   ∈ critical | high | medium | low   -- cached, worst engagement
  current_residual_score      numeric  -- cached from latest assessment
  current_grade               string   -- cached
  business_owner_id           fk membership
  security_owner_id           fk membership
  relationship_owner_id       fk membership
  annual_contract_value       numeric  -- cached from active contracts
  next_reassessment_on        date     -- computed from schedule, NOT from completion
  tags                        jsonb
+ source / external_id / synced_at        -- Integratable; see below
```

`vendors` composes **`Integratable`**. `docs/conventions/database.md` names this table by name —
*"Apply it even when the table is manual-only today — assets, vulnerabilities, tasks, users,
vendors, discovered apps"* — so the register carries `source`, `external_id` and `synced_at` with
`UNIQUE (tenant_id, source, external_id)` from its first migration, exactly like `vendor_signals`
and `vendor_discovered_apps` do further down. A procurement or SSO connector is then an upsert, not
a migration.

The four cached columns exist for one reason: ranking a portfolio of hundreds without joining
every engagement. **They are derived and never authoritative (V10).** A vendor serving two
departments with different data is two risks; the vendor row shows the worse one so it sorts to
the top, and the engagement row is what anyone acts on. `name` and `website` carry **no unique
constraint** — duplicate detection is application logic on save (ER ¶90) that warns and offers the
match, because two genuinely different subsidiaries can share a trading name and a hard constraint
would refuse a legitimate record.
```
vendor_engagements                            -- ER VENDOR_ENGAGEMENTS
  vendor_id                   fk vendors
  name                        string   -- one use of the vendor
  service_description         text
  business_unit               string
  internal_owner_id           fk membership
  tier                        string   -- engagement-level tier; the real one
  status                      string
  start_date                  date
  end_date                    date
```

**The engagement is the unit of risk (V10).** Stages, tiering runs, assessments and contracts all
hang off an engagement, not off the vendor. Every vendor gets one implicit default engagement at
creation, so no query anywhere special-cases a null engagement and the simple case stays simple.

```
vendor_contacts                               -- ER VENDOR_CONTACTS
  vendor_id                   fk vendors
  name                        string
  email                       string
  phone                       string
  contact_type                string   ∈ security | privacy | commercial | portal
```

```
vendor_team_roster                            -- ER VENDOR_TEAM_ROSTER
  role                        string   ∈ tprm_lead | analyst | security | privacy | legal
                                         | procurement | exec_approver | it
  user_id                     fk membership   -- ER writes user_id; it is a membership (rule 3)
```

Tenant-wide, not per-engagement — the ER draws no `vendor_id` here and none is added. Roles as
rows, not the reference product's JSON blob. Together with the tiering policy's
`required_reviewer_roles_by_tier` this is the whole of spec ¶82's "required reviewers".

```
vendor_intake_requests                        -- ER VENDOR_INTAKE_REQUESTS
  requested_by                fk membership
  department                  string
  proposed_service            text
  data_types_shared           jsonb
  urgency                     string
  screening_status            string   ∈ pending | passed | flagged
  decision                    string   ∈ pending | approved | auto_approved | rejected
  decided_by                  fk membership
  created_vendor_id           fk vendors      -- set on approval
  created_at                  timestamptz     -- from Timestamped
```

The front door. `auto_approved` is what `vendor_tiering_policies.auto_approve_low_tier` produces,
and it is a distinct value from `approved` precisely so an auditor can tell a machine decision from
a human one. **This is the one table with a real `DELETE`** — a draft request never submitted
(rule 6 covers compliance objects; an unsubmitted draft is not one yet).

### 1.2 Tiering and the lifecycle

```
vendor_tiering_policies                       -- ER TIERING_POLICIES
  factor_weights                    jsonb  -- five factors, normalise to 1
  tier_thresholds                   jsonb  -- critical, high, medium; ordered
  cadence_days_by_tier              jsonb  -- 180 / 365 / 730 / 1095
  questionnaire_bundle_by_tier      jsonb
  finding_sla_days_by_severity      jsonb  -- 7 / 30 / 90 / 180
  auto_approve_low_tier             bool
+ stage_skip_matrix_by_tier         jsonb  -- V9: which stages a tier may skip
+ required_reviewer_roles_by_tier   jsonb  -- spec ¶82; roles resolved via vendor_team_roster
```

One row per tenant, seeded with the **V6** / **V9** defaults by the migration, so a customer
retunes the model without a release. The two additions are the mechanism behind spec ¶82's
"right-sizes assessment depth, required reviewers, and reassessment cadence" — the ER draws the
depth and the cadence but leaves the other two implicit.

```
vendor_tiering_assessments                    -- ER VENDOR_TIERING_ASSESSMENTS
  vendor_id                   fk vendors
  engagement_id               fk vendor_engagements   -- ER: optional, per engagement
  data_sensitivity            int      0..4
  business_criticality        int      0..4
  system_access               int      0..4
  regulatory_scope            int      0..4
  fourth_party_reliance       int      0..4
  inherent_score              numeric  0..100
  computed_tier               string
  override_tier               string
  override_justification      text
  assessed_by                 fk membership
  assessed_at                 timestamptz
```

Immutable history: a retier writes a new row and the old one stays readable. `override_tier` with
`override_justification` is how a human beats the arithmetic on the record rather than by editing
the inputs until the model agrees — the ER draws both, and a CHECK requires the justification
whenever the override is set.

```
vendor_stages                                 -- ER VENDOR_STAGES
  vendor_id                   fk vendors
  engagement_id               fk vendor_engagements   -- the pipeline runs per engagement
  stage                       string   ∈ intake | tiering | diligence | questionnaire
                                         | scoring | findings | contracting | approval
                                         | onboarding | monitoring | reassessment
                                         | offboarding
  status                      string   ∈ not_started | in_progress | complete | skipped
  is_gate                     bool     -- true for approval only (V2)
  checklist                   jsonb
  entered_at                  timestamptz
  exited_at                   timestamptz
+ cycle                       int      -- 1, incremented by each reassessment
+ is_required                 bool     -- tiering: required, never skippable, but not a gate
+ skipped_by                  fk membership
+ skipped_reason              text
+ skipped_by_policy           string   -- the tier rule that skipped it, for the audit trail

  UNIQUE (tenant_id, engagement_id, cycle, stage)
  CHECK  NOT (is_gate AND status = 'skipped')
```

**The lifecycle is rows, not a status column or a code branch** (ER ¶101). `cycle` is a plain
integer rather than a `vendor_cycles` table: a reassessment increments it and inserts a fresh set of
stage rows, the previous cycle stays untouched, and a table would add a join to every lifecycle
query in order to hold one integer and a start date the stage rows already imply.

The `CHECK` is spec ¶82's "approval gates are never skipped" as a constraint rather than a
convention. It is the one rule in this module whose violation is a control failure rather than a
bug, so it lives in the database.

`skipped_by_policy` is why the three skip columns are worth their width: *"policy said this was
disproportionate"* and *"someone forgot"* must never look the same to an auditor.

```
vendor_transitions                            -- + Verity; the ER draws no such table
  vendor_id                   fk vendors
  engagement_id               fk vendor_engagements
  stage_id                    fk vendor_stages    ON DELETE NO ACTION
  from_stage                  string
  to_stage                    string
  action                      string   ∈ advance | send_back | skip
  reason                      text
  actor_id                    fk membership  NULL  ON DELETE NO ACTION   -- null = system
  occurred_at                 timestamptz          -- append-only: no created_at/updated_at
```

Append-only, mirroring `task_transitions` / `asset_transitions` / `vuln_transitions`. **The actor
FK is `ON DELETE NO ACTION`, deliberately**: `SET NULL` would issue an `UPDATE`, which the
append-only trigger refuses, which fails the delete. The other three tables have the same latent
problem today and it only stays latent because IAM disables memberships instead of deleting them.

```
vendor_approvals                              -- ER VENDOR_APPROVALS
  vendor_id                   fk vendors
  stage_id                    fk vendor_stages   ON DELETE NO ACTION -- the gate being exited
  decision                    string   ∈ approve | approve_with_conditions | defer | reject
  decided_by                  fk membership      ON DELETE NO ACTION -- must differ from submitter
  rationale                   text
  decided_at                  timestamptz        -- append-only
```

Append-only (ER ¶122). Four-valued **(V3)**: `defer` is not `reject`, and a product that offers
only the two extremes gets `reject` used as "not yet", which then reads as a refused vendor
forever. Segregation of duties **(V4)** is enforced server-side, not by the form.
**The gate-freshness rule.** A gate exits only on an approval belonging to *this* attempt:
`approval.decided_at >= stage.entered_at`. A send-back therefore invalidates a stale approval
without ever mutating the append-only row — the old approval stays in the record, it simply no
longer satisfies a stage that restarted after it.

```
vendor_approval_conditions                    -- ER VENDOR_APPROVAL_CONDITIONS
  approval_id                 fk vendor_approvals
  description                 text
  owner_id                    fk membership
  due_date                    date
  status                      string   ∈ open | met | overdue | waived
+ task_id                     fk tasks   -- each condition also creates a real task
```

### 1.3 The review

```
questionnaire_templates                       -- ER QUESTIONNAIRE_TEMPLATES  · GLOBAL, no tenant_id, no RLS
  name                        string   -- ER: "SIG CAIQ HECVAT DPA custom"
  version                     string   -- annual versioning
  suggested_tiers             jsonb
  framework_mappings          jsonb
  built_in                    bool
```

```
questionnaire_questions                       -- ER QUESTIONS  · GLOBAL, no tenant_id, no RLS
  template_id                 fk questionnaire_templates
  parent_question_id          fk questionnaire_questions   -- conditional branching
  trigger_condition           jsonb    -- parent answers that activate this
  answer_type                 string   ∈ yes_no_na | select | multi_select | text | numeric
  domain                      string   -- one of the ten risk domains
  scope_level                 string   ∈ lite | core | detail
  weight                      numeric
  critical_control            bool
  non_negotiable              bool
  evidence_required           bool
  framework_refs              jsonb
+ body                        text     -- the question itself; the diagram omits it
+ position                    int
```

Global content with no `tenant_id` and no RLS, exactly like the SOC 2 control library **(V5)**.
`body` is added because a question table without the question text cannot work and the diagram
plainly relies on ER ¶17's shared-column note; it is a transcription gap, not a design choice.

**V13 confirmed:** the ER's `name` annotation lists SIG, CAIQ and HECVAT, and **none of their
question text is seeded.** That content belongs to Shared Assessments, CSA and EDUCAUSE. Verity
ships one authored bank across the ten domains with `framework_mappings` and `framework_refs`
naming those standards, so an auditor recognises the coverage without the licensed wording.

```
vendor_assessments                            -- ER VENDOR_ASSESSMENTS
  vendor_id                   fk vendors
  engagement_id               fk vendor_engagements   -- ER: optional
  template_id                 fk questionnaire_templates
  kind                        string   ∈ initial | reassessment
  review_format               string   ∈ questionnaire | soc_report_review | external_report
  assessment_domain           string   ∈ security | privacy | legal | esg
  scope                       jsonb    -- domains, scope levels, question count; snapshotted at dispatch
  status                      string   ∈ pending | in_progress | submitted | expired | scored
  due_date                    date
  residual_score              numeric
  grade                       string   -- A..F
  domain_scores               jsonb
  decision                    string   ∈ pending | approved | approved_with_conditions | rejected
~ portal_token_hash           string   -- ER: portal_token. V11 — hashed, never stored readable
+ portal_token_expires_at     timestamptz
+ portal_token_revoked_at     timestamptz
+ cycle                       int      -- ties the assessment to the stage cycle
```

`scope` is snapshotted at dispatch on purpose: the template is versioned global content that can
change under a vendor mid-questionnaire, and a residual score computed against a question set
nobody can reconstruct is not defensible.

```
vendor_assessment_responses                   -- ER ASSESSMENT_RESPONSES
  assessment_id               fk vendor_assessments
  question_id                 fk questionnaire_questions
  answer                      string   ∈ yes | partial | no | na
  answer_value                jsonb    -- select and multi-select qualifiers
  implementation_notes        text
  na_justification            text
  delegated_to_contact_id     fk vendor_contacts   -- portal delegation
  evidence_id                 fk evidence
+ id                          uuid PK  -- the diagram marks none
  UNIQUE (tenant_id, assessment_id, question_id)
```

**This is the table the reference product had and never wrote to** — its portal wrote a JSON blob
and scoring silently parsed it, so the normalised table sat empty and every per-question query
returned nothing. The portal writes here. Scoring reads here. There is no JSON path.

```
vendor_assessment_comments                    -- ER ASSESSMENT_COMMENTS
  assessment_id               fk vendor_assessments
  question_id                 fk questionnaire_questions  NULL   -- null = thread level
  author_type                 string   ∈ internal_user | vendor_contact
  author_id                   uuid     -- polymorphic, NO FK (see below)
  visibility                  string   ∈ internal_only | vendor_shared
  body                        text
  created_at                  timestamptz
```

`author_type` + `author_id` is the same polymorphic actor pair `audit_log` uses, for the same
reason: one foreign key cannot point at `tenant_memberships` and `vendor_contacts` at once. The
`visibility` column is load-bearing — an `internal_only` comment leaking through the portal is a
disclosure incident, so the portal query filters on it and the isolation test covers it.

```
vendor_findings                               -- ER VENDOR_FINDINGS
  vendor_id                   fk vendors
  assessment_id               fk vendor_assessments
  question_id                 fk questionnaire_questions   -- the failing answer
  finding_source              string   ∈ assessment | sla_breach | signal | document_review
                                         | offboarding
  is_blocking                 bool     -- a critical-control failure gates approval
  severity                    string   ∈ critical | high | medium | low
  status                      string   ∈ open | in_remediation | accepted | closed
  treatment                   string   ∈ remediate | mitigate | transfer | accept
  sla_due                     date     -- from finding_sla_days_by_severity
  owner_id                    fk membership
  promoted_risk_id            uuid  NULL  -- NO FK, no promotion action; see below
+ task_id                     fk tasks   -- remediation is a real task, not a vendor to-do list
+ accepted_until              date       -- acceptance is time-boxed or it is not acceptance
```

`promoted_risk_id` ships **nullable, with no FK and no promotion action**, because `modules/risk/`
is an empty stub — no tables in any of the thirty-eight migrations. The seam is designed on both
sides (`risks.risk_source` already reserves `vendor_finding`), so the column is here and the
button is absent rather than faked. **Spec ¶85 and the ¶109 exit criterion are not satisfiable
until a risk slice lands. It is a sequencing gap, and it is stated rather than hidden.**
**Remediation is a task**, not a `vendor_remediations` table. The ER draws none, and the tasks
module already carries assignment, SLA, transitions and CAPA. A vendor-local to-do list would be a
second, worse tasks module that no dashboard counts.

### 1.4 Documents, contracts and the fourth party

```
vendor_documents                              -- ER VENDOR_DOCUMENTS
  vendor_id                   fk vendors
  doc_type                    string   ∈ soc_report | iso_cert | bridge_letter | dpa | pentest
                                         | insurance | financials | bcdr | policy
  file_ref                    string
  issue_date                  date
  valid_until                 date     -- expiry drives "needs update"
  collection_status           string   ∈ requested | received | reviewed
  review_notes                text
  reviewed_by                 fk membership
  evidence_id                 fk evidence   -- a reviewed document stands as audit evidence
```

```
vendor_soc_report_reviews                     -- ER SOC_REPORT_REVIEWS
  assessment_id               fk vendor_assessments
  document_id                 fk vendor_documents
  report_kind                 string   ∈ soc1 | soc2 | soc3
  report_type                 string   ∈ type_i | type_ii
  audit_period_start          date
  audit_period_end            date
  tsc_included                jsonb
  opinion                     string   ∈ unqualified | qualified | adverse | disclaimer
  bridge_letter_received      bool
  findings_material           bool
  cuec_reviewed               bool     -- complementary user-entity controls
  subservice_orgs             text
  cpa_firm                    string
  reviewed_by                 fk membership
```

**ER ¶110 calls this "precisely the CC9.2 evidence an auditor asks for."** It is the reason the
module can satisfy a control the platform already ships and currently cannot answer. The screen for
it leads with `opinion` and `findings_material`, because those two decide whether anything else on
the record matters.

```
vendor_contracts                              -- ER VENDOR_CONTRACTS
  vendor_id                   fk vendors
  engagement_id               fk vendor_engagements   -- ER: optional
  contract_type               string   ∈ master | dpa | sla | security_addendum | nda
  start_date                  date
  end_date                    date
  renewal_date                date     -- triggers re-review
  auto_renew                  bool
  notice_period_days          int
  breach_notification_hours   int
  right_to_audit              bool
  subprocessor_terms          bool
  exit_data_return_clause     bool
  value                       numeric
  status                      string   ∈ draft | active | expired | terminated
  file_ref                    string
```

The five clause flags are not decoration. `right_to_audit`, `breach_notification_hours` and
`exit_data_return_clause` are each an answer a questionnaire asks and an auditor checks, and each
one is otherwise buried in a PDF nobody re-reads.

```
vendor_slas                                   -- ER VENDOR_SLAS
  contract_id                 fk vendor_contracts
  name                        string
  target                      string   -- the committed level
  measurement                 string
  cure_period_days            int
  status                      string   ∈ on_track | at_risk | breached
```

`status` is the ER's column and is stored, but **the breach flag the UI shows is derived on read**
from the measurement against the target. A stored breach is a value that goes stale between
sweeps, and "breached" that quietly means "was breached last Tuesday" is worse than no flag.

```
vendor_subprocessors                          -- ER VENDOR_SUBPROCESSORS
  vendor_id                   fk vendors
  name                        string
  service                     text
  data_location               string
  provenance                  string   ∈ vendor_declared | auto_detected | intelligence
  linked_vendor_id            fk vendors  NULL   -- when the subprocessor is also a direct vendor
  status                      string   ∈ active | removed
+ notification_obligation     string    -- what the contract requires on a change
```

The fourth-party register, and a named table rather than the typed link an earlier draft proposed:
the ER draws it, and a subprocessor carries a data location and a notification obligation that a
link row cannot hold. `linked_vendor_id` is the join that makes concentration risk visible — the
same cloud provider sitting under nine of your vendors.

```
vendor_offboardings                           -- ER VENDOR_OFFBOARDING
  vendor_id                   fk vendors
  engagement_id               fk vendor_engagements   -- exit one engagement, not the vendor
  access_revoked_at           timestamptz
  revoked_by                  fk membership
  data_return_attested_at     timestamptz
  attestation_assessment_id   fk vendor_assessments   -- the vendor-facing survey
  contract_provisions_reviewed  bool
  final_payments_settled      bool
  certificate_evidence_id     fk evidence
  notes                       text
```

The evidenced exit (ER ¶127). `engagement_id` is the point: ending one department's use of a vendor
is not terminating the vendor, and a module that cannot tell those apart revokes too much or too
little. **Nothing hard-deletes** — a terminated vendor is archived (rule 6).

### 1.5 Monitoring — the four tables nothing feeds

```
vendor_scorecards                             -- ER VENDOR_SCORECARDS
  vendor_id                   fk vendors
  provider                    string   ∈ securityscorecard | bitsight | upguard | manual
  score                       numeric
  overall_grade               string
  factor_scores               jsonb
  as_of                       timestamptz    -- append-only history
```

```
vendor_signals                                -- ER VENDOR_SIGNALS
  vendor_id                   fk vendors
  signal_type                 string   ∈ rating_change | breach | adverse_media | financial
                                         | sla_breach | cert_expiry
  source_class                string   ∈ rating_platform | breach_intel | media
                                         | financial_provider | internal
  severity                    string
  dedup_key                   string   -- suppresses repeats
  status                      string   ∈ new | acknowledged | dismissed
  acknowledged_by             fk membership
  triggered_assessment_id     fk vendor_assessments   -- auto-reassessment
  observed_at                 timestamptz
```

```
vendor_alert_rules                            -- ER VENDOR_ALERT_RULES
  tier_scope                  jsonb    -- which tiers alert
  signal_types                jsonb
  min_severity                string
  action                      string   ∈ notify | create_task | trigger_reassessment
  channel                     string   ∈ slack | email
```

```
vendor_discovered_apps                        -- ER DISCOVERED_APPS
  source_connection_id        uuid  NULL   -- IdP/SSO connector; NO FK until connectors land
  app_name                    string
  oauth_scopes                jsonb
  authorizing_users           int
  first_seen_at               timestamptz
  disposition                 string   ∈ pending | added_as_vendor | linked_to_vendor | ignored
  vendor_id                   fk vendors  NULL   -- when added or linked
```

All four are **built, migrated and surfaced, and nothing feeds any of them.** `vendor_signals` and
`vendor_discovered_apps` wait on Phase 2; Slack delivery on `vendor_alert_rules` waits on the same
connector; and the scorecard providers named in the ER's own annotation — SecurityScorecard,
BitSight, UpGuard — are in **no** phase's connector catalogue at all. Every row is typed in by a
person until that changes. Two consequences the build must honour:

1. They carry `source`, `external_id` and `synced_at` from their first migration (rule 9), so the
   later connector is a sync and not a migration. `vendor_signals.dedup_key` is what makes that
   sync idempotent.
2. Their screens say **"no data source connected"** and never render an empty table. On a
   monitoring surface, *"we are watching and found nothing"* and *"we are not watching"* look
   identical and mean opposite things — and only one of them is safe to believe.

### 1.6 The seams — vendor columns on other modules' tables

These four already exist or are already reserved. **This change writes no migration for any of
them**, which is the point of checking.

| Table | Column | State |
|---|---|---|
| `risks` | `risk_source` ∈ `manual`, `starter_library`, `vendor_finding`, `assessment`; `origin_id` | Reserved in the ER. `modules/risk/` has no tables yet, so nothing to alter. |
| `assets` | ER section 3.8 draws `vendor_id` FK | **Verified absent.** `assets.models` carries `vendor_ref: Mapped[str | None]` — free text, with the comment *"Free text until the vendors module lands; then it becomes a link."* The seam is therefore a `links` row, not a column, and the ER's FK is not built. Backfilling `vendor_ref` into links is **out of scope for this change** and gets its own task when the register has rows to match against. |
| `approvals` | `object_type` includes `vendor_stage` | ER section 3.11. The vendor gate writes `vendor_approvals`, so this is a read-side concern only. |
| `links` | `to_type` and `from_type` both include `vendor` | **Verified live.** `LINK_TYPES` in `modules/links/models.py` lists `vendor`, and `status_check` puts it in the database constraint on both columns. The linkage fabric owes no migration. |

---

## 2. The lifecycle engine

Twelve stages **(V1)**, in spec ¶81 order, with `approval` the only gate **(V2)**:

```
intake → tiering* → diligence → questionnaire → scoring → findings
       → contracting → approval[GATE] → onboarding → monitoring
       → reassessment → offboarding
                                    * required, never skippable, but not a gate
```

**Three transitions, and nothing else.**

- **advance** — permitted only when `evaluate_exit(stage)` returns no blockers. Marks the stage
  complete, walks forward over any skipped rows to the next actionable stage, and writes a
  `vendor_transitions` row plus an `audit_log` row in the same transaction.
- **send_back** — to any strictly earlier stage. Every stage at or after the target resets to
  `not_started` and its blockers clear. Downstream work is invalidated **by design**, and the
  gate-freshness rule means a previously granted approval no longer counts.
- **skip** — only where the tier's skip matrix permits **(V9)**, never for a gate, and never for
  `tiering`. Requires a reason and records who skipped it.

A database `CHECK` enforces the invariant the spec states in prose: **`is_gate` and
`status = 'skipped'` cannot both be true**. Spec ¶82's "approval gates are never skipped" becomes
a constraint, not a convention, because it is the one rule in this module whose violation is a
control failure rather than a bug.

**Exit criteria** are computed, never stored as a boolean. Each returns a list of blockers, each
blocker naming the object that clears it, so the UI can link straight to it:

| Stage | Exits when |
|---|---|
| intake | name, business owner, and a data classification are set |
| tiering | a tiering assessment exists for this cycle |
| diligence | at least one bank selected and the tier's required reviewers assigned |
| questionnaire | every question answered, and no `evidence_required` question missing its file |
| scoring | a residual score has been computed |
| findings | no open finding of critical severity without an active risk acceptance |
| contracting | a contract is linked, when the tier is high or critical |
| approval | an approval exists with `decided_at >= stage.entered_at` **and** no unmitigated critical finding |
| onboarding | always passes — it is a handoff, not a control |
| monitoring | never exits; it is the steady state |
| reassessment | a new cycle has been opened |
| offboarding | terminal |

**A check is three-valued, not two.** `ExitCheck.satisfied` is `True`, `False`, or
`None` — and `None` means *the module that would answer this is not built yet*. Six stages depend
on tables sections 3 and 4 create. Their rules are written and unit-tested now against synthetic
facts, and until the facts exist they report pending: never blocking an advance, and never
rendering as a tick either. That is rule 7's `error`-versus-`fail` distinction applied to a
checklist, and it is why sections 3 and 4 widen the *fact collector* without touching a rule.

**Contracting is conditional on tier.** A contract is demanded of critical and high engagements
only. Requiring paperwork from a low-tier vendor is exactly the disproportionate work tiering
exists to remove, so the check reports "no contract required at this tier" rather than silently
passing — the reader sees the rule that let them through.

**Auto-suspend.** An onboarded vendor that acquires an open critical finding moves to
`flagged` automatically, and back when it clears. Both are audited. This is ER ¶125's rule, and
it is the one place the module changes a vendor's status without a person asking it to — which is
exactly why it is audited with an explicit machine actor rather than an inherited one.

---

## 3. Scoring

A pure module, `modules/vendors/scoring.py`, mirroring `vulnerabilities/scoring.py`: no session,
no I/O, its own unit tests, and every intermediate step returned rather than discarded — because
the vulnerability module already proved that a score whose derivation is thrown away cannot be
explained on screen afterwards.

**Inherent (V6)** — `Σ (clamp(fᵢ,0,4)/4 × wᵢ) × 100`, weights `.30 .25 .20 .15 .10`, bands at
75 / 50 / 25.

**Residual (V7)** — per domain `inherent × (1 − 0.70 × posture)` where posture is the
weight-averaged answer value (`yes 1.0`, `partial 0.5`, `no 0.0`, `na` excluded from both sides),
then weight-averaged across domains, clamped `≤ inherent`, floored at "high" when any
critical-control question is answered `no`.

Both return a breakdown — factor, answer, weight, points, and the cap — so the tiering panel can
show its arithmetic the way the vulnerability risk panel does. The clamp and the floor are
reported as their own steps, not folded into the number, for the same reason the KEV floor is:
a bar chart whose bars do not sum to the total is worse than no bar chart.

**`next_reassessment_on` is computed from the cadence schedule, not from the completion date**
(ER ¶101, `data-model.md`). A review completed late does not push the next one late; reviews
cannot drift a little further out every cycle, which is the failure mode this rule exists to
prevent.

---

## 4. Interface

Four module-root tabs — **Overview / Register / Intake / Settings** — following the tabs pattern
the assets and vulnerabilities modules already use.

**The register** earns its keep with one column the reference product does not have: **Blocker /
next action**. A vendor directory tells you who your vendors are; a worklist tells you what to do
today. That column turns one into the other, and it is the reason the register is the module's
landing tab rather than a dashboard.

When nothing is blocked, overdue, or due within thirty days, the register says so in a single
line — *"All 41 vendors are current. Next up: Stripe, review due 14 March."* Every GRC register
makes the reader infer health from the absence of red, and absence of red also looks like the
data failed to load. Naming the healthy state makes it a claim the system is willing to make.

**The lifecycle workspace** is the hard screen: twelve stages with gates, skips and blockers,
legible at once. It is a **vertical stage rail** rather than the reference product's wrapping
horizontal chips — twelve chips wrap unpredictably and lose their order, while a vertical rail
holds twelve rows with room for each stage's status, owner and blocker count on the row itself.

- **A gate looks different in kind, not in colour**: fenced by hairlines above and below and
  marked with a diamond rather than a dot, so it reads as a checkpoint at a glance. It is
  coloured by its actual state, not permanently amber — a padlock on a passed gate is a lie.
- **Blockers are the fix, not the complaint**: a danger card naming verb + the object as a link +
  its own action button. "2 blockers" with no route to clearing them is where most GRC tools stop.
- **A skipped stage carries the policy that skipped it** — dashed connector, neutral "Skipped"
  pill, and the tier rule, person, date and reason on the row. *"Policy said this was
  disproportionate"* and *"someone forgot"* must never look the same to an auditor.

**Two moments get specific attention.** When the last blocker on a gate clears, the blockers card
collapses to one success line, the disabled button becomes an enabled **Submit to approval
decision**, and a line names who must act and whether they know yet. In gated workflows the
expensive delay is not the blocker — it is the silence after it clears, because the person who
closed the finding is not the person who advances the stage.

And **segregation of duties is enforced while you pick, not after you submit**: the approver
selector greys disqualified names with the reason — *"Priya Nair — business owner, cannot
decide"*. Enforcing it only on submit means the user has already written a rationale and attached
a paper before learning the rule, and learns it as an obstacle rather than a policy.

**A reassessment opens as a diff, not a blank form** — last cycle's answers pre-filled and marked
unchanged, with a "what changed since" panel and the score delta *with its cause*. A reassessment
reviewed from scratch takes as long as the first one, so it gets rubber-stamped; reviewed as a
diff it takes twenty minutes and is actually read. It is also literally the question an auditor
asks, so the screen and the audit answer become the same artefact.

### Primitives that do not exist yet

Building this needs six additions to `components/ui`, and one correction: the stage rail, a
checklist row, a threshold ruler, a `date` variant on `TextField`, a sparkline, and the diff view
(**the documents module now has a block-and-word diff renderer — reuse it rather than build a
second**). Only six `status-*` families exist in `tokens.css`; `lock`, `calendar`, `flag` and
`history` are **not** in the icon map. A class naming a family that does not exist paints nothing
and fails silently — that has already caused one production bug in this codebase.

---

## 5. Audit, history and boundaries

**Two records per state change**, the pattern assets and vulnerabilities already document: a
columnar `vendor_transitions` row (the domain history, append-only, machine actions carry a null
actor) and an `audit_log` row via `AuditService` with before/after snapshots, in the same
transaction as the change (rule 5).

**Append-only tables carry no `ON DELETE SET NULL` actor FK.** Deleting the referenced membership
would issue an `UPDATE`, which the append-only trigger refuses, failing the delete.
`task_transitions`, `asset_transitions` and `vuln_transitions` all have this today; it is latent
only because IAM disables memberships rather than deleting them. The vendor tables use
`ON DELETE NO ACTION` and keep the id.

**Cross-module calls are service → service**, function-local imports with `# noqa: PLC0415`, and
need these `import-linter` entries in `pyproject.toml`:

```
"verity.modules.vendors.service -> verity.modules.tasks.service"
"verity.modules.vendors.service -> verity.modules.evidence.service"
"verity.modules.vendors.service -> verity.modules.documents.service"
"verity.modules.vendors.service -> verity.modules.iam.service"
```

plus a new `"vendors reaches no other module's data"` forbidden contract mirroring the other
fifteen. `links` is exempt from every contract, so calling it is free.

**Nothing hard-deletes.** A terminated vendor is archived (ER ¶127, rule 6). `DELETE` exists only
for a draft intake request that was never submitted.
