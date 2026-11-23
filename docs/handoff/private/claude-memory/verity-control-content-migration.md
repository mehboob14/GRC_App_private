---
name: verity-control-content-migration
description: "Shipped control text is changed via an Alembic data migration; tenant copies need a FORCE-RLS lift before the read, not just the write"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-24T08:53:25.700Z
---

All 114 shipped SOC 2 controls carry a statement (why the control exists) and
four newline-separated implementation steps, which the UI's `Guidance` component
renders as bullets. Written to a consistent professional depth on 2026-08-24,
replacing one-line guidance (111 of 114 were under 160 chars) and some casual
probo-imported prose. Deployed as migration `a4c81f37b902`.

**Changing that text takes a data migration, not just a seed edit.** The seed
loader upserts `control_templates`, but each tenant's `controls` row is a copy
made at adoption and nothing re-syncs it. Pattern that works (see
`20260824_1000_control_guidance_rewrite.py`):

1. Lift FORCE RLS on `controls`.
2. Capture "unedited" rows — those still equal to their template — into a temp
   table. This must happen *before* the templates move, since that equality is
   the definition of unedited. Preserves tenant customisation.
3. Update `control_templates` from the embedded new text.
4. Propagate template text to the captured rows; restore FORCE RLS.

**The trap:** FORCE ROW LEVEL SECURITY filters `SELECT`, not just writes, and it
applies to the owner role a migration runs as. Lifting FORCE only around the
UPDATE means step 2's read silently returns zero rows and the backfill updates
nothing — with no error. This was caught only by testing the *downgrade*; the
upgrade looked fine because the rows had already been backfilled by hand. Always
test a data migration by first resetting rows to the pre-state.

Match old text to new by `canonical_key`, never by `code`: the GRC-NN → GOV-NN
re-code means codes are not stable across versions.

Related: [[verity-deploy-runbook]], [[verity-control-library-provenance]]
