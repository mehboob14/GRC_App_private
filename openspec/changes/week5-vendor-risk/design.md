# Design — third-party vendor risk

Every decision tagged **(Vn)** rests on an unconfirmed answer in `vendor-decisions.md` and
changes if that answer changes. Untagged design rests on the signed documents or on an existing
Verity convention.

---

## 1. Data model

Sixteen tenant-owned tables and two global ones. The ER design specifies twenty-six; **V14**
records what is absorbed rather than built and why.

Every tenant-owned table composes `UUIDPrimaryKey, TenantScoped, Timestamped, Base`, carries
`tenant_id` as the first column of every composite index (rule 1), gets `enable_rls` +
`grant_crud` in the same migration that creates it (rule 12), and declares its vocabularies as
module-level `Final[tuple[str, ...]]` re-stated in the migration and again in the frontend types
— three copies, deliberately, because Alembic must not import a model and TypeScript cannot
import Python.

### The register

| Table | What it is |
|---|---|
| `vendors` | The organisation. Firmographics, the three owners, lifecycle status, and **cached** worst-of-engagements tier / residual / grade for portfolio ranking **(V10)**. |
| `vendor_engagements` | One *use* of the vendor (ADR-0009). Carries its own tier, owner, assessments and contract. Every vendor gets one implicit default engagement at creation so no query special-cases null **(V10)**. |
| `vendor_contacts` | People at the vendor. The portal addressee lives here. |

`vendors.name` and `website` are **not** uniquely constrained. Duplicate detection is application
logic on save (ER ¶90) that warns and offers the match, because two genuinely different
subsidiaries can share a trading name and a hard constraint would block a legitimate record.

### The lifecycle

