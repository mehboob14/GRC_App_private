---
name: verity-spec-gap-2026-10
description: "2026-10-03 static audit of Verity against the signed spec (3 phases, 7 deliverables) and the 8 week plan: what is built, partial, open; Phase 1 exit criteria status; decisions still pending"
metadata:
  node_type: memory
  type: project
  originSessionId: 6ccef17a-c871-4bbb-87d0-d988eb0d9721
  modified: 2026-10-03T17:15:42.039Z
---

Five read-only code audits (nothing run) on 2026-10-03, biggest claims re-checked by hand. Re-verify before relying on a line; this goes stale as work lands.

Headline: Phase 1 is built and deployable but not sign-off clean (about 30 open clauses). Phase 2 is 1 of 15 connectors plus approvals. Phase 3 is placeholders plus framework engine groundwork. Nothing from the spec's out-of-scope list was built. Phase 2 and 3 are priced separately per the build plan, so they are next-up, not overdue.

Phase 1 exit criteria: workspace end to end passes (Types/Sub-types empty, sidebar /dashboard is mock); isolation test passes in CI; each object end to end + four hop trace is partial (tasks and documents have zero tests, no trace view, control page shows no risks or policies, task edits not audited); deploy + migrations fine but backup/restore never demonstrated (no script, no drill, runbook tars `minio-data` while evidence lives on `evidence-data`), no /metrics.

Open Phase 1 clauses worth remembering: tenant admin MFA defaults off; spec roles (Compliance manager, Control owner, Employee, Auditor) not built-in and `EngagementScope` wired to no route; no rate limit on auth endpoints; no readiness snapshots; PDF is a browser print; no audit export; no retention config or legal hold; no auto renewal task for stale evidence; no task recurrence/severity/attachments; no Change Management or Acceptable Use template; document review dates cannot be set from the UI; no ack reminders or completion export; no SIG/CAIQ/ISO Annex A/DPA questionnaires; XML scan upload refused by the storage sniffer (service.import_file stores before parsing), no PDF or AI parsing; asset form drops owning team and has no tier override control; provider plane has no UI.

Phase 2: framework hard-wired to GitHub (PROVIDERS=("github",) + DB CHECK), 7 of 81 checks run, no findings/waivers/alerts/digest/AI drafting/Jira/Slack. Phase 3: RCSA, assessments, incidents, KRIs, appetite are "Soon" screens; SSO, access reviews, CIS, live scanners absent; auditor access is a time boxed guest invite only.

Pending decisions (proposed readings given to the user): add the five spec roles as built-ins; Type = the 11 control domains, Sub-type = system; SIG is licensed content (CAIQ free, Annex A and DPA can be authored); "trial" is only a plan label.

Related: [[verity-evidence-composition]], [[verity-common-control-framework]], [[verity-connectors-github]].
