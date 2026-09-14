# Tasks: risk register

Each task is at most two hours. Tables are the blocks in `design.md` §1; rules are §2.
Integration and isolation tests run against `verity_test` only.

## 0. Plan

- [x] 0.1 Read the signed spec (1.2, 1.3 trace, Phase 3 ERM), ER 3.6 and 3.12, GRC-Tenant's ERM
      model and risk form, Vanta Risk and Drata Risk Management.
- [x] 0.2 proposal, design (build reference and deviation register), decisions R1 to R16.
- [x] 0.3 `docs/product/risk-management-requirements.md`: the ERM requirements for later phases.

## 1. Schema

- [x] 1.1 Models for the seven tables in `modules/risk/models.py`.
- [x] 1.2 Migration `b6d2e8f41a37`: tables, generated scores, checks, indexes, RLS and grants, SELECT
      grant on `risk_templates`, four permission keys, the `vendor_findings.promoted_risk_id` foreign
      key, notification kinds (risk kinds plus the two vendor kinds the constraint was refusing).
      Upgrade, downgrade and upgrade verified on `verity_test`.
- [x] 1.3 Content pack `risk_library` (60 Verity authored risks, suggested SOC 2 controls) and the
      loader section for `risk_templates`.

## 2. Service

- [x] 2.1 Registers: ensure default, create, update matrix and bands with the shrink guard, taxonomy save.
- [x] 2.2 Risks: create, update, scale validation, bands, codes, events and audit.
- [x] 2.3 Status transitions, close and reopen, mark reviewed.
- [x] 2.4 Controls map; links to assets, vulnerabilities, evidence, tasks, vendors, documents with
      label resolution through their services; treatment actions as tasks.
- [x] 2.5 Acceptances: request, decide, withdraw, revoke; expiry sweep.
- [x] 2.6 List with filters and sort, facets, summary with heatmaps and attention.
- [x] 2.7 Library listing and adoption with control linking.
- [x] 2.8 Import template, preview, commit; export CSV and Excel.
- [x] 2.9 AI assist with the library fallback.
- [x] 2.10 Vendor finding promotion (`vendor_service` marks the finding).
- [x] 2.11 Form options (owners, business units) under `risks:read`, so the form needs neither the
      members nor the groups permission.

## 3. HTTP and jobs

- [x] 3.1 Schemas and router, static paths first, a permission on every route.
- [x] 3.2 Daily job `sweep_risk_register`: expire acceptances, notify overdue reviews. Beat entry.

## 4. Tests

- [x] 4.1 Unit: bands, default bands by size, transitions, import normalisation, assist ranking,
      library taxonomy (20 tests).
- [x] 4.2 Integration through the app: every read route reachable, the lifecycle (create, score,
      link control, treat, request, approve, expire reopens), close and reopen, taxonomy rules,
      matrix shrink guard, second register, import preview and commit, template round trip, library
      adoption, assist fallback, promotion (12 tests).
- [x] 4.3 Isolation: the six tenant tables under the four properties (5 tests).

## 5. Frontend

- [x] 5.1 Types, API client, tokens (status, band, treatment, register type), nav and routes.
- [x] 5.2 Module layout with register switcher, export menu, tabs and Soon tabs.
- [x] 5.3 Register page.
- [x] 5.4 Risk form popup with AI assist, dynamic subcategory, scales and linked assets.
- [x] 5.5 Risk detail page and its tabs.
- [x] 5.6 Overview with heatmaps.
- [x] 5.7 Library page.
- [x] 5.8 Settings: registers, matrix and bands, taxonomy, Soon rows.
- [x] 5.9 Import dialog and export.
- [x] 5.10 Promote to risk on vendor findings.

## 6. Verify

- [x] 6.1 ruff, mypy, import linter (17 of 17), eslint, tsc, vite build.
- [x] 6.2 Migrate and seed the dev database; every screen walked in headless Chrome with screenshots.

## Follow ups (not in this change)

- Wire the Soon linkage on other records: "Link risks" on the control form, a Risks card on asset
  and vulnerability detail pages (`GET /risks/refs` exists for the picker).
- Approve an acceptance from the notification bell, like document approvals.
- The Phase 2 and Phase 3 items in `docs/product/risk-management-requirements.md`.
