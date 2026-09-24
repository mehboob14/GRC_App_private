"""The questionnaire, the portal and the findings, end to end against Postgres.

The portal half is the security-relevant one, so its tests are written as attacks
rather than as happy paths: a token from another tenant, a question from another
assessment, a revoked link, a replaced link, a submitted questionnaire being
answered again.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

import pytest
from sqlalchemy import select

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import Membership
from verity.modules.tasks.service import task_service
from verity.modules.vendors.models import (
    QuestionnaireQuestion,
    QuestionnaireTemplate,
    VendorPortalToken,
)
from verity.modules.vendors.portal import vendor_portal_service
from verity.modules.vendors.service import (
    ContactInput,
    TieringAnswers,
    VendorInput,
    vendor_service,
)

pytestmark = [pytest.mark.integration]

HOST = "203.0.113.9"


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Issued:
    workspace: Workspace
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID
    assessment_id: uuid.UUID
    token: str
    question_count: int

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.workspace.tenant_id

    @property
    def actor(self) -> Membership:
        return Membership(self.workspace.membership_id)


async def _bank_loaded() -> bool:
    async with session_scope(None) as session:
        return (
            await session.execute(select(QuestionnaireTemplate).limit(1))
        ).scalar_one_or_none() is not None


async def _issue(company: str, email: str, *, tier_answers: TieringAnswers) -> Issued:
    workspace = await signup_workspace(company=company, email=email)
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
        await vendor_service.add_contact(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            data=ContactInput(name="Dana Reed", email="dana@acme.test", contact_type="portal"),
        )
        engagement_id = vendor.engagements[0].id
        await vendor_service.tier_engagement(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            engagement_id=engagement_id,
            answers=tier_answers,
        )
        issued = await vendor_service.issue_questionnaire(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            engagement_id=engagement_id,
        )
    return Issued(
        workspace=workspace,
        vendor_id=vendor.id,
        engagement_id=engagement_id,
        assessment_id=issued.assessment_id,
        token=issued.portal_url.rsplit("/", 1)[-1],
        question_count=issued.question_count,
    )


@pytest.fixture
async def issued() -> Issued:
    if not await _bank_loaded():
        pytest.skip("questionnaire bank not seeded — run `python -m verity.manage seed-content`")
    return await _issue(
        "Alpha Compliance",
        "founder@alpha.example",
        tier_answers=TieringAnswers(fourth_party_reliance=2),
    )


# -- issuing ------------------------------------------------------------------


async def test_the_tier_decides_how_many_questions_are_asked(issued: Issued) -> None:
    """Spec ¶82's "right-sizes assessment depth", as a number a vendor feels.

    A low-tier vendor answers the lite set; a critical one answers everything.
    """
    assert issued.question_count == 15

    critical = await _issue(
        "Bravo Assurance",
        "founder@bravo.example",
        tier_answers=TieringAnswers(data_sensitivity=4, business_criticality=4, system_access=4),
    )
    assert critical.question_count == 59


async def test_issuing_snapshots_the_question_set(issued: Issued) -> None:
    """The tenant's questionnaire can be edited under a vendor mid-answer, so what
    was asked is frozen onto the assessment. With nothing named, the questionnaire
    holding the engagement's tier is the one sent."""
    async with session_scope(issued.tenant_id) as session:
        view = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
    assert view.scope["questionnaire_name"] == "Security review, lite"
    assert view.scope["tier"] == "low"
    assert len(view.scope["question_keys"]) == 15
    assert view.question_count == 15
    assert view.answered_count == 0
    assert view.portal_link_live is True


async def test_a_questionnaire_cannot_be_sent_before_the_engagement_is_tiered() -> None:
    workspace = await signup_workspace(company="Gamma Ltd", email="founder@gamma.example")
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        vendor = await vendor_service.create_vendor(
            session, tenant_id=workspace.tenant_id, actor=actor, data=VendorInput(name="Untiered")
        )
        await vendor_service.add_contact(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            data=ContactInput(name="X", email="x@untiered.test", contact_type="portal"),
        )
        with pytest.raises(Conflict, match=r"[Tt]ier"):
            await vendor_service.issue_questionnaire(
                session,
                tenant_id=workspace.tenant_id,
                actor=actor,
                vendor_id=vendor.id,
                engagement_id=vendor.engagements[0].id,
            )


