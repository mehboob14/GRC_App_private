# ISO/IEC 27001:2022 plan

Draft of 2026-10-10 for the next call with Faheem. ISO 27001 is signed as Phase 3, deliverable 3.1, and
priced separately when we reach it. This plan says what it takes, what already helps and what to do
first. Build reference stays `openspec/changes/common-control-framework/` (tasks A and E1 to E3);
requirement IDs (CF, FW) are in `docs/product/control-framework-requirements.md`; the working
crosswalk is `docs/product/iso27001-draft-crosswalk.csv` (draft, unreviewed, rule FW-5).

"Following Probo" is read as: use the Probo (MIT) catalogue and measures as the starting point, then
write and review our own crosswalk.

## 1. Summary

- ISO is a content pack on the engine we have, not a rebuild. It has 123 requirements: 30 clause items
  (4 to 10) and 93 Annex A controls. Probo's catalogue lists the same 123 ids.
- Draft crosswalk to our 116 controls: 59 requirements already have a primary control, 45 are partly
  met, 18 need a new control and 1 is organisational. 113 of 116 existing controls would serve both
  frameworks. 16 new controls are proposed: 10 for the management system, 6 for Annex A gaps.
- GitHub: the seven checks need no change. Through the controls they evidence, they already reach 11 ISO
  requirements (4 as the main route, 7 as support), against 5 SOC 2 criteria. Two catalogued checks and
  four proposed ones would raise that.
- Implementation guidance: 26 of 116 controls carry SOC 2 only wording to neutralise (31 sentences), 10
  ISO rows need an extension note, and 16 new controls and about 9 document templates are to write.
- Four things in the code stop a second framework today (section 6.3). They are small, safe for
  SOC 2 and needed for Phase 2 anyway, so they go first.
- Estimate for one developer: about 7 weeks (range 6 to 9) for pack and product, plus 4 to 6 days of a
  qualified reviewer. Each stage is demoable (section 7).

## 2. Following Probo: what we take and what we do not

| Probo asset | What it holds | How we use it |
|---|---|---|
| `apps/console/public/data/frameworks/ISO27001-2022.json` | 123 entries, id and name only | Requirement ids and structure. Our 123 rows match its ids exactly. |
| `data/mitigations.json` | 81 measures, each with a `standards` string naming ISO and SOC 2 items (last changed 2025-03-30) | Source material for the new management system controls: 18 measures are written for clauses only (scope, stakeholders, objectives, SoA, internal audit, management review). A cross-check for the reviewer, never the crosswalk. |
| Model | framework, control (requirement), measure, task, evidence; a requirement carries an implementation state and a justification when not implemented | Same shape as ours (requirement, control, test, evidence). The Statement of Applicability is that state plus justification. |

What we do not take is its mapping. Reasons found in the data:

- Clause references are coarser than its own catalogue (`7.5`, `9.2`, `9.3`) and some carry stray dots
  (`A.8.10.`, `A.8.20.`), so ids need normalising before any join.
- Even after normalising, 34 of 123 ISO items have no measure: 6 clause items (4.4, 6.1.2, 6.3, 7.1, 7.2,
  8.2) and 28 Annex A controls, among them A.5.1 (policies), A.8.24 (cryptography) and A.8.28 (secure
  coding).
- The two encryption measures map to A.8.11 (data masking). A.8.24 (use of cryptography) is never mapped.
- Only 3 of its 81 measure keys equal ours (our library comes from another Probo snapshot), so there is
  no join by key.

Probo's MIT licence does not cover ISO text. The pack ships identifiers and Verity summaries; titles
only after legal review (design section 6). The Probo attribution notice (task A6) goes in with this.

## 3. How ISO differs from SOC 2

