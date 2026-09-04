"""HTTP for the vulnerabilities module.

Reads need ``vulnerabilities:read``; adding/transitioning needs
``vulnerabilities:manage``; importing a report needs ``vulnerabilities:import``;
accepting the risk (a waiver) needs ``vulnerabilities:accept`` (deny-by-default,
rule 7). Import is multipart CSV; the prioritised register is the default list.
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
from verity.core.errors import InvalidInput
from verity.modules.audit.service import Membership
from verity.modules.vulnerabilities.schemas import (
    AcceptRequest,
    AddFindingRequest,
    AssignRequest,
    CancelRemediationRequest,
    ExceptionDecisionIn,
    ExceptionRequestIn,
    ImportResultOut,
    InstanceDetailOut,
    InstanceOut,
    KpiOut,
    LinkAssetRequest,
    LookupCveOut,
    LookupCveRequest,
    RemediationPlanOut,
    ReportOut,
    SlaPolicyOut,
    SlaPolicyUpdate,
    ThroughputOut,
    TransitionRequest,
    VerifyRemediationRequest,
    VerifyRequest,
)
from verity.modules.vulnerabilities.service import (
    ExceptionRequest,
    FindingRow,
    vulnerability_service,
)

vulnerabilities_router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])

require_read = require("vulnerabilities:read")
require_manage = require("vulnerabilities:manage")
require_import = require("vulnerabilities:import")
require_accept = require("vulnerabilities:accept")

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]

_MAX_CSV_BYTES = 10 * 1024 * 1024


def _actor(principal: Principal) -> Membership:
    assert principal.membership_id is not None  # noqa: S101
    return Membership(principal.membership_id)


# -- static paths first ------------------------------------------------------


@vulnerabilities_router.get("", response_model=list[InstanceOut], summary="Prioritised register")
async def list_vulnerabilities(  # noqa: PLR0913, PLR0917
    context: _Ctx,
    session: _Db,
    _principal: Annotated[Principal, Depends(require_read)],
    state: str = "open",
    severity: str | None = None,
    asset_id: uuid.UUID | None = None,
    kev_only: bool = False,
    overdue_only: bool = False,
    search: str | None = None,
) -> list[InstanceOut]:
    views = await vulnerability_service.list_instances(
        session,
        tenant_id=context.tenant_id,
        state=state,
        severity=severity,
        asset_id=asset_id,
        kev_only=kev_only,
        overdue_only=overdue_only,
        search=search,
    )
    return [InstanceOut.model_validate(v) for v in views]


@vulnerabilities_router.get("/kpis", response_model=KpiOut, summary="Register KPIs")
async def kpis(
    context: _Ctx, session: _Db, _principal: Annotated[Principal, Depends(require_read)]
) -> KpiOut:
    return KpiOut.model_validate(
        await vulnerability_service.kpis(session, tenant_id=context.tenant_id)
    )


@vulnerabilities_router.get(
    "/sla", response_model=list[SlaPolicyOut], summary="Remediation SLA per severity"
)
async def get_sla(
    context: _Ctx, session: _Db, _principal: Annotated[Principal, Depends(require_read)]
) -> list[SlaPolicyOut]:
    views = await vulnerability_service.sla_policy(session, tenant_id=context.tenant_id)
    return [SlaPolicyOut.model_validate(v) for v in views]


@vulnerabilities_router.put(
    "/sla", response_model=list[SlaPolicyOut], summary="Set the SLA for one severity"
)
async def set_sla(
    body: SlaPolicyUpdate,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> list[SlaPolicyOut]:
    views = await vulnerability_service.set_sla_policy(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        severity=body.severity,
        days=body.days,
    )
    return [SlaPolicyOut.model_validate(v) for v in views]


@vulnerabilities_router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=ImportResultOut,
    summary="Import findings from a scanner CSV export",
)
async def import_findings(  # noqa: PLR0913, PLR0917
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_import)],
    file: Annotated[UploadFile, File()],
    report_name: Annotated[str, Form()],
    report_type: Annotated[str, Form()] = "vulnerability_scan",
    scan_tool: Annotated[str | None, Form()] = None,
) -> ImportResultOut:
    data = await file.read()
    if len(data) > _MAX_CSV_BYTES:
        raise InvalidInput(
            "This file is larger than 10 MB. Split the scan export into smaller files "
            "and upload them one at a time.",
            detail="file is too large (max 10 MB)",
        )
    result = await vulnerability_service.import_file(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        file_data=data,
        file_name=file.filename or "report.csv",
        report_name=report_name,
        report_type=report_type,
        scan_tool=scan_tool,
    )
    return ImportResultOut.model_validate(result)


@vulnerabilities_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InstanceDetailOut,
    summary="Add a finding manually",
)
async def add_finding(
    body: AddFindingRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    view = await vulnerability_service.add_finding(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        row=FindingRow(
            title=body.title,
            severity=body.severity,
            asset_id=body.asset_id,
            cve_id=body.cve_id,
            description=body.description,
            cvss_score=body.cvss_score,
            cvss_vector=body.cvss_vector,
            cwe_id=body.cwe_id,
            recommendation=body.recommendation,
            component=body.component,
            port=body.port,
            affected_url=body.affected_url,
            evidence=body.evidence,
            reproduction_steps=body.reproduction_steps,
            source="manual",
        ),
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.get(
    "/throughput", response_model=ThroughputOut, summary="Remediation throughput / MTTR"
)
async def throughput(
    context: _Ctx, session: _Db, _principal: Annotated[Principal, Depends(require_read)]
) -> ThroughputOut:
    return ThroughputOut.model_validate(
        await vulnerability_service.throughput(session, tenant_id=context.tenant_id)
    )


@vulnerabilities_router.get(
    "/reports", response_model=list[ReportOut], summary="Uploaded scan/test reports"
)
async def list_reports(
    context: _Ctx, session: _Db, _principal: Annotated[Principal, Depends(require_read)]
) -> list[ReportOut]:
    views = await vulnerability_service.list_reports(session, tenant_id=context.tenant_id)
    return [ReportOut.model_validate(v) for v in views]


@vulnerabilities_router.get(
    "/reports/{report_id}/download", summary="Download a stored report file"
)
async def download_report(
    report_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    _principal: Annotated[Principal, Depends(require_read)],
) -> Response:
    data, filename, content_type = await vulnerability_service.report_file(
        session, tenant_id=context.tenant_id, report_id=report_id
    )
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@vulnerabilities_router.post(
    "/reports/{report_id}/reparse",
    response_model=ImportResultOut,
    summary="Re-run parsing on a report's stored file",
)
async def reparse_report(
    report_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_import)],
) -> ImportResultOut:
    result = await vulnerability_service.reparse_report(
        session, tenant_id=context.tenant_id, actor=_actor(principal), report_id=report_id
    )
    return ImportResultOut.model_validate(result)


@vulnerabilities_router.post(
    "/lookup-by-title",
    response_model=LookupCveOut,
    summary="Resolve a CVE from a title/id and pull NVD data (manual-add autofill)",
)
async def lookup_by_title(
    body: LookupCveRequest,
    context: _Ctx,
    session: _Db,
    _principal: Annotated[Principal, Depends(require_read)],
) -> LookupCveOut:
    view = await vulnerability_service.lookup_cve(
        session, tenant_id=context.tenant_id, title=body.title, cve_id=body.cve_id
    )
    return LookupCveOut.model_validate(view)


@vulnerabilities_router.get(
    "/{instance_id}", response_model=InstanceDetailOut, summary="One finding with detail"
)
async def get_vulnerability(
    instance_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    _principal: Annotated[Principal, Depends(require_read)],
) -> InstanceDetailOut:
    view = await vulnerability_service.get_instance(
        session, tenant_id=context.tenant_id, instance_id=instance_id
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/transition",
    response_model=InstanceDetailOut,
    summary="Move a finding through its state machine",
)
async def transition(
    instance_id: uuid.UUID,
    body: TransitionRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    view = await vulnerability_service.transition_instance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        to_state=body.to_state,
        note=body.note,
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/verify",
    response_model=InstanceDetailOut,
    summary="Verify a retested finding as fixed (formal closure)",
)
async def verify(
    instance_id: uuid.UUID,
    body: VerifyRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_accept)],
) -> InstanceDetailOut:
    view = await vulnerability_service.verify_instance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        resolution_notes=body.resolution_notes,
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/reenrich",
    response_model=InstanceDetailOut,
    summary="Refresh threat intel and re-prioritise this finding",
)
async def reenrich(
    instance_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    view = await vulnerability_service.reenrich_instance(
        session, tenant_id=context.tenant_id, actor=_actor(principal), instance_id=instance_id
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/assign",
    response_model=InstanceDetailOut,
    summary="Assign this finding to a person, and optionally roles or groups",
)
async def assign_instance(
    instance_id: uuid.UUID,
    body: AssignRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    view = await vulnerability_service.assign_instance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        owner_membership_id=body.owner_membership_id,
        targets=[(t.target_type, t.target_id) for t in body.targets],
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/link-asset",
    response_model=InstanceDetailOut,
    summary="Record that this finding also affects another asset",
)
async def link_asset(
    instance_id: uuid.UUID,
    body: LinkAssetRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    view = await vulnerability_service.link_asset(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        asset_id=body.asset_id,
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/move-asset",
    response_model=InstanceDetailOut,
    summary="Re-point a mis-attached finding to the correct asset",
)
async def move_asset(
    instance_id: uuid.UUID,
    body: LinkAssetRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    view = await vulnerability_service.move_asset(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        asset_id=body.asset_id,
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.get(
    "/{instance_id}/remediation-plan",
    response_model=RemediationPlanOut,
    summary="The finding's remediation plan (or a heuristic preview)",
)
async def get_remediation_plan(
    instance_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    _principal: Annotated[Principal, Depends(require_read)],
) -> RemediationPlanOut:
    view = await vulnerability_service.remediation_plan(
        session, tenant_id=context.tenant_id, instance_id=instance_id
    )
    return RemediationPlanOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/remediation-plan",
    response_model=RemediationPlanOut,
    summary="Generate (or regenerate) the remediation plan",
)
async def generate_remediation_plan(
    instance_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> RemediationPlanOut:
    view = await vulnerability_service.generate_remediation(
        session, tenant_id=context.tenant_id, actor=_actor(principal), instance_id=instance_id
    )
    return RemediationPlanOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/remediation-plan/approve",
    response_model=RemediationPlanOut,
    summary="Approve the remediation plan",
)
async def approve_remediation_plan(
    instance_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> RemediationPlanOut:
    view = await vulnerability_service.approve_remediation(
        session, tenant_id=context.tenant_id, actor=_actor(principal), instance_id=instance_id
    )
    return RemediationPlanOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/remediation-plan/apply",
    response_model=RemediationPlanOut,
    summary="Apply the remediation plan (simulated executor)",
)
async def apply_remediation_plan(
    instance_id: uuid.UUID,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> RemediationPlanOut:
    view = await vulnerability_service.apply_remediation(
        session, tenant_id=context.tenant_id, actor=_actor(principal), instance_id=instance_id
    )
    return RemediationPlanOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/remediation-plan/verify",
    response_model=RemediationPlanOut,
    summary="Attest the fix and close the finding",
)
async def verify_remediation_plan(
    instance_id: uuid.UUID,
    body: VerifyRemediationRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_accept)],
) -> RemediationPlanOut:
    view = await vulnerability_service.verify_remediation(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        evidence=body.evidence,
    )
    return RemediationPlanOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/remediation-plan/cancel",
    response_model=RemediationPlanOut,
    summary="Cancel the remediation plan (finding stays open)",
)
async def cancel_remediation_plan(
    instance_id: uuid.UUID,
    body: CancelRemediationRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> RemediationPlanOut:
    view = await vulnerability_service.cancel_remediation(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        reason=body.reason,
    )
    return RemediationPlanOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/accept",
    response_model=InstanceDetailOut,
    summary="Accept the risk (a recorded, expiring waiver)",
)
async def accept(
    instance_id: uuid.UUID,
    body: AcceptRequest,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_accept)],
) -> InstanceDetailOut:
    view = await vulnerability_service.accept_instance(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        reason=body.reason,
        expires_at=body.expires_at,
        compensating_controls=body.compensating_controls,
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/exception",
    response_model=InstanceDetailOut,
    summary="Request a risk exception on this finding",
)
async def request_exception(
    instance_id: uuid.UUID,
    body: ExceptionRequestIn,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_manage)],
) -> InstanceDetailOut:
    """Raising a request needs only ``vulnerabilities:manage`` — anyone working
    the finding can make the case. Granting it is the privileged step."""
    view = await vulnerability_service.request_exception(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        request=ExceptionRequest(
            duration_days=body.duration_days,
            rationale=body.rationale,
            potential_risks=body.potential_risks,
            compensating_controls=body.compensating_controls,
        ),
    )
    return InstanceDetailOut.model_validate(view)


@vulnerabilities_router.post(
    "/{instance_id}/exception/decide",
    response_model=InstanceDetailOut,
    summary="Approve or reject the open risk exception",
)
async def decide_exception(
    instance_id: uuid.UUID,
    body: ExceptionDecisionIn,
    context: _Ctx,
    session: _Db,
    principal: Annotated[Principal, Depends(require_accept)],
) -> InstanceDetailOut:
    """Deciding is the waiver itself, so it needs ``vulnerabilities:accept``.
    The service refuses a decision from whoever raised the request."""
    view = await vulnerability_service.decide_exception(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(principal),
        instance_id=instance_id,
        approve=body.approve,
        note=body.note,
    )
    return InstanceDetailOut.model_validate(view)
