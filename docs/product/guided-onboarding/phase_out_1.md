# Phase out 1: guided onboarding work outside the signed phases

A running log of what is built for guided onboarding, set against the signed delivery plan
(`docs/product/delivery-plan.md`), so it can be priced or shared separately. It records scope and
effort, never prices.

The delivery plan says anything not listed in a phase "is scoped separately and agreed before any
work starts". On 2026-11-21 the owner agreed to proceed (decision D-1) and asked for this log.

How to read the "Signed?" column:

| Value | Meaning |
|---|---|
| Defect | Repairs something delivered in a signed phase. Not chargeable as new scope |
| Follows ISO | Needed because ISO 27001 (signed item 3.1) was delivered on the same engine, but not itemised in the plan |
| Extension | Not in any signed phase. To be priced or shared separately |
| Out of scope | Named as out of scope in the signed plan. Guidance only |

## Decisions taken

| Id | Decision | Date |
|---|---|---|
| D-1 | Proceed with guided onboarding; log work outside the signed phases here | 2026-11-21 |
| D-2 | A workspace may run ISO 27001 without SOC 2 (setup chooses frameworks; existing workspaces unchanged) | 2026-11-21 |
| D-3 | SOC 1 is a guidance page only: no engagement, no figures, no generated objectives | 2026-11-21 |
| D-6 | Shared scope items when both frameworks run, one statement each, provided both frameworks' rules allow it | 2026-11-21 |
| D-12 | A built in role that runs the programme without being Admin (Compliance Manager) | 2026-11-21 |

## Log

