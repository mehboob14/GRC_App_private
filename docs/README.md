# Documentation index

**Architecture** — how the system is shaped
- [overview.md](architecture/overview.md) — the whole system in one page
- [multi-tenancy.md](architecture/multi-tenancy.md) — isolation, the most important property here
- [data-model.md](architecture/data-model.md) — entities, linkage, and the modules
- [integrations.md](architecture/integrations.md) — the connector framework
- [ai-features.md](architecture/ai-features.md) — where AI is used and its hard limits

**Decisions** — [adr/](adr/) — why things are the way they are. Read before proposing a change.

**Conventions** — how we write things
- [database.md](conventions/database.md), [api.md](conventions/api.md),
  [testing.md](conventions/testing.md), [git.md](conventions/git.md),
  [workflow.md](conventions/workflow.md)
- Backend and frontend specifics live in `backend/CLAUDE.md` and `frontend/CLAUDE.md`

**Security** — [security/baseline.md](security/baseline.md)

**Product** — [product/delivery-plan.md](product/delivery-plan.md)

**Runbooks** — [runbooks/local-setup.md](runbooks/local-setup.md)

## Rule

A change that makes a doc wrong updates the doc in the same commit. A stale doc is worse than no
doc, because both people and agents will believe it.
