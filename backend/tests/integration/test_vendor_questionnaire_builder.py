"""Questionnaires a tenant builds: the library, the builder, tiering and dispatch.

Three promises carry the feature, and each test below pins one of them:

- A tenant can build what real programmes ask: choice, multiple choice, text,
  numbers, dates and files, required or optional, with branching and evidence
  rules, started from the library or from nothing.
- Answers are scored by the options a tenant set, for the tier (exposure) and for
  the residual (control credit), and the vendor never sees how.
- Editing a questionnaire never changes a tier already set or a review already sent.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Final

import pytest
from sqlalchemy import select

from tests.support.iam import Workspace, signup_workspace
from verity.core.db import dispose_engine, session_scope
from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.models import AuditLog
from verity.modules.audit.service import Membership
from verity.modules.vendors.models import QuestionnaireTemplate
from verity.modules.vendors.portal import vendor_portal_service
from verity.modules.vendors.questionnaires import (
    QuestionInput,
    QuestionnaireInput,
    QuestionnaireView,
    questionnaire_service,
)
from verity.modules.vendors.service import (
    ContactInput,
    QuestionnaireTieringInput,
    VendorInput,
    vendor_service,
)

pytestmark = [pytest.mark.integration]

HOST: Final = "203.0.113.9"
_PDF: Final = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


@pytest.fixture(autouse=True)
async def _fresh_state(
    clean_iam: None, clean_tenancy: None, clean_audit_log: None
) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@dataclass(frozen=True, slots=True)
class Tenant:
    workspace: Workspace

    @property
    def id(self) -> uuid.UUID:
        return self.workspace.tenant_id

    @property
    def actor(self) -> Membership:
        return Membership(self.workspace.membership_id)


async def _library_loaded() -> bool:
    async with session_scope(None) as session:
        return (
            await session.execute(
                select(QuestionnaireTemplate).where(QuestionnaireTemplate.purpose == "tiering")
            )
        ).scalar_one_or_none() is not None


@pytest.fixture
async def tenant() -> Tenant:
    if not await _library_loaded():
        pytest.skip(
            "questionnaire libraries not seeded, run `python -m verity.manage seed-content`"
        )
    return Tenant(await signup_workspace(company="Delta Health", email="founder@delta.example"))


def _choice(*options: tuple[str, str, float], **extra: object) -> list[dict[str, Any]]:
    return [{"key": k, "label": label, "score": score, **extra} for k, label, score in options]


async def _vendor(tenant: Tenant, name: str = "Northwind") -> tuple[uuid.UUID, uuid.UUID]:
    async with session_scope(tenant.id) as session:
        vendor = await vendor_service.create_vendor(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            data=VendorInput(
                name=name, business_owner_membership_id=tenant.workspace.membership_id
            ),
        )
        await vendor_service.add_contact(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor.id,
            data=ContactInput(name="Lee Park", email="lee@northwind.test", contact_type="portal"),
        )
    return vendor.id, vendor.engagements[0].id


# -- the library and the defaults ---------------------------------------------


async def test_a_new_workspace_gets_starting_questionnaires_exactly_once(tenant: Tenant) -> None:
    async with session_scope(tenant.id) as session:
        first = await questionnaire_service.list_questionnaires(session, tenant_id=tenant.id)
    async with session_scope(tenant.id) as session:
        second = await questionnaire_service.list_questionnaires(session, tenant_id=tenant.id)
    assert [q.id for q in first] == [q.id for q in second]

    tiering = [q for q in first if q.purpose == "tiering"]
    assert len(tiering) == 1
    assert tiering[0].is_default is True
    assert tiering[0].question_count == 5, "the standard set is the five factors"

    by_tier = {t: q.name for q in first if q.purpose == "due_diligence" for t in q.default_tiers}
    assert by_tier == {
        "low": "Security review, lite",
        "medium": "Security review, core",
        "high": "Security review, full",
        "critical": "Security review, full",
    }

    async with session_scope(tenant.id) as session:
        audit = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.object_type == "vendor_questionnaire")
                )
            ).scalars()
        )
    assert len(audit) == len(first)
    assert {row.actor_type for row in audit} == {"system"}


async def test_starting_from_a_library_preset_copies_its_questions(tenant: Tenant) -> None:
    async with session_scope(tenant.id) as session:
        library = await questionnaire_service.library(session, purpose="tiering")
        template = next(t for t in library if t.code == "verity-inherent-risk")
        extended = next(p for p in template.presets if p.key == "extended")
        view = await questionnaire_service.create_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            purpose="tiering",
            name="Engineering vendors",
            library_code=template.code,
            preset="extended",
        )
    assert view.question_count == extended.question_count
    multi = next(q for q in view.questions if q.library_code == "tier.data.types")
    assert multi.answer_type == "multi_choice"
    assert any(o["min_tier"] == "high" for o in multi.options)
    assert view.is_default is False, "the workspace already has a default"


async def test_library_branches_arrive_wired_to_the_copied_parent(tenant: Tenant) -> None:
    async with session_scope(tenant.id) as session:
        view = await questionnaire_service.create_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            purpose="due_diligence",
            name="Profile",
            library_code="verity-vendor-profile",
        )
    parent = next(q for q in view.questions if q.library_code == "vp.assurance.attestations")
    report = next(q for q in view.questions if q.library_code == "vp.assurance.soc2_report")
    assert report.answer_type == "file"
    assert report.condition == {
        "question_id": str(parent.id),
        "option_keys": ["soc2_type2", "soc2_type1"],
    }


# -- building -----------------------------------------------------------------


async def test_every_question_type_can_be_built_and_rules_are_enforced(tenant: Tenant) -> None:
    async with session_scope(tenant.id) as session:
        blank = await questionnaire_service.create_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            purpose="due_diligence",
            name="AI suppliers",
        )
        assert blank.question_count == 0
        qid = blank.id
        view = blank
        for answer_type, extra in (
            ("single_choice", {"options": _choice(("yes", "Yes", 100), ("no", "No", 0))}),
            (
                "multi_choice",
                {"options": _choice(("a", "A", 50), ("b", "B", 100), ("c", "C", 0))},
            ),
            ("text", {}),
            ("paragraph", {"required": False}),
            ("number", {}),
            ("date", {}),
            ("file", {}),
        ):
            view = await questionnaire_service.add_question(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=qid,
                data=QuestionInput(
                    prompt=f"A {answer_type} question", answer_type=answer_type, **extra
                ),
            )
    assert [q.answer_type for q in view.questions] == [
        "single_choice",
        "multi_choice",
        "text",
        "paragraph",
        "number",
        "date",
        "file",
    ]
    assert all(o["key"] for q in view.questions for o in q.options)

    async with session_scope(tenant.id) as session:
        with pytest.raises(InvalidInput, match="at least two options"):
            await questionnaire_service.add_question(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=qid,
                data=QuestionInput(
                    prompt="Lonely", answer_type="single_choice", options=_choice(("x", "X", 1))
                ),
            )
    text_question = view.questions[2]
    async with session_scope(tenant.id) as session:
        with pytest.raises(InvalidInput, match="choice question"):
            await questionnaire_service.add_question(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=qid,
                data=QuestionInput(
                    prompt="Follow up",
                    answer_type="text",
                    condition={"question_id": str(text_question.id), "option_keys": ["x"]},
                ),
            )


async def test_removing_a_parent_releases_its_follow_ups(tenant: Tenant) -> None:
    async with session_scope(tenant.id) as session:
        view = await questionnaire_service.create_questionnaire(
            session, tenant_id=tenant.id, actor=tenant.actor, purpose="tiering", name="Small"
        )
        view = await questionnaire_service.add_question(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            questionnaire_id=view.id,
            data=QuestionInput(
                prompt="Uses AI?",
                options=_choice(("no", "No", 0), ("yes", "Yes", 2)),
            ),
        )
        parent = view.questions[0]
        view = await questionnaire_service.add_question(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            questionnaire_id=view.id,
            data=QuestionInput(
                prompt="Trains on our data?",
                options=_choice(("no", "No", 0), ("yes", "Yes", 4)),
                condition={"question_id": str(parent.id), "option_keys": ["yes"]},
            ),
        )
        child = view.questions[1]
        with pytest.raises(InvalidInput, match="after the question it depends on"):
            await questionnaire_service.reorder_questions(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=view.id,
                question_ids=[child.id, parent.id],
            )
        view = await questionnaire_service.delete_question(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            questionnaire_id=view.id,
            question_id=parent.id,
        )
    assert [q.id for q in view.questions] == [child.id]
    assert view.questions[0].condition == {}


async def test_a_tier_belongs_to_one_questionnaire_and_the_default_cannot_be_archived(
    tenant: Tenant,
) -> None:
    async with session_scope(tenant.id) as session:
        rows = await questionnaire_service.list_questionnaires(session, tenant_id=tenant.id)
        lite = next(q for q in rows if q.name == "Security review, lite")
        core = next(q for q in rows if q.name == "Security review, core")
        await questionnaire_service.update_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            questionnaire_id=core.id,
            data=QuestionnaireInput(name=core.name, default_tiers=["low", "medium"]),
        )
        after = {
            q.name: q.default_tiers
            for q in await questionnaire_service.list_questionnaires(session, tenant_id=tenant.id)
        }
        assert after[core.name] == ["medium", "low"]
        assert after[lite.name] == []

        default = next(q for q in rows if q.purpose == "tiering")
        with pytest.raises(InvalidInput, match="default"):
            await questionnaire_service.set_status(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=default.id,
                status="archived",
            )


# -- tiering ------------------------------------------------------------------


async def _tiering_questionnaire(tenant: Tenant) -> QuestionnaireView:
    async with session_scope(tenant.id) as session:
        view = await questionnaire_service.create_questionnaire(
            session, tenant_id=tenant.id, actor=tenant.actor, purpose="tiering", name="Intake"
        )
        for data in (
            QuestionInput(
                prompt="What data?",
                answer_type="multi_choice",
                weight=10,
                options=[
                    {"key": "none", "label": "None", "score": 0},
                    {"key": "pii", "label": "Personal data", "score": 4},
                    {"key": "health", "label": "Health data", "score": 1, "min_tier": "high"},
                ],
            ),
            QuestionInput(
                prompt="How critical?",
                weight=10,
                options=_choice(("low", "Barely", 0), ("mid", "Somewhat", 2), ("top", "Very", 4)),
            ),
            QuestionInput(prompt="Notes", answer_type="paragraph", required=False),
        ):
            view = await questionnaire_service.add_question(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=view.id,
                data=data,
            )
    return view


async def test_tiering_scores_the_tenants_own_questions_with_floors(tenant: Tenant) -> None:
    questionnaire = await _tiering_questionnaire(tenant)
    data, critical, _notes = questionnaire.questions
    vendor_id, engagement_id = await _vendor(tenant)

    async with session_scope(tenant.id) as session:
        with pytest.raises(InvalidInput, match="required"):
            await vendor_service.tier_engagement(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                vendor_id=vendor_id,
                engagement_id=engagement_id,
                answers=QuestionnaireTieringInput(
                    questionnaire_id=questionnaire.id,
                    answers={str(data.id): {"value": ["health"]}},
                ),
            )

    async with session_scope(tenant.id) as session:
        detail = await vendor_service.tier_engagement(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            answers=QuestionnaireTieringInput(
                questionnaire_id=questionnaire.id,
                answers={
                    str(data.id): {"value": ["health"]},
                    str(critical.id): {"value": "low"},
                },
            ),
        )
    tiering = detail.tierings[0]
    # 1 of 4 points on the first, 0 of 4 on the second: a low score.
    assert tiering.score == 12.5
    assert tiering.computed_tier == "high", "health data floors the tier at high"
    assert tiering.floor_tier == "high"
    assert tiering.factors == []
    assert [line.answer_labels for line in tiering.questions[:2]] == [["Health data"], ["Barely"]]

    # Rewording the questionnaire afterwards does not rewrite the run.
    async with session_scope(tenant.id) as session:
        await questionnaire_service.update_question(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            questionnaire_id=questionnaire.id,
            question_id=data.id,
            data=QuestionInput(
                prompt="Reworded",
                answer_type="multi_choice",
                options=[
                    {"key": "none", "label": "None", "score": 0},
                    {"key": "x", "label": "X", "score": 1},
                ],
            ),
        )
        again = await vendor_service.get_vendor(session, tenant_id=tenant.id, vendor_id=vendor_id)
    assert again.tierings[0].questions[0].prompt == "What data?"
    assert again.tierings[0].computed_tier == "high"


# -- due diligence through the portal ------------------------------------------


async def test_a_typed_questionnaire_is_answered_scored_and_flagged_end_to_end(
    tenant: Tenant,
) -> None:
    vendor_id, engagement_id = await _vendor(tenant)
    async with session_scope(tenant.id) as session:
        tiering = await questionnaire_service.list_questionnaires(
            session, tenant_id=tenant.id, purpose="tiering"
        )
        standard = await questionnaire_service.get_questionnaire(
            session, tenant_id=tenant.id, questionnaire_id=tiering[0].id
        )
        await vendor_service.tier_engagement(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            answers=QuestionnaireTieringInput(
                answers={str(q.id): {"value": q.options[2]["key"]} for q in standard.questions}
            ),
        )

        view = await questionnaire_service.create_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            purpose="due_diligence",
            name="Custom",
        )
        for data in (
            QuestionInput(
                prompt="Do you encrypt data at rest?",
                domain="data_protection_privacy",
                critical=True,
                evidence="required",
                evidence_on=["yes"],
                options=[
                    {"key": "yes", "label": "Yes", "score": 100},
                    {"key": "no", "label": "No", "score": 0, "flag": True},
                ],
            ),
            QuestionInput(
                prompt="Which certifications?",
                answer_type="multi_choice",
                options=[
                    {"key": "soc2", "label": "SOC 2", "score": 100},
                    {"key": "none", "label": "None", "score": 0, "flag": True},
                ],
            ),
            QuestionInput(prompt="Employees", answer_type="number"),
            QuestionInput(prompt="Last pentest", answer_type="date"),
            QuestionInput(prompt="Anything else?", answer_type="paragraph", required=False),
        ):
            view = await questionnaire_service.add_question(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                questionnaire_id=view.id,
                data=data,
            )
        certs = view.questions[1]
        view = await questionnaire_service.add_question(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            questionnaire_id=view.id,
            data=QuestionInput(
                prompt="Upload the SOC 2 report",
                answer_type="file",
                condition={"question_id": str(certs.id), "option_keys": ["soc2"]},
            ),
        )
        encrypt, certs, employees, pentest, _notes, report = view.questions
        issued = await vendor_service.issue_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            questionnaire_id=view.id,
        )
    token = issued.portal_url.rsplit("/", 1)[-1]

    opened = await vendor_portal_service.open_portal(token, client_host=HOST)
    # The follow-up is not asked yet, and the vendor sees no scores or gap flags.
    assert opened.question_count == 5
    assert not any(
        hasattr(o, "score") or hasattr(o, "flag") for q in opened.questions for o in q.options
    )

    save = vendor_portal_service.save_answer
    await save(token, client_host=HOST, question_id=encrypt.id, value="yes")
    await save(token, client_host=HOST, question_id=certs.id, value=["soc2"])
    await save(token, client_host=HOST, question_id=employees.id, value="240")
    await save(token, client_host=HOST, question_id=pentest.id, value="2026-05-01")
    with pytest.raises(InvalidInput, match="date"):
        await save(token, client_host=HOST, question_id=pentest.id, value="last spring")

    with pytest.raises(InvalidInput, match=r"(need|needs) an answer"):
        await vendor_portal_service.submit(token, client_host=HOST)
    await vendor_portal_service.attach_evidence(
        token, client_host=HOST, question_id=report.id, filename="soc2.pdf", data=_PDF
    )
    with pytest.raises(InvalidInput, match="supporting document"):
        await vendor_portal_service.submit(token, client_host=HOST)
    await vendor_portal_service.attach_evidence(
        token, client_host=HOST, question_id=encrypt.id, filename="kms.pdf", data=_PDF
    )
    submitted = await vendor_portal_service.submit(token, client_host=HOST)
    assert submitted.status == "scored"

    async with session_scope(tenant.id) as session:
        scored = await vendor_service.get_assessment(
            session, tenant_id=tenant.id, assessment_id=issued.assessment_id
        )
    assert scored.findings == []
    by_id = {r.question_id: r for r in scored.responses}
    assert by_id[employees.id].value == 240
    assert by_id[certs.id].answer_labels == ["SOC 2"]
    assert by_id[report.id].visible is True

    # The same review with a gap: a flagged pick on a critical question.
    async with session_scope(tenant.id) as session:
        rows = await vendor_service.answers_with_questions(
            session, tenant_id=tenant.id, assessment_id=issued.assessment_id
        )
        row = next(r for r, q in rows if q.id == encrypt.id)
        row.answer, row.answer_value = "no", {"value": "no"}
        await session.flush()
        rescored = await vendor_service.score_assessment(
            session, tenant_id=tenant.id, actor=tenant.actor, assessment_id=issued.assessment_id
        )
    assert [f.severity for f in rescored.findings] == ["critical"]
    assert rescored.findings[0].question_id == encrypt.id
    assert rescored.residual_score is not None
    assert rescored.residual_score >= 50.0


async def test_one_tenant_cannot_read_or_use_anothers_questionnaire(tenant: Tenant) -> None:
    other = Tenant(await signup_workspace(company="Echo Bank", email="founder@echo.example"))
    async with session_scope(tenant.id) as session:
        mine = await questionnaire_service.list_questionnaires(session, tenant_id=tenant.id)
    async with session_scope(other.id) as session:
        with pytest.raises(NotFound):
            await questionnaire_service.get_questionnaire(
                session, tenant_id=other.id, questionnaire_id=mine[0].id
            )
        theirs = await questionnaire_service.list_questionnaires(session, tenant_id=other.id)
    assert not {q.id for q in mine} & {q.id for q in theirs}


async def test_resending_another_questionnaire_replaces_only_an_unanswered_review(
    tenant: Tenant,
) -> None:
    """Picking a different questionnaire on resend swaps it while nothing is
    answered, and is refused once the vendor has started: their work would go."""
    vendor_id, engagement_id = await _vendor(tenant)
    async with session_scope(tenant.id) as session:
        rows = await questionnaire_service.list_questionnaires(session, tenant_id=tenant.id)
        standard = await questionnaire_service.get_questionnaire(
            session,
            tenant_id=tenant.id,
            questionnaire_id=next(q.id for q in rows if q.purpose == "tiering"),
        )
        await vendor_service.tier_engagement(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            answers=QuestionnaireTieringInput(
                answers={str(q.id): {"value": q.options[0]["key"]} for q in standard.questions}
            ),
        )
        lite = next(q for q in rows if q.name == "Security review, lite")
        profile = next(q for q in rows if q.name == "Vendor profile")
        first = await vendor_service.issue_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            questionnaire_id=lite.id,
        )
    async with session_scope(tenant.id) as session:
        swapped = await vendor_service.issue_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            questionnaire_id=profile.id,
        )
    assert swapped.assessment_id != first.assessment_id
    with pytest.raises(NotFound):
        await vendor_portal_service.open_portal(
            first.portal_url.rsplit("/", 1)[-1], client_host=HOST
        )
    async with session_scope(tenant.id) as session:
        retired = await vendor_service.get_assessment(
            session, tenant_id=tenant.id, assessment_id=first.assessment_id
        )
    assert retired.status == "expired"

    token = swapped.portal_url.rsplit("/", 1)[-1]
    opened = await vendor_portal_service.open_portal(token, client_host=HOST)
    await vendor_portal_service.save_answer(
        token, client_host=HOST, question_id=opened.questions[0].id, value="Northwind Ltd"
    )
    async with session_scope(tenant.id) as session:
        with pytest.raises(Conflict, match="started answering"):
            await vendor_service.issue_questionnaire(
                session,
                tenant_id=tenant.id,
                actor=tenant.actor,
                vendor_id=vendor_id,
                engagement_id=engagement_id,
                questionnaire_id=lite.id,
            )
    async with session_scope(tenant.id) as session:
        resent = await vendor_service.issue_questionnaire(
            session,
            tenant_id=tenant.id,
            actor=tenant.actor,
            vendor_id=vendor_id,
            engagement_id=engagement_id,
            questionnaire_id=profile.id,
        )
    assert resent.assessment_id == swapped.assessment_id
