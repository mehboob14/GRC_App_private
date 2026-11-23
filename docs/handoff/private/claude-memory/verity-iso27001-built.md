---
name: verity-iso27001-built
description: "2026-10-10/11 ISO 27001 built end to end on the one control library (uncommitted): what exists, numbers, checks run, gotchas, which paths to commit, what is still open"
metadata:
  node_type: memory
  type: project
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-11T07:34:38.819Z
---

User asked for ISO 27001 "end to end now": a separate framework in Frameworks with its own scope, its controls beside SOC 2 in one library, connectors later. Built and verified, NOT committed or pushed yet (needs the user's go).

**What exists.** Migration `c5d8a2f7e91b` (down `7c3e91d2a8f4`): `frameworks.scope_model/position`, `tenant_frameworks` (SOC 2 backfilled for every tenant), `requirement_applicability` (reason CHECK), per-framework engagement. Sealed pack `seed/content/iso27001` (123 requirements, 16 new controls GOV-23..30, HR-09, CS-06, CS-07, LM-12, DM-18, DM-19, NS-12, EP-07, 242 mappings, id_only text). New backend: `framework_service.py`, `soa_export.py`, `tenant_framework_router.py`; every `/engagement*` takes `?framework=CODE` (default SOC2). Frontend: `frameworks-api.ts`, `use-frameworks.ts` (framework lives in `?framework=`), add-framework dialog, management-system-scope, statement-page (`/frameworks/soa`), switcher in frameworks-layout. Plan + built status: `docs/product/iso27001-plan.md` section 10.

**Numbers.** Workspace with all 116 SOC 2 controls: adding ISO answers 112 of 123 requirements, 11 need a new control, 100 controls gain links, 16 added, library 132. SOC 2 dashboard unchanged (asserted in `tests/integration/test_iso27001.py`).

**Checks run (2026-10-10).** 11 ISO integration + isolation tests pass, earlier SOC 2 regression 151 pass, unit 1113, ruff, mypy, import-linter 19 contracts, tsc, eslint; screens checked headless on the demo DB (`verity_guide`, API 8111, vite 5175, workspace "Northwind Software Ltd"). Statement states: met = all mapped controls ready, partly = some ready or started (in_progress/implemented), not_started otherwise.

**Gotchas.** `link_framework` must `flush()` first: adoption adds links with autoflush off, so the linker inserted the same pair twice (`uq_control_requirements`). Frameworks are ordered `(position, code)` so SOC 2 stays `[0]`. Killing the WSL keepalive (`wsl -d Ubuntu -u root -- bash -c "sleep 86400"`) takes Postgres 5433 and Redis down: restart before any DB test. `git diff --cached` must name the branch (`feat/phase1-completion`) or it diffs against the checkout's HEAD (codex/public-website).

**To commit.** Checkout is on codex/public-website: build the commit with a temp index on top of feat/phase1-completion (head 371f8a7), ISO paths only: the files listed in `git diff --cached --name-status feat/phase1-completion` under compliance, iso27001 pack, policies templates, loader, seal_content, migration 20261010, ai/mapping, iam/service, core/email, main, `__init__`, the 6 ISO tests plus test_control_sub_type and test_leads, THIRD_PARTY_NOTICES, iso27001 plan + csv, deployment runbook, common-control-framework tasks.md, and the frontend compliance files, routes, endpoints, types. Leave out website/*, add-public-website openspec, the risk settings popup files and AGENTS.md/README.md unless checked. No Claude co-author trailer (see [[feedback-commit-attribution]]). Deploy: migrate then seed-content, no backfill needed.

**Still open.** Second reviewer sign-off (FW-5), 26 controls with SOC 2 only wording (data migration), ISO document templates, platform tests for management system controls, user guide and website pages, connectors (AWS first). See [[verity-iso27001-plan]], [[verity-common-control-framework]], [[verity-multiframework-design]].
