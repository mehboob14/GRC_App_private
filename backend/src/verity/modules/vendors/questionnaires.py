"""Questionnaires a tenant builds, for tiering and for due diligence.

**Two questionnaires, easily confused.** A *tiering* questionnaire is internal: the
business owner answers it about how we use a vendor (what data, what access, how
much depends on it) and the answers set the tier. A *due diligence* questionnaire
goes to the vendor through the portal: they answer it about their own controls,
with evidence, and the answers set the residual score and raise findings. The
builder is the same for both, so the table and this service are too, and
``purpose`` says which one a row is.

**The library is copied, never answered.** Shipped questions live on the global
content plane (``questionnaire_templates``); a tenant starts a questionnaire from
a template or picks questions into one, and from then on edits its own copy.

**Editing never reaches back.** A tiering run and a dispatched review each keep a
snapshot of the questions as they were answered (see ``snapshot``), so a
questionnaire can be reworded or pruned the day after it was used without
changing what any past tier or score meant.
"""

from __future__ import annotations

import math
import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any, Final

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, Membership, System, audit_service
from verity.modules.vendors.models import (
    CHOICE_TYPES,
    EVIDENCE_RULES,
    QUESTION_TYPES,
    QUESTIONNAIRE_PURPOSES,
    RISK_DOMAIN_LABELS,
    RISK_DOMAINS,
    TIERS,
    QuestionnaireQuestion,
    QuestionnaireTemplate,
    VendorAssessmentResponse,
    VendorQuestionnaire,
    VendorQuestionnaireQuestion,
)
from verity.modules.vendors.scoring import ChoiceOption, QuestionRule, picked_keys, visible_ids
from verity.shared.ids import uuid7

_GONE: Final = "This questionnaire no longer exists."
_QUESTION_GONE: Final = "This question is no longer part of the questionnaire."

_KEY: Final = re.compile(r"^[a-z0-9_]{1,40}$")
_MIN_OPTIONS: Final = 2
_MAX_OPTIONS: Final = 50
_MAX_QUESTIONS: Final = 300
_MAX_PROMPT: Final = 1000
_MAX_SECTION: Final = 80
_MAX_LABEL: Final = 200
_MAX_NAME: Final = 200
_MAX_SCORE: Final = 100.0
"""The ceiling for an option's score and a question's weight alike."""

# The bank's four answers as builder options. Scores follow V7 (yes 1.0, partial
# 0.5, no 0.0, na excluded), a "no" is the gap that raises a finding, and "not
# applicable" needs its reason, exactly as the bank's rows always behaved.
STANDARD_OPTIONS: Final[tuple[dict[str, Any], ...]] = (
    {"key": "yes", "label": "Yes", "score": 100},
    {"key": "partial", "label": "Partially", "score": 50},
    {"key": "no", "label": "No", "score": 0, "flag": True},
    {
        "key": "na",
        "label": "Not applicable",
        "score": 0,
        "not_applicable": True,
        "comment_required": True,
    },
)
# A yes or a partial claims the control, so it owes the document (portal rule).
_CLAIMS: Final[tuple[str, ...]] = ("yes", "partial")

# Starting points per library template: which scope levels a preset copies.
_PRESETS: Final[dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]]] = {
    "tiering": (
        ("standard", "Standard", ("lite",)),
        ("extended", "Extended", ("lite", "core")),
    ),
    "due_diligence": (
        ("lite", "Lite", ("lite",)),
        ("core", "Core", ("lite", "core")),
        ("full", "Full", ("lite", "core", "detail")),
    ),
}

# What a tenant with no questionnaires is given, so tiering and sending work on
# day one. Mirrors BUNDLE_BY_TIER: the tier still right-sizes the review.
_DEFAULTS: Final[dict[str, tuple[dict[str, Any], ...]]] = {
    "tiering": (
        {
            "library": "verity-inherent-risk",
            "preset": "standard",
            "name": "Inherent risk",
            "description": "Data, access, criticality, regulation and reliance. Sets the tier.",
            "is_default": True,
        },
    ),
    "due_diligence": (
        {
            "library": "verity-core",
            "preset": "lite",
            "name": "Security review, lite",
            "description": "The essential controls, for low risk vendors.",
            "default_tiers": ["low"],
        },
        {
            "library": "verity-core",
            "preset": "core",
            "name": "Security review, core",
            "description": "Broader controls, for medium risk vendors.",
            "default_tiers": ["medium"],
        },
        {
            "library": "verity-core",
            "preset": "full",
            "name": "Security review, full",
            "description": "Every control area, for high and critical vendors.",
            "default_tiers": ["high", "critical"],
        },
        {
            "library": "verity-vendor-profile",
            "preset": "lite",
            "name": "Vendor profile",
            "description": "Company details, attestations and the reports behind them.",
        },
    ),
}


# -- views --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionView:
    id: uuid.UUID
    position: int
    section: str
    prompt: str
    help_text: str | None
    answer_type: str
    options: list[dict[str, Any]]
    required: bool
    evidence: str
    evidence_on: list[str]
    weight: float
    domain: str | None
    domain_label: str | None
    critical: bool
    blocking: bool
    condition: dict[str, Any]
    framework_refs: list[str]
    library_code: str | None


@dataclass(frozen=True, slots=True)
class QuestionnaireSummaryView:
    id: uuid.UUID
    purpose: str
    name: str
    description: str | None
    status: str
    is_default: bool
    default_tiers: list[str]
    question_count: int
    section_count: int
    library_code: str | None
    updated_at: datetime
    updated_by_name: str | None


@dataclass(frozen=True, slots=True)
class QuestionnaireView(QuestionnaireSummaryView):
    tier_thresholds: dict[str, float]
    questions: list[QuestionView]


@dataclass(frozen=True, slots=True)
class LibraryQuestionView:
    id: uuid.UUID
    code: str
    section: str
    prompt: str
    help_text: str | None
    answer_type: str
    options: list[dict[str, Any]]
    required: bool
    evidence: str
    weight: float
    domain: str | None
    domain_label: str | None
    critical: bool
    blocking: bool
    scope_level: str
    framework_refs: list[str]
    condition_code: str | None


@dataclass(frozen=True, slots=True)
class LibraryPresetView:
    key: str
    label: str
    question_count: int


@dataclass(frozen=True, slots=True)
class LibraryTemplateView:
    code: str
    name: str
    description: str | None
    purpose: str
    version: str
    presets: list[LibraryPresetView]
    questions: list[LibraryQuestionView]


# -- inputs -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionInput:
    prompt: str
    answer_type: str = "single_choice"
    section: str = "General"
    help_text: str | None = None
    options: Sequence[Mapping[str, Any]] = ()
    required: bool = True
    evidence: str = "none"
    evidence_on: Sequence[str] = ()
    weight: float = 1.0
    domain: str | None = None
    critical: bool = False
    blocking: bool = False
    condition: Mapping[str, Any] | None = None
    framework_refs: Sequence[str] = ()
    library_code: str | None = None


