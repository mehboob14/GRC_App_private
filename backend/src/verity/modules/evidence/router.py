"""HTTP for the evidence library.

Uploads arrive as multipart, so the file route takes form fields rather than a
JSON body — that is the only reason its signature looks different from the link
route beside it.

The download route streams from the store, which scopes every read to the
tenant: a key from one tenant cannot address another tenant's object even if it
leaked. Reads need ``evidence:read``, writes ``evidence:manage``.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import (
    Principal,
    TenantContext,
    get_tenant_context,
    get_tenant_session,
    require,
)
from verity.modules.audit.service import Membership
from verity.modules.evidence.models import DEFAULT_VALIDITY_DAYS, EVIDENCE_TYPES
from verity.modules.evidence.schemas import (
    EvidenceLinkCreate,
    EvidenceOut,
    EvidenceReviewRequest,
    EvidenceTypeOut,
    EvidenceUpdate,
    EvidenceVocabularyOut,
)
from verity.modules.evidence.service import evidence_service

evidence_router = APIRouter(prefix="/evidence", tags=["evidence"])

require_evidence_read = require("evidence:read")
require_evidence_manage = require("evidence:manage")
require_evidence_review = require("evidence:review")

FRESHNESS_STATES = ("current", "aging", "stale", "no_expiry")


def _actor(principal: Principal) -> Membership:
    assert principal.membership_id is not None  # noqa: S101
    return Membership(principal.membership_id)


def _humanise(value: str) -> str:
    return value.replace("_", " ").capitalize()


@evidence_router.get(
    "/vocabulary",
    response_model=EvidenceVocabularyOut,
    summary="Evidence types with their default validity periods",
)
async def get_vocabulary(
    _principal: Annotated[Principal, Depends(require_evidence_read)],
) -> EvidenceVocabularyOut:
    # Served from the same constants the CHECK is built from, so the UI cannot
    # offer a type the database would reject.
    return EvidenceVocabularyOut(
        types=[
            EvidenceTypeOut(
                value=value,
                label=_humanise(value),
                default_validity_days=DEFAULT_VALIDITY_DAYS[value],
            )
            for value in EVIDENCE_TYPES
        ],
        freshness_states=list(FRESHNESS_STATES),
    )


@evidence_router.get(
    "",
    response_model=list[EvidenceOut],
    summary="The evidence library, with each item's controls and freshness",
)
async def list_evidence(
    _principal: Annotated[Principal, Depends(require_evidence_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    evidence_type: str | None = None,
    control_id: uuid.UUID | None = None,
    freshness: Annotated[str | None, Query(alias="freshness")] = None,
) -> list[EvidenceOut]:
    views = await evidence_service.list_evidence(
        session,
        tenant_id=context.tenant_id,
        evidence_type=evidence_type,
        control_id=control_id,
        freshness_filter=freshness,
    )
    return [EvidenceOut.model_validate(view) for view in views]


@evidence_router.get("/{evidence_id}", response_model=EvidenceOut, summary="One evidence item")
async def get_evidence(
    evidence_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_evidence_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> EvidenceOut:
    view = await evidence_service.get(session, tenant_id=context.tenant_id, evidence_id=evidence_id)
    return EvidenceOut.model_validate(view)


@evidence_router.get(
    "/{evidence_id}/download",
    summary="Download the stored file; the sha256 on the record proves integrity",
)
async def download_evidence(
    evidence_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_evidence_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> Response:
    data, filename, content_type = await evidence_service.download(
        session, tenant_id=context.tenant_id, evidence_id=evidence_id
    )
    return Response(
        content=data,
        media_type=content_type,
        # attachment, not inline: an uploaded artefact is never rendered in the
        # app's own origin, which is what keeps a malicious upload inert.
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@evidence_router.post(
    "/file",
    status_code=status.HTTP_201_CREATED,
    response_model=EvidenceOut,
    summary="Upload a file or image as evidence",
)
async def upload_evidence(  # noqa: PLR0913, PLR0917 — multipart form fields
    principal: Annotated[Principal, Depends(require_evidence_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    evidence_type: Annotated[str, Form()],
    collected_at: Annotated[date, Form()],
    description: Annotated[str | None, Form()] = None,
    source_label: Annotated[str | None, Form()] = None,
    owner_membership_id: Annotated[uuid.UUID | None, Form()] = None,
    renewal_date: Annotated[date | None, Form()] = None,
    control_ids: Annotated[list[uuid.UUID] | None, Form()] = None,
) -> EvidenceOut:
    view = await evidence_service.add_file(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        title=title,
        filename=file.filename or "upload",
        data=await file.read(),
        evidence_type=evidence_type,
        collected_at=collected_at,
        description=description,
        source_label=source_label,
        owner_membership_id=owner_membership_id,
        renewal_date=renewal_date,
        control_ids=control_ids or [],
    )
    return EvidenceOut.model_validate(view)


@evidence_router.post(
    "/link",
    status_code=status.HTTP_201_CREATED,
    response_model=EvidenceOut,
    summary="Record a link as evidence",
)
async def add_link(
    body: EvidenceLinkCreate,
    principal: Annotated[Principal, Depends(require_evidence_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> EvidenceOut:
    view = await evidence_service.add_link(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        title=body.title,
        link_url=body.link_url,
        evidence_type=body.evidence_type,
        collected_at=body.collected_at,
        description=body.description,
        source_label=body.source_label,
        owner_membership_id=body.owner_membership_id,
        renewal_date=body.renewal_date,
        control_ids=body.control_ids,
    )
    return EvidenceOut.model_validate(view)


@evidence_router.patch(
    "/{evidence_id}",
    response_model=EvidenceOut,
    summary="Edit an item, its renewal date, or the controls it supports",
)
async def update_evidence(
    evidence_id: uuid.UUID,
    body: EvidenceUpdate,
    principal: Annotated[Principal, Depends(require_evidence_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> EvidenceOut:
    view = await evidence_service.update(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        evidence_id=evidence_id,
        title=body.title,
        description=body.description,
        evidence_type=body.evidence_type,
        source_label=body.source_label,
        owner_membership_id=body.owner_membership_id,
        clear_owner=body.clear_owner,
        collected_at=body.collected_at,
        renewal_date=body.renewal_date,
        control_ids=body.control_ids,
    )
    return EvidenceOut.model_validate(view)


@evidence_router.post(
    "/{evidence_id}/review",
    response_model=EvidenceOut,
    summary="Approve or reject an item — the four-eyes review step",
)
async def review_evidence(
    evidence_id: uuid.UUID,
    body: EvidenceReviewRequest,
    principal: Annotated[Principal, Depends(require_evidence_review)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> EvidenceOut:
    assert principal.membership_id is not None  # noqa: S101 — tenant plane always has one
    view = await evidence_service.review(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        evidence_id=evidence_id,
        reviewer_membership_id=principal.membership_id,
        decision=body.decision,
        note=body.note,
    )
    return EvidenceOut.model_validate(view)
