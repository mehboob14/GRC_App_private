# Architecture Decision Records

One file per decision that would be expensive to reverse. Numbered, immutable once accepted.

**Do not edit an accepted ADR.** If a decision changes, write a new ADR that supersedes it and mark
the old one `Superseded by ADR-XXXX`. The history of why you believed something is the point.

Write an ADR when a choice affects the schema, a module boundary, a security property, an external
dependency, or anything a future engineer would otherwise have to reverse-engineer from code. Skip
it for reversible, local choices.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-shared-schema-multi-tenancy-with-rls.md) | Shared schema multi-tenancy with RLS | Accepted |
| [0002](0002-uuidv7-primary-keys.md) | UUIDv7 primary keys | Accepted |
| [0003](0003-hybrid-linkage-model.md) | Hybrid linkage model | Accepted |
| [0004](0004-evidence-anchors-to-controls.md) | Evidence anchors to controls | Accepted |
| [0005](0005-append-only-history.md) | Append-only history tables | Accepted |
| [0006](0006-keycloak-as-identity-provider.md) | Identity: native auth now, external Keycloak IdP later | Accepted |
| [0007](0007-provider-plane-above-tenant-plane.md) | Provider plane above tenant plane | Accepted |
| [0008](0008-modular-monolith.md) | Modular monolith, not microservices | Accepted |
| [0009](0009-vendor-engagement-two-level-model.md) | Vendor and engagement, two-level TPRM | Accepted |
| [0010](0010-vulnerability-definition-and-instance.md) | Definition and instance vulnerability model | Accepted |
| [0011](0011-tenant-membership-model.md) | Users are global; membership is `tenant_memberships` (global-users-ready) | Accepted |
