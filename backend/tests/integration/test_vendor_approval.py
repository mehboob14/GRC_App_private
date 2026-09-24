"""The approval gate, the paperwork and the exit, against a real Postgres.

The gate is the one rule in this module whose violation is a control failure
rather than a bug, so most of what is below is written as an attempt to get past
it: decide your own vendor, decide a stage you submitted, reuse a decision after a
send-back, complete an exit with access still live.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Final

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from tests.support.iam import Workspace, invite_directly, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import Conflict, InvalidInput
from verity.modules.audit.service import Membership
from verity.modules.tasks.service import task_service
from verity.modules.vendors import lifecycle
from verity.modules.vendors.models import (
    Vendor,
    VendorApproval,
    VendorFinding,
    VendorOffboarding,
    VendorStage,
)
from verity.modules.vendors.service import (
    ConditionInput,
    ContractInput,
    DocumentInput,
    EngagementInput,
    IntakeInput,
    OffboardingCompletion,
    SocReviewInput,
    SubprocessorInput,
    TieringAnswers,
    VendorDetailView,
    VendorInput,
    vendor_service,
)
from verity.shared.ids import uuid7

pytestmark = [pytest.mark.integration]


_LOW_TIER_CADENCE_DAYS: Final = 1095
"""``lifecycle.DEFAULT_CADENCE_DAYS["low"]``. Asserted as a literal rather than
imported, so retuning the default is a decision somebody makes here too."""


def _today() -> date:
    """Timezone-explicit "today". ``date.today()`` reads the machine's local zone,
    and every date this product stores is UTC."""
    return datetime.now(UTC).date()


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Ready:
    workspace: Workspace
    other_membership_id: uuid.UUID
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.workspace.tenant_id

    @property
    def owner(self) -> Membership:
        """The admin, who is also the vendor's business owner — and therefore
        barred from approving it."""
        return Membership(self.workspace.membership_id)

    @property
    def other(self) -> Membership:
        """A second member, who may decide."""
        return Membership(self.other_membership_id)


async def _advance_to_gate(ready: Ready, mover: Membership) -> None:
    """Walk the engagement up to the approval gate.

    Low tier, so the heavy stages are skipped by policy and the path is
    intake -> tiering -> contracting -> approval. ``mover`` becomes the stage
    submitter, and is therefore barred from deciding what they submitted (V4).
    """
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.get_vendor(
            session, tenant_id=ready.tenant_id, vendor_id=ready.vendor_id
        )
        for _ in range(len(lifecycle.STAGES)):
            current = next(
                (s for s in detail.stages if s.status == "in_progress"),
                None,
            ) or next((s for s in detail.stages if s.status == "not_started"), None)
            if current is None or current.stage == "approval" or current.blockers:
                break
            detail = await vendor_service.advance_stage(
                session,
                tenant_id=ready.tenant_id,
                actor=mover,
                vendor_id=ready.vendor_id,
                stage_id=current.id,
            )


async def _make(company: str, email: str, *, answers: TieringAnswers) -> Ready:
    workspace = await signup_workspace(company=company, email=f"founder@{email}")
    invited = await invite_directly(
        workspace,
        email=f"reviewer@{email}",
        full_name="Robin Shaw",
        # An approver has to hold vendors:approve, and of the built-in roles only
        # Admin does. The picker bars everyone else, which is tested below.
        role_name="Admin",
    )
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        vendor = await vendor_service.create_vendor(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            data=VendorInput(
                name="Acme Cloud",
                data_classification="confidential",
                business_owner_membership_id=workspace.membership_id,
            ),
        )
        await vendor_service.tier_engagement(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            engagement_id=vendor.engagements[0].id,
            answers=answers,
        )
    return Ready(
        workspace=workspace,
        other_membership_id=invited.member.membership_id,
        vendor_id=vendor.id,
        engagement_id=vendor.engagements[0].id,
    )


@pytest.fixture
async def ready() -> Ready:
    """A low-tier engagement standing at the approval gate.

    Low tier because the point of these tests is the gate, and a low-tier vendor
    reaches it through four stages rather than twelve — the proportionality
    tiering exists to produce, used here to keep the setup honest rather than
    mocked. The business owner walks it up, so they are both the owner *and* the
    submitter, and doubly barred from deciding.
    """
    ready = await _make(
        "Alpha Compliance", "alpha.example", answers=TieringAnswers(fourth_party_reliance=2)
    )
    await _advance_to_gate(ready, ready.owner)
    return ready


@pytest.fixture
async def critical() -> Ready:
    """A critical-tier engagement, for the checks that only apply to one."""
    return await _make(
        "Bravo Assurance",
        "bravo.example",
        answers=TieringAnswers(data_sensitivity=4, business_criticality=4, system_access=4),
    )


# -- segregation of duties (V4) -----------------------------------------------


async def test_the_business_owner_cannot_approve_their_own_vendor(ready: Ready) -> None:
    """V4 takes the ER's prose over its diagram: two exclusions, not one.

    It has a consequence worth stating — a one-admin workspace cannot approve its
    own vendors. That is correct, and it is the same rule the vulnerability
    exception flow already enforces.
    """
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(Conflict, match="business owner"):
            await vendor_service.decide(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                engagement_id=ready.engagement_id,
                decision="approve",
                rationale="Looks fine to me.",
            )


async def test_somebody_else_can(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve",
            rationale="SOC 2 Type II reviewed, no material findings.",
        )
    assert len(detail.approvals) == 1
    assert detail.approvals[0].decision == "approve"
    assert detail.approvals[0].decided_by_name is not None


async def test_the_picker_says_who_is_barred_and_why_before_anyone_submits(
    ready: Ready,
) -> None:
    """Enforcing the rule only on submit means the user has written a rationale
    before learning it. The reason travels with the name instead."""
    async with session_scope(ready.tenant_id) as session:
        approvers = await vendor_service.approvers(
            session, tenant_id=ready.tenant_id, engagement_id=ready.engagement_id
        )
    barred = {a.membership_id: a.disqualified_reason for a in approvers if a.disqualified_reason}
    assert ready.workspace.membership_id in barred
    assert "business owner" in barred[ready.workspace.membership_id]
    assert ready.other_membership_id not in barred


async def test_whoever_submitted_the_stage_cannot_also_decide_it(ready: Ready) -> None:
    """The second exclusion (V4).

    The fixture has the business owner walk the engagement up to the gate, so they
    are barred twice over — and the reason reported is the one the picker shows.
    Read from the append-only transition history, so it cannot be edited after the
    fact by anybody, including us.
    """
    async with session_scope(ready.tenant_id) as session:
        approvers = await vendor_service.approvers(
            session, tenant_id=ready.tenant_id, engagement_id=ready.engagement_id
        )
    owner = next(a for a in approvers if a.membership_id == ready.workspace.membership_id)
    assert owner.disqualified_reason is not None

    # Somebody who neither owns the vendor nor submitted the stage may decide.
    other = next(a for a in approvers if a.membership_id == ready.other_membership_id)
    assert other.disqualified_reason is None


async def test_the_decision_records_who_was_barred_at_the_time(ready: Ready) -> None:
    """The business owner can change afterwards, so "was segregation of duties
    applied here" has to be answerable from the row rather than recomputed."""
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve",
            rationale="Reviewed and accepted.",
        )
    assert str(ready.workspace.membership_id) in detail.approvals[0].excluded_membership_ids


