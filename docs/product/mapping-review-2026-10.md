# Mapping review, October 2026: findings and where each stands

An automated review of the repository at commit `61929d1` (3 October 2026) read the four mappings an
auditor follows, requirement to control, control to test, test to system, and test or control to
evidence, and ran 11 adversarial cases against the GitHub evaluator. It found twenty things. This
page records what was done about each, so the review is not a document that goes stale beside the
code. The review's own tables (all 150 links, all 70 test links, evidence per control) are inputs to
the content review in task A5, not shipped content.

The reading taken of the request: build the model Vanta and Drata describe (a requirement is answered
by controls, a control is evidenced by tests and by documents, one control can need several systems
and some people), say it for every control, and make the same model carry ISO 27001 later. The
product definition is `control-framework-requirements.md` section 3A; the design is
`openspec/changes/common-control-framework/design.md` section 4.5.

## Findings

| # | Finding | Status | Where |
|---|---|---|---|
| F01 | A criterion can be ready with other controls unimplemented | Fixed | `compliance/readiness.py`: met only when every applicable control is ready (CF-4) |
| F02 | Pending, rejected, stale or out of window evidence can count | Partly | Rejected and past-renewal evidence no longer counts; a failing, unreadable or out of date test blocks readiness whatever evidence exists. Open: pending evidence still counts, and the Type II window (AU-7) is not applied |
| F03 | A merged-change test cannot show approval before the merge | Fixed | `github._effective_approvers`: each reviewer's last decision before the merge; approval after the merge, withdrawn or dismissed approvals and the author's own do not count |
| F04 | Branch protection passes do not prove the stated gate | Partly | A pull request requirement, push restriction or lock is needed; classic bypass by administrators is said on the result. Open: a ruleset's bypass list is not read |
| F05 | Unreadable rulesets become failures | Fixed | A policy source that could not be read makes a would be failure an `error`; protection that was read is never undone by one that was not |
| F06 | A sampled population can pass an every change test | Fixed | Up to 100 merged changes and 500 closed pull requests per repository, reviews paginated, and a cut short population is stated in the result and the evidence. An unreviewed change found is always a `fail` |
| F07 | Population completeness and production scope are not enforced | Partly | Scope with reasons (AU-9) and an explicit `error` when more than 300 repositories are in scope. Open: the default branch is still taken as production |
| F08 | All 150 requirement links load as full without a rationale | Fixed | 167 links carry coverage and a rationale (37 full); the loader refuses one without them |
| F09 | Several full test to control links overstate what the test observes | Fixed | 16 of 101 test links are full, and only where the control has that one test; every link says what it does not prove |
| F10 | Partial or all not applicable automation can show Passing | Partly | Not applicable alone is never a pass. The control page states how many checks run of how many. Open: a dimension aware overall state |
| F11 | Latest automation status has no freshness cutoff | Fixed | A result older than two days is `stale`, shown in place of pass or fail and blocking readiness |
| F12 | Evidence is linked but its required contents are not modelled | Partly | Every control lists the evidence an auditor expects, design or operating, with cadence and route. Open: it is guidance, not slots, so readiness does not require each item (F5 in tasks) |
| F13 | A connection wide snapshot is the artifact for every mapped control | Open | Per control projections (F9 in tasks) |
| F14 | Immutable results reference mutable test definitions | Partly | Every result names the rules that judged it (`rule`). Open: versioned definitions pinned on each run |
| F15 | Unchanged outcomes suppress changed evidence | Fixed | The run digest includes the detail, so a changed reviewer, setting or population files new evidence |
| F16 | SOC 2 manifest is stale and unvalidated by the loader | Fixed | Manifests sealed (`scripts/seal_content.py`), line endings normalised, the loader refuses a mismatch, a unit test checks every pack |
| F17 | Loading another framework can prune shared mappings and controls | Fixed | Templates pruned per pack, mappings per framework; proved with a probe framework in `tests/integration/test_content_loader.py` |
| F18 | Most tests and several promised routes are catalogue only | Disclosed | 7 of 81 tests run today (GitHub). Every other test shows its state for the workspace: ready to connect, planned, or needing a system outside the plan. The 18 platform tests are catalogued and planned |
| F19 | Probo reference lacks a pinned derivation trail and attribution | Open | Task A6 |
| F20 | SOC 2 text reuse permission is undocumented | Open | Task A4. A decision for the client, not for the code |

## The weak links

The review marked 17 links as weak or conditional (for example GOV-10 to CC1.5, GOV-15 to CC1.2,
EP-02 to CC6.5, DM-11 to P6.7). None was removed. Each is kept as `partial` with a rationale that
says what the control does not show, which is the honest reading: a security officer is accountable
for the program but does not show how individuals are held accountable. Removing them would also
change every workspace's adopted mappings, which the library update rule (CF-6) allows only for a
mapping that is wrong, not for one that is thin. A reviewer may still decide otherwise (task A5).

## Gaps the review pointed at that the library now closes

- **CC8.1** had six controls and no deployment or traceability control. SD-13 Controlled
  production deployments and SD-14 Change traceability are added, so the criterion reads process,
  authorization, review, testing, environments, emergencies, deployment and traceability.
- **P6.4** had only the agreement. BC-08 vendor security due diligence now supports it.
- **Provider honesty.** Tests that need a collector that does not exist read "planned", and
  evidence a planned test will collect reads "provide it for now".

## What was not in the review and is still true

It saw no tenant data and ran no browser. The new pages were checked against a local demo
workspace with a recorded GitHub. Nothing here is a compliance opinion: the mappings are Verity's
reading and need a qualified second reviewer before they are published as reviewed.
