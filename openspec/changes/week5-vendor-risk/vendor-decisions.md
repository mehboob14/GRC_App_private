# Vendor risk — decisions needed before the schema is cut

**Status: FOUR CONFIRMED 2026-09-09. The other ten stand as "recommendation taken" — they are
implemented as written below unless you say otherwise, and each says what it costs to revisit.**

| Confirmed 2026-09-09 | Answer |
|---|---|
| **V1** Lifecycle stages | **Twelve** — reassessment and offboarding are separate stages |
| **V10** Vendor vs engagement | **The engagement is the unit of risk**; the vendor caches its worst |
| **V13** Questionnaire content | **Ship a Verity-authored bank.** No SIG/CAIQ/HECVAT text |
| **V14** Scope | **The full ER — 26 tables** (this overrode the recommendation of 16) |

Every decision below is a place where the two signed documents disagree with each other, specify
a thing in words but never numerically, or do not cover it at all. CLAUDE.md's working agreement
is *"never invent schema"* and *"if the requirement is ambiguous, say so and propose the reading
you took"* — so each item states the conflict, quotes the source, gives a **recommendation** you
can simply confirm, and says what it costs to change later.

The ones that are expensive to change after a tenant has data are marked **load-bearing**. The
rest can be revised in a later migration without a data repair.

| | Decision | Load-bearing | Answer |
|---|---|---|---|
| V1 | Eleven stages or twelve | ●●● | **CONFIRMED — twelve** |
| V2 | Which stages are gates | ●●● | Approval only *(taken)* |
| V3 | Which approval decision enum is authoritative | ●● | `vendor_approvals`, four-valued *(taken)* |
| V4 | Segregation of duties — how many exclusions | ● | Two (the prose) *(taken)* |
| V5 | Questionnaire banks: global or tenant-authorable | ●●● | Global in Phase 1 *(taken)* |
| V6 | Inherent tiering weights and thresholds | ●● | As below *(taken)* |
| V7 | Residual formula and grade bands | ●● | As below *(taken)* |
| V8 | The ten risk domains | ● | As below *(taken)* |
| V9 | Which stages each tier skips | ●● | As below *(taken)* |
| V10 | Vendor-level vs engagement-level precedence | ●●● | **CONFIRMED — engagement wins** |
| V11 | Vendor portal token design | ●●● | Hashed, expiring, single-assessment *(taken)* |
| V12 | Object-level scoping for vendors | ●● | Tenant-wide read, no owner scoping *(taken)* |
| V13 | Shipping SIG / CAIQ / HECVAT question text | ●●● | **CONFIRMED — our own bank** |
| V14 | Scope: the ER-only tables, and the Week-5 vs 1.2 gap | ●●● | **CONFIRMED — full ER, 26 tables** |

---

## V1 — Eleven stages, or twelve? **(load-bearing)** — APPROVED 2026-09-09: TWELVE

The spec names **eleven**, fusing the last two:

> ¶81: "…Onboarding, Continuous Monitoring, and **Reassessment and Offboarding**."

The ER's `vendor_stages.stage` enumerates **twelve**, splitting them:
`intake tiering diligence questionnaire scoring findings contracting approval onboarding
monitoring reassessment offboarding`.

**Recommendation: twelve.** Reassessment is recurring and offboarding is terminal; fusing them
would mean a stage that is both. The spec's eleventh is a prose contraction, not a data model.

**CONFIRMED: twelve.** `reassessment` and `offboarding` are separate stage rows. The spec's
eleventh is read as prose shorthand. The `CHECK` constraint carries twelve values.

## V2 — Which stages are gates? **(load-bearing)**

Spec ¶82 says *"approval gates are never skipped"*, implying gates are the approval stages. The
ER's `is_gate` annotation names **two**: *"tiering and approval never skipped"*. ER ¶101 says a
gate *"requires an approval record to exit"*.

That reads wrong for tiering: exiting a scoring step should not require a four-valued approval
decision with segregation of duties.

**Recommendation: `approval` is the only gate.** Tiering becomes *unskippable but not a gate* —
a third flag (`is_required`), so it still cannot be skipped, but it exits on "a tier has been
computed" rather than on an approval record. That satisfies both sentences without forcing a
sign-off ceremony onto a calculation.

