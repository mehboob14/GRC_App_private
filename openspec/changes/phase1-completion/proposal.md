# Phase 1 completion: the five open items

Checked against the signed spec (`docs/product/SOC2-Compliance-Platform-Requirements-Specification
Document.docx`) and the 8 week build plan (`docs/SOC2-Platform-Phase1-Build-Plan-8-Weeks.docx`).
Phase 2 and 3 are out of this change.

## Reading taken

The product owner listed five items after the 2026-10-03 spec audit. Those five are this change.
The rest of the Phase 1 gaps from that audit are **not** in it and stay open (listed at the end), so
nothing here widens beyond what was asked.

## The five items and what "done" means

| # | Item | Spec words | Done when |
|---|---|---|---|
| 1 | Login rate limit | §9 "rate-limits requests"; week 1 "secure authentication" | The eleventh login attempt for one account inside the window gets a 429 with a retry time; MFA verify, signup, password reset and provider login are limited the same way; other accounts are unaffected |
| 2 | Tasks | §1.1 "severity ... SLA level, and recurrence; recurring tasks can require approval"; "every transition ... can attach evidence or notes"; "evidence past [its validity] is flagged stale with a renewal task created automatically" | A stale evidence item gets one renewal task by itself; a task can be created with severity and a repeat rule and spawns its next occurrence; a repeating task can require approval; a transition can carry attached evidence or a file |
| 3 | Type and Sub-type | §1.1 "Every control carries a Type and a Sub-type column ... filtered, grouped, and owned domain by domain"; week 2 "Type and Sub-type filters" | All 116 shipped controls show a Type and a Sub-type in the register and detail, the register filters and groups by both, and a custom control can set them |
| 4 | Provider plane UI and branding | Week 1 "internal admin panel to register, brand, and provision each tenant"; §9 "per-workspace branding, white-label ready" | A platform admin signs in (with TOTP), registers a tenant, sets its branding, runs provisioning and invites the first admin from screens, and a tenant's own screens then show that logo, name and colour |
| 5 | Dashboard live | §1.1 "posture dashboard ... health"; week 3 "readiness dashboards" | The sidebar Dashboard shows the workspace's own numbers for every tile it draws, and no tile is fabricated |

## Round 2 (2026-10-06)

Three more items from that list, built after the first five: the trace view and the risks and policies
on the control page, the audit export, and review dates with acknowledgement reminders (plus the
completion export that sits in the same spec sentence). Plus one script to deploy and one to back up.

## Not in this change (still open for Phase 1)

Tenant admin MFA default, the spec's five roles and their scoping, evidence retention and legal
hold, readiness over time, branded PDF, criteria colouring view and renewal queue, Change Management
and Acceptable Use templates, SIG / CAIQ / ISO / DPA questionnaires, scan ingest (XML upload, PDF,
AI parsing), the asset form gaps, a demonstrated restore (the backup script exists, the drill does
not), the metrics endpoint, and tests for evidence and controls.
