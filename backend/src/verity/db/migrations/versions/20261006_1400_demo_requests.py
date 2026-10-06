"""demo requests: the website's public form lands in a provider-plane table

Revision ID: 61e2554a5209
Revises: b4e1f9a2c7d3

``demo_requests`` holds what a visitor typed into the marketing site's "ask for a demo"
form, and what was done about it: the owner's notification (``notified_at``) and the
visitor's receipt (``confirmation_sent_at``).

**It has no ``tenant_id``, and that is deliberate.** A prospect asks the platform's
owner for a conversation before any tenant exists, so the row belongs to no tenant and
could not be scoped to one. The provider plane sits above the tenant boundary (rule 2),
and that is where it lives, beside ``tenants`` and ``platform_admins``. What polices it
instead is that plane's own wall, not the tenant one:

    application role   SELECT, INSERT, UPDATE. No DELETE and no TRUNCATE: the default
                       privileges grant DELETE on every new table, so it is revoked here.
    row-level security ENABLE and FORCE, with one policy per allowed command keyed on
                       ``app.provider_plane``, the setting only
                       ``core.db.provider_session_scope`` binds. A tenant-bound or
                       unbound session sees no row and cannot add or change one. There
                       is deliberately no DELETE policy, so even a future grant could not
                       remove a row through the application.

``audit_log`` is where a request is audited, in the provider stream (``tenant_id`` NULL),
and carries only the request's id and three non-personal labels, never the personal data
held here.

An index on ``(email, created_at)`` serves the "has this address been sent a receipt
today" check.

The **downgrade is destructive**: it drops the table and every request stored in it,
which are the leads the platform has not yet answered. The audit rows survive, by design.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from verity.core.rls import PROVIDER_PLANE_ON, PROVIDER_PLANE_SETTING
from verity.db.rls import grant_crud, revoke_delete

revision: str = "61e2554a5209"
down_revision: str | None = "b4e1f9a2c7d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "demo_requests"

_PROVIDER = f"NULLIF(current_setting('{PROVIDER_PLANE_SETTING}', true), '') = '{PROVIDER_PLANE_ON}'"

_POLICIES = (
    f"CREATE POLICY {TABLE}_provider_select ON {TABLE} FOR SELECT USING ({_PROVIDER})",
    f"CREATE POLICY {TABLE}_provider_insert ON {TABLE} FOR INSERT WITH CHECK ({_PROVIDER})",
    f"CREATE POLICY {TABLE}_provider_update ON {TABLE} "
    f"FOR UPDATE USING ({_PROVIDER}) WITH CHECK ({_PROVIDER})",
)


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        # Lower-cased and stripped by the service, so equality is the comparison.
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("interest", sa.Text(), nullable=True),
        # Which website button was clicked: a label, not an integration origin.
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("page", sa.Text(), nullable=True),
        sa.Column("notified_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("confirmation_sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_demo_requests__email_created_at", TABLE, ["email", "created_at"])

    op.execute(sa.text(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY"))
    for policy in _POLICIES:
        op.execute(sa.text(policy))

    # grant_crud then revoke_delete nets SELECT, INSERT and UPDATE for the application
    # role, the same way audit_log nets SELECT and INSERT.
    grant_crud(TABLE)
    revoke_delete(TABLE)


def downgrade() -> None:
    # THIS DROPS EVERY STORED DEMO REQUEST. Dropping the table takes its policies,
    # index and privileges with it; the audit rows about the requests stay.
    op.drop_table(TABLE)