| | SOC 2 | ISO/IEC 27001:2022 | What the platform needs |
|---|---|---|---|
| What is assessed | 61 criteria; scope chosen by Trust Services Category | Clauses 4 to 10 always, plus the Annex A controls the organisation selects | `scope_group`; per requirement applicability |
| Selection | Whole library adopted | Controls chosen from the risk treatment; every exclusion justified in the Statement of Applicability | `requirement_applicability`; justification linked to risks |
| Management system | Light (CC1 to CC5) | Mandatory records: scope, policy, objectives, risk method and results, SoA, competence, audit programme, management review, corrective actions | 10 new controls, platform tests, document templates |
| Audit | Type I (a date) or Type II (a period) | Stage 1 and 2 certification, yearly surveillance, recertification in year 3 | engagement types per framework, certificate dates |
| Evidence timing | A window | At least one internal audit and one management review are expected before Stage 2 | readiness gates |
| Text | AICPA, all rights reserved | ISO, no copying | identifiers and Verity summaries |

Exclusions are per requirement, never per control. Marking a shared control not applicable to satisfy
ISO would quietly weaken SOC 2 too (CF-5), so excluding A.7.6 must not switch off PE-02.

## 4. Common controls: SOC 2 and ISO 27001

Draft numbers (method: `iso27001-draft-crosswalk.csv` against `template_requirements.json` and
`checks.json`; they will move after review).

| ISO area | Requirements | Primary control exists | Partly met | New control | Organisational |
|---|---|---|---|---|---|
| Clauses 4 to 10 | 30 | 13 | 5 | 11 | 1 |
| A.5 Organizational | 37 | 19 | 15 | 3 | |
| A.6 People | 8 | 5 | 3 | | |
| A.7 Physical | 14 | 2 | 12 | | |
| A.8 Technological | 34 | 20 | 10 | 4 | |
| Total | 123 | 59 | 45 | 18 | 1 |

- 113 of 116 controls carry at least one ISO requirement. Only GOV-12 (fraud), SD-07 (pipeline storage
  integrity) and SD-08 (processing reconciliation) stay SOC 2 only. 58 of 61 SOC 2 criteria have a
  control that also serves ISO; the exceptions are CC3.3, PI1.4 and PI1.5.
- Physical controls are mostly partial because PE-01 (cloud subservice review) and PE-02 (office access)
  were written for CC6.4. In an ISO audit most of A.7 for a cloud hosted company is "included, inherited
  from the supplier", with the supplier's ISO certificate on file. The vendors module already stores
  `iso_cert` documents, so the Statement of Applicability needs an "inherited" status linked to one.
- Real shared examples:
  - Change: CC8.1 and A.8.32 both rest on SD-01, SD-06, SD-02, SD-04, SD-12, SD-13 and SD-14. One
    GitHub run is evidence for both.
  - MFA: CC6.1 and A.8.5 both rest on IAM-03, fed by the GitHub two factor check and the identity
    provider check.
  - Incidents: CC7.3 to CC7.5 and A.5.24 to A.5.27 both rest on LM-04, LM-07, LM-06 and LM-05.
  - Internal audit: CC4.1 and clause 9.2.1 both rest on GOV-13. Clause 9.2.2 (the audit programme) needs
    an extension.
- ISO only: scope (4.3), the Statement of Applicability (6.1.3), objectives (6.2), threat intelligence
  (A.5.7). SOC 2 only: processing integrity (PI1.4, PI1.5) and fraud (CC3.3).
- Readiness rule stays CF-4: a requirement is met only when every published control mapped to it is
  ready. So the crosswalk must stay tight. The draft has 305 edges (72 primary, 212 supporting, 21 to
  new controls); publish the ones an auditor would test, not every plausible link. SOC 2 has 2.7 edges
  per criterion, the draft 2.5 per requirement.

## 5. New controls (16)

