# ADR-0007: A provider plane above the tenant plane

**Status:** Accepted (amended 2026-08-12: alternatives and consequences aligned with ADR-0011;
`tenants` RLS strengthening noted per week1-review-decisions.md item 9)
**Source:** Data Model and ER Design, Section 5

## Context

The product is sold one account per company and operated from an internal panel. The operator and
the customers are different populations.

## Decision

The provider plane — platform admins, the tenants register, branding, provisioning — sits above
the tenant boundary. `platform_admins` and `tenants` carry no `tenant_id`; `tenant_branding` and
`tenant_provisioning` reference their tenant per the ER, and all of them carry RLS policies.
`tenants` is additionally policed **on its own primary key** (`id` = the bound tenant, `SELECT`
only): it still carries no `tenant_id`, but without that policy a missing `WHERE` clause in any
tenant-plane query would list every customer company by legal name. A strengthening of this ADR,
approved in `openspec/changes/week1-review-decisions.md`, item 9.

Every other table is tenant-scoped. Users are a **global identity** (`users`, `credentials`,
`user_identities` carry no `tenant_id`; email is unique globally); a user's place in a tenant is a
`tenant_memberships` row — see [ADR-0011](0011-tenant-membership-model.md).

## Alternatives considered

**Model the operator as just another tenant.** Rejected: weakens the boundary and forces operator
features through tenant-scoped queries.

**Per-tenant user accounts instead of a global identity.** Originally chosen here, superseded by
ADR-0011: users are global, and a person at several customer companies is one account with several
memberships. The operator/customer split this ADR draws is unaffected — a platform admin is still
never a tenant user with extra permissions.

## Consequences

Two logins and two populations, deliberately: platform admins authenticate against their own
table with their own credential columns, tenant users through `credentials`/`tenant_memberships`.
The tenant profile has a natural home, so company details captured once at registration flow into
every generated document. A person working at two customer companies has **one account with two
memberships** (ADR-0011); an operator who is also a customer has an operator account and a user
account, which is correct — the planes do not share identities.
