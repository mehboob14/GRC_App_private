"""The chain behind a criterion: the controls that answer it and what evidences each.

A criterion is met by the controls mapped to it, a control is evidenced by checks that
connected systems and Verity modules run and by what people provide, and each of those
leaves evidence. This reads that chain top down for one criterion, the way a buyer's
auditor reads it, so a person can answer "why is CC8.1 not met" by following it.

Whether a criterion is met is decided by the same rules as the dashboard
(``compliance.readiness``), not re-derived here, so the two cannot disagree.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.compliance.control_service import (
    ControlView,
    RequirementView,
    control_service,
)
from verity.modules.compliance.readiness import control_ready, requirement_ready

if TYPE_CHECKING:
    from verity.modules.connectors.service import ControlChain


@dataclass(frozen=True, slots=True)
class ChainControlView:
    control: ControlView
    coverage: str | None
    rationale: str | None
    origin: str
    ready: bool
    chain: ControlChain | None


@dataclass(frozen=True, slots=True)
class RequirementChainView:
    requirement: RequirementView
    state: str
    """met, partly, not_started or no_controls."""
    controls: list[ChainControlView]


class ChainService:
    async def requirement_chain(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, requirement_id: uuid.UUID
    ) -> RequirementChainView:
        # Both services answer to this one: the connectors module reads the compliance
        # module for its controls, so these are imported where they are used.
        from verity.modules.connectors.service import connector_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

        requirement = await control_service.get_requirement(session, requirement_id=requirement_id)
        found = await control_service.controls_for_requirement(
            session, tenant_id=tenant_id, requirement_id=requirement_id
        )
        chains = await connector_service.control_chains(
            session,
            tenant_id=tenant_id,
            controls=[(item.control.id, item.control.template_id) for item in found],
        )
        with_current = await evidence_service.control_ids_with_current_evidence(session, tenant_id)

        controls = []
        for item in found:
            chain = chains.get(item.control.id)
            ready = control_ready(
                status=item.control.status,
                has_current_evidence=item.control.id in with_current,
                automation=chain.automation_status if chain else None,
            )
            controls.append(
                ChainControlView(
                    control=item.control,
                    coverage=item.coverage,
                    rationale=item.rationale,
                    origin=item.origin,
                    ready=ready,
                    chain=chain,
                )
            )
        if not controls:
            state = "no_controls"
        elif requirement_ready((c.control.status, c.ready) for c in controls):
            state = "met"
        elif any(c.ready for c in controls):
            state = "partly"
        else:
            state = "not_started"
        return RequirementChainView(requirement=requirement, state=state, controls=controls)


chain_service = ChainService()
