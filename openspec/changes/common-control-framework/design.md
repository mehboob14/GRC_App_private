# Design: the Verity control framework, automation, platform evidence and new frameworks

Build reference for `proposal.md`. Product requirements (IDs CF, AU, ME, FW) are in
`docs/product/control-framework-requirements.md`; the architecture decision is ADR-0014.

## 0. Where the code is today

| Layer | Tables (as shipped) | Notes |
|---|---|---|
| Framework content (global) | `frameworks`, `framework_versions`, `requirements`, `framework_version_requirements` | Generic. `requirement_key` is namespaced (`SOC2:CC6.1`). Versions are pinned by engagements (D7b). |
| Control library (global) | `control_templates` (114), `template_requirement_map` (150) | `canonical_key` is not unique on purpose: two packs that ship one concept collapse into one tenant control (D7a). Map rows carry `coverage`, `weight`, `rationale`, all left at full, 1.0, NULL. |
| Working library (tenant) | `controls`, `control_requirements` | Template text is copied at adoption; the tenant owns its mappings. |
| Evidence (tenant) | `evidence`, `evidence_controls` | `kind` includes connector results; `source`, `external_id`, `synced_at` exist (rule 9). |
| Linkage (tenant) | `links`, `modules/linkage` | Assets, vulnerabilities, risks, controls, evidence, documents, vendors, tasks. |
| Automation | none | `docs/architecture/data-model.md` promises capability free checks bound to control templates, `check_results` partitioned monthly, findings per check, connection and resource. |

Two known gaps from the week 2 review carry into this change: the content loader prunes globally,
so a second pack would delete the first pack's rows; and no mapping has a rationale, so the
crosswalk cannot be defended to an auditor.

## 1. Vocabulary

- **Framework.** A published set of requirements an organisation is audited or assessed against
  (SOC 2, ISO/IEC 27001:2022, HIPAA Security Rule, GDPR). Versioned.
- **Requirement.** One unit of a framework: a SOC 2 criterion, an ISO clause or Annex A control, a
  HIPAA implementation specification, a GDPR article or paragraph. Hierarchical.
- **Verity control (common control).** A framework neutral statement of what the organisation does,
  written once in Verity's words, with a stable code (`IAM-03`) and a stable `canonical_key`.
- **Mapping.** An edge from a Verity control to a requirement with a relationship, a coverage
  judgement and a written rationale.
- **Capability.** A kind of system a test needs to read, for example version control or identity
  provider. Tests bind to capabilities, never to one vendor.
- **Provider.** A product that offers a capability (GitHub, GitLab, Bitbucket and Azure DevOps all
  offer version control). Verity itself is a provider for its own modules.
- **Test.** A named, automatable assertion about a capability, for example "every production
  repository protects its default branch". A test has one implementation per provider.
- **Evidence source.** Where a control's proof comes from: manual upload, a test on a connected
  provider, or a Verity module report. A control can have all three.

## 2. The common control framework (content plane)

### 2.1 control_templates (additive columns)

| Column | Type | Purpose |
|---|---|---|
| `objective` | text null | Why the control exists, one sentence, in Verity's words. |
| `test_procedure` | text null | How an auditor tests it (inspect, observe, reperform), so evidence requests match audit practice. |
| `evidence_guidance` | text null | What proof satisfies it, by evidence type and source. |
| `frequency` | text null | `continuous`, `daily`, `weekly`, `monthly`, `quarterly`, `annual`, `event`. Drives renewal and monitoring defaults. |
| `applicability` | jsonb default `{}` | Conditions from the company profile (`uses_cloud`, `has_office`, `processes_payment_cards`, `processes_phi`). Drives the adoption preview, never deletes. |
| `status` | text default `active` | `active`, `deprecated`. A deprecated template stays for history; `superseded_by` names its successor. |
| `superseded_by` | text null | A `canonical_key`. |
| `content_version` | int default 1 | Bumped by the loader when text changes, so a tenant sees "the library wording changed" and chooses. |

