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
  controls, a finding's asset) are not generic links and never become them here.
  A control's page and a document's page still show the ones they do not manage,
  read only, and say where to change them.

The trace walks every kind of edge outwards from one record, reading the generic
links here and each join table through the module that owns it.

Reads are filtered by what the caller may read, so a page never shows the title
of a record from a module the caller has no access to.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound, PermissionDenied
from verity.modules.audit.service import Actor, Membership, audit_service
from verity.modules.linkage.trace import (
    MAX_DEPTH,
    Candidate,
    Label,
    Ref,
    Trace,
    phrase,
    relation_key,
    walk,
)
from verity.modules.links.service import link_service

if TYPE_CHECKING:
    from verity.modules.compliance.control_service import ControlView

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

READ_ONLY: Final[dict[str, dict[str, str]]] = {
    "control": {
        "risk": "Linked from the risk page",
        "document": "Linked from the document page",
    },
    "document": {"control": "Linked on the Mappings tab"},
}
"""Groups a page shows but cannot draw. The pair has a table of its own and is managed
from the other record's page, so each says where. They show ahead of ``OFFERED``."""

PAIR_RELATION: Final[dict[tuple[str, str], tuple[str, str]]] = {
    ("risk", "control"): ("mitigated_by", "outgoing"),
    ("control", "risk"): ("mitigates", "incoming"),
    ("document", "control"): ("documents", "outgoing"),
    ("control", "document"): ("documented_by", "incoming"),
    ("evidence", "control"): ("proves", "outgoing"),
    ("control", "evidence"): ("proven_by", "incoming"),
    ("vulnerability", "asset"): ("found_on", "outgoing"),
    ("asset", "vulnerability"): ("affected_by", "incoming"),
}
"""The pairs that have a join table of their own, read from either end. Keyed by the
record read from and the record it reaches. The value is the relation as the first of
them would say it, and the way the pair is stored: risk to control, document to
control, evidence to control, finding to asset."""

_EPOCH: Final = datetime.min.replace(tzinfo=UTC)

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


def _control_label(control: ControlView) -> tuple[str, str, str, str | None]:
    """``(code, title, status, detail)`` of a control, as every page that names one reads it."""
    return control.code, control.name, control.status, control.category


def scaled(level: int, levels: int) -> int:
    """A 1 to 5 level on a register that may use 3 to 6 levels."""
    return max(1, min(levels, math.ceil(level * levels / 5)))


