"""What the workspace's records already say for each area of the SOC 2 system description (EN-6).

The description itself is a document started from the ``soc2-system-description`` template, with
versions and approval from the documents module (design 2.4). This read gathers, per area, the
facts already held, and names what a person still has to write. No criterion text is returned.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.compliance.engagement_service import engagement_service
from verity.modules.compliance.programme_service import programme_service
from verity.modules.compliance.scope_service import scope_service

_CATEGORIES: Final = ("Availability", "Confidentiality", "Processing Integrity", "Privacy")


@dataclass(frozen=True, slots=True)
class DescriptionArea:
    key: str
    title: str
    filled: list[str]
    to_write: str


class DescriptionService:
    async def inputs(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[DescriptionArea]:
        from verity.modules.tenancy.service import tenancy_service  # noqa: PLC0415

        profile = await tenancy_service.get_own_company_profile(session, tenant_id)
        engagement = await engagement_service.get(
            session, tenant_id=tenant_id, framework_code="SOC2"
        )
        items = [
            i
            for i in await scope_service.list_items(
                session, tenant_id=tenant_id, framework_code="SOC2"
            )
            if i.in_scope
        ]
        commitments = await programme_service.commitments(session, tenant_id=tenant_id)
        vendors = await programme_service.engagement_vendors(
            session, tenant_id=tenant_id, framework_code="SOC2"
        )
        changes = await programme_service.changes_in_period(
            session, tenant_id=tenant_id, framework_code="SOC2"
        )
        elected = set(engagement.categories_in_scope) if engagement else set()
        services = [s for s in (profile.description, profile.industry) if s]
        return [
            DescriptionArea(
                "services",
                "Types of services provided",
                services,
                "Describe each service in the report, in your customers' terms.",
            ),
            DescriptionArea(
                "commitments",
                "Principal service commitments and system requirements",
                [c.statement for c in commitments],
                "Say where each commitment is written and how the system meets it.",
            ),
            DescriptionArea(
                "components",
                "Components of the system",
                [f"{i.name} ({i.kind.replace('_', ' ')})" for i in items],
                "Cover infrastructure, software, people, procedures and data for each component.",
            ),
            DescriptionArea(
                "incidents",
                "Significant incidents",
                [],
                "Describe any incident that broke a commitment, or say there was none.",
            ),
            DescriptionArea(
                "control_environment",
                "Control environment, risk assessment, information and monitoring",
                [],
                "Describe how oversight, risk assessment, communication and monitoring work.",
            ),
            DescriptionArea(
                "user_entity_controls",
                "Controls your customers are expected to run",
                [],
                "List what customers must do for your controls to work, such as managing users.",
            ),
            DescriptionArea(
                "subservice",
                "Subservice organisations",
                [
                    f"{v.name}, {v.method or 'method not chosen'}"
                    for v in vendors
                    if v.role == "subservice"
                ],
                "For each, say whether it is carved out or included and what you rely on it for.",
            ),
            DescriptionArea(
                "criteria_not_applicable",
                "Criteria not in scope",
                [f"{c} is not in scope" for c in _CATEGORIES if c not in elected],
                "Say why each category left out does not apply to the service.",
            ),
            DescriptionArea(
                "changes",
                "Significant changes during the period",
                [c.summary for c in changes],
                "Describe changes to the system during the period, or say there were none.",
            ),
        ]


description_service = DescriptionService()
