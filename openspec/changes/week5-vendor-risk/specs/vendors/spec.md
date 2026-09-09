# Vendors (third-party risk)

> **Four decisions are CONFIRMED (2026-09-09): V1** twelve stages, **V10** the engagement is the
> unit of risk, **V13** ship a Verity-authored questionnaire bank only, **V14** build the full ER
> at twenty-six tables. The remaining ten stand as *recommendation taken* and are still tagged
> below — **(V2)** approval is the only gate, **(V5)** banks are global content, **(V11)** portal
> token design, and so on. A tagged requirement changes if that recommendation is overridden; an
> untagged one rests on the signed requirements document, the ER design, or an existing Verity
> rule.

## ADDED Requirements

### Requirement: A vendor is an organisation; an engagement is one use of it

The register records the organisation. Risk is scoped to an engagement — one use of that vendor
by one part of the business — because the same vendor serving two departments with different data
is two different risks, and averaging them destroys the information tiering exists to produce
(ER ¶89, ADR-0009).

Every vendor has at least one engagement. A vendor created without one is given a single implicit
default engagement in the same transaction, so the simple case stays simple and no query has to
special-case an absent engagement.

`vendors.tier`, `current_residual_score` and `current_grade` are **cached read-model columns**
holding the values of the vendor's highest-risk engagement. They are recomputed whenever any
engagement is scored, and they are never the source of truth.

#### Scenario: A vendor used by two departments carries two tiers

- **GIVEN** a vendor with one engagement handling marketing analytics and another handling
  payroll
- **WHEN** each engagement is tiered
- **THEN** the marketing engagement is tiered Low and the payroll engagement Critical
- **AND** the vendor row caches Critical, because the register must rank on the worst case
- **AND** each engagement runs its own lifecycle, with the Low one skipping the heavier stages

#### Scenario: A small workspace never sees engagements

- **GIVEN** a workspace that has never created an engagement explicitly
- **WHEN** a vendor is added
- **THEN** a default engagement is created with it
- **AND** every screen presents the vendor as a single record

---

### Requirement: Inherent tiering right-sizes the work, and shows how (V6, V9)

Tiering scores five weighted factors — data sensitivity, business criticality, system access,
regulatory scope, fourth-party reliance — into a 0–100 score and one of Critical, High, Medium or
Low (spec ¶82).

The tier is not a label. It **determines** assessment depth, the number of required reviewers,
and the reassessment cadence. A product that tiers without changing the workload has added a
dropdown, not a control.

The scoring function returns every intermediate step — each factor's answer, weight, points and
cap — so the interface can show the arithmetic. A tier a reviewer cannot interrogate is a tier
they will not defend to an auditor.

Weights, thresholds, cadence-by-tier and the skip matrix are stored per tenant and seeded with
defaults, so a customer retunes them without a release.

#### Scenario: A low-tier vendor's process visibly collapses

- **GIVEN** a vendor engagement scoring below 25
- **WHEN** tiering completes
- **THEN** the tier is Low
- **AND** the diligence, questionnaire, scoring and findings stages are marked skipped, each
  carrying the tier rule that skipped it, the person and the time
- **AND** the approval gate is **not** skipped
- **AND** the lifecycle shows seven active stages instead of twelve, so the proportionality is
  visible rather than implied

#### Scenario: The reviewer can see why the tier came out as it did

- **GIVEN** a completed tiering assessment
- **WHEN** the reviewer opens it
- **THEN** each factor shows its answer, its weight and the points it contributed
- **AND** the distance to the next threshold is shown, so "what would change this" is answerable
  without re-running the form

---

### Requirement: The lifecycle is data, and a gate can never be skipped (V1, V2)

The staged lifecycle is rows in `vendor_stages`, one set per engagement per cycle — not branches
in code (ER ¶101). Adding, reordering or re-gating a stage is a data change.

`approval` is a gate. A gate exits only on an approval record decided **for the current attempt**,
and a gate is never skipped regardless of tier (spec ¶82). This is enforced by a database `CHECK`
that `is_gate` and `status = 'skipped'` cannot both hold, because the violation of this rule is a
control failure, not a bug.

`tiering` is required and unskippable but is **not** a gate: exiting it requires a computed tier,
not a signed approval.

Three transitions exist and no others: **advance** (only with zero blockers), **send back** (to
any earlier stage, resetting everything at or after the target), and **skip** (only where the
tier permits, never a gate, always with a reason and an actor).

#### Scenario: A send-back invalidates a granted approval without erasing it

- **GIVEN** an engagement whose approval gate was passed
- **WHEN** it is sent back to the findings stage
- **THEN** every stage from findings onward resets to not started
- **AND** the approval row is **not** modified — it is append-only and remains in the record
- **AND** the gate no longer counts it, because the approval was decided before the stage
  restarted