async def test_the_token_is_stored_only_as_a_hash(issued: Issued) -> None:
    """A dump of the token table cannot be replayed against the portal."""
    async with session_scope(None) as session:
        rows = list((await session.execute(select(VendorPortalToken))).scalars())
    assert len(rows) == 1
    assert rows[0].token_hash != issued.token
    assert issued.token not in rows[0].token_hash
    assert len(rows[0].token_hash) == 64  # sha256 hex


# -- the portal ---------------------------------------------------------------


async def test_a_token_opens_exactly_one_questionnaire_and_nothing_else(
    issued: Issued,
) -> None:
    view = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    assert view.assessment_id == issued.assessment_id
    assert view.vendor_name == "Acme Cloud"
    assert len(view.questions) == 15
    # The scoring weights are ours, not the vendor's: showing them would say which
    # questions to answer generously.
    assert not hasattr(view.questions[0], "weight")
    assert not hasattr(view.questions[0], "critical_control")


async def test_an_unknown_token_is_refused_without_saying_why(issued: Issued) -> None:
    with pytest.raises(NotFound) as seen:
        await vendor_portal_service.open_portal("x" * 43, client_host=HOST)
    assert "expired" in seen.value.message
    assert "not exist" not in seen.value.message


async def test_a_token_cannot_reach_another_tenants_questionnaire(issued: Issued) -> None:
    """The whole point of the design: the token resolves the tenant, and it
    resolves to exactly one."""
    other = await _issue(
        "Bravo Assurance",
        "founder@bravo.example",
        tier_answers=TieringAnswers(fourth_party_reliance=2),
    )
    mine = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    theirs = await vendor_portal_service.open_portal(other.token, client_host=HOST)
    assert mine.assessment_id == issued.assessment_id
    assert theirs.assessment_id == other.assessment_id
    assert mine.assessment_id != theirs.assessment_id

    # Each tenant answers its own copy of the questions, so a question id from the
    # other review is simply not part of this one: it cannot be answered through
    # this token, and answering this token's own questions never touches theirs.
    theirs_question = theirs.questions[0]
    assert theirs_question.id not in {q.id for q in mine.questions}
    with pytest.raises(NotFound, match="not part of this questionnaire"):
        await vendor_portal_service.save_answer(
            issued.token, client_host=HOST, question_id=theirs_question.id, answer="yes"
        )
    await vendor_portal_service.save_answer(
        issued.token, client_host=HOST, question_id=mine.questions[0].id, answer="yes"
    )

    after_mine = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    after_theirs = await vendor_portal_service.open_portal(other.token, client_host=HOST)
    assert after_mine.questions[0].answer == "yes"
    assert all(q.answer is None for q in after_theirs.questions)
    assert after_theirs.answered_count == 0


async def test_reissuing_revokes_the_previous_link(issued: Issued) -> None:
    """What somebody expects from "resend": the old link stops working."""
    async with session_scope(issued.tenant_id) as session:
        again = await vendor_service.issue_questionnaire(
            session,
            tenant_id=issued.tenant_id,
            actor=issued.actor,
            vendor_id=issued.vendor_id,
            engagement_id=issued.engagement_id,
        )
    fresh = again.portal_url.rsplit("/", 1)[-1]
    assert fresh != issued.token

    # The new one works; the old one does not, and the revocation is a written
    # row rather than a deletion, so the history survives.
    await vendor_portal_service.open_portal(fresh, client_host=HOST)
    with pytest.raises(NotFound):
        await vendor_portal_service.open_portal(issued.token, client_host=HOST)

    async with session_scope(None) as session:
        rows = list((await session.execute(select(VendorPortalToken))).scalars())
    assert len(rows) == 2
    assert sum(1 for r in rows if r.revoked_at is not None) == 1


