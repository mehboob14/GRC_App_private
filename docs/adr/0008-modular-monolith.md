# ADR-0008: Modular monolith, not microservices

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

Fifteen bounded contexts, a small team, and a product where cross-module traceability (the
360-degree model) is the core value proposition.

## Decision

One deployable backend with hard module boundaries under `modules/`. Modules communicate through
service interfaces and never reach into another module's repository, models, or tables. Background
work runs in separate worker processes from the same codebase.

## Alternatives considered

**Microservices per module.** Rejected: the 360-degree linkage is a join-heavy read model that
would become distributed queries, and sagas would be needed for flows that are currently one
transaction. The team is too small to absorb the operational cost.

**No internal boundaries.** Rejected: fifteen modules without enforced boundaries becomes
unmaintainable, and this is exactly the failure mode AI-assisted development accelerates.

## Consequences

Simple deployment and real transactions across the linkage model. The discipline moves to code
review and import rules: a boundary violation is easy to write and must be caught. Extraction stays
possible later because the boundaries are real.

**Revisit per-module when:** it needs to scale independently, or a separate team owns it.
