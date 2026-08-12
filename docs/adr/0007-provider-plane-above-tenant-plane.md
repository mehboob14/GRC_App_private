# ADR-0007: A provider plane above the tenant plane

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

The product is sold one account per company and operated from an internal panel. The operator and
the customers are different populations.

## Decision

Platform admins, the tenants register, branding, and provisioning are global tables with no
`tenant_id`. Every other table is tenant-scoped. Users are a **global identity** (`users`,
`credentials`, `user_identities` carry no `tenant_id`; email is unique globally); a user's place in a
tenant is a `tenant_memberships` row — see [ADR-0011](0011-tenant-membership-model.md).

## Alternatives considered

**Model the operator as just another tenant.** Rejected: weakens the boundary and forces operator
features through tenant-scoped queries.

**Global users joining many tenants.** Rejected: that is a collaboration product, not a compliance
platform, and it weakens isolation for no benefit.

## Consequences

Two logins and two populations, deliberately. The tenant profile has a natural home, so company
details captured once at registration flow into every generated document. A person working at two
customer companies has two accounts, which is correct for this product.
