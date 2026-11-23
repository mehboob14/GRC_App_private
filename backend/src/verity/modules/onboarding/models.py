"""The one thing Get Started stores: a person's decision to skip a step, with a reason.

Status itself is never stored. It is computed from the records each step counts, so it
cannot drift from them (requirement GS-4). A skip is a decision, so it is kept: reopening
a skipped step stamps the row, it never deletes it (rule 4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Final

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.naming import conv

from verity.db.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey, tenant_index


class OnboardingStepSkip(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A Get Started step a member chose to skip, and whether it was reopened."""

    __tablename__ = "onboarding_step_skips"

    step_key: Mapped[str]
    """The step's key, with the framework code for a per framework step (``scope:ISO27001``)."""
    reason: Mapped[str]
    skipped_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    reopened_at: Mapped[datetime | None] = mapped_column(default=None)
    reopened_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        CheckConstraint(
            "length(btrim(reason)) > 0", name=conv("ck_onboarding_step_skips__reason_present")
        ),
        # One open skip per step; reopened rows stay as history.
        Index(
            "uq_onboarding_step_skips__tenant_id_step_key_open",
            "tenant_id",
            "step_key",
            unique=True,
            postgresql_where=text("reopened_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"OnboardingStepSkip(tenant_id={self.tenant_id!r}, step_key={self.step_key!r})"


class OwnerFunction(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Which member holds one of the eight owner functions (guided onboarding OW-1). One member
    may hold several. Reassigned in place and audited; there is nothing to delete."""

    __tablename__ = "owner_functions"

    function_key: Mapped[str]
    membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        CheckConstraint(
            "function_key IN ('executive_sponsor', 'security_lead', 'engineering_lead', "
            "'it_lead', 'hr_lead', 'legal_privacy_lead', 'vendor_lead', 'finance_lead')",
            name=conv("ck_owner_functions__function_key_valid"),
        ),
        tenant_index("owner_functions", "function_key", unique=True),
    )


class ProposalDecision(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A person's answer to one suggestion (guided onboarding PL-1 to PL-5).

    Suggestions themselves are computed on every read from the profile and the workspace's
    state, so they cannot drift. Only the decision is stored, keyed on the suggestion's
    ``dedupe_key`` (rule and subject). A changed mind updates the row; the audit log keeps the
    history. An accepted decision whose rule no longer fires reads "review needed".
    """

    __tablename__ = "onboarding_proposal_decisions"

    dedupe_key: Mapped[str]
    rule_key: Mapped[str]
    kind: Mapped[str]
    subject_key: Mapped[str]
    decision: Mapped[str]
    reason: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB(), default=dict, server_default=text("'{}'::jsonb")
    )
    because: Mapped[str]
    """The answer behind the suggestion when it was decided."""
    profile_version: Mapped[int | None] = mapped_column(default=None)
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('accepted', 'rejected')",
            name=conv("ck_onboarding_proposal_decisions__decision_valid"),
        ),
        CheckConstraint(
            "kind IN ('control_status', 'iso_applicability', 'soc2_category')",
            name=conv("ck_onboarding_proposal_decisions__kind_valid"),
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name=conv("ck_onboarding_proposal_decisions__reason_present"),
        ),
        tenant_index("onboarding_proposal_decisions", "dedupe_key", unique=True),
    )


BASELINE_ANSWERS: Final[tuple[str, ...]] = ("in_place", "partly", "not_in_place", "not_sure")


class Baseline(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One pass over the controls asking what is already in place (PL-6). Answers are the
    person's own view, kept apart from the control's status, which only evidence moves."""

    __tablename__ = "baselines"

    taken_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )
    status: Mapped[str] = mapped_column(default="open", server_default=text("'open'"))
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        CheckConstraint("status IN ('open', 'complete')", name=conv("ck_baselines__status_valid")),
        # One open baseline at a time; completed ones stay as history.
        Index(
            "uq_baselines__tenant_id_open",
            "tenant_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )


class BaselineAnswer(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    __tablename__ = "baseline_answers"

    baseline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("baselines.id", ondelete="CASCADE"))
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))
    answer: Mapped[str]
    note: Mapped[str | None] = mapped_column(default=None)
    answered_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        CheckConstraint(
            "answer IN ('in_place', 'partly', 'not_in_place', 'not_sure')",
            name=conv("ck_baseline_answers__answer_valid"),
        ),
        tenant_index("baseline_answers", "baseline_id", "control_id", unique=True),
    )


class ReadinessSnapshot(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Figures frozen at a moment (the baseline, a milestone), so progress can be shown
    against where the workspace started (PL-9). Append only."""

    __tablename__ = "readiness_snapshots"

    label: Mapped[str]
    figures: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB())

    __table_args__ = (tenant_index("readiness_snapshots", "created_at"),)


class OnboardingState(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Where the setup flow stands for a workspace (part 3 section 3). One row per workspace."""

    __tablename__ = "onboarding_state"

    start_point: Mapped[str | None] = mapped_column(default=None)
    setup_step: Mapped[str | None] = mapped_column(default=None)
    setup_completed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        CheckConstraint(
            "start_point IS NULL OR start_point IN ('fresh', 'existing')",
            name=conv("ck_onboarding_state__start_point_valid"),
        ),
        Index("uq_onboarding_state__tenant_id", "tenant_id", unique=True),
    )