# -- the four-valued decision (V3) --------------------------------------------


async def test_a_decision_needs_a_rationale(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="Say why"):
            await vendor_service.decide(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.other,
                vendor_id=ready.vendor_id,
                engagement_id=ready.engagement_id,
                decision="reject",
                rationale="   ",
            )


async def test_defer_is_not_reject(ready: Ready) -> None:
    """A product offering only the two extremes gets `reject` used to mean "not
    yet", which then reads as a refused vendor forever."""
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="defer",
            rationale="Waiting on their updated pen-test report.",
        )
    assert detail.approvals[0].decision == "defer"
    # Deferring settles nothing, so the engagement is not approved and not on hold.
    assert detail.engagements[0].status not in {"approved", "on_hold"}


async def test_approving_with_conditions_needs_conditions(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="at least one condition"):
            await vendor_service.decide(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.other,
                vendor_id=ready.vendor_id,
                engagement_id=ready.engagement_id,
                decision="approve_with_conditions",
                rationale="Fine subject to the MFA rollout.",
            )


async def test_every_condition_becomes_a_real_task(ready: Ready) -> None:
    """A condition with no task is a note in a record nobody opens again."""
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve_with_conditions",
            rationale="Approved subject to two things.",
            conditions=[
                ConditionInput(
                    description="Enforce MFA on all administrative access",
                    owner_membership_id=ready.workspace.membership_id,
                    due_date=_today() + timedelta(days=60),
                ),
                ConditionInput(description="Provide the current pen-test report"),
            ],
        )
    conditions = detail.approvals[0].conditions
    assert len(conditions) == 2
    assert all(c.status == "open" for c in conditions)
    task_ids = [c.task_id for c in conditions]
    assert all(t is not None for t in task_ids)

    async with session_scope(ready.tenant_id) as session:
        first = task_ids[0]
        assert first is not None
        task = await task_service.get_task(session, tenant_id=ready.tenant_id, task_id=first)
    assert "Acme Cloud" in task.title


