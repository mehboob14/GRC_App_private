---
name: verity-custom-fields
description: Tenant-defined fields on assets and findings — the customfields primitive, where values live, and what is deliberately not built
metadata:
  type: project
---

Built 2026-09-24 (commit 77ee629) for [[verity-assets-module]] and the vulnerabilities module.

`backend/src/verity/modules/customfields/` is a **primitive** like `modules/links`: models +
service, no router, no audit dependency. Primitives are absent from every import-linter
contract's `forbidden_modules`, so adding one needs no pyproject change — that is why this
shape was chosen over a full module.

- Definition: `custom_field_definitions` (tenant-owned, `object_type` in asset/vulnerability,
  `key` slugged from the first label and never renamed, six `field_type`s, JSONB options,
  required, position, `archived_at`). Archived, never deleted.
- Value: a `custom_fields` JSONB column on `assets` and `vuln_instances`. `clean()` validates
  and coerces before it lands, carries archived keys forward from `previous`, and rejects a key
  the tenant never defined.
- The audit row is written by the owning module's service (`asset_service.save_custom_field`),
  not by the primitive.
- Routes live under each module's prefix (`/assets/custom-fields`, `/vulnerabilities/custom-fields`)
  so each carries that module's permission; they are declared **before** `/{id}` or FastAPI
  matches "custom-fields" as an id.
- Frontend `features/custom-fields/` is shared: `CustomFieldsCard` (settings), `CustomFieldInputs`
  (form), `customFieldText` in `format.ts` (kept out of the component file for react-refresh).
  Assets collect values on the form; a finding collects them on the record
  (`PATCH /vulnerabilities/{id}/custom-fields`) because scanners fill the rest.

**Not built:** custom fields in filters, register columns, or import mapping.

Related: [[verity-vulnerabilities-module]], [[verity-ui-consistency-primitives]].
