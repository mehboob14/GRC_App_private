"""What the workspace records about objectives: a decision that one does not apply, with its
reason, and which evidence a person filed for which artifact (guided onboarding AO-1 to AO-4).

Outcomes are never stored; they are derived per request. Both tables keep history: a withdrawn
decision or a removed tag is stamped, never deleted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.naming import conv

from verity.db.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class ObjectiveDecision(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """An objective the workspace decided does not apply, and why."""

    __tablename__ = "objective_decisions"

    objective_code: Mapped[str]
    reason: Mapped[str]
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(default=None)
    withdrawn_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        CheckConstraint(
            "length(btrim(reason)) > 0", name=conv("ck_objective_decisions__reason_present")
        ),
        Index(
            "uq_objective_decisions__tenant_id_objective_code_open",
            "tenant_id",
            "objective_code",
            unique=True,
            postgresql_where=text("withdrawn_at IS NULL"),
        ),
    )


class EvidenceArtifact(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A person's statement that an evidence row is a given artifact (the evidence slot)."""

    __tablename__ = "evidence_artifacts"

    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"))
    artifact_key: Mapped[str]
    tagged_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    removed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_evidence_artifacts__tenant_id_evidence_id_artifact_key_open",
            "tenant_id",
            "evidence_id",
            "artifact_key",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index("ix_evidence_artifacts__tenant_id_artifact_key", "tenant_id", "artifact_key"),
    )