| Code | Control | Covers | Evidence or platform source |
|---|---|---|---|
| GOV-23 | ISMS scope and boundaries | 4.3, 4.4 | Scope statement in Documents, signed by leadership |
| GOV-24 | Context of the organization | 4.1 | Issues register reviewed yearly |
| GOV-25 | Interested parties and their requirements | 4.2 | Register linked to GOV-05 obligations |
| GOV-26 | Security objectives, plans and measures | 6.2, 7.1, 9.1 | Objectives with owner, target, date (Tasks) |
| GOV-27 | Statement of Applicability | 6.1.3 | Generated from applicability; approved version kept |
| HR-09 | Competence of people in security roles | 7.2 | Competence record per role |
| CS-06 | Security communication plan | 7.4 | Plan in Documents |
| GOV-28 | Control of documented information | 7.5.1 to 7.5.3 | Documents versions, approvals, review dates |
| GOV-29 | Operational planning and control of the ISMS | 8.1 | Operating plan |
| GOV-30 | Continual improvement of the ISMS | 10.1 | Improvement log (Tasks) |
| CS-07 | Contacts with authorities and security communities | A.5.5, A.5.6 | Contact list |
| LM-12 | Threat intelligence | A.5.7 | Advisory sources; Verity KEV and EPSS enrichment |
| DM-18 | Data masking | A.8.11 | Masking rules for test data |
| DM-19 | Data leakage prevention | A.8.12 | Suite policies (identity provider or suite connector) |
| NS-12 | Time synchronization | A.8.17 | One cloud check |
| EP-07 | Web filtering | A.8.23 | Device management connector |

Probo has source material for 9 of the 10 management system controls (not competence). It is
rewritten in our words, with attribution.

Cheap platform tests that make the clauses real, all on data Verity already holds (proposed names):
`verity.soa.complete` (every Annex A item decided, every exclusion justified), `verity.isms.scope_signed`,
`verity.objectives.owned`, `verity.audit.internal_in_12_months`, `verity.management_review.in_12_months`.
A "ready for Stage 1" view is the sum of these plus risk assessment (GOV-18), treatment (GOV-20) and
documents reviewed.

## 6. What changes in what exists

### 6.1 Implementation guidance

- Neutralise SOC 2 only wording in 26 controls: BC-03, BC-08, CS-04, CS-05, DM-01, DM-02, DM-05, DM-14,
  GOV-02, GOV-04, GOV-06, GOV-08, GOV-09, GOV-11, GOV-12, GOV-13, GOV-17, GOV-21, GOV-22, HR-04, LM-04,
  LM-06, PE-01, SD-01, SD-06, SD-08. Examples: "The criteria require...", "SOC 2 expects...", "A Type II
  opinion covers a period". Tenants hold copies, so this needs a data migration that rewrites only copies
  still equal to the old template text and offers the rest as "library wording changed" (CF-6).
- Extension notes where ISO makes the team do more: 5.2 (objectives framework in the policy), 6.1.1
  (opportunities), 6.3 (changes to the ISMS), 9.2.2 (audit programme), 9.3.2 and 9.3.3 (management
  review inputs and recorded decisions), A.5.10, A.5.23, A.5.37 and A.6.7 (acceptable use, cloud use,
  procedures, remote working: mostly new document templates).
- Everything else stays. "Why this control answers A.8.28 and what ISO also expects" is the mapping
  rationale, already shown per requirement on the control page. No second copy of guidance per framework.
- Document templates: the 15 shipped ones carry `satisfies: {"SOC 2": [...]}`. Add `"ISO 27001"` ids to
  them and write about 9 more: ISMS scope, objectives, risk assessment method, internal audit procedure
  and programme, management review minutes, corrective action procedure, document control procedure,
  acceptable use, remote working.

### 6.2 GitHub checks

No change to the seven checks, their evidence or the per check linking. Check to control links are
framework neutral (none of the check rationales mention a criterion), so ISO results appear on ISO
requirements the day the mappings exist. Evidence from one run attaches to every mapped control (AU-11).

