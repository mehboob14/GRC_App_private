"""HTTP for the documents & policies module.

Reads need ``documents:read``; authoring needs ``documents:manage``; approving a
tier needs ``documents:approve``; publishing needs ``documents:publish``
(deny-by-default, rule 7). Uploads are multipart; the download route streams the
current version's file from the tenant-scoped store.
"""

from __future__ import annotations

import uuid
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
from verity.modules.documents.models import CLASSIFICATIONS, DOC_TYPES, LIFECYCLES
from verity.modules.documents.schemas import (
    AcknowledgeCampaignRequest,
    ApprovalDecision,
    ArchiveRequest,
    AssignApprovalRequest,
    CampaignCommentCreate,
    CampaignCreate,
    CampaignOut,
    CampaignSummaryOut,
    CreateFromTemplateIn,
    DocumentContentUpdate,
    DocumentCreate,
    DocumentDetailOut,
    DocumentKpisOut,
    DocumentOut,
    DocumentUpdate,
    DocumentVocabularyOut,
    PendingApprovalOut,
    PendingCampaignOut,
    ReminderOut,
    TemplateOut,
    VersionDiffOut,
)
from verity.modules.documents.service import RecipientSelection, document_service

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
        renewal_date=body.renewal_date,
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


# -- acknowledgement campaigns (static paths before /{document_id}) ----------


