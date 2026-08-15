"""Compliance reads over shipped global content.

Read-only in this change: nothing here mutates state, so nothing writes an
audit row. When the tenant control library lands, the write paths join this
module and every one of them records its actor.

No HTTP types cross this boundary — the router translates. Missing rows raise
``NotFound`` from ``core.errors``, which the one exception handler turns into a
404 with a stable code.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import NotFound
from verity.modules.compliance.models import (
    ControlTemplate,
    Framework,
    FrameworkVersion,
    Requirement,
)
from verity.modules.compliance.repository import (
    ControlTemplateRepository,
    FrameworkRepository,
    RequirementRepository,
)


@dataclass(frozen=True, slots=True)
class FrameworkVersionView:
    id: uuid.UUID
    version: str
    published_at: datetime
    is_current: bool
    requirement_count: int


@dataclass(frozen=True, slots=True)
class FrameworkView:
    """A framework with its versions and each version's requirement count."""

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    built_in: bool
    versions: list[FrameworkVersionView]

    @classmethod
    def of(
        cls, framework: Framework, versions: Sequence[tuple[FrameworkVersion, int]]
    ) -> FrameworkView:
        return cls(
            id=framework.id,
            code=framework.code,
            name=framework.name,
            description=framework.description,
            built_in=framework.built_in,
            versions=[
                FrameworkVersionView(
                    id=version.id,
                    version=version.version,
                    published_at=version.published_at,
                    is_current=version.is_current,
                    requirement_count=count,
                )
                for version, count in versions
            ],
        )


class RequirementView:
    """A requirement plus how many shipped templates satisfy it."""

    def __init__(self, requirement: Requirement, template_count: int) -> None:
        self.id = requirement.id
        self.requirement_key = requirement.requirement_key
        self.code = requirement.code
        self.name = requirement.name
        self.description = requirement.description
        self.category = requirement.category
        self.trust_services_category = requirement.trust_services_category
        self.is_always_in_scope = requirement.is_always_in_scope
        self.template_count = template_count


class TemplateDetailView:
    def __init__(self, template: ControlTemplate, requirements: list[RequirementView]) -> None:
        for field in (
            "id",
            "code",
            "canonical_key",
            "name",
            "description",
            "implementation_guidance",
            "category",
            "control_type",
            "control_sub_type",
            "importance",
            "built_in",
        ):
            setattr(self, field, getattr(template, field))
        self.requirements = requirements


class ComplianceService:
    def __init__(
        self,
        frameworks: FrameworkRepository | None = None,
        requirements: RequirementRepository | None = None,
        templates: ControlTemplateRepository | None = None,
    ) -> None:
        self._frameworks = frameworks or FrameworkRepository()
        self._requirements = requirements or RequirementRepository()
        self._templates = templates or ControlTemplateRepository()

    async def list_frameworks(self, session: AsyncSession) -> list[FrameworkView]:
        frameworks = await self._frameworks.list_frameworks(session)
        versions = await self._frameworks.list_versions(session)
        counts = await self._frameworks.requirement_counts_by_version(session)
        by_framework: dict[uuid.UUID, list[tuple[FrameworkVersion, int]]] = {}
        for version in versions:
            by_framework.setdefault(version.framework_id, []).append(
                (version, counts.get(version.id, 0))
            )
        return [
            FrameworkView.of(framework, by_framework.get(framework.id, []))
            for framework in frameworks
        ]

    async def list_requirements(
        self,
        session: AsyncSession,
        *,
        framework_id: uuid.UUID,
        version_id: uuid.UUID | None = None,
    ) -> list[RequirementView]:
        framework = await self._frameworks.get(session, framework_id)
        if framework is None:
            raise NotFound(detail=f"framework {framework_id}")
        if version_id is None:
            version = await self._frameworks.current_version(session, framework_id)
        else:
            version = await self._frameworks.get_version(session, version_id)
            if version is not None and version.framework_id != framework_id:
                version = None
        if version is None:
            raise NotFound(detail=f"no published version for framework {framework_id}")

        requirements = await self._requirements.list_for_version(session, version.id)
        counts = await self._requirements.template_counts(session)
        return [RequirementView(r, counts.get(r.id, 0)) for r in requirements]

    async def list_templates(  # noqa: PLR0913 — one argument per query filter
        self,
        session: AsyncSession,
        *,
        framework_id: uuid.UUID | None = None,
        category: str | None = None,
        control_type: str | None = None,
        importance: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[ControlTemplate], int]:
        return await self._templates.list_page(
            session,
            framework_id=framework_id,
            category=category,
            control_type=control_type,
            importance=importance,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def get_template(
        self, session: AsyncSession, template_id: uuid.UUID
    ) -> TemplateDetailView:
        template = await self._templates.get(session, template_id)
        if template is None:
            raise NotFound(detail=f"control template {template_id}")
        requirements = await self._requirements.list_for_template(session, template_id)
        counts = await self._requirements.template_counts(session)
        return TemplateDetailView(
            template, [RequirementView(r, counts.get(r.id, 0)) for r in requirements]
        )


compliance_service = ComplianceService()