| # | Date | What | Signed? | Effort | Where |
|---|---|---|---|---|---|
| 1 | 2026-11-21 | Plan documents: official journey, requirements, experience, country reference, control library review, required documents, build spec | Extension | about 2 days | `docs/product/guided-onboarding/`, `openspec/changes/guided-onboarding/` |
| 2 | 2026-11-21 | Get Started: security only now counts as a categories decision | Defect | small | phase 1 |
| 3 | 2026-11-21 | Get Started: removed the footer saying connections arrive in a later phase | Defect | small | phase 1 |
| 4 | 2026-11-21 | Get Started: owner and evidence steps count every control instead of ticking on the first one | Defect | small | phase 1 |
| 5 | 2026-11-21 | Get Started loads for every built in role (it failed for every role but Admin) | Defect | small | phase 1 |
| 6 | 2026-11-21 | Get Started covers ISO 27001: framework chips, a lane per framework, scope statement and applicability steps, separate figures per framework | Follows ISO | about 1 day | phase 1 |
| 7 | 2026-11-21 | Status computed on the server (`GET /onboarding/status`), new module `onboarding`, step catalogue, risk and connection counts | Extension | about 1 day | phase 1 |
| 8 | 2026-11-21 | Skip a step with a reason, reopen it, both audited (table `onboarding_step_skips`) | Extension | about half a day | phase 1 |
| 9 | 2026-11-21 | Invite dialog opens from a link (`?invite=1`) | Extension | small | phase 1 |
| 10 | 2026-11-21 | Typed company profile: 33 questions in six sections (16 key), each saying what reads it; draft and confirmed states; frozen versions with history | Extension | about 1.5 days | phase 2 |
| 11 | 2026-11-21 | Country picker with all 249 countries, region groups, aliases and spelling tolerance | Extension | about half a day | phase 2 |
| 12 | 2026-11-21 | Source checks: ISO 27001 certification facts and the 26 first tier country entries (AI pass to help the human reviewer, not a legal review) | Extension | about half a day | research notes |
| 13 | 2026-11-21 | Built in Compliance Manager role (D-12), with a test that it never holds workspace administration or management approvals | Extension | small | iam |
| 14 | 2026-11-21 | Audit details for every framework: auditor or still deciding, contact, letter date, accreditation body, needed by, who asked, Type 1 as of date, ISO go live date; "Name your auditor" step on Get Started | Extension (the ISO fields follow ISO) | about 1 day | phase 3 |
| 15 | 2026-11-21 | Source checks: shared scope rules for SOC 2 and ISO 27001 (D-6), four remaining ISO certification points | Extension | about half a day | research notes |
| 16 | 2026-11-21 | Shared scope items with in or out decided per framework, reasons, auditor notices on changes; "What is in scope" on both scope pages | Extension | about 1 day | phase 3 |
| 17 | 2026-11-21 | Audit plan with milestones and a Get Started timeline, engagement cycles with history, customer commitments register, subservice organisations and suppliers per audit, scope suggestions from assets and vendors, changes in the SOC 2 period, turning a framework off with a reason | Extension | about 2 days | phase 3 |
| 18 | 2026-11-21 | Who owns what: eight owner functions, applied to every control with the internal audit warning | Extension | about 1 day | phase 4 |
| 19 | 2026-11-21 | Required documents page from Appendix A, drafts linked to their controls | Extension | about 1 day | phase 4 |
| 20 | 2026-11-21 | Fourteen new document templates drafted (unreviewed) and shipped | Extension | about 2 days of writing | content L3 |
| 21 | 2026-11-21 | Guidance on all 277 evidence items, 25 renames, 14 new items | Mixed: renames of sample items fix delivered content; guidance is extension | about 1 day | content L5 |
| 22 | 2026-11-21 | Plain word rewrites of the seven Openlane templates drafted, not shipped (D-5) | Defect fix to delivered content, pending legal read | about 1 day | content L1 |
| 23 | 2026-11-21 | Suggestions from the profile with accept, reject and review, through the owning services | Extension | about 2 days | phase 5 |
| 24 | 2026-11-21 | Baseline, readiness snapshot, work plan raised as tasks, evidence requests, connection suggestions | Extension | about 2 days | phase 5 |
| 25 | 2026-11-21 | Approved and frozen Statement of Applicability versions with download | Extension | about half a day | phase 5 |
| 26 | 2026-11-21 | Guided setup flow with Help me choose, sign up adoption behind a setting | Extension | about 1 day | phase 5 |
| 27 | 2026-11-21 | Fix: Required documents compared SOC 2 categories in the wrong case | Defect fix to this change's own work | minutes | phase 4 |
| 28 | 2026-11-21 | Country reference panel: 83 drafted entries for nine jurisdictions, matching, page, decisions; hidden until legally reviewed | Extension | about 3 days plus legal review | phase 6 |
| 29 | 2026-11-22 | Internal audits, management reviews, audit stages, past reports and certificates, graded findings raised as tasks | Extension | about 2 days | phase 7 |
| 30 | 2026-11-22 | SOC 2 description inputs, documents approved outside Verity, SOC 1 guide, check and audit steps on Get Started | Extension | about 1.5 days | phase 7 |
| 31 | 2026-11-22 | AI drafts for scope statement, description, control explanation and suggestion reasons, with offline templates and injection tests | Within the signed AI item (drafts only) | about 1 day | phase 8 |
| 32 | 2026-11-23 | Assessment objectives wave 1: 163 objectives and 119 artifacts on 35 controls, both frameworks, outcomes beside readiness, comparison report, Objectives tab and page | Extension (content package O1, not in the signed plan) | about 4 days plus independent review | O1, O2 part |
| 33 | 2026-11-23 | Gaps closed: Your part, prefill, section tasks, document variables and markers, acknowledgement step, disabled member reassignment, in scope for, periodic controls | Extension | about 2.5 days | phases 2 to 4 |
| 34 | 2026-11-23 | Gaps closed: milestone snapshots, certificate planning, bulk import with matches, setup import screen, laws in setup, obligations register, SoA version on scope, scope notes, guidance notes, scope statement approval, AI tailoring | Extension | about 3 days | phases 5 to 8 |
| 35 | 2026-11-23 | Objectives for the other 98 controls (428 more, 591 in all), interviewees, only reviewed evidence counts | Extension (O2) | about 5 days plus independent review | O2 |
| 36 | 2026-11-23 | Owner decisions applied: Openlane rewrites shipped as drafts, 13 mapping fixes with notice and audit, law entries shown with disclaimer, profile fields in five templates | Mixed: D-5 and D-10 fix delivered content; the rest is extension | about 1.5 days | content L1, L6, phase 6 |

## Coming, per the build plan

| Phase | What | Signed? |
|---|---|---|
| 2 (rest) | Prefill from sign up and connections, document variables from the profile, assign a profile section to a colleague | Extension |
| 3 | Framework choice in setup, engagement dates and outside party, milestones, timeline, scope items | Extension; engagement fields for ISO follow ISO |
| 4 | Owner functions, required documents list, documents linked to controls on creation | Extension |
| 5 | Suggestions a person accepts, baseline, work plan, setup flow | Extension |
| 6 | Country reference panel (build); content review by counsel is separate | Extension |
| 7 | Internal audit, management review and audit records; system description; existing programme import; SOC 1 guidance page | Extension; SOC 1 is out of scope, guidance only |
| 8 | AI drafting inside onboarding | Uses signed item 2.2 (AI drafting) |
| Content | Library fixes and missing templates (part 5, packages L1 to L6) | Mixed: wording fixes to delivered content are defects, new templates are extension |

Outside review (an ISO lead auditor, a CPA with SOC 2 experience, privacy counsel for the country
content) is a separate cost the owner decides on (decisions D-8, D-9).
