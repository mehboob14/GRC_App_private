"""The 360 degree linkage, as seen from one record.

Links already exist (ADR-0003, the ``links`` table), and the risk register and
evidence already draw them. What was missing was every other end: an asset or a
vulnerability could be linked from a risk and show nothing of it. This module
reads and draws links from assets, vulnerabilities, controls and documents.

Two rules keep one fact in one place:

* A pair a module already owns is drawn through that module. The risk register
  owns a risk's links to assets, vulnerabilities, evidence, tasks, vendors and
  documents; evidence owns its links to tasks, documents, assets and
  vulnerabilities. Linking an asset to a risk from the asset calls
  ``risk_service.link_record``, so the edge, its direction and the risk's own
  history are exactly what the risk page writes.
* Pairs with a join table of their own (a risk's, a document's or evidence's
  controls, an asset's vulnerabilities) are not generic links and never become
  them here.

Reads are filtered by what the caller may read, so a page never shows the title
of a record from a module the caller has no access to.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound, PermissionDenied
from verity.modules.audit.service import Actor, Membership, audit_service
from verity.modules.links.service import link_service

READ_PERMISSION: Final[dict[str, str]] = {
    "asset": "assets:read",
    "vulnerability": "vulnerabilities:read",
    "risk": "risks:read",
    "control": "frameworks:read",
    "evidence": "evidence:read",
    "document": "documents:read",
    "vendor": "vendors:read",
    "task": "tasks:read",
}

MANAGE_PERMISSION: Final[dict[str, str]] = {
    "asset": "assets:manage",
    "vulnerability": "vulnerabilities:manage",
    "risk": "risks:manage",
    "control": "controls:manage",
    "evidence": "evidence:manage",
    "document": "documents:manage",
    "vendor": "vendors:manage",
    "task": "tasks:manage",
}

OFFERED: Final[dict[str, tuple[str, ...]]] = {
    "asset": ("risk", "control", "evidence", "document", "vendor"),
    "vulnerability": ("risk", "control", "evidence", "document", "task"),
    "control": ("asset", "vulnerability"),
    "document": ("asset", "vulnerability", "risk"),
}
"""What each record's page offers to link, in the order its groups show."""

AUDIT_TYPE: Final[dict[str, str]] = {
    "asset": "asset",
    "vulnerability": "vuln_instance",
    "control": "control",
    "document": "document",
}
"""The object type each anchor's own audit rows already use."""

_RISK_OWNS: Final = frozenset({"asset", "vulnerability", "evidence", "task", "vendor", "document"})
_EVIDENCE_OWNS: Final = frozenset({"task", "document", "asset", "vulnerability"})

_SEVERITY_IMPACT: Final[dict[str, int]] = {"critical": 5, "high": 4, "medium": 3, "low": 2}

_LINK_GONE: Final = "This link no longer exists. It may have been removed already."
_TARGET_GONE: Final = "That record no longer exists. It may have been removed."


def owner_of(a: str, b: str) -> str | None:
    """The module that owns the edge between two record types, if any."""
    if "risk" in (a, b) and (b if a == "risk" else a) in _RISK_OWNS:
        return "risk"
    if "evidence" in (a, b) and (b if a == "evidence" else a) in _EVIDENCE_OWNS:
        return "evidence"
    return None


def may_write(anchor: str, other: str, permissions: frozenset[str]) -> bool:
    """Drawing or removing an edge needs manage on the record it is drawn from,
    manage on the module that owns the pair, and read on the other end."""
    owner = owner_of(anchor, other)
    return (
        MANAGE_PERMISSION[anchor] in permissions
        and (owner is None or MANAGE_PERMISSION[owner] in permissions)
        and READ_PERMISSION[other] in permissions
    )


def scaled(level: int, levels: int) -> int:
    """A 1 to 5 level on a register that may use 3 to 6 levels."""
    return max(1, min(levels, math.ceil(level * levels / 5)))


