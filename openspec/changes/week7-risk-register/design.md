# Risk register design

## 1. Build reference: tables

Columns transcribed from ER 3.6 (`RISKS`, `RISK_MATRIX_SETTINGS`, `RISK_TEMPLATES`,
`RISK_CONTROL_MAP`, `RISK_ACCEPTANCES`) and extended per `risk-decisions.md`. Person references are
`*_membership_id` to `tenant_memberships` (rule 3). Every tenant owned table has `tenant_id` first in
every composite index, forced RLS and its policy in the same migration (rules 1, 2, 12).

### risk_registers (tenant owned)

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | uuid7 |
| tenant_id | uuid fk tenants cascade | |
| name | text | unique per tenant (case insensitive, service checked plus unique index) |
| register_type | text | CHECK: enterprise, rcsa, iso_27001, soc_2, pci_dss, sox, gdpr, nist_csf, sama_csf, internal, project, third_party, other |
| description | text null | |
| owner_membership_id | uuid null | fk memberships set null |
| is_default | bool | partial unique `(tenant_id) WHERE is_default` |
| status | text | CHECK active, archived |
| likelihood_levels | smallint | CHECK 3..6 |
| impact_levels | smallint | CHECK 3..6 |
| likelihood_scale | jsonb | `[{level, label, description}]`, length = likelihood_levels |
| impact_scale | jsonb | same, length = impact_levels |
| severity_bands | jsonb | `[{key, label, min_score}]`, ascending, first min_score 1 |
| review_cadence_days | int | default 90, CHECK 7..730 |
| created_by_membership_id | uuid null | |
| created_at, updated_at | timestamptz | |

Replaces ER `RISK_MATRIX_SETTINGS` (R1).

### risk_categories (tenant owned)

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid | |
| register_id | uuid fk risk_registers cascade | |
| parent_id | uuid null fk risk_categories cascade | null = category, set = sub-category |
| name | text | unique among siblings (expression index on coalesce(parent_id), lower(name)) |
| position | int | display order among siblings |
| archived_at | timestamptz null | archived instead of deleted when in use |
| created_at, updated_at | timestamptz | |

Index `(tenant_id, register_id)`.

### risks (tenant owned, integratable)

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid | |
| register_id | uuid fk risk_registers restrict | |
| code | text | `RSK-0001`, unique `(tenant_id, code)` |
| title | text | |
| description | text | default '' |
| category_id | uuid fk risk_categories restrict | a top level category |
| sub_category_id | uuid null fk risk_categories restrict | a child of category_id (service checked) |
| status | text | CHECK open, in_treatment, mitigated, accepted, closed |
| treatment | text null | CHECK mitigate, accept, avoid, transfer |
| inherent_likelihood, inherent_impact | smallint null | CHECK >= 1, both or neither |
| residual_likelihood, residual_impact | smallint null | CHECK >= 1, both or neither |
| inherent_score | int generated stored | likelihood × impact |
| residual_score | int generated stored | likelihood × impact |
| root_cause, consequences, recommendations, treatment_plan | text null | |
| owner_membership_id | uuid null | the business owner (ER `owner_id`) |
| department_group_id | uuid null fk groups set null | business unit (R8) |
| treatment_due_on | date null | |
| next_review_on | date null | ER |
| last_reviewed_at | timestamptz null | |
| origin | text | CHECK manual, library, import, vendor_finding, assessment (ER `risk_source`) |
| template_id | uuid null fk risk_templates set null | library ancestry |
| origin_ref | uuid null | ER `origin_id`, e.g. the vendor finding |
| closure_justification | text null | CHECK required when status = closed (ER) |
| closed_at | timestamptz null | |
| closed_by_membership_id | uuid null | |
| created_by_membership_id | uuid null | |
| source, external_id, synced_at | | rule 9, unique `(tenant_id, source, external_id)` |
| created_at, updated_at | timestamptz | |

Indexes: `(tenant_id, register_id)`, `(tenant_id, status)`, `(tenant_id, owner_membership_id)`,
`(tenant_id, residual_score)`, `(tenant_id, next_review_on)`, `(tenant_id, category_id)`.
Upper bounds of the four scores are checked in the service against the register's levels.

### risk_control_map (tenant owned)

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid | |
| risk_id | uuid fk risks cascade | |
| control_id | uuid fk controls restrict | controls are never deleted (rule 6) |
| created_by_membership_id | uuid null | |
| created_at | timestamptz | |

Unique `(tenant_id, risk_id, control_id)`; index `(tenant_id, control_id)`.

