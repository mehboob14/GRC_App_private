"""Questionnaire builder routes, mounted under ``/vendors/questionnaires``.

Included into ``vendors_router`` ahead of its ``/{vendor_id}`` routes, because a
literal segment declared after a parameterised one is never reached (see
``tests/unit/test_route_shadowing.py``).

Reading needs ``vendors:read``. Building needs ``vendors:manage``: a questionnaire
decides what every future vendor is asked and how a tier is reached, which is
programme configuration rather than work on one vendor.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.vendors.questionnaires import (
    QuestionInput,
    QuestionnaireInput,
    questionnaire_service,
)
from verity.modules.vendors.schemas import (
    LibraryTemplateOut,
    QuestionCreateWrite,
    QuestionImportWrite,
    QuestionnaireCreateWrite,
    QuestionnaireOut,
    QuestionnaireStatusWrite,
    QuestionnaireSummaryOut,
    QuestionnaireWrite,
    QuestionOrderWrite,
    QuestionWrite,
)

questionnaire_router = APIRouter(prefix="/questionnaires")

require_read = require("vendors:read")
require_manage = require("vendors:manage")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


def _question(body: QuestionWrite) -> QuestionInput:
    return QuestionInput(
        prompt=body.prompt,
        answer_type=body.answer_type,
        section=body.section,
        help_text=body.help_text,
        options=[o.model_dump() for o in body.options],
        required=body.required,
        evidence=body.evidence,
        evidence_on=body.evidence_on,
        weight=body.weight,
        domain=body.domain,
        critical=body.critical,
        blocking=body.blocking,
        condition=(
            {
                "question_id": str(body.condition.question_id),
                "option_keys": body.condition.option_keys,
            }
            if body.condition
            else None
        ),
    )


# -- static paths first --------------------------------------------------------


@questionnaire_router.get(
    "", response_model=list[QuestionnaireSummaryOut], summary="The tenant's questionnaires"
)
async def list_questionnaires(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    purpose: Annotated[str | None, Query()] = None,
    include_archived: bool = False,
) -> list[QuestionnaireSummaryOut]:
    rows = await questionnaire_service.list_questionnaires(
        session,
        tenant_id=context.tenant_id,
        purpose=purpose,
        include_archived=include_archived,
    )
    return [QuestionnaireSummaryOut.model_validate(r) for r in rows]


@questionnaire_router.get(
    "/library", response_model=list[LibraryTemplateOut], summary="Templates to start from"
)
async def library(
    _p: Annotated[Principal, Depends(require_read)],
    session: _Db,
    purpose: Annotated[str | None, Query()] = None,
) -> list[LibraryTemplateOut]:
    templates = await questionnaire_service.library(session, purpose=purpose)
    return [LibraryTemplateOut.model_validate(t) for t in templates]


@questionnaire_router.post(
    "",
    response_model=QuestionnaireOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start a questionnaire, blank or from the library",
)
async def create_questionnaire(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    body: QuestionnaireCreateWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.create_questionnaire(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        purpose=body.purpose,
        name=body.name,
        description=body.description,
        library_code=body.library_code,
        preset=body.preset,
    )
    return QuestionnaireOut.model_validate(view)


# -- one questionnaire -----------------------------------------------------------


@questionnaire_router.get(
    "/{questionnaire_id}", response_model=QuestionnaireOut, summary="A questionnaire"
)
async def get_questionnaire(
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
) -> QuestionnaireOut:
    view = await questionnaire_service.get_questionnaire(
        session, tenant_id=context.tenant_id, questionnaire_id=questionnaire_id
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.patch(
    "/{questionnaire_id}", response_model=QuestionnaireOut, summary="Edit its settings"
)
async def update_questionnaire(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    body: QuestionnaireWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.update_questionnaire(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        data=QuestionnaireInput(
            name=body.name,
            description=body.description,
            default_tiers=body.default_tiers,
            tier_thresholds=body.tier_thresholds,
            is_default=body.is_default,
        ),
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.post(
    "/{questionnaire_id}/duplicate",
    response_model=QuestionnaireOut,
    status_code=status.HTTP_201_CREATED,
    summary="Copy a questionnaire",
)
async def duplicate_questionnaire(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
) -> QuestionnaireOut:
    view = await questionnaire_service.duplicate_questionnaire(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.post(
    "/{questionnaire_id}/status", response_model=QuestionnaireOut, summary="Archive or restore"
)
async def set_questionnaire_status(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    body: QuestionnaireStatusWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.set_status(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        status=body.status,
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.post(
    "/{questionnaire_id}/questions/import",
    response_model=QuestionnaireOut,
    summary="Add questions from the library",
)
async def import_questions(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    body: QuestionImportWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.import_questions(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        library_question_ids=body.library_question_ids,
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.post(
    "/{questionnaire_id}/questions/order",
    response_model=QuestionnaireOut,
    summary="Reorder the questions",
)
async def reorder_questions(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    body: QuestionOrderWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.reorder_questions(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        question_ids=body.question_ids,
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.post(
    "/{questionnaire_id}/questions",
    response_model=QuestionnaireOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a question of your own",
)
async def add_question(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    body: QuestionCreateWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.add_question(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        data=_question(body),
        after_question_id=body.after_question_id,
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.patch(
    "/{questionnaire_id}/questions/{question_id}",
    response_model=QuestionnaireOut,
    summary="Edit a question",
)
async def update_question(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    question_id: uuid.UUID,
    body: QuestionWrite,
) -> QuestionnaireOut:
    view = await questionnaire_service.update_question(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        question_id=question_id,
        data=_question(body),
    )
    return QuestionnaireOut.model_validate(view)


@questionnaire_router.delete(
    "/{questionnaire_id}/questions/{question_id}",
    response_model=QuestionnaireOut,
    summary="Remove a question",
)
async def delete_question(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    questionnaire_id: uuid.UUID,
    question_id: uuid.UUID,
) -> QuestionnaireOut:
    view = await questionnaire_service.delete_question(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        questionnaire_id=questionnaire_id,
        question_id=question_id,
    )
    return QuestionnaireOut.model_validate(view)
