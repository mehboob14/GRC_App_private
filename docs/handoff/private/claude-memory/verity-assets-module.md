---
name: verity-assets-module
description: Asset management module — built (frontend on mocks + backend), and given a tasks-parity UI/UX pass (⋯ menus, split-free register, scanner-integration + linkage "Soon")
metadata:
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-09-03T18:45:21.302Z
---

Asset management in C:\Development\Verity_GRC_Platform, `features/assets/` (frontend ON MOCKS — api.ts→mock.ts direct, like tasks pre-wiring) + a backend assets module (Alembic head `a7d2e9f10b34`). Files: api.ts, mock.ts (9 seed assets), tokens.ts, types.ts, components/(assets-register-page, asset-detail-page, asset-form-page, assets-import-page, assets-layout, assets-overview-page). Routes: /assets (register), /assets/overview, /assets/import, /assets/new, /assets/:id, /assets/:id/edit. Lifecycle `ASSET_STATUSES` = planned→active→in_maintenance→decommissioned→retired (transitionAsset + allowed_transitions served; decommission has its own dialog/record). Criticality = CIA (1-5) → tier; unrated shows `NEEDS_ASSESSMENT`. Cross-module links via `a.links` + `linked_summary: Record<LinkTarget,number>`; asset↔asset deps via the Relationships tab (addRelationship/deleteRelationship). CSV import exists: `assetImportTemplateCsv()` + `importAssets()` + a client-side CSV parser/preview.

**MOCK → REAL BACKEND SWAP (2026-09-03) — the assets frontend now calls the API.** Root cause of a reported bug ("no assets in the vulnerability Add-finding asset dropdown even though assets exist"): `features/assets/api.ts` was Phase-A mock-backed (never imported `apiFetch`), so assets created in the UI lived in an in-memory `STORE` and never reached Postgres — while `vulnerabilities/api.ts:listAssetOptions()` reads the REAL `GET /assets`. Endpoint + shape were fine; the table was simply empty. Swapped 11 functions to `apiFetch`: listAssets (array facets go over the wire as REPEATED keys `?tiers=a&tiers=b`; param is `page_size`, snake_case), getAsset (404 → `null` via `ApiError.status`), getFacets, getSummary, listMembers (**served by IAM `GET /members`, needs `members:read` — an assets-only role sees empty owner pickers**; maps `full_name`→`name`), createAsset, updateAsset (PATCH but a FULL REPLACE server-side — always send every field), transitionAsset, recordReview, importAssets (`POST /assets/import` body `{rows: AssetWrite[]}`), decommissionAsset. Deleted the dead mock helpers (toRow/matches/compare/criticalityFrom/ownershipFrom/bulkCreate). This one diff also fixes BOTH linkage directions: the asset-detail Vulnerabilities tab now passes real asset ids to `listVulnerabilities`, and `vuln_count` now reads the value the backend already computes (`assets/service.py` `_vuln_counts()` → `open_counts_by_asset()`), instead of the mock's hardcoded 3/5/1.

**Gaps this exposed (still open):** (1) **`AssetWrite` has `extra="forbid"`** — owner fields must be renamed `*_id`→`*_membership_id` (done in `writeBody()`), and **`owning_team` cannot be sent**: the API wants an `owning_team_group_id` (group UUID) but the form collected a free-text name, so the field was REMOVED from asset-form-drawer rather than silently dropped — it needs to come back as a group picker. (2) **links / relationships / linked_summary do not exist on the backend** (no table, no endpoint; `relationship_count` and `link_count` are hardcoded 0 in `assets/service.py`) — `getAsset` synthesizes empty collections via `withEmptyLinks()`, and `addRelationship`/`deleteRelationship` now THROW "Asset relationships aren't available yet." (3) `watchers` is always `[]` server-side. (4) `mock.ts` is retained ONLY for the pure helpers `computeCriticality`/`isHighImpact`/`effectiveTier` that power the form's live criticality preview — its seed `STORE` is now dead weight and should be split out. (5) Assets saved views were removed from the UI this session, so `listSavedViews`/`SavedView`/`AssetFilters.needs_attention` were deleted too (no backend existed for them either). Verified: tsc(-p tsconfig.app.json) + eslint + `npm run build` clean; NOT verified live (preview-browser login still blocked).

