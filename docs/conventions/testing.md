# Testing

Tests exist to make change safe. On a compliance platform, they also *are* evidence — the isolation
suite is a control.

## Layers

**Unit** — services with repositories faked. No database, fast, runs on every save.

**Integration** — real Postgres with RLS enabled, connecting as the **application role** (never a
`BYPASSRLS` role). Covers repositories, migrations, and service transactions.

**Isolation** (`backend/tests/isolation/`) — seeds two tenants and asserts that every list, read,
update, and delete path returns and touches nothing belonging to the other. **Merge blocker.** Every
new module adds its isolation test in the same change.

**E2E** (Playwright) — the journeys that must never break: login, evidence upload and mapping,
control pass/fail, approval flow, the four-hop 360 trace.

## Rules

- **Never disable RLS in a fixture.** If a test needs two tenants, create two tenants.
- Every bug fix starts with a failing test that reproduces it. No test, no fix.
- Test behaviour, not implementation. A test asserting a private method was called is a test that
  will fail on refactor and catch nothing.
- Deterministic: no real clock, no real network, no random data without a fixed seed. Freeze time
  for anything touching SLAs, staleness, or expiry — most of this product is date logic.
- Factories over fixtures for domain objects. Fixtures for infrastructure.
- Connectors test against **recorded fixtures**, never a live account in CI.

## What must have tests

Anything enforcing a compliance property: tenant isolation, audit-trail writes, append-only
enforcement, approval gates (including segregation of duties), waiver and acceptance expiry, evidence
staleness, SLA clocks, the vulnerability state machine, and the asset merge and split.

These are the properties an auditor tests. If they regress silently, the product is not what it
claims to be.

## Coverage

No target number. Coverage is a diagnostic, not a goal. A module enforcing a compliance rule with
thin tests is a problem at 95% coverage; a mapper is fine at 40%.