async def test_a_waived_condition_states_why(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve_with_conditions",
            rationale="Approved subject to one thing.",
            conditions=[ConditionInput(description="Provide the DPA")],
        )
        condition_id = detail.approvals[0].conditions[0].id

    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="why the condition"):
            await vendor_service.close_condition(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.other,
                vendor_id=ready.vendor_id,
                condition_id=condition_id,
                status="waived",
            )

    async with session_scope(ready.tenant_id) as session:
        waived = await vendor_service.close_condition(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            condition_id=condition_id,
            status="waived",
            waived_reason="Superseded by the master agreement signed last week.",
        )
    assert waived.status == "waived"


async def test_an_approval_cannot_be_rewritten(ready: Ready) -> None:
    """Append-only, enforced by the trigger. A decision is a thing that happened;
    changing your mind is a new row."""
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve",
            rationale="Reviewed.",
        )
    async with session_scope(ready.tenant_id) as session:
        row = (await session.execute(select(VendorApproval))).scalars().one()
        row.decision = "reject"
        with pytest.raises(DBAPIError):
            await session.flush()


# -- the gate-freshness rule ---------------------------------------------------


async def test_a_send_back_invalidates_an_approval_without_touching_it(
    ready: Ready,
) -> None:
    """The whole point of `decided_at >= stage.entered_at`: the old decision stays
    in the record and simply stops satisfying a stage that restarted after it."""
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve",
            rationale="Reviewed.",
        )
        detail = await vendor_service.get_vendor(
            session, tenant_id=ready.tenant_id, vendor_id=ready.vendor_id
        )
    approval_stage = next(s for s in detail.stages if s.stage == "approval")
    decided = next(c for c in approval_stage.checks if c.code == "approval.decided")
    assert decided.satisfied is True, "the decision counts before any send-back"

    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.send_back(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            stage_id=approval_stage.id,
            to_stage="tiering",
            reason="The classification was wrong.",
        )

    approval_stage = next(s for s in detail.stages if s.stage == "approval")
    decided = next(c for c in approval_stage.checks if c.code == "approval.decided")
    assert decided.satisfied is False
    assert "predates" in (decided.detail or "")

    # And the approval row itself is untouched.
    async with session_scope(ready.tenant_id) as session:
        row = (await session.execute(select(VendorApproval))).scalars().one()
    assert row.decision == "approve"


# -- the paperwork -------------------------------------------------------------


async def test_a_contract_satisfies_the_contracting_check_for_an_exposed_tier(
    critical: Ready,
) -> None:
    """Section 2 wrote this rule against a table that did not exist. Nothing in
    lifecycle.py changed; the collector caught up."""
    async with session_scope(critical.tenant_id) as session:
        detail = await vendor_service.get_vendor(
            session, tenant_id=critical.tenant_id, vendor_id=critical.vendor_id
        )
    contracting = next(s for s in detail.stages if s.stage == "contracting")
    assert [c.code for c in contracting.blockers] == ["contracting.contract_linked"]
    assert not contracting.pending, "the contract table exists now; nothing should abstain"

    async with session_scope(critical.tenant_id) as session:
        await vendor_service.add_contract(
            session,
            tenant_id=critical.tenant_id,
            actor=critical.owner,
            vendor_id=critical.vendor_id,
            data=ContractInput(title="Master services agreement", status="active"),
        )
        detail = await vendor_service.get_vendor(
            session, tenant_id=critical.tenant_id, vendor_id=critical.vendor_id
        )
    contracting = next(s for s in detail.stages if s.stage == "contracting")
    assert not contracting.blockers


