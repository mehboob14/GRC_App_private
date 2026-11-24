# Tasks: the connection platform and the Go collector runtime

Each task names what proves it. Tick only with the commit and what was verified. Decisions R1 to R6 are in
`design.md` section 10; R1 (accept ADR-0016) comes first.

## 0. Before code

- [ ] 0.1 Owner accepts ADR-0016 (R1) and answers R2 to R6.
- [ ] 0.2 Go installed in the development setup; `docs/runbooks/local-setup.md` gains Go and the
      collector; CI gains a Go job (build, test with race detector, `golangci-lint`, `govulncheck`).

## 1. Contracts (shared)

- [ ] 1.1 `contracts/`: JSON Schemas for the job (`verity.collect.job/v1`), the manifest, and the first
      observation types (`identity.user`, `identity.policy`, `identity.app`, `repository`, `branch_rule`,
      `change`, `review`), versioned.
- [ ] 1.2 Generators: Go structs into `collectors/internal/contracts`, Python models into the core; a CI
      check fails when generated files are stale. Proof: a schema change without regeneration fails CI.

## 2. Core: data and internal API (Python)

- [ ] 2.1 Migration: `check_runs` gains executor, lease, collector id, job id, manifest; new
      `observations` and `observation_batches` tenant tables with RLS in the same migration; up, down, up
      on `verity_test`; the RLS coverage test passes.
- [ ] 2.2 Internal API on its own port (8100) in the api container: credential, observations (gzipped
      NDJSON, schema validation, idempotent batches, raw batch to the object store), heartbeat, complete.
      Service token verification (Ed25519, audience, expiry, collector id holds the lease).
- [ ] 2.3 Credential hand out per pattern (design 2.2); never logged; audit of each hand out without the
      value.
- [ ] 2.4 Worker: due connections create runs with leases and `XADD` jobs; `finalise_run` evaluates the
      capability checks over observations, files evidence, refreshes outcomes; stalled leases expire runs as
      `error` with a reason.
- [ ] 2.5 Isolation tests: a token for run A cannot post to run B; a run of tenant A cannot write tenant B
      rows; with the app role.
- [ ] 2.6 Outbound guard for customer supplied URLs (HTTPS only, no private or link local addresses unless
      allowlisted), used by every place that fetches a customer URL.

## 3. Connection platform (F4)

- [ ] 3.1 Provider content schema, loader, seal; GitHub's entry and guide written as content.
- [ ] 3.2 `GET /integrations` and `GET /integrations/{provider}`; catalogue state per workspace.
- [ ] 3.3 `POST /connections` validated by the provider's field schema; OAuth start and callback with state
      and PKCE in Redis; cloud role external id per workspace and template link.
- [ ] 3.4 Test step: a `probe` job and per check readiness in the response.
- [ ] 3.5 Health: lag, per capability state, completeness, plain errors with fixes, credential expiry
      reminders through Notifications.
- [ ] 3.6 Frontend: catalogue from the API (retire `connector-catalogue.ts`), generated wizard, guide side
      panel, test results, health page, scope dialog for every resource type.
- [ ] 3.7 `tenant_sso.connection_id` and the single card joining sign in and evidence.
- [ ] 3.8 Proof: GitHub connects and runs through the new screens with unchanged results; a fake second
      provider needs content only for its screens.

## 4. Go collector runtime (F5)

- [ ] 4.1 `collectors/` module skeleton (design 5.1); `collector run | health | version`.
- [ ] 4.2 Queue consumer (consumer group, ack, reclaim after the lease), core API client, service token.
- [ ] 4.3 Runtime: worker pool, deadlines, heartbeats, retries, limiters, error classes, redacted logging.
- [ ] 4.4 `Sink`: batching, sequence numbers, completeness per type.
- [ ] 4.5 A `fake` provider and a fake provider server for tests; local compose flow from schedule to
      objective outcome.
- [ ] 4.6 Contract and fixture tests in CI.

## 5. Images and deployment

- [ ] 5.1 `collectors/Dockerfile` (multi stage, distroless, non root, version baked in).
- [ ] 5.2 Compose service (design 6.2): read only, no new privileges, all capabilities dropped, 512 MB and
      one CPU, health check; the api internal port on the network only.
- [ ] 5.3 `.env.collector.example`, the secrets folder layout, and the key generation step in
      `docs/runbooks/deployment.md`; `.gitignore` covers the real files.
- [ ] 5.4 `deploy.sh` readiness gains `collector health` and a live consumer on `collect:jobs`.
- [ ] 5.5 Runbook: switch on (`COLLECTOR_ENABLED`), switch off, rollback, reading collector logs, stuck
      stream handling. The owner runs every server command; the sheet starts with a read only survey.
- [ ] 5.6 Tell the server's owner and the client before the first deploy (design section 9).
- [ ] 5.7 First deploy with the collector idle; then a probe against an internal test account; record the
      results.

## 6. GitHub on Go

- [ ] 6.1 Port `github.collect` to `providers/github` emitting the repository, branch rule, change and
      review observations.
- [ ] 6.2 Parity on the Python fixtures: identical observations and identical check results.
- [ ] 6.3 Two weeks in shadow on production (Go stored, Python shown); compare daily; switch when identical.
- [ ] 6.4 Retire the Python GitHub collector; the connector document moves from plan to as built.