- **AND** a new approval is required to pass the gate again

#### Scenario: Exit criteria name the thing that clears them

- **GIVEN** a questionnaire stage with three unanswered questions and one missing evidence file
- **WHEN** the owner opens the stage
- **THEN** the blockers are listed as actions, each linking to the exact question or upload that
  clears it
- **AND** the advance control is disabled until none remain

---

### Requirement: The approval decision is four-valued, with segregation of duties (V3, V4)

An approval records one of **approve**, **approve with conditions**, **defer** or **reject**, with
the approver, the rationale and the time (ER ¶122). Approving with conditions records those
conditions, and each becomes a task.

The decider must differ from **both** the vendor's business owner and the person who submitted
the stage. The check runs server-side and is recorded in the audit trail; the interface enforces
it while the approver is being chosen, not after the form is submitted.

An engagement cannot be approved while it carries an unmitigated critical finding.

#### Scenario: A disqualified approver is unavailable, with the reason visible

- **GIVEN** an approval form on an engagement whose business owner is Priya Nair and whose stage
  was submitted by Sam Ortiz
- **WHEN** the approver is chosen
- **THEN** both names appear but cannot be selected, each annotated with why
- **AND** submitting either server-side is refused with a typed error, because the interface is a
  convenience and never the enforcement

---

### Requirement: A vendor answers for itself, through a link that expires (V11)

A questionnaire is issued to a vendor contact as a self-service link (spec ¶83). The vendor
answers, attaches evidence per question, and submits — without an account.

The token is stored **hashed**, expires, can be revoked, and grants access to exactly one
assessment. It carries no tenant identifier; the tenant is resolved from the token. Portal
endpoints are rate limited, and uploaded files pass the same magic-byte allowlist and size cap
the evidence uploader enforces.

This is the only externally reachable write path in the platform, and neither signed document
addresses its security. The design above is proposed, not transcribed.

#### Scenario: An expired link reveals nothing

- **GIVEN** a portal token past its expiry
- **WHEN** the vendor opens the link
- **THEN** they are told the link has expired and who to contact
- **AND** no vendor name, question, answer or tenant identifier is disclosed

---

### Requirement: Residual risk is derived from the answers, and controls can only reduce it (V7)

The residual score is derived from the inherent tier and the vendor's control answers (spec ¶84),
per domain and then weight-averaged, and is **clamped so it can never exceed the inherent score**
— controls reduce risk; they never add it.

A vendor answering "no" to any critical-control question is floored at High regardless of its
other answers.

The clamp and the floor are reported as their own steps in the breakdown, never folded silently
into the number.

#### Scenario: Perfect answers do not produce zero risk

- **GIVEN** an engagement with inherent 80 and every question answered "yes"
- **WHEN** residual is computed
- **THEN** residual is 24, not 0
- **AND** the breakdown states that control answers may reduce inherent risk by at most 70%,
  because a questionnaire is a claim and not a proof

---

### Requirement: Reviews cannot drift later each cycle

`next_reassessment_on` is computed from the cadence schedule, **not** from the completion date
(ER ¶101). A review completed three weeks late does not push the following review three weeks
out.

A reassessment opens a new cycle: intake and tiering carry forward, the engagement re-enters at
the diligence stage, and the previous cycle's stages, assessment and score remain readable.

#### Scenario: A late review does not move the next one

- **GIVEN** an annual cadence with a review due 1 March
- **WHEN** it is completed on 22 March
- **THEN** the next review is due 1 March the following year, not 22 March

---

### Requirement: Offboarding is an evidenced exit, and nothing is deleted

Termination records access revocation with who and when, a vendor-facing attestation recorded as
an assessment, a contract exit-provisions review, and a completion certificate stored as evidence
(ER ¶127).

A terminated vendor is **archived, never deleted** (rule 6). Its assessments, findings, approvals
and history remain readable, because the audit question is about a period, not about who is a
supplier today.

#### Scenario: An archived vendor is still auditable

- **GIVEN** a vendor terminated eight months ago
- **WHEN** an auditor asks what due diligence was performed before it was onboarded
- **THEN** every assessment, finding, approval and stage transition is still readable
- **AND** the vendor does not appear in the active register

---

### Requirement: A vendor finding is tracked, and remediation is a task

A finding carries severity, domain, status and the response that produced it. Remediation is
created as a **task in the tasks module**, not a vendor-local to-do list, so it inherits
assignment, SLA, transitions, CAPA and every dashboard that already counts work.