async def test_an_auto_renewing_contract_reports_its_notice_deadline(
    ready: Ready,
) -> None:
    """The date somebody actually needs is never the one printed on the contract."""
    renewal = _today() + timedelta(days=120)
    async with session_scope(ready.tenant_id) as session:
        contract = await vendor_service.add_contract(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=ContractInput(
                title="Master services agreement",
                status="active",
                renewal_date=renewal,
                auto_renew=True,
                notice_period_days=90,
                right_to_audit=True,
                exit_data_return_clause=True,
            ),
        )
    assert contract.notice_deadline == renewal - timedelta(days=90)
    assert contract.clauses_present == 2


async def test_a_qualified_soc_opinion_raises_a_finding_rather_than_being_filed(
    ready: Ready,
) -> None:
    """Recording the review and leaving the reader to notice is how a bad report
    gets filed and forgotten."""
    async with session_scope(ready.tenant_id) as session:
        review = await vendor_service.review_soc_report(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=SocReviewInput(
                opinion="qualified",
                audit_period_start=_today() - timedelta(days=400),
                audit_period_end=_today() - timedelta(days=200),
                cpa_firm="A Firm LLP",
            ),
        )
    assert review.opinion == "qualified"
    # The period ended more than a year ago and there is no bridge letter.
    assert review.needs_bridge_letter is True

    async with session_scope(ready.tenant_id) as session:
        findings = await vendor_service.list_findings(
            session, tenant_id=ready.tenant_id, vendor_id=ready.vendor_id
        )
    assert any(f.finding_source == "document_review" for f in findings)


async def test_a_document_reports_its_expiry_rather_than_storing_it(
    ready: Ready,
) -> None:
    async with session_scope(ready.tenant_id) as session:
        expired = await vendor_service.add_document(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=DocumentInput(
                title="ISO 27001 certificate",
                doc_type="iso_cert",
                issue_date=_today() - timedelta(days=800),
                valid_until=_today() - timedelta(days=10),
            ),
        )
    assert expired.is_expired is True
    assert expired.expires_in_days == -10

    async with session_scope(ready.tenant_id) as session:
        due = await vendor_service.expiring_documents(session, tenant_id=ready.tenant_id)
    assert [d.id for d in due] == [expired.id]


async def test_a_document_cannot_expire_before_it_was_issued(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="expires before"):
            await vendor_service.add_document(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                data=DocumentInput(
                    title="Backwards",
                    issue_date=_today(),
                    valid_until=_today() - timedelta(days=1),
                ),
            )


async def test_a_shared_subprocessor_shows_its_concentration(ready: Ready) -> None:
    """The question a fourth-party register exists to answer: how much of our
    estate depends on this one supplier."""
    async with session_scope(ready.tenant_id) as session:
        cloud = await vendor_service.create_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            data=VendorInput(name="Bigcloud Inc"),
        )
        second = await vendor_service.create_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            data=VendorInput(name="Another Supplier"),
        )
        await vendor_service.add_subprocessor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=SubprocessorInput(name="Bigcloud", linked_vendor_id=cloud.id),
        )
        subs = await vendor_service.add_subprocessor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=second.id,
            data=SubprocessorInput(name="Bigcloud", linked_vendor_id=cloud.id),
        )
    assert subs[0].also_used_by_vendors == 1


async def test_a_vendor_cannot_subprocess_to_itself(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="own subprocessor"):
            await vendor_service.add_subprocessor(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                data=SubprocessorInput(name="Itself", linked_vendor_id=ready.vendor_id),
            )


# -- intake --------------------------------------------------------------------


async def test_a_declined_request_creates_no_vendor_and_keeps_its_reason(
    ready: Ready,
) -> None:
    """The register stays a list of vendors the organisation actually uses."""
    async with session_scope(ready.tenant_id) as session:
        request = await vendor_service.request_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            data=IntakeInput(vendor_name="Sketchy Analytics", proposed_service="Web analytics"),
        )
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="why the request"):
            await vendor_service.decide_intake(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                request_id=request.id,
                approve=False,
            )
    async with session_scope(ready.tenant_id) as session:
        declined = await vendor_service.decide_intake(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            request_id=request.id,
            approve=False,
            reason="They will not sign a DPA.",
        )
    assert declined.decision == "rejected"
    assert declined.created_vendor_id is None
    assert "DPA" in (declined.decision_reason or "")


