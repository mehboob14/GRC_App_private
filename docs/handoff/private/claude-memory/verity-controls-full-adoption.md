---
name: verity-controls-full-adoption
description: Every Verity tenant auto-adopts all 114 SOC 2 controls; evidence control-picker sources tenant controls grouped by criterion
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-17T12:10:30.160Z
---

Product decision (2026-08-17): every tenant starts with the **full SOC 2 control
library adopted** — all 114 controls / 61 criteria / 150 mappings — so there is
something to scope, own and evidence from day one (Vanta/Drata pattern).

**How:** `iam.service._adopt_control_library()` calls
`control_service.instantiate_library(tenant_id, actor)` (idempotent) from both
tenant-setup paths — `signup` and `invite_admin` (provider path). Existing
tenants were backfilled once via `backend/scripts/backfill_adopt_soc2.py`
(idempotent; 8 tenants adopted, the crosstab test tenant already had it).

**Evidence "Add evidence" control-linkage picker**
(`frontend/src/features/evidence/components/control-picker.tsx`) sources
**tenant-adopted controls** (`controlsApi.list`) grouped by criterion — NOT the
global template catalog. Searchable combobox, criteria headers labelled
`CODE · name` (needs `complianceApi.listRequirements`), rich rows, chips.

A backend restart is required to activate the signup/invite auto-adoption for
NEW tenants (the picker + existing tenants work without it).

**Controls page CRUD** (`features/compliance/components/controls-page.tsx` +
`control-form-dialog.tsx`): New-control (internal, `origin=custom`) + edit-any +
disable-with-reason. Source shows Internal vs SOC 2; disabled controls stay
visible with derived status "Disabled" (list uses `include_disabled:true` under
query key `["controls","all"]`). Link-to-asset / link-to-risk are "coming soon"
placeholders (assets/risk modules are empty stubs).

**Control codes (2026-08-17):** the 114 SOC 2 controls use category-based codes
`<ABBR>-<NN>` — IAM/GRC/HR/NS/DM/SD/LM/BC/CS/EP/PE (e.g. `IAM-01`), NOT the old
descriptive slugs. Regenerate with `scripts/recode_soc2_controls.py` (numbers
within a category by `canonical_key`, deterministic); tenant-side rename is
migration `d1f4c8a9b370`. That migration must lift `FORCE ROW LEVEL SECURITY` on
`controls` for its UPDATE — a migration runs as owner with no tenant bound, and
FORCE applies to the owner too, so without it the UPDATE silently matches 0 rows.
The seed loader now keys control templates on `canonical_key`, not `code`
(keying on code turns a re-code into delete+insert, which the adopted-controls FK
refuses).

**Landmine:** `controls` columns `category` / `control_type` / `control_sub_type`
are DB CHECK-constrained (`CONTROL_CATEGORIES` 11 values, `CONTROL_TYPES`
Preventive/Detective/Corrective, `CONTROL_SUB_TYPES` Manual/Automated/Hybrid).
Any create/edit form MUST source these from `controlsApi.vocabulary()` selects —
free text (e.g. category "Access control") returns a masked 500 (CheckViolation).
The domain sub-types the client wants (HR/Cloud/CI-CD) are NOT storable without a
migration. Relates to [[verity-grc-platform]] and [[verity-design-reskin]].
