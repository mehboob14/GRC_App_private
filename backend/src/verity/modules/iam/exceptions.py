"""IAM's domain errors. Codes are stable: the frontend switches on them.

The four codes the already-built frontend handles are fixed by the Week 1
contract: ``email_taken``, ``already_member``, ``invalid_invite``,
``invite_already_accepted``, and ``weak_password``. Everything else uses the
generic envelope codes from ``core.errors``.
"""

from __future__ import annotations

from verity.core.errors import AuthenticationRequired, Conflict, InvalidInput


class EmailTaken(Conflict):
    """Signup with an email that already belongs to a user."""

    code = "email_taken"
    message = "That work email is already registered."


class WeakPassword(InvalidInput):
    """The platform's password policy: at least 10 characters (decision 19 era)."""

    code = "weak_password"
    message = "Use at least 10 characters for your password."


class AlreadyMember(Conflict):
    """Inviting a person who already holds an active membership in this tenant."""

    code = "already_member"
    message = "That person is already a member of this workspace."


class InvalidInvite(AuthenticationRequired):
    """The invite token is malformed, expired, or names a membership that is gone.

    One code for every failure mode: an invite link is a bearer credential, and
    telling the caller *why* it failed would let a prober map the difference
    between "expired" and "never existed".
    """

    code = "invalid_invite"
    message = "This invite link is invalid or has expired. Ask a workspace admin to send a new one."


class InviteAlreadyAccepted(Conflict):
    """The membership behind the invite token is already active — single use."""

    code = "invite_already_accepted"
    message = "This invitation was already accepted. Sign in with your email and password."


class MfaEnrollmentConflict(Conflict):
    """Enrollment attempted from the wrong state (already enabled, or confirm
    before enroll). Mirrors the provider plane's ``EnrollmentConflict``."""

    code = "mfa_enrollment_conflict"
    message = "MFA enrollment cannot proceed from the current state."


class BuiltInRoleImmutable(Conflict):
    """Built-in roles refuse deletion; the platform's baseline cannot be removed."""

    code = "built_in_role_immutable"
    message = "Built-in roles cannot be deleted."


class DuplicateAssignment(Conflict):
    """The same role is already assigned to the same assignee for the same
    engagement — a second row would double-count in the permission union."""

    code = "duplicate_assignment"
    message = "This role is already assigned to that member or group."


class NameConflict(Conflict):
    """A tenant-unique name (group or role) is already taken."""

    code = "name_conflict"
    message = "That name is already in use in this workspace."
