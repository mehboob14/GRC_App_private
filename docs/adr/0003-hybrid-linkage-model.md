# ADR-0003: Hybrid linkage model

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

The 360-degree model connects controls, evidence, risks, documents, assets, vulnerabilities,
tasks, and incidents. Some pairs are queried on every dashboard load; others are browsed rarely
but must be possible.

## Decision

Explicit join tables for hot pairs (control-requirement, evidence-control, risk-control,
check-control_template, ticket-instances). One polymorphic `links` table, indexed in both
directions, for the long tail. Direct foreign keys for one-way promotions.

## Alternatives considered

**All explicit join tables.** Roughly a dozen tables and still cannot express task-to-anything.
Rejected.

**All polymorphic.** Gives up referential integrity on exactly the joins the dashboards hammer.
Rejected.

## Consequences

Rigor where the load is, flexibility where the breadth is. The cost is two mechanisms to learn.
Adding a link means deciding which category it falls into: hot and computed, or browsed.
