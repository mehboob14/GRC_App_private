# Guided onboarding plan

Written 2026-11-21. A plan, not a build. Nothing in here exists in the product yet, and nothing
starts before the decisions in section 6 are made.

The question it answers: when a company comes to Verity to get SOC 2, ISO 27001 or both, with a
programme already running or from nothing, what does it have to decide and hand over before
compliance work starts, what does the official process of each framework ask at each step, who
does what, and how does the product guide all of it with real links into the work.

## 1. The plan in one page

1. **Ask about the company once.** A typed company profile, about sixteen questions and ten
   minutes: who it is, where it operates, how it works, what it runs, what data it holds. Countries
   come from a real list with search and spelling tolerance.
2. **Then ask per framework.** For each of SOC 2 and ISO 27001: the type, the dates, who audits,
   who signs, what is in scope. That is an engagement, and a company has a new one each cycle.
3. **Name eight owners once.** Executive sponsor, security lead, engineering, IT, HR, legal or
   privacy, vendors, finance. Every control, document and task gets its owner from that.
4. **Suggest, never decide.** From those answers the product suggests which controls apply, the
   ISO applicability decisions with their written reasons, the SOC 2 categories, the documents
   needed and the systems to connect. A named person accepts or rejects each one and the decision
   is audited.
5. **Show where the company stands and what to do next.** A baseline in the company's own words,
   then a work plan with owners and due dates worked back from the audit dates.
6. **Get Started becomes the programme home** for both frameworks: shared steps shown once,
   a short lane per framework, counts in place of ticks, a timeline, and every step a door into
   the real page.
7. **Documents link to compliance.** A Required documents list per workspace. Starting one from a
   template links it to the controls it supports, and the links run both ways.
8. **A country reference panel** shows the laws and standards a company should know for the
   countries it picked, in a matrix with dates. Written once with AI help, reviewed by a person,
   shipped as content. Reference only, never a score.
9. **The control library is fixed where it blocks this**, and assessment objectives are rolled out
   in waves on top (part 5).

SOC 1 is not a step before SOC 2. It is a different report for services that affect customers'
financial statements, and it is outside the signed scope. The plan gives it one guidance page.

## 2. Reading order

| Part | File | Read it for |
|---|---|---|
| 1 | [01-compliance-journey.md](01-compliance-journey.md) | The official process of SOC 1, SOC 2 and ISO 27001, who does what (management, consultant, platform, auditor), what must be decided before work starts, dates, assessments, documents |
| 2 | [02-requirements.md](02-requirements.md) | Every requirement with an id and an acceptance test, the profile questions, the Get Started step list |
| 3 | [03-experience.md](03-experience.md) | Screens, wireframes, the country picker, the navigation map, copy |
| 4 | [04-jurisdiction-catalogue.md](04-jurisdiction-catalogue.md) | The country reference panel: coverage, content model, review, wording |
| 5 | [05-control-library-and-objectives.md](05-control-library-and-objectives.md) | What must change in the control library, profile facts and what they switch, owner functions, assessment objectives in waves |
| A | [appendix-a-required-documents.md](appendix-a-required-documents.md) | The 54 documents and records both frameworks expect, with template, controls and gaps |
| Build | `openspec/changes/guided-onboarding/` (`proposal.md`, `design.md`, `tasks.md`) | Data model, API, phases, sizes |

## 3. What exists today and what is new

| Area | Today | In this plan |
|---|---|---|
| Sign up | Name, company, email, password. SOC 2 and 116 controls added automatically | Frameworks chosen in setup |
| Company profile | A settings page of free text fields | Typed, versioned, confirmed, with consumers for every answer |
| Country | Free text | A searchable list of all countries, with zones and regions |
| Frameworks | SOC 2 always. ISO 27001 can be added | Either or both, chosen up front, with an overlap preview |
| Engagement | One row per framework: type, window, categories. ISO has scope text and a body | History, target and stage dates, Type 1 date, outside party for both, signers, milestones |
| Scope | A statement for ISO. A free tag on assets | Scope items linked to assets, vendors and groups, commitments, vendors that count, versioned applicability |
| Ownership | Set control by control | Eight functions, applied once |
| Documents | 30 templates, a picker | A required list, links to controls on creation, import for existing programmes |
| Guidance | None | Suggestions with reasons, baseline, work plan, evidence requests |
| Get Started | Nine SOC 2 steps computed in the browser, four defects | Both frameworks, computed on the server, 25 steps with honest states |
| Country rules | None | Reference panel for nine jurisdictions |
| Audit records | Uploads | Internal audit, management review and findings as records. System description as a document with assembled inputs |
| SOC 1 | None | One guidance page |

## 4. Build order

Each phase ships on its own. Detail and sizes are in `tasks.md`.

| Phase | Delivers | Needs |
|---|---|---|
| 1 Honest Get Started | Defects fixed, both frameworks on the page, server status, address hooks | Nothing |
| 2 Profile and country picker | Typed profile, confirm and versions, country selection | Phase 1 |
| 3 Frameworks, engagements, scope | Chooser, engagement dates and outside party, milestones, timeline, scope items | Phase 2, decision D-2 |
| 4 Ownership and required documents | Owner functions, required list, links on creation | Content packages L2, L4 (half), L5 |
| 5 Suggestions, baseline, plan, setup flow | The guided part proper | Content package L4 |
| 6 Country panel | Reference panel for the first pack | Reviewed content, decisions D-7 and D-8 |
| 7 Records, description, existing programmes, SOC 1 | What an ISO Stage 1 and a SOC 2 Type 1 need | Template work in L3 |
| 8 AI assists | Drafts inside the flow | Phase 5 |

