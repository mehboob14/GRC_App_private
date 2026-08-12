# Git and review

## Branches

`main` is always deployable. Work on `feat/<short-name>`, `fix/<short-name>`, `chore/<short-name>`.
Short-lived: a branch open longer than a few days is a merge conflict accumulating interest.

## Commits

Conventional commits: `feat(vendors): add tiering policy evaluation`.

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `security`.

One logical change per commit. The body explains **why**, not what — the diff already says what.

## Pull requests

Every PR states what changed, why, and how it was verified. If it touches the schema, auth, or
tenant isolation, it says so explicitly in the description so the reviewer knows where to look.

Reviewers check the [workflow checklist](workflow.md#review-checklist). The isolation suite and
migration checks are automated merge blockers — never merged red, never merged with a skip.

## Migrations in review

A migration PR gets read twice: once for the DDL and once for what happens to existing rows on a
live database. Every new tenant-owned table must enable RLS and add its policy in the same
migration. A table without a policy is a silent isolation hole and passes every other test.

## Never

- Force-push to `main`.
- Commit secrets — pre-commit secret scanning is enabled and its failure is never bypassed.
- Merge with the isolation suite skipped or red.
- Edit a migration that has run anywhere but your machine.
