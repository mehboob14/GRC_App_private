"""Frameworks a workspace runs: the catalogue as this workspace sees it, the overlap
preview, adding a framework, and the Statement of Applicability.

There is one control library. A framework is a view over it: each requirement points at the
controls that answer it. Adding a second framework therefore adopts only the controls that
framework needs and links the controls the workspace already runs to its requirements, in
one audited step, so evidence collected once counts everywhere the control is mapped.

Nothing here infers one framework's status from another's (CF-5). A requirement is met when
the controls mapped to it are ready, by the same rules as the dashboard, wherever those
controls also appear.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.modules.compliance.control_service import control_service
from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.models import (
    Control,
    ControlRequirement,
    ControlTemplate,
    Framework,
    FrameworkVersion,
    FrameworkVersionRequirement,
    Requirement,
    RequirementApplicability,
    TemplateRequirementMap,
    TenantFramework,
    natural_key,
)
from verity.modules.compliance.readiness import BUILT_IN_SOURCE, control_ready, requirement_ready
from verity.modules.compliance.service import compliance_service
from verity.modules.compliance.soa_export import build_soa_workbook
from verity.shared.ids import uuid7

_APPLICABILITY_SNAPSHOT: Final = (
    "applicable",
    "justification",
    "provided_by",
    "owner_membership_id",
    "reviewed_at",
)

_STARTED: Final = frozenset({"in_progress", "implemented"})

_IMPLEMENTATION_LABEL: Final = {
    "excluded": "Excluded",
    "met": "Implemented",
    "partly": "In progress",
    "not_started": "Not started",
    "no_controls": "No control",
}


# -- views ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DecisionFact:
    """One requirement's Statement of Applicability decision, for the built-in checks.
    No row recorded reads as applicable and never reviewed, as on the statement page."""

    requirement_id: uuid.UUID
    code: str
    name: str
    locked: bool
    applicable: bool
    justification: str | None
    provided_by: str
    owner_membership_id: uuid.UUID | None
    reviewed_at: datetime | None


@dataclass(frozen=True, slots=True)
class TenantFrameworkView:
    framework_id: uuid.UUID
    code: str
    name: str
    description: str | None
    scope_model: str
    position: int
    version_id: uuid.UUID | None
    version: str | None
    requirement_count: int
    added: bool
    added_at: datetime | None


@dataclass(frozen=True, slots=True)
class OverlapGroup:
    group: str
    total: int
    covered: int
    partly: int
    needs_new: int
    no_control: int


@dataclass(frozen=True, slots=True)
class OverlapControl:
    code: str
    name: str
    category: str


@dataclass(frozen=True, slots=True)
class OverlapView:
    framework_id: uuid.UUID
    code: str
    name: str
    version: str
    added: bool
    requirements_total: int
    covered: int
    partly: int
    needs_new: int
    no_control: int
    controls_in_use: int
    controls_to_adopt: list[OverlapControl]
    groups: list[OverlapGroup]


@dataclass(frozen=True, slots=True)
class AddedView:
    framework: TenantFrameworkView
    controls_adopted: int
    links_created: int


@dataclass(frozen=True, slots=True)
class ApplicabilityControl:
    control_id: uuid.UUID
    code: str
    name: str
    status: str
    ready: bool
    coverage: str | None


@dataclass(frozen=True, slots=True)
class ApplicabilityRow:
    requirement_id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    description: str | None
    category: str
    locked: bool
    applicable: bool
    justification: str | None
    provided_by: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    reviewed_at: datetime | None
    state: str
    controls: list[ApplicabilityControl] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ApplicabilitySummary:
    total: int
    applicable: int
    excluded: int
    reviewed: int
    met: int
    partly: int
    not_started: int
    no_controls: int


@dataclass(frozen=True, slots=True)
class StatementView:
    framework_id: uuid.UUID
    code: str
    name: str
    version: str
    scope_statement: str | None
    summary: ApplicabilitySummary
    rows: list[ApplicabilityRow]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class FrameworkService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- the catalogue as this workspace sees it ------------------------------------

    async def list_for_tenant(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[TenantFrameworkView]:
        catalogue = await compliance_service.list_frameworks(session)
        held = {
            row.framework_id: row
            for row in (
                await session.execute(
                    select(TenantFramework).where(TenantFramework.tenant_id == tenant_id)
                )
            ).scalars()
        }
        out: list[TenantFrameworkView] = []
        for framework in catalogue:
            current = next((v for v in framework.versions if v.is_current), None)
            row = held.get(framework.id)
            held_row = row if row is not None and row.status == "active" else None
            active = held_row is not None
            shown = current
            if held_row is not None:
                shown = next(
                    (v for v in framework.versions if v.id == held_row.framework_version_id),
                    current,
                )
            out.append(
                TenantFrameworkView(
                    framework_id=framework.id,
                    code=framework.code,
                    name=framework.name,
                    description=framework.description,
                    scope_model=framework.scope_model,
                    position=framework.position,
                    version_id=shown.id if shown else None,
                    version=shown.version if shown else None,
                    requirement_count=shown.requirement_count if shown else 0,
                    added=active,
                    added_at=held_row.created_at if held_row is not None else None,
                )
            )
        return out

    async def _framework(self, session: AsyncSession, framework_id: uuid.UUID) -> Framework:
        framework = await session.get(Framework, framework_id)
        if framework is None:
            raise NotFound(
                "That framework is not available here.", detail=f"framework {framework_id}"
            )
        return framework

    async def _current_version(
        self, session: AsyncSession, framework: Framework
    ) -> FrameworkVersion:
        version = (
            await session.execute(
                select(FrameworkVersion).where(
                    FrameworkVersion.framework_id == framework.id,
                    FrameworkVersion.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise NotFound(
                f"{framework.name} has no published version yet.",
                detail=f"no current version for framework {framework.id}",
            )
        return version

    async def _requirements(
        self, session: AsyncSession, version: FrameworkVersion
    ) -> list[Requirement]:
        rows = await session.execute(
            select(Requirement)
            .join(
                FrameworkVersionRequirement,
                FrameworkVersionRequirement.requirement_id == Requirement.id,
            )
            .where(FrameworkVersionRequirement.framework_version_id == version.id)
        )
        return sorted(rows.scalars(), key=lambda r: natural_key(r.code))

    # -- the overlap preview --------------------------------------------------------

    async def overlap(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_id: uuid.UUID
    ) -> OverlapView:
        """What adding a framework would mean here, counted from what the workspace runs now."""
        framework = await self._framework(session, framework_id)
        version = await self._current_version(session, framework)
        requirements = await self._requirements(session, version)
        ids = [r.id for r in requirements]

        edges = (
            await session.execute(
                select(
                    TemplateRequirementMap.requirement_id,
                    TemplateRequirementMap.template_id,
                    TemplateRequirementMap.coverage,
                ).where(TemplateRequirementMap.requirement_id.in_(ids))
            )
        ).all()
        adopted = set(
            (
                await session.execute(
                    select(Control.template_id).where(
                        Control.tenant_id == tenant_id,
                        Control.disabled_at.is_(None),
                        Control.template_id.is_not(None),
                    )
                )
            ).scalars()
        )
        template_ids = {template_id for _req, template_id, _cov in edges}
        templates = {
            t.id: t
            for t in (
                await session.execute(
                    select(ControlTemplate).where(ControlTemplate.id.in_(template_ids))
                )
            ).scalars()
        }
        by_requirement: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = defaultdict(list)
        for requirement_id, template_id, coverage in edges:
            by_requirement[requirement_id].append((template_id, coverage))

        added = (
            await session.execute(
                select(TenantFramework.id).where(
                    TenantFramework.tenant_id == tenant_id,
                    TenantFramework.framework_id == framework.id,
                    TenantFramework.status == "active",
                )
            )
        ).first() is not None

        totals = {"covered": 0, "partly": 0, "needs_new": 0, "no_control": 0}
        groups: dict[str, dict[str, int]] = {}
        for requirement in requirements:
            options = by_requirement.get(requirement.id, [])
            running = [(t, c) for t, c in options if t in adopted]
            if not options:
                state = "no_control"
            elif not running:
                state = "needs_new"
            elif any(c == "full" for _t, c in running):
                state = "covered"
            else:
                state = "partly"
            totals[state] += 1
            bucket = groups.setdefault(
                requirement.category,
                {"total": 0, "covered": 0, "partly": 0, "needs_new": 0, "no_control": 0},
            )
            bucket["total"] += 1
            bucket[state] += 1

        to_adopt = sorted(
            (templates[t] for t in template_ids if t not in adopted and t in templates),
            key=lambda t: natural_key(t.code),
        )
        return OverlapView(
            framework_id=framework.id,
            code=framework.code,
            name=framework.name,
            version=version.version,
            added=added,
            requirements_total=len(requirements),
            covered=totals["covered"],
            partly=totals["partly"],
            needs_new=totals["needs_new"],
            no_control=totals["no_control"],
            controls_in_use=len(template_ids & adopted),
            controls_to_adopt=[OverlapControl(t.code, t.name, t.category) for t in to_adopt],
            groups=[OverlapGroup(group=name, **counts) for name, counts in groups.items()],
        )

    # -- adding a framework ---------------------------------------------------------

    async def add(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_id: uuid.UUID,
    ) -> AddedView:
        """Add a framework: adopt the controls it needs, link the ones already running.

        One transaction, audited. Idempotent: adding a framework twice changes nothing the
        second time. Nothing already in the library is changed or removed.
        """
        framework = await self._framework(session, framework_id)
        version = await self._current_version(session, framework)
        row = (
            await session.execute(
                select(TenantFramework).where(
                    TenantFramework.tenant_id == tenant_id,
                    TenantFramework.framework_id == framework.id,
                )
            )
        ).scalar_one_or_none()
        if row is not None and row.status == "active":
            return AddedView(await self._view_of(session, tenant_id, framework), 0, 0)

        if row is None:
            row = TenantFramework(
                id=uuid7(),
                tenant_id=tenant_id,
                framework_id=framework.id,
                framework_version_id=version.id,
                status="active",
                activated_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            )
            session.add(row)
        else:
            row.status = "active"
            row.framework_version_id = version.id
        await session.flush([row])

        requirement_ids = [r.id for r in await self._requirements(session, version)]
        adoption = await control_service.instantiate_library(
            session, tenant_id=tenant_id, actor=actor, requirement_ids=requirement_ids
        )
        links = await control_service.link_framework(
            session, tenant_id=tenant_id, framework_id=framework.id
        )
        await self._audit.record(
            session,
            action="create",
            object_type="tenant_framework",
            object_id=row.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "framework": framework.code,
                "version": version.version,
                "status": "active",
                "controls_adopted": adoption.created,
                "links_created": adoption.mappings_created + links,
            },
        )
        return AddedView(
            await self._view_of(session, tenant_id, framework),
            adoption.created,
            adoption.mappings_created + links,
        )

    async def _view_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, framework: Framework
    ) -> TenantFrameworkView:
        for view in await self.list_for_tenant(session, tenant_id=tenant_id):
            if view.framework_id == framework.id:
                return view
        raise NotFound("That framework is not available here.", detail=str(framework.id))

    # -- the Statement of Applicability ---------------------------------------------

    async def applicability_decisions(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_code: str
    ) -> tuple[uuid.UUID, str, list[DecisionFact]] | None:
        """The decisions behind a framework's Statement of Applicability, without the
        readiness work ``statement`` does. None when the workspace has not added the
        framework or the framework is not decided by applicability. Read only."""
        framework = (
            await session.execute(select(Framework).where(Framework.code == framework_code))
        ).scalar_one_or_none()
        if framework is None or framework.scope_model != "applicability":
            return None
        held = (
            await session.execute(
                select(TenantFramework).where(
                    TenantFramework.tenant_id == tenant_id,
                    TenantFramework.framework_id == framework.id,
                    TenantFramework.status == "active",
                )
            )
        ).scalar_one_or_none()
        if held is None:
            return None
        version = await session.get(FrameworkVersion, held.framework_version_id)
        if version is None:
            return None
        requirements = await self._requirements(session, version)
        decisions = {
            row.requirement_id: row
            for row in (
                await session.execute(
                    select(RequirementApplicability).where(
                        RequirementApplicability.tenant_id == tenant_id
                    )
                )
            ).scalars()
        }
        rows: list[DecisionFact] = []
        for requirement in requirements:
            decision = decisions.get(requirement.id)
            rows.append(
                DecisionFact(
                    requirement_id=requirement.id,
                    code=requirement.code,
                    name=requirement.name,
                    locked=requirement.is_always_in_scope,
                    applicable=decision.applicable if decision else True,
                    justification=decision.justification if decision else None,
                    provided_by=decision.provided_by if decision else "organization",
                    owner_membership_id=decision.owner_membership_id if decision else None,
                    reviewed_at=decision.reviewed_at if decision else None,
                )
            )
        return framework.id, framework.name, rows

    async def _statement_context(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_id: uuid.UUID
    ) -> tuple[Framework, FrameworkVersion]:
        framework = await self._framework(session, framework_id)
        if framework.scope_model != "applicability":
            raise InvalidInput(
                f"{framework.name} does not use a Statement of Applicability.",
                detail=f"scope model {framework.scope_model!r}",
            )
        held = (
            await session.execute(
                select(TenantFramework).where(
                    TenantFramework.tenant_id == tenant_id,
                    TenantFramework.framework_id == framework.id,
                    TenantFramework.status == "active",
                )
            )
        ).scalar_one_or_none()
        if held is None:
            raise Conflict(
                f"Add {framework.name} to your workspace first.",
                detail=f"statement of applicability before {framework.code} was added",
            )
        version = await session.get(FrameworkVersion, held.framework_version_id)
        assert version is not None  # noqa: S101 — the foreign key guarantees it
        return framework, version

    async def statement(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_id: uuid.UUID
    ) -> StatementView:
        """Every requirement with the workspace's decision and what is behind it."""
        # Both services answer to this module: connectors and evidence read compliance
        # for their controls, so they are imported where they are used.
        from verity.modules.connectors.service import connector_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        framework, version = await self._statement_context(
            session, tenant_id=tenant_id, framework_id=framework_id
        )
        requirements = await self._requirements(session, version)
        ids = [r.id for r in requirements]
        decisions = {
            row.requirement_id: row
            for row in (
                await session.execute(
                    select(RequirementApplicability).where(
                        RequirementApplicability.tenant_id == tenant_id
                    )
                )
            ).scalars()
        }
        linked = (
            await session.execute(
                select(ControlRequirement.requirement_id, Control)
                .join(Control, Control.id == ControlRequirement.control_id)
                .where(
                    ControlRequirement.tenant_id == tenant_id,
                    ControlRequirement.requirement_id.in_(ids),
                    Control.disabled_at.is_(None),
                )
                .order_by(Control.code)
            )
        ).all()
        coverage = {
            (template_id, requirement_id): value
            for template_id, requirement_id, value in (
                await session.execute(
                    select(
                        TemplateRequirementMap.template_id,
                        TemplateRequirementMap.requirement_id,
                        TemplateRequirementMap.coverage,
                    ).where(TemplateRequirementMap.requirement_id.in_(ids))
                )
            ).all()
        }
        with_current = await evidence_service.control_ids_with_current_evidence(
            session, tenant_id, exclude_source=BUILT_IN_SOURCE
        )
        automation = await connector_service.automation_statuses(session, tenant_id=tenant_id)
        names = {
            m.membership_id: m.full_name
            for m in await iam_service.list_members(session, tenant_id=tenant_id)
        }
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code=framework.code
        )

        by_requirement: dict[uuid.UUID, list[ApplicabilityControl]] = defaultdict(list)
        for requirement_id, control in linked:
            by_requirement[requirement_id].append(
                ApplicabilityControl(
                    control_id=control.id,
                    code=control.code,
                    name=control.name,
                    status=control.status,
                    ready=control_ready(
                        status=control.status,
                        has_current_evidence=control.id in with_current,
                        automation=automation.get(control.id),
                    ),
                    coverage=coverage.get((control.template_id, requirement_id)),
                )
            )

        rows: list[ApplicabilityRow] = []
        for requirement in requirements:
            decision = decisions.get(requirement.id)
            applicable = decision.applicable if decision else True
            controls = by_requirement.get(requirement.id, [])
            if not applicable:
                state = "excluded"
            elif not controls:
                state = "no_controls"
            elif requirement_ready((c.status, c.ready) for c in controls):
                state = "met"
            elif any(c.ready or c.status in _STARTED for c in controls):
                # Work under way counts, not only finished-and-evidenced work: a control
                # marked implemented that still lacks evidence is not "not started".
                state = "partly"
            else:
                state = "not_started"
            owner_id = decision.owner_membership_id if decision else None
            rows.append(
                ApplicabilityRow(
                    requirement_id=requirement.id,
                    requirement_key=requirement.requirement_key,
                    code=requirement.code,
                    name=requirement.name,
                    description=requirement.description,
                    category=requirement.category,
                    locked=requirement.is_always_in_scope,
                    applicable=applicable,
                    justification=decision.justification if decision else None,
                    provided_by=decision.provided_by if decision else "organization",
                    owner_membership_id=owner_id,
                    owner_name=names.get(owner_id) if owner_id else None,
                    reviewed_at=decision.reviewed_at if decision else None,
                    state=state,
                    controls=controls,
                )
            )
        summary = ApplicabilitySummary(
            total=len(rows),
            applicable=sum(1 for r in rows if r.applicable),
            excluded=sum(1 for r in rows if not r.applicable),
            reviewed=sum(1 for r in rows if r.reviewed_at is not None),
            met=sum(1 for r in rows if r.state == "met"),
            partly=sum(1 for r in rows if r.state == "partly"),
            not_started=sum(1 for r in rows if r.state == "not_started"),
            no_controls=sum(1 for r in rows if r.state == "no_controls"),
        )
        return StatementView(
            framework_id=framework.id,
            code=framework.code,
            name=framework.name,
            version=version.version,
            scope_statement=engagement.scope_statement if engagement else None,
            summary=summary,
            rows=rows,
        )

    async def set_applicability(  # noqa: PLR0913 — one argument per field of the decision
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        framework_id: uuid.UUID,
        requirement_id: uuid.UUID,
        applicable: bool,
        justification: str | None,
        provided_by: str,
        owner_membership_id: uuid.UUID | None,
        reviewed: bool,
    ) -> ApplicabilityRow:
        """Record the workspace's decision about one requirement.

        Excluding needs a reason, and a requirement the framework marks always in scope
        (the management system clauses) cannot be excluded. Exclusion is per requirement:
        it never touches a control, so the same control keeps working for any other
        framework it serves.
        """
        framework, version = await self._statement_context(
            session, tenant_id=tenant_id, framework_id=framework_id
        )
        requirement = await session.get(Requirement, requirement_id)
        member = (
            await session.execute(
                select(FrameworkVersionRequirement.requirement_id).where(
                    FrameworkVersionRequirement.framework_version_id == version.id,
                    FrameworkVersionRequirement.requirement_id == requirement_id,
                )
            )
        ).first()
        if requirement is None or member is None:
            raise NotFound(
                f"That requirement is not part of {framework.name}.",
                detail=f"requirement {requirement_id} not in framework {framework.code}",
            )
        reason = _clean(justification)
        if not applicable:
            if requirement.is_always_in_scope:
                raise InvalidInput(
                    "This requirement applies to every management system and cannot be excluded.",
                    detail=f"exclusion of {requirement.requirement_key}, always in scope",
                )
            if reason is None:
                raise InvalidInput(
                    "Say why this requirement does not apply. The reason goes on the statement.",
                    detail="exclusion without a justification",
                )
        if owner_membership_id is not None:
            from verity.modules.iam.service import iam_service  # noqa: PLC0415

            members = {
                m.membership_id
                for m in await iam_service.list_members(session, tenant_id=tenant_id)
            }
            if owner_membership_id not in members:
                raise InvalidInput(
                    "Choose an owner from this workspace's members.",
                    detail=f"owner {owner_membership_id} is not a member",
                )

        row = (
            await session.execute(
                select(RequirementApplicability).where(
                    RequirementApplicability.tenant_id == tenant_id,
                    RequirementApplicability.requirement_id == requirement_id,
                )
            )
        ).scalar_one_or_none()
        before = AuditService.snapshot(row, fields=_APPLICABILITY_SNAPSHOT) if row else None
        changed = row is not None and (
            row.applicable != applicable
            or (row.justification or None) != reason
            or row.provided_by != provided_by
        )
        # A decision changed without being marked reviewed has not been reviewed: keeping
        # the old stamp would show a new decision as reviewed on a date before it existed.
        if reviewed:
            stamp: datetime | None = datetime.now(UTC)
        elif row is None or changed:
            stamp = None
        else:
            stamp = row.reviewed_at
        if row is None:
            row = RequirementApplicability(
                id=uuid7(),
                tenant_id=tenant_id,
                requirement_id=requirement_id,
                applicable=applicable,
                justification=reason,
                provided_by=provided_by,
                owner_membership_id=owner_membership_id,
                reviewed_at=stamp,
            )
            session.add(row)
        else:
            row.applicable = applicable
            row.justification = reason
            row.provided_by = provided_by
            row.owner_membership_id = owner_membership_id
            row.reviewed_at = stamp
        await session.flush([row])
        after: dict[str, Any] = AuditService.snapshot(row, fields=_APPLICABILITY_SNAPSHOT)
        if after != before:
            await self._audit.record(
                session,
                action="create" if before is None else "update",
                object_type="requirement_applicability",
                object_id=row.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after={**after, "requirement": requirement.requirement_key},
            )
        statement = await self.statement(session, tenant_id=tenant_id, framework_id=framework_id)
        return next(r for r in statement.rows if r.requirement_id == requirement_id)

    async def statement_workbook(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, framework_id: uuid.UUID
    ) -> tuple[bytes, str]:
        """The Statement of Applicability as XLSX, and the file name to offer."""
        statement = await self.statement(session, tenant_id=tenant_id, framework_id=framework_id)
        rows = [
            {
                "reference": row.code,
                "title": row.name,
                "section": row.category,
                "applicable": "Yes" if row.applicable else "No",
                "justification": row.justification or "",
                "provided_by": "Supplier" if row.provided_by == "supplier" else "Organization",
                "implementation": _IMPLEMENTATION_LABEL[row.state],
                "controls": ", ".join(c.code for c in row.controls),
                "owner": row.owner_name or "",
                "reviewed": row.reviewed_at.date().isoformat() if row.reviewed_at else "",
            }
            for row in statement.rows
        ]
        today = datetime.now(UTC).date()
        data = build_soa_workbook(
            framework_name=statement.name,
            version=statement.version,
            scope_statement=statement.scope_statement,
            generated_on=today,
            rows=rows,
        )
        return data, f"statement-of-applicability-{statement.code.lower()}-{today.isoformat()}.xlsx"


framework_service = FrameworkService()
