"""audit_log: a vendor contact is a fourth kind of actor

The vendor questionnaire portal is the platform's first path on which a state
change is made by somebody who is not a member of the tenant and not the system.
They hold a token, not a session, and giving them a tenant_memberships row would
break rule 3 — a membership means a person who may sign in.

The audit table was built for this. actor_type/actor_id is a polymorphic pair with
no foreign key precisely because "one foreign key cannot point at
tenant_memberships, platform_admins, and nothing at once"; a vendor contact is the
fourth case of the same shape, and the paired CHECK that ties a NULL actor_id to
the system actor still holds because a vendor contact carries one.

Without this the portal would have to record every answer as the system, and
"who answered this question" — the first thing an auditor asks about a vendor
questionnaire — would have no answer in the trail.

Revision ID: c8e1a4b62f39
Revises: b6d3f8a25c07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8e1a4b62f39"
down_revision: str | None = "b6d3f8a25c07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_audit_log__actor_type_valid"
_OLD = ("membership", "platform_admin", "system")
_NEW = (*_OLD, "vendor_contact")


def _recreate(values: tuple[str, ...]) -> None:
    joined = ", ".join(f"'{v}'" for v in values)
    # Raw SQL rather than op.create_check_constraint: the metadata naming
    # convention would re-apply itself and produce ck_audit_log__ck_audit_log__...
    op.execute(sa.text(f"ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS {_CONSTRAINT}"))
    op.execute(
        sa.text(
            f"ALTER TABLE audit_log ADD CONSTRAINT {_CONSTRAINT} CHECK (actor_type IN ({joined}))"
        )
    )


def upgrade() -> None:
    _recreate(_NEW)


def downgrade() -> None:
    # audit_log is append-only, so rows written by a vendor contact cannot be
    # deleted or rewritten to fit the narrower constraint. Refuse rather than
    # fail halfway through, and say what the operator would have to accept.
    remaining = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM audit_log WHERE actor_type = 'vendor_contact'"))
        .scalar_one()
    )
    if remaining:
        message = (
            f"{remaining} audit_log rows were written by a vendor contact. The table is "
            "append-only, so they cannot be removed or relabelled to narrow the "
            "constraint. Reversing this migration means accepting the loss of the "
            "audit trail those rows are, which is a decision for a person and not "
            "for a downgrade."
        )
        raise RuntimeError(message)
    _recreate(_OLD)