async def test_an_accepted_request_creates_the_vendor_and_its_first_engagement(
    ready: Ready,
) -> None:
    async with session_scope(ready.tenant_id) as session:
        request = await vendor_service.request_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            data=IntakeInput(vendor_name="Helpful Tooling", department="Engineering"),
        )
        accepted = await vendor_service.decide_intake(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            request_id=request.id,
            approve=True,
        )
    assert accepted.decision == "approved"
    assert accepted.created_vendor_id is not None

    async with session_scope(ready.tenant_id) as session:
        created = await vendor_service.get_vendor(
            session, tenant_id=ready.tenant_id, vendor_id=accepted.created_vendor_id
        )
    assert created.name == "Helpful Tooling"
    assert len(created.engagements) == 1


async def test_a_request_for_a_vendor_we_already_have_is_flagged(ready: Ready) -> None:
    """Screening is a name match, not a judgement — the requester should know
    before anyone spends time reviewing it."""
    async with session_scope(ready.tenant_id) as session:
        request = await vendor_service.request_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            data=IntakeInput(vendor_name="Acme Cloud, Inc."),
        )
    assert request.screening_status == "flagged"
    assert request.duplicates


async def test_a_request_cannot_be_decided_twice(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        request = await vendor_service.request_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            data=IntakeInput(vendor_name="Once Only"),
        )
        await vendor_service.decide_intake(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            request_id=request.id,
            approve=True,
        )
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(Conflict, match="already been decided"):
            await vendor_service.decide_intake(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                request_id=request.id,
                approve=True,
            )


# -- the exit ------------------------------------------------------------------


async def test_an_exit_cannot_be_completed_with_steps_outstanding(ready: Ready) -> None:
    """An offboarding marked complete with access still live is exactly the record
    an auditor uses to show the process is theatre."""
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.offboard(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            engagement_id=None,
            reason="Contract not renewed.",
        )
        offboarding_id = (await session.execute(select(VendorOffboarding.id))).scalar_one()

    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(Conflict, match="not finished"):
            await vendor_service.complete_offboarding(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                offboarding_id=offboarding_id,
                data=OffboardingCompletion(access_revoked=True, complete=True),
            )

    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.complete_offboarding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            offboarding_id=offboarding_id,
            data=OffboardingCompletion(
                access_revoked=True,
                data_returned=True,
                contract_provisions_reviewed=True,
                final_payments_settled=True,
                complete=True,
            ),
        )
    # Archived, never deleted (rule 6).
    assert detail.lifecycle_status == "archived"


async def test_offboarding_without_a_reason_is_refused(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="why the relationship"):
            await vendor_service.offboard(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                engagement_id=None,
                reason="  ",
            )


# -- reassessment --------------------------------------------------------------


async def _go_live(ready: Ready) -> VendorDetailView:
    """Approve the engagement at the gate and walk it through onboarding."""
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision="approve",
            rationale="Reviewed.",
        )
        for name in ("approval", "onboarding"):
            detail = await vendor_service.advance_stage(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.other,
                vendor_id=ready.vendor_id,
                stage_id=next(s.id for s in detail.stages if s.stage == name),
            )
    return detail


async def _reassess(ready: Ready) -> VendorDetailView:
    async with session_scope(ready.tenant_id) as session:
        return await vendor_service.open_reassessment(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
        )


async def test_a_new_cycle_lays_out_fresh_stages_and_keeps_the_old_ones(
    ready: Ready,
) -> None:
    before = await _go_live(ready)
    assert before.engagements[0].status == "active"
    detail = await _reassess(ready)
    assert {s.cycle for s in before.stages} == {1}
    assert {s.cycle for s in detail.stages} == {2}
    assert len(detail.stages) == len(lifecycle.STAGES)
    # The old cycle is closed, not left with a stage in progress forever.
    async with session_scope(ready.tenant_id) as session:
        old = (await session.execute(select(VendorStage).where(VendorStage.cycle == 1))).scalars()
        statuses = {row.stage: row.status for row in old}
    assert "in_progress" not in statuses.values()
    assert statuses["reassessment"] == "complete"


async def test_the_next_review_waits_for_this_one_to_pass_the_gate(ready: Ready) -> None:
    """Opening a new cycle mid-review would hide the review in flight."""
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(Conflict, match="still under way"):
            await vendor_service.open_reassessment(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                engagement_id=ready.engagement_id,
            )


