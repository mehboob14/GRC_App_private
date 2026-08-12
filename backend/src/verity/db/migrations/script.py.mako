"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Before requesting review, check each of these (docs/conventions/workflow.md):

- A new tenant-owned table calls ``enable_rls(...)`` and ``grant_crud(...)`` from
  ``verity.db.rls`` **in this migration**. A table without a policy is a silent
  isolation hole and passes every other test.
- ``tenant_id`` leads every composite index. Use ``verity.db.base.tenant_index``.
- A new append-only table calls ``make_append_only(...)``.
- A status column is text with a ``CHECK``, never a Postgres enum. Use
  ``verity.db.base.status_check``.
- A table that could ever receive a row from an outside system carries ``source``,
  ``external_id``, ``synced_at`` and the ``integration_unique`` constraint.
- ``downgrade`` reverses this, or the docstring says why it cannot.
- A backfill over a large table is its own migration, batched, separate from the DDL.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
