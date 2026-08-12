"""Users, groups, roles, permissions, identities.

A user is a global identity; membership in a tenant is `tenant_memberships` (ADR-0011).
`users`, `credentials`, and `user_identities` carry no `tenant_id`. `user_identities` is
the provider-agnostic federation seam, built now and used in Phase 3 (ADR-0006).

The module owns native authentication (signup, login, TOTP, workspaces,
invitations), the RBAC tables and their management routes, and the provisioning
gates the tenancy module asks about memberships. `user_identities` is written by
nothing until Phase 3 — a unit test enforces it.
"""
