"""The lifecycle machine against a real Postgres, through the real service.

The unit tests in ``tests/unit/test_vendor_tiering.py`` pin the pure rules. These
pin the things only a database can prove: that tiering writes the stage rows in
the same transaction, that a gate is refused twice over, that a send-back really
resets the rows after it, and that both histories are written.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import Membership
from verity.modules.vendors.models import VendorStage, VendorTransition
from verity.modules.vendors.service import (
    TieringAnswers,
    VendorDetailView,
    VendorInput,
    vendor_service,
)
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Seeded:
    workspace: Workspace
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.workspace.tenant_id

    @property
    def actor(self) -> Membership:
        return Membership(self.workspace.membership_id)


@pytest.fixture
async def seeded() -> Seeded:
    workspace = await signup_workspace(company="Alpha Compliance", email="founder@alpha.example")
    async with session_scope(workspace.tenant_id) as session:
        vendor = await vendor_service.create_vendor(
            session,
            tenant_id=workspace.tenant_id,
            actor=Membership(workspace.membership_id),
            # Intake's exit checks want an owner and a classification, so the
            # fixture supplies both and the tests below start from a clean gate.
            data=VendorInput(
                name="Acme Cloud",
                data_classification="confidential",
                business_owner_membership_id=workspace.membership_id,
            ),
        )
    return Seeded(workspace=workspace, vendor_id=vendor.id, engagement_id=vendor.engagements[0].id)


async def _tier(  # noqa: PLR0913
    seeded: Seeded,
    *,
    data_sensitivity: int = 0,
    business_criticality: int = 0,
    system_access: int = 0,
    regulatory_scope: int = 0,
    fourth_party_reliance: int = 0,
) -> VendorDetailView:
    async with session_scope(seeded.tenant_id) as session:
        return await vendor_service.tier_engagement(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            engagement_id=seeded.engagement_id,
            answers=TieringAnswers(
                data_sensitivity=data_sensitivity,
                business_criticality=business_criticality,
                system_access=system_access,
                regulatory_scope=regulatory_scope,
                fourth_party_reliance=fourth_party_reliance,
            ),
        )


def _stage(detail: VendorDetailView, name: str) -> uuid.UUID:
    return next(s.id for s in detail.stages if s.stage == name)


async def test_a_vendor_has_no_stages_until_it_is_tiered(seeded: Seeded) -> None:
    """The cycle is laid out by tiering, not by creation — because what the cycle
    looks like is exactly what the tier decides."""
    async with session_scope(seeded.tenant_id) as session:
        detail = await vendor_service.get_vendor(
            session, tenant_id=seeded.tenant_id, vendor_id=seeded.vendor_id
        )
    assert detail.stages == []
    assert detail.tierings == []


async def test_tiering_writes_the_score_the_tier_and_the_twelve_rows(seeded: Seeded) -> None:
    detail = await _tier(seeded, data_sensitivity=4, business_criticality=4, system_access=4)

    assert len(detail.stages) == 12
    assert detail.engagements[0].tier == "critical"
    assert detail.tier == "critical", "the vendor caches its worst engagement"

    tiering = detail.tierings[0]
    assert tiering.score == 75.0
    assert tiering.computed_tier == "critical"
    assert [f.key for f in tiering.factors] == [
        "data_sensitivity",
        "business_criticality",
        "system_access",
        "regulatory_scope",
        "fourth_party_reliance",
    ]
    assert sum(f.points for f in tiering.factors) == pytest.approx(75.0, abs=0.02)
    # A critical vendor skips nothing.
    assert [s.stage for s in detail.stages if s.status == "skipped"] == []


async def test_a_low_tier_vendor_visibly_collapses_to_seven_active_stages(
    seeded: Seeded,
) -> None:
    """Spec ¶82's scenario, end to end: the tier changes the work in the same
    transaction that computes it."""
    detail = await _tier(seeded, fourth_party_reliance=2)

    assert detail.engagements[0].tier == "low"
    skipped = {s.stage for s in detail.stages if s.status == "skipped"}
    assert skipped == {"diligence", "questionnaire", "scoring", "findings"}

    active = [s for s in detail.stages if s.status != "skipped" and s.stage != "offboarding"]
    assert len(active) == 7

    # Every skipped row carries the policy that skipped it, and the gate does not.
    for stage in detail.stages:
        if stage.stage in skipped:
            assert stage.skipped_by_policy == "low tier"
        if stage.is_gate:
            assert stage.status != "skipped"


async def test_the_database_refuses_a_skipped_gate_even_bypassing_the_service(
    seeded: Seeded,
) -> None:
    """Spec ¶82 as a CHECK. A control enforced only in application code is one bug
    away from not existing, so the constraint is asserted directly."""
    detail = await _tier(seeded, data_sensitivity=4)
    async with session_scope(seeded.tenant_id) as session:
        stage = await session.get(VendorStage, _stage(detail, "approval"))
        assert stage is not None
        stage.status = "skipped"
        with pytest.raises(DBAPIError, match="gate_never_skipped"):
            await session.flush()


async def test_advancing_walks_over_the_skipped_rows(seeded: Seeded) -> None:
    detail = await _tier(seeded, fourth_party_reliance=2)
    intake = _stage(detail, "intake")

    async with session_scope(seeded.tenant_id) as session:
        after_intake = await vendor_service.advance_stage(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=intake,
        )
    tiering_stage = next(s for s in after_intake.stages if s.stage == "tiering")
    assert tiering_stage.status == "in_progress"

    async with session_scope(seeded.tenant_id) as session:
        after_tiering = await vendor_service.advance_stage(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=tiering_stage.id,
        )
    by_stage = {s.stage: s for s in after_tiering.stages}
    assert by_stage["tiering"].status == "complete"
    # diligence, questionnaire, scoring and findings are skipped at low tier, so
    # the next actionable stage is contracting.
    assert by_stage["contracting"].status == "in_progress"
    assert by_stage["diligence"].status == "skipped"


async def test_a_blocked_stage_refuses_to_advance_and_names_the_blockers(
    seeded: Seeded,
) -> None:
    async with session_scope(seeded.tenant_id) as session:
        await vendor_service.update_vendor(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            data=VendorInput(name="Acme Cloud"),  # drops the owner and classification
        )
    detail = await _tier(seeded, data_sensitivity=4)
    intake = next(s for s in detail.stages if s.stage == "intake")
    assert {c.code for c in intake.blockers} == {"intake.owned", "intake.classified"}
    assert "advance" not in intake.allowed_transitions

    async with session_scope(seeded.tenant_id) as session:
        with pytest.raises(Conflict):
            await vendor_service.advance_stage(
                session,
                tenant_id=seeded.tenant_id,
                actor=seeded.actor,
                vendor_id=seeded.vendor_id,
                stage_id=intake.id,
            )


async def test_a_send_back_resets_every_stage_at_or_after_the_target(
    seeded: Seeded,
) -> None:
    detail = await _tier(seeded, fourth_party_reliance=2)
    async with session_scope(seeded.tenant_id) as session:
        detail = await vendor_service.advance_stage(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=_stage(detail, "intake"),
        )
    async with session_scope(seeded.tenant_id) as session:
        detail = await vendor_service.advance_stage(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=_stage(detail, "tiering"),
        )
    assert {s.stage: s.status for s in detail.stages}["contracting"] == "in_progress"

    async with session_scope(seeded.tenant_id) as session:
        detail = await vendor_service.send_back(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=_stage(detail, "contracting"),
            to_stage="tiering",
            reason="The data classification was wrong.",
        )

    by_stage = {s.stage: s for s in detail.stages}
    assert by_stage["intake"].status == "complete", "stages before the target are untouched"
    assert by_stage["tiering"].status == "in_progress"
    assert by_stage["tiering"].exited_at is None
    assert by_stage["contracting"].status == "not_started"
    assert by_stage["approval"].status == "not_started"
    # Skipped rows stay skipped: a send-back re-opens work, it does not re-plan
    # what the tier decided was disproportionate.
    assert by_stage["diligence"].status == "skipped"


async def test_a_send_back_only_goes_backwards(seeded: Seeded) -> None:
    detail = await _tier(seeded, data_sensitivity=4)
    async with session_scope(seeded.tenant_id) as session:
        with pytest.raises(Conflict):
            await vendor_service.send_back(
                session,
                tenant_id=seeded.tenant_id,
                actor=seeded.actor,
                vendor_id=seeded.vendor_id,
                stage_id=_stage(detail, "intake"),
                to_stage="approval",
                reason="Trying to jump the queue.",
            )


async def test_a_send_back_without_a_reason_is_refused(seeded: Seeded) -> None:
    detail = await _tier(seeded, data_sensitivity=4)
    async with session_scope(seeded.tenant_id) as session:
        with pytest.raises(InvalidInput):
            await vendor_service.send_back(
                session,
                tenant_id=seeded.tenant_id,
                actor=seeded.actor,
                vendor_id=seeded.vendor_id,
                stage_id=_stage(detail, "tiering"),
                to_stage="intake",
                reason="   ",
            )


async def test_the_service_refuses_to_skip_a_gate_or_a_required_stage(
    seeded: Seeded,
) -> None:
    detail = await _tier(seeded, fourth_party_reliance=2)
    for stage_name in ("approval", "tiering", "intake"):
        async with session_scope(seeded.tenant_id) as session:
            with pytest.raises(Conflict):
                await vendor_service.skip_stage(
                    session,
                    tenant_id=seeded.tenant_id,
                    actor=seeded.actor,
                    vendor_id=seeded.vendor_id,
                    stage_id=_stage(detail, stage_name),
                    reason="Not needed for this one.",
                )


async def test_a_stage_this_tier_does_not_skip_is_refused(seeded: Seeded) -> None:
    """A critical vendor skips nothing, so skipping diligence is a Conflict rather
    than a silent shortcut."""
    detail = await _tier(seeded, data_sensitivity=4, business_criticality=4, system_access=4)
    async with session_scope(seeded.tenant_id) as session:
        with pytest.raises(Conflict):
            await vendor_service.skip_stage(
                session,
                tenant_id=seeded.tenant_id,
                actor=seeded.actor,
                vendor_id=seeded.vendor_id,
                stage_id=_stage(detail, "diligence"),
                reason="We trust them.",
            )


async def test_every_move_writes_both_histories(seeded: Seeded) -> None:
    """Two records per state change (rule 5): the columnar row an operator reads
    down, and the audit row an auditor reads across."""
    detail = await _tier(seeded, fourth_party_reliance=2)
    async with session_scope(seeded.tenant_id) as session:
        await vendor_service.advance_stage(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=_stage(detail, "intake"),
        )

    async with session_scope(seeded.tenant_id) as session:
        transitions = list((await session.execute(select(VendorTransition))).scalars())
        audited = (
            await session.execute(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.object_type == "vendor_stage")
            )
        ).scalar_one()

    assert len(transitions) == 1
    assert transitions[0].action == "advance"
    assert transitions[0].from_stage == "intake"
    assert transitions[0].to_stage == "tiering"
    assert transitions[0].actor_membership_id == seeded.workspace.membership_id
    assert audited == 1


async def test_the_transition_history_refuses_to_be_rewritten(seeded: Seeded) -> None:
    """Append-only, enforced by the trigger and not by convention."""
    detail = await _tier(seeded, fourth_party_reliance=2)
    async with session_scope(seeded.tenant_id) as session:
        await vendor_service.advance_stage(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            stage_id=_stage(detail, "intake"),
        )
    async with session_scope(seeded.tenant_id) as session:
        row = (await session.execute(select(VendorTransition))).scalars().one()
        row.reason = "rewritten"
        with pytest.raises(DBAPIError):
            await session.flush()


async def test_an_override_without_a_justification_is_refused(seeded: Seeded) -> None:
    async with session_scope(seeded.tenant_id) as session:
        with pytest.raises(InvalidInput):
            await vendor_service.tier_engagement(
                session,
                tenant_id=seeded.tenant_id,
                actor=seeded.actor,
                vendor_id=seeded.vendor_id,
                engagement_id=seeded.engagement_id,
                answers=TieringAnswers(override_tier="critical"),
            )


async def test_an_override_beats_the_arithmetic_and_keeps_both_on_the_record(
    seeded: Seeded,
) -> None:
    detail = await _tier(
        seeded,
        fourth_party_reliance=2,
    )
    assert detail.engagements[0].tier == "low"

    async with session_scope(seeded.tenant_id) as session:
        detail = await vendor_service.tier_engagement(
            session,
            tenant_id=seeded.tenant_id,
            actor=seeded.actor,
            vendor_id=seeded.vendor_id,
            engagement_id=seeded.engagement_id,
            answers=TieringAnswers(
                fourth_party_reliance=2,
                override_tier="critical",
                override_justification="They hold the production database.",
            ),
        )

    latest = detail.tierings[0]
    assert latest.computed_tier == "low"
    assert latest.override_tier == "critical"
    assert latest.effective_tier == "critical"
    assert detail.engagements[0].tier == "critical"
    # Re-tiering replans what is still ahead: the low tier's skips are lifted.
    assert [s.stage for s in detail.stages if s.status == "skipped"] == []


async def test_the_next_review_is_scheduled_from_the_cadence(seeded: Seeded) -> None:
    """Anchored to the schedule, not to the completion date, so a late review does
    not push the next one late (ER ¶101)."""
    first = await _tier(seeded, data_sensitivity=4, business_criticality=4, system_access=4)
    assert first.next_reassessment_on is not None
    booked = first.next_reassessment_on

    second = await _tier(seeded, data_sensitivity=4, business_criticality=4, system_access=4)
    assert second.next_reassessment_on == booked + timedelta(days=180)


async def test_a_stage_belonging_to_another_vendor_is_not_found(seeded: Seeded) -> None:
    """The path names a vendor; disagreeing with the record is a stale link."""
    detail = await _tier(seeded, data_sensitivity=4)
    async with session_scope(seeded.tenant_id) as session:
        with pytest.raises(NotFound):
            await vendor_service.advance_stage(
                session,
                tenant_id=seeded.tenant_id,
                actor=seeded.actor,
                vendor_id=uuid7(),
                stage_id=_stage(detail, "intake"),
            )


async def test_a_check_whose_module_is_not_built_yet_reports_pending(
    seeded: Seeded,
) -> None:
    """Three-valued checks, proven against what is and is not built.

    Section 3 built the questionnaire and the findings, so those checks answer now
    — and nothing in ``lifecycle.py`` changed to make that happen, only the
    collector. Contracting and approval are section 4, so theirs still report
    pending: not blocking, and not a tick either.
    """
    detail = await _tier(seeded, data_sensitivity=4, business_criticality=4, system_access=4)
    by_stage = {s.stage: s for s in detail.stages}

    # Answerable now that section 3 exists: no questionnaire has been issued, so
    # the check fails rather than abstaining.
    questionnaire = by_stage["questionnaire"]
    assert not questionnaire.pending, "the questionnaire module is built; nothing should abstain"

    # Still unbuilt. A critical vendor needs a contract, and no contract table
    # exists yet, so the check abstains rather than blocking the lifecycle.
    contracting = by_stage["contracting"]
    assert [c.code for c in contracting.pending] == ["contracting.contract_linked"]
    assert not contracting.blockers
    assert all(c.satisfied is None for c in contracting.pending)

    approval = by_stage["approval"]
    assert "approval.decided" in {c.code for c in approval.pending}