### risk_acceptances (tenant owned)

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid | |
| risk_id | uuid fk risks cascade | |
| status | text | CHECK pending, active, rejected, withdrawn, expired, revoked |
| rationale | text | |
| expires_on | date | |
| requested_by_membership_id | uuid null | |
| approver_membership_id | uuid null | ER `approved_by`; CHECK differs from requester |
| residual_score_at_request | int null | what was accepted |
| decided_at | timestamptz null | |
| decision_note | text null | |
| revoked_at | timestamptz null | |
| revoked_by_membership_id | uuid null | |
| revoke_reason | text null | |
| created_at, updated_at | timestamptz | |

Partial unique `(tenant_id, risk_id) WHERE status IN ('pending','active')`; index
`(tenant_id, status, expires_on)`.

### risk_events (tenant owned)

The risk's own history, like `asset_transitions`. The platform `audit_log` row is written as well.

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid | |
| risk_id | uuid fk risks cascade | |
| kind | text | CHECK, see §2.6 |
| from_value, to_value | text null | |
| note | text null | |
| inherent_score, residual_score | int null | snapshot for score history |
| actor_membership_id | uuid null | null = the system |
| created_at | timestamptz | |

Index `(tenant_id, risk_id, created_at)`.

### risk_templates (global content)

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| code | text unique | `RL-TEC-001` |
| title, description | text | |
| category, sub_category | text | default taxonomy names |
| default_likelihood, default_impact | smallint | 1..5 |
| root_cause, consequences, recommendations | text null | |
| treatment | text null | |
| control_keys | jsonb | SOC 2 control template canonical keys |
| frameworks | jsonb | labels |
| built_in | bool | ER |
| created_at, updated_at | timestamptz | |

App role holds SELECT only; the seed loader writes it on the owner connection.

## 2. Rules

1. **Scale.** A score value must be within 1..levels of the risk's register. A partial pair is refused.
2. **Band.** `band(score)` is the highest band whose `min_score <= score`. The effective band of a risk
   is its residual band, else its inherent band, else none (unscored).
3. **Status transitions** (served to the client):
   open → in_treatment, mitigated, closed · in_treatment → open, mitigated, closed ·
   mitigated → in_treatment, closed · accepted → closed (and to open only by revoke or expiry) ·
   closed → open (reopen, note required). `accepted` is never a manual target.
4. **Closure** needs a justification; reopening clears `closed_at` and keeps the justification in history.
5. **Acceptance.** Request needs approver (not the requester), rationale, a future expiry, and no other
   pending or active acceptance. Approve sets active, stamps `decided_at`, moves the risk to accepted.
   Reject and withdraw leave the risk as it was. Revoke and expiry move an accepted risk to open.
6. **Event kinds:** created, updated, scored, status, treatment, owner, control_linked,
   control_unlinked, linked, unlinked, action_added, acceptance_requested, acceptance_approved,
   acceptance_rejected, acceptance_withdrawn, acceptance_revoked, acceptance_expired, reviewed,
   imported, adopted, promoted.
7. **Attention** (computed): no_controls (not closed or accepted, zero controls), review_overdue
   (next_review_on before today, not closed), treatment_overdue (treatment_due_on before today, open or
   in_treatment), unscored (no inherent score), unowned, acceptance_expiring (active, expires within
   30 days), acceptance_pending.
8. **Matrix edits.** Levels may shrink only when no risk in the register holds a larger value.
   Bands must be ascending with the first at 1.
9. **Categories.** Saving the taxonomy diffs by id: new rows are created, renamed rows updated, missing
   rows deleted when unused and archived when in use. A risk's sub-category must belong to its category.
10. **Default register.** Created on first read of the registers list with a 5×5 matrix, the default
    bands and the default taxonomy. Exactly one default per tenant.

## 3. API (`/api/v1/risks`)