async def test_opening_moves_the_questionnaire_off_pending(issued: Issued) -> None:
    """ "Sent but never opened" and "opened and abandoned" are different things to
    whoever is chasing it."""
    async with session_scope(issued.tenant_id) as session:
        before = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
    assert before.status == "pending"

    await vendor_portal_service.open_portal(issued.token, client_host=HOST)

    async with session_scope(issued.tenant_id) as session:
        after = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
    assert after.status == "in_progress"


async def test_an_answer_is_written_and_audited_as_the_vendor_contact(
    issued: Issued,
) -> None:
    """Rule 5 wants an actor, and "who answered this" is the first thing an
    auditor asks about a vendor questionnaire. It is not the system."""
    view = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    question = view.questions[0]
    updated = await vendor_portal_service.save_answer(
        issued.token,
        client_host=HOST,
        question_id=question.id,
        answer="yes",
        implementation_notes="Enforced through the identity provider.",
    )
    assert updated.answered_count == 1
    assert next(q for q in updated.questions if q.id == question.id).answer == "yes"

    async with session_scope(issued.tenant_id) as session:
        rows = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.object_type == "vendor_assessment_response")
                )
            ).scalars()
        )
    assert rows
    assert {r.actor_type for r in rows} == {"vendor_contact"}
    assert all(r.actor_id is not None for r in rows)


async def test_not_applicable_needs_a_reason(issued: Issued) -> None:
    view = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    with pytest.raises(InvalidInput, match="does not apply"):
        await vendor_portal_service.save_answer(
            issued.token, client_host=HOST, question_id=view.questions[0].id, answer="na"
        )


async def test_an_answer_outside_the_vocabulary_is_refused(issued: Issued) -> None:
    view = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    with pytest.raises(InvalidInput):
        await vendor_portal_service.save_answer(
            issued.token, client_host=HOST, question_id=view.questions[0].id, answer="maybe"
        )


async def test_a_question_outside_this_questionnaire_cannot_be_answered(
    issued: Issued,
) -> None:
    """A token scopes to one assessment, so a valid-looking question id from the
    wider bank is still not answerable through it."""
    async with session_scope(None) as session:
        asked = {
            q.id
            for q in (
                await session.execute(
                    select(QuestionnaireQuestion).where(
                        QuestionnaireQuestion.scope_level == "detail"
                    )
                )
            ).scalars()
        }
    not_asked = next(iter(asked))
    with pytest.raises(NotFound, match="not part of this questionnaire"):
        await vendor_portal_service.save_answer(
            issued.token, client_host=HOST, question_id=not_asked, answer="yes"
        )


async def test_submitting_needs_every_question_answered(issued: Issued) -> None:
    """A partial submission that scores is worse than no score: it produces a
    number that looks like a review and is not one."""
    view = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    await vendor_portal_service.save_answer(
        issued.token, client_host=HOST, question_id=view.questions[0].id, answer="yes"
    )
    with pytest.raises(InvalidInput, match="need an answer"):
        await vendor_portal_service.submit(issued.token, client_host=HOST)


# The smallest thing the shared store's magic-byte sniffer accepts as a PDF.
# Using a real signature rather than arbitrary bytes is the point: the portal goes
# through the same allowlist every other upload in the platform does.
_PDF: Final = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


async def _answer_all(issued: Issued, answer: str = "yes") -> None:
    """Answer every question, attaching a file wherever one is required.

    Submitting refuses a `yes` on an evidence-required question with nothing
    attached, so answering everything means uploading too — which is how the
    portal's upload path gets exercised on the way through.
    """
    view = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    for question in view.questions:
        await vendor_portal_service.save_answer(
            issued.token,
            client_host=HOST,
            question_id=question.id,
            answer=answer,
            na_justification="Not in scope for this service." if answer == "na" else None,
        )
        if question.evidence_required and answer == "yes":
            await vendor_portal_service.attach_evidence(
                issued.token,
                client_host=HOST,
                question_id=question.id,
                filename=f"{question.code}.pdf",
                data=_PDF,
            )