@dataclass(frozen=True, slots=True)
class LinkedRecord:
    link_id: uuid.UUID | None
    """None for a pair the other record's page manages: there is no link to remove."""

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

    managed_elsewhere: dict[str, str]
    """The read only groups among them, each with where its pair is changed."""


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

                found = await asset_service.label(session, tenant_id=tenant_id, asset_id=obj_id)
                return None if found is None else (found[0] or "", *found[1:])
            if obj_type == "vulnerability":
                from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
                    vulnerability_service,
                )

                cve = await vulnerability_service.label(
                    session, tenant_id=tenant_id, instance_id=obj_id
                )
                return None if cve is None else (cve[0] or "", *cve[1:])
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
                return _control_label(control)
            if obj_type == "evidence":
                from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

                item = await evidence_service.label(
                    session, tenant_id=tenant_id, evidence_id=obj_id
                )
                return None if item is None else ("", *item)
            if obj_type == "document":
                from verity.modules.documents.service import document_service  # noqa: PLC0415

                return await document_service.label(
                    session, tenant_id=tenant_id, document_id=obj_id
                )
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
        # A group the caller cannot read would only ever read "none linked", which is
        # not true, so it is left out rather than shown empty.
        read_only = {
            other: where
            for other, where in READ_ONLY.get(anchor_type, {}).items()
            if READ_PERMISSION[other] in permissions
        }
        if read_only:
            out.extend(
                await self._read_only(session, tenant_id, anchor_type, anchor_id, set(read_only))
            )
        out.sort(key=lambda r: (r.target_type, r.title.lower()))
        offered = OFFERED[anchor_type]
        return LinkedRecords(
            records=out,
            offered=[*read_only, *offered],
            can_link=[t for t in offered if may_write(anchor_type, t, permissions)],
            managed_elsewhere=read_only,
        )

    async def _read_only(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        anchor_type: str,
        anchor_id: uuid.UUID,
        types: set[str],
    ) -> list[LinkedRecord]:
        """The records tied to this one through a pair with a table of its own, drawn
        with no link to remove: the other record's page is where that pair changes."""
        out: list[LinkedRecord] = []
        for edge in await self._pair_edges(session, tenant_id, Ref(anchor_type, anchor_id)):
            if edge.ref.type not in types:
                continue
            resolved = await self.resolve(session, tenant_id, edge.ref.type, edge.ref.id)
            if resolved is None:
                continue  # the other end is gone; the edge renders nothing
            code, title, status, detail = resolved
            out.append(
                LinkedRecord(
                    link_id=None,
                    target_type=edge.ref.type,
                    target_id=edge.ref.id,
                    relation=edge.relation,
                    direction=edge.direction,
                    code=code,
                    title=title,
                    status=status,
                    detail=detail,
                    can_unlink=False,
                )
            )
        return out

    async def _pair_edges(
        self, session: AsyncSession, tenant_id: uuid.UUID, ref: Ref
    ) -> list[Candidate]:
        """The edges of a record that have a join table of their own, read through the
        module that owns each. Only ids come back: a title is the other module's to say."""
        from verity.modules.documents.service import document_service  # noqa: PLC0415
        from verity.modules.evidence.service import evidence_service  # noqa: PLC0415
        from verity.modules.risk.service import risk_service  # noqa: PLC0415
        from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
            vulnerability_service,
        )

        kind, rid = ref.type, ref.id
        found: list[tuple[str, Sequence[uuid.UUID]]] = []
        if kind == "risk":
            controls = await risk_service.control_ids_for_risk(
                session, tenant_id=tenant_id, risk_id=rid
            )
            found = [("control", controls)]
        elif kind == "control":
            risks = await risk_service.risk_ids_for_control(
                session, tenant_id=tenant_id, control_id=rid
            )
            documents = await document_service.document_ids_for_control(
                session, tenant_id=tenant_id, control_id=rid
            )
            # Evidence offers no order of its own; ids are time ordered, so oldest first.
            attached = await evidence_service.evidence_ids_for_control(session, tenant_id, rid)
            found = [("risk", risks), ("document", documents), ("evidence", sorted(attached))]
        elif kind == "document":
            controls = await document_service.control_ids_for_document(
                session, tenant_id=tenant_id, document_id=rid
            )
            found = [("control", controls)]
        elif kind == "evidence":
            controls = await evidence_service.control_ids_for_evidence(session, tenant_id, rid)
            found = [("control", controls)]
        elif kind == "vulnerability":
            asset_id = await vulnerability_service.asset_id_for_instance(
                session, tenant_id=tenant_id, instance_id=rid
            )
            found = [("asset", [] if asset_id is None else [asset_id])]
        elif kind == "asset":
            findings = await vulnerability_service.instance_ids_for_asset(
                session, tenant_id=tenant_id, asset_id=rid
            )
            found = [("vulnerability", findings)]
        return [
            Candidate(Ref(other, other_id), *PAIR_RELATION[(kind, other)])
            for other, ids in found
            for other_id in ids
        ]

    async def _edges(
        self, session: AsyncSession, tenant_id: uuid.UUID, ref: Ref
    ) -> list[Candidate]:
        """Every edge of a record, for the trace: the generic links oldest first, then
        the pairs that have a table of their own."""
        generic = await link_service.for_object(
            session, tenant_id=tenant_id, obj_type=ref.type, obj_id=ref.id
        )
        drawn = [
            Candidate(
                Ref(edge.other_type, edge.other_id),
                relation_key(edge.relation, edge.direction),
                edge.direction,
                edge.created_at,
                edge.created_by_membership_id,
            )
            for edge in sorted(generic, key=lambda e: (e.created_at or _EPOCH, e.link_id))
            if edge.other_type in READ_PERMISSION  # an incident has no module to open yet
        ]
        return [*drawn, *await self._pair_edges(session, tenant_id, ref)]

    async def _control_labels(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[str, str, str, str | None]]:
        """Every control, retired ones too, labelled in one read. Naming one control costs
        as many statements as listing the library, so a trace lists it once."""
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        controls = await control_service.list_controls(
            session, tenant_id=tenant_id, include_disabled=True
        )
        return {c.id: _control_label(c) for c in controls}

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    async def trace(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        record_type: str,
        record_id: uuid.UUID,
        depth: int,
        permissions: frozenset[str],
    ) -> Trace:
        """Everything connected to one record, hop by hop, as far as the caller may see.

        A read, so no audit row. The start record needs its own module's read key. Every
        other type is opened only if the caller can read it; one they cannot read is
        neither shown nor walked through, so nothing behind it leaks either.
        """
        if record_type not in READ_PERMISSION:
            raise InvalidInput(
                "That kind of record cannot be traced.", detail=f"trace from {record_type!r}"
            )
        if READ_PERMISSION[record_type] not in permissions:
            raise PermissionDenied(
                detail=f"tracing {record_type} needs {READ_PERMISSION[record_type]}"
            )
        resolved = await self.resolve(session, tenant_id, record_type, record_id)
        if resolved is None:
            raise NotFound(_TARGET_GONE, detail=f"{record_type} {record_id}")

        async def edges(ref: Ref) -> list[Candidate]:
            return await self._edges(session, tenant_id, ref)

        controls: dict[uuid.UUID, tuple[str, str, str, str | None]] | None = None

        async def label(ref: Ref) -> Label | None:
            nonlocal controls
            if ref.type == "control":
                if controls is None:
                    controls = await self._control_labels(session, tenant_id)
                found = controls.get(ref.id)
            else:
                found = await self.resolve(session, tenant_id, ref.type, ref.id)
            return None if found is None else Label(*found)

        walked = await walk(
            Ref(record_type, record_id),
            Label(*resolved),
            edges=edges,
            label=label,
            readable=frozenset(t for t, key in READ_PERMISSION.items() if key in permissions),
            depth=max(1, min(depth, MAX_DEPTH)),
        )
        names = (
            await self._member_names(session, tenant_id)
            if any(node.linked_by_id for node in walked.nodes)
            else {}
        )
        return replace(
            walked,
            nodes=[
                replace(
                    node,
                    relation=phrase(node.relation) if node.relation else None,
                    linked_by=names.get(node.linked_by_id) if node.linked_by_id else None,
                )
                for node in walked.nodes
            ],
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