A finding may be accepted with a rationale and a **required future expiry**, matching the risk
acceptance rule the vulnerabilities module already enforces. A lapsed acceptance stops clearing
the approval gate.

`promoted_risk_id` exists and is nullable. **Promotion into the risk register is not implemented
in this change** — `modules/risk/` does not exist yet — so spec ¶85 and the ¶109 exit criterion
are not fully satisfied until the risk slice lands. This is a stated shortfall, not an oversight.

#### Scenario: An open critical finding suspends an onboarded vendor

- **GIVEN** an active vendor with no open findings
- **WHEN** a critical finding is raised against it
- **THEN** the vendor is flagged automatically and the change is audited with a machine actor
- **AND** when the finding is closed or accepted, the vendor returns to active, also audited

---

### Requirement: Vendor documents carry their coverage window and expire visibly

A SOC 2 report, DPA or certification records the period it **covers**, not merely when it was
issued. Expiry is shown as a countdown on the row, and a document inside the renewal window is
surfaced in the register's next-action column.

A reviewed document can stand as audit evidence and is linked to the evidence record (ER ¶109).

#### Scenario: A stale SOC report is impossible to miss

- **GIVEN** a SOC 2 Type II covering a period that ended fourteen months ago
- **WHEN** the vendor is opened
- **THEN** the document row reads as expired with the coverage window shown
- **AND** the vendor's next action is to request a current report
- **AND** the reader never has to subtract two dates in their head to discover it

---

### Requirement: A SOC report is reviewed into fields, not filed as a PDF

A vendor's SOC 2 report is recorded as a structured review — report kind and type, the audit
period it covers, the criteria included, the auditor's opinion, bridge-letter status, whether
findings were material, and whether the complementary user entity controls were reviewed
(ER ¶110).

The ER is explicit that this is the point: *"This structured review is precisely the CC9.2
evidence an auditor asks for."* A PDF in a folder is not that. `SOC2:CC9.2` is already in Verity's
seeded content and always in scope, so this is the artefact that lets a tenant answer it.

The reviewed report links to the evidence record, and its coverage window drives the expiry
countdown.

#### Scenario: An unqualified opinion with material findings is not silently reassuring

- **GIVEN** a SOC 2 Type II with an unqualified opinion but material findings noted
- **WHEN** the review is recorded
- **THEN** both facts are shown together at the top of the review
- **AND** the opinion alone is never presented as the summary, because "unqualified" and "nothing
  went wrong" are not the same statement

---

### Requirement: The fourth party is registered, not just scored

Fourth-party reliance is one of the five tiering factors, and it is also a register: which
subprocessors a vendor uses, where they hold data, and what the vendor is obliged to tell you
when that list changes (ER ¶126).

A subprocessor that is itself a vendor in the register is linked to that record rather than
duplicated, using the `links` primitive where `vendor` is already an allowed type on both sides.

#### Scenario: A shared subprocessor is visible across vendors

- **GIVEN** two vendors that both subprocess to the same cloud provider
- **WHEN** either vendor is opened
- **THEN** the shared subprocessor is the same record, not two unlinked names
- **AND** a concentration question — "how much of our estate depends on this one fourth party" —
  is answerable

---

### Requirement: Intake is the front door, and a request is not yet a vendor

A vendor begins as a request: who is asking, for what service, with what data, and why. A request
that is declined is recorded with its reason and never becomes a vendor row; a request that is
accepted creates the vendor and its first engagement in one transaction.

This keeps the register a list of vendors the organisation actually uses, rather than a list of
everything anyone ever proposed.

#### Scenario: A declined request leaves a trail without polluting the register

- **GIVEN** an intake request for a tool the security team rejects
- **WHEN** it is declined with a reason
- **THEN** no vendor or engagement is created
- **AND** the request, its reason and its decider remain readable, so the same tool arriving again
  next quarter is recognisable

---

### Requirement: A screen with no data source says so (V14)

`vendor_scorecards`, `vendor_signals` and `discovered_apps` are built, but nothing feeds them
until Phase 2 connectors exist — and the scorecard providers are not in any phase's connector
catalogue. Every row is manually entered until then.

Those surfaces state that no data source is connected. They do **not** render an empty table.

On a monitoring surface, *"we are watching and found nothing"* and *"we are not watching"* look
identical and mean opposite things. Only one of them is safe to act on, so the interface must
never let the reader mistake the second for the first.

#### Scenario: An unmonitored vendor does not look like a clean one

- **GIVEN** a vendor with no scorecard provider connected
- **WHEN** its monitoring tab is opened
- **THEN** it reads "No rating source connected" with what connecting one would provide
- **AND** it does not show a rating of zero, an empty chart, or a green state
