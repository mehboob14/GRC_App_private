"""HTTP for the Task & Issue module.

Reads need ``tasks:read``; creating, editing and transitioning need
``tasks:manage``; changing who is assigned needs ``tasks:assign``; approving a
task needs ``tasks:approve`` (deny-by-default, rule 7). Evidence on a task is the
evidence library's, so reading it needs ``evidence:read`` and uploading a file
as new evidence needs ``evidence:manage`` as well. Static collection paths
are declared before ``/{task_id}`` so they are not captured by it.
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
from verity.core.errors import InvalidInput, PermissionDenied
from verity.modules.audit.service import Membership
from verity.modules.tasks.recurrence import Repeat
from verity.modules.tasks.schemas import (
    ApprovalDecision,
    AssignRequest,
    AutomationOut,
    AutomationUpdate,
    CapaCreate,
    CapaTransitionRequest,
    CapaUpdate,
    CommentRequest,
    MatrixCellUpdate,
    RepeatIn,
    SavedViewOut,
    SeverityMatrixCellOut,
    SlaDefinitionOut,
    SlaDefinitionUpsert,
    SubtaskRequest,
    TaskCreate,
    TaskDetailOut,
    TaskOut,
    TaskPageOut,
    TaskSummaryOut,
    TaskTemplateOut,
    TaskUpdate,
    TransitionRequest,
)
from verity.modules.tasks.service import (
    SeverityInput,
    TaskDetailView,
    TaskFilters,
    Upload,
    task_service,
)

tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

require_read = require("tasks:read")
require_manage = require("tasks:manage")
require_assign = require("tasks:assign")
require_approve = require("tasks:approve")
require_evidence_read = require("evidence:read")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]

_SEVERITY_FIELDS = frozenset({"impact", "urgency", "severity", "severity_reason"})


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


def _detail(view: TaskDetailView, principal: Principal) -> TaskDetailOut:
    """The detail as this caller may see it. Evidence is read with the evidence key, so a
    caller who can read tasks but not evidence sees the task and none of its attachments."""
    out = TaskDetailOut.model_validate(view)
    if not principal.has("evidence:read"):
        out.attachments = []
    return out


def _repeat(body: RepeatIn | None) -> Repeat | None:
    if body is None:
        return None
    if body.until is not None and body.count is not None:
        raise InvalidInput(
            "Choose an end date or a number of repeats, not both.",
            detail="repeat with both until and count",
        )
    return Repeat(
        frequency=body.frequency, interval=body.interval, until=body.until, count=body.count
    )


def _need_evidence(principal: Principal, *, files: bool, picked: bool) -> None:
    """Attaching touches the evidence library, so it needs that module's keys on top of
    ``tasks:manage``: read to attach an item already there, manage to add a new one."""
    if files and not principal.has("evidence:manage"):
        raise PermissionDenied(
            "You need access to add evidence to attach a file here.",
            detail=f"evidence:manage is not granted to membership {principal.membership_id}",
        )
    if picked and not principal.has("evidence:read"):
        raise PermissionDenied(
            "You need access to view evidence to attach an item from the library.",
            detail=f"evidence:read is not granted to membership {principal.membership_id}",
        )


async def _uploads(files: list[UploadFile] | None) -> list[Upload]:
    return [Upload(filename=f.filename or "upload", data=await f.read()) for f in files or []]


# -- static collection paths first -------------------------------------------


@tasks_router.get("", response_model=TaskPageOut, summary="List tasks")
async def list_tasks(  # noqa: PLR0913, PLR0917 — one query parameter per filter
    _p: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    search: str | None = None,
    kind: str | None = None,
    statuses: Annotated[list[str] | None, Query()] = None,
    priorities: Annotated[list[str] | None, Query()] = None,
    categories: Annotated[list[str] | None, Query()] = None,
    assignee: str | None = None,
    source_type: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> TaskPageOut:
    filters = TaskFilters(
        search=search,
        kind=kind,
        statuses=tuple(statuses or ()),
        priorities=tuple(priorities or ()),
        categories=tuple(categories or ()),
        assignee=assignee,
        source_type=source_type,
    )
    items, total = await task_service.list_tasks(
        session,
        tenant_id=context.tenant_id,
        filters=filters,
        page=page,
        page_size=page_size,
        caller_membership_id=context.membership_id,
    )
    return TaskPageOut(items=[TaskOut.model_validate(v) for v in items], total=total)


@tasks_router.get("/summary", response_model=TaskSummaryOut, summary="Overview dashboard")
async def summary(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> TaskSummaryOut:
    return TaskSummaryOut.model_validate(
        await task_service.summary(session, tenant_id=context.tenant_id)
    )


@tasks_router.get("/sla-definitions", response_model=list[SlaDefinitionOut], summary="SLA levels")
async def sla_definitions(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[SlaDefinitionOut]:
    rows = await task_service.sla_definitions(session, tenant_id=context.tenant_id)
    return [SlaDefinitionOut.model_validate(r) for r in rows]


@tasks_router.put(
    "/sla-definitions", response_model=list[SlaDefinitionOut], summary="Add or edit an SLA level"
)
async def upsert_sla_definition(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    body: SlaDefinitionUpsert,
) -> list[SlaDefinitionOut]:
    rows = await task_service.upsert_sla_definition(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        original_level=body.original_level,
        level=body.level,
        respond_hours=body.respond_hours,
        resolve_hours=body.resolve_hours,
    )
    return [SlaDefinitionOut.model_validate(r) for r in rows]


@tasks_router.delete(
    "/sla-definitions/{level}", response_model=list[SlaDefinitionOut], summary="Remove an SLA level"
)
async def delete_sla_definition(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    level: str,
) -> list[SlaDefinitionOut]:
    rows = await task_service.delete_sla_definition(
        session, tenant_id=context.tenant_id, actor=_actor(context), level=level
    )
    return [SlaDefinitionOut.model_validate(r) for r in rows]


@tasks_router.get(
    "/severity-matrix", response_model=list[SeverityMatrixCellOut], summary="Severity matrix"
)
async def severity_matrix(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[SeverityMatrixCellOut]:
    cells = await task_service.severity_matrix(session, tenant_id=context.tenant_id)
    return [SeverityMatrixCellOut.model_validate(c) for c in cells]


@tasks_router.put(
    "/severity-matrix", response_model=list[SeverityMatrixCellOut], summary="Edit a matrix cell"
)
async def update_matrix_cell(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    body: MatrixCellUpdate,
) -> list[SeverityMatrixCellOut]:
    cells = await task_service.upsert_matrix_cell(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        impact=body.impact,
        urgency=body.urgency,
        severity=body.severity,
        respond_hours=body.respond_hours,
        resolve_hours=body.resolve_hours,
    )
    return [SeverityMatrixCellOut.model_validate(c) for c in cells]


@tasks_router.get("/saved-views", response_model=list[SavedViewOut], summary="Saved views")
async def saved_views(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[SavedViewOut]:
    rows = await task_service.saved_views(session, tenant_id=context.tenant_id)
    return [SavedViewOut.model_validate(r) for r in rows]


@tasks_router.get("/templates", response_model=list[TaskTemplateOut], summary="Task templates")
async def templates(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[TaskTemplateOut]:
    rows = await task_service.templates(session, tenant_id=context.tenant_id)
    return [TaskTemplateOut.model_validate(r) for r in rows]


@tasks_router.get("/automations", response_model=list[AutomationOut], summary="Automations")
async def list_automations(
    _p: Annotated[Principal, Depends(require_read)], context: _Ctx, session: _Db
) -> list[AutomationOut]:
    rows = await task_service.list_automations(session, tenant_id=context.tenant_id)
    return [AutomationOut.model_validate(r) for r in rows]


@tasks_router.patch(
    "/automations/{automation_key}", response_model=AutomationOut, summary="Edit an automation"
)
async def update_automation(
    _p: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    automation_key: str,
    body: AutomationUpdate,
) -> AutomationOut:
    row = await task_service.update_automation(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        automation_key=automation_key,
        patch=body.model_dump(exclude_unset=True),
    )
    return AutomationOut.model_validate(row)


@tasks_router.post(
    "", response_model=TaskDetailOut, status_code=status.HTTP_201_CREATED, summary="Create a task"
)
async def create_task(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    body: TaskCreate,
) -> TaskDetailOut:
    view = await task_service.create_task(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_kind=body.task_kind,
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        sla_level=body.sla_level,
        owner_membership_id=body.owner_membership_id,
        assignee_ids=body.assignee_ids,
        due_at=body.due_at,
        severity_input=SeverityInput(
            impact=body.impact,
            urgency=body.urgency,
            severity=body.severity,
            reason=body.severity_reason,
        ),
        repeat=_repeat(body.repeat),
        requires_approval=body.requires_approval,
    )
    return _detail(view, principal)


# -- item paths --------------------------------------------------------------


@tasks_router.get("/{task_id}", response_model=TaskDetailOut, summary="Task detail")
async def get_task(
    principal: Annotated[Principal, Depends(require_read)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
) -> TaskDetailOut:
    return _detail(
        await task_service.get_task(session, tenant_id=context.tenant_id, task_id=task_id),
        principal,
    )


@tasks_router.patch("/{task_id}", response_model=TaskDetailOut, summary="Edit a task")
async def update_task(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: TaskUpdate,
) -> TaskDetailOut:
    view = await task_service.update_task(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        sla_level=body.sla_level,
        owner_membership_id=body.owner_membership_id,
        clear_owner=body.clear_owner,
        due_at=body.due_at,
        severity_input=(
            SeverityInput(
                impact=body.impact,
                urgency=body.urgency,
                severity=body.severity,
                reason=body.severity_reason,
            )
            if body.model_fields_set & _SEVERITY_FIELDS
            else None
        ),
        repeat=_repeat(body.repeat),
        clear_repeat=body.clear_repeat,
        requires_approval=body.requires_approval,
    )
    return _detail(view, principal)


@tasks_router.post("/{task_id}/transition", response_model=TaskDetailOut, summary="Move a task")
async def transition(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: TransitionRequest,
) -> TaskDetailOut:
    _need_evidence(principal, files=False, picked=bool(body.evidence_ids))
    view = await task_service.transition(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        to_status=body.to_status,
        note=body.note,
        evidence_ids=body.evidence_ids,
    )
    return _detail(view, principal)


@tasks_router.post(
    "/{task_id}/transition/files",
    response_model=TaskDetailOut,
    summary="Move a task, attaching files and evidence",
)
async def transition_with_files(  # noqa: PLR0913, PLR0917 — multipart form fields
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    to_status: Annotated[str, Form()],
    note: Annotated[str | None, Form()] = None,
    evidence_ids: Annotated[list[uuid.UUID] | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> TaskDetailOut:
    _need_evidence(principal, files=bool(files), picked=bool(evidence_ids))
    view = await task_service.transition(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        to_status=to_status,
        note=note,
        evidence_ids=evidence_ids or [],
        uploads=await _uploads(files),
    )
    return _detail(view, principal)


@tasks_router.post(
    "/{task_id}/attachments", response_model=TaskDetailOut, summary="Attach evidence or files"
)
async def attach(  # noqa: PLR0913, PLR0917 — multipart form fields
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    evidence_ids: Annotated[list[uuid.UUID] | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> TaskDetailOut:
    _need_evidence(principal, files=bool(files), picked=bool(evidence_ids))
    view = await task_service.attach(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        evidence_ids=evidence_ids or [],
        uploads=await _uploads(files),
    )
    return _detail(view, principal)


@tasks_router.get(
    "/{task_id}/attachments/{evidence_id}/download",
    summary="Download a file attached to a task; the sha256 on the record proves integrity",
)
async def download_attachment(
    _p: Annotated[Principal, Depends(require_read)],
    _e: Annotated[Principal, Depends(require_evidence_read)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> Response:
    data, filename, content_type = await task_service.download_attachment(
        session, tenant_id=context.tenant_id, task_id=task_id, evidence_id=evidence_id
    )
    return Response(
        content=data,
        media_type=content_type,
        # attachment, not inline: an uploaded artefact is never rendered in the app's own
        # origin, which is what keeps a malicious upload inert.
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@tasks_router.post("/{task_id}/assign", response_model=TaskDetailOut, summary="Set assignees")
async def assign(
    principal: Annotated[Principal, Depends(require_assign)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: AssignRequest,
) -> TaskDetailOut:
    view = await task_service.set_assignees(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        membership_ids=body.membership_ids,
    )
    return _detail(view, principal)


@tasks_router.post("/{task_id}/comments", response_model=TaskDetailOut, summary="Add a comment")
async def add_comment(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: CommentRequest,
) -> TaskDetailOut:
    view = await task_service.add_comment(
        session, tenant_id=context.tenant_id, actor=_actor(context), task_id=task_id, body=body.body
    )
    return _detail(view, principal)


@tasks_router.post("/{task_id}/subtasks", response_model=TaskDetailOut, summary="Add a sub-task")
async def add_subtask(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: SubtaskRequest,
) -> TaskDetailOut:
    view = await task_service.add_subtask(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        parent_id=task_id,
        title=body.title,
    )
    return _detail(view, principal)


@tasks_router.post("/{task_id}/approve", response_model=TaskDetailOut, summary="Approve or reject")
async def decide_approval(
    principal: Annotated[Principal, Depends(require_approve)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: ApprovalDecision,
) -> TaskDetailOut:
    view = await task_service.decide_approval(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        decision=body.decision,
        note=body.note,
    )
    return _detail(view, principal)


# -- CAPA actions (issues only) ----------------------------------------------


@tasks_router.post("/{task_id}/actions", response_model=TaskDetailOut, summary="Add a CAPA action")
async def add_capa_action(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    body: CapaCreate,
) -> TaskDetailOut:
    view = await task_service.add_capa_action(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        action_type=body.action_type,
        title=body.title,
        description=body.description,
        owner_membership_id=body.owner_membership_id,
        due_at=body.due_at,
    )
    return _detail(view, principal)


@tasks_router.patch(
    "/{task_id}/actions/{action_id}", response_model=TaskDetailOut, summary="Edit a CAPA action"
)
async def update_capa_action(  # noqa: PLR0913, PLR0917 — one path parameter per level
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    action_id: uuid.UUID,
    body: CapaUpdate,
) -> TaskDetailOut:
    view = await task_service.update_capa_action(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        action_id=action_id,
        action_type=body.action_type,
        title=body.title,
        description=body.description,
        owner_membership_id=body.owner_membership_id,
        clear_owner=body.clear_owner,
        due_at=body.due_at,
    )
    return _detail(view, principal)


@tasks_router.post(
    "/{task_id}/actions/{action_id}/transition",
    response_model=TaskDetailOut,
    summary="Move a CAPA action",
)
async def transition_capa_action(  # noqa: PLR0913, PLR0917 — one path parameter per level
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    action_id: uuid.UUID,
    body: CapaTransitionRequest,
) -> TaskDetailOut:
    view = await task_service.transition_capa_action(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        action_id=action_id,
        to_status=body.to_status,
    )
    return _detail(view, principal)


@tasks_router.post(
    "/{task_id}/actions/{action_id}/promote",
    response_model=TaskDetailOut,
    summary="Promote a CAPA action to a task",
)
async def promote_capa_action(
    principal: Annotated[Principal, Depends(require_manage)],
    context: _Ctx,
    session: _Db,
    task_id: uuid.UUID,
    action_id: uuid.UUID,
) -> TaskDetailOut:
    view = await task_service.promote_capa_to_task(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        task_id=task_id,
        action_id=action_id,
    )
    return _detail(view, principal)
