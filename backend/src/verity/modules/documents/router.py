"""HTTP for the documents & policies module.

Reads need ``documents:read``; authoring needs ``documents:manage``; approving a
tier needs ``documents:approve``; publishing needs ``documents:publish``
(deny-by-default, rule 7). Uploads are multipart; the download route streams the
current version's file from the tenant-scoped store.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
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
from verity.modules.documents.models import CLASSIFICATIONS, DOC_TYPES, LIFECYCLES
from verity.modules.documents.schemas import (
    ApprovalDecision,
    ArchiveRequest,
    DocumentContentUpdate,
    DocumentCreate,
    DocumentDetailOut,
    DocumentKpisOut,
    DocumentOut,
    DocumentUpdate,
    DocumentVocabularyOut,
    SubmitRequest,
)
from verity.modules.documents.service import document_service

documents_router = APIRouter(prefix="/documents", tags=["documents"])

require_read = require("documents:read")
require_manage = require("documents:manage")
require_approve = require("documents:approve")
require_publish = require("documents:publish")


def _actor(principal: Principal) -> Membership:
    assert principal.membership_id is not None  # noqa: S101
    return Membership(principal.membership_id)


# -- static paths first, so they are not captured by /{document_id} ----------


@documents_router.get("", response_model=list[DocumentOut], summary="List documents")
async def list_documents(
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[DocumentOut]:
    views = await document_service.list_documents(session, tenant_id=context.tenant_id)
    return [DocumentOut.model_validate(v) for v in views]


@documents_router.get("/kpis", response_model=DocumentKpisOut, summary="Register KPIs")
async def document_kpis(
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentKpisOut:
    return DocumentKpisOut.model_validate(
        await document_service.kpis(session, tenant_id=context.tenant_id)
    )


@documents_router.get(
    "/vocabulary", response_model=DocumentVocabularyOut, summary="Types and classifications"
)
async def vocabulary(
    _principal: Annotated[Principal, Depends(require_read)],
) -> DocumentVocabularyOut:
    return DocumentVocabularyOut(
        doc_types=list(DOC_TYPES),
        classifications=list(CLASSIFICATIONS),
        lifecycles=list(LIFECYCLES),
    )


@documents_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
    summary="Author a new document",
)
async def create_document(
    body: DocumentCreate,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.create_document(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        title=body.title,
        doc_type=body.doc_type,
        classification=body.classification,
        description=body.description,
        content_html=body.content_html,
        assigned_to=body.assigned_to,
        owner_membership_id=body.owner_membership_id,
        framework_ids=body.framework_ids,
        control_ids=body.control_ids,
    )
    return DocumentOut.model_validate(view)


@documents_router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
    summary="Create a document from an uploaded PDF/Word file",
)
async def upload_document(  # noqa: PLR0913, PLR0917 — multipart form fields
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    doc_type: Annotated[str, Form()],
    classification: Annotated[str, Form()] = "internal",
    description: Annotated[str | None, Form()] = None,
    assigned_to: Annotated[str | None, Form()] = None,
) -> DocumentOut:
    view = await document_service.create_uploaded(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        title=title,
        doc_type=doc_type,
        filename=file.filename or "upload",
        data=await file.read(),
        classification=classification,
        description=description,
        assigned_to=assigned_to,
    )
    return DocumentOut.model_validate(view)


@documents_router.get(
    "/{document_id}", response_model=DocumentDetailOut, summary="One document with detail"
)
async def get_document(
    document_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentDetailOut:
    view = await document_service.get_document(
        session,
        tenant_id=context.tenant_id,
        document_id=document_id,
        me=principal.membership_id,
    )
    return DocumentDetailOut.model_validate(view)


@documents_router.patch(
    "/{document_id}", response_model=DocumentOut, summary="Edit document metadata"
)
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdate,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.update_document(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        title=body.title,
        description=body.description,
        doc_type=body.doc_type,
        classification=body.classification,
        assigned_to=body.assigned_to,
        renewal_date=body.renewal_date,
        owner_membership_id=body.owner_membership_id,
        clear_owner=body.clear_owner,
        framework_ids=body.framework_ids,
        control_ids=body.control_ids,
    )
    return DocumentOut.model_validate(view)


@documents_router.post(
    "/{document_id}/archive",
    response_model=DocumentOut,
    summary="Archive a document with a recorded reason (never hard-deleted)",
)
async def archive_document(
    document_id: uuid.UUID,
    body: ArchiveRequest,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.archive_document(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        reason=body.reason,
    )
    return DocumentOut.model_validate(view)


@documents_router.get(
    "/{document_id}/download", summary="Download the current version's uploaded file"
)
async def download_document(
    document_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> Response:
    data, filename, content_type = await document_service.download(
        session, tenant_id=context.tenant_id, document_id=document_id
    )
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@documents_router.put(
    "/{document_id}/content",
    response_model=DocumentDetailOut,
    summary="Save authored content as a new version",
)
async def save_content(
    document_id: uuid.UUID,
    body: DocumentContentUpdate,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentDetailOut:
    view = await document_service.save_content(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        content_html=body.content_html,
        change_type=body.change_type,
        summary=body.summary,
    )
    return DocumentDetailOut.model_validate(view)


@documents_router.post(
    "/{document_id}/submit", response_model=DocumentOut, summary="Submit for approval"
)
async def submit_document(
    document_id: uuid.UUID,
    body: SubmitRequest,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.submit_for_approval(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        approver_ids=body.approver_ids,
    )
    return DocumentOut.model_validate(view)


@documents_router.post(
    "/{document_id}/approvals/{tier}/decide",
    response_model=DocumentOut,
    summary="Approve or reject an approval tier",
)
async def decide_approval(  # noqa: PLR0913, PLR0917
    document_id: uuid.UUID,
    tier: int,
    body: ApprovalDecision,
    principal: Annotated[Principal, Depends(require_approve)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.decide_approval(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        tier=tier,
        decision=body.decision,
        note=body.note,
    )
    return DocumentOut.model_validate(view)


@documents_router.post(
    "/{document_id}/publish", response_model=DocumentOut, summary="Publish an approved document"
)
async def publish_document(
    document_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_publish)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.publish(
        session, tenant_id=context.tenant_id, actor=_actor(principal), document_id=document_id
    )
    return DocumentOut.model_validate(view)


@documents_router.post(
    "/{document_id}/acknowledge",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Acknowledge (attest to) the current version",
)
async def acknowledge_document(
    document_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> Response:
    assert principal.membership_id is not None  # noqa: S101
    await document_service.acknowledge(
        session,
        tenant_id=context.tenant_id,
        membership_id=principal.membership_id,
        document_id=document_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