async def test_a_completed_questionnaire_scores_itself_on_submit(issued: Issued) -> None:
    """An internal reviewer opens the record and finds the score waiting, rather
    than a queue item somebody has to remember to process."""
    await _answer_all(issued, "yes")
    submitted = await vendor_portal_service.submit(issued.token, client_host=HOST)
    # Scored already: submitting and scoring are one transaction, so the view the
    # vendor gets back is built after the score exists. That is the point — an
    # internal reviewer never finds a submitted-but-unscored record waiting.
    assert submitted.status == "scored"

    async with session_scope(issued.tenant_id) as session:
        view = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
    assert view.status == "scored"
    assert view.residual_score is not None
    assert view.grade in {"A", "B", "C", "D", "F"}
    # The steps are what makes the number explainable, including the ones that
    # did not fire.
    assert [s["label"] for s in view.score_steps] == [
        "Inherent risk",
        "Weighted domain residual",
        "Clamp to inherent",
        "Critical-control floor",
    ]
    assert view.findings == [], "a vendor that answered yes to everything has no findings"


async def test_a_submitted_questionnaire_refuses_further_answers(issued: Issued) -> None:
    await _answer_all(issued, "yes")
    await vendor_portal_service.submit(issued.token, client_host=HOST)
    view_questions = await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    with pytest.raises(NotFound):
        await vendor_portal_service.save_answer(
            issued.token,
            client_host=HOST,
            question_id=view_questions.questions[0].id,
            answer="no",
        )


# -- findings -----------------------------------------------------------------


async def test_every_no_raises_a_finding_with_a_severity_from_the_question(
    issued: Issued,
) -> None:
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)

    async with session_scope(issued.tenant_id) as session:
        view = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
    # One per question that can have a gap. A free-text question ("which countries
    # hold our data?") is read by a reviewer, not failed by a "no".
    gaps = [r for r in view.responses if any(o["flag"] for o in r.options)]
    free_text = [r for r in view.responses if r.answer_type == "paragraph"]
    assert free_text, "the lite set asks at least one question in the vendor's own words"
    assert len(view.findings) == len(gaps) == view.question_count - len(free_text)
    severities = {f.severity for f in view.findings}
    assert "critical" in severities, "the lite set contains critical controls"
    # A critical-control failure floors the residual, however few questions there were.
    assert view.residual_score is not None
    assert view.residual_score >= 50.0
    blocking = [f for f in view.findings if f.is_blocking]
    assert blocking, "a non-negotiable answered no blocks the approval gate"


async def test_correcting_an_answer_closes_the_finding_it_caused(issued: Issued) -> None:
    """Re-scoring updates the record rather than growing a second copy of it."""
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)

    async with session_scope(issued.tenant_id) as session:
        first = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
        target = first.responses[0]
        response_rows = await vendor_service.answers_with_questions(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
        row = next(r for r, q in response_rows if q.id == target.question_id)
        row.answer = "yes"
        row.answer_value = {"value": "yes"}
        await session.flush()
        second = await vendor_service.score_assessment(
            session,
            tenant_id=issued.tenant_id,
            actor=issued.actor,
            assessment_id=issued.assessment_id,
        )

    assert len(second.findings) == len(first.findings), "no duplicate was raised"
    corrected = next(f for f in second.findings if f.question_id == target.question_id)
    assert corrected.status == "closed"
    assert corrected.closed_at is not None


async def test_remediation_opens_a_real_task_in_the_tasks_module(issued: Issued) -> None:
    """Not a vendor-local to-do list that no dashboard counts."""
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)

    async with session_scope(issued.tenant_id) as session:
        findings = await vendor_service.list_findings(
            session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
        )
        finding = findings[0]
        updated = await vendor_service.remediate_finding(
            session,
            tenant_id=issued.tenant_id,
            actor=issued.actor,
            vendor_id=issued.vendor_id,
            finding_id=finding.id,
            owner_membership_id=issued.workspace.membership_id,
        )
    assert updated.task_id is not None
    assert updated.status == "in_remediation"

    async with session_scope(issued.tenant_id) as session:
        task = await task_service.get_task(
            session, tenant_id=issued.tenant_id, task_id=updated.task_id
        )
    assert "Acme Cloud" in task.title


