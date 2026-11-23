---
name: verity-risk-settings-live
description: Risk register settings made functional 2026-10-08 : scoring formula, appetite per category, custom fields; migration 7c3e91d2a8f4 swaps generated score columns for a trigger
metadata:
  type: project
---

Custom fields (tenant-wide, scope `risks`, form/detail/register facets/import columns), scoring formula (product|additive|weighted, per register) and risk appetite (appetite+tolerance per top-level category) are live in Risk > Settings.

**Why it matters:** `risks.inherent_score/residual_score` are no longer generated columns. Trigger `trg_risks_scores` reads `risk_registers.scoring_formula` via SQL fn `risk_score`; changing the formula runs a self-assign UPDATE to refire it and resets bands to defaults. Frontend must use `features/risk/scoring.ts scoreOf`, never `l * i`.

**How to apply:** deploy needs migrate (deploy.sh does it). Custom field filters only cover choice/yes-no fields; export has no custom columns. Library pages still use fixed 5x5 product. Checks run: ruff, mypy, import-linter, tsc, eslint, unit (1110), risk integration file; no live browser check.