@dataclass(frozen=True, slots=True)
class LinkedRecord:
    link_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relation: str
    direction: str
    """``outgoing`` when the edge was drawn from this record, else ``incoming``."""

    code: str
    title: str
    status: str
    detail: str | None
    can_unlink: bool


@dataclass(frozen=True, slots=True)
class LinkedRecords:
    records: list[LinkedRecord]
    offered: list[str]
    """The groups the page shows, in order."""

    can_link: list[str]
    """Of those, the types this caller may link right now."""


@dataclass(frozen=True, slots=True)
class RaisedRisk:
    id: uuid.UUID
    code: str
    title: str


class LinkageService:
    async def resolve(  # noqa: PLR0911 — one branch per module
        self, session: AsyncSession, tenant_id: uuid.UUID, obj_type: str, obj_id: uuid.UUID
    ) -> tuple[str, str, str, str | None] | None:
        """``(code, title, status, detail)`` of a record, or None when it is gone."""
        try:
            if obj_type == "asset":
                from verity.modules.assets.service import asset_service  # noqa: PLC0415

                asset = await asset_service.get_asset(session, tenant_id=tenant_id, asset_id=obj_id)
                return asset.hostname or "", asset.name, asset.status, asset.asset_type
            if obj_type == "vulnerability":
                from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
                    vulnerability_service,
                )

                vuln = await vulnerability_service.get_instance(
                    session, tenant_id=tenant_id, instance_id=obj_id
                )
                return vuln.cve_id or "", vuln.title, vuln.state, vuln.severity
            if obj_type == "risk":
                from verity.modules.risk.service import risk_service  # noqa: PLC0415

                risk = await risk_service.get_ref(session, tenant_id=tenant_id, risk_id=obj_id)
                return risk.code, risk.title, risk.status, risk.band
            if obj_type == "control":
                from verity.modules.compliance.control_service import (  # noqa: PLC0415
                    control_service,
                )

                control = await control_service.get_control(
                    session, tenant_id=tenant_id, control_id=obj_id
                )
                return control.code, control.name, control.status, control.category
            if obj_type == "evidence":
                from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

                evidence = await evidence_service.get(
                    session, tenant_id=tenant_id, evidence_id=obj_id
                )
                return "", evidence.title, evidence.freshness, evidence.evidence_type
            if obj_type == "document":
                from verity.modules.documents.service import document_service  # noqa: PLC0415

                doc = await document_service.get_document(
                    session, tenant_id=tenant_id, document_id=obj_id
                )
                return doc.code, doc.title, doc.lifecycle, doc.doc_type
            if obj_type == "vendor":
                from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

                vendor = await vendor_service.get_ref(
                    session, tenant_id=tenant_id, vendor_id=obj_id
                )
                return "", vendor.name, vendor.lifecycle_status, vendor.tier
            if obj_type == "task":
                from verity.modules.tasks.service import task_service  # noqa: PLC0415

                task = await task_service.get_task(session, tenant_id=tenant_id, task_id=obj_id)
                return task.code, task.title, task.status, task.task_kind
        except NotFound:
            return None
        return None

    async def _anchor(
        self, session: AsyncSession, tenant_id: uuid.UUID, anchor_type: str, anchor_id: uuid.UUID
    ) -> None:
        if anchor_type not in OFFERED:
            raise InvalidInput(
                "Links are not shown for this kind of record.", detail=f"anchor {anchor_type!r}"
            )
        if await self.resolve(session, tenant_id, anchor_type, anchor_id) is None:
            raise NotFound(_TARGET_GONE, detail=f"{anchor_type} {anchor_id}")

    async def records(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        anchor_type: str,
        anchor_id: uuid.UUID,
        permissions: frozenset[str],
    ) -> LinkedRecords:
        await self._anchor(session, tenant_id, anchor_type, anchor_id)
        edges = await link_service.for_object(
            session, tenant_id=tenant_id, obj_type=anchor_type, obj_id=anchor_id
        )
        out: list[LinkedRecord] = []
        seen: set[tuple[str, uuid.UUID, str]] = set()
        for edge in edges:
            other = edge.other_type
            if other not in READ_PERMISSION or READ_PERMISSION[other] not in permissions:
                continue
            key = (other, edge.other_id, edge.relation)
            if key in seen:
                continue  # the same pair drawn from both ends reads once
            seen.add(key)
            resolved = await self.resolve(session, tenant_id, other, edge.other_id)
            if resolved is None:
                continue  # the other end is gone; the edge renders nothing
            code, title, status, detail = resolved
            out.append(
                LinkedRecord(
                    link_id=edge.link_id,
                    target_type=other,
                    target_id=edge.other_id,
                    relation=edge.relation,
                    direction=edge.direction,
                    code=code,
                    title=title,
                    status=status,
                    detail=detail,
                    can_unlink=may_write(anchor_type, other, permissions),
                )
            )
        out.sort(key=lambda r: (r.target_type, r.title.lower()))
        offered = OFFERED[anchor_type]
        return LinkedRecords(
            records=out,
            offered=list(offered),
            can_link=[t for t in offered if may_write(anchor_type, t, permissions)],
        )

    async def link(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        anchor_type: str,
        anchor_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        permissions: frozenset[str],
    ) -> LinkedRecords:
        await self._anchor(session, tenant_id, anchor_type, anchor_id)
        if target_type not in OFFERED[anchor_type]:
            raise InvalidInput(
                "That is not something you can link here. Choose one of the types offered.",
                detail=f"{anchor_type} does not link to {target_type!r}",
            )
        if not may_write(anchor_type, target_type, permissions):
            raise PermissionDenied(detail=f"linking {anchor_type} to {target_type} is not granted")
        if await self.resolve(session, tenant_id, target_type, target_id) is None:
            raise NotFound(_TARGET_GONE, detail=f"{target_type} {target_id}")

        owner = owner_of(anchor_type, target_type)
        if owner == "risk":
            from verity.modules.risk.service import risk_service  # noqa: PLC0415

            await risk_service.link_record(
                session,
                tenant_id=tenant_id,
                actor=actor,
                risk_id=target_id,
                target_type=anchor_type,
                target_id=anchor_id,
            )
        elif owner == "evidence":
            from verity.modules.evidence.service import (  # noqa: PLC0415
                LinkTarget,
                evidence_service,
            )

            await evidence_service.link_record(
                session,
                tenant_id=tenant_id,
                actor=actor,
                evidence_id=target_id,
                target=LinkTarget(type=anchor_type, id=anchor_id),
            )
        else:
            existing = await link_service.for_object(
                session, tenant_id=tenant_id, obj_type=anchor_type, obj_id=anchor_id
            )
            if not any(e.other_type == target_type and e.other_id == target_id for e in existing):
                await link_service.create(
                    session,
                    tenant_id=tenant_id,
                    from_type=anchor_type,
                    from_id=anchor_id,
                    to_type=target_type,
                    to_id=target_id,
                    created_by_membership_id=actor.id if isinstance(actor, Membership) else None,
                )
        await audit_service.record(
            session,
            action="update",
            object_type=AUDIT_TYPE[anchor_type],
            object_id=anchor_id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"linked": f"{target_type}:{target_id}"},
        )
        return await self.records(
            session,
            tenant_id=tenant_id,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            permissions=permissions,
        )

    async def unlink(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        anchor_type: str,
        anchor_id: uuid.UUID,
        link_id: uuid.UUID,
        permissions: frozenset[str],
    ) -> LinkedRecords:
        await self._anchor(session, tenant_id, anchor_type, anchor_id)
        edges = await link_service.for_object(
            session, tenant_id=tenant_id, obj_type=anchor_type, obj_id=anchor_id
        )
        edge = next((e for e in edges if e.link_id == link_id), None)
        if edge is None:
            raise NotFound(_LINK_GONE, detail=f"link {link_id} on {anchor_type} {anchor_id}")
        if edge.other_type not in READ_PERMISSION or not may_write(
            anchor_type, edge.other_type, permissions
        ):
            raise PermissionDenied(detail=f"unlinking {edge.other_type} is not granted")

        owner = owner_of(anchor_type, edge.other_type)
        if owner == "risk":
            from verity.modules.risk.service import risk_service  # noqa: PLC0415

            await risk_service.unlink_record(
                session, tenant_id=tenant_id, actor=actor, risk_id=edge.other_id, link_id=link_id
            )
        elif owner == "evidence":
            from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

            await evidence_service.unlink_record(
                session,
                tenant_id=tenant_id,
                actor=actor,
                evidence_id=edge.other_id,
                link_id=link_id,
            )
        else:
            await link_service.delete(session, tenant_id=tenant_id, link_id=link_id)
        await audit_service.record(
            session,
            action="update",
            object_type=AUDIT_TYPE[anchor_type],
            object_id=anchor_id,
            actor=actor,
            tenant_id=tenant_id,
            before={"linked": f"{edge.other_type}:{edge.other_id}"},
            after=None,
        )
        return await self.records(
            session,
            tenant_id=tenant_id,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            permissions=permissions,
        )

    async def raise_risk(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        instance_id: uuid.UUID,
        title: str | None,
        register_id: uuid.UUID | None,
        permissions: frozenset[str],
    ) -> RaisedRisk:
        """A risk in the register, scored from the finding and linked back to it.

        Impact follows severity; likelihood follows the exploit picture (known
        exploited, then EPSS). The risk is linked to the finding as ``caused_by``
        and to its asset, so both pages show where the risk came from.
        """
        if READ_PERMISSION["vulnerability"] not in permissions:
            raise PermissionDenied(detail="raising a risk needs vulnerabilities:read")
        from verity.modules.risk.service import RiskInput, risk_service  # noqa: PLC0415
        from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
            vulnerability_service,
        )

        vuln = await vulnerability_service.get_instance(
            session, tenant_id=tenant_id, instance_id=instance_id
        )
        if register_id is None:
            register_id = (
                await risk_service.ensure_default_register(
                    session, tenant_id=tenant_id, actor=actor
                )
            ).id
        register, categories = await risk_service.register_context(
            session, tenant_id=tenant_id, register_id=register_id
        )
        top = [c for c in categories if c.parent_id is None and c.archived_at is None]
        category = next((c for c in top if c.name == "Technology"), top[0] if top else None)
        if category is None:
            raise InvalidInput(
                "This register has no categories yet. Add one in risk settings, then try again.",
                detail=f"register {register.id} has no active category",
            )
        epss = vuln.epss_score or 0.0
        likelihood = 5 if vuln.kev_flag else 4 if epss >= 0.5 else 3 if epss >= 0.1 else 2  # noqa: PLR2004
        name = (title or "").strip() or f"{vuln.title} on {vuln.asset_name}"
        source = " ".join(p for p in (vuln.cve_id, vuln.title) if p)
        exploited = ", known to be exploited" if vuln.kev_flag else ""
        risk = await risk_service.create_risk(
            session,
            tenant_id=tenant_id,
            actor=actor,
            data=RiskInput(
                register_id=register.id,
                title=name[:300],
                category_id=category.id,
                description=(
                    f"Raised from the vulnerability {source} on {vuln.asset_name} "
                    f"({vuln.severity} severity{exploited})."
                ),
                treatment="mitigate",
                inherent_likelihood=scaled(likelihood, register.likelihood_levels),
                inherent_impact=scaled(
                    _SEVERITY_IMPACT.get(vuln.severity, 2), register.impact_levels
                ),
                owner_membership_id=vuln.owner_membership_id,
                asset_ids=[vuln.asset_id],
            ),
        )
        await risk_service.link_record(
            session,
            tenant_id=tenant_id,
            actor=actor,
            risk_id=risk.id,
            target_type="vulnerability",
            target_id=vuln.id,
            relation="caused_by",
        )
        await audit_service.record(
            session,
            action="update",
            object_type=AUDIT_TYPE["vulnerability"],
            object_id=vuln.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"raised_risk": str(risk.id)},
        )
        return RaisedRisk(id=risk.id, code=risk.code, title=risk.title)


linkage_service = LinkageService()