async def test_a_finding_cannot_be_remediated_twice(issued: Issued) -> None:
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)
    async with session_scope(issued.tenant_id) as session:
        findings = await vendor_service.list_findings(
            session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
        )
        await vendor_service.remediate_finding(
            session,
            tenant_id=issued.tenant_id,
            actor=issued.actor,
            vendor_id=issued.vendor_id,
            finding_id=findings[0].id,
        )
    async with session_scope(issued.tenant_id) as session:
        with pytest.raises(Conflict, match="already has a remediation task"):
            await vendor_service.remediate_finding(
                session,
                tenant_id=issued.tenant_id,
                actor=issued.actor,
                vendor_id=issued.vendor_id,
                finding_id=findings[0].id,
            )


async def test_accepting_a_risk_is_time_boxed_and_reasoned(issued: Issued) -> None:
    """An open-ended acceptance is a risk nobody will look at again."""
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)
    async with session_scope(issued.tenant_id) as session:
        findings = await vendor_service.list_findings(
            session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
        )
        target = findings[0].id

    async with session_scope(issued.tenant_id) as session:
        with pytest.raises(InvalidInput, match="expire in the future"):
            await vendor_service.accept_finding(
                session,
                tenant_id=issued.tenant_id,
                actor=issued.actor,
                vendor_id=issued.vendor_id,
                finding_id=target,
                until=datetime.now(UTC).date(),
                rationale="Fine for now.",
            )

    async with session_scope(issued.tenant_id) as session:
        with pytest.raises(InvalidInput, match="why this risk is acceptable"):
            await vendor_service.accept_finding(
                session,
                tenant_id=issued.tenant_id,
                actor=issued.actor,
                vendor_id=issued.vendor_id,
                finding_id=target,
                until=datetime.now(UTC).date() + timedelta(days=90),
                rationale="   ",
            )

    async with session_scope(issued.tenant_id) as session:
        accepted = await vendor_service.accept_finding(
            session,
            tenant_id=issued.tenant_id,
            actor=issued.actor,
            vendor_id=issued.vendor_id,
            finding_id=target,
            until=datetime.now(UTC).date() + timedelta(days=90),
            rationale="Compensating control: the data is tokenised before it reaches them.",
        )
    assert accepted.status == "accepted"
    assert accepted.treatment == "accept"
    assert accepted.accepted_until is not None


async def test_an_accepted_risk_stops_counting_as_open(issued: Issued) -> None:
    """Acceptance is a decision somebody made and time-boxed, not an outstanding
    item — so it must not keep the approval gate shut."""
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)

    async with session_scope(issued.tenant_id) as session:
        before = await vendor_service.open_critical_count(
            session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
        )
        # What holds the gate: critical findings, and any finding a
        # non-negotiable question marked blocking, whatever its severity.
        criticals = [
            f
            for f in await vendor_service.list_findings(
                session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
            )
            if f.severity == "critical" or f.is_blocking
        ]
    assert before == len(criticals) > 0

    for finding in criticals:
        async with session_scope(issued.tenant_id) as session:
            await vendor_service.accept_finding(
                session,
                tenant_id=issued.tenant_id,
                actor=issued.actor,
                vendor_id=issued.vendor_id,
                finding_id=finding.id,
                until=datetime.now(UTC).date() + timedelta(days=30),
                rationale="Accepted pending their next audit.",
            )

    async with session_scope(issued.tenant_id) as session:
        after = await vendor_service.open_critical_count(
            session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
        )
    assert after == 0


