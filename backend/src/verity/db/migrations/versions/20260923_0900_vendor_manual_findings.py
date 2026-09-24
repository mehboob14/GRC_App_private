"""Vendor findings raised by hand.

A reviewer hears something on a call, or spots a gap no question asked about. Every
other source on ``vendor_findings.finding_source`` is written by the platform, so
until now a person could not raise one at all, and the workaround was to write it
into a questionnaire answer that nobody asked.

``manual`` stays a distinct value rather than reusing ``assessment``: "the review
found this" and "a person decided this" are different claims, and an auditor
reading the register has to be able to tell them apart.

Revision ID: 8a1f4c26d05b
Revises: 63ac7a1e3c8f
Create Date: 2026-09-23
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.sql.elements import conv

revision: str = "8a1f4c26d05b"
down_revision: str | None = "63ac7a1e3c8f"
branch_labels: str | None = None
depends_on: str | None = None

_WITHOUT_MANUAL = ("assessment", "sla_breach", "signal", "document_review", "offboarding")
_WITH_MANUAL = (*_WITHOUT_MANUAL, "manual")

_CONSTRAINT = conv("ck_vendor_findings__finding_source_valid")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _set_sources(values: tuple[str, ...]) -> None:
    op.drop_constraint(_CONSTRAINT, "vendor_findings", type_="check")
    op.create_check_constraint(_CONSTRAINT, "vendor_findings", _in("finding_source", values))


def upgrade() -> None:
    _set_sources(_WITH_MANUAL)


def downgrade() -> None:
    # Rows the new value allowed would fail the narrower check, so they move to the
    # closest truthful source rather than blocking the downgrade or being deleted.
    op.execute(
        "UPDATE vendor_findings SET finding_source = 'assessment' WHERE finding_source = 'manual'"
    )
    _set_sources(_WITHOUT_MANUAL)