| Table | What it is |
|---|---|
| `vendor_stages` | **The lifecycle, as rows** (ER ¶101). Unique on `(tenant_id, engagement_id, cycle, stage_key)`. Carries `is_gate`, `is_required`, `status`, `checklist` JSONB, `exit_blockers` JSONB, and who skipped it and why. |
| `vendor_tiering_policies` | Per-tenant weights, thresholds, cadence-by-tier and the skip matrix. Seeded with the defaults in **V6**/**V9** so a customer retunes without a release. |
| `vendor_tiering_assessments` | One scored tiering run: the five factor answers, the computed score, the tier, and who ran it. Immutable history — a retier writes a new row. |
| `vendor_reviewers` | Who must review this engagement, sized by tier (spec ¶82 "required reviewers"). |
| `vendor_approvals` | **Append-only.** The gate record: four-valued decision, approver, rationale, conditions JSONB, time (ER ¶122). |
| `vendor_transitions` | **Append-only.** The module's columnar history — one row per stage movement, mirroring `asset_transitions` / `vuln_transitions`. |

`cycle` is a plain integer on `vendor_stages` rather than a `vendor_cycles` table. A reassessment
increments it and inserts a fresh set of stage rows; the previous cycle's rows stay untouched and
readable. A table would add a join to every lifecycle query to hold one integer and a start date
that the stage rows already imply.

**The gate-freshness rule.** A gate exits only when an approval exists *for this attempt*:
`approval.decided_at >= stage.started_at`. That makes a send-back invalidate a stale approval
without ever mutating the append-only row — the old approval stays in the record, it simply no
longer satisfies a stage that restarted after it.

### The review

| Table | What it is |
|---|---|
| `vendor_assessments` | One review cycle. `review_format` ∈ questionnaire / soc_report_review / external_report (ER ¶105). Holds the portal token *hash*, its expiry and revocation **(V11)**, the computed residual, domain scores and grade. |
| `vendor_responses` | One answer per question. Carries the answer, a note, and an optional `evidence_id` — a vendor answer can carry its proof (ER Table 1). |
| `vendor_findings` | What the review found. `promoted_risk_id` ships **nullable with no promotion action** until `modules/risk/` exists. |
| `vendor_documents` | SOC reports, DPAs, certifications. Coverage window plus expiry, `evidence_id` so a reviewed document stands as audit evidence (ER ¶109). |
| `vendor_contracts` | Term dates, renewal, notice period, and the security/privacy clause flags. |
| `vendor_signals` | Adverse events. Carries `source`, `external_id`, `synced_at` from the first migration (rule 9) even though every Phase 1 row is manual. |
| `vendor_offboardings` | The evidenced exit (ER ¶127): access revocation with who and when, the data-destruction attestation recorded as an assessment, and a completion certificate stored as evidence. |

### Global content plane

`questionnaire_banks` and `questionnaire_questions` carry **no `tenant_id`** and no RLS, exactly
like the SOC 2 control library **(V5)**. Questions carry `domain`, `weight`,
`is_critical_control` and `evidence_required`.

**Subject to V13**: one Verity-authored bank across the ten domains. No SIG, CAIQ or HECVAT
question text is seeded until there is a licensing answer.

### Things deliberately not built

- **Remediations** — a finding's remediation is a **task**. The tasks module already has
  assignment, SLA, transitions and CAPA. A `vendor_remediations` table would be a second, worse
  tasks module that no dashboard knows about.
- **Approval conditions** — JSONB on the approval row. "Approve with conditions" produces
  conditions that are *read together with the decision they qualify*; splitting them into a table
  buys a join and loses that.
- **Subprocessors** — a typed edge in the existing `links` table, where `vendor` is already an
  allowed type on both sides. A fourth party is a vendor.
- **Scorecards, discovered apps, alert rules** — no data source until Phase 2 connectors.

---

## 2. The lifecycle engine

Twelve stages **(V1)**, in spec ¶81 order, with `approval` the only gate **(V2)**:

```
intake → tiering* → diligence → questionnaire → scoring → findings
       → contracting → approval[GATE] → onboarding → monitoring
       → reassessment → offboarding
                                    * required, never skippable, but not a gate
```

**Three transitions, and nothing else.**

- **advance** — permitted only when `evaluate_exit(stage)` returns no blockers. Marks the stage
  complete, walks forward over any skipped rows to the next actionable stage, and writes a
  `vendor_transitions` row plus an `audit_log` row in the same transaction.
- **send_back** — to any strictly earlier stage. Every stage at or after the target resets to
  `not_started` and its blockers clear. Downstream work is invalidated **by design**, and the
  gate-freshness rule means a previously granted approval no longer counts.
- **skip** — only where the tier's skip matrix permits **(V9)**, never for a gate, and never for
  `tiering`. Requires a reason and records who skipped it.

A database `CHECK` enforces the invariant the spec states in prose: **`is_gate` and
`status = 'skipped'` cannot both be true**. Spec ¶82's "approval gates are never skipped" becomes
a constraint, not a convention, because it is the one rule in this module whose violation is a
control failure rather than a bug.

**Exit criteria** are computed, never stored as a boolean. Each returns a list of blockers, each
blocker naming the object that clears it, so the UI can link straight to it:

| Stage | Exits when |
|---|---|
| intake | name, business owner, and a data classification are set |
| tiering | a tiering assessment exists for this cycle |
| diligence | at least one bank selected and the tier's required reviewers assigned |
| questionnaire | every question answered, and no `evidence_required` question missing its file |
| scoring | a residual score has been computed |
| findings | no open finding of critical severity without an active risk acceptance |
| contracting | a contract is linked, when the tier is high or critical |
| approval | an approval exists with `decided_at >= stage.started_at` **and** no unmitigated critical finding |
| onboarding | always passes — it is a handoff, not a control |
| monitoring | never exits; it is the steady state |
| reassessment | a new cycle has been opened |
| offboarding | terminal |

**Auto-suspend.** An onboarded vendor that acquires an open critical finding moves to
`flagged` automatically, and back when it clears. Both are audited. This is ER ¶125's rule, and
it is the one place the module changes a vendor's status without a person asking it to — which is
exactly why it is audited with an explicit machine actor rather than an inherited one.

---

## 3. Scoring

A pure module, `modules/vendors/scoring.py`, mirroring `vulnerabilities/scoring.py`: no session,
no I/O, its own unit tests, and every intermediate step returned rather than discarded — because
the vulnerability module already proved that a score whose derivation is thrown away cannot be
explained on screen afterwards.

**Inherent (V6)** — `Σ (clamp(fᵢ,0,4)/4 × wᵢ) × 100`, weights `.30 .25 .20 .15 .10`, bands at
75 / 50 / 25.

**Residual (V7)** — per domain `inherent × (1 − 0.70 × posture)` where posture is the
weight-averaged answer value (`yes 1.0`, `partial 0.5`, `no 0.0`, `na` excluded from both sides),
then weight-averaged across domains, clamped `≤ inherent`, floored at "high" when any
critical-control question is answered `no`.

Both return a breakdown — factor, answer, weight, points, and the cap — so the tiering panel can
show its arithmetic the way the vulnerability risk panel does. The clamp and the floor are
reported as their own steps, not folded into the number, for the same reason the KEV floor is:
a bar chart whose bars do not sum to the total is worse than no bar chart.

**`next_reassessment_on` is computed from the cadence schedule, not from the completion date**
(ER ¶101, `data-model.md`). A review completed late does not push the next one late; reviews
cannot drift a little further out every cycle, which is the failure mode this rule exists to
prevent.

---

## 4. Interface

Four module-root tabs — **Overview / Register / Intake / Settings** — following the tabs pattern
the assets and vulnerabilities modules already use.

**The register** earns its keep with one column the reference product does not have: **Blocker /
next action**. A vendor directory tells you who your vendors are; a worklist tells you what to do
today. That column turns one into the other, and it is the reason the register is the module's
landing tab rather than a dashboard.

When nothing is blocked, overdue, or due within thirty days, the register says so in a single
line — *"All 41 vendors are current. Next up: Stripe, review due 14 March."* Every GRC register
makes the reader infer health from the absence of red, and absence of red also looks like the
data failed to load. Naming the healthy state makes it a claim the system is willing to make.

**The lifecycle workspace** is the hard screen: twelve stages with gates, skips and blockers,
legible at once. It is a **vertical stage rail** rather than the reference product's wrapping
horizontal chips — twelve chips wrap unpredictably and lose their order, while a vertical rail
holds twelve rows with room for each stage's status, owner and blocker count on the row itself.

- **A gate looks different in kind, not in colour**: fenced by hairlines above and below and
  marked with a diamond rather than a dot, so it reads as a checkpoint at a glance. It is
  coloured by its actual state, not permanently amber — a padlock on a passed gate is a lie.
- **Blockers are the fix, not the complaint**: a danger card naming verb + the object as a link +
  its own action button. "2 blockers" with no route to clearing them is where most GRC tools stop.
- **A skipped stage carries the policy that skipped it** — dashed connector, neutral "Skipped"
  pill, and the tier rule, person, date and reason on the row. *"Policy said this was
  disproportionate"* and *"someone forgot"* must never look the same to an auditor.

**Two moments get specific attention.** When the last blocker on a gate clears, the blockers card
collapses to one success line, the disabled button becomes an enabled **Submit to approval
decision**, and a line names who must act and whether they know yet. In gated workflows the
expensive delay is not the blocker — it is the silence after it clears, because the person who
closed the finding is not the person who advances the stage.

And **segregation of duties is enforced while you pick, not after you submit**: the approver
selector greys disqualified names with the reason — *"Priya Nair — business owner, cannot
decide"*. Enforcing it only on submit means the user has already written a rationale and attached
a paper before learning the rule, and learns it as an obstacle rather than a policy.

**A reassessment opens as a diff, not a blank form** — last cycle's answers pre-filled and marked
unchanged, with a "what changed since" panel and the score delta *with its cause*. A reassessment
reviewed from scratch takes as long as the first one, so it gets rubber-stamped; reviewed as a
diff it takes twenty minutes and is actually read. It is also literally the question an auditor
asks, so the screen and the audit answer become the same artefact.

### Primitives that do not exist yet

Building this needs six additions to `components/ui`, and one correction: the stage rail, a
checklist row, a threshold ruler, a `date` variant on `TextField`, a sparkline, and the diff view
(**the documents module now has a block-and-word diff renderer — reuse it rather than build a
second**). Only six `status-*` families exist in `tokens.css`; `lock`, `calendar`, `flag` and
`history` are **not** in the icon map. A class naming a family that does not exist paints nothing
and fails silently — that has already caused one production bug in this codebase.

---

## 5. Audit, history and boundaries

**Two records per state change**, the pattern assets and vulnerabilities already document: a
columnar `vendor_transitions` row (the domain history, append-only, machine actions carry a null
actor) and an `audit_log` row via `AuditService` with before/after snapshots, in the same
transaction as the change (rule 5).

**Append-only tables carry no `ON DELETE SET NULL` actor FK.** Deleting the referenced membership
would issue an `UPDATE`, which the append-only trigger refuses, failing the delete.
`task_transitions`, `asset_transitions` and `vuln_transitions` all have this today; it is latent
only because IAM disables memberships rather than deleting them. The vendor tables use
`ON DELETE NO ACTION` and keep the id.

**Cross-module calls are service → service**, function-local imports with `# noqa: PLC0415`, and
need these `import-linter` entries in `pyproject.toml`:

```
"verity.modules.vendors.service -> verity.modules.tasks.service"
"verity.modules.vendors.service -> verity.modules.evidence.service"
"verity.modules.vendors.service -> verity.modules.documents.service"
"verity.modules.vendors.service -> verity.modules.iam.service"
```

plus a new `"vendors reaches no other module's data"` forbidden contract mirroring the other
fifteen. `links` is exempt from every contract, so calling it is free.

**Nothing hard-deletes.** A terminated vendor is archived (ER ¶127, rule 6). `DELETE` exists only
for a draft intake request that was never submitted.