**Alternative if you disagree:** keep both as gates and accept that tiering needs an approver.

## V3 — Two approval decision enums that disagree

`vendor_assessments.decision` = `pending approved approved_with_conditions rejected` — **no
`defer`**.
`vendor_approvals.decision` = `approve approve_with_conditions defer reject` — has `defer`, and
uses verbs rather than participles.

Spec ¶85 and ER ¶122 both give the four-valued set as *the* approval decision.

**Recommendation: `vendor_approvals` is authoritative**, four-valued, verb tense. Drop
`decision` from `vendor_assessments` entirely — two tables holding overlapping decision state is
a data-integrity trap, and the assessment already has `status`. The approval row is the record of
who decided what, when and why; the assessment is the work product.

## V4 — Segregation of duties: two exclusions or one?

ER ¶122 prose excludes two people: *"the decider [must] differ from the vendor's business owner
**and** the stage submitter"*. The diagram annotation on `decided_by` says only *"must differ
from submitter"*.

**Recommendation: take the prose (two exclusions).** It is the stricter reading and the one an
auditor will expect. Note that it makes a single-admin workspace unable to approve its own
vendors — which is correct, and is the same rule the vulnerability exception flow already
enforces.

## V5 — Are questionnaire banks global content or tenant-authorable? **(load-bearing)**

ER ¶269 lists questionnaire templates among the **global content tables that carry no
`tenant_id`**. But the same diagram gives `templates.name` the value `custom` and a `built_in`
boolean — both of which only make sense if a tenant authors its own.

**Recommendation: global-only in Phase 1.** Ship versioned banks with no `tenant_id`, exactly
like the SOC 2 control library. Treat `built_in` / `custom` as forward-looking for a Phase 2
tenant-authored bank, which will need its own table with `tenant_id` and RLS rather than a
nullable column retrofitted onto global content.

**Cost of changing later:** adding `tenant_id` to a global table after rows exist means an RLS
policy, a backfill, and a rethink of what "global" meant. Cheap now, expensive later.

## V6 — Inherent tiering: the weights and thresholds are never stated

Spec ¶82 names the five factors. Neither document gives a weight, a scale mapping, or a
threshold. The ER says factors are `0..4`, weights *"normalize to 1"*, score is `0..100`, and
`tier_thresholds` is *"critical high medium ordered"* — three cut-points, no values.

**Recommendation** (weights and thresholds from the reference product's shipped
`DEFAULT_TIERING_CONFIG`, so this is a port and not an invention):

```
inherent = Σ (clamp(factorᵢ, 0, 4) / 4 × weightᵢ) × 100

  data sensitivity      0.30
  business criticality  0.25
  system access         0.20
  regulatory scope      0.15
  fourth-party reliance 0.10

  ≥75 critical    ≥50 high    ≥25 medium    <25 low
```

Stored per-tenant in `vendor_tiering_policies` so a customer can retune without a release, with
these as the seeded defaults.

## V7 — The residual formula does not exist anywhere

Spec ¶84 says residual is *"derived from the inherent tier and the vendor's control answers"*.
That is the entire specification. Unstated: how `partial` scores, how `na` is excluded, how
domains roll up, and where the A–F grade boundaries fall.

