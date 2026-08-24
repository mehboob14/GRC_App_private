"""Control sub-category column + widened control_type vocabulary.

Adds ``controls.sub_category`` (a finer, app-defined grouping under ``category``;
deliberately not CHECK-constrained because the taxonomy varies per register
type) and widens the ``control_type`` CHECK on both ``controls`` and
``control_templates`` from three values to six (adds Deterrent, Compensating,
Directive). Widening a CHECK is safe against existing rows, which only ever hold
the original three.

Raw SQL is used for the CHECK swap so the constraint keeps its exact
convention name — ``op.drop_constraint`` / ``create_check_constraint`` re-apply
the naming convention and would double-prefix it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d8f2b4c091a7"
down_revision = "c5d9e1a72f80"
branch_labels = None
depends_on = None

_OLD = "'Preventive', 'Detective', 'Corrective'"
_NEW = "'Preventive', 'Detective', 'Corrective', 'Deterrent', 'Compensating', 'Directive'"


def _swap_type_check(values: str) -> None:
    for table in ("controls", "control_templates"):
        name = f"ck_{table}__control_type_valid"
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK (control_type IN ({values}))")


def upgrade() -> None:
    op.add_column("controls", sa.Column("sub_category", sa.String(), nullable=True))
    _swap_type_check(_NEW)


def downgrade() -> None:
    # Reverting the CHECK will fail if any row now holds one of the new types;
    # that is the correct signal (the data no longer fits the old vocabulary).
    _swap_type_check(_OLD)
    op.drop_column("controls", "sub_category")
