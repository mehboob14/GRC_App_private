---
name: verity-linkage
description: "Cross-module linked records (360 linkage) for assets, vulnerabilities, controls and documents via backend modules/linkage + frontend features/linkage; uncommitted as of 2026-09-17"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-17T17:37:26.197Z
---

Backend `modules/linkage` (router, service, schemas) serves `GET/POST /{assets|vulnerabilities|controls|documents}/{id}/links`, `DELETE .../links/{link_id}` and `POST /vulnerabilities/{id}/raise-risk`. Pairs the risk register or evidence already own are drawn THROUGH `risk_service.link_record` / `evidence_service.link_record` so there is one edge per pair and their histories stay right; other pairs are generic `links` rows from the anchor. Reads filter by the caller's read keys; writes need manage on anchor + owner module. Raise risk scores impact from severity, likelihood from KEV/EPSS, links risk caused_by finding and relates_to asset.

Gotcha: routes built in a loop with `from __future__ import annotations` must pass `Depends(require(...))` as a default, not in `Annotated[...]`, or FastAPI treats the principal as a query param (422).

Frontend: `features/linkage` (api with per-type SEARCH, meta, hooks, LinkedRecordsPanel with filter chips and folded empty groups, LinkPickerDialog, RaiseRiskDialog) mounted on asset, vulnerability, control and document detail tabs. Asset Vulnerabilities tab gained Link finding + Add finding; vulnerability rail has always visible Affected assets and Risks panels. Fixed bug: link-asset response (new sibling instance) was painted onto the current finding page.

**How to apply:** new record pages reuse LinkedRecordsPanel + add an anchor in router `_ANCHORS` and service `OFFERED`/`AUDIT_TYPE`. Related: [[verity-risk-register]], [[verity-module-header-pattern]], [[verity-evidence-ai-linkage]].

Committed 2026-09-24 in 8301042 alongside the GitHub connector. Panels are live on the
asset, vulnerability, control and document pages.
