# Guided onboarding: one company profile, engagements per framework, a Get Started page that covers SOC 2 and ISO 27001

Status: proposed on 2026-11-21; the owner said proceed the same day (D-1, D-2, D-3), then D-6 and
D-12. Phases 1 to 8 are built and uncommitted as of 2026-11-22, with the gaps listed in `tasks.md`
(owner answers still owed: D-4, D-5, D-8 legal review of the country pack, D-9, D-10, D-13). Work outside the signed phases is logged in
`docs/product/guided-onboarding/phase_out_1.md`.

Product plan: `docs/product/guided-onboarding/` (README, parts 1 to 5, Appendix A). Requirement ids
below (PR, FS, EN, SC, OW, RD, PL, GS, JC, AI, CN, EX, NV, S1, NF, CL, AO) refer to it.

## Why

A new workspace today gets a company name, a SOC 2 framework row and 116 controls. Nothing asks who
the company is, which frameworks it wants, by when, who audits it or who owns what. Get Started is
nine SOC 2 steps computed in the browser. ISO 27001 was added in October and has no place on it.

Four facts from the code and the compliance review make this more than a page redesign:

1. **Get Started is SOC 2 only and wrong in four places.** A security only scope can never tick the
   categories step, the footer says connections arrive later, control steps tick on 1 of 116, and
   every built in role except Admin gets an error on its landing page.
2. **The engagement cannot hold what an audit needs.** No auditor for SOC 2, no Type 1 date, no
   target or stage dates, no history, no scope items, no approvals, no system description.
3. **The library cannot answer the questions onboarding asks.** No applicability condition, no
   owner hint, documents that do not bind to controls, and evidence items a newcomer cannot act on
   (part 5).
4. **Nothing explains the journey.** The official steps, the dates that matter and the documents
   each framework needs live in consultants' heads.

## What changes

- **Company profile, asked once.** The existing `company_profile` becomes typed, versioned and
  confirmed, with countries chosen from a real list (PR).
- **Framework choice and engagements.** A workspace chooses SOC 2, ISO 27001 or both in setup.
  Each framework has engagements over time with type, dates, outside party, milestones and named
  signers (FS, EN).
- **Scope that is data.** Scope items linked to assets, vendors and groups, commitments, vendors
  that count for an engagement, and versioned applicability with approval (SC).
- **Ownership once.** Eight owner functions mapped to members, proposed onto controls, documents
  and tasks (OW).
- **Required documents.** A list driven by templates, the profile and the active frameworks, where
  starting a draft links it to its controls (RD).
- **Suggestions a person accepts.** A small rule evaluator over profile facts produces suggestions
  for applicability, categories, scope, owners and documents. Accepting applies the change through
  the owning module with an audit row (PL).
- **Baseline and work plan.** The company's own view of where it stands, then a previewed and
  approved set of tasks with owners and due dates worked back from the engagement (PL).
- **Get Started rebuilt.** Status computed on the server, shared steps shown once with framework
  chips, a lane per framework, counts in place of ticks, a timeline, a view for people who own only
  a part (GS).
- **Country reference panel.** A sealed, reviewed catalogue of the rules a company should know by
  where it operates. Reference only, no score (JC).
- **Records an ISO audit needs.** Internal audit, management review and audit findings as light
  records. The SOC 2 system description as a document with assembled inputs (EN-6, EN-9, EN-10).
- **Content changes in the library** that the above depend on (part 5: CL-4, CL-5, CL-7, CL-8,
  CL-9).

## Scope against the signed plan

Guided onboarding is in none of the three signed phases. The delivery plan says anything not
listed "is scoped separately and agreed before any work starts". This proposal is that scoping.

| Group | Relation to the signed plan |
|---|---|
| Fixing the four Get Started defects, loading the page for every role | Defects in delivered Phase 1 work |
| Get Started for two frameworks, engagement fields ISO needs | Follows from ISO 27001 (3.1), not itemised there |
| Profile, setup flow, ownership, suggestions, baseline, work plan, required documents | Extension |
| Country reference panel | Extension |
| System description, internal audit and management review records | Extension, needed for a credible SOC 2 Type 1 and ISO Stage 1 |
| AI drafting inside onboarding | Uses the Phase 2.2 AI drafting item. No new AI scope beyond drafts |
| SOC 1 | Out of the signed scope. Guidance page only |

Decision D-1 in the plan README covers the commercial side. No build starts before it.

## Impact

- **Schema.** Additive: new columns on `company_profile` and `engagements`, new tenant tables with
  forced row level security in their first migration, one relaxed uniqueness rule on engagements.
  No new global table (the step catalogue, rule expressions and country catalogue are sealed files
  read at start). Every migration has a working downgrade.
- **Modules.** One new backend module, `onboarding`, and one small one, `regulations`. Changes in
  `tenancy` (profile), `compliance` (engagements, scope, applicability versions, assurance
  records), `documents` (required list, import, links on create), `iam` (role grants). Calls
  between modules go service to service.
- **API.** New routes under `/onboarding`, `/regulations`, `/engagements`. Existing routes keep
  their contracts. Sign up stops adding SOC 2 on its own only when decision D-2 says so, behind a
  setting.
- **Permissions.** Existing keys only. One grant change (`members:read` or a narrower read) and a
  possible new built in role are decision D-12.
- **Frontend.** New `features/onboarding` and `features/regulations`, a rebuilt quick start page,
  nine small shared components, address hooks on four existing pages.
- **Content.** New fields on control and document templates, a step catalogue, a country pack.
  All sealed. No tenant data migration is needed for template guidance read at request time.
  Mapping changes that alter status for existing workspaces are a separate decision (D-10).
- **Tests.** Isolation tests for every new tenant table, content tests for the new fields, a query
  count test on the status endpoint, the copy scan.

## Not in this change

- SOC 1 engagements, objectives or readiness. SOC 3.
- A partner or consultant console across workspaces.
- Auditor access for the outside party (signed item 3.2).
- A general questionnaire builder for internal use.
- Training courseware.
- Assessment objectives (part 5, packages O1 and O2). Onboarding is sequenced so it does not
  depend on them, and avoids shapes that would block them.
- Any country content that a person has not reviewed.
- Mapping and wording fixes to the library that change meaning (part 5, packages L1 and L6). They
  are their own change with their own sign off.

## Open decisions

D-1 to D-16 in `docs/product/guided-onboarding/README.md`. The ones that block the first build
step are D-1 (scope and terms), D-2 (ISO without SOC 2) and D-12 (roles).
