---
name: verity-evidence-ai-linkage
description: Evidence module — AI-driven control-mapping suggestions + evidence↔task linkage, built to the Week-3 spec (both functional, real backend, verified live)
metadata:
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-31T11:27:23.784Z
---

Evidence in C:\Development\Verity_GRC_Platform is a **real-backend** module (`modules/evidence/`, `features/evidence/`, wired via `@/lib/api/endpoints` `evidenceApi`), unlike tasks/assets which were frontend-mock. Evidence↔control mapping is a bare `evidence_controls` join (no status/source); the review/approve pattern lives on the `Evidence` row (review_status/reviewed_by). See [[verity-grc-platform]].

**EVIDENCE AI MAPPINGS + TASK LINKAGE — BUILT & VERIFIED LIVE (2026-08-31), Week-3 spec ("AI powered mappings of any uploaded evidence to controls across frameworks").**

**Feature A — AI-driven control mappings** (suggests, never links; rule 11 draft→human-approve; rule 8 evidence-is-data-not-instructions):
- NEW `modules/ai/mapping.py`: `suggest_mappings(EvidenceContext, [ControlCandidate]) -> ([MappingSuggestion], source)`. Uses the LLM (`ai.llm.get_chat_model().ainvoke`) WHEN `settings.ai.api_key` is set (source="ai"), else a deterministic **term-overlap matcher** (source="heuristic") so it's functional offline. Any LLM/parse failure degrades to the heuristic. **The AI module was previously a bare traced client with ZERO consumers — this is the first thing that calls it.** No LLM key on this machine (`AI_API_KEY` commented in root `.env`, provider=openai) so it runs the heuristic; it correctly ranked IAM-03 (MFA) top for MFA evidence.
- `evidence.service.suggest_mappings()` (loads evidence + control_service.list_controls, excludes already-linked, returns `SuggestionView`s) + `approve_mapping()` (merges ONE control via map_controls replace=False — avoids the replace-race, audits control-side). Endpoints: `POST /evidence/{id}/suggest-mappings` + `POST /evidence/{id}/mappings/approve {control_id}` (both `evidence:manage`). NO schema change (suggestions ephemeral; approve reuses the join). NO new permission key.
- Frontend: `evidenceApi.suggestMappings/approveMapping`; the illustrative `SuggestedMappingsTeaser` component REWRITTEN → functional `SuggestedMappings` (Suggest button → rows with code/name/coverage/confidence/rationale + source badge AI/Suggested → Link[approve]/Dismiss). Types `MappingSuggestion(s)` in @/lib/api/types.

**Feature B — evidence↔task linkage** (reuses the `modules/links/` primitive — task+evidence are both in LINK_TYPES; link_service was fully built but had ZERO consumers):
- `evidence.service.linked_tasks/link_task/unlink_task` via `link_service.create/for_object/delete` (from_type="evidence" to_type="task"), resolving task titles through `task_service.get_task` (rule 4, N+1 for the few links — ponytail). link_service does NOT audit → evidence side writes the audit. Endpoints: GET/POST `/evidence/{id}/tasks`, DELETE `/evidence/{id}/tasks/{link_id}` (POST/DELETE=`evidence:manage`). `LinkedTaskView`/`LinkedTaskOut` = {link_id, task_id, code, title, status, task_kind}.
- **import-linter fix**: evidence→tasks.service opened a transitive reach (evidence→tasks.service→notifications.models etc.) breaking the evidence AND compliance contracts. Fixed by adding `"verity.modules.evidence.service -> verity.modules.tasks.service"` to BOTH contracts' `ignore_imports` in backend/pyproject.toml `[tool.importlinter]` (service→service is sanctioned; what tasks does internally is private). links.models isn't in any forbidden list so links needed no ignore. Now 17/17.
- Frontend: NEW `features/evidence/components/linked-tasks-section.tsx` (`LinkedTasksSection` + `LinkTaskDialog` picking a task via `listTasks` from features/tasks/api); added to the evidence detail after LinkageSection. `LinkedTask` type + `evidenceApi.linkedTasks/linkTask/unlinkTask`.

ruff+mypy+import-linter + tsc+eslint(all) clean. Verified live: suggest→Link IAM-03 appears in Controls; link TSK-0002 shows in the evidence Tasks section (idempotent). **RECIPROCAL NOT WIRED** (task's Related tab doesn't yet read the links primitive to show linked evidence — tasks link_count is still hardcoded 0; the DB edge exists bidirectionally). Test artifacts in mehboob tenant: evidence 01a05784-8ff0-7000-b898-15f4d50b80db ("MFA enforcement export…") linked to IAM-03 + TSK-0002. To enable real AI: set `AI_API_KEY` (+ optionally AI_PROVIDER/AI_MODEL) in root .env and restart the API.