@dataclass(frozen=True, slots=True)
class QuestionnaireInput:
    name: str
    description: str | None = None
    default_tiers: Sequence[str] = ()
    tier_thresholds: Mapping[str, float] = field(default_factory=dict)
    is_default: bool = False


# -- a question as a review or a tiering run asked it --------------------------


@dataclass(frozen=True, slots=True)
class AskedQuestion:
    """One question as it was put to somebody, from the bank or from a snapshot.

    The rest of the module reads this and never the two sources directly, so the
    portal, scoring, findings and the reviewer's screen have one shape to handle.
    """

    id: uuid.UUID
    code: str
    prompt: str
    section: str
    domain: str
    help_text: str | None
    answer_type: str
    options: tuple[ChoiceOption, ...]
    required: bool
    evidence: str
    evidence_on: tuple[str, ...]
    weight: float
    critical: bool
    blocking: bool
    condition_question: str | None
    condition_options: tuple[str, ...]
    framework_refs: tuple[str, ...]
    scope_level: str
    from_bank: bool
    position: int = 0

    @property
    def key(self) -> str:
        return str(self.id)

    @property
    def scored(self) -> bool:
        """Only a choice with some option worth more than nothing moves a score."""
        return self.answer_type in CHOICE_TYPES and any(
            o.score > 0 for o in self.options if not o.not_applicable
        )

    def rule(self) -> QuestionRule:
        return QuestionRule(
            id=self.key,
            prompt=self.prompt,
            section=self.section,
            answer_type=self.answer_type,
            options=self.options,
            weight=self.weight,
            required=self.required,
            condition_question=self.condition_question,
            condition_options=self.condition_options,
        )

    def option(self, key: str) -> ChoiceOption | None:
        return next((o for o in self.options if o.key == key), None)


def _options(raw: Iterable[Mapping[str, Any]]) -> tuple[ChoiceOption, ...]:
    return tuple(
        ChoiceOption(
            key=str(o["key"]),
            label=str(o.get("label", o["key"])),
            score=float(o.get("score", 0) or 0),
            flag=bool(o.get("flag", False)),
            not_applicable=bool(o.get("not_applicable", False)),
            comment_required=bool(o.get("comment_required", False)),
            min_tier=o.get("min_tier") or None,
        )
        for o in raw
    )


def asked_from_bank(question: QuestionnaireQuestion) -> AskedQuestion:
    """A bank row, as it has always been answered: yes, partially, no or n/a."""
    domain = question.domain or "information_security"
    return AskedQuestion(
        id=question.id,
        code=question.code,
        prompt=question.body,
        section=RISK_DOMAIN_LABELS[domain],
        domain=domain,
        help_text=question.help_text,
        answer_type="single_choice",
        options=_options(STANDARD_OPTIONS),
        required=True,
        evidence="required" if question.evidence_required else "none",
        evidence_on=_CLAIMS,
        weight=question.weight,
        critical=question.critical_control,
        blocking=question.non_negotiable,
        condition_question=None,
        condition_options=(),
        framework_refs=tuple(question.framework_refs or ()),
        scope_level=question.scope_level,
        from_bank=True,
        position=question.position,
    )


def asked_from_snapshot(data: Mapping[str, Any]) -> AskedQuestion:
    """A question copied onto a response row or a tiering run when it was asked."""
    condition = data.get("condition") or {}
    domain = data.get("domain") or "information_security"
    return AskedQuestion(
        id=uuid.UUID(str(data["id"])),
        code=str(data.get("library_code") or str(data["id"])[:8]),
        prompt=str(data["prompt"]),
        section=str(data.get("section") or "General"),
        domain=domain,
        help_text=data.get("help_text"),
        answer_type=str(data["answer_type"]),
        options=_options(data.get("options") or ()),
        required=bool(data.get("required", True)),
        evidence=str(data.get("evidence") or "none"),
        evidence_on=tuple(data.get("evidence_on") or ()),
        weight=float(data.get("weight", 1.0)),
        critical=bool(data.get("critical", False)),
        blocking=bool(data.get("blocking", False)),
        condition_question=str(condition["question_id"]) if condition.get("question_id") else None,
        condition_options=tuple(condition.get("option_keys") or ()),
        framework_refs=tuple(data.get("framework_refs") or ()),
        scope_level="core",
        from_bank=False,
        position=int(data.get("position", 0)),
    )


_MAX_TEXT_ANSWER: Final = 8000


def normalize_answer(  # noqa: PLR0912 -- one branch per answer type
    question: AskedQuestion, value: object
) -> object | None:
    """An answer in the shape it is stored in, or a refusal naming what is wrong.

    ``None`` means cleared. Used by the tiering dialog and the vendor portal
    alike, so a value the portal accepts is a value scoring can read.
    """
    if value is None or value in ("", []):
        return None
    kind = question.answer_type
    if kind == "single_choice":
        if not isinstance(value, str) or question.option(value) is None:
            raise InvalidInput("Pick one of the options.", detail=f"{question.key}: {value!r}")
        return value
    if kind == "multi_choice":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise InvalidInput("Pick from the options.", detail=f"{question.key}: {value!r}")
        unknown = set(value) - {o.key for o in question.options}
        if unknown:
            raise InvalidInput("Pick from the options.", detail=f"{question.key}: {unknown}")
        return [o.key for o in question.options if o.key in set(value)]
    if kind in ("text", "paragraph"):
        if not isinstance(value, str):
            raise InvalidInput("Type an answer.", detail=f"{question.key}: not text")
        text_value = value.strip()
        if len(text_value) > _MAX_TEXT_ANSWER:
            raise InvalidInput(
                f"Keep the answer under {_MAX_TEXT_ANSWER:,} characters.",
                detail=f"{question.key}: text too long",
            )
        return text_value or None
    if kind == "number":
        try:
            number = float(value) if not isinstance(value, bool) else math.nan  # type: ignore[arg-type]
        except (TypeError, ValueError):
            number = math.nan
        if not math.isfinite(number):
            raise InvalidInput("Enter a number.", detail=f"{question.key}: {value!r}")
        return int(number) if number.is_integer() else number
    if kind == "date":
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError as exc:
            raise InvalidInput("Enter a date.", detail=f"{question.key}: {value!r}") from exc
    raise InvalidInput(
        "Upload a document to answer this question.", detail=f"{question.key}: file question"
    )


def picked_options(question: AskedQuestion, value: object) -> list[ChoiceOption]:
    keys = set(picked_keys(value))
    return [o for o in question.options if o.key in keys]


def response_value(response: VendorAssessmentResponse, question: AskedQuestion) -> object:
    """What was answered, in the question's own shape."""
    if question.from_bank:
        return response.answer
    return (response.answer_value or {}).get("value")


def is_answered(response: VendorAssessmentResponse, question: AskedQuestion) -> bool:
    if question.from_bank:
        return bool(response.answer)
    if question.answer_type == "file":
        return response.evidence_id is not None
    return response.answered_at is not None