async def test_a_late_review_does_not_push_the_next_one_late(ready: Ready) -> None:
    """Reviews drifting a little further out every cycle is the failure this rule
    exists to prevent (ER 101)."""
    await _go_live(ready)
    due = _today() - timedelta(days=40)
    async with session_scope(ready.tenant_id) as session:
        vendor = await session.get(Vendor, ready.vendor_id)
        assert vendor is not None
        vendor.next_reassessment_on = due
    detail = await _reassess(ready)
    # Anchored to the date it was due, not to today. Low tier reviews every three
    # years, which is the proportionality the tier is *for*.
    assert detail.next_reassessment_on == due + timedelta(days=_LOW_TIER_CADENCE_DAYS)


async def test_an_early_review_books_the_next_one_from_today(ready: Ready) -> None:
    """Anchoring an early review on its due date would stretch the gap between two
    reviews past the cadence."""
    await _go_live(ready)
    detail = await _reassess(ready)
    assert detail.next_reassessment_on == _today() + timedelta(days=_LOW_TIER_CADENCE_DAYS)


async def test_the_reassessment_queue_finds_what_is_due(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        due = await vendor_service.due_for_reassessment(
            session,
            tenant_id=ready.tenant_id,
            on=_today() + timedelta(days=_LOW_TIER_CADENCE_DAYS + 1),
        )
    assert ready.vendor_id in due

    async with session_scope(ready.tenant_id) as session:
        not_yet = await vendor_service.due_for_reassessment(
            session, tenant_id=ready.tenant_id, on=_today()
        )
    assert ready.vendor_id not in not_yet


async def test_an_archived_vendor_drops_out_of_the_queue(ready: Ready) -> None:
    """Chasing a review for a vendor you no longer use is the kind of noise that
    teaches people to ignore the queue."""
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.update_vendor(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=VendorInput(name="Acme Cloud"),
        )
        vendor = await vendor_service.get_vendor(
            session, tenant_id=ready.tenant_id, vendor_id=ready.vendor_id
        )
        assert vendor is not None
        await vendor_service.offboard(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            engagement_id=None,
            reason="No longer used.",
        )
        offboarding_id = (await session.execute(select(VendorOffboarding.id))).scalar_one()
        await vendor_service.complete_offboarding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            offboarding_id=offboarding_id,
            data=OffboardingCompletion(
                access_revoked=True,
                data_returned=True,
                contract_provisions_reviewed=True,
                final_payments_settled=True,
                complete=True,
            ),
        )
    async with session_scope(ready.tenant_id) as session:
        due = await vendor_service.due_for_reassessment(
            session,
            tenant_id=ready.tenant_id,
            on=_today() + timedelta(days=_LOW_TIER_CADENCE_DAYS * 2),
        )
    assert ready.vendor_id not in due


# -- the roster ----------------------------------------------------------------


async def test_the_roster_resolves_a_role_to_a_person(critical: Ready) -> None:
    """Together with the tiering policy's required roles, this is the whole of
    spec 82's "required reviewers" — and it needed no table of its own."""
    async with session_scope(critical.tenant_id) as session:
        roster = await vendor_service.set_roster_role(
            session,
            tenant_id=critical.tenant_id,
            actor=critical.owner,
            role="security",
            membership_id=critical.other_membership_id,
        )
    assert roster["security"] == (critical.other_membership_id,)

    async with session_scope(critical.tenant_id) as session:
        detail = await vendor_service.get_vendor(
            session, tenant_id=critical.tenant_id, vendor_id=critical.vendor_id
        )
    diligence = next(s for s in detail.stages if s.stage == "diligence")
    reviewers = next(c for c in diligence.checks if c.code == "diligence.reviewers_assigned")
    # Critical tier wants security, privacy and legal; only security is rostered.
    assert reviewers.satisfied is False
    assert "Privacy" in (reviewers.detail or "")