async def test_findings_reach_the_lifecycle_checks_that_were_pending(
    issued: Issued,
) -> None:
    """Section 2 wrote these rules against facts that did not exist yet. Nothing
    in the rules changed; the collector now fills them in."""
    await _answer_all(issued, "no")
    await vendor_portal_service.submit(issued.token, client_host=HOST)

    async with session_scope(issued.tenant_id) as session:
        detail = await vendor_service.get_vendor(
            session, tenant_id=issued.tenant_id, vendor_id=issued.vendor_id
        )
    approval = next(s for s in detail.stages if s.stage == "approval")
    critical_check = next(
        c for c in approval.checks if c.code == "approval.no_unmitigated_critical"
    )
    assert critical_check.satisfied is False, "it is answerable now, and it is failing"


async def test_a_review_sent_from_the_shipped_bank_still_answers_and_scores() -> None:
    """API clients that name the bank keep the older path: rows point at bank
    questions, answers use yes/partial/no/na, and scoring reads them as before."""
    if not await _bank_loaded():
        pytest.skip("questionnaire bank not seeded")
    workspace = await signup_workspace(company="Kilo Bank", email="founder@kilo.example")
    actor = Membership(workspace.membership_id)
    async with session_scope(workspace.tenant_id) as session:
        vendor = await vendor_service.create_vendor(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            data=VendorInput(
                name="Legacy Co", business_owner_membership_id=workspace.membership_id
            ),
        )
        await vendor_service.add_contact(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            data=ContactInput(name="Lee", email="lee@legacy.test", contact_type="portal"),
        )
        engagement_id = vendor.engagements[0].id
        await vendor_service.tier_engagement(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            engagement_id=engagement_id,
            answers=TieringAnswers(fourth_party_reliance=2),
        )
        issued = await vendor_service.issue_questionnaire(
            session,
            tenant_id=workspace.tenant_id,
            actor=actor,
            vendor_id=vendor.id,
            engagement_id=engagement_id,
            bank_code="verity-core",
        )
    token = issued.portal_url.rsplit("/", 1)[-1]
    legacy = Issued(
        workspace=workspace,
        vendor_id=vendor.id,
        engagement_id=engagement_id,
        assessment_id=issued.assessment_id,
        token=token,
        question_count=issued.question_count,
    )
    assert legacy.question_count == 15
    async with session_scope(workspace.tenant_id) as session:
        view = await vendor_service.get_assessment(
            session, tenant_id=workspace.tenant_id, assessment_id=issued.assessment_id
        )
    assert view.scope["bank_code"] == "verity-core"

    await _answer_all(legacy, "yes")
    submitted = await vendor_portal_service.submit(token, client_host=HOST)
    assert submitted.status == "scored"


async def test_offboarding_revokes_the_portal_link(issued: Issued) -> None:
    """A portal link is a credential held outside the organisation. It must not
    outlive the relationship it was issued for."""
    await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    async with session_scope(issued.tenant_id) as session:
        await vendor_service.offboard(
            session,
            tenant_id=issued.tenant_id,
            actor=issued.actor,
            vendor_id=issued.vendor_id,
            engagement_id=None,
            reason="Contract ended.",
        )
    with pytest.raises(NotFound):
        await vendor_portal_service.open_portal(issued.token, client_host=HOST)
    async with session_scope(issued.tenant_id) as session:
        view = await vendor_service.get_assessment(
            session, tenant_id=issued.tenant_id, assessment_id=issued.assessment_id
        )
        with pytest.raises(Conflict, match="offboarded"):
            await vendor_service.issue_questionnaire(
                session,
                tenant_id=issued.tenant_id,
                actor=issued.actor,
                vendor_id=issued.vendor_id,
                engagement_id=issued.engagement_id,
            )
    assert view.status == "expired"


async def test_a_questionnaire_is_scored_only_once_submitted(issued: Issued) -> None:
    """Scoring an unsubmitted questionnaire locked the vendor out of answering it."""
    async with session_scope(issued.tenant_id) as session:
        with pytest.raises(Conflict, match="not submitted"):
            await vendor_service.score_assessment(
                session,
                tenant_id=issued.tenant_id,
                actor=issued.actor,
                assessment_id=issued.assessment_id,
            )
