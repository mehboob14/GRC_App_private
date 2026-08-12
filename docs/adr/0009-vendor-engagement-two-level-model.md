# ADR-0009: Vendor and engagement, a two-level TPRM model

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

The same vendor serving two departments with different data represents two different risks.
Dedicated TPRM products all model this.

## Decision

The vendor is the organisation; an engagement is one use of it, with its own tier, owner,
assessments, and contract. Engagement references are optional throughout, so a small organisation
can ignore them.

## Alternatives considered

**A single vendor record with one tier and one risk level.** Rejected: averaging two uses loses
exactly the information the tiering engine exists to produce.

## Consequences

Risk is scoped to the relationship rather than averaged across uses. Every vendor query must decide
whether it operates at vendor or engagement level. Optionality keeps the simple case simple, at the
cost of nullable engagement references throughout the module.
