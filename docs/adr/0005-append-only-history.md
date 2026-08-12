# ADR-0005: Append-only history tables

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

Immutability of the audit trail is a compliance property the product sells. Auditors test it.

## Decision

`audit_log`, `task_transitions`, `vuln_transitions`, `check_results`, `readiness_snapshots`,
`kri_measurements`, and `document_versions` are insert-only. No row is ever updated or deleted.
Enforced by revoked grants, not convention. `check_results` is partitioned by month from the first
migration.

## Alternatives considered

**Mutable rows with an updated timestamp.** Rejected: destroys the record the product exists to
produce.

**Database triggers writing shadow tables.** Rejected: hides the write path and complicates
migrations.

## Consequences

Full reconstructable history. Storage grows monotonically, handled by partitioning the one hot
table. Appending is the cheapest thing a database does, so write cost is not a concern.
Corrections are new rows, never edits, and the UI must present them that way.