**Recommendation** (again porting the reference product's arithmetic):

```
answer value:  yes 1.0   partial 0.5   no 0.0   na excluded from both numerator and denominator
posture(domain) = Σ(value × weight) / Σ(weight)          over answered questions
residual(domain) = inherent × (1 − 0.70 × posture)
residual = Σ(residual(domain) × domain weight) / Σ(domain weight)
           clamped so residual ≤ inherent            — controls reduce risk, never add
           floored at "high" if any critical-control question is answered `no`
grade:  A <20   B <40   C <60   D <80   F ≥80
```

The `0.70` is the ceiling on how much good control answers may reduce inherent risk — a vendor
with perfect answers still carries 30% of its inherent risk, because a questionnaire is a claim,
not a proof. That number is a judgement call worth your eye.

## V8 — The "ten risk domains" are named nowhere

`questions.domain` is annotated *"of ten risk domains"*. The ten are listed in neither document.

**Recommendation:** information security, access control, data protection and privacy, business
continuity and resilience, incident response, secure development, infrastructure and cloud,
personnel security, compliance and legal, fourth-party management.

Low cost to change — it is a vocabulary on question rows, not a structural choice.

## V9 — Which stages does each tier skip?

Spec ¶82: *"low-tier vendors skip the heavier stages automatically."* ER ¶101: *"Tier based
stage skipping means inserting fewer rows."* Neither says which.

**Recommendation:**

| Tier | Skips |
|---|---|
| Critical | nothing |
| High | nothing |
| Medium | `diligence` |
| Low | `diligence`, `questionnaire`, `scoring`, `findings` |

A gate is never in that list regardless of tier (V2). A low-tier vendor therefore runs
intake → tiering → contracting → approval → onboarding → monitoring → reassessment, which is
the proportionality the spec is asking for.

## V10 — When vendor and engagement disagree, which wins? **(load-bearing)** — APPROVED 2026-09-09

ADR-0009 is accepted and separates the vendor (the organisation) from the engagement (one use of
it). Its own Consequences say *"every vendor query must decide whether it operates at vendor or
engagement level"*, and the ER leaves that unresolved: `vendors.tier` and
`vendor_engagements.tier` both exist, `vendors.next_reassessment_on` is vendor-level while
`vendor_stages` runs per engagement, and findings/documents/signals are vendor-level only.

**Recommendation: the engagement is the unit of risk; the vendor caches the worst of its
engagements.** `vendors.tier`, `current_residual_score` and `current_grade` become derived
read-model columns holding the highest-risk engagement's values, recomputed whenever an
engagement is scored. The register ranks on the cache; every workflow runs on an engagement.

A vendor with no explicit engagement gets one implicit default engagement at creation, so the
simple case stays simple exactly as ER ¶89 promises, and no query has to special-case null.

**CONFIRMED.** The engagement is the unit of risk. Tiering, stages, assessments, approvals and
contracts all run per engagement; `vendors.tier`, `current_residual_score` and `current_grade`
are cached read-model columns holding the worst engagement's values.

## V11 — The vendor portal token needs designing, not transcribing **(load-bearing)**

`vendor_assessments.portal_token` is drawn as a bare string with no expiry, no revocation and no
hash. It is the only externally reachable write path in the platform. ADR-0006 item 7 requires
*"signed, expiring tokens"*, and the multi-tenancy doc requires the tenant to be resolved **from
the token**.

**Recommendation:** store `portal_token_hash` (never the token), `portal_token_expires_at`,
`portal_token_revoked_at`, and issue a single-assessment token that carries no tenant identifier
in the URL. Rate-limit the portal endpoints per token and per IP. A vendor contact can see
exactly one assessment and nothing else.

Also unaddressed by either document, and worth an explicit answer: **file uploads from an
unauthenticated party.** Recommendation — same magic-byte allowlist the evidence uploader
already enforces, a size cap, and no execution path.

## V12 — Object-level scoping for vendors

CLAUDE.md rule 7 requires object-level scope in the service layer on top of the flat permission.
No document names a single vendor permission key, and the role table gives only *"Compliance
manager: read and write on compliance data"*.

**Recommendation:** four keys — `vendors:read`, `vendors:manage`, `vendors:assess`,
`vendors:approve` — with **tenant-wide read and no owner-level row scoping in Phase 1**. A
vendor register that hides vendors from the compliance manager is worse than one that does not.
`vendors:approve` is the segregation-of-duties key (V4), separate from `manage` for the same
reason `vulnerabilities:accept` is separate.

## V13 — SIG, CAIQ and HECVAT cannot simply be shipped **(load-bearing)** — APPROVED 2026-09-09

ER ¶104 says the standard questionnaires *"ship as versioned question banks"*. But SIG is a
licensed commercial product of Shared Assessments, CAIQ is CSA-licensed, and HECVAT is
EDUCAUSE's. Neither document addresses licensing. This is the same exposure already recorded
against the control library's verbatim AICPA criteria text.

**Recommendation: do not seed SIG or CAIQ question text.** Ship one Verity-authored bank
covering the ten domains, and let a customer import their own SIG/CAIQ workbook if they are
licensed for it. Mapping *to* those standards by name is fine; reproducing their question text
is not.

**CONFIRMED: ship a Verity-authored bank only.** No SIG, CAIQ or HECVAT question text is
seeded. Banks map to those standards **by name** so an auditor recognises the coverage, and a
customer licensed for one may import their own workbook. No legal review blocks the build.

## V14 — Scope: the ER-only tables, and the Week-5 gap **(load-bearing)** — APPROVED 2026-09-09: FULL ER

Two different scope statements are in play.

**The ER specifies 26 vendor tables. The requirements spec's vendor section is 7 bullets.**
Absent from the signed spec entirely: engagements, team roster, intake requests, discovered apps
(shadow IT), contracts as clause-level objects, SLAs, scorecards, alert rules, subprocessors,
SOC report reviews, assessment comments. If scope needs trimming, that is where the contract is
thinnest — though `delivery-plan.md` says *"full TPRM lifecycle"*, which arguably pulls them in.

**The Week-5 build list is narrower than Deliverable 1.2.** Week 5 names register, tiering,
questionnaire + portal, findings, approval. Deliverable 1.2 additionally requires contracts,
monitoring signals, reassessment cadence, structured offboarding and the portfolio dashboard.
The build plan is a schedule; the spec is the contract — so those are Phase 1 obligations the
schedule under-describes, not deferrals.

~~Recommendation: sixteen tables.~~ **OVERRIDDEN. CONFIRMED: build the full ER — 26 tables.**

Everything the ER draws is built, including the tables the requirements spec never mentions:
SOC report reviews, SLAs, subprocessors, intake requests, team roster, assessment comments,
approval conditions as their own table, scorecards, alert rules and discovered apps.

**One thing this decision does not change, and it must not be mistaken for scope:** four of
those tables have **no data source until Phase 2 connectors exist**. They are built, migrated,
RLS'd and surfaced, but every row in them will be typed in by a human until then:

| Table | Fed by, when |
|---|---|
| `vendor_scorecards` | SecurityScorecard / BitSight / UpGuard — **not in the connector catalogue in any phase** |
| `vendor_signals` | breach intel, adverse media, financial health — same, no catalogued connector |
| `discovered_apps` | the identity connectors (Google Workspace, Okta, M365) — Phase 2 |
| `vendor_alert_rules` (slack channel) | the Slack connector — Phase 2 |

Building them now is still the right call under the delivery plan's own rule — *"build the phase
you are in, design the schema for all three"* — and it means no later change has to alter what
was shipped. But the UI must say "no data source connected yet" on those surfaces rather than
render an empty state that reads as "no risk found".

---

## Already decided — recorded, not asked

These came out of the same reading but are settled by existing Verity rules, so they need no
answer. They are here so the reasoning is not lost.

- **Every person FK targets `tenant_memberships`, never `users`.** The ER diagrams draw them as
  bare untargeted uuids and ER ¶263 predates the identity split. CLAUDE.md rule 3 is explicit,
  and `data-model.md` already records that the ER's identity diagrams are stale. Drift, not
  ambiguity.
- **`vendor_signals` and any future scorecard table carry `source`, `external_id`, `synced_at`
  from their first migration** (rule 9). The diagrams omit them because the ER shows defining
  columns only, which is not permission to leave them out.
- **`vendor_findings.promoted_risk_id` ships nullable with no promotion action.**
  `modules/risk/` is an empty stub. `risks.risk_source` already reserves `vendor_finding`, so
  the seam is designed on both sides; only the far side is missing.
- **Append-only tables must not carry `ON DELETE SET NULL` actor FKs.** Deleting the referenced
  membership would issue an `UPDATE`, which the append-only trigger refuses, failing the delete.
  `task_transitions`, `asset_transitions` and `vuln_transitions` all have this today; it is
  latent because IAM disables memberships rather than deleting them. The vendor append-only
  tables will use `ON DELETE NO ACTION` and keep the id.