| ISO requirement | Control | GitHub test feeding it today | What it shows | Still missing |
|---|---|---|---|---|
| A.8.32 Change management | SD-01 (main), SD-06, SD-02 | default branch protected, review required, merged changes reviewed | code reaches production only through review by someone else | request and approval trace (ticket), deployments (SD-13, SD-14 collectors) |
| A.8.29 Security testing | SD-02 (main) | status checks required | the gate exists | tests passed on each change (CI) |
| A.8.5 Secure authentication | IAM-03 (main) | organisation two factor required | GitHub only | identity provider, cloud root |
| A.8.8 Technical vulnerabilities | LM-11 (main), SD-03 | dependency alerts on | alerts are enabled | alerts closed within SLA |
| A.8.25 Secure development | SD-10 (main), SD-01, SD-06, SD-02 | the review and status checks | the process is enforced | the policy in Documents |
| A.8.28 Secure coding | SD-05, SD-03, SD-11, SD-06 | secret scanning, dependency alerts | leaks and known flaws surface | code scanning |
| A.8.4 Access to source code | SD-06, IAM-08 | branch protection | writes are gated | who has repository access |
| A.5.17 Authentication information | IAM-05, IAM-06 (main), SD-11 | secret scanning on | leaked secrets are detected | rotation record (a person) |

To add, each also helping SOC 2:

1. Build two checks already catalogued: `vcs.code_scanning_enabled` (A.8.28, A.8.29) and
   `vcs.unreviewed_merges_recorded` (A.8.32 exceptions; SD-04, SD-06).
2. Propose four: repository access review (admins and outside collaborators, for A.8.4, A.5.18 and
   CC6.3), SSO required in the organisation (A.5.16, A.8.5), secret scanning push protection (A.5.17),
   audit log available (A.8.15; some GitHub plans only).
3. Open: repository exclusions (D7) are per connection. If the SOC 2 system boundary and the ISMS scope
   differ, an exclusion needs an "applies to engagement" qualifier. Start with one shared scope.

### 6.3 Other things that must change

| Where | Today | Change |
|---|---|---|
| `Engagement` | one per tenant (`UNIQUE tenant_id`); audit type `type_1` or `type_2`; scope is Trust Services Categories | one per framework version (FW-10); audit types per framework (ISO: initial certification, surveillance, recertification); certificate dates; scope by group or Statement of Applicability |
| `Requirement` and loader | `trust_services_category` is NOT NULL and the loader reads it and `is_always_in_scope` from every requirement, so an ISO pack fails to load | add `scope_group`, `kind`, `parent_code`, `summary`; loader accepts packs without TSC fields; write `framework_packs` rows |
| `instantiate_library` | with no filter adopts every template of every pack; skips controls already adopted, so they never get links to a newly loaded framework | adopt per pack; add an activation path that creates `ControlRequirement` rows for controls already adopted and respects mappings a tenant removed |
| Callers: signup (`iam/service.py`), `POST /controls/adopt`, `scripts/backfill_adopt_soc2.py` | adopt everything | limit to the SOC 2 pack plus frameworks the workspace activated. Otherwise loading ISO makes every new signup adopt the management system controls |
| New tables | none | `tenant_frameworks`, `requirement_applicability` (RLS, audit, downgrade) |
| `engagement_service` scope and coverage | one engagement, category election | per engagement; ISO scope is clauses plus Annex A items not excluded |
| `report_service` label map | `{"SOC2": "SOC 2"}` | add ISO; controls export lists the frameworks each control serves |
| `ai/mapping.py` | prompt says "senior SOC 2 auditor" | name the frameworks linked to the control |
| Copy | invitation emails, email footer and API description say SOC 2 | neutral wording |
| Frontend | 14 files reference Trust Services (scope, coverage, framework detail, dashboards, controls register, control detail, quick start, types); `trustServicesFor` already ignores non SOC 2 keys | framework picker and activation with overlap preview, per framework dashboard, ISO scope step, Statement of Applicability page with XLSX export, "Serves SOC 2 / ISO / both" on the register, a warning when disabling a shared control |
| Assets | `compliance_scope` is a free list per asset | tag assets with the frameworks they are in scope for (later, with per framework scope) |

Regression guard: a test that activating ISO changes no SOC 2 number (readiness, coverage, counts), on
top of the loader test that already proves a second pack leaves SOC 2 content alone.

## 7. Work packages and order

