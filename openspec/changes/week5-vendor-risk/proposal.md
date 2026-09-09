# Third-party vendor risk: the register, the tiering engine, and the staged lifecycle

## Why

Every module built so far answers "is our own house in order". This one answers the question an
auditor asks next, and the one that has caused most of the breaches a SOC 2 report exists to
reassure a customer about: **what about the people you gave your data to?**

It is also a control we already ship and cannot currently satisfy. `SOC2:CC9.2` is in the seeded
content today — *"The entity assesses and manages risks associated with vendors and business
partners"* — flagged `is_always_in_scope`. A tenant can see that criterion on their readiness
dashboard and has nowhere in the product to do the work it asks for. This change closes that.

The spec is unusually clear about what makes this real rather than a directory of company names
with a colour on each row:

> ¶82: "Inherent risk tiering on weighted factors (data sensitivity, business criticality,
> system access, regulatory scope, fourth-party reliance) produces a Critical, High, Medium, or
> Low tier that **right-sizes assessment depth, required reviewers, and reassessment cadence**;
> low-tier vendors skip the heavier stages automatically, and approval gates are never skipped."

That sentence is the module. Tiering is not a label — it is the thing that decides how much work
a vendor is worth, and a product that tiers without changing the workload has only added a
dropdown. The staged lifecycle (¶81) is how that proportionality becomes visible: a low-tier
vendor's process visibly collapses to four stages, a critical one runs all twelve, and the
approval gate holds in both cases.

## What this change delivers

**Deliverable 1.2's vendor half**, sequenced so the Week-5 review list — *"add a vendor, tier
it, issue a questionnaire, and log a finding"* — works end to end first.

- A **vendor register** with the profile, data scope, contacts and commercials of ¶80, duplicate
  detection on save, and a portfolio view ranked by residual risk.
- **Vendor and engagement** as two levels, per the accepted ADR-0009: the vendor is the
  organisation, an engagement is one use of it. A vendor serving two departments with different
  data is two risks, not one averaged one. The simple case stays simple — a vendor with no
  explicit engagement gets one implicit default.
- **Inherent tiering** on the five weighted factors, showing its arithmetic the way the
  vulnerability risk-score panel does, because a tier nobody can interrogate is a tier nobody
  trusts.
- **The staged lifecycle as data** — `vendor_stages` rows, not code branches — with gates that
  cannot be skipped, tier-driven skipping that is visible rather than silent, and per-stage exit
  criteria that name the blocker and link to the thing that clears it.
- **Questionnaires** with a self-service vendor portal link, evidence upload against individual
  answers, and residual scoring from the responses.
- **Findings**, their remediation as real tasks in the tasks module rather than a vendor-local
  to-do list, and time-boxed risk acceptance.
- **The approval decision** — four-valued, with segregation of duties enforced server-side.
- **Contracts, monitoring signals, reassessment on a cadence that cannot drift, and an evidenced
  offboarding** where a terminated vendor is archived, never deleted.

## What this change does not deliver

- **Finding → risk-register promotion.** `modules/risk/` is an empty stub: no tables in any of
  the 38 migrations, and the frontend feature is a `.gitkeep`. The seam is designed on both
  sides — `risks.risk_source` already reserves `vendor_finding` — so `promoted_risk_id` ships
  nullable and the action is absent rather than faked. Spec ¶85 and the ¶109 exit criterion are
  not fully satisfiable until the risk slice lands. **This is the one place the module knowingly
  falls short of the contract, and it is a sequencing gap, not a design one.**
- **Live data in four connector-fed tables.** `vendor_scorecards`, `vendor_signals`,
  `vendor_discovered_apps` and Slack alert delivery are **built, migrated and surfaced** under the
  confirmed full-ER scope, but nothing feeds them until Phase 2 — and the scorecard providers
  (SecurityScorecard, BitSight, UpGuard) are not in the connector catalogue in **any** phase.
  Every row is typed in by a human until then. Those screens say "no data source connected"
  rather than showing an empty state that reads as "no risk found", because on a monitoring
  surface those two look identical and mean opposite things.
- **SIG / CAIQ / HECVAT question text.** Not shipped — **V13 confirmed**. Licensed content
  belonging to Shared Assessments, CSA and EDUCAUSE. Verity ships its own bank across the ten
  domains, mapped to those standards by name so an auditor recognises the coverage.

## Where this sits

**Phase 1, Deliverable 1.2**, Week 5 of the signed eight-week plan, shared with the risk
register. Depends on: the compliance engine (findings and vendors both hang off controls), the
evidence module (vendor documents and questionnaire answers carry proof), tasks (remediation),
documents (contracts and DPAs), and the links primitive — where `vendor` is **already** an
allowed type in both the ORM constant and the live database constraint, so the linkage fabric
owes no migration.

Two scope statements were in play and they disagreed: the ER design specifies 26 vendor tables,
the requirements spec's vendor section is 7 bullets, and the Week-5 build list is narrower still.
**V14 is confirmed as the full ER — 26 tables**, which is broader than this change originally
recommended. That pulls in ten capabilities the signed requirements document never mentions:
SOC report reviews, SLAs, subprocessors, intake requests, team roster, assessment comments,
approval conditions as their own table, scorecards, alert rules and discovered apps.

It roughly doubles the build. It also means no later change has to alter what shipped, which is
the delivery plan's own instruction — *"build the phase you are in, design the schema for all
three"*.

Transcribing those diagrams into `design.md` §1 settled the count at **27 tables — 25 tenant-owned
plus 2 global**: the ER's 26, plus `vendor_transitions`, which the ER does not draw and which rule 5
and every other module in this codebase require. One table an earlier draft of this change proposed,
`vendor_reviewers`, was **cut** — the tiering policy and the team roster already answer spec ¶82's
"required reviewers" between them. Seven of the ER's names are prefixed or pluralised to survive in a
shared schema, and every rename and structural departure is listed in §1's deviation register rather
than absorbed silently.

## Provenance

The lifecycle shape, the tiering weights and the residual formula are ported from the working
TPRM implementation in the client's existing GRC-Tenant product, which is a real product rather
than a prototype: a gated eleven-stage lifecycle, two pure scoring engines, a vendor portal and
an executive dashboard. Its genuinely good ideas are adopted — the lifecycle as rows, the pure
gate engine, auto-suspend on an open critical finding, versioned reassessment that supersedes
rather than overwrites, and the append-only risk-score time series.

Its weaknesses are deliberately not: two coexisting lifecycle vocabularies that do not map to
each other, five JSON blobs doing the work of tables, `owner_id` pointing at users instead of
memberships, a hard-deleting vendor endpoint, an evidence table with no `tenant_id`, and a
normalised response table the live portal never writes to, so scoring silently parses a JSON
blob instead. Where a number here came from that product rather than from a signed document, the
decision log says so.

## Status

**Ready to implement.** Four decisions are confirmed (2026-09-09): **V1** twelve stages,
**V10** the engagement is the unit of risk, **V13** ship our own questionnaire bank, **V14** the
full ER at 26 tables. The remaining ten stand as *recommendation taken* — they are built as
written in `vendor-decisions.md` and each records what revisiting would cost.

The one thing still outside this change's control is `modules/risk/`. Until a risk slice exists,
spec ¶85 and the ¶109 exit criterion cannot be met.