Static paths precede `/{risk_id}`.

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | /registers | read | list, ensures the default |
| POST | /registers | configure | create (default taxonomy copied) |
| GET | /registers/{id} | read | register with matrix and taxonomy |
| PATCH | /registers/{id} | configure | name, type, description, owner, matrix, bands, cadence, default, status |
| PUT | /registers/{id}/categories | configure | save the taxonomy tree |
| GET | /summary?register_id | read | tiles, heatmaps, breakdowns, top risks |
| GET | /facets?register_id | read | filter counts |
| GET | "" | read | list with filters and sort, paged |
| GET | /export?register_id&format | read | csv or xlsx |
| GET | /import/template?register_id | manage | xlsx with dropdowns |
| POST | /import/preview | manage | multipart file → normalised rows with errors |
| POST | /import | manage | rows → created count |
| POST | /assist | manage | AI draft for the form |
| GET | /library | read | global templates with adopted flag |
| POST | /library/adopt | manage | copy templates into a register |
| GET | /refs?search | read | lightweight picker for other modules |
| GET | /link-options?type&search | read | picker rows for assets, vulnerabilities, evidence, tasks, vendors, documents |
| POST | /from-vendor-finding | manage | promote a vendor finding |
| POST | "" | manage | create |
| GET | /{id} | read | detail with controls, links, actions, acceptances, history |
| PATCH | /{id} | manage | edit fields and scores |
| POST | /{id}/status | manage | transition, close, reopen |
| POST | /{id}/review | manage | mark reviewed |
| POST | /{id}/controls | manage | link controls |
| DELETE | /{id}/controls/{control_id} | manage | unlink |
| POST | /{id}/links | manage | link a record |
| DELETE | /{id}/links/{link_id} | manage | unlink |
| POST | /{id}/actions | manage | create a treatment task |
| POST | /{id}/acceptances | manage | request |
| POST | /{id}/acceptances/{aid}/decision | approve | approve or reject (named approver only) |
| POST | /{id}/acceptances/{aid}/withdraw | manage | requester withdraws |
| POST | /{id}/acceptances/{aid}/revoke | approve | revoke an active acceptance |

## 4. Interface

- **Navigation.** Risks becomes live at `/risks`.
- **Module header.** Title, register switcher (remembered), Import, Export, Add risk.
  Tabs: Overview · Register · Library · Settings, plus Assessments and KRIs marked Soon.
- **Overview.** Attention tiles linking to filtered register views; inherent and residual heatmaps
  with clickable cells; top risks; treatment status; by category. Soon cards for appetite, snapshots
  and reports.
- **Register.** Search and facets (status, band, category, treatment, owner, business unit,
  attention), sortable table (code, title with category, inherent, residual, status, treatment, owner,
  controls, next review), column picker, row menu.
- **Risk form (popup).** Two column wide dialog. Left: title with AI Assist and its suggestion panel
  (apply per field or all), description, root cause, consequences, recommendations, treatment and
  treatment plan. Right: register and type, category, sub-category (follows category), status,
  business owner, business unit, linked assets, inherent and residual scales with live score and
  band, treatment due, next review. Custom fields marked Soon.
- **Risk detail.** Header with code, status, band chips and "No controls" warning; actions Edit,
  Request acceptance, Mark reviewed, Close or Reopen. Tabs: Overview (narrative and matrix position),
  Treatment (decision, plan, actions as tasks), Controls, Links (assets, vulnerabilities, evidence,
  issues and tasks, vendors, documents), Acceptance, History; Assessments and KRIs marked Soon.
  Side rail: details and the score card.
- **Library.** Search and category filter, multi select, add to register.
- **Settings.** Registers list; register dialog; matrix and bands editor with live preview;
  taxonomy editor; Soon rows for custom fields, scoring formula, approval workflow, permissions.
- **Import dialog.** Download template, upload, preview with row errors, import valid rows.
- **Vendors.** Findings get Promote to risk; a promoted finding links to its risk.

## 5. Deviation register

| # | ER or spec | Built | Why |
|---|---|---|---|
| D1 | `RISK_MATRIX_SETTINGS` keyed by tenant | matrix columns on `risk_registers` | R1 |
| D2 | `RISKS.category` text | `category_id`, `sub_category_id` rows | R10 |
| D3 | status open, accepted, closed | adds in_treatment, mitigated | R4 |
| D4 | `risk_source` | `origin` plus the integration triple `source` | rule 9 needs `source` |
| D5 | `origin_id` | `origin_ref` plus `template_id` fk | library ancestry is a real fk |
| D6 | `RISK_ACCEPTANCES` status active, expired, revoked | adds pending, rejected, withdrawn | R6 needs a request state |
| D7 | `approved_by` | `approver_membership_id` plus `requested_by_membership_id` | R6 |
| D8 | not in ER | `risk_registers`, `risk_categories`, `risk_events` | multiple registers, taxonomy, history |
| D9 | not in ER | root_cause, consequences, recommendations, treatment_plan, department_group_id, treatment_due_on | product owner field list |
| D10 | APPROVALS generic record | acceptance decision on `risk_acceptances` | the generic approvals module is an empty stub; Phase 2 workflow engine replaces this |
