# ADR-0013: Tenant-built vendor questionnaires, snapshotted where they are used

**Status:** Accepted
**Date:** 2026-09-14

## Context

Tiering was five fixed factors with platform weights (V6), and due diligence was one global
question bank a tenant could not change (V5, which named a tenant-authored bank as Phase 2).
Real programmes pick questions from a library, add their own, and set per question the answer
type, the options and what each is worth, whether it is required, whether evidence is needed, and
which answers open a follow-up. Both questionnaires need that, and they are often confused: the
tiering one is answered by our own people about how we use a vendor and sets the tier; the due
diligence one is answered by the vendor through the portal and sets the residual score.

## Decision

- One builder for both purposes: `vendor_questionnaires` and `vendor_questionnaire_questions`,
  tenant-owned with RLS, `purpose` in (`tiering`, `due_diligence`). Options live as JSON on the
  question (key, label, score, gap flag, not applicable, note required, minimum tier).
- The shipped library stays on the global content plane (`questionnaire_templates`, now with a
  `purpose`), and tenants copy from it. Every workspace is given starting questionnaires once per
  purpose; the tiering "Standard" set is the five factors with V6's weights, and a unit test proves
  it tiers identically.
- **Snapshots, not versions.** A tiering run stores the questions and answers it used
  (`questionnaire_snapshot`, `answers`); a dispatched review copies each question onto its response
  row (`question_key`, `question_snapshot`). Editing a questionnaire never changes a stored tier,
  score or finding. Rows written against the bank keep `question_id` and keep working.
- Scoring stays in `scoring.py`: exposure points over the most the answered questions could give,
  banded by thresholds and lifted by option minimums; residual credit from the picked option.
  Scores and gap flags never reach the portal.

## Alternatives considered

**Immutable published versions of each questionnaire, with responses pointing at a version.**
Rejected: every wording fix would mint a version and a migration path for in-flight reviews, and
the snapshot already answers "what was asked" for audit.

**A nullable `tenant_id` on the global bank.** Rejected by V5 for the reason it gave: RLS, a backfill
and a changed meaning of "global" after rows exist.

**Separate tables for tiering and due diligence questionnaires.** Rejected: the builder, the
validation and the answer shapes are the same; two copies would drift.

## Consequences

Tenants own their questionnaires and past results stay explainable. The cost is duplication of
question text into snapshots (small, per use) and two read paths in `answers_with_questions`, which
normalises bank and snapshot rows into one `AskedQuestion`. Revisit if reporting needs to join
answers to a live question across reviews, which a snapshot cannot give.
