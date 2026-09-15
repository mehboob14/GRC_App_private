"""Asset management — business logic.

DB access lives here (no separate repository, matching the tasks and documents
modules). The rules the frontend was built against live here as the one
authority: the ISO 27005 criticality scorer (highest CIA harm wins, adjusted for
exposure and data sensitivity), the inventory-hygiene computation, and the
lifecycle transition allow-list served to the client.

Nothing defaults criticality — a NULL score/tier means "not assessed". Two
records are written for every state change: a columnar ``asset_transitions`` row
(the domain history the detail page renders) and a platform ``audit_log`` row
(rule 5). Cross-module reads go through sibling services (rule 4): member and
group names via IAM.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.assets.models import Asset, AssetTransition, DecommissionRecord
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.shared.ids import uuid7

# -- shared rules (the client is served these; it never hardcodes them) ------

LIFECYCLE_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "planned": ("active", "retired"),
    "active": ("in_maintenance", "decommissioned"),
    "in_maintenance": ("active", "decommissioned"),
    "decommissioned": ("retired", "active"),
    "retired": (),
}

_HARM: Final[dict[int, float]] = {1: 2.0, 2: 4.0, 3: 6.0, 4: 8.0, 5: 10.0}
_STALE_DAYS: Final = 90
# Score thresholds for the tier bands (out of 10).
_CRITICAL_AT: Final = 8.5
_HIGH_AT: Final = 6.5
_MEDIUM_AT: Final = 4.0

# Business functions that carry the +1.5 criticality boost. In a later phase this
# becomes the ``high_impact`` flag on a business-function catalogue; the set is
# duplicated from the frontend for now so both sides score identically.
HIGH_IMPACT_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {
        "Payment processing",
        "Authentication / IAM",
        "Regulated data (PHI)",
        "Customer data",
        "Financial reporting",
    }
)


def _is_high_impact(fn: str | None) -> bool:
    return fn is not None and fn in HIGH_IMPACT_FUNCTIONS


def compute_criticality(  # noqa: PLR0913 — the scorer's inputs, no more
    confidentiality: int | None,
    integrity: int | None,
    availability: int | None,
    *,
    internet_facing: bool,
    data_classification: str | None,
    business_function: str | None,
) -> tuple[float, str] | None:
    """ISO 27005: base = highest CIA harm (not a sum), then exposure and
    data-sensitivity boosts, clamped to [0, 10]. Returns None when NOTHING is
    rated — no phantom default."""
    rated = [r for r in (confidentiality, integrity, availability) if r is not None]
    if not rated:
        return None
    score = max(_HARM[r] for r in rated)
    if internet_facing:
        score += 2.5
    if data_classification == "restricted":
        score += 1.5
    elif data_classification == "confidential":
        score += 1.0
    if _is_high_impact(business_function):
        score += 1.5
    score = min(10.0, round(score, 1))
    tier = (
        "critical"
        if score >= _CRITICAL_AT
        else "high"
        if score >= _HIGH_AT
        else "medium"
        if score >= _MEDIUM_AT
        else "low"
    )
    return score, tier


def _is_stale(last: datetime | None, *, now: datetime) -> bool:
    return last is not None and (now - last) > timedelta(days=_STALE_DAYS)


def compute_hygiene(asset: Asset, *, now: datetime) -> tuple[int, list[str], bool]:
    """Five checks; NULL means unmet, so an unassessed record scores low honestly."""
    missing: list[str] = []
    if asset.primary_owner_membership_id is None:
        missing.append("no_owner")
    if not asset.asset_type:
        missing.append("no_type")
    if (asset.tier_override or asset.tier) is None:
        missing.append("no_criticality")
    if asset.data_classification is None:
        missing.append("no_classification")
    if asset.confidentiality is None or asset.integrity is None or asset.availability is None:
        missing.append("no_cia")
    score = round((5 - len(missing)) / 5 * 100)
    return score, missing, _is_stale(asset.last_reviewed_at or asset.last_seen_at, now=now)


def _effective_tier(asset: Asset) -> str | None:
    return asset.tier_override or asset.tier


# -- views (returned to the router; never ORM rows) --------------------------


@dataclass(frozen=True, slots=True)
class Member:
    membership_id: uuid.UUID
    name: str


@dataclass(frozen=True, slots=True)
class CriticalityView:
    confidentiality: int | None
    integrity: int | None
    availability: int | None
    score: float | None
    tier: str | None
    tier_override: str | None
    tier_override_reason: str | None


@dataclass(frozen=True, slots=True)
class OwnershipView:
    primary_owner: Member | None
    secondary_owner: Member | None
    business_owner: Member | None
    custodian: Member | None
    escalation_contact: Member | None
    owning_team: str | None


@dataclass(frozen=True, slots=True)
class HygieneView:
    score: int
    missing: list[str]
    is_stale: bool


@dataclass(frozen=True, slots=True)
class AssetView:
    id: uuid.UUID
    name: str
    asset_type: str
    description: str
    hostname: str | None
    ip_address: str | None
    fqdn: str | None
    os_normalized: str | None
    environment: str | None
    location: str | None
    vendor_ref: str | None
    data_classification: str | None
    regulated_data_type: str | None
    compliance_scope: list[str]
    internet_facing: bool
    customer_facing: bool
    network_segment: str | None
    business_function: str | None
    criticality: CriticalityView
    ownership: OwnershipView
    status: str
    replaced_by_asset_id: uuid.UUID | None
    valuation: float | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    last_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    source: str
    hygiene: HygieneView
    vuln_count: int
    link_count: int
    relationship_count: int


@dataclass(frozen=True, slots=True)
class AssetRef:
    """The lightweight asset facts a sibling module needs (rule 4) — no hygiene,
    no ownership resolution. Used by vulnerabilities to inherit the owner and
    weight prioritisation by criticality/exposure without an N+1 of get_asset."""

    id: uuid.UUID
    name: str
    host: str | None
    tier: str | None
    internet_facing: bool
    customer_facing: bool
    primary_owner_membership_id: uuid.UUID | None
    escalation_contact_membership_id: uuid.UUID | None
    status: str
    #: The C/I/A ratings (1-5, or None where not assessed). Prioritisation uses
    #: only the collapsed ``tier``; these travel so a sibling module can show a
    #: reader *why* an asset is rated the way it is, without an N+1 of get_asset.
    confidentiality: int | None = None
    integrity: int | None = None
    availability: int | None = None


@dataclass(frozen=True, slots=True)
class DecommissionView:
    disposal_method: str
    media_sanitised: bool
    replacement_asset_id: uuid.UUID | None
    evidence_ref: str | None
    reason: str
    decommissioned_by: str | None
    decommissioned_at: datetime


@dataclass(frozen=True, slots=True)
class TransitionView:
    id: uuid.UUID
    actor: str | None
    field_changed: str
    old_value: str | None
    new_value: str | None
    note: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AssetDetailView(AssetView):
    serial_number: str | None
    primary_mac: str | None
    cloud_resource_id: str | None
    business_impact_notes: str | None
    operational_dependency_rating: str | None
    decommission: DecommissionView | None
    transitions: list[TransitionView]
    watchers: list[Member]
    allowed_transitions: list[str]


@dataclass(frozen=True, slots=True)
class AssetFilters:
    search: str | None = None
    asset_type: str | None = None
    tiers: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    environments: tuple[str, ...] = ()
    classifications: tuple[str, ...] = ()
    exposure: str | None = None  # "internet_facing" | "customer_facing"
    owner: str | None = None  # membership_id, "me", or "unassigned"
    needs_attention: bool = False


@dataclass(frozen=True, slots=True)
class AssetInput:
    """The fields create/update accept. Criticality is derived, so the caller
    supplies the CIA inputs and the override, never the score/tier."""

    name: str
    asset_type: str = "application"
    description: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    environment: str | None = None
    location: str | None = None
    vendor_ref: str | None = None
    data_classification: str | None = None
    regulated_data_type: str | None = None
    compliance_scope: tuple[str, ...] = ()
    internet_facing: bool = False
    customer_facing: bool = False
    network_segment: str | None = None
    business_function: str | None = None
    confidentiality: int | None = None
    integrity: int | None = None
    availability: int | None = None
    tier_override: str | None = None
    tier_override_reason: str | None = None
    primary_owner_membership_id: uuid.UUID | None = None
    secondary_owner_membership_id: uuid.UUID | None = None
    business_owner_membership_id: uuid.UUID | None = None
    custodian_membership_id: uuid.UUID | None = None
    escalation_contact_membership_id: uuid.UUID | None = None
    owning_team_group_id: uuid.UUID | None = None
    valuation: float | None = None
    business_impact_notes: str | None = None
    operational_dependency_rating: str | None = None


def _member_of(mid: uuid.UUID | None, names: dict[uuid.UUID, str]) -> Member | None:
    if mid is None:
        return None
    return Member(membership_id=mid, name=names.get(mid, "Unknown"))


# -- service -----------------------------------------------------------------


_MAX_SHEET_BYTES: Final = 10 * 1024 * 1024


def _sheet_cell(value: object) -> str:
    """One Excel cell as the text a CSV would have held."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def read_sheet(data: bytes) -> list[list[str]]:
    """The first worksheet of an .xlsx file as text rows, header first, blank rows dropped.

    The import page previews and validates in the browser and reads CSV itself;
    Excel is the one format it cannot open, so the server only turns the workbook
    into the same grid and the import then goes through ``import_assets`` as ever.
    """
    if len(data) > _MAX_SHEET_BYTES:
        raise InvalidInput(
            "This file is larger than 10 MB. Split it and import the parts one at a time.",
            detail="asset import sheet too large (max 10 MB)",
        )
    from zipfile import BadZipFile  # noqa: PLC0415

    import openpyxl  # noqa: PLC0415 — heavy import, only on the Excel path
    from openpyxl.utils.exceptions import InvalidFileException  # noqa: PLC0415

    try:
        workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, KeyError, ValueError, OSError) as exc:
        raise InvalidInput(
            "We could not read this Excel file. Save it as .xlsx and try again.",
            detail=f"openpyxl could not open the upload ({type(exc).__name__})",
        ) from exc
    try:
        sheet = workbook.active
        if sheet is None:
            return []
        rows = ([_sheet_cell(v) for v in values] for values in sheet.iter_rows(values_only=True))
        return [cells for cells in rows if any(cells)]
    finally:
        workbook.close()