def owes_evidence(
    response: VendorAssessmentResponse, question: AskedQuestion, *, visible: bool = True
) -> bool:
    """A document this answer still needs before the questionnaire can go back."""
    if not visible or question.answer_type == "file" or question.evidence != "required":
        return False
    if response.evidence_id is not None or not is_answered(response, question):
        return False
    if not question.evidence_on:
        return True
    return bool(set(picked_keys(response_value(response, question))) & set(question.evidence_on))


def answer_labels(response: VendorAssessmentResponse, question: AskedQuestion) -> list[str]:
    """The answer as a person reads it: option labels, or the value itself."""
    if not is_answered(response, question):
        return []
    value = response_value(response, question)
    if question.answer_type in CHOICE_TYPES:
        return [o.label for o in question.options if o.key in set(picked_keys(value))]
    if question.answer_type == "file":
        return ["Document attached"]
    return [str(value)] if value not in (None, "") else []


def visible_keys(
    pairs: Sequence[tuple[VendorAssessmentResponse, AskedQuestion]],
) -> set[str]:
    """The questions a review actually asks, given the answers so far."""
    answers = {q.key: response_value(r, q) for r, q in pairs if is_answered(r, q)}
    return visible_ids([q.rule() for _, q in pairs], answers)


# -- the service --------------------------------------------------------------


