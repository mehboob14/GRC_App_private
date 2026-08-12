"""create audit_log — the first table, and the first append-only one

Revision ID: ddd9734e6c34
Revises:
Create Date: 2026-08-12 19:47:11.538634

Everything the table needs to be safe ships in this one migration
(openspec/changes/add-audit-trail): the schema, the three ``tenant_id``-leading
indexes, ``ENABLE`` and ``FORCE`` row-level security with all four policies, the
application role's narrowed grant, and the append-only trigger.

Four policies rather than one, because ``audit_log`` serves both planes. Postgres
combines permissive policies with ``OR``: tenant sessions read and write their own
stream keyed on ``app.tenant_id``; provider-plane sessions read and write across
streams keyed on ``app.provider_plane = 'on'``, which only
``core.db.provider_session_scope`` sets. Rows with ``tenant_id IS NULL`` never
satisfy the tenant predicate, so provider-plane rows are invisible to every tenant
by construction. There is no UPDATE or DELETE policy: with RLS enabled and no policy
for a command, the command matches nothing — a third wall behind the revoked grant
and the trigger.

The **downgrade is destructive in the real sense**: it is mechanically reversible,
and it drops the audit trail — every recorded action, on both planes. Run it against
a database that matters only if that is genuinely the intent.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.core.rls import PROVIDER_PLANE_ON, PROVIDER_PLANE_SETTING
from verity.db.rls import drop_append_only, grant_crud, make_append_only, tenant_policy_predicate

revision: str = "ddd9734e6c34"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_log"

_TENANT_PREDICATE = tenant_policy_predicate()
_PROVIDER_PREDICATE = (
    f"NULLIF(current_setting('{PROVIDER_PLANE_SETTING}', true), '') = '{PROVIDER_PLANE_ON}'"
)

_POLICIES = (
    f"CREATE POLICY audit_log_tenant_select ON {TABLE} FOR SELECT USING ({_TENANT_PREDICATE})",
    f"CREATE POLICY audit_log_tenant_insert ON {TABLE} FOR INSERT WITH CHECK ({_TENANT_PREDICATE})",
    f"CREATE POLICY audit_log_provider_select ON {TABLE} FOR SELECT USING ({_PROVIDER_PREDICATE})",
    f"CREATE POLICY audit_log_provider_insert ON {TABLE} "
    f"FOR INSERT WITH CHECK ({_PROVIDER_PREDICATE})",
)


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # The stream the event belongs to, not the actor's tenant. NULL = provider
        # plane. Deliberately no FK: every FK action is a mutation the append-only
        # trigger refuses, and the record of a tenant teardown must outlive the
        # tenant (week1-review-decisions.md, decision 1).
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.Text(), nullable=False),
        # Polymorphic with actor_type — membership, platform admin, or nothing —
        # so no FK is possible.
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        # occurred_at alone — no created_at/updated_at. An updated_at on a table
        # that refuses UPDATE could only ever repeat this column
        # (docs/conventions/database.md, append-only exception).
        sa.Column(
            "occurred_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # op.f marks each name as final: the metadata naming convention for checks
        # contains %(constraint_name)s, and an unmarked explicit name would be
        # wrapped a second time — ck_audit_log__ck_audit_log__actor_type_valid.
        sa.CheckConstraint(
            "actor_type IN ('membership', 'platform_admin', 'system')",
            name=op.f("ck_audit_log__actor_type_valid"),
        ),
        sa.CheckConstraint(
            "action IN ('create', 'update', 'delete', 'transition', 'approve')",
            name=op.f("ck_audit_log__action_valid"),
        ),
        # A system row cannot name an actor and a person row cannot omit one —
        # without this the discriminator is decoration.
        sa.CheckConstraint(
            "(actor_type = 'system') = (actor_id IS NULL)",
            name=op.f("ck_audit_log__system_actor_has_no_actor_id"),
        ),
    )

    # tenant_id leads every composite index. NULLs are indexed, so provider-plane
    # rows ride the same indexes with no partial-index special case.
    op.create_index(
        "ix_audit_log__tenant_id_occurred_at",
        TABLE,
        ["tenant_id", sa.literal_column("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_log__tenant_id_object_type_object_id",
        TABLE,
        ["tenant_id", "object_type", "object_id"],
    )
    op.create_index("ix_audit_log__tenant_id_actor_id", TABLE, ["tenant_id", "actor_id"])

    op.execute(sa.text(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY"))
    for policy in _POLICIES:
        op.execute(sa.text(policy))

    # grant_crud then make_append_only nets to SELECT + INSERT for the application
    # role: the revoke inside make_append_only strips UPDATE, DELETE, and TRUNCATE
    # in the same transaction, and also attaches the BEFORE UPDATE OR DELETE
    # trigger that binds the owner role too.
    grant_crud(TABLE)
    make_append_only(TABLE)


def downgrade() -> None:
    # THIS DESTROYS THE AUDIT TRAIL. Dropping the table takes its policies and
    # indexes with it; the shared append-only guard function stays for the other
    # append-only tables.
    drop_append_only(TABLE)
    op.drop_table(TABLE)
