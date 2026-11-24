# Proposal: the connection platform and the Go collector runtime

## Why

Every connector in the evidence connectors plan needs the same machinery: a catalogue and connect
screens generated from content, credentials handled safely, a test step, scope, health, and a runtime
that reads provider APIs at scale without breaking tenant isolation. Building that once, before the
first new connector, is work packages F4 and F5 of
`docs/product/evidence-connectors/04-phases-and-work-packages.md`. The owner wants collectors in Go.

## What

- **Connection platform (F4):** provider content and setup guides as sealed content; the catalogue,
  before you connect screen, connect wizard per credential pattern, OAuth and cloud role flows, permission
  probe, health and expiry reminders; one card per provider joining sign in and evidence.
- **Collector runtime (F5):** a Go worker container (`verity-collector`) that takes jobs from a Redis
  Stream, gets a short lived credential from an internal API of the core, posts normalised observations
  back, and never touches the database; JSON Schema contracts shared by Go and Python; an
  `observations` store with row level security; leases, heartbeats and completeness.
- **Build and deployment:** a distroless collector image built by the existing `deploy.sh`, a compose
  service with resource caps and a read only filesystem, separate collector configuration and secrets on
  the host, gradual switch on, rollback as today.
- **Migration:** GitHub keeps running in Python until a Go port proves parity on recorded fixtures and in
  two weeks of shadow runs.

Design: `design.md`. Decision record: `docs/adr/0016-go-collectors-beside-the-python-core.md` (Proposed).

## Not in this change

Any provider beyond GitHub's port and a fake test provider; those are packages C1 onward. CI built
images and a registry (decision R3). A staging server (decision R5).