class QuestionnaireService:
    """Tenant questionnaires: the library, the builder, and the snapshots."""

    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- reads -----------------------------------------------------------------

    async def list_questionnaires(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        purpose: str | None = None,
        include_archived: bool = False,
    ) -> list[QuestionnaireSummaryView]:
        await self.ensure_defaults(session, tenant_id=tenant_id)
        stmt = select(VendorQuestionnaire).where(VendorQuestionnaire.tenant_id == tenant_id)
        if purpose:
            self._check_purpose(purpose)
            stmt = stmt.where(VendorQuestionnaire.purpose == purpose)
        if not include_archived:
            stmt = stmt.where(VendorQuestionnaire.status == "active")
        rows = list(
            (await session.execute(stmt.order_by(VendorQuestionnaire.created_at))).scalars()
        )
        counts = await self._counts(session, tenant_id, [r.id for r in rows])
        names = await self._member_names(session, tenant_id)
        return [self._summary(r, counts.get(r.id, (0, 0)), names) for r in rows]

    async def get_questionnaire(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, questionnaire_id: uuid.UUID
    ) -> QuestionnaireView:
        row = await self._load(session, tenant_id, questionnaire_id)
        questions = await self._questions(session, tenant_id, row.id)
        names = await self._member_names(session, tenant_id)
        return self._view(row, questions, names)

    async def library(
        self, session: AsyncSession, *, purpose: str | None = None
    ) -> list[LibraryTemplateView]:
        stmt = select(QuestionnaireTemplate).order_by(QuestionnaireTemplate.name)
        if purpose:
            self._check_purpose(purpose)
            stmt = stmt.where(QuestionnaireTemplate.purpose == purpose)
        templates = list((await session.execute(stmt)).scalars())
        views: list[LibraryTemplateView] = []
        for template in templates:
            questions = await self._library_questions(session, template.id)
            by_id = {q.id: q for q in questions}
            views.append(
                LibraryTemplateView(
                    code=template.code,
                    name=template.name,
                    description=template.description,
                    purpose=template.purpose,
                    version=template.version,
                    presets=[
                        LibraryPresetView(
                            key=key,
                            label=label,
                            question_count=sum(1 for q in questions if q.scope_level in levels),
                        )
                        for key, label, levels in self._presets(template, questions)
                    ],
                    questions=[
                        self._library_view(
                            template,
                            q,
                            by_id.get(q.parent_question_id) if q.parent_question_id else None,
                        )
                        for q in questions
                    ],
                )
            )
        return views

    # -- creating --------------------------------------------------------------

    async def create_questionnaire(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        purpose: str,
        name: str,
        description: str | None = None,
        library_code: str | None = None,
        preset: str | None = None,
    ) -> QuestionnaireView:
        """Start a questionnaire, blank or from a library template's preset."""
        self._check_purpose(purpose)
        # Defaults first: they are given only to a workspace that has never had a
        # questionnaire of this purpose, which this one is about to stop being.
        await self.ensure_defaults(session, tenant_id=tenant_id)
        row = VendorQuestionnaire(
            id=uuid7(),
            tenant_id=tenant_id,
            purpose=purpose,
            name=self._name(name),
            description=self._text(description, 2000),
            status="active",
            library_code=library_code,
            created_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            updated_by_membership_id=actor.id if isinstance(actor, Membership) else None,
        )
        session.add(row)
        await session.flush([row])

        copied = 0
        if library_code:
            template, questions = await self._library_template(session, library_code, purpose)
            levels = next(
                (lv for key, _, lv in self._presets(template, questions) if key == preset),
                None,
            )
            if preset and levels is None:
                raise InvalidInput(
                    "That starting point is not available for this template.",
                    detail=f"preset {preset!r} not on {library_code}",
                )
            chosen = [q for q in questions if levels is None or q.scope_level in levels]
            copied = await self._copy_library(session, tenant_id, row, template, chosen)

        if purpose == "tiering":
            existing_default = await self._default_tiering_row(session, tenant_id)
            if existing_default is None:
                row.is_default = True

        await self._audit.record(
            session,
            action="create",
            object_type="vendor_questionnaire",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "purpose": purpose,
                "name": row.name,
                "library_code": library_code,
                "preset": preset,
                "question_count": copied,
            },
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    async def duplicate_questionnaire(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
    ) -> QuestionnaireView:
        source = await self._load(session, tenant_id, questionnaire_id)
        questions = await self._questions(session, tenant_id, source.id)
        copy = VendorQuestionnaire(
            id=uuid7(),
            tenant_id=tenant_id,
            purpose=source.purpose,
            name=f"{source.name} (copy)"[:200],
            description=source.description,
            status="active",
            tier_thresholds=dict(source.tier_thresholds or {}),
            library_code=source.library_code,
            created_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            updated_by_membership_id=actor.id if isinstance(actor, Membership) else None,
        )
        session.add(copy)
        await session.flush([copy])
        # New ids, so conditions are rewritten to point at the copies.
        new_ids = {q.id: uuid7() for q in questions}
        for q in questions:
            condition = dict(q.condition or {})
            if condition.get("question_id"):
                old = uuid.UUID(str(condition["question_id"]))
                condition["question_id"] = str(new_ids[old]) if old in new_ids else None
                if not condition["question_id"]:
                    condition = {}
            session.add(
                VendorQuestionnaireQuestion(
                    id=new_ids[q.id],
                    tenant_id=tenant_id,
                    questionnaire_id=copy.id,
                    position=q.position,
                    section=q.section,
                    prompt=q.prompt,
                    help_text=q.help_text,
                    answer_type=q.answer_type,
                    options=[dict(o) for o in q.options],
                    required=q.required,
                    evidence=q.evidence,
                    evidence_on=list(q.evidence_on),
                    weight=q.weight,
                    domain=q.domain,
                    critical=q.critical,
                    blocking=q.blocking,
                    condition=condition,
                    framework_refs=list(q.framework_refs),
                    library_code=q.library_code,
                )
            )
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_questionnaire",
            object_id=copy.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"duplicated_from": str(source.id), "question_count": len(questions)},
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=copy.id)

    # -- settings --------------------------------------------------------------

    async def update_questionnaire(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        data: QuestionnaireInput,
    ) -> QuestionnaireView:
        row = await self._load(session, tenant_id, questionnaire_id)
        before = self._settings_snapshot(row)
        row.name = self._name(data.name)
        row.description = self._text(data.description, 2000)

        if row.purpose == "tiering":
            row.tier_thresholds = self._thresholds(data.tier_thresholds)
            if data.is_default and not row.is_default:
                if row.status != "active":
                    raise InvalidInput(
                        "Restore this questionnaire before making it the default.",
                        detail="archived questionnaire cannot be the tiering default",
                    )
                current = await self._default_tiering_row(session, tenant_id)
                if current is not None:
                    current.is_default = False
                    await session.flush([current])
                row.is_default = True
        else:
            tiers = self._tiers(data.default_tiers)
            if tiers and row.status != "active":
                raise InvalidInput(
                    "Restore this questionnaire before using it as a tier default.",
                    detail="archived questionnaire cannot hold default tiers",
                )
            # A tier has one default. Taking it here takes it from wherever it was.
            if tiers:
                others = (
                    await session.execute(
                        select(VendorQuestionnaire)
                        .where(VendorQuestionnaire.tenant_id == tenant_id)
                        .where(VendorQuestionnaire.purpose == "due_diligence")
                        .where(VendorQuestionnaire.id != row.id)
                    )
                ).scalars()
                for other in others:
                    remaining = [t for t in other.default_tiers or [] if t not in tiers]
                    if remaining != list(other.default_tiers or []):
                        other.default_tiers = remaining
            row.default_tiers = tiers

        row.updated_by_membership_id = actor.id if isinstance(actor, Membership) else None
        after = self._settings_snapshot(row)
        if before != after:
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_questionnaire",
                object_id=row.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    async def set_status(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        status: str,
    ) -> QuestionnaireView:
        """Archive or restore. Never delete: runs and reviews point at it (rule 6)."""
        row = await self._load(session, tenant_id, questionnaire_id)
        if status not in ("active", "archived"):
            raise InvalidInput("Pick active or archived.", detail=f"status={status!r}")
        if status == row.status:
            return await self.get_questionnaire(
                session, tenant_id=tenant_id, questionnaire_id=row.id
            )
        before = self._settings_snapshot(row)
        if status == "archived" and row.is_default:
            raise InvalidInput(
                "Make another tiering questionnaire the default before archiving this one.",
                detail="cannot archive the tiering default",
            )
        row.status = status
        if status == "archived":
            row.default_tiers = []
        row.updated_by_membership_id = actor.id if isinstance(actor, Membership) else None
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_questionnaire",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=self._settings_snapshot(row),
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    # -- questions -------------------------------------------------------------

    async def add_question(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        data: QuestionInput,
        after_question_id: uuid.UUID | None = None,
    ) -> QuestionnaireView:
        row = await self._load(session, tenant_id, questionnaire_id)
        questions = await self._questions(session, tenant_id, row.id)
        if len(questions) >= _MAX_QUESTIONS:
            raise InvalidInput(
                f"A questionnaire holds at most {_MAX_QUESTIONS} questions.",
                detail="question limit reached",
            )
        if after_question_id is not None:
            index = next(
                (i + 1 for i, q in enumerate(questions) if q.id == after_question_id),
                len(questions),
            )
        else:
            index = self._slot(questions, data)
        question_id = uuid7()
        earlier = questions[:index]
        clean = self._validate(row.purpose, data, earlier=earlier, own_id=question_id)
        question = VendorQuestionnaireQuestion(
            id=question_id, tenant_id=tenant_id, questionnaire_id=row.id, position=index, **clean
        )
        session.add(question)
        await session.flush([question])
        questions.insert(index, question)
        self._renumber(questions)
        self._touch(row, actor)
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_questionnaire_question",
            object_id=question.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"questionnaire_id": str(row.id), **self._question_snapshot(question)},
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    async def import_questions(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        library_question_ids: Sequence[uuid.UUID],
    ) -> QuestionnaireView:
        """Copy chosen library questions onto the end, bringing any parent they branch from."""
        row = await self._load(session, tenant_id, questionnaire_id)
        if not library_question_ids:
            raise InvalidInput("Pick at least one question to add.", detail="empty import")
        wanted = list(
            (
                await session.execute(
                    select(QuestionnaireQuestion, QuestionnaireTemplate)
                    .join(
                        QuestionnaireTemplate,
                        QuestionnaireTemplate.id == QuestionnaireQuestion.template_id,
                    )
                    .where(QuestionnaireQuestion.id.in_(list(library_question_ids)))
                )
            ).all()
        )
        if not wanted:
            raise NotFound(
                "Those library questions are not available.", detail="no library questions found"
            )
        if any(template.purpose != row.purpose for _, template in wanted):
            raise InvalidInput(
                "Those questions belong to a different kind of questionnaire.",
                detail="library purpose mismatch",
            )
        existing = await self._questions(session, tenant_id, row.id)
        if len(existing) + len(wanted) > _MAX_QUESTIONS:
            raise InvalidInput(
                f"A questionnaire holds at most {_MAX_QUESTIONS} questions.",
                detail="question limit reached",
            )

        copied = 0
        for template in {t.id: t for _, t in wanted}.values():
            questions = await self._library_questions(session, template.id)
            by_id = {q.id: q for q in questions}
            chosen_ids = {q.id for q, t in wanted if t.id == template.id}
            # A branch cannot stand without the question it branches from.
            for q, t in wanted:
                if t.id == template.id and q.parent_question_id in by_id:
                    chosen_ids.add(q.parent_question_id)
            present = {q.library_code for q in existing if q.library_code}
            chosen = [q for q in questions if q.id in chosen_ids and q.code not in present]
            copied += await self._copy_library(session, tenant_id, row, template, chosen)

        self._touch(row, actor)
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_questionnaire",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"question_count": len(existing)},
            after={"question_count": len(existing) + copied, "imported": copied},
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    async def update_question(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        question_id: uuid.UUID,
        data: QuestionInput,
    ) -> QuestionnaireView:
        row = await self._load(session, tenant_id, questionnaire_id)
        questions = await self._questions(session, tenant_id, row.id)
        index = next((i for i, q in enumerate(questions) if q.id == question_id), None)
        if index is None:
            raise NotFound(_QUESTION_GONE, detail=f"question {question_id} not on {row.id}")
        question = questions[index]
        before = self._question_snapshot(question)
        moved_from = question.section
        clean = self._validate(row.purpose, data, earlier=questions[:index], own_id=question.id)
        for key, value in clean.items():
            setattr(question, key, value)
        self._prune_dependents(questions, question)
        if question.section != moved_from:
            others = [q for q in questions if q.id != question.id]
            if any(q.section == question.section for q in others):
                slot = self._slot(others, question)
                candidate = [*others[:slot], question, *others[slot:]]
                # Kept where it is when moving would put it before a question it
                # depends on, or after one that depends on it.
                if self._order_ok(candidate):
                    questions = candidate
                    self._renumber(questions)
        self._touch(row, actor)
        after = self._question_snapshot(question)
        if before != after:
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_questionnaire_question",
                object_id=question.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    async def delete_question(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> QuestionnaireView:
        """Remove a question from the questionnaire.

        A question here is the questionnaire's draft wording, not a compliance
        record: every run and review that asked it holds its own copy, so removing
        it here changes only what is asked next time. The audit row keeps the text.
        """
        row = await self._load(session, tenant_id, questionnaire_id)
        questions = await self._questions(session, tenant_id, row.id)
        question = next((q for q in questions if q.id == question_id), None)
        if question is None:
            raise NotFound(_QUESTION_GONE, detail=f"question {question_id} not on {row.id}")
        before = self._question_snapshot(question)
        questions.remove(question)
        for other in questions:
            if (other.condition or {}).get("question_id") == str(question.id):
                other.condition = {}
        await session.delete(question)
        self._renumber(questions)
        self._touch(row, actor)
        await self._audit.record(
            session,
            action="delete",
            object_type="vendor_questionnaire_question",
            object_id=question_id,
            actor=actor,
            tenant_id=tenant_id,
            before={"questionnaire_id": str(row.id), **before},
            after=None,
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    async def reorder_questions(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        questionnaire_id: uuid.UUID,
        question_ids: Sequence[uuid.UUID],
    ) -> QuestionnaireView:
        row = await self._load(session, tenant_id, questionnaire_id)
        questions = await self._questions(session, tenant_id, row.id)
        by_id = {q.id: q for q in questions}
        if set(question_ids) != set(by_id) or len(question_ids) != len(by_id):
            raise InvalidInput(
                "The order must list every question in this questionnaire once.",
                detail="reorder ids do not match the questionnaire",
            )
        ordered = [by_id[i] for i in question_ids]
        seen: set[str] = set()
        for q in ordered:
            parent = (q.condition or {}).get("question_id")
            if parent and parent not in seen:
                raise InvalidInput(
                    "A question has to come after the question it depends on.",
                    detail=f"question {q.id} would precede its condition {parent}",
                )
            seen.add(str(q.id))
        before = [str(q.id) for q in questions]
        self._renumber(ordered)
        self._touch(row, actor)
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_questionnaire",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"order": before},
            after={"order": [str(q.id) for q in ordered]},
        )
        await session.flush()
        return await self.get_questionnaire(session, tenant_id=tenant_id, questionnaire_id=row.id)

    # -- what tiering and dispatch use ----------------------------------------

    async def ensure_defaults(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> None:
        """Give a tenant its starting questionnaires, once per purpose.

        Only when the tenant has never had one of that purpose, archived included,
        so archiving everything never brings the defaults back. A transaction lock
        keyed on the tenant stops two first page loads from both provisioning.
        """
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"vendor_questionnaires:{tenant_id}"},
        )
        have = set(
            (
                await session.execute(
                    select(VendorQuestionnaire.purpose)
                    .where(VendorQuestionnaire.tenant_id == tenant_id)
                    .distinct()
                )
            ).scalars()
        )
        for purpose in QUESTIONNAIRE_PURPOSES:
            if purpose in have:
                continue
            for spec in _DEFAULTS[purpose]:
                found = await self._library_template_or_none(session, spec["library"], purpose)
                if found is None:
                    continue
                template, questions = found
                levels = next(
                    (
                        lv
                        for key, _, lv in self._presets(template, questions)
                        if key == spec["preset"]
                    ),
                    None,
                )
                chosen = [q for q in questions if levels is None or q.scope_level in levels]
                row = VendorQuestionnaire(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    purpose=purpose,
                    name=spec["name"],
                    description=spec.get("description", template.description),
                    status="active",
                    is_default=bool(spec.get("is_default", False)),
                    default_tiers=list(spec.get("default_tiers", [])),
                    library_code=template.code,
                )
                session.add(row)
                await session.flush([row])
                copied = await self._copy_library(session, tenant_id, row, template, chosen)
                await self._audit.record(
                    session,
                    action="create",
                    object_type="vendor_questionnaire",
                    object_id=row.id,
                    actor=System(),
                    tenant_id=tenant_id,
                    before=None,
                    after={
                        "purpose": purpose,
                        "name": row.name,
                        "library_code": template.code,
                        "question_count": copied,
                        "reason": "starting questionnaire for a new workspace",
                    },
                )
        await session.flush()

    async def load_for_use(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        questionnaire_id: uuid.UUID | None,
        purpose: str,
        tier: str | None = None,
    ) -> VendorQuestionnaire | None:
        """The questionnaire a run or a dispatch should use.

        Named, it must be active and of the right purpose. Unnamed, tiering takes
        the tenant default and due diligence takes the one holding this tier.
        """
        await self.ensure_defaults(session, tenant_id=tenant_id)
        if questionnaire_id is not None:
            row = await self._load(session, tenant_id, questionnaire_id)
            if row.purpose != purpose:
                raise InvalidInput(
                    "That questionnaire is for a different job. Pick a "
                    + ("tiering" if purpose == "tiering" else "due diligence")
                    + " questionnaire.",
                    detail=f"questionnaire {row.id} is {row.purpose}, wanted {purpose}",
                )
            if row.status != "active":
                raise InvalidInput(
                    "That questionnaire is archived. Restore it or pick another.",
                    detail=f"questionnaire {row.id} is archived",
                )
            return row
        if purpose == "tiering":
            return await self._default_tiering_row(session, tenant_id)
        rows = (
            await session.execute(
                select(VendorQuestionnaire)
                .where(VendorQuestionnaire.tenant_id == tenant_id)
                .where(VendorQuestionnaire.purpose == "due_diligence")
                .where(VendorQuestionnaire.status == "active")
                .order_by(VendorQuestionnaire.created_at)
            )
        ).scalars()
        for row in rows:
            if tier and tier in (row.default_tiers or []):
                return row
        return None

    async def snapshot(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, questionnaire: VendorQuestionnaire
    ) -> dict[str, Any]:
        """The questionnaire exactly as it stands, to be stored with what it is used for."""
        questions = await self._questions(session, tenant_id, questionnaire.id)
        return {
            "id": str(questionnaire.id),
            "name": questionnaire.name,
            "purpose": questionnaire.purpose,
            "tier_thresholds": dict(questionnaire.tier_thresholds or {}),
            "questions": [{"id": str(q.id), **self._question_snapshot(q)} for q in questions],
        }

    # -- validation ------------------------------------------------------------

    def _validate(  # noqa: PLR0912, PLR0915 -- one branch per rule, kept together
        self,
        purpose: str,
        data: QuestionInput,
        *,
        earlier: Sequence[VendorQuestionnaireQuestion],
        own_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Every rule a question has to meet, returning the columns to write."""
        if data.answer_type not in QUESTION_TYPES:
            raise InvalidInput(
                "Pick a question type from the list.",
                detail=f"answer_type={data.answer_type!r}",
            )
        prompt = (data.prompt or "").strip()
        if not prompt:
            raise InvalidInput("Write the question before saving it.", detail="empty prompt")
        if len(prompt) > _MAX_PROMPT:
            raise InvalidInput(
                "Keep the question under 1,000 characters.", detail="prompt too long"
            )
        section = (data.section or "").strip() or "General"
        if len(section) > _MAX_SECTION:
            raise InvalidInput(
                "Keep the section name under 80 characters.", detail="section too long"
            )
        weight = float(data.weight)
        if not math.isfinite(weight) or weight < 0 or weight > _MAX_SCORE:
            raise InvalidInput("Weight has to be between 0 and 100.", detail=f"weight={weight}")

        is_choice = data.answer_type in CHOICE_TYPES
        options: list[dict[str, Any]] = []
        if is_choice:
            options = self._clean_options(purpose, data.options)
        keys = {o["key"] for o in options}

        evidence = data.evidence
        evidence_on: list[str] = []
        if evidence not in EVIDENCE_RULES:
            raise InvalidInput("Pick how evidence is handled.", detail=f"evidence={evidence!r}")
        if purpose == "tiering" or data.answer_type == "file":
            # Tiering is answered by our own team, and a file question's answer
            # already is the document.
            evidence = "none"
        elif evidence == "required" and is_choice:
            evidence_on = [k for k in dict.fromkeys(data.evidence_on) if k in keys]
            unknown = set(data.evidence_on) - keys
            if unknown:
                raise InvalidInput(
                    "Evidence can only be tied to options this question has.",
                    detail=f"unknown evidence_on {sorted(unknown)}",
                )

        domain: str | None = None
        critical = blocking = False
        if purpose == "due_diligence":
            domain = data.domain or "information_security"
            if domain not in RISK_DOMAINS:
                raise InvalidInput("Pick a risk domain from the list.", detail=f"domain={domain!r}")
            critical = bool(data.critical)
            blocking = bool(data.blocking)

        condition: dict[str, Any] = {}
        raw = dict(data.condition or {})
        if raw.get("question_id"):
            parent_id = str(raw["question_id"])
            if parent_id == str(own_id):
                raise InvalidInput(
                    "A question cannot depend on itself.", detail="self-referencing condition"
                )
            parent = next((q for q in earlier if str(q.id) == parent_id), None)
            if parent is None:
                raise InvalidInput(
                    "A question can only depend on a question that comes before it.",
                    detail=f"condition parent {parent_id} is not earlier",
                )
            if parent.answer_type not in CHOICE_TYPES:
                raise InvalidInput(
                    "A question can only depend on a choice question.",
                    detail=f"condition parent {parent_id} is {parent.answer_type}",
                )
            parent_keys = {o["key"] for o in parent.options}
            option_keys = [
                k for k in dict.fromkeys(raw.get("option_keys") or []) if isinstance(k, str)
            ]
            if not option_keys or set(option_keys) - parent_keys:
                raise InvalidInput(
                    "Pick which answers to that question should show this one.",
                    detail=f"condition options {option_keys} not in {sorted(parent_keys)}",
                )
            condition = {"question_id": parent_id, "option_keys": option_keys}

        return {
            "section": section,
            "prompt": prompt,
            "help_text": self._text(data.help_text, 2000),
            "answer_type": data.answer_type,
            "options": options,
            "required": bool(data.required),
            "evidence": evidence,
            "evidence_on": evidence_on,
            "weight": weight,
            "domain": domain,
            "critical": critical,
            "blocking": blocking,
            "condition": condition,
            "framework_refs": [str(r)[:40] for r in list(data.framework_refs)[:20]],
            "library_code": data.library_code,
        }

    @staticmethod
    def _clean_options(purpose: str, raw: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if len(raw) < _MIN_OPTIONS:
            raise InvalidInput(
                "A choice question needs at least two options.", detail="fewer than two options"
            )
        if len(raw) > _MAX_OPTIONS:
            raise InvalidInput(
                f"A question can have at most {_MAX_OPTIONS} options.", detail="too many options"
            )
        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, option in enumerate(raw):
            label = str(option.get("label") or "").strip()
            if not label or len(label) > _MAX_LABEL:
                raise InvalidInput(
                    "Every option needs a label under 200 characters.",
                    detail=f"option {index} label",
                )
            key = str(option.get("key") or "").strip().lower() or f"option_{index + 1}"
            if not _KEY.match(key) or key in seen:
                raise InvalidInput(
                    "Two options cannot share a key, and keys use lowercase letters, "
                    "numbers and underscores.",
                    detail=f"option key {key!r}",
                )
            seen.add(key)
            try:
                score = float(option.get("score") or 0)
            except (TypeError, ValueError) as exc:
                raise InvalidInput(
                    "An option's score has to be a number.", detail=f"option {key} score"
                ) from exc
            if not math.isfinite(score) or score < 0 or score > _MAX_SCORE:
                raise InvalidInput(
                    "Option scores run from 0 to 100.", detail=f"option {key} score={score}"
                )
            min_tier = option.get("min_tier") or None
            if purpose != "tiering":
                min_tier = None
            elif min_tier is not None and min_tier not in TIERS:
                raise InvalidInput(
                    "Pick a tier for the minimum from the list.",
                    detail=f"option {key} min_tier={min_tier!r}",
                )
            cleaned.append(
                {
                    "key": key,
                    "label": label,
                    "score": score,
                    "flag": bool(option.get("flag")) if purpose == "due_diligence" else False,
                    "not_applicable": bool(option.get("not_applicable")),
                    "comment_required": bool(option.get("comment_required")),
                    "min_tier": min_tier,
                }
            )
        return cleaned

    @staticmethod
    def _prune_dependents(
        questions: Sequence[VendorQuestionnaireQuestion], changed: VendorQuestionnaireQuestion
    ) -> None:
        """Keep later conditions honest when a question's options change or go away."""
        keys = {o["key"] for o in changed.options} if changed.answer_type in CHOICE_TYPES else set()
        for other in questions:
            condition = other.condition or {}
            if condition.get("question_id") != str(changed.id):
                continue
            kept = [k for k in condition.get("option_keys") or [] if k in keys]
            other.condition = {"question_id": str(changed.id), "option_keys": kept} if kept else {}

    # -- library ---------------------------------------------------------------

    @staticmethod
    def _presets(
        template: QuestionnaireTemplate, questions: Sequence[QuestionnaireQuestion]
    ) -> list[tuple[str, str, tuple[str, ...]]]:
        levels = {q.scope_level for q in questions}
        presets = [
            (key, label, lv)
            for key, label, lv in _PRESETS.get(template.purpose, ())
            if levels & set(lv)
        ]
        # A template that uses one level offers one start: the whole thing.
        distinct: dict[int, tuple[str, str, tuple[str, ...]]] = {}
        for preset in presets:
            count = sum(1 for q in questions if q.scope_level in preset[2])
            distinct.setdefault(count, preset)
        if len(distinct) == 1:
            key, _, lv = next(iter(distinct.values()))
            return [(key, "All questions", lv)]
        return list(distinct.values())

    async def _library_questions(
        self, session: AsyncSession, template_id: uuid.UUID
    ) -> list[QuestionnaireQuestion]:
        return list(
            (
                await session.execute(
                    select(QuestionnaireQuestion)
                    .where(QuestionnaireQuestion.template_id == template_id)
                    .order_by(QuestionnaireQuestion.position)
                )
            ).scalars()
        )

    async def _library_template_or_none(
        self, session: AsyncSession, code: str, purpose: str
    ) -> tuple[QuestionnaireTemplate, list[QuestionnaireQuestion]] | None:
        template = (
            await session.execute(
                select(QuestionnaireTemplate).where(QuestionnaireTemplate.code == code)
            )
        ).scalar_one_or_none()
        if template is None or template.purpose != purpose:
            return None
        return template, await self._library_questions(session, template.id)

    async def _library_template(
        self, session: AsyncSession, code: str, purpose: str
    ) -> tuple[QuestionnaireTemplate, list[QuestionnaireQuestion]]:
        found = await self._library_template_or_none(session, code, purpose)
        if found is None:
            raise NotFound(
                "That template is not in the library.", detail=f"library {code} for {purpose}"
            )
        return found

    def _library_input(
        self, template: QuestionnaireTemplate, question: QuestionnaireQuestion
    ) -> QuestionInput:
        """A library question in the builder's shape. The bank's older types convert here."""
        answer_type = question.answer_type
        options: Sequence[Mapping[str, Any]] = question.options or []
        evidence_on: tuple[str, ...] = ()
        if answer_type == "yes_no_na":
            answer_type, options, evidence_on = "single_choice", STANDARD_OPTIONS, _CLAIMS
        elif options:
            answer_type = (
                "multi_choice"
                if answer_type in ("multi_select", "multi_choice")
                else "single_choice"
            )
        else:
            answer_type = {"numeric": "number", "select": "paragraph"}.get(answer_type, answer_type)
        due = template.purpose == "due_diligence"
        domain = (question.domain or "information_security") if due else None
        return QuestionInput(
            prompt=question.body,
            answer_type=answer_type,
            section=question.section or (RISK_DOMAIN_LABELS[domain] if domain else "General"),
            help_text=question.help_text,
            options=[dict(o) for o in options],
            required=question.required,
            evidence="required" if question.evidence_required else "none",
            evidence_on=evidence_on if question.evidence_required else (),
            weight=question.weight,
            domain=domain,
            critical=question.critical_control if due else False,
            blocking=question.non_negotiable if due else False,
            framework_refs=list(question.framework_refs or []),
            library_code=question.code,
        )

    def _library_view(
        self,
        template: QuestionnaireTemplate,
        question: QuestionnaireQuestion,
        parent: QuestionnaireQuestion | None,
    ) -> LibraryQuestionView:
        data = self._library_input(template, question)
        return LibraryQuestionView(
            id=question.id,
            code=question.code,
            section=data.section,
            prompt=data.prompt,
            help_text=data.help_text,
            answer_type=data.answer_type,
            options=[dict(o) for o in data.options],
            required=data.required,
            evidence=data.evidence,
            weight=data.weight,
            domain=data.domain,
            domain_label=RISK_DOMAIN_LABELS.get(data.domain or ""),
            critical=data.critical,
            blocking=data.blocking,
            scope_level=question.scope_level,
            framework_refs=list(data.framework_refs),
            condition_code=parent.code if parent else None,
        )

    async def _copy_library(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        questionnaire: VendorQuestionnaire,
        template: QuestionnaireTemplate,
        chosen: Sequence[QuestionnaireQuestion],
    ) -> int:
        """Write library questions as the tenant's own, resolving branches by code.

        A parent is looked up in the whole template, because it may already be in
        the questionnaire from an earlier import rather than among these. Each
        question lands at the end of its own section, so sections stay together.
        """
        existing = await self._questions(session, tenant_id, questionnaire.id)
        by_code = {q.library_code: q for q in existing if q.library_code}
        library_by_id = {q.id: q for q in await self._library_questions(session, template.id)}
        written: list[VendorQuestionnaireQuestion] = list(existing)
        for question in chosen:
            data = self._library_input(template, question)
            parent = (
                library_by_id.get(question.parent_question_id)
                if question.parent_question_id
                else None
            )
            tenant_parent = by_code.get(parent.code) if parent else None
            if tenant_parent is not None and question.trigger_condition:
                data = replace(
                    data,
                    condition={
                        "question_id": str(tenant_parent.id),
                        "option_keys": list(question.trigger_condition),
                    },
                )
            new_id = uuid7()
            slot = self._slot(written, data)
            clean = self._validate(
                questionnaire.purpose, data, earlier=written[:slot], own_id=new_id
            )
            row = VendorQuestionnaireQuestion(
                id=new_id,
                tenant_id=tenant_id,
                questionnaire_id=questionnaire.id,
                position=slot,
                **clean,
            )
            session.add(row)
            written.insert(slot, row)
            by_code[question.code] = row
        self._renumber(written)
        await session.flush()
        return len(chosen)

    # -- helpers ---------------------------------------------------------------

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, questionnaire_id: uuid.UUID
    ) -> VendorQuestionnaire:
        row = await session.get(VendorQuestionnaire, questionnaire_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_GONE, detail=f"vendor questionnaire {questionnaire_id}")
        return row

    async def _questions(
        self, session: AsyncSession, tenant_id: uuid.UUID, questionnaire_id: uuid.UUID
    ) -> list[VendorQuestionnaireQuestion]:
        return list(
            (
                await session.execute(
                    select(VendorQuestionnaireQuestion)
                    .where(VendorQuestionnaireQuestion.tenant_id == tenant_id)
                    .where(VendorQuestionnaireQuestion.questionnaire_id == questionnaire_id)
                    .order_by(
                        VendorQuestionnaireQuestion.position, VendorQuestionnaireQuestion.created_at
                    )
                )
            ).scalars()
        )

    async def _counts(
        self, session: AsyncSession, tenant_id: uuid.UUID, ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        if not ids:
            return {}
        rows = await session.execute(
            select(
                VendorQuestionnaireQuestion.questionnaire_id,
                func.count(),
                func.count(func.distinct(VendorQuestionnaireQuestion.section)),
            )
            .where(VendorQuestionnaireQuestion.tenant_id == tenant_id)
            .where(VendorQuestionnaireQuestion.questionnaire_id.in_(list(ids)))
            .group_by(VendorQuestionnaireQuestion.questionnaire_id)
        )
        return {qid: (int(total), int(sections)) for qid, total, sections in rows.all()}

    async def _default_tiering_row(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> VendorQuestionnaire | None:
        return (
            await session.execute(
                select(VendorQuestionnaire)
                .where(VendorQuestionnaire.tenant_id == tenant_id)
                .where(VendorQuestionnaire.purpose == "tiering")
                .where(VendorQuestionnaire.is_default.is_(True))
            )
        ).scalar_one_or_none()

    @staticmethod
    def _touch(row: VendorQuestionnaire, actor: Actor) -> None:
        row.updated_by_membership_id = actor.id if isinstance(actor, Membership) else None
        row.updated_at = func.now()

    @staticmethod
    def _renumber(questions: Sequence[VendorQuestionnaireQuestion]) -> None:
        for index, question in enumerate(questions):
            question.position = index

    @staticmethod
    def _slot(
        questions: Sequence[VendorQuestionnaireQuestion],
        data: QuestionInput | VendorQuestionnaireQuestion,
    ) -> int:
        """Where a question goes: after the last one in its section, else at the end.

        At the end regardless when it branches from a question that would
        otherwise come after it.
        """
        section = (data.section or "").strip() or "General"
        last = max((i for i, q in enumerate(questions) if q.section == section), default=None)
        if last is None:
            return len(questions)
        slot = last + 1
        parent = (data.condition or {}).get("question_id")
        if parent and parent not in {str(q.id) for q in questions[:slot]}:
            return len(questions)
        return slot

    @staticmethod
    def _order_ok(questions: Sequence[VendorQuestionnaireQuestion]) -> bool:
        """Every follow-up still comes after the question it depends on."""
        seen: set[str] = set()
        for q in questions:
            parent = (q.condition or {}).get("question_id")
            if parent and parent not in seen:
                return False
            seen.add(str(q.id))
        return True

    @staticmethod
    def _check_purpose(purpose: str) -> None:
        if purpose not in QUESTIONNAIRE_PURPOSES:
            raise InvalidInput("Pick tiering or due diligence.", detail=f"purpose={purpose!r}")

    @staticmethod
    def _name(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise InvalidInput("Give the questionnaire a name.", detail="empty name")
        if len(cleaned) > _MAX_NAME:
            raise InvalidInput("Keep the name under 200 characters.", detail="name too long")
        return cleaned

    @staticmethod
    def _text(value: str | None, limit: int) -> str | None:
        cleaned = (value or "").strip()
        if len(cleaned) > limit:
            raise InvalidInput(
                f"Keep that under {limit:,} characters.", detail=f"text over {limit}"
            )
        return cleaned or None

    @staticmethod
    def _tiers(values: Sequence[str]) -> list[str]:
        unknown = set(values) - set(TIERS)
        if unknown:
            raise InvalidInput(
                "Pick tiers from the list.", detail=f"unknown tiers {sorted(unknown)}"
            )
        return [t for t in TIERS if t in set(values)]

    @staticmethod
    def _thresholds(values: Mapping[str, float]) -> dict[str, float]:
        if not values:
            return {}
        try:
            bands = {tier: float(values[tier]) for tier in ("critical", "high", "medium")}
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidInput(
                "Set a starting score for critical, high and medium.",
                detail="thresholds need critical, high and medium",
            ) from exc
        if not 0 < bands["medium"] < bands["high"] < bands["critical"] <= _MAX_SCORE:
            raise InvalidInput(
                "Scores have to rise from medium to high to critical, between 0 and 100.",
                detail=f"thresholds out of order: {bands}",
            )
        return bands

    @staticmethod
    def _settings_snapshot(row: VendorQuestionnaire) -> dict[str, Any]:
        return {
            "name": row.name,
            "description": row.description,
            "status": row.status,
            "is_default": row.is_default,
            "default_tiers": list(row.default_tiers or []),
            "tier_thresholds": dict(row.tier_thresholds or {}),
        }

    @staticmethod
    def _question_snapshot(q: VendorQuestionnaireQuestion) -> dict[str, Any]:
        return {
            "position": q.position,
            "section": q.section,
            "prompt": q.prompt,
            "help_text": q.help_text,
            "answer_type": q.answer_type,
            "options": [dict(o) for o in q.options or []],
            "required": q.required,
            "evidence": q.evidence,
            "evidence_on": list(q.evidence_on or []),
            "weight": q.weight,
            "domain": q.domain,
            "critical": q.critical,
            "blocking": q.blocking,
            "condition": dict(q.condition or {}),
            "framework_refs": list(q.framework_refs or []),
            "library_code": q.library_code,
        }

    def _summary(
        self,
        row: VendorQuestionnaire,
        counts: tuple[int, int],
        names: dict[uuid.UUID, str],
    ) -> QuestionnaireSummaryView:
        editor = row.updated_by_membership_id
        return QuestionnaireSummaryView(
            id=row.id,
            purpose=row.purpose,
            name=row.name,
            description=row.description,
            status=row.status,
            is_default=row.is_default,
            default_tiers=list(row.default_tiers or []),
            question_count=counts[0],
            section_count=counts[1],
            library_code=row.library_code,
            updated_at=row.updated_at,
            updated_by_name=names.get(editor) if editor else None,
        )

    def _view(
        self,
        row: VendorQuestionnaire,
        questions: Sequence[VendorQuestionnaireQuestion],
        names: dict[uuid.UUID, str],
    ) -> QuestionnaireView:
        summary = self._summary(row, (len(questions), len({q.section for q in questions})), names)
        return QuestionnaireView(
            **{f: getattr(summary, f) for f in QuestionnaireSummaryView.__dataclass_fields__},
            tier_thresholds=dict(row.tier_thresholds or {}),
            questions=[
                QuestionView(
                    id=q.id,
                    position=q.position,
                    section=q.section,
                    prompt=q.prompt,
                    help_text=q.help_text,
                    answer_type=q.answer_type,
                    options=[dict(o) for o in q.options or []],
                    required=q.required,
                    evidence=q.evidence,
                    evidence_on=list(q.evidence_on or []),
                    weight=q.weight,
                    domain=q.domain,
                    domain_label=RISK_DOMAIN_LABELS.get(q.domain or ""),
                    critical=q.critical,
                    blocking=q.blocking,
                    condition=dict(q.condition or {}),
                    framework_refs=list(q.framework_refs or []),
                    library_code=q.library_code,
                )
                for q in questions
            ],
        )


questionnaire_service = QuestionnaireService()