| Stage | Work | Size | Shows |
|---|---|---|---|
| A. Groundwork (Phase 2 safe) | `scope_group` and loader, `tenant_frameworks`, adoption fixes, relaxed engagement, neutral wording migration, AI prompt and copy, A6 and A7 | 2 weeks | nothing new for SOC 2 users; unblocks ISO and the connectors |
| B. Requirements only plus mapped | ISO pack with 123 requirements, summaries and the crosswalk for existing controls; overlap preview and activation; coverage view | 2 weeks | "ISO 27001: 59 of 123 requirements have a control you already run" |
| C. Management system | 16 new controls, platform tests, document templates, Statement of Applicability page and export, ISO engagement and Stage 1 readiness | 2 weeks | a Statement of Applicability generated from the risk register and controls |
| D. Review and hardening | second reviewer signs the pack, content CI, isolation tests, SOC 2 regression test, runbook, deploy order (migrate, seed-content) | 1 week plus reviewer | a pack that can load in production |
| E. Automation | connectors in the order of section 8 | Phase 2 | ISO results running on live data |

Stage A and the guidance neutralisation do not commit us to delivering ISO, so they can sit inside Phase 2.
Stages B to D are Phase 3.1.

## 8. Automation after the pack: which connector buys the most

Reach of each capability through the draft crosswalk (ISO requirements it touches: main route and any
route; SOC 2 criteria for comparison):

| Capability | ISO main / any | SOC 2 | Status |
|---|---|---|---|
| Cloud infrastructure | 15 / 36 | 17 | AWS Phase 2 |
| Verity policies (built in) | 3 / 18 | 4 | needs the platform test runner (C2) |
| Identity provider | 8 / 15 | 5 | Okta, Google, Entra Phase 2 (Keycloak proposed) |
| Version control | 4 / 13 | 6 | GitHub live |
| Device management | 1 / 11 | 5 | not in the signed catalogue (question 1) |
| Ticketing | 4 / 10 | 4 | Jira Phase 2 |
| Network and edge | 1 / 8 | 3 | Cloudflare, Tailscale Phase 2 |
| Verity risk register, assets, vendors | 5, 4, 1 / 5, 6, 7 | 4, 6, 2 | needs the platform test runner |

Two readings. AWS gives the most ISO and SOC 2 value of any connector. And ISO's management system
evidence mostly lives in our own modules, so the platform test runner (C2, F7) helps ISO more than any
other connector after AWS.

## 9. Risks and decisions needed

1. **Scope and price.** ISO is Phase 3.1, priced separately. Decide with Faheem when it starts and
   whether stage A runs inside Phase 2. My advice: stage A now, the pack after the first connectors.
2. **Second reviewer.** An ISO 27001 lead implementer or auditor signs the crosswalk (FW-5). The 305
   draft edges are their review list. Mapping correctness, not code, is the schedule risk.
3. **The standards.** Buy ISO/IEC 27001:2022 and 27002:2022 for the reviewer and for writing our
   summaries.
4. **Titles.** Ship identifiers and Verity summaries, or short titles after legal review.
5. **Inherited controls.** Agree an "inherited from supplier" Statement of Applicability status with the
   supplier certificate attached, for most of A.7.
6. **One scope or two.** A shared boundary for SOC 2 and ISO to start, or per framework scope from day one.
7. **HR and device connectors.** Open question 1 decides how far A.6 and A.8.1 can be automated.
8. **Honest claims.** Verity prepares for certification and cannot certify. The UI says "ready for Stage 1",
   never "certified".

## 10. What was built (2026-10-10)

The plan above was implemented end to end in one change, on the one control library.

**Content** (`backend/src/verity/seed/content/iso27001`, sealed by `scripts/seal_content.py`)

- The framework record: `scope_model` applicability, listed after SOC 2.
- 123 requirements: 30 in clauses 4 to 10 (always in scope) and 93 in Annex A (37 organizational, 8 people,
  14 physical, 34 technological). Names and summaries are Verity's own words; the pack carries identifiers
  and none of the standard's text.