async def test_setting_a_roster_role_twice_is_idempotent(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.set_roster_role(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            role="legal",
            membership_id=ready.other_membership_id,
        )
        roster = await vendor_service.set_roster_role(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            role="legal",
            membership_id=ready.other_membership_id,
        )
    assert roster["legal"] == (ready.other_membership_id,)


# -- the gate refuses an unsupported "yes" --------------------------------------


async def _finding(
    ready: Ready,
    *,
    engagement_id: uuid.UUID | None,
    severity: str = "high",
    blocking: bool = True,
) -> uuid.UUID:
    async with session_scope(ready.tenant_id) as session:
        finding = VendorFinding(
            id=uuid7(),
            tenant_id=ready.tenant_id,
            vendor_id=ready.vendor_id,
            engagement_id=engagement_id,
            title="No MFA on administrator accounts",
            finding_source="assessment",
            severity=severity,
            is_blocking=blocking,
        )
        session.add(finding)
        await session.flush()
        return finding.id


async def _decide(ready: Ready, decision: str, rationale: str = "Reviewed.") -> VendorDetailView:
    async with session_scope(ready.tenant_id) as session:
        return await vendor_service.decide(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            engagement_id=ready.engagement_id,
            decision=decision,
            rationale=rationale,
        )


async def test_the_gate_refuses_an_approval_while_a_blocking_finding_is_open(
    ready: Ready,
) -> None:
    """A non-negotiable answered badly blocks, whatever its severity, and the gate
    refuses the "yes" rather than recording it and failing the exit later."""
    finding_id = await _finding(ready, engagement_id=ready.engagement_id)
    with pytest.raises(Conflict, match="still open"):
        await _decide(ready, "approve")

    # Saying "not yet" is always allowed.
    deferred = await _decide(ready, "defer", "Waiting on the MFA fix.")
    assert deferred.approvals[0].decision == "defer"

    # Closing a blocking finding needs a note, and closing it clears the way.
    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(InvalidInput, match="how this was resolved"):
            await vendor_service.close_finding(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                finding_id=finding_id,
            )
        await vendor_service.close_finding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            finding_id=finding_id,
            note="MFA enforced for every administrator; screenshot on file.",
        )
    approved = await _decide(ready, "approve", "MFA now enforced.")
    assert approved.approvals[0].decision == "approve"


async def test_a_blocking_finding_on_another_engagement_does_not_hold_this_gate(
    ready: Ready,
) -> None:
    """One department's review is not held by another's. Vendor-wide findings,
    with no engagement named, still hold every gate."""
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.add_engagement(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=EngagementInput(name="Marketing analytics"),
        )
    elsewhere = next(e.id for e in detail.engagements if e.id != ready.engagement_id)
    await _finding(ready, engagement_id=elsewhere)
    approved = await _decide(ready, "approve")
    assert approved.approvals[0].decision == "approve"


async def test_a_vendor_wide_blocking_finding_holds_the_gate(ready: Ready) -> None:
    await _finding(ready, engagement_id=None, severity="critical", blocking=False)
    with pytest.raises(Conflict, match="still open"):
        await _decide(ready, "approve")


async def test_a_later_reject_withdraws_an_earlier_approval(ready: Ready) -> None:
    """Counting approvals alone let a later "no" sit on the record while the gate
    still opened on the "yes" before it."""
    await _decide(ready, "approve")
    detail = await _decide(ready, "reject", "Their breach notice changes this.")
    gate = next(s for s in detail.stages if s.stage == "approval")
    decided = next(c for c in gate.checks if c.code == "approval.decided")
    assert decided.satisfied is False
    assert "rejected" in (decided.detail or "")
    assert "advance" not in gate.allowed_transitions
    assert detail.engagements[0].status == "on_hold"


async def test_the_picker_bars_a_member_who_cannot_approve_vendors(ready: Ready) -> None:
    """The route refuses them anyway. The picker says so before a rationale is
    written, and lists the people who can decide first."""
    invited = await invite_directly(
        ready.workspace,
        email="analyst@alpha.example",
        full_name="Sam Lee",
        role_name="Security Officer",
    )
    async with session_scope(ready.tenant_id) as session:
        approvers = await vendor_service.approvers(
            session, tenant_id=ready.tenant_id, engagement_id=ready.engagement_id
        )
    sam = next(a for a in approvers if a.membership_id == invited.member.membership_id)
    assert sam.disqualified_reason == "does not hold the vendor approval permission"
    assert approvers[0].disqualified_reason is None


