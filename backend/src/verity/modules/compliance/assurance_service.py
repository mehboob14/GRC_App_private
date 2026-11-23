"""Assurance records: internal audits, management reviews, outside audit stages, and reports or
certificates the company already holds (guided onboarding EN-9, EN-10, CN-5, EX-2, EX-4).

A finding raises a corrective action task through the tasks service, keyed on
``(assurance, finding id)``. The task carries the work; the finding keeps what was found, the
response, the closure evidence and, for an outside body, when it verified the fix. A major or
minor finding cannot close without closure evidence. Records are closed, never deleted.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.models import (
    ASSURANCE_KINDS,
    ASSURANCE_STATUSES,
    FINDING_GRADES,
    AssuranceFinding,
    AssuranceRecord,
)
from verity.shared.ids import uuid7

SOURCE: Final = "assurance"
_RECORD_FIELDS: Final = (
    "kind",
    "label",
    "starts_on",
    "ends_on",
    "performed_by_membership_id",
    "performed_by_name",
    "performed_by_firm",
    "independence_confirmed_by_membership_id",
    "scope_note",
    "document_id",
    "inputs",
    "status",
)
_FINDING_FIELDS: Final = (
    "grade",
    "summary",
    "due_on",
    "owner_membership_id",
    "response",
    "closed_on",
    "closure_evidence_id",
    "verified_on",
)
_LABELS: Final[dict[str, str]] = {
    "internal_audit": "Internal audit",
    "management_review": "Management review",
    "external_stage": "Audit",
    "prior_report": "Past report",
    "prior_certificate": "Certificate",
}
MANAGEMENT_REVIEW_INPUTS: Final[tuple[str, ...]] = (
    "Status of actions from previous reviews",
    "Changes in internal and external issues",
    "Changes in needs and expectations of interested parties",
    "Nonconformities and corrective actions",
    "Monitoring and measurement results",
    "Audit results",
    "Fulfilment of information security objectives",
    "Feedback from interested parties",
    "Results of risk assessment and status of the risk treatment plan",
    "Opportunities for continual improvement",
)
"""ISO/IEC 27001 clause 9.3.2, in our own words."""


@dataclass(frozen=True, slots=True)
class FindingView:
    id: uuid.UUID
    grade: str
    summary: str
    due_on: date | None
    owner_membership_id: uuid.UUID | None
    response: str | None
    task_id: uuid.UUID | None
    closed_on: date | None
    closure_evidence_id: uuid.UUID | None
    verified_on: date | None
    overdue: bool


@dataclass(frozen=True, slots=True)
class RecordView:
    id: uuid.UUID
    kind: str
    label: str
    starts_on: date | None
    ends_on: date | None
    performed_by_membership_id: uuid.UUID | None
    performed_by_name: str | None
    performed_by_firm: str | None
    independence_confirmed_by_membership_id: uuid.UUID | None
    scope_note: str | None
    document_id: uuid.UUID | None
    inputs: dict[str, Any]
    status: str
    findings: list[FindingView] = field(default_factory=list)
    notice: str | None = None


@dataclass(frozen=True, slots=True)
class AssuranceSummary:
    """What Get Started reads (steps 21 to 24)."""

    internal_audit_reported: bool
    review_minuted: bool
    findings_open: int
    findings_overdue: int
    audit_recorded: bool
    majors_unverified: int


def _finding_view(f: AssuranceFinding, today: date) -> FindingView:
    return FindingView(
        id=f.id,
        grade=f.grade,
        summary=f.summary,
        due_on=f.due_on,
        owner_membership_id=f.owner_membership_id,
        response=f.response,
        task_id=f.task_id,
        closed_on=f.closed_on,
        closure_evidence_id=f.closure_evidence_id,
        verified_on=f.verified_on,
        overdue=f.closed_on is None and f.due_on is not None and f.due_on < today,
    )


class AssuranceService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    async def _engagement_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, framework_code: str
    ) -> uuid.UUID:
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        if engagement is None:
            raise Conflict(
                "Set up this framework's audit first, then record against it.",
                detail=f"no engagement for {framework_code}",
            )
        return engagement.id

    async def _records(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_ids: list[uuid.UUID]
    ) -> list[RecordView]:
        if not engagement_ids:
            return []
        records = list(
            (
                await session.execute(
                    select(AssuranceRecord)
                    .where(
                        AssuranceRecord.tenant_id == tenant_id,
                        AssuranceRecord.engagement_id.in_(engagement_ids),
                    )
                    .order_by(
                        AssuranceRecord.starts_on.desc().nulls_last(), AssuranceRecord.created_at
                    )
                )
            ).scalars()
        )
        findings: dict[uuid.UUID, list[AssuranceFinding]] = {}
        if records:
            for f in (
                await session.execute(
                    select(AssuranceFinding)
                    .where(
                        AssuranceFinding.tenant_id == tenant_id,
                        AssuranceFinding.record_id.in_([r.id for r in records]),
                    )
                    .order_by(AssuranceFinding.created_at)
                )
            ).scalars():
                findings.setdefault(f.record_id, []).append(f)
        today = datetime.now(UTC).date()
        return [
            RecordView(
                **{k: getattr(r, k) for k in ("id", *_RECORD_FIELDS)},
                findings=[_finding_view(f, today) for f in findings.get(r.id, [])],
            )
            for r in records
        ]

    async def records(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> list[RecordView]:
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework_code
        )
        return await self._records(session, tenant_id, [engagement.id] if engagement else [])

    @staticmethod
    def _check(values: dict[str, Any]) -> None:
        if values.get("kind") not in ASSURANCE_KINDS:
            raise InvalidInput(
                "Choose what kind of record this is.", detail=str(values.get("kind"))
            )
        if values.get("status") not in ASSURANCE_STATUSES:
            raise InvalidInput("Choose planned, held or closed.", detail=str(values.get("status")))
        if values.get("performed_by_membership_id") and values.get("performed_by_name"):
            raise InvalidInput(
                "Name a member or an outside person, not both.", detail="two performers"
            )
        starts, ends = values.get("starts_on"), values.get("ends_on")
        if starts and ends and ends < starts:
            raise InvalidInput("The end date falls before the start date.", detail="dates")

    async def save_record(  # noqa: PLR0913 — who, where, which record and its fields
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_code: str,
        record_id: uuid.UUID | None,
        values: dict[str, Any],
    ) -> RecordView:
        engagement_id = await self._engagement_id(session, tenant_id, framework_code)
        values = {k: v for k, v in values.items() if k in _RECORD_FIELDS}
        values["label"] = (values.get("label") or "").strip() or _LABELS.get(
            str(values.get("kind")), "Record"
        )
        values.setdefault("status", "planned")
        values.setdefault("inputs", {})
        for key in ("performed_by_name", "performed_by_firm", "scope_note"):
            if key in values:
                values[key] = (values[key] or "").strip() or None
        self._check(values)
        if record_id is None:
            row = AssuranceRecord(id=uuid7(), tenant_id=tenant_id, engagement_id=engagement_id)
            session.add(row)
            before = None
        else:
            row = await self._record(session, tenant_id, record_id)
            before = AuditService.snapshot(row, fields=_RECORD_FIELDS)
        for key, value in values.items():
            setattr(row, key, value)
        await session.flush([row])
        await self._audit.record(
            session,
            action="create" if before is None else "update",
            object_type="assurance_record",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(row, fields=_RECORD_FIELDS),
        )
        notice = None
        if row.kind == "prior_certificate":
            notice = await engagement_service.plan_from_certificate(
                session,
                tenant_id=tenant_id,
                actor=actor,
                framework_code=framework_code,
                issued_on=row.starts_on,
                expires_on=row.ends_on,
            )
        view = next(
            r for r in await self._records(session, tenant_id, [engagement_id]) if r.id == row.id
        )
        return replace(view, notice=notice)

    async def _record(
        self, session: AsyncSession, tenant_id: uuid.UUID, record_id: uuid.UUID
    ) -> AssuranceRecord:
        row = await session.get(AssuranceRecord, record_id)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound("That record does not exist.", detail=str(record_id))
        return row

    async def add_finding(  # noqa: PLR0913 — who, which record and the finding's fields
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        record_id: uuid.UUID,
        grade: str,
        summary: str,
        due_on: date | None,
        owner_membership_id: uuid.UUID | None,
    ) -> FindingView:
        """Record a finding and raise its corrective action task (EN-9, EX-4)."""
        from verity.modules.tasks.service import PlannedTask, task_service  # noqa: PLC0415

        record = await self._record(session, tenant_id, record_id)
        if grade not in FINDING_GRADES:
            raise InvalidInput("Choose the grade the auditor gave.", detail=grade)
        if not summary.strip():
            raise InvalidInput("Say what was found.", detail="empty finding")
        row = AssuranceFinding(
            id=uuid7(),
            tenant_id=tenant_id,
            record_id=record.id,
            grade=grade,
            summary=summary.strip(),
            due_on=due_on,
            owner_membership_id=owner_membership_id,
        )
        session.add(row)
        await session.flush([row])
        await task_service.raise_planned(
            session,
            tenant_id=tenant_id,
            actor=actor,
            source=SOURCE,
            items=[
                PlannedTask(
                    key=str(row.id),
                    title=f"Fix finding from {record.label}: {row.summary}"[:300],
                    description=f"Grade: {grade}. Raised from {record.label}.",
                    owner_membership_id=owner_membership_id,
                    due_at=datetime.combine(due_on, time.min, tzinfo=UTC) if due_on else None,
                    control_id=None,
                )
            ],
        )
        made = await task_service.task_ids_for_keys(
            session, tenant_id=tenant_id, source=SOURCE, keys=[str(row.id)]
        )
        row.task_id = made.get(str(row.id))
        await session.flush([row])
        await self._audit.record(
            session,
            action="create",
            object_type="assurance_finding",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            after={
                **AuditService.snapshot(row, fields=_FINDING_FIELDS),
                "record_id": str(record.id),
            },
        )
        return _finding_view(row, datetime.now(UTC).date())

    async def update_finding(  # noqa: PLR0913 — who, which finding and what changed
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        membership_id: uuid.UUID,
        finding_id: uuid.UUID,
        response: str | None,
        closed_on: date | None,
        closure_evidence_id: uuid.UUID | None,
        verified_on: date | None,
    ) -> FindingView:
        row = await session.get(AssuranceFinding, finding_id)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound("That finding does not exist.", detail=str(finding_id))
        before = AuditService.snapshot(row, fields=_FINDING_FIELDS)
        if response is not None:
            row.response = response.strip() or None
        if closure_evidence_id is not None:
            row.closure_evidence_id = closure_evidence_id
        if closed_on is not None:
            if row.grade in {"major", "minor", "exception"} and row.closure_evidence_id is None:
                raise InvalidInput(
                    "Attach the evidence that shows the fix before closing this finding.",
                    detail="closing a graded finding without evidence",
                )
            row.closed_on = closed_on
        if verified_on is not None:
            if row.closed_on is None:
                raise InvalidInput("Close the finding before marking it verified.", detail="verify")
            row.verified_on = verified_on
            row.verified_by_membership_id = membership_id
        await session.flush([row])
        await self._audit.record(
            session,
            action="update",
            object_type="assurance_finding",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(row, fields=_FINDING_FIELDS),
        )
        return _finding_view(row, datetime.now(UTC).date())

    async def summary(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> AssuranceSummary:
        """One framework's records, as Get Started's check and audit steps read them."""
        records = await self.records(session, tenant_id=tenant_id, framework_code=framework_code)
        findings = [f for r in records for f in r.findings]
        return AssuranceSummary(
            internal_audit_reported=any(
                r.kind == "internal_audit" and r.document_id is not None for r in records
            ),
            review_minuted=any(
                r.kind == "management_review" and r.document_id is not None for r in records
            ),
            findings_open=sum(1 for f in findings if f.closed_on is None),
            findings_overdue=sum(1 for f in findings if f.overdue),
            audit_recorded=any(r.kind == "external_stage" and r.starts_on for r in records),
            majors_unverified=sum(
                1 for f in findings if f.grade == "major" and f.verified_on is None
            ),
        )


assurance_service = AssuranceService()