**ASSETS UI/UX PASS — DONE & VERIFIED LIVE (2026-08-31), tasks-parity.** (1) **Register** rewritten: dropped the fluff subtitle; compact toolbar (search left, Import + New asset right, NO button icons); KPI strip stays (Total/Critical/Need CIA/Regulated/Stale); filters on their own wrap row; saved-views conditional. Added an **Actions column** (last `<TH className="w-10"/>`) with a per-row **⋯ DropdownMenu** (View details, Edit) — the `<TD onClick stopPropagation>` so ⋯ doesn't trigger the row's navigate. "— assess" em-dash → "Not rated" (register CIA + criticality cells). (2) **Detail header** → ⋯ menu (like tasks): primary lifecycle transition stays a button, Edit + other transitions fold into ⋯ (decommission/retire = danger variant); removed the Edit gear icon. (3) **Import page** → two-path layout: "Upload a CSV" card (Download template [already existed] + Choose CSV, icon-free) + a dashed **"Connect a scanner"** card marked **Soon** listing Tenable Nessus / Qualys / Microsoft Defender / AWS Config (automated-discovery placeholder). Removed the check icon in the preview Ready state. (4) **"Linked" tab → "Related"** (`LinkedTab`): shows existing links (grouped, icon-free) + a per-module list (Controls/Risks/Vulnerabilities/Evidence/Documents) showing `{n} linked` or **Soon** — reflects that vuln/risk/control linkage arrives with those modules. Removed `LINK_ICON`/`IconName`. (5) Em-dash fixes: `NEEDS_ASSESSMENT.label` "— assess"→"Not rated" (tokens.ts) + asset-form-page. tsc+eslint(all src) clean.

**DEV ENV (this Win+WSL machine, recurring)**: WSL idle-terminates between sessions → Postgres(5433)+Redis(6379) drop AND the Windows→WSL localhost port-forwards drop (API readyz 503, WinError 1225). Fix: run a persistent `wsl -d Ubuntu -- sleep infinity` in the BACKGROUND to hold the forwards, confirm with `Test-NetConnection 127.0.0.1 -Port 5433`, THEN restart the API so it gets a fresh pool. vite(5173)+API(8001) also die between sessions — restart both via Start-Process (see [[verity-tasks-module]] for exact cmds). Login as mehboobarshad300@gmail.com / boobhem@007 (Admin) + inject session into sessionStorage for the preview browser.

**Asset dependencies built (2026-09-24, uncommitted):** migration `b3f7c81e5d24` adds
`asset_relationships` (source/target/type/provenance + Integratable, RLS, unique edge, no self
edge). Service `relationships` / `add_relationship` / `remove_relationship`; the edge is stored
once and read from either end (`direction` computed per asset), removable from both. Routes
`GET|POST /assets/{id}/relationships`, `DELETE .../{rel_id}`; the detail view carries
`relationships`. Frontend api.ts stubs that threw are now wired, and the inbound label uses
`INVERSE_LABEL` ("hosts", not "is runs on by"). The Vulnerabilities tab (Add/Link finding) and the
Linked records panel were already working: complaints about them were a stale browser bundle.

**Dependencies are real (2026-09-24, commit 306a8e2):** `asset_relationships` (migration
`b3f7c81e5d24`) stores one row per edge and reads it from both ends, so the inverse can
never disagree; `direction` on the write decides which end is the source. The Relationships
tab used to reach a client stub that threw, which is what the user saw as "try again, or
contact support". `provenance` (declared vs discovered) and the `source`/`external_id`/
`synced_at` columns are there for the discovery connector that fills this next. The Linked
records tab is no longer "Soon": it runs on [[verity-linkage]]. Adding a vulnerability from
an asset prefills that asset.

**Inventory settings (2026-09-24, commit 77ee629):** Assets > Settings holds the review
cadence per criticality (`asset_policies`, one optional row, `DEFAULT_REVIEW_DAYS_BY_TIER`
in code is the default, 7 to 1095 days) and the custom fields card. `compute_hygiene` now
returns the window it judged against as a fourth value, and the hygiene panel lists all five
checks met or unmet rather than only the failures, because "100% complete" alone told the
reader nothing about what was counted.
