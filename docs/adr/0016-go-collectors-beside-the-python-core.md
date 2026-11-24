# ADR-0016: Collect provider data in Go workers; keep evaluation in the Python core

**Status:** Proposed
**Date:** 2026-11-24

## Context

Verity plans about thirty connectors (`docs/product/evidence-connectors/`). Each reads a provider's API
on a schedule, pages through large populations (every user, device, repository, sign in event), and
honours rate limits, for every connected workspace. Today the one built connector (GitHub) is Python
inside the Celery worker, and it already separates collecting (`github.collect`) from judging (the
result functions). The owner wants collectors written in Go. The rules that make Verity safe live in the
Python core: row level security bound per transaction (CLAUDE.md rules 1 and 2), audit rows in the
same transaction (rule 5), envelope encrypted credentials (rule 8), checks as reviewed content mapped to
controls. The production host is a shared server where the owner runs every command by hand.

## Decision

1. **Collectors are Go workers in their own container (`verity-collector`).** They authenticate to
   providers, page, respect rate limits, normalise what they read into versioned observation types, and
   report completeness. They hold no pass or fail logic.
2. **Evaluation, scheduling, scope, credentials, evidence and audit stay in the Python core.** A check
   is evaluated once per capability over normalised observations, whatever the provider.
3. **Collectors never open the database.** Jobs arrive on a Redis Stream; collectors fetch a short lived
   credential and post observations to an internal API of the core, which binds the tenant in the
   transaction. Jobs carry no secrets.
4. **One contract, generated twice.** Observation and job schemas are JSON Schema files in
   `contracts/`; Go structs and Python models are generated from them and checked in CI.
5. **One binary, all providers**, scaled by running more replicas; per connection exclusivity is a lease
   the core grants.

## Alternatives considered

- **Keep everything in Python (Celery).** Works today and needs no new toolchain. Rejected as the
  default for new providers because the owner chose Go, and because long paging jobs with many
  concurrent connections are a better fit for goroutines than for Celery prefork workers on a small
  shared host. Python stays for GitHub until the Go port proves parity.
- **Go collectors that also evaluate.** Fewer moving parts per provider, but checks would then be code
  in two languages, the same check key could mean different things per provider, and a content change
  would need a collector release. Rejected.
- **Go collectors writing to Postgres directly.** Simplest data path, but every collector would carry
  database credentials and would have to reproduce tenant binding and audit correctly. Rejected:
  isolation must have one owner.
- **Celery from Go, or a new broker (NATS, RabbitMQ).** Celery's wire protocol from Go is awkward to
  keep compatible; a new broker is one more service on a shared host. Redis Streams already run in
  Redis 7, give consumer groups, acknowledgement and reclaiming of stalled jobs. Chosen.
- **Serverless collectors (Lambda, Cloud Run).** Rejected for now: production is one shared server,
  and customers may need to allowlist one stable egress address.

## Consequences

- A second toolchain (Go) in the repository, in CI and in the image build. Developers need Go
  installed; `docs/runbooks/local-setup.md` gains it.
- An internal API surface on the core that must never be reachable from the internet (a separate
  port, not proxied by the web container, plus a signed service token).
- Observations become stored data with their own retention and row level security.
- Revisit when collectors need to run close to customers (self managed systems behind firewalls), or
  when the volume calls for a managed queue.