The `code` stays the public control ID (`IAM-03`). Codes are never reused.

### 2.2 requirements (additive columns)

| Column | Type | Purpose |
|---|---|---|
| `parent_code` | text null | Hierarchy inside a framework (ISO `5` > `5.1`; HIPAA `164.308(a)(1)` > `(ii)(A)`). |
| `kind` | text | `criterion`, `point_of_focus`, `clause`, `annex_control`, `article`, `safeguard`, `implementation_spec`, `requirement`. |
| `title` | text | Short title. Shipped only where the licence allows (section 6). |
| `summary` | text null | Verity's own words: what the requirement expects. Always shippable. |
| `text_policy` | text | `full`, `title_only`, `id_only`. What the pack may carry for this framework. |
| `scope_group` | text null | Generalises `trust_services_category`: the unit an engagement scopes on (SOC 2 category, ISO clause set, HIPAA safeguard family, GDPR chapter). The old column is kept and copied. |
| `obligation` | text null | `required`, `addressable` (HIPAA), `recommended`. |
| `sort_order` | int | Stable display order. |

### 2.3 template_requirement_map (additive columns)

The fields are the ones NIST IR 8477 recommends for a set theory mapping, so the crosswalk can be
exported as an OSCAL 1.2 `mapping-collection` and read by an auditor without Verity.

| Column | Type | Purpose |
|---|---|---|
| `relationship` | text null | The control compared with the requirement: `equal`, `subset_of` (meets part of it), `superset_of` (does more than it asks), `intersects_with`. NULL means not reviewed yet. |
| `rationale_type` | text null | `syntactic` (similar wording), `semantic` (similar meaning), `functional` (similar result when operated). |
| `strength` | smallint null | 0 to 10 (IR 8278A: 10 equal, 7 to 9 strong overlap, 4 to 6 moderate, 1 to 3 weak). |
| `coverage` | existing | `full` or `partial`: does this control, on its own, meet the requirement. |
| `weight` | existing | Readiness weight, unchanged. |
| `rationale` | existing, required to publish | One or two sentences an auditor can read. |
| `source` | text | `verity_expert`, `publisher` (the standard body's own mapping), `nist_olir` (NIST authored entries only). Where the proposal came from; the decision is always Verity's. |
| `status` | text | `draft`, `reviewed`, `published`. Only published rows count. |
| `authored_by`, `reviewed_by`, `reviewed_at` | text, text, timestamptz | Two person rule, recorded in the pack. |

Backfill: the 150 SOC 2 rows become `published` with `relationship NULL` and `source
verity_expert`, and sit in the review queue until a reviewer fills the rest. Readiness does not
change: it still reads `coverage` and `weight`.

A requirement counts as met only when every published control mapped to it is implemented and
passing (Drata, Vanta and Secureframe behave the same way). Compliance is never inferred from one
framework's requirement to another's: reuse happens through the shared control and its evidence.
Any result the platform infers for a person is a draft they confirm (rule 11).

### 2.4 New global tables

- `requirement_transitions`: `from_requirement_id`, `to_requirement_id`, `relationship`, `note`.
  Carries a framework's own revision (PCI DSS 4.0 to 4.0.1, the 2024 climate amendment to ISO/IEC
  27001:2022, the next SOC 2 points of focus) so a tenant upgrades with its work carried across.
  The ISO 2013 to 2022 transition closed on 31 October 2025, so only the 2022 edition ships.
- `framework_packs`: `framework_id`, `pack_version`, `sha256`, `source`, `licence_note`,
  `loaded_at`. One row per loaded pack: provenance for every requirement and mapping.
- `frameworks.maturity`: `requirements_only` (structure shipped, the tenant maps it to its own
  controls), `mapped` (expert crosswalk published), `automated` (tests and reports cover what can be
  automated). A framework can ship early as requirements only, the way Drata ships COBIT and SOX
  ITGC, and deepen without a migration.

Global tables stay global (rule 1): no `tenant_id`, `GRANT SELECT` only to the application role.

## 3. Tenant plane

