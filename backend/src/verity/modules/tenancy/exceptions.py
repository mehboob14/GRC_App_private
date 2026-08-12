"""Tenancy's domain errors. Codes are stable: the frontend switches on them."""

from __future__ import annotations

from verity.core.errors import Conflict


class SlugConflict(Conflict):
    """The requested slug is already a tenant's subdomain."""

    code = "slug_conflict"
    message = "A tenant with this slug already exists."


class IdempotencyKeyConflict(Conflict):
    """The idempotency key was already used with a different request body.

    Silently returning the first result would hide a client bug
    (add-provider-plane/design.md, "Idempotency").
    """

    code = "idempotency_key_conflict"
    message = "This idempotency key was already used with a different request."


class CustomDomainConflict(Conflict):
    """The requested custom domain already belongs to a tenant."""

    code = "custom_domain_conflict"
    message = "This custom domain is already in use."


class EnrollmentConflict(Conflict):
    """MFA enrollment was attempted from the wrong state.

    Either the admin is already enrolled (a re-enrollment must be an explicit,
    audited reset flow, which Week 1 does not have) or confirmation arrived before
    enrollment started.
    """

    code = "mfa_enrollment_conflict"
    message = "MFA enrollment cannot proceed from the current state."
