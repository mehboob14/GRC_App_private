"""Seeding and token helpers for the IAM suites.

Everything goes through the real entry points — the auth service's own units of
work, ``core.security``, the migrated tables with their policies — as the
application role. Nothing bypasses RLS and nothing writes a table directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from tests.support.tenancy import totp_code
from verity.core.db import session_scope
from verity.core.security import issue_token
from verity.modules.iam.service import (
    ChallengeIssued,
    InviteResult,
    SessionIssued,
    iam_auth_service,
    iam_service,
)

SIGNUP_PASSWORD = "orbit-mango-quartz-42"  # noqa: S105 — test credential
INVITEE_PASSWORD = "delta-crimson-otter-77"  # noqa: S105 — test credential


@dataclass(frozen=True, slots=True)
class Workspace:
    """A signed-up tenant with its enrolled first admin."""

    tenant_id: uuid.UUID
    membership_id: uuid.UUID
    email: str
    totp_secret: str
    session_token: str


async def signup_workspace(
    *,
    company: str = "Acme Compliance",
    email: str = "founder@acme.example",
    password: str = SIGNUP_PASSWORD,
) -> Workspace:
    """Trial signup plus TOTP enrollment, through the real flows.

    Returns a workspace whose admin holds a live session token. The enrollment
    consumed the current TOTP step; use ``totp_code(secret, step_offset=1)``
    for the next code this admin submits.
    """
    outcome = await iam_auth_service.signup(
        company_name=company, full_name="Founding Admin", email=email, password=password
    )
    assert isinstance(outcome, ChallengeIssued), outcome
    assert outcome.next_step == "mfa_enrollment_required"
    started = await iam_auth_service.start_enrollment(challenge_token=outcome.challenge_token)
    issued = await iam_auth_service.confirm_enrollment(
        challenge_token=outcome.challenge_token, code=totp_code(started.secret)
    )
    assert isinstance(issued, SessionIssued)
    return Workspace(
        tenant_id=issued.principal.tenant_id,
        membership_id=issued.principal.membership_id,
        email=email,
        totp_secret=started.secret,
        session_token=issued.token,
    )


async def invite_directly(  # noqa: PLR0913 — the invite contract's fields
    workspace: Workspace,
    *,
    email: str,
    full_name: str,
    role_name: str,
    valid_from: date | None = None,
    valid_until: date | None = None,
) -> InviteResult:
    """Invite through the real service on the inviter's tenant-bound session.

    The role is named rather than identified because the built-in ids are minted
    per tenant at seed time; the optional window is the guest-auditor time-box.
    """
    async with session_scope(workspace.tenant_id) as session:
        roles = await iam_service.list_roles(session, tenant_id=workspace.tenant_id)
        role = next(r for r in roles if r.name == role_name)
        return await iam_service.invite_member(
            session,
            tenant_id=workspace.tenant_id,
            actor_membership_id=workspace.membership_id,
            email=email,
            full_name=full_name,
            role_id=role.id,
            valid_from=valid_from,
            valid_until=valid_until,
        )


def tenant_session_headers(membership_id: uuid.UUID) -> dict[str, str]:
    """A real tenant-plane session token, minted directly.

    The full login flow is proven in the auth suite; the other suites only need
    an authenticated caller, and ``get_current_principal`` validates this token
    against the database exactly as it would one from ``/auth/login``.
    """
    issued = issue_token(subject=membership_id, plane="tenant", typ="session")
    return {"Authorization": f"Bearer {issued.token}"}