| Table | New or changed | Purpose |
|---|---|---|
| `tenant_frameworks` | new | Which frameworks and versions a workspace has turned on, with scope choices and who activated them. Replaces "SOC 2 is implied". |
| `engagements` | changed later | The `UNIQUE (tenant_id)` is relaxed to one engagement per framework version when a second framework ships (Phase 3). |
| `control_requirements` | changed | Add `origin` (`template`, `tenant`) and `rationale`: a mapping the tenant adds or removes is a decision an auditor may ask about. |
| `requirement_applicability` | new | Per tenant and requirement: `applicable`, `justification`, `implementation_status`, `owner_membership_id`, `reviewed_at`. Generates the ISO Statement of Applicability. |
| `custom_frameworks`, `custom_requirements` | new, later | A workspace's own framework (customer contract, internal standard) with the same shape as the global tables, tenant owned with RLS, mapped to the same controls. |

Every new tenant table carries `tenant_id` first in its indexes, forced RLS and grants in its
migration, and audit rows for every write (rules 1, 2, 5, 12).

## 4. Automation model

### 4.1 Global content

| Table | Key columns | Notes |
|---|---|---|
| `integration_capabilities` | `key` (`version_control`), `name`, `description` | About 15 capabilities; list in the requirements appendix. |
| `integration_providers` | `key` (`github`), `name`, `status` (`available`, `beta`, `planned`), `delivery_phase` | The catalogue the Connections page and the control page read. Replaces the hardcoded frontend list. |
| `provider_capabilities` | `provider_key`, `capability_key` | GitHub offers `version_control` and `ci_cd`. |
| `checks` | `key` (`vc.default_branch_protected`), `name`, `description`, `resource_type`, `severity`, `default_frequency`, `remediation`, `evidence_description`, `version` | Provider neutral. |
| `check_capability_requirements` | `check_key`, `capability_key`, `rule` (`any_of`, `all_of`), `group_no` | "Needs one version control system", or "needs an HR system and an identity provider". |
| `check_implementations` | `check_key`, `provider_key`, `status` | Which providers can run the test today. A capability with no available implementation shows the providers as Soon. |
| `control_template_checks` | `template_id`, `check_key`, `coverage` | Which tests automate which control, fully or partly. |

### 4.2 Tenant tables

| Table | Notes |
|---|---|
| `connections` | Provider, display name, scope (organisation, account, projects), status, last sync, error streak, credential expiry. Credentials envelope encrypted (rule 8), never logged. Integratable triple. |
| `control_checks` | Copied from `control_template_checks` at adoption. A tenant can disable a test with a reason (rule 6) or scope it to resources (tags, repositories, accounts). |
| `check_runs` | One row per execution: check, connection, started, finished, outcome, counts. |
| `check_results` | Append only, partitioned by month. One row per check, connection and resource per run: `pass`, `fail`, `error`, `not_applicable`, `stale`, with the observed value and a pointer to the raw snapshot. |
| `findings` | One per failing check, connection and resource; `open`, `acknowledged`, `snoozed`, `resolved`; resolves itself on the next pass (spec 2.2). |
| `waivers` | Time boxed, justified, signed off; expiry reopens the finding (spec 2.2). |
| `integration_requests` | A customer asks for a provider Verity does not support: provider name, capability, use, requester. Visible to the provider plane for roadmap triage. |

### 4.3 States and aggregation

- A test on a capability with no connected provider is `not_configured`. This is derived, never
  stored, never counts as failing and never counts as passing: the control falls back to its manual
  evidence path. One connected provider in the capability is enough; with several connected, the
  test runs on each and every one must pass.
- Excluding a resource from a test (a sandbox repository, a break glass account) needs a written
  reason, is audited, and shows on the evidence.
- A collection problem is `error`, never `fail` (spec 2.2).
- A control's automated status: `failing` if any enabled test fails on any in scope resource without
  a live waiver; else `error` if any errored; else `passing` if at least one ran and all passed;
  else `not_configured`.