class AssetService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- cross-module resolution (rule 4) ------------------------------------

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    async def _vuln_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, int]:
        """Open-vulnerability count per asset (rule 4, service->service)."""
        from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
            vulnerability_service,
        )

        return await vulnerability_service.open_counts_by_asset(session, tenant_id=tenant_id)

    async def _rescore_vulns(
        self, session: AsyncSession, tenant_id: uuid.UUID, asset_id: uuid.UUID
    ) -> None:
        """Re-prioritise the asset's open vulnerabilities after a criticality or
        exposure change (rule 4, service->service)."""
        from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
            vulnerability_service,
        )

        await vulnerability_service.rescore_for_asset(
            session, tenant_id=tenant_id, asset_id=asset_id
        )

    async def _group_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        groups = await iam_service.list_groups(session, tenant_id=tenant_id)
        return {g.id: g.name for g in groups}

    # -- helpers -------------------------------------------------------------

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, asset_id: uuid.UUID
    ) -> Asset:
        # populate_existing forces a fresh row so a mutating method that re-renders
        # through here does not read an expired server-computed column.
        asset = await session.get(Asset, asset_id, populate_existing=True)
        if asset is None or asset.tenant_id != tenant_id:
            raise NotFound(
                "This asset no longer exists. It may have been deleted.",
                detail=f"asset {asset_id}",
            )
        return asset

    def _actor_membership(self, actor: Actor) -> uuid.UUID | None:
        return actor.id if isinstance(actor, Membership) else None

    async def _transition_row(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        asset: Asset,
        actor: Actor,
        field_changed: str,
        old: str | None,
        new: str | None,
        note: str | None,
    ) -> None:
        session.add(
            AssetTransition(
                id=uuid7(),
                tenant_id=asset.tenant_id,
                asset_id=asset.id,
                actor_membership_id=self._actor_membership(actor),
                field_changed=field_changed,
                old_value=old,
                new_value=new,
                note=note,
                occurred_at=datetime.now(UTC),
            )
        )

    def _apply_criticality(self, asset: Asset) -> None:
        """Recompute and store score + tier from the CIA/exposure inputs. The
        override is left untouched; the view surfaces both."""
        result = compute_criticality(
            asset.confidentiality,
            asset.integrity,
            asset.availability,
            internet_facing=asset.internet_facing,
            data_classification=asset.data_classification,
            business_function=asset.business_function,
        )
        asset.criticality_score = result[0] if result else None
        asset.tier = result[1] if result else None

    def _to_view(
        self,
        asset: Asset,
        names: dict[uuid.UUID, str],
        groups: dict[uuid.UUID, str],
        now: datetime,
        vuln_counts: dict[uuid.UUID, int] | None = None,
    ) -> AssetView:
        score, missing, stale = compute_hygiene(asset, now=now)
        return AssetView(
            id=asset.id,
            name=asset.name,
            asset_type=asset.asset_type,
            description=asset.description or "",
            hostname=asset.hostname,
            ip_address=asset.ip_address,
            fqdn=asset.fqdn,
            os_normalized=asset.os_normalized,
            environment=asset.environment,
            location=asset.location,
            vendor_ref=asset.vendor_ref,
            data_classification=asset.data_classification,
            regulated_data_type=asset.regulated_data_type,
            compliance_scope=list(asset.compliance_scope or []),
            internet_facing=asset.internet_facing,
            customer_facing=asset.customer_facing,
            network_segment=asset.network_segment,
            business_function=asset.business_function,
            criticality=CriticalityView(
                confidentiality=asset.confidentiality,
                integrity=asset.integrity,
                availability=asset.availability,
                score=asset.criticality_score,
                tier=asset.tier,
                tier_override=asset.tier_override,
                tier_override_reason=asset.tier_override_reason,
            ),
            ownership=OwnershipView(
                primary_owner=_member_of(asset.primary_owner_membership_id, names),
                secondary_owner=_member_of(asset.secondary_owner_membership_id, names),
                business_owner=_member_of(asset.business_owner_membership_id, names),
                custodian=_member_of(asset.custodian_membership_id, names),
                escalation_contact=_member_of(asset.escalation_contact_membership_id, names),
                owning_team=groups.get(asset.owning_team_group_id)
                if asset.owning_team_group_id
                else None,
            ),
            status=asset.status,
            replaced_by_asset_id=asset.replaced_by_asset_id,
            valuation=asset.valuation,
            first_seen_at=asset.first_seen_at,
            last_seen_at=asset.last_seen_at,
            last_reviewed_at=asset.last_reviewed_at,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            source=asset.source,
            hygiene=HygieneView(score=score, missing=missing, is_stale=stale),
            vuln_count=(vuln_counts or {}).get(asset.id, 0),
            link_count=0,
            relationship_count=0,
        )

    # -- reads ---------------------------------------------------------------

    async def list_assets(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        filters: AssetFilters,
        page: int = 1,
        page_size: int = 25,
        caller_membership_id: uuid.UUID | None = None,
    ) -> tuple[list[AssetView], int]:
        stmt = select(Asset).where(Asset.tenant_id == tenant_id)
        if filters.asset_type and filters.asset_type != "all":
            stmt = stmt.where(Asset.asset_type == filters.asset_type)
        if filters.statuses:
            stmt = stmt.where(Asset.status.in_(list(filters.statuses)))
        if filters.tiers:
            stmt = stmt.where(
                func.coalesce(Asset.tier_override, Asset.tier).in_(list(filters.tiers))
            )
        if filters.environments:
            stmt = stmt.where(Asset.environment.in_(list(filters.environments)))
        if filters.classifications:
            stmt = stmt.where(Asset.data_classification.in_(list(filters.classifications)))
        if filters.exposure == "internet_facing":
            stmt = stmt.where(Asset.internet_facing.is_(True))
        elif filters.exposure == "customer_facing":
            stmt = stmt.where(Asset.customer_facing.is_(True))
        if filters.owner == "unassigned":
            stmt = stmt.where(Asset.primary_owner_membership_id.is_(None))
        elif filters.owner == "me" and caller_membership_id is not None:
            stmt = stmt.where(Asset.primary_owner_membership_id == caller_membership_id)
        elif filters.owner:
            stmt = stmt.where(Asset.primary_owner_membership_id == uuid.UUID(filters.owner))
        if filters.search:
            like = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Asset.name).like(like),
                    func.lower(func.coalesce(Asset.hostname, "")).like(like),
                    func.lower(func.coalesce(Asset.ip_address, "")).like(like),
                    func.lower(func.coalesce(Asset.fqdn, "")).like(like),
                )
            )

        assets = list((await session.execute(stmt)).scalars())
        now = datetime.now(UTC)
        names = await self._member_names(session, tenant_id)
        groups = await self._group_names(session, tenant_id)
        vuln_counts = await self._vuln_counts(session, tenant_id)
        views = [self._to_view(a, names, groups, now, vuln_counts) for a in assets]
        if filters.needs_attention:
            views = [v for v in views if v.hygiene.missing or v.hygiene.is_stale]

        views.sort(key=self._register_sort_key)
        total = len(views)
        start = (page - 1) * page_size
        return views[start : start + page_size], total

    async def asset_refs(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        asset_ids: Sequence[uuid.UUID] | None = None,
    ) -> dict[uuid.UUID, AssetRef]:
        """Lightweight (id -> AssetRef) map for sibling modules. Pass ``asset_ids``
        to scope it, or omit for the whole tenant. The effective tier is the
        override when set, else the derived tier."""
        stmt = select(Asset).where(Asset.tenant_id == tenant_id)
        if asset_ids is not None:
            ids = list(asset_ids)
            if not ids:
                return {}
            stmt = stmt.where(Asset.id.in_(ids))
        rows = (await session.execute(stmt)).scalars()
        return {
            a.id: AssetRef(
                id=a.id,
                name=a.name,
                host=a.hostname or a.fqdn or a.ip_address,
                tier=a.tier_override or a.tier,
                internet_facing=a.internet_facing,
                customer_facing=a.customer_facing,
                confidentiality=a.confidentiality,
                integrity=a.integrity,
                availability=a.availability,
                primary_owner_membership_id=a.primary_owner_membership_id,
                escalation_contact_membership_id=a.escalation_contact_membership_id,
                status=a.status,
            )
            for a in rows
        }

    @staticmethod
    def _register_sort_key(v: AssetView) -> tuple[int, int, str]:
        tier = v.criticality.tier_override or v.criticality.tier
        tier_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(tier or "", 9)
        attention = 0 if (v.hygiene.missing or v.hygiene.is_stale) else 1
        return tier_rank, attention, v.name.lower()

    async def get_asset(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, asset_id: uuid.UUID
    ) -> AssetDetailView:
        asset = await self._load(session, tenant_id, asset_id)
        now = datetime.now(UTC)
        names = await self._member_names(session, tenant_id)
        groups = await self._group_names(session, tenant_id)
        vuln_counts = await self._vuln_counts(session, tenant_id)
        base = self._to_view(asset, names, groups, now, vuln_counts)

        transitions = list(
            (
                await session.execute(
                    select(AssetTransition)
                    .where(
                        AssetTransition.tenant_id == tenant_id, AssetTransition.asset_id == asset.id
                    )
                    .order_by(AssetTransition.occurred_at.desc())
                )
            ).scalars()
        )
        record = (
            await session.execute(
                select(DecommissionRecord).where(
                    DecommissionRecord.tenant_id == tenant_id,
                    DecommissionRecord.asset_id == asset.id,
                )
            )
        ).scalar_one_or_none()

        return AssetDetailView(
            **{f: getattr(base, f) for f in base.__dataclass_fields__},
            serial_number=asset.serial_number,
            primary_mac=asset.primary_mac,
            cloud_resource_id=asset.cloud_resource_id,
            business_impact_notes=asset.business_impact_notes,
            operational_dependency_rating=asset.operational_dependency_rating,
            decommission=(
                DecommissionView(
                    disposal_method=record.disposal_method,
                    media_sanitised=record.media_sanitised,
                    replacement_asset_id=record.replacement_asset_id,
                    evidence_ref=record.evidence_ref,
                    reason=record.reason,
                    decommissioned_by=names.get(record.decommissioned_by_membership_id)
                    if record.decommissioned_by_membership_id
                    else None,
                    decommissioned_at=record.decommissioned_at,
                )
                if record
                else None
            ),
            transitions=[
                TransitionView(
                    id=t.id,
                    actor=names.get(t.actor_membership_id) if t.actor_membership_id else None,
                    field_changed=t.field_changed,
                    old_value=t.old_value,
                    new_value=t.new_value,
                    note=t.note,
                    occurred_at=t.occurred_at,
                )
                for t in transitions
            ],
            watchers=[],
            allowed_transitions=list(LIFECYCLE_TRANSITIONS[asset.status]),
        )

    # -- writes --------------------------------------------------------------

    def _assign(self, asset: Asset, data: AssetInput) -> None:
        asset.name = data.name.strip()
        asset.asset_type = data.asset_type
        asset.description = (data.description or "").strip() or None
        asset.hostname = data.hostname
        asset.ip_address = data.ip_address
        asset.environment = data.environment
        asset.location = data.location
        asset.vendor_ref = data.vendor_ref
        asset.data_classification = data.data_classification
        asset.regulated_data_type = data.regulated_data_type
        asset.compliance_scope = list(data.compliance_scope)
        asset.internet_facing = data.internet_facing
        asset.customer_facing = data.customer_facing
        asset.network_segment = data.network_segment
        asset.business_function = data.business_function
        asset.confidentiality = data.confidentiality
        asset.integrity = data.integrity
        asset.availability = data.availability
        asset.tier_override = data.tier_override
        asset.tier_override_reason = data.tier_override_reason
        asset.primary_owner_membership_id = data.primary_owner_membership_id
        asset.secondary_owner_membership_id = data.secondary_owner_membership_id
        asset.business_owner_membership_id = data.business_owner_membership_id
        asset.custodian_membership_id = data.custodian_membership_id
        asset.escalation_contact_membership_id = data.escalation_contact_membership_id
        asset.owning_team_group_id = data.owning_team_group_id
        asset.valuation = data.valuation
        asset.business_impact_notes = data.business_impact_notes
        asset.operational_dependency_rating = data.operational_dependency_rating

    async def create_asset(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, data: AssetInput
    ) -> AssetDetailView:
        if not data.name.strip():
            raise InvalidInput(
                "Give this asset a name before saving it.",
                detail="an asset needs a name",
            )
        now = datetime.now(UTC)
        asset = Asset(
            id=uuid7(),
            tenant_id=tenant_id,
            status="planned",
            first_seen_at=now,
            last_reviewed_at=now,
        )
        self._assign(asset, data)
        self._apply_criticality(asset)
        session.add(asset)
        await session.flush([asset])
        await self._transition_row(session, asset, actor, "created", None, asset.name, None)
        await self._audit.record(
            session,
            action="create",
            object_type="asset",
            object_id=asset.id,
            actor=actor,
            tenant_id=tenant_id,
            after={
                "name": asset.name,
                "asset_type": asset.asset_type,
                "tier": _effective_tier(asset),
            },
        )
        await session.flush()
        return await self.get_asset(session, tenant_id=tenant_id, asset_id=asset.id)

    async def update_asset(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        asset_id: uuid.UUID,
        data: AssetInput,
    ) -> AssetDetailView:
        asset = await self._load(session, tenant_id, asset_id)
        before = _effective_tier(asset)
        before_exposure = (asset.internet_facing, asset.customer_facing)
        self._assign(asset, data)
        self._apply_criticality(asset)
        asset.last_reviewed_at = datetime.now(UTC)
        after = _effective_tier(asset)
        if before != after:
            await self._transition_row(session, asset, actor, "criticality", before, after, None)
        await self._audit.record(
            session,
            action="update",
            object_type="asset",
            object_id=asset.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"name": asset.name, "tier": after},
        )
        await session.flush()
        # Criticality/exposure feed vulnerability prioritisation — re-score this
        # asset's open findings when either changed (rule 4, service->service).
        if before != after or before_exposure != (asset.internet_facing, asset.customer_facing):
            await self._rescore_vulns(session, tenant_id, asset.id)
        return await self.get_asset(session, tenant_id=tenant_id, asset_id=asset.id)

    async def transition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        asset_id: uuid.UUID,
        to_status: str,
        note: str | None = None,
    ) -> AssetDetailView:
        asset = await self._load(session, tenant_id, asset_id)
        if to_status not in LIFECYCLE_TRANSITIONS:
            raise InvalidInput(
                "That is not a lifecycle status we recognise. "
                "Choose one of the statuses offered for this asset.",
                detail=f"unknown status {to_status!r}",
            )
        if to_status not in LIFECYCLE_TRANSITIONS[asset.status]:
            raise Conflict(
                "This asset cannot move to that status from where it is now. "
                "Refresh the page to see the moves available.",
                detail=f"cannot move a {asset.status} asset to {to_status}",
            )
        old = asset.status
        asset.status = to_status
        await self._transition_row(session, asset, actor, "status", old, to_status, note)
        await self._audit.record(
            session,
            action="transition",
            object_type="asset",
            object_id=asset.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": old},
            after={"status": to_status},
        )
        await session.flush()
        return await self.get_asset(session, tenant_id=tenant_id, asset_id=asset.id)

    async def decommission(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        asset_id: uuid.UUID,
        disposal_method: str,
        media_sanitised: bool,
        replacement_asset_id: uuid.UUID | None,
        evidence_ref: str | None,
        reason: str,
    ) -> AssetDetailView:
        asset = await self._load(session, tenant_id, asset_id)
        if "decommissioned" not in LIFECYCLE_TRANSITIONS[asset.status]:
            raise Conflict(
                "This asset cannot be decommissioned from its current status. "
                "Refresh the page to see the actions available for it.",
                detail=f"cannot decommission a {asset.status} asset",
            )
        if not reason.strip():
            raise InvalidInput(
                "Give a reason before decommissioning this asset.",
                detail="a reason is required to decommission an asset",
            )
        now = datetime.now(UTC)
        old = asset.status
        asset.status = "decommissioned"
        asset.replaced_by_asset_id = replacement_asset_id
        session.add(
            DecommissionRecord(
                id=uuid7(),
                tenant_id=tenant_id,
                asset_id=asset.id,
                disposal_method=disposal_method,
                media_sanitised=media_sanitised,
                replacement_asset_id=replacement_asset_id,
                evidence_ref=evidence_ref,
                reason=reason.strip(),
                decommissioned_by_membership_id=self._actor_membership(actor),
                decommissioned_at=now,
            )
        )
        # Retiring the host removes the exposure, so its open vulnerabilities close
        # with a recorded reason (spec 123). Cross-module, service->service (rule 4).
        from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
            vulnerability_service,
        )

        await vulnerability_service.close_open_for_asset(
            session, tenant_id=tenant_id, actor=actor, asset_id=asset.id, reason=reason.strip()
        )
        await self._transition_row(
            session, asset, actor, "status", old, "decommissioned", reason.strip()
        )
        await self._audit.record(
            session,
            action="transition",
            object_type="asset",
            object_id=asset.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"status": old},
            after={"status": "decommissioned", "disposal_method": disposal_method},
        )
        await session.flush()
        return await self.get_asset(session, tenant_id=tenant_id, asset_id=asset.id)

    async def record_review(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, asset_id: uuid.UUID
    ) -> AssetDetailView:
        asset = await self._load(session, tenant_id, asset_id)
        asset.last_reviewed_at = datetime.now(UTC)
        await self._transition_row(
            session, asset, actor, "reviewed", None, "inventory reviewed", None
        )
        await self._audit.record(
            session,
            action="update",
            object_type="asset",
            object_id=asset.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"last_reviewed_at": asset.last_reviewed_at.isoformat()},
        )
        await session.flush()
        return await self.get_asset(session, tenant_id=tenant_id, asset_id=asset.id)

    async def import_assets(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        rows: Sequence[AssetInput],
        statuses: Sequence[str] | None = None,
    ) -> int:
        now = datetime.now(UTC)
        for index, data in enumerate(rows):
            asset = Asset(
                id=uuid7(),
                tenant_id=tenant_id,
                status=statuses[index] if statuses else "active",
                source="import",
                first_seen_at=now,
                last_seen_at=now,
                last_reviewed_at=now,
            )
            self._assign(asset, data)
            self._apply_criticality(asset)
            session.add(asset)
            await session.flush([asset])
            await self._transition_row(
                session, asset, actor, "created", None, asset.name, "imported"
            )
            await self._audit.record(
                session,
                action="create",
                object_type="asset",
                object_id=asset.id,
                actor=actor,
                tenant_id=tenant_id,
                after={"name": asset.name, "source": "import"},
            )
        return len(rows)

    # -- dashboard -----------------------------------------------------------

    async def summary(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
        assets = list(
            (await session.execute(select(Asset).where(Asset.tenant_id == tenant_id))).scalars()
        )
        now = datetime.now(UTC)
        by_tier = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unassessed": 0}
        by_status = dict.fromkeys(LIFECYCLE_TRANSITIONS, 0)
        by_type: dict[str, int] = {}
        needs_cia = regulated = stale = hygiene_total = 0
        for a in assets:
            by_tier[_effective_tier(a) or "unassessed"] += 1
            by_status[a.status] = by_status.get(a.status, 0) + 1
            by_type[a.asset_type] = by_type.get(a.asset_type, 0) + 1
            score, missing, is_stale = compute_hygiene(a, now=now)
            if "no_cia" in missing:
                needs_cia += 1
            if a.regulated_data_type or "PCI" in (a.compliance_scope or []):
                regulated += 1
            if is_stale:
                stale += 1
            hygiene_total += score
        return {
            "total": len(assets),
            "by_tier": by_tier,
            "by_type": sorted(
                ({"type": t, "count": c} for t, c in by_type.items()), key=lambda x: -x["count"]
            ),
            "by_status": by_status,
            "needs_cia": needs_cia,
            "regulated": regulated,
            "stale": stale,
            "hygiene_avg": round(hygiene_total / len(assets)) if assets else 0,
        }

    async def facets(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
        assets = list(
            (await session.execute(select(Asset).where(Asset.tenant_id == tenant_id))).scalars()
        )
        now = datetime.now(UTC)
        asset_type: dict[str, int] = {}
        status: dict[str, int] = {}
        environment: dict[str, int] = {}
        tier = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unassessed": 0}
        needs_attention = 0
        for a in assets:
            asset_type[a.asset_type] = asset_type.get(a.asset_type, 0) + 1
            status[a.status] = status.get(a.status, 0) + 1
            if a.environment:
                environment[a.environment] = environment.get(a.environment, 0) + 1
            tier[_effective_tier(a) or "unassessed"] += 1
            _score, missing, is_stale = compute_hygiene(a, now=now)
            if missing or is_stale:
                needs_attention += 1
        return {
            "asset_type": asset_type,
            "tier": tier,
            "status": status,
            "environment": environment,
            "needs_attention": needs_attention,
        }


asset_service = AssetService()
