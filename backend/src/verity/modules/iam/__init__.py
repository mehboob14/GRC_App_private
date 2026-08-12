"""Users, groups, roles, permissions, identities.

A user is a global identity; membership in a tenant is `tenant_memberships` (ADR-0011).
`users`, `credentials`, and `user_identities` carry no `tenant_id`. `user_identities` is
the provider-agnostic federation seam, built now and used in Phase 3 (ADR-0006).

Not implemented yet. See docs/product/delivery-plan.md for the phase this belongs to
and backend/CLAUDE.md for the file layout a module uses.
"""