- Observation window coverage for Type II: the share of days in the window on which every test of
  the control passed, shown per control and rolled into readiness.
- Every run writes an evidence item (`kind` connector result) with the raw snapshot, its hash and the
  resources read, attached to the control. Automated and manual evidence share one table and one
  renewal queue (data model, Evidence).

### 4.4 As built (GitHub, build plan week 7)

Simplifications against 4.1 to 4.3, each reversible without a data migration of tenant rows:

- `checks.capabilities` (JSONB list, all required) replaces `check_capability_requirements`;
  `checks.implementations` (JSONB list) replaces `check_implementations`; providers live in
  `integration_capabilities.providers` (JSONB) rather than their own tables. One content file
  drives all three.
- No `control_checks` yet: every mapped check applies to every adopted control. Per control
  disabling and scoping (AU-9) add it.
- No `findings` or `waivers` yet: the latest run's failing rows are the open issues. Phase 2 (spec
  2.2) adds them with auto resolve.
- `check_results` monthly partitions are pre-created to December 2028 with a default partition;
  `tests/unit/test_check_result_partitions.py` fails six months before the range ends.
- Evidence: one JSON snapshot per connection per day, sooner when results change, attached to every
  control whose checks produced a pass or fail, valid seven days.

## 5. Verity modules as evidence (platform provider)

Verity is registered as the provider `verity`, always connected, with capabilities
`asset_inventory`, `vulnerability_management`, `risk_management`, `vendor_management`,
`policy_management`, `task_management`, and later `access_reviews`, `incident_management`,
`training_records`. Platform tests read module tables through their services (rule 4); they never
query another module's tables.

Two kinds of output:

1. **Platform tests.** Continuous, per resource, same states as connector tests. Examples: every
   active asset has an owner and a classification; no critical or high vulnerability is past its SLA
   without an approved exception; a risk assessment was completed in the last twelve months; every
   critical or high vendor was assessed inside its cadence; every required policy was reviewed in the
   last twelve months and at least the target share of staff acknowledged it.
