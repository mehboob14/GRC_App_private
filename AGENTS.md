# Agent instructions

This file exists for tools that look for `AGENTS.md` (Codex and others).

**The authoritative instructions are in [CLAUDE.md](CLAUDE.md).** Read it first, then the
directory-specific files:

- [backend/CLAUDE.md](backend/CLAUDE.md) — Python, FastAPI, SQLAlchemy conventions
- [frontend/CLAUDE.md](frontend/CLAUDE.md) — React, TypeScript, Tailwind conventions
- [docs/conventions/workflow.md](docs/conventions/workflow.md) — spec-driven process and the review
  checklist
- [docs/adr/](docs/adr/) — decisions already made; do not re-litigate them in code

## The short version

1. Specs before code. No spec, no implementation — write the spec and stop for review.
2. Never invent schema. If the column you need is not in the data model, say so and stop.
3. Never weaken tenant isolation, auth, or the audit trail to make something pass.
4. `error` is never `fail`.
5. AI drafts; humans decide. Nothing publishes or changes state without human approval.
6. Update the docs in the same change.