About ten to fourteen working weeks of build for one developer, before content writing and outside
review. An estimate, to be corrected after the models are read in detail.

## 5. How sure this is

| Area | Basis | Confidence |
|---|---|---|
| What the product does today | Code read on 2026-11-21, with file and line references in the research notes | High |
| SOC 1 and SOC 2 process | Research with primary sources read | Good |
| ISO 27001 process | Written from knowledge of the standards. The research pass failed on a network error and was not repeated | Medium. Needs an ISO lead auditor's read |
| Library findings and the document list | Verity's own compliance review. No second qualified reviewer | Medium |
| Country content | 89 drafted entries, mostly from search summaries | Low until reviewed. Not shippable as is |
| Competitor behaviour | Public help centres. No hands on use | Medium |
| Sizes | Before reading every model | Rough |

Research notes are outside the repository, in
`C:\Users\HP\OneDrive\Desktop\Platform\grc-s\research_notes\Guided onboarding plan\`:
`current_platform.md`, `soc_official_process.md`, `competitor_onboarding.md`,
`jurisdiction_catalogue.md`, `library_and_documents_review.md`.

## 6. Decisions needed

"Blocks" names the first phase that cannot start without the answer.

| Id | Decision | Recommendation | Blocks |
|---|---|---|---|
| D-1 | Guided onboarding is in none of the signed phases. Is it agreed as an extension, and on what terms? | DECIDED 2026-11-21: proceed, and log work outside the signed phases in `phase_out_1.md` to price or share separately | Done |
| D-2 | May a workspace run ISO 27001 without SOC 2? Today sign up always adds SOC 2 | DECIDED 2026-11-21 (yes). Choose frameworks in setup, behind a setting, existing workspaces unchanged | Phase 3 |
| D-3 | SOC 1 | DECIDED 2026-11-21: guidance page only. No engagement, no figures | Phase 7 |
| D-4 | The SOC 2 pack ships the criterion text word for word. Onboarding shows it on more screens | DECIDED 2026-11-23: keep the criterion text as it is for now; revisit before wider sale | Content L1. Should be settled before phase 5 widens its use |
| D-5 | Seven templates taken from Openlane follow the 2013 wording of ISO 27001 Annex A | DECIDED 2026-11-23: ship the plain word rewrites now, marked draft and not reviewed | Content L1 |
| D-6 | One scope or two when both frameworks run | DECIDED 2026-11-21 (yes, if both frameworks' rules allow it): one set of scope items and commitments, one statement per framework, the second started from the first. Being checked against each framework's official rules before phase 3 | Phase 3 |
| D-7 | Country content: written once and reviewed, or generated per workspace at run time | DECIDED 2026-11-23 (confirmed as built): written once with AI help, reviewed, shipped as content | Phase 6 |
| D-8 | Who reviews the country content, and what it is called until then | DECIDED 2026-11-23: show the entries in production now with the disclaimer and a not legally reviewed mark; review follows | Phase 6 release |
| D-9 | A second qualified reviewer for compliance content: an ISO lead auditor and a CPA with SOC 2 experience | DECIDED 2026-11-23: engage an ISO 27001 lead auditor and a CPA with SOC 2 experience; until then "reviewed internally" | Any public claim |
| D-10 | Mapping changes that alter what existing workspaces see as met (part 5, section 7), and a requirement resting on one partial control no longer reading met | DECIDED 2026-11-23: apply, with a notice to existing workspaces and an audit row per change | Content L6 |
| D-11 | Documents approved before Verity: do they count? | DECIDED 2026-11-23 (confirmed as built): yes, once a member who may approve confirms it and when | Phase 7 |
| D-12 | Roles. No built in role except Admin can load Get Started or run a programme | DECIDED 2026-11-21 (yes). Get Started needs only `tenant:read`, which every role holds. New built in role Compliance Manager runs the programme; it cannot invite people (an invite may hand out Admin), change roles, groups or security, edit the company profile (`tenant:manage` also sets the mail server), or approve what management signs off | Built |
| D-13 | AI inside onboarding, and sending a company's website to a model to prefill its profile | DECIDED 2026-11-23: AI drafts only; no website prefill | Phase 8 |
| D-14 | Internal audit, management review and audit findings as light records, or as uploaded documents only | DECIDED 2026-11-23 (confirmed as built): light records | Phase 7 |
| D-15 | Verity may itself be a supplier or subservice organisation for a customer whose controls it helps run | DECIDED 2026-11-23 (confirmed as built): ask in the profile and show a short note | Phase 2 |
| D-16 | Build order | As in section 4 | Planning |

## 7. Not in this plan

- SOC 1 engagements and SOC 3.
- A partner console for consultants across workspaces.
- Access for the outside auditor (a signed item of its own).
- Training courseware and a general internal questionnaire builder.
- New frameworks. HIPAA and GDPR arrive through the framework process, not through the country
  panel.
- Go collectors and connector work. Part 5 keeps the library ready for them.

## 8. Rules this plan keeps

1. The product proposes. A named person decides. The decision is audited.
2. AI output is a draft and looks like one.
3. Done is computed from records. A skipped step is shown as skipped.
4. SOC 2 is a report, never a certification. No blended readiness percentage. No promised
   timeline or outcome. No auditor chosen, ranked or priced by the product.
5. The country panel is reference, never advice and never a score.
6. No standard text Verity holds no licence for. Identifiers and its own words.
7. Every new tenant table has its row level security in its first migration. No hard delete.
   People are memberships. Existing permission keys.
8. Short copy, popups for single decisions, no dash characters as punctuation or placeholders.
