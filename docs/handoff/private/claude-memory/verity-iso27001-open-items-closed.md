---
name: verity-iso27001-open-items-closed
description: "2026-10-16..19 ISO open items closed (uncommitted): compliance-auditor persona review, 300-mapping crosswalk, wording migration, 30 templates, 30 built-in Verity checks, code review fixes, guide shots; open owner decisions"
metadata:
  node_type: memory
  type: project
  originSessionId: 39419d38-57d3-4967-bef0-8210df94f40c
  modified: 2026-10-18T20:16:40.421Z
---

Follow-up to [[verity-iso27001-built]]. User asked to close the ISO open items with a reviewer agent who knows ISO 27001, PCI DSS, banking and on-prem audits. All built and verified, NOT committed (needs the user's go; commit with `local-context/tools/commit_paths.py`, see [[feedback-commit-attribution]]).

**Reviewer.** `compliance-auditor` agent: `local-context/agents/compliance-auditor.md` (copy in `~/.claude/agents/`). Its review is an internal persona pass: never call it independent or accredited in public copy; FW-5 (second qualified person) stays open.

**What landed.** Crosswalk 300 mappings (47 full / 253 partial), 17 new ISO controls (PE-03 own-site environment, payment device inspection), 10 evidence lists widened, A.5.34 allowed 7 controls in `test_iso27001_pack.py`. Wording migration `e3a91c5d7b20` (60 controls, edited copies kept; regenerate with scratch `regen_wording_migration.py` if SOC 2 text changes again). 15 Verity templates (30 total). Built-in checks: `connectors/verity.py`, provider `verity`, migration `f6c2b8e4a915` (head), 30 checks, hourly worker ensures the connection. Code review: 20 findings fixed (staff-wide code of conduct ack minus guest auditors, severity raise shortens SLA, readiness excludes source `verity`, not-applicable controls don't mitigate, 12-month floors, DPA signed copy, bounded evidence files, per-tenant worker guard). Guide: 7 new shots from a second demo workspace (`tools/demo_session.shots.json`).

**Open for the owner.** Ack population (all active members minus guests?), SLA anchor on severity raise (first detection built), ISO on which plans (website), website SOC 2 counts wait for the 116 pack on feat/website-deploy, no ISO backfill for controls shipped after a workspace added ISO.

**How to apply.** Before claiming numbers, recount from the pack files. Deploy order unchanged: migrate then seed-content; readiness will drop where built-in checks fail.
