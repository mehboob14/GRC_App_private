# Identity and access: native auth, MFA, RBAC, memberships

## Why

Everything above this change has a place for people to live but nowhere for a person to be. The
provider plane registers a company; this change is what puts the company's first admin inside it,
lets that admin invite others, and is what every later module's `require(permission)` and
ownership filter hang off.

It is also the change that makes ADR-0011 real. Up to now "a user is a global identity;
membership is `tenant_memberships`" has been a decision. This change puts the join table in, puts
every in-tenant person reference on it, and proves that a second membership for the same user needs
no schema change — which is the Week 1 demo criterion.

This change belongs to **Phase 1, deliverable 1.1 — Foundation**. It depends on `add-audit-trail`
and `add-provider-plane`.

## What changes

- **Migration**: `users`, `credentials`, `user_identities`, `tenant_memberships`, `groups`,
  `group_members`, `permissions`, `roles`, `role_permissions`, `role_assignments`. Every
  tenant-owned table gets RLS and its policy in the same migration.
- `backend/src/verity/modules/iam/` — the vertical slice.
- **Native auth**: login, self-service trial signup (tenant + first user + first membership, on top
  of the registration service from `add-provider-plane`), password change, and TOTP MFA required
  for the built-in Admin role.
- **`user_identities`** is created and left unused — the federation seam, built now so Phase 3
  federates additively (ADR-0006).
- **RBAC**: flat `module:action` permission keys, roles as named bundles, assignment to a membership
  or a group, with the auditor time-box on `role_assignments`.
- **`require(permission)`** and the object-scope hook, completing the placeholders in `core/deps.py`.
- **Built-in roles** seeded per tenant at creation: Admin, Compliance Manager, Control Owner,
  Employee, Auditor — with the permission sets recorded in `design.md`.
- Every state-changing route writes the audit trail in the same transaction.
- Isolation tests covering two tenants *and* one user with memberships in both.

## Non-goals

- **No external IdP.** `user_identities` is empty. SSO, OIDC, and SAML are Phase 3 (ADR-0006).
- **No access reviews.** Phase 3.
- **No invitation email delivery.** Creating an invitation and a pending membership is in scope;
  delivering the email is the notifications module.
- **No password-reset email delivery.** The token is issued and verified; delivery is notifications.
- **No frontend.**
- **No other modules.** Compliance, evidence, tasks, documents, risk, vendors, assets,
  vulnerabilities, connectors, approvals, AI — none.

## Modules touched

`iam` (new). Consumes `tenancy` (registration service, for self-service signup) and `audit`
(`AuditService`) through their service interfaces only. Completes the placeholders in `core/deps.py`.

## Closest-review flags

**This change touches tenant isolation, authentication, authorization, and the audit trail. All
four.**

- It is the first change that puts a real person inside a tenant, so it is the first change that can
  fail a cross-tenant access in anger rather than against a probe table.
- It completes `require(permission)`. Every later module inherits whatever this gets wrong.
- It stores password hashes and MFA secrets. Both must be absent from logs, errors, responses, and
  audit snapshots — the deny-list from `add-audit-trail` is what enforces the last of those.
- It is the change whose schema is **derived**, because the ER diagrams for identity are stale (see
  below). Every derived column is listed in `design.md` for explicit approval.

## Schema status — derived, for approval

The ER identity diagrams are byte-identical to the pre-identity-update backup. They still show
`USERS.tenant_id`, "unique per tenant" email, `GROUP_MEMBERS(user_id)`, and no `TENANT_MEMBERSHIPS`
box. The prose of the same document, plus ADR-0011 and `data-model.md`, describe the membership
model. Per the review decision, this change derives the column lists from the prose and the ADRs,
lists every derived column in `design.md`, and includes a task to update the ER document.

The auditor time-box lives on `role_assignments` per the ER diagram and the reference project, not
on `tenant_memberships`. ADR-0011's wording is noted as a clarification in the doc task.

`engagement_id` is a nullable uuid with **no foreign key** in this migration. The constraint is
added when the compliance module creates `engagements`.