- 16 new controls: GOV-23 to GOV-30 (scope, context, interested parties, objectives, Statement of
  Applicability, documented information, operational control, improvement), HR-09, CS-06, CS-07, LM-12,
  DM-18, DM-19, NS-12, EP-07.
- 242 requirement to control mappings (49 full, 193 partial), each with a written rationale.
- ISO 27001 requirement ids added to the policy templates that satisfy them.

**Engine**

- `tenant_frameworks`: a workspace says which frameworks it runs. SOC 2 is recorded for every existing
  workspace by the migration, so nothing changes for them.
- `requirement_applicability`: the Statement of Applicability decisions, with a database check that an
  exclusion carries a written reason. Clauses cannot be excluded.
- One engagement per framework (initial certification, surveillance, recertification for ISO; scope
  statement, certification body, audit date). Every `/engagement*` endpoint takes `?framework=CODE` and
  defaults to SOC 2.
- Adding a framework adopts only the controls it needs, links the controls the workspace already runs
  (disabled ones included), and writes one audit row, in one transaction.
- Dashboards and coverage count per framework; a control that serves both is counted in each and worked,
  evidenced and owned once.
- Statement of Applicability: one row per requirement with decision, justification, operated by
  (organization or supplier), owner, review date and the state derived from its controls; XLSX export.

**Screens**: the Frameworks list with an Add dialog that previews the overlap before anything changes; a
switcher when a workspace runs more than one framework; per framework Dashboard, Scope (management system
scope and audit) and Applicability (Statement of Applicability with a decision dialog); the Controls list
and control detail show both frameworks side by side.

**Numbers on a workspace that runs all SOC 2 controls** (116 of them): adding ISO 27001 answers 112 of the
123 requirements with controls already running, 11 need one of the new controls, 100 existing controls gain
ISO links and 16 are added. The library becomes 132 controls. The SOC 2 dashboard and coverage read the same
before and after (asserted by `tests/integration/test_iso27001.py`).

**Checks run**: 11 ISO integration and isolation tests, the earlier SOC 2 regression set (151), 1113 unit
tests, ruff, mypy, import-linter (19 contracts), tsc and eslint, and the screens in a browser against a
real database.

**Closed on 2026-10-19**

- Review pass: an internal compliance reviewer persona (ISO 27001 lead auditor, PCI DSS QSA, SOC 2, banking and
  on premises) reviewed every mapping, requirement summary and shared control; a critic merged the chunks; 300
  confirmed fixes were applied. The pack now has 300 mappings (47 full, 253 partial) and 17 new controls (PE-03,
  environment and equipment protection at own sites, was added). A workspace with all SOC 2 controls answers 111 of
  123 requirements with controls it runs; 104 SOC 2 controls gain ISO links.
- Wording: migration `e3a91c5d7b20` rewrites 60 shipped controls (no framework framed reasons, testable guidance,
  on premises, banking and card data cases as conditional sentences). Edited workspace copies are kept.
- Templates: 15 written by Verity for ISO 27001 and good practice (scope, context, objectives, methodology, change,
  document control, internal audit, management review, corrective action, acceptable use, remote working,
  competence, communication, cloud services, operating procedure).
- Platform tests (C2): 30 built-in checks over the workspace's own records (provider `verity`, always on),
  including the management system documents, internal audit, management review, scope and SoA decisions.
- User guide chapters and the website docs pages describe ISO 27001 and the built-in checks.

**Still open**

- FW-5: the review above is an internal pass, not an independent or accredited one. A second qualified person
  should confirm the mappings before they are presented as reviewed. Names still sit close to official titles
  (section 9, item 4).
- No ISO backfill: a control shipped after a workspace added ISO 27001 is not adopted by it.
- No connector automation for ISO beyond GitHub and the built-in checks: section 8 order.
- SOC 2 only controls after the review: CS-01, CS-02, CS-05, DM-02, DM-07, DM-14, GOV-12, HR-07, LM-08, SD-07,
  SD-08, SD-09.
