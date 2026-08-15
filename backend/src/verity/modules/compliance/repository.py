"""Data access for shipped global content. No business rules, no commits.

These tables carry no ``tenant_id`` and have no RLS: they are the platform's
own content, readable by every authenticated tenant (see the global-content
migration and week2-decisions.md D10). So unlike every other repository in this
codebase, the queries here deliberately carry no tenant filter — there is no
tenant column to filter on.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.compliance.models import (
    ControlTemplate,
    Framework,
    FrameworkVersion,
    FrameworkVersionRequirement,
    Requirement,
    TemplateRequirementMap,
)


class FrameworkRepository:
    async def list_frameworks(self, session: AsyncSession) -> list[Framework]:
        result = await session.execute(select(Framework).order_by(Framework.code))
        return list(result.scalars())

    async def get(self, session: AsyncSession, framework_id: uuid.UUID) -> Framework | None:
        return await session.get(Framework, framework_id)

    async def list_versions(self, session: AsyncSession) -> list[FrameworkVersion]:
        result = await session.execute(
            select(FrameworkVersion).order_by(
                FrameworkVersion.framework_id, FrameworkVersion.version
            )
        )
        return list(result.scalars())

    async def requirement_counts_by_version(self, session: AsyncSession) -> dict[uuid.UUID, int]:
        """One query for every version's requirement count — not one per row."""
        result = await session.execute(
            select(
                FrameworkVersionRequirement.framework_version_id,
                func.count(FrameworkVersionRequirement.requirement_id),
            ).group_by(FrameworkVersionRequirement.framework_version_id)
        )
        return {row[0]: row[1] for row in result}

    async def current_version(
        self, session: AsyncSession, framework_id: uuid.UUID
    ) -> FrameworkVersion | None:
        result = await session.execute(
            select(FrameworkVersion).where(
                FrameworkVersion.framework_id == framework_id,
                FrameworkVersion.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_version(
        self, session: AsyncSession, version_id: uuid.UUID
    ) -> FrameworkVersion | None:
        return await session.get(FrameworkVersion, version_id)


class RequirementRepository:
    async def list_for_version(
        self, session: AsyncSession, version_id: uuid.UUID
    ) -> list[Requirement]:
        result = await session.execute(
            select(Requirement)
            .join(
                FrameworkVersionRequirement,
                FrameworkVersionRequirement.requirement_id == Requirement.id,
            )
            .where(FrameworkVersionRequirement.framework_version_id == version_id)
            .order_by(Requirement.code)
        )
        return list(result.scalars())

    async def template_counts(self, session: AsyncSession) -> dict[uuid.UUID, int]:
        """How many templates satisfy each requirement, in one query."""
        result = await session.execute(
            select(
                TemplateRequirementMap.requirement_id,
                func.count(TemplateRequirementMap.template_id),
            ).group_by(TemplateRequirementMap.requirement_id)
        )
        return {row[0]: row[1] for row in result}

    async def list_for_template(
        self, session: AsyncSession, template_id: uuid.UUID
    ) -> list[Requirement]:
        result = await session.execute(
            select(Requirement)
            .join(
                TemplateRequirementMap,
                TemplateRequirementMap.requirement_id == Requirement.id,
            )
            .where(TemplateRequirementMap.template_id == template_id)
            .order_by(Requirement.code)
        )
        return list(result.scalars())


class ControlTemplateRepository:
    def _conditions(
        self,
        *,
        framework_id: uuid.UUID | None,
        category: str | None,
        control_type: str | None,
        importance: str | None,
        search: str | None,
    ) -> list[ColumnElement[bool]]:
        """The WHERE terms, built once and applied to both the page and the count.

        Returning conditions rather than a Select keeps the two queries provably
        in step: a filter that narrows the rows but not the total is how a
        paginator starts lying about how much there is.
        """
        clauses: list[ColumnElement[bool]] = []
        if category is not None:
            clauses.append(ControlTemplate.category == category)
        if control_type is not None:
            clauses.append(ControlTemplate.control_type == control_type)
        if importance is not None:
            clauses.append(ControlTemplate.importance == importance)
        if search:
            clauses.append(func.lower(ControlTemplate.name).like(f"%{search.strip().lower()}%"))
        if framework_id is not None:
            # Templates satisfying at least one requirement of this framework.
            clauses.append(
                ControlTemplate.id.in_(
                    select(TemplateRequirementMap.template_id)
                    .join(Requirement, Requirement.id == TemplateRequirementMap.requirement_id)
                    .where(Requirement.framework_id == framework_id)
                )
            )
        return clauses

    async def list_page(  # noqa: PLR0913 — one filter per query parameter, no more
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
        clauses = self._conditions(
            framework_id=framework_id,
            category=category,
            control_type=control_type,
            importance=importance,
            search=search,
        )
        rows = await session.execute(
            select(ControlTemplate)
            .where(*clauses)
            .order_by(ControlTemplate.code)
            .limit(limit)
            .offset(offset)
        )
        total = await session.execute(
            select(func.count()).select_from(ControlTemplate).where(*clauses)
        )
        return list(rows.scalars()), int(total.scalar_one() or 0)

    async def get(self, session: AsyncSession, template_id: uuid.UUID) -> ControlTemplate | None:
        return await session.get(ControlTemplate, template_id)