2. **Evidence reports.** A point in time export that an auditor can test as information produced by
   the entity. Generated on a schedule (the control's frequency) and on demand. Each report is an
   XLSX with fixed header columns plus a PDF cover sheet that states the source module, the filters
   and parameters used, generated at and by, the row count, a completeness statement and the SHA256
   of the XLSX. Stored as evidence (`kind` platform report), attached to every mapped control,
   renewed by the normal renewal queue. Screenshots are not generated: an export with parameters is
   stronger evidence than a picture of a screen.

Column sets are fixed per report and listed in the requirements appendix, so a template change is a
content change reviewed like any other.

## 6. Content and licensing policy

| Source | Licence | What a pack may carry |
|---|---|---|
| NIST CSF 2.0, SP 800-53 | Public domain (NIST work) | Full text |
| HIPAA Security Rule | US government work, no copyright | Full text |
| GDPR, NIS2, DORA | EU reuse notice: commercial reuse with attribution | Full text with attribution |
| AICPA Trust Services Criteria | All rights reserved | Identifiers and Verity summaries (titles after legal review) |
| ISO/IEC 27001, 27002, 42001 | No copying without ISO permission | Identifiers, short titles after legal review, Verity summaries |
| PCI DSS 4.0.1 | PCI SSC licence agreement per use | Requirement numbers and Verity summaries |
| CIS Controls v8.1 | CC BY-NC-ND 4.0, commercial use needs CIS approval | Identifiers only unless approved |
| Secure Controls Framework | CC BY-ND 4.0; derivatives need a commercial licence | Nothing shipped; used internally as a coverage checklist |

- The pack declares `text_policy`, and the loader refuses a pack whose text fields break it. A
  tenant may paste in text from its own licensed copy; that text is tenant data, never content.
- The SOC 2 pack carries verbatim TSC wording today (week 2 decision). It moves to identifiers and
  Verity summaries unless the AICPA grants permission. A release blocker for commercial sale, not for
  the pilot.
- Mapping sources: only NIST authored OLIR entries and a publisher's own mappings are consulted;
  third party OLIR entries (ISO to CSF) are redone by Verity reviewers; SCF is never copied or
  used to derive a shipped crosswalk without a commercial licence and legal review.
- The 114 controls derive from Probo (MIT): an attribution notice goes in the repository. Probo's
  licence does not extend to the AICPA text it carried.

## 7. Adding a framework: the pipeline

1. **Intake.** Framework, version, publisher, licence, text policy, target customers. Decision
   recorded in the pack `MANIFEST.json`.
2. **Requirements.** `requirements.json` with hierarchy, kinds, scope groups, obligation, summaries.
3. **Mapping.** For every requirement: map to existing Verity controls (relationship, rationale
   type, strength, coverage, rationale, source) or mark it `needs_new_control`. Reference crosswalks
   are consulted, not trusted.
4. **New controls.** Requirements no existing control meets get new templates in
   `new_controls.json` (for ISO 27001: management review, internal audit programme, Statement of
   Applicability, ISMS scope and context; for HIPAA: business associate agreements, the security
   risk analysis; for GDPR: records of processing, DPIA, data subject requests, breach notification).
   They join the one library with their own codes.
5. **Tests and evidence.** New controls get tests and platform reports where they can be automated.
6. **Validation in CI.** Every requirement is mapped, marked organisational (a policy or a decision,
   not a control), or `not_applicable_to_saas` with a reason; every mapping has a rationale; no
   dangling keys; text policy respected; pack hash matches the manifest.
7. **Review.** Author and a second qualified reviewer (ISO lead implementer or auditor for ISO,
   CISA or CPA for SOC 2) sign the pack. Material mapping changes need the same.
8. **Load.** The loader prunes per pack (fixes the global prune), writes `framework_packs`, and prints
   a diff. Loading never changes a tenant's controls.
9. **Activation (tenant).** Add framework, pick version and scope, see the overlap preview (for
   example "71 of 93 Annex A controls map to controls you already run; 12 new controls to adopt"),
   adopt, then set applicability. ISO clauses 4 to 10 are always applicable; only Annex A controls
   can be excluded, each with a justification (Statement of Applicability). HIPAA addressable
   specifications need either implementation or a documented reason plus an equivalent measure.
10. **Upkeep.** A publisher revision becomes a new framework version with `requirement_transitions`;
    tenants upgrade through a guided diff; engagements stay pinned to their version.

## 8. API sketch

| Route | Purpose |
|---|---|
| `GET /frameworks`, `GET /frameworks/{id}/requirements` | Tree with coverage per requirement for the workspace. |
| `GET /frameworks/{id}/overlap` | Before activation: requirements met by existing controls, partly met, new controls needed. |
| `POST /tenant-frameworks` | Activate with version and scope; adopts new controls in the same transaction. |
| `GET/PUT /tenant-frameworks/{id}/applicability` | The Statement of Applicability; `GET .../soa.xlsx` exports it. |
| `GET /controls/{id}/automation` | Tests, their capability rules, providers per capability with status, connected providers, latest results. |
| `POST /integration-requests` | Ask for a provider Verity does not support. |
| `GET /controls/{id}/evidence-sources` | Manual types, platform reports, connector tests for the control. |
| `POST /controls/{id}/platform-evidence` | Generate the control's platform report now. |
| `GET /frameworks/{id}/mappings.csv` | The published crosswalk with relationship, rationale and reviewer. OSCAL 1.2 `mapping-collection` JSON later (extension). |

## 9. Migration plan

All changes are additive with defaults, so nothing existing breaks:

1. Content columns and new global tables; backfill SOC 2 rows; loader per pack prune.
2. Capability, provider, check tables loaded from a `automation/` pack (content only) so the control
   page can show automation options before any connector exists.
3. Tenant automation tables with RLS, partitions and grants (Phase 2 build).
4. `tenant_frameworks`, `requirement_applicability`, relaxed engagement uniqueness (Phase 3 build).

Every migration ships with a working downgrade and its RLS policies (rule 12).
