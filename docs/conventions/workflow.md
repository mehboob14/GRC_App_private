# How work happens here

Spec-driven. The spec is the record of intent; the code is the consequence. This exists because
AI-assisted development makes it trivially easy to produce a working feature whose reasoning lives
only in a chat transcript nobody will ever read again.

## The loop

1. **Propose.** A change starts as a spec: what it does, what it changes, why, and how it is
   verified. Use `openspec` (`/opsx:*` in Claude Code) to scaffold the proposal, spec, design notes,
   and tasks.
2. **Review the spec, not the code.** This is where the judgment goes. A spec approved by skimming
   moves the problem one level up and makes it worse, because everything downstream implements
   against it.
3. **Implement against the spec.** The agent codes to the approved spec. Divergence from the spec is
   a spec change, not an implementation detail.
4. **Verify.** Tests, isolation suite, review checklist.
5. **Archive.** The spec becomes the permanent record of why.

## When a spec is required

Anything that adds a table or column, changes a module boundary, touches auth or tenant isolation,
adds a dependency, adds a connector, or changes an API contract.

Not required for: a bug fix with a failing test, copy changes, dependency patch bumps, or a local
refactor with no behaviour change.

## When to write an ADR instead

If the decision would be expensive to reverse and outlives the change that prompted it, it is an
ADR. Specs describe *what we are building now*; ADRs describe *what we decided and will keep
believing*.

## Review checklist

Before a change is done:

- [ ] Tenant scoping: every new table has `tenant_id` + RLS policy in the **same** migration
- [ ] `tenant_id` leads every new composite index
- [ ] Every state-changing path writes `audit_log` with before/after
- [ ] Append-only tables are only inserted into
- [ ] New ingestible table has `source`, `external_id`, `synced_at`
- [ ] Every route declares its required permission; object-scoped access filtered in the service
- [ ] No secrets in logs, exception messages, or `__repr__`
- [ ] Errors return no internals; correlation id returned instead
- [ ] Isolation tests pass; new module has an isolation test
- [ ] Loading, empty, and error states exist for every new data view
- [ ] Docs updated in the same commit
- [ ] No `any` in TypeScript; no boundary violations between backend modules

## What "done" means

Deployed from documented steps, migration reversible or documented as not, tests green including
isolation, docs current, and the feature demonstrated against its spec's verification section.
Not "the code is written."
