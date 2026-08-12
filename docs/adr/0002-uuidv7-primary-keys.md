# ADR-0002: UUIDv7 primary keys everywhere

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

The platform is integration-heavy: records arrive by CSV import, connector sync, and merge from
multiple sources.

## Decision

Time-ordered UUIDs (version 7) as the primary key on every table.

## Alternatives considered

**Integer sequence keys.** Smaller and marginally faster, but collide across systems and leak row
counts. Rejected.

**UUIDv4.** Rejected: random ordering fragments B-tree indexes on insert.

## Consequences

Identifiers survive import, cross-system synchronisation, and merges without collision. Version 7
is time-ordered, so the classic index-fragmentation argument against UUIDs does not apply. Costs 8
bytes per key versus bigint, which is acceptable.