async def test_a_lapsed_acceptance_reopens_the_finding(ready: Ready) -> None:
    """Leaving a finding accepted past its date is the platform asserting a
    decision nobody renewed."""
    finding_id = await _finding(ready, engagement_id=ready.engagement_id)
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.accept_finding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.other,
            vendor_id=ready.vendor_id,
            finding_id=finding_id,
            until=_today() + timedelta(days=30),
            rationale="Compensating control: admin access only from the office network.",
        )
    async with session_scope(ready.tenant_id) as session:
        row = await session.get(VendorFinding, finding_id)
        assert row is not None
        row.accepted_until = _today() - timedelta(days=1)  # the clock moves on
    async with session_scope(ready.tenant_id) as session:
        assert await vendor_service.expire_acceptances(session, tenant_id=ready.tenant_id) == 1
    async with session_scope(ready.tenant_id) as session:
        finding = await vendor_service.get_finding(
            session, tenant_id=ready.tenant_id, finding_id=finding_id
        )
        assert await vendor_service.expire_acceptances(session, tenant_id=ready.tenant_id) == 0
    assert finding.status == "open"
    assert finding.accepted_until is None


async def test_a_closed_finding_can_be_reopened_with_a_reason(ready: Ready) -> None:
    finding_id = await _finding(ready, engagement_id=ready.engagement_id, blocking=False)
    async with session_scope(ready.tenant_id) as session:
        await vendor_service.close_finding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            finding_id=finding_id,
        )
        with pytest.raises(Conflict, match="already closed"):
            await vendor_service.close_finding(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                finding_id=finding_id,
            )
        reopened = await vendor_service.reopen_finding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            finding_id=finding_id,
            reason="The fix was rolled back.",
        )
    assert reopened.status == "open"
    assert reopened.closed_at is None


# -- the exit, end to end --------------------------------------------------------


async def test_an_exit_runs_once_closes_the_review_and_lists_its_steps(ready: Ready) -> None:
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.offboard(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            engagement_id=None,
            reason="Contract not renewed.",
        )
    assert detail.lifecycle_status == "offboarding"
    assert [o.reason for o in detail.offboardings] == ["Contract not renewed."]
    exit_stage = next(s for s in detail.stages if s.stage == "offboarding")
    assert exit_stage.status == "in_progress"
    # The review is closed: nothing moves, and nothing can be approved.
    assert all(s.allowed_transitions == [] for s in detail.stages)
    with pytest.raises(Conflict, match="offboarded"):
        await _decide(ready, "approve")

    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(Conflict, match="already under way"):
            await vendor_service.offboard(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                engagement_id=None,
                reason="Again.",
            )

    everything = OffboardingCompletion(
        access_revoked=True,
        data_returned=True,
        contract_provisions_reviewed=True,
        final_payments_settled=True,
        complete=True,
    )
    async with session_scope(ready.tenant_id) as session:
        done = await vendor_service.complete_offboarding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            offboarding_id=detail.offboardings[0].id,
            data=everything,
        )
    assert done.lifecycle_status == "archived"
    assert done.offboardings[0].completed_at is not None
    assert next(s for s in done.stages if s.stage == "offboarding").status == "complete"

    async with session_scope(ready.tenant_id) as session:
        with pytest.raises(Conflict, match="already complete"):
            await vendor_service.complete_offboarding(
                session,
                tenant_id=ready.tenant_id,
                actor=ready.owner,
                vendor_id=ready.vendor_id,
                offboarding_id=detail.offboardings[0].id,
                data=everything,
            )


async def test_ending_one_engagement_does_not_end_the_vendor(ready: Ready) -> None:
    """Rolled up to the vendor while it runs, and released when it is done: the
    vendor reads what its remaining engagement says, not "offboarding" forever."""
    async with session_scope(ready.tenant_id) as session:
        detail = await vendor_service.add_engagement(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            data=EngagementInput(name="Marketing analytics"),
        )
        leaving = next(e.id for e in detail.engagements if e.id != ready.engagement_id)
        started = await vendor_service.offboard(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            engagement_id=leaving,
            reason="Marketing moved to another tool.",
        )
    assert started.lifecycle_status == "offboarding"
    async with session_scope(ready.tenant_id) as session:
        done = await vendor_service.complete_offboarding(
            session,
            tenant_id=ready.tenant_id,
            actor=ready.owner,
            vendor_id=ready.vendor_id,
            offboarding_id=started.offboardings[0].id,
            data=OffboardingCompletion(
                access_revoked=True,
                data_returned=True,
                contract_provisions_reviewed=True,
                final_payments_settled=True,
                complete=True,
            ),
        )
    by_id = {e.id: e.status for e in done.engagements}
    assert by_id[leaving] == "archived"
    assert done.lifecycle_status == by_id[ready.engagement_id] == "under_review"
