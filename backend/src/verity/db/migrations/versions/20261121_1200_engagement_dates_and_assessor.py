"""Engagements: the dates and the outside party an audit needs, for every framework.

Phase 3 of the guided onboarding change (openspec/changes/guided-onboarding, tasks 3.1 and
3.5; requirements EN-2, EN-3). Additive columns on ``engagements``:

* ``as_of_date``: the SOC 2 Type 1 as of date (a Type 1 has no window). CHECK: only a Type 1
  carries it.
* ``target_date`` and ``driver``: by when the report or certificate is needed, and who asked.
* ``live_date``: the day the management system went live (ISO 27001 and frameworks built like
  it); records are counted from it.
* ``assessor_state`` (``unknown``, ``undecided``, ``chosen``), ``assessor_accreditation_body``,
  ``assessor_contact`` and ``assessor_engaged_on``. The outside party's name stays in
  ``certification_body`` and now serves SOC 2 too (the CPA firm). The product never suggests
  a firm.

Existing rows get ``unknown``. No data is rewritten here: under forced RLS an UPDATE from a
migration matches no rows. The service reads ``unknown`` with a named body as ``chosen``.

Revision ID: 6b8df681a7aa
Revises: 3b03e4d1a72c
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "6b8df681a7aa"
down_revision: str | None = "3b03e4d1a72c"
branch_labels: str | None = None
depends_on: str | None = None

_T = "engagements"
_COLUMNS = (
    ("as_of_date", sa.Date()),
    ("target_date", sa.Date()),
    ("driver", sa.Text()),
    ("live_date", sa.Date()),
    ("assessor_accreditation_body", sa.Text()),
    ("assessor_contact", sa.Text()),
    ("assessor_engaged_on", sa.Date()),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column(_T, sa.Column(name, type_, nullable=True))
    op.add_column(
        _T,
        sa.Column("assessor_state", sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
    )
    op.create_check_constraint(
        op.f(f"ck_{_T}__assessor_state_valid"),
        _T,
        "assessor_state IN ('unknown', 'undecided', 'chosen')",
    )
    op.create_check_constraint(
        op.f(f"ck_{_T}__as_of_only_type_1"), _T, "audit_type = 'type_1' OR as_of_date IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint(op.f(f"ck_{_T}__as_of_only_type_1"), _T, type_="check")
    op.drop_constraint(op.f(f"ck_{_T}__assessor_state_valid"), _T, type_="check")
    op.drop_column(_T, "assessor_state")
    for name, _ in reversed(_COLUMNS):
        op.drop_column(_T, name)
