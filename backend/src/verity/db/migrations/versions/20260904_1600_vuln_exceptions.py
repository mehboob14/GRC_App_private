"""Vulnerability exceptions: a requested-and-decided waiver, not a one-step one.

Accepting risk was a single act — the approver typed a reason and an expiry and
the finding moved to ``accepted``. That records the decision but not the case for
it, and nowhere to put the three things a reviewer actually needs: how long, why
it is needed, and what could go wrong if it is granted.

This table holds the request and the decision as separate steps, so the finding
carries the argument as well as the outcome. ``vuln_instances.accepted_*`` stays
as the denormalised current-waiver view, which is what the register, the KPI
counts and the expiry sweep already read — nothing built on those changes.

Expiry is stored as an absolute timestamp derived from the requested duration:
the requester thinks in "90 days", but a stored duration would silently mean a
different date depending on when it was approved.

Revision ID: c5d92a68b31f
Revises: b3c81f47a205
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import conv

from verity.db.rls import disable_rls, enable_rls, grant_crud

revision = "c5d92a68b31f"
down_revision = "b3c81f47a205"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "vuln_exceptions"
#: requested -> approved | rejected; approved -> expired | revoked. Terminal
#: states are never deleted (rule 6): a withdrawn waiver is part of the record.
_STATUSES = ("requested", "approved", "rejected", "expired", "revoked")


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    joined = ", ".join(f"'{v}'" for v in _STATUSES)
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("tenant_id", _UUID, nullable=False),
        sa.Column("instance_id", _UUID, nullable=False),
        # -- the request --------------------------------------------------------
        # rule 3: a person in a tenant is a membership, never a global user.
        sa.Column("requested_by_membership_id", _UUID, nullable=True),
        sa.Column(
            "requested_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("potential_risks", sa.Text(), nullable=False),
        sa.Column("compensating_controls", sa.Text(), nullable=True),
        # -- the decision -------------------------------------------------------
        sa.Column("status", sa.Text(), nullable=False, server_default="requested"),
        sa.Column("decided_by_membership_id", _UUID, nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        # Absolute, and only set once approved — see the module docstring.
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name=f"fk_{_TABLE}__tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["vuln_instances.id"],
            ondelete="CASCADE",
            name=f"fk_{_TABLE}__instance_id",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__requested_by",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_membership_id"],
            ["tenant_memberships.id"],
            ondelete="SET NULL",
            name=f"fk_{_TABLE}__decided_by",
        ),
        sa.CheckConstraint(f"status IN ({joined})", name=conv(f"ck_{_TABLE}__status_valid")),
        # A waiver with no end date is a silent permanent one, which is exactly
        # what an auditor flags. Enforced here so it cannot be bypassed.
        sa.CheckConstraint(
            "duration_days > 0 AND duration_days <= 365",
            name=conv(f"ck_{_TABLE}__duration_bounded"),
        ),
        # An approved waiver must say when it lapses; an undecided one must not
        # pretend to.
        sa.CheckConstraint(
            "(status = 'requested' AND expires_at IS NULL) OR "
            "(status <> 'requested' AND (status <> 'approved' OR expires_at IS NOT NULL))",
            name=conv(f"ck_{_TABLE}__expiry_matches_status"),
        ),
        # A decision has to say who made it and when.
        sa.CheckConstraint(
            "status = 'requested' OR decided_at IS NOT NULL",
            name=conv(f"ck_{_TABLE}__decision_recorded"),
        ),
    )
    # tenant_id first, per rule 1.
    op.create_index(f"ix_{_TABLE}__tenant_id_instance_id", _TABLE, ["tenant_id", "instance_id"])
    op.create_index(f"ix_{_TABLE}__tenant_id_status", _TABLE, ["tenant_id", "status"])
    # One live request per finding: a second pending waiver on the same finding
    # is two people asking for the same thing and one of them being ignored.
    op.create_index(
        f"uq_{_TABLE}__one_open_per_instance",
        _TABLE,
        ["tenant_id", "instance_id"],
        unique=True,
        postgresql_where=sa.text("status = 'requested'"),
    )
    enable_rls(_TABLE)
    grant_crud(_TABLE)


def downgrade() -> None:
    disable_rls(_TABLE)
    op.drop_index(f"uq_{_TABLE}__one_open_per_instance", table_name=_TABLE)
    op.drop_index(f"ix_{_TABLE}__tenant_id_status", table_name=_TABLE)
    op.drop_index(f"ix_{_TABLE}__tenant_id_instance_id", table_name=_TABLE)
    op.drop_table(_TABLE)
