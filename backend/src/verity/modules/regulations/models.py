"""The workspace's own call on each regulation the panel shows (guided onboarding JC-6, J5).

The pack itself is sealed content held in memory; only this decision is stored. A changed mind
updates the row and the audit log keeps the history.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.naming import conv

from verity.db.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey, tenant_index


class RegulationDecision(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    __tablename__ = "regulation_decisions"

    regulation_key: Mapped[str]
    relevance: Mapped[str]
    note: Mapped[str | None] = mapped_column(default=None)
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    register_row_added_at: Mapped[datetime | None] = mapped_column(default=None)
    profile_version: Mapped[int | None] = mapped_column(default=None)

    __table_args__ = (
        CheckConstraint(
            "relevance IN ('relevant', 'not_relevant')",
            name=conv("ck_regulation_decisions__relevance_valid"),
        ),
        tenant_index("regulation_decisions", "regulation_key", unique=True),
    )