@documents_router.get(
    "/campaigns/pending",
    response_model=list[PendingCampaignOut],
    summary="Campaigns awaiting my acknowledgement",
)
async def my_pending_campaigns(
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[PendingCampaignOut]:
    assert principal.membership_id is not None  # noqa: S101
    views = await document_service.my_pending_campaigns(
        session, tenant_id=context.tenant_id, membership_id=principal.membership_id
    )
    return [PendingCampaignOut.model_validate(v) for v in views]


@documents_router.get(
    "/campaigns/pending/count", summary="Count of campaigns awaiting my acknowledgement"
)
async def my_pending_campaign_count(
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> dict[str, int]:
    assert principal.membership_id is not None  # noqa: S101
    count = await document_service.my_pending_count(
        session, tenant_id=context.tenant_id, membership_id=principal.membership_id
    )
    return {"count": count}


@documents_router.get(
    "/approvals/pending",
    response_model=list[PendingApprovalOut],
    summary="Tiers waiting on my decision",
)
async def pending_approvals(
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[PendingApprovalOut]:
    assert principal.membership_id is not None  # noqa: S101
    views = await document_service.my_pending_approvals(
        session, tenant_id=context.tenant_id, membership_id=principal.membership_id
    )
    return [PendingApprovalOut.model_validate(v) for v in views]


@documents_router.get("/approvals/pending/count", summary="Count of tiers waiting on my decision")
async def pending_approval_count(
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> dict[str, int]:
    assert principal.membership_id is not None  # noqa: S101
    count = await document_service.my_pending_approval_count(
        session, tenant_id=context.tenant_id, membership_id=principal.membership_id
    )
    return {"count": count}


@documents_router.get(
    "/campaigns/{campaign_id}", response_model=CampaignOut, summary="One campaign with detail"
)
async def get_campaign(
    campaign_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CampaignOut:
    view = await document_service.get_campaign(
        session, tenant_id=context.tenant_id, campaign_id=campaign_id
    )
    return CampaignOut.model_validate(view)


@documents_router.post(
    "/campaigns/{campaign_id}/acknowledge",
    response_model=CampaignOut,
    summary="Acknowledge a campaign, optionally with a comment",
)
async def acknowledge_campaign(
    campaign_id: uuid.UUID,
    body: AcknowledgeCampaignRequest,
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CampaignOut:
    assert principal.membership_id is not None  # noqa: S101
    view = await document_service.acknowledge_campaign(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        membership_id=principal.membership_id,
        campaign_id=campaign_id,
        comment=body.comment,
    )
    return CampaignOut.model_validate(view)


@documents_router.post(
    "/campaigns/{campaign_id}/comments",
    response_model=CampaignOut,
    summary="Comment on a campaign, optionally tagging members",
)
async def comment_campaign(
    campaign_id: uuid.UUID,
    body: CampaignCommentCreate,
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CampaignOut:
    view = await document_service.add_campaign_comment(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        campaign_id=campaign_id,
        body=body.body,
        mentioned_ids=body.mentioned_ids,
    )
    return CampaignOut.model_validate(view)


@documents_router.post(
    "/campaigns/{campaign_id}/remind",
    response_model=ReminderOut,
    summary="Remind everyone who has not signed (campaign owner or document manager)",
)
async def remind_campaign(
    campaign_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> ReminderOut:
    """Reading the campaign is the flat permission; who may chase is decided in the
    service, which lets the person who sent it, or a document manager, through."""
    result = await document_service.remind_campaign(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        campaign_id=campaign_id,
        is_manager=principal.has("documents:manage"),
    )
    return ReminderOut(reminded=result.reminded, skipped=result.skipped)


@documents_router.get(
    "/campaigns/{campaign_id}/export",
    summary="Export who was asked and who signed, as CSV or Excel",
)
async def export_campaign(
    campaign_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    file_format: Annotated[str, Query(alias="format", pattern="^(csv|xlsx)$")] = "csv",
) -> Response:
    exported = await document_service.export_campaign(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        campaign_id=campaign_id,
        file_format=file_format,
    )
    return Response(
        content=exported.data,
        media_type=exported.content_type,
        headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
    )


@documents_router.post(
    "/campaigns/{campaign_id}/close",
    response_model=CampaignOut,
    summary="Close a campaign (owner)",
)
async def close_campaign(
    campaign_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CampaignOut:
    view = await document_service.close_campaign(
        session, tenant_id=context.tenant_id, actor=_actor(principal), campaign_id=campaign_id
    )
    return CampaignOut.model_validate(view)


@documents_router.post(
    "/{document_id}/campaigns",
    status_code=status.HTTP_201_CREATED,
    response_model=CampaignOut,
    summary="Start an acknowledgement campaign against a document",
)
async def create_campaign(
    document_id: uuid.UUID,
    body: CampaignCreate,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> CampaignOut:
    view = await document_service.create_campaign(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        title=body.title,
        message=body.message,
        reviewers=RecipientSelection(
            user_ids=body.reviewers.user_ids,
            role_ids=body.reviewers.role_ids,
            group_ids=body.reviewers.group_ids,
        ),
        approvers=RecipientSelection(
            user_ids=body.approvers.user_ids,
            role_ids=body.approvers.role_ids,
            group_ids=body.approvers.group_ids,
        ),
        due_at=body.due_at,
    )
    return CampaignOut.model_validate(view)


@documents_router.get(
    "/{document_id}/campaigns",
    response_model=list[CampaignSummaryOut],
    summary="Acknowledgement campaigns for a document",
)
async def list_document_campaigns(
    document_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[CampaignSummaryOut]:
    views = await document_service.list_document_campaigns(
        session, tenant_id=context.tenant_id, document_id=document_id
    )
    return [CampaignSummaryOut.model_validate(v) for v in views]


@documents_router.get(
    "/templates",
    response_model=list[TemplateOut],
    summary="Shipped policy templates a document can be started from",
)
async def list_templates(
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> list[TemplateOut]:
    """Browsing the library is a read. Starting a document from one is not."""
    views = await document_service.list_templates(session, tenant_id=context.tenant_id)
    return [TemplateOut.model_validate(v) for v in views]


@documents_router.post(
    "/from-template",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start a draft from a shipped policy template",
)
async def create_from_template(
    body: CreateFromTemplateIn,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    """The tenant gets a copy, not a reference: from here the wording is theirs.
    `{{company_name}}` is filled in from the workspace; anything else is left for
    someone to decide and is counted on the document."""
    view = await document_service.create_from_template(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        template_key=body.template_key,
        title=body.title,
        owner_membership_id=body.owner_membership_id,
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
        clear_renewal_date=body.clear_renewal_date,
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


@documents_router.get(
    "/{document_id}/versions/{version_id}/diff",
    response_model=VersionDiffOut,
    summary="What this version changed, against the one before it",
)
async def version_diff(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    _principal: Annotated[Principal, Depends(require_read)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> VersionDiffOut:
    """Reading history is a read: anyone who can open the document can see what
    changed in it and who changed it."""
    view = await document_service.version_diff(
        session,
        tenant_id=context.tenant_id,
        document_id=document_id,
        version_id=version_id,
    )
    return VersionDiffOut.model_validate(view)


@documents_router.post(
    "/{document_id}/versions/{version_id}/restore",
    response_model=DocumentDetailOut,
    summary="Put an earlier version's text back as a new version",
)
async def restore_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentDetailOut:
    """Restoring writes a NEW version carrying the old text — nothing is
    overwritten, so the version you left is still there to restore forward to.
    It routes through save_content, which means an approved or published
    document goes back to draft here too."""
    view = await document_service.restore_version(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        version_id=version_id,
    )
    return DocumentDetailOut.model_validate(view)


@documents_router.post(
    "/{document_id}/approvals/{tier}/assign",
    response_model=DocumentOut,
    summary="Assign who reviews/approves a tier",
)
async def assign_approval_tier(  # noqa: PLR0913, PLR0917
    document_id: uuid.UUID,
    tier: int,
    body: AssignApprovalRequest,
    principal: Annotated[Principal, Depends(require_manage)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.assign_approval_tier(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        document_id=document_id,
        tier=tier,
        targets=RecipientSelection(
            user_ids=body.targets.user_ids,
            role_ids=body.targets.role_ids,
            group_ids=body.targets.group_ids,
        ),
    )
    return DocumentOut.model_validate(view)


@documents_router.post(
    "/{document_id}/approvals/{tier}/decide",
    response_model=DocumentOut,
    summary="Approve or reject an approval tier you were assigned",
)
async def decide_approval(  # noqa: PLR0913, PLR0917
    document_id: uuid.UUID,
    tier: int,
    body: ApprovalDecision,
    principal: Annotated[Principal, Depends(require_approve)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
) -> DocumentOut:
    view = await document_service.decide_approval_tier(
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
